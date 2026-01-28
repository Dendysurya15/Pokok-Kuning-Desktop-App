"""
Alternatif: Bundle Python Embedded + dependencies.
Lebih kecil tapi perlu setup PATH.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
import zipfile

def download_python_embedded():
    """Download Python embedded untuk Windows"""
    # Python 3.11 embedded
    url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    # Implementasi download jika diperlukan
    pass

def build_python_embedded():
    """Build Python embedded distribution dengan dependencies"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    python_ai_dir = project_root / "python_ai"
    src_tauri_dir = project_root / "src-tauri"
    resources_dir = src_tauri_dir / "resources" / "python"
    
    resources_dir.mkdir(parents=True, exist_ok=True)
    
    print("Building Python embedded distribution...")
    print("NOTE: Ini memerlukan Python embedded yang sudah didownload")
    
    # Copy infer_worker.py
    shutil.copy2(
        python_ai_dir / "infer_worker.py",
        resources_dir / "infer_worker.py"
    )
    
    # Install dependencies ke resources/python
    print("Installing dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install",
        "-r", str(python_ai_dir / "requirements.txt"),
        "--target", str(resources_dir / "site-packages")
    ])
    
    print(f"✓ Python embedded siap di: {resources_dir}")
    return True

if __name__ == "__main__":
    build_python_embedded()
