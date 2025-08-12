#!/usr/bin/env python3
"""
Build script untuk membuat executable dari Pokok Kuning Desktop App
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run command and print output"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0

def build_exe():
    """Build executable using PyInstaller"""
    
    # Get current directory
    current_dir = Path(__file__).parent
    
    # Clean previous builds
    dist_dir = current_dir / "dist"
    build_dir = current_dir / "build"
    
    if dist_dir.exists():
        print("Cleaning previous dist directory...")
        shutil.rmtree(dist_dir)
    
    if build_dir.exists():
        print("Cleaning previous build directory...")
        shutil.rmtree(build_dir)
    
    # Install PyInstaller if not available
    print("Checking PyInstaller...")
    try:
        import PyInstaller
        print("PyInstaller is available")
    except ImportError:
        print("Installing PyInstaller...")
        if not run_command("pip install pyinstaller"):
            print("Failed to install PyInstaller")
            return False
    
    # Create spec file if it doesn't exist
    spec_file = current_dir / "pokok_kuning.spec"
    if not spec_file.exists():
        print("Creating PyInstaller spec file...")
        create_spec_file(spec_file)
    
    # Build the executable
    print("Building executable...")
    cmd = f"pyinstaller --clean {spec_file}"
    
    if not run_command(cmd, cwd=current_dir):
        print("Build failed!")
        return False
    
    print("Build completed successfully!")
    print(f"Executable can be found in: {dist_dir}")
    
    return True

def create_spec_file(spec_path):
    """Create PyInstaller spec file"""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
import os
from pathlib import Path

# Get current directory
current_dir = Path.cwd()

# Define data files and hidden imports
added_files = [
    ('model/*.pt', 'model'),  # Include model files
    ('ui/*.py', 'ui'),
    ('core/*.py', 'core'), 
    ('utils/*.py', 'utils'),
    ('assets', 'assets'),     # Include assets directory with icons and images
]

# Hidden imports for ultralytics and other dependencies
hiddenimports = [
    'ultralytics',
    'ultralytics.models',
    'ultralytics.models.yolo',
    'ultralytics.models.yolo.detect',
    'ultralytics.utils',
    'ultralytics.engine',
    'ultralytics.engine.predictor',
    'cv2',
    'numpy',
    'PIL',
    'PIL.Image',
    'torch',
    'torchvision',
    'geojson',
    'shapely',
    'shapely.geometry',
    'fastkml',
    'geopandas',
    'tqdm',
    'PyQt5.QtCore',
    'PyQt5.QtGui', 
    'PyQt5.QtWidgets',
    'PyQt5.QtOpenGL',
    'PyQt5.QtSvg',
]

# Collect all packages
import pkg_resources
import site
import ultralytics

# Get ultralytics package path
ultralytics_path = ultralytics.__path__[0]
torch_site_packages = None

# Find torch installation
for site_dir in site.getsitepackages() + [site.getusersitepackages()]:
    if site_dir and os.path.exists(os.path.join(site_dir, 'torch')):
        torch_site_packages = site_dir
        break

# Additional data files
if torch_site_packages:
    added_files.extend([
        (os.path.join(torch_site_packages, 'torch'), 'torch'),
        (os.path.join(torch_site_packages, 'torchvision'), 'torchvision'),
    ])

# Add ultralytics data
added_files.append((ultralytics_path, 'ultralytics'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PokokKuningApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging, False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/img/logo.ico',  # Application icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PokokKuningApp',
)
'''
    
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"Spec file created: {spec_path}")

if __name__ == "__main__":
    if build_exe():
        print("\n✅ Build completed successfully!")
        print("\nTo run the executable:")
        print("1. Go to the 'dist/PokokKuningApp' folder")
        print("2. Run 'PokokKuningApp.exe'")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)
