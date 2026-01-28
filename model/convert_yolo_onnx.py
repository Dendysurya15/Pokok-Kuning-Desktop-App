"""
Auto PT to ONNX Converter
Otomatis convert semua file .pt ke .onnx di folder yang sama

Usage:
    python convert_pt_to_onnx.py                    # Convert semua .pt di current folder
    python convert_pt_to_onnx.py /path/to/folder    # Convert di folder tertentu
    python convert_pt_to_onnx.py model.pt           # Convert file spesifik
"""

import os
import sys
import glob
from pathlib import Path


def check_dependencies():
    """Check required libraries"""
    missing = []
    
    try:
        import torch
    except ImportError:
        missing.append("torch")
    
    try:
        from ultralytics import YOLO
    except ImportError:
        missing.append("ultralytics")
    
    try:
        import onnx
        # Check if onnx has __version__ attribute (some versions don't expose it)
        if not hasattr(onnx, '__version__'):
            # Try to get version another way
            try:
                import onnx.version
                version = onnx.version.version
            except:
                print("⚠️  Warning: Could not determine ONNX version, but package is installed")
    except ImportError:
        missing.append("onnx")
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("\n📦 Install dependencies:")
        print("   pip install -r requirements.txt")
        print("   or")
        print("   pip install torch torchvision ultralytics onnx onnxruntime-gpu")
        return False
    
    return True


def get_device():
    """Get best available device"""
    import torch
    if torch.cuda.is_available():
        device = 'cuda:0'
        gpu_name = torch.cuda.get_device_name(0)
        print(f"🎮 Using GPU: {gpu_name}")
    else:
        device = 'cpu'
        print(f"💻 Using CPU")
    return device


def convert_pt_to_onnx(pt_path, onnx_path=None, imgsz=640, device='cpu', skip_existing=True):
    """
    Convert single .pt file to .onnx
    
    Args:
        pt_path: Path to .pt file
        onnx_path: Output path (auto-generate if None)
        imgsz: Image size for export
        device: 'cpu' or 'cuda:0'
        skip_existing: Skip if .onnx already exists
    """
    from ultralytics import YOLO
    
    pt_path = Path(pt_path)
    if not pt_path.exists():
        print(f"❌ File not found: {pt_path}")
        return False
    
    # Auto-generate output path
    if onnx_path is None:
        onnx_path = pt_path.with_suffix('.onnx')
    else:
        onnx_path = Path(onnx_path)
    
    # Skip if exists
    if skip_existing and onnx_path.exists():
        size_mb = onnx_path.stat().st_size / (1024 * 1024)
        print(f"⏭️  Skip (already exists): {onnx_path.name} ({size_mb:.1f} MB)")
        return True
    
    try:
        print(f"\n📥 Loading: {pt_path.name}")
        model = YOLO(str(pt_path))
        
        # Move to device
        model.to(device)
        
        print(f"⚙️  Exporting to ONNX (imgsz={imgsz})...")
        model.export(
            format="onnx",
            imgsz=imgsz,
            simplify=True,
            opset=12,
            dynamic=False,
            half=False,
            device=device,
        )
        
        # Ultralytics creates .onnx in same dir as .pt
        auto_onnx = pt_path.with_suffix('.onnx')
        
        # Move to desired location if different
        if auto_onnx.exists() and auto_onnx != onnx_path:
            auto_onnx.rename(onnx_path)
        
        if onnx_path.exists():
            size_mb = onnx_path.stat().st_size / (1024 * 1024)
            print(f"✅ Success: {onnx_path.name} ({size_mb:.1f} MB)")
            return True
        else:
            print(f"❌ Failed: Output not found at {onnx_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error converting {pt_path.name}: {e}")
        return False


def find_pt_files(directory):
    """Find all .pt files in directory"""
    directory = Path(directory)
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return []
    
    pt_files = list(directory.glob("*.pt"))
    return sorted(pt_files)


def main():
    """Main function"""
    print("=" * 60)
    print("🔄 PT to ONNX Converter")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Get device
    device = get_device()
    
    # Parse arguments
    if len(sys.argv) > 1:
        target = sys.argv[1]
        target_path = Path(target)
        
        # Single file
        if target_path.is_file() and target_path.suffix == '.pt':
            print(f"\n📂 Converting single file: {target_path}")
            pt_files = [target_path]
        # Directory
        elif target_path.is_dir():
            print(f"\n📂 Scanning directory: {target_path}")
            pt_files = find_pt_files(target_path)
        else:
            print(f"❌ Invalid path: {target}")
            sys.exit(1)
    else:
        # Current directory
        print(f"\n📂 Scanning current directory")
        pt_files = find_pt_files(Path.cwd())
    
    # Check if any .pt files found
    if not pt_files:
        print("\n⚠️  No .pt files found!")
        sys.exit(0)
    
    print(f"\n📋 Found {len(pt_files)} .pt file(s):")
    for i, pt_file in enumerate(pt_files, 1):
        size_mb = pt_file.stat().st_size / (1024 * 1024)
        print(f"   {i}. {pt_file.name} ({size_mb:.1f} MB)")
    
    # Convert each file
    print(f"\n{'=' * 60}")
    print("🚀 Starting conversion...")
    print(f"{'=' * 60}")
    
    success_count = 0
    failed_count = 0
    
    for i, pt_file in enumerate(pt_files, 1):
        print(f"\n[{i}/{len(pt_files)}]", end=" ")
        
        # You can customize imgsz per file if needed
        imgsz = 640  # Change this if needed
        
        if convert_pt_to_onnx(pt_file, imgsz=imgsz, device=device):
            success_count += 1
        else:
            failed_count += 1
    
    # Summary
    print(f"\n{'=' * 60}")
    print("📊 Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed:  {failed_count}")
    print(f"   📁 Total:   {len(pt_files)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()