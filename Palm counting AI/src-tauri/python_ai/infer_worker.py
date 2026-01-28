"""
Python sidecar untuk conversion model .pt → .onnx.
Hanya untuk conversion, semua inference dilakukan di Rust dengan ONNX.

Usage: infer_worker.py --convert <input.pt> <output.onnx> <imgsz>
"""
from __future__ import annotations

import os
import sys

# Redirect stderr to help with debugging
def log_error(msg: str) -> None:
    """Log error to stderr (will be captured by Rust)"""
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)


def convert_mode() -> None:
    """Conversion mode: convert .pt to .onnx"""
    if len(sys.argv) < 4:
        log_error("Usage: infer_worker.py --convert <input.pt> <output.onnx> <imgsz>")
        sys.exit(1)
    
    pt_path = sys.argv[2]
    onnx_path = sys.argv[3]
    imgsz = int(sys.argv[4]) if len(sys.argv) > 4 else 1280
    
    try:
        from ultralytics import YOLO
    except ImportError as e:
        log_error(f"Failed to import ultralytics: {e}")
        log_error("Please install: pip install ultralytics")
        sys.exit(1)
    
    try:
        print(f"Loading model: {pt_path}", file=sys.stderr, flush=True)
        model = YOLO(pt_path)
        
        print(f"Exporting to ONNX: {onnx_path}", file=sys.stderr, flush=True)
        model.export(
            format="onnx",
            imgsz=imgsz,
            simplify=True,
            opset=12,
            dynamic=False,
            half=False,
        )
        
        # Ultralytics exports to same directory with .onnx extension
        # Move to desired location
        exported_path = os.path.splitext(pt_path)[0] + ".onnx"
        if os.path.exists(exported_path) and exported_path != onnx_path:
            import shutil
            shutil.move(exported_path, onnx_path)
            print(f"Moved {exported_path} -> {onnx_path}", file=sys.stderr, flush=True)
        
        if not os.path.exists(onnx_path):
            # Try to find the exported file
            possible_paths = [
                os.path.splitext(pt_path)[0] + ".onnx",
                os.path.join(os.path.dirname(onnx_path), os.path.basename(os.path.splitext(pt_path)[0] + ".onnx")),
            ]
            for pp in possible_paths:
                if os.path.exists(pp):
                    import shutil
                    shutil.move(pp, onnx_path)
                    print(f"Found and moved: {pp} -> {onnx_path}", file=sys.stderr, flush=True)
                    break
        
        if os.path.exists(onnx_path):
            size_mb = os.path.getsize(onnx_path) / (1024 * 1024)
            print(f"✓ Conversion successful: {onnx_path} ({size_mb:.2f} MB)", file=sys.stderr, flush=True)
            sys.exit(0)
        else:
            log_error(f"ONNX file not found at {onnx_path}")
            sys.exit(1)
            
    except Exception as e:
        log_error(f"Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Hanya support conversion mode
    if len(sys.argv) > 1 and sys.argv[1] == "--convert":
        convert_mode()
    else:
        log_error("This script only supports conversion mode.")
        log_error("Usage: infer_worker.py --convert <input.pt> <output.onnx> <imgsz>")
        log_error("All inference is done in Rust with ONNX models.")
        sys.exit(1)
