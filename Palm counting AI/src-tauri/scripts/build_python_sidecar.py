"""
Build Python sidecar untuk Tauri.
Menggunakan PyInstaller untuk bundle infer_worker.py sebagai standalone executable.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def get_target_triple():
    """Get Rust target triple untuk platform saat ini"""
    result = subprocess.run(
        ["rustc", "--print", "target-triple"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    # Fallback untuk Windows
    if sys.platform == "win32":
        return "x86_64-pc-windows-msvc"
    elif sys.platform == "darwin":
        return "aarch64-apple-darwin" if "arm" in os.uname().machine else "x86_64-apple-darwin"
    else:
        return "x86_64-unknown-linux-gnu"

def build_python_sidecar():
    """Build Python worker sebagai standalone executable dengan PyInstaller"""
    script_dir = Path(__file__).parent
    src_tauri_dir = script_dir.parent  # scripts/ -> src-tauri/
    python_ai_dir = src_tauri_dir / "python_ai"  # python_ai sekarang di src-tauri/
    binaries_dir = src_tauri_dir / "binaries"
    
    # Buat direktori binaries jika belum ada
    binaries_dir.mkdir(exist_ok=True)
    
    # Path ke infer_worker.py
    worker_script = python_ai_dir / "infer_worker.py"
    if not worker_script.exists():
        print(f"ERROR: {worker_script} tidak ditemukan!")
        return False
    
    print(f"Building Python sidecar dari {worker_script}")
    
    # Install PyInstaller jika belum ada
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Build dengan PyInstaller
    target_triple = get_target_triple()
    output_name = f"infer_worker-{target_triple}"
    
    print(f"Target triple: {target_triple}")
    print(f"Output name: {output_name}")
    
    # PyInstaller command
    # Note: --collect-all akan bundle semua submodules, penting untuk PyTorch/CUDA
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "infer_worker",
        "--hidden-import", "ultralytics",
        "--hidden-import", "torch",
        "--hidden-import", "torchvision",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "numpy",
        "--collect-all", "ultralytics",  # Bundle semua ultralytics modules
        "--collect-all", "torch",         # Bundle semua torch modules (termasuk CUDA)
        "--collect-all", "torchvision",  # Bundle torchvision
        "--noconsole",  # Hide console window (optional, bisa dihapus untuk debugging)
        str(worker_script)
    ]
    
    print(f"Running: {' '.join(pyinstaller_cmd)}")
    
    # Run PyInstaller
    result = subprocess.run(
        pyinstaller_cmd,
        cwd=python_ai_dir,
        check=False
    )
    
    if result.returncode != 0:
        print("ERROR: PyInstaller build failed!")
        return False
    
    # Move hasil build ke binaries directory
    dist_dir = python_ai_dir / "dist"
    if sys.platform == "win32":
        build_output = dist_dir / "infer_worker.exe"
    else:
        build_output = dist_dir / "infer_worker"
    
    if not build_output.exists():
        print(f"ERROR: Build output tidak ditemukan: {build_output}")
        print(f"  Dist directory contents: {list(dist_dir.iterdir()) if dist_dir.exists() else 'not found'}")
        return False
    
    # Rename sesuai target triple
    final_output = binaries_dir / output_name
    if sys.platform == "win32" and not final_output.suffix:
        final_output = final_output.with_suffix(".exe")
    
    print(f"Copying {build_output} -> {final_output}")
    shutil.copy2(build_output, final_output)
    
    # Cleanup PyInstaller artifacts
    build_dir = python_ai_dir / "build"
    spec_file = python_ai_dir / "infer_worker.spec"
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if spec_file.exists():
        spec_file.unlink()
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    print(f"✓ Python sidecar berhasil dibuild: {final_output}")
    print(f"  Size: {final_output.stat().st_size / (1024*1024):.2f} MB")
    
    return True

if __name__ == "__main__":
    success = build_python_sidecar()
    sys.exit(0 if success else 1)
