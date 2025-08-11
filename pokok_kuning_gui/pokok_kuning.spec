# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
import os
from pathlib import Path

# Define data files to include
added_files = [
    ('model', 'model'),  # Include entire model directory
    ('ui', 'ui'),        # Include ui package
    ('core', 'core'),    # Include core package
    ('utils', 'utils'),  # Include utils package
    ('README.md', '.'),
]

# Hidden imports for all required packages
hiddenimports = [
    # Local modules
    'ui',
    'ui.main_window',
    'core',
    'core.processor',
    'core.cli',
    'utils',
    'utils.config_manager',
    
    # Ultralytics and YOLO
    'ultralytics',
    'ultralytics.models',
    'ultralytics.models.yolo',
    'ultralytics.models.yolo.detect',
    'ultralytics.models.yolo.detect.predict',
    'ultralytics.utils',
    'ultralytics.utils.plotting',
    'ultralytics.utils.ops',
    'ultralytics.engine',
    'ultralytics.engine.predictor',
    'ultralytics.engine.results',
    'ultralytics.data',
    'ultralytics.data.utils',
    'ultralytics.nn',
    'ultralytics.nn.modules',
    'ultralytics.trackers',
    
    # Computer Vision
    'cv2',
    'numpy',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    
    # PyTorch
    'torch',
    'torch.nn',
    'torch.utils',
    'torch.utils.data',
    'torchvision',
    'torchvision.transforms',
    'torchvision.models',
    
    # Geospatial libraries
    'geojson',
    'shapely',
    'shapely.geometry',
    'shapely.ops',
    'fastkml',
    'fastkml.kml',
    'geopandas',
    'fiona',
    'pyproj',
    
    # PyQt5
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui', 
    'PyQt5.QtWidgets',
    'PyQt5.QtOpenGL',
    'PyQt5.sip',
    
    # Other utilities
    'tqdm',
    'yaml',
    'matplotlib',
    'seaborn',
    'pandas',
    'scipy',
    'sklearn',
    
    # System libraries
    'pkg_resources',
    'setuptools',
    'wheel',
]

# Collect package data
def collect_pkg_data():
    """Collect package data files"""
    data_files = []
    
    try:
        # Get ultralytics package path
        import ultralytics
        ultralytics_path = ultralytics.__path__[0]
        data_files.append((ultralytics_path, 'ultralytics'))
        print(f"Added ultralytics from: {ultralytics_path}")
    except ImportError:
        print("Warning: ultralytics not found")
    
    try:
        # Get torch data
        import torch
        torch_path = torch.__path__[0]
        data_files.append((torch_path, 'torch'))
        print(f"Added torch from: {torch_path}")
    except ImportError:
        print("Warning: torch not found")
    
    try:
        # Get torchvision data
        import torchvision
        torchvision_path = torchvision.__path__[0]
        data_files.append((torchvision_path, 'torchvision'))
        print(f"Added torchvision from: {torchvision_path}")
    except ImportError:
        print("Warning: torchvision not found")
    
    return data_files

# Add collected package data
added_files.extend(collect_pkg_data())

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib.backends._backend_tk',
        'matplotlib.backends.backend_tkagg',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicates and filter
a.datas = list(set(a.datas))

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
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add 'icon.ico' if you have an icon file
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
