# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
import os
from pathlib import Path

# Explicit paths for yolov9 environment
YOLOV9_ENV_PATH = r"C:\Users\jaja.valentino\AppData\Local\anaconda3\envs\yolov9"
SITE_PACKAGES = r"C:\Users\jaja.valentino\AppData\Local\anaconda3\envs\yolov9\Lib\site-packages"

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

# Hidden imports for ultralytics and other dependencies + minimal CUDA
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
    
    # PyTorch with basic CUDA support
    'torch',
    'torch.cuda',
    'torch.backends',
    'torch.backends.cuda',
    'torch.backends.cudnn',
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

# Collect packages from specific yolov9 environment
def collect_from_yolov9_env():
    """Collect packages specifically from yolov9 environment"""
    data_files = []
    
    # Add torch package from yolov9 environment
    torch_path = os.path.join(SITE_PACKAGES, 'torch')
    if os.path.exists(torch_path):
        data_files.append((torch_path, 'torch'))
        print(f"Added torch from yolov9 env: {torch_path}")
    
    # Add torchvision package
    torchvision_path = os.path.join(SITE_PACKAGES, 'torchvision')
    if os.path.exists(torchvision_path):
        data_files.append((torchvision_path, 'torchvision'))
        print(f"Added torchvision from yolov9 env: {torchvision_path}")
    
    # Add ultralytics package
    ultralytics_path = os.path.join(SITE_PACKAGES, 'ultralytics')
    if os.path.exists(ultralytics_path):
        data_files.append((ultralytics_path, 'ultralytics'))
        print(f"Added ultralytics from yolov9 env: {ultralytics_path}")
    
    return data_files

# Add packages from yolov9 environment
added_files.extend(collect_from_yolov9_env())

# Add basic CUDA DLLs from yolov9 environment if available
cuda_lib_path = os.path.join(YOLOV9_ENV_PATH, 'Library', 'bin')
if os.path.exists(cuda_lib_path):
    print(f"Looking for CUDA files in: {cuda_lib_path}")
    essential_cuda_files = [
        'cudart64_12.dll', 'cublas64_12.dll', 'cublasLt64_12.dll'
    ]
    for cuda_file in essential_cuda_files:
        cuda_file_path = os.path.join(cuda_lib_path, cuda_file)
        if os.path.exists(cuda_file_path):
            added_files.append((cuda_file_path, '.'))
            print(f"Added CUDA file: {cuda_file}")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-cuda-simple.py'] if os.path.exists('hook-cuda-simple.py') else [],
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
    console=True,  # Keep True for CUDA debugging and stability
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
