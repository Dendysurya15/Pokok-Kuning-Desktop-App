# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# Base files to include
added_files = [
    ('model', 'model'),
    ('ui', 'ui'),
    ('core', 'core'),
    ('utils', 'utils'),
    ('assets', 'assets'),
]

# Add README if exists
if os.path.exists('README.md'):
    added_files.append(('README.md', '.'))

# Complete hidden imports
hiddenimports = [
    # Local modules
    'ui', 'ui.main_window', 'core', 'core.processor', 'core.cli',
    'utils', 'utils.config_manager',
    
    # Ultralytics complete
    'ultralytics', 'ultralytics.models', 'ultralytics.models.yolo',
    'ultralytics.models.yolo.detect', 'ultralytics.models.yolo.detect.predict',
    'ultralytics.utils', 'ultralytics.utils.plotting', 'ultralytics.utils.ops',
    'ultralytics.engine', 'ultralytics.engine.predictor', 'ultralytics.engine.results',
    'ultralytics.data', 'ultralytics.data.utils', 'ultralytics.nn', 'ultralytics.nn.modules',
    'ultralytics.trackers',
    
    # Computer Vision
    'cv2', 'numpy', 'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw', 'PIL.ImageFont',
    
    # PyTorch complete with CUDA
    'torch', 'torch.nn', 'torch.utils', 'torch.utils.data', 'torch.optim',
    'torch.cuda', 'torch.cuda.comm', 'torch.cuda.nccl', 'torch.cuda.nvtx',
    'torch.cuda.sparse', 'torch.cuda._utils', 'torch.cuda.streams',
    'torch.cuda.memory', 'torch.cuda.profiler', 'torch.cuda.amp',
    'torch._C', 'torch._C._cuda_init', 'torch._C._cuda_setDevice',
    'torch._C._cuda_getDeviceCount', 'torch.version', 'torch.jit',
    'torch.backends', 'torch.backends.cuda', 'torch.backends.cudnn',
    'torchvision', 'torchvision.transforms', 'torchvision.models',
    
    # Geospatial
    'geojson', 'shapely', 'shapely.geometry', 'shapely.ops',
    'fastkml', 'fastkml.kml', 'geopandas', 'fiona', 'pyproj',
    
    # PyQt5 complete
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
    'PyQt5.QtOpenGL', 'PyQt5.QtSvg', 'PyQt5.sip',
    
    # Other essentials
    'tqdm', 'yaml', 'matplotlib', 'seaborn', 'pandas', 'scipy', 'sklearn',
    'pkg_resources', 'setuptools', 'wheel', 'psutil', 'logging',
]

def get_conda_prefix():
    """Get conda environment prefix"""
    conda_prefix = os.environ.get('CONDA_PREFIX')
    if conda_prefix and os.path.exists(conda_prefix):
        return conda_prefix
    
    # Fallback detection
    python_path = sys.executable
    if 'envs' in python_path and 'yolov9' in python_path:
        parts = python_path.split(os.sep)
        try:
            envs_idx = parts.index('envs')
            if envs_idx + 1 < len(parts):
                env_name = parts[envs_idx + 1]
                conda_root = os.sep.join(parts[:envs_idx])
                return os.path.join(conda_root, 'envs', env_name)
        except ValueError:
            pass
    return None

def collect_all_packages():
    """Collect all package data"""
    data_files = []
    
    # PyTorch package
    try:
        import torch
        torch_path = torch.__path__[0]
        data_files.append((torch_path, 'torch'))
        print(f"Added torch package: {torch_path}")
    except ImportError:
        print("Warning: torch not found")
    
    # Torchvision package
    try:
        import torchvision
        torchvision_path = torchvision.__path__[0]
        data_files.append((torchvision_path, 'torchvision'))
        print(f"Added torchvision package: {torchvision_path}")
    except ImportError:
        print("Warning: torchvision not found")
    
    # Ultralytics package
    try:
        import ultralytics
        ultralytics_path = ultralytics.__path__[0]
        data_files.append((ultralytics_path, 'ultralytics'))
        print(f"Added ultralytics package: {ultralytics_path}")
    except ImportError:
        print("Warning: ultralytics not found")
    
    return data_files

def collect_all_cuda_files():
    """Collect ALL CUDA files from environment"""
    cuda_files = []
    conda_prefix = get_conda_prefix()
    
    if not conda_prefix:
        print("Warning: Cannot find conda environment")
        return cuda_files
    
    print(f"Collecting CUDA files from: {conda_prefix}")
    
    # 1. Conda Library/bin - system CUDA
    conda_lib_bin = Path(conda_prefix) / "Library" / "bin"
    if conda_lib_bin.exists():
        print(f"Scanning: {conda_lib_bin}")
        cuda_patterns = [
            "*cuda*", "*cublas*", "*cufft*", "*curand*", "*cusolver*", 
            "*cusparse*", "*cudnn*", "*nvrtc*", "*nvtx*", "*nvcuda*"
        ]
        
        for pattern in cuda_patterns:
            for file_path in conda_lib_bin.glob(f"{pattern}.dll"):
                # Copy to multiple strategic locations
                cuda_files.extend([
                    (str(file_path), 'Library_bin'),           # Original location
                    (str(file_path), '.'),                     # Root dist
                    (str(file_path), '_internal'),             # Internal root
                ])
                print(f"Found CUDA: {file_path.name}")
    
    # 2. PyTorch lib directory - PyTorch CUDA
    try:
        import torch
        torch_lib = Path(torch.__path__[0]) / "lib"
        if torch_lib.exists():
            print(f"Scanning: {torch_lib}")
            for file_path in torch_lib.glob("*.dll"):
                # Copy to multiple strategic locations
                cuda_files.extend([
                    (str(file_path), 'torch/lib'),
                    (str(file_path), '_internal/torch/lib'),
                    (str(file_path), '_internal'),
                ])
            print(f"Added {len(list(torch_lib.glob('*.dll')))} PyTorch DLLs")
    except ImportError:
        print("Warning: Cannot access torch lib directory")
    
    return cuda_files

# Collect everything
print("=== PyInstaller Spec File Generation ===")
package_data = collect_all_packages()
cuda_data = collect_all_cuda_files()

added_files.extend(package_data)
added_files.extend(cuda_data)

print(f"Total files collected: {len(added_files)}")

# Runtime hooks
runtime_hooks = []
if os.path.exists('hook-torch.py'):
    runtime_hooks.append('hook-torch.py')
    print("Using runtime hook: hook-torch.py")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[
        'tkinter', 'matplotlib.backends._backend_tk', 'matplotlib.backends.backend_tkagg',
        'IPython', 'jupyter', 'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicates but keep strategic copies
unique_datas = {}
for data_tuple in a.datas:
    # Handle both (src, dst) and (src, dst, type) formats
    if len(data_tuple) >= 2:
        src, dst = data_tuple[0], data_tuple[1]
        key = (os.path.basename(src), dst)
        if key not in unique_datas:
            unique_datas[key] = data_tuple

a.datas = list(unique_datas.values())

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
    console=True,  # REQUIRED for CUDA stability
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/img/logo.ico' if os.path.exists('assets/img/logo.ico') else None,
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
