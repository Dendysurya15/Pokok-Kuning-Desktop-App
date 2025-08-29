#!/usr/bin/env python3
"""
Build script untuk membuat executable dari Pokok Kuning Desktop App
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_and_activate_environment():
    """Check if we're in yolov9 environment and provide guidance"""
    
    print("🔍 Environment Check")
    print("=" * 50)
    
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    conda_prefix = os.environ.get('CONDA_PREFIX')
    python_path = sys.executable
    
    print(f"Current Conda Environment: {conda_env}")
    print(f"Python Executable: {python_path}")
    print(f"Conda Prefix: {conda_prefix}")
    
    # Target environment path
    target_env_path = r"C:\Users\jaja.valentino\AppData\Local\anaconda3\envs\yolov9"
    
    # Check if we're in the correct environment
    if conda_env != 'yolov9':
        print(f"\n❌ NOT in 'yolov9' environment!")
        print(f"Current environment: {conda_env}")
        print(f"\n🔧 To fix this, run these commands:")
        print(f"1. conda activate yolov9")
        print(f"2. python build_exe_old.py")
        return False
    
    # Check if the path matches expected location
    if target_env_path.lower() not in python_path.lower():
        print(f"\n⚠️  Warning: Python path might not be from expected environment")
        print(f"Expected path to contain: {target_env_path}")
        print(f"Actual Python path: {python_path}")
        print(f"\nContinuing anyway, but please verify environment is correct...")
    
    # Test key packages
    print(f"\n📦 Testing key packages...")
    try:
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
        print(f"✅ CUDA Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"✅ CUDA Version: {torch.version.cuda}")
    except ImportError as e:
        print(f"❌ PyTorch import failed: {e}")
        return False
    
    try:
        import ultralytics
        print(f"✅ Ultralytics: {ultralytics.__version__}")
    except ImportError as e:
        print(f"❌ Ultralytics import failed: {e}")
        return False
    
    print(f"\n✅ Environment check passed!")
    return True

def get_yolov9_environment_paths():
    """Get paths specifically from yolov9 environment"""
    
    # Primary target path
    target_env_path = r"C:\Users\jaja.valentino\AppData\Local\anaconda3\envs\yolov9"
    
    # Use conda prefix if available, otherwise use target path
    conda_prefix = os.environ.get('CONDA_PREFIX', target_env_path)
    
    # Ensure we're using the right environment
    if 'yolov9' not in conda_prefix:
        print(f"⚠️  Warning: conda_prefix doesn't contain 'yolov9': {conda_prefix}")
        conda_prefix = target_env_path
    
    paths = {
        'conda_prefix': conda_prefix,
        'python_exe': os.path.join(conda_prefix, 'python.exe'),
        'site_packages': os.path.join(conda_prefix, 'Lib', 'site-packages'),
        'library_bin': os.path.join(conda_prefix, 'Library', 'bin'),
        'scripts': os.path.join(conda_prefix, 'Scripts'),
    }
    
    print(f"\n📍 YOLOv9 Environment Paths:")
    for name, path in paths.items():
        exists = "✅" if os.path.exists(path) else "❌"
        print(f"{exists} {name}: {path}")
    
    return paths

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
    
    # Check environment first
    if not check_and_activate_environment():
        print("❌ Environment check failed! Please activate yolov9 environment first.")
        return False
    
    # Get environment paths
    env_paths = get_yolov9_environment_paths()
    
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
    
    # Install PyInstaller if not available (using correct environment)
    print("Checking PyInstaller...")
    try:
        import PyInstaller
        print("PyInstaller is available")
    except ImportError:
        print("Installing PyInstaller in yolov9 environment...")
        python_exe = env_paths['python_exe']
        if not run_command(f'"{python_exe}" -m pip install pyinstaller'):
            print("Failed to install PyInstaller")
            return False
    
    # Create simple CUDA hook
    create_simple_cuda_hook(current_dir, env_paths)
    
    # Create spec file if it doesn't exist
    spec_file = current_dir / "pokok_kuning_old.spec"
    if not spec_file.exists():
        print("Creating PyInstaller spec file...")
        create_spec_file(spec_file, env_paths)
    else:
        print("Updating existing spec file with correct environment paths...")
        create_spec_file(spec_file, env_paths)
    
    # Build the executable using correct Python
    print("Building executable...")
    python_exe = env_paths['python_exe']
    cmd = f'"{python_exe}" -m PyInstaller --clean {spec_file}'
    
    if not run_command(cmd, cwd=current_dir):
        print("Build failed!")
        return False
    
    print("Build completed successfully!")
    print(f"Executable can be found in: {dist_dir}")
    
    return True

def create_spec_file(spec_path, env_paths):
    """Create PyInstaller spec file with correct environment paths"""
    
    conda_prefix = env_paths['conda_prefix']
    site_packages = env_paths['site_packages']
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
import os
from pathlib import Path

# Explicit paths for yolov9 environment
YOLOV9_ENV_PATH = r"{conda_prefix}"
SITE_PACKAGES = r"{site_packages}"

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
        print(f"Added torch from yolov9 env: {{torch_path}}")
    
    # Add torchvision package
    torchvision_path = os.path.join(SITE_PACKAGES, 'torchvision')
    if os.path.exists(torchvision_path):
        data_files.append((torchvision_path, 'torchvision'))
        print(f"Added torchvision from yolov9 env: {{torchvision_path}}")
    
    # Add ultralytics package
    ultralytics_path = os.path.join(SITE_PACKAGES, 'ultralytics')
    if os.path.exists(ultralytics_path):
        data_files.append((ultralytics_path, 'ultralytics'))
        print(f"Added ultralytics from yolov9 env: {{ultralytics_path}}")
    
    return data_files

# Add packages from yolov9 environment
added_files.extend(collect_from_yolov9_env())

# Add basic CUDA DLLs from yolov9 environment if available
cuda_lib_path = os.path.join(YOLOV9_ENV_PATH, 'Library', 'bin')
if os.path.exists(cuda_lib_path):
    print(f"Looking for CUDA files in: {{cuda_lib_path}}")
    essential_cuda_files = [
        'cudart64_12.dll', 'cublas64_12.dll', 'cublasLt64_12.dll'
    ]
    for cuda_file in essential_cuda_files:
        cuda_file_path = os.path.join(cuda_lib_path, cuda_file)
        if os.path.exists(cuda_file_path):
            added_files.append((cuda_file_path, '.'))
            print(f"Added CUDA file: {{cuda_file}}")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
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
'''
    
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"Spec file created/updated: {spec_path}")

def create_simple_cuda_hook(current_dir, env_paths):
    """Create a simple CUDA hook that uses correct environment paths"""
    
    conda_prefix = env_paths['conda_prefix']
    library_bin = env_paths['library_bin']
    
    hook_content = f'''#!/usr/bin/env python3
"""
Simple CUDA hook - environment-specific paths for yolov9
"""

import os
import sys

# Only run in PyInstaller bundle
if hasattr(sys, '_MEIPASS'):
    try:
        # Set paths specific to yolov9 environment
        base_dir = sys._MEIPASS
        yolov9_env_path = r"{conda_prefix}"
        
        # Add CUDA paths to system PATH
        cuda_paths = [
            os.path.join(base_dir, '_internal'),
            os.path.join(base_dir, 'torch', 'lib'),
            base_dir,
        ]
        
        current_path = os.environ.get('PATH', '')
        for cuda_path in cuda_paths:
            if os.path.exists(cuda_path) and cuda_path not in current_path:
                current_path = cuda_path + os.pathsep + current_path
        
        os.environ['PATH'] = current_path
        
        # Set minimal CUDA environment variables for detection only
        os.environ['CUDA_VISIBLE_DEVICES'] = '0'
        os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
        
        print("CUDA Hook: YOLOv9 environment CUDA setup completed")
        print(f"CUDA Hook: Using environment from {{yolov9_env_path}}")
        
    except Exception as e:
        print(f"CUDA Hook: Setup failed, continuing anyway: {{e}}")
        # Continue execution - don't crash if CUDA setup fails
'''
    
    hook_file = current_dir / "hook-cuda-simple.py"
    with open(hook_file, 'w', encoding='utf-8') as f:
        f.write(hook_content)
    
    print(f"Simple CUDA hook created: {hook_file}")

if __name__ == "__main__":
    if build_exe():
        print("\n✅ Build completed successfully!")
        print("\n🎯 STABLE BUILD WITH YOLOV9 ENVIRONMENT")
        print("=" * 50)
        print("✅ Used yolov9 Anaconda environment")
        print("✅ Correct Python and package paths")
        print("✅ Minimal CUDA detection support")
        print("✅ Should be stable AND detect CUDA")
        print("\nTo run the executable:")
        print("1. Go to the 'dist/PokokKuningApp' folder")
        print("2. Run 'PokokKuningApp.exe'")
        print("\n🧪 Testing:")
        print("- Should show GPU detection in Device Specs")
        print("- Should use correct PyTorch/Ultralytics versions")
        print("- Will fallback to CPU if CUDA issues occur")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)