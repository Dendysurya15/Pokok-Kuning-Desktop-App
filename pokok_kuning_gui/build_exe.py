#!/usr/bin/env python3
"""
Complete build script untuk Pokok Kuning Desktop App dengan CUDA support
All-in-one solution - tinggal jalankan!
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_environment():
    """Check if we're in the correct environment"""
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    conda_prefix = os.environ.get('CONDA_PREFIX')
    
    print("🔍 Environment Check")
    print("=" * 40)
    print(f"Conda Environment: {conda_env}")
    print(f"Python: {sys.executable}")
    
    if conda_env != 'yolov9':
        print("❌ Not in 'yolov9' environment!")
        print("Please run: conda activate yolov9")
        return False
    
    # Test PyTorch and CUDA
    try:
        import torch
        print(f"PyTorch: {torch.__version__}")
        print(f"CUDA Available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA Version: {torch.version.cuda}")
            print(f"GPU: {torch.cuda.get_device_name(0)}")
        
        return True
    except ImportError:
        print("❌ PyTorch not installed!")
        return False

def create_complete_spec_file():
    """Create complete spec file with all CUDA handling"""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

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
for src, dst in a.datas:
    key = (os.path.basename(src), dst)
    if key not in unique_datas:
        unique_datas[key] = (src, dst)

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
    console=True,  # Keep True for CUDA debugging
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
'''
    
    spec_file = Path("pokok_kuning_new.spec")
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✅ Created complete spec file: {spec_file}")
    return spec_file

def create_improved_hook():
    """Create improved torch hook"""
    
    hook_content = '''#!/usr/bin/env python3
"""
Complete PyTorch CUDA runtime hook - handles all CUDA initialization
"""

import os
import sys
import ctypes
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='PyTorch Hook: %(message)s')
logger = logging.getLogger(__name__)

def setup_complete_cuda():
    """Complete CUDA setup for PyInstaller executable"""
    
    if not hasattr(sys, '_MEIPASS'):
        return  # Not running in PyInstaller bundle
    
    try:
        base_dir = sys._MEIPASS
        logger.info(f"Initializing CUDA in: {base_dir}")
        
        # All possible CUDA locations in our bundle
        cuda_paths = [
            os.path.join(base_dir, '_internal'),
            os.path.join(base_dir, '_internal', 'torch', 'lib'),
            os.path.join(base_dir, 'Library_bin'),
            os.path.join(base_dir, 'torch', 'lib'),
            base_dir,
        ]
        
        # Add all paths to system PATH
        current_path = os.environ.get('PATH', '')
        new_paths = []
        
        for cuda_path in cuda_paths:
            if os.path.exists(cuda_path) and cuda_path not in current_path:
                new_paths.append(cuda_path)
                logger.info(f"Added CUDA path: {cuda_path}")
        
        if new_paths:
            os.environ['PATH'] = os.pathsep.join(new_paths) + os.pathsep + current_path
        
        # Set comprehensive CUDA environment variables
        cuda_env_vars = {
            'CUDA_PATH': base_dir,
            'CUDA_HOME': base_dir,
            'CUDA_ROOT': base_dir,
            'CUDA_CACHE_DISABLE': '1',
            'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:512',
        }
        
        for var, value in cuda_env_vars.items():
            os.environ[var] = value
            logger.info(f"Set {var} = {value}")
        
        # Add DLL directories (Windows 10+)
        if hasattr(os, 'add_dll_directory'):
            for cuda_path in cuda_paths:
                if os.path.exists(cuda_path):
                    try:
                        os.add_dll_directory(cuda_path)
                        logger.info(f"Added DLL directory: {cuda_path}")
                    except:
                        pass
        
        # Preload critical CUDA DLLs
        preload_cuda_dlls(cuda_paths)
        
        # Test CUDA after setup
        test_cuda_final()
        
    except Exception as e:
        logger.error(f"CUDA setup failed: {e}")

def preload_cuda_dlls(search_paths):
    """Preload CUDA DLLs in correct order"""
    
    # Critical DLLs in dependency order
    critical_dlls = [
        'cudart64_12.dll',      # CUDA runtime (load first)
        'cublas64_12.dll',      # cuBLAS
        'cublasLt64_12.dll',    # cuBLAS Lt
        'c10_cuda.dll',         # PyTorch CUDA (load after CUDA runtime)
        'caffe2_nvrtc.dll',     # PyTorch NVRTC
    ]
    
    loaded_count = 0
    
    for dll_name in critical_dlls:
        for search_path in search_paths:
            dll_path = os.path.join(search_path, dll_name)
            if os.path.exists(dll_path):
                try:
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.LoadLibraryW(dll_path)
                    if handle:
                        logger.info(f"Preloaded: {dll_name}")
                        loaded_count += 1
                        break  # Stop searching once loaded
                except Exception as e:
                    logger.warning(f"Failed to preload {dll_name}: {e}")
    
    logger.info(f"Successfully preloaded {loaded_count} critical CUDA DLLs")

def test_cuda_final():
    """Final CUDA test"""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        logger.info(f"Final CUDA test - Available: {cuda_available}")
        
        if cuda_available:
            device_count = torch.cuda.device_count()
            logger.info(f"CUDA devices detected: {device_count}")
            
            if device_count > 0:
                device_name = torch.cuda.get_device_name(0)
                logger.info(f"Primary GPU: {device_name}")
        
    except Exception as e:
        logger.error(f"Final CUDA test failed: {e}")

# Execute setup immediately when hook is imported
logger.info("Starting complete CUDA setup...")
setup_complete_cuda()
logger.info("CUDA setup completed!")
'''
    
    hook_file = Path("hook-torch.py")
    with open(hook_file, 'w', encoding='utf-8') as f:
        f.write(hook_content)
    
    print(f"✅ Created improved hook: {hook_file}")

def clean_and_install():
    """Clean previous builds and install dependencies"""
    
    print("\n🧹 Cleaning previous builds...")
    
    # Clean directories
    for dir_name in ["dist", "build", "__pycache__"]:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Removed: {dir_name}/")
    
    # Install dependencies
    print("\n📦 Installing build dependencies...")
    
    dependencies = ["pyinstaller>=6.0.0", "pyinstaller-hooks-contrib"]
    
    for dep in dependencies:
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print(f"✅ {dep}")
            else:
                print(f"⚠️  {dep} - already installed or failed")
        except:
            print(f"⚠️  {dep} - timeout or error")

def build_executable():
    """Build the executable"""
    
    print("\n🔨 Building executable...")
    print("=" * 50)
    
    spec_file = "pokok_kuning_new.spec"
    
    # Run PyInstaller
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", spec_file]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        print("✅ Build completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def post_build_fixes():
    """Post-build CUDA fixes"""
    
    print("\n🔧 Applying post-build CUDA fixes...")
    
    dist_dir = Path("dist/PokokKuningApp")
    internal_dir = dist_dir / "_internal"
    
    if not internal_dir.exists():
        print("❌ _internal directory not found!")
        return False
    
    # Ensure critical CUDA files are in _internal root
    critical_files = ["cudart64_12.dll", "c10_cuda.dll", "cublas64_12.dll"]
    
    copied = 0
    for critical_file in critical_files:
        # Find file anywhere in dist
        found_file = None
        for file_path in dist_dir.rglob(critical_file):
            found_file = file_path
            break
        
        if found_file:
            target = internal_dir / critical_file
            try:
                shutil.copy2(found_file, target)
                print(f"✅ Ensured {critical_file} in _internal/")
                copied += 1
            except:
                pass
    
    print(f"✅ Post-build fixes applied ({copied} files ensured)")
    return True

def verify_build():
    """Verify build output"""
    
    print("\n🔍 Verifying build...")
    
    exe_file = Path("dist/PokokKuningApp/PokokKuningApp.exe")
    
    if not exe_file.exists():
        print("❌ Executable not found!")
        return False
    
    # Get size info
    try:
        size_mb = exe_file.stat().st_size / (1024 * 1024)
        print(f"✅ Executable created: {size_mb:.1f} MB")
    except:
        print("✅ Executable created")
    
    # Count CUDA files in _internal
    internal_dir = Path("dist/PokokKuningApp/_internal")
    if internal_dir.exists():
        cuda_count = len(list(internal_dir.glob("*cuda*.dll")))
        total_count = len(list(internal_dir.glob("*.dll")))
        print(f"✅ DLLs in _internal: {total_count} total, {cuda_count} CUDA")
    
    return True

def main():
    """Main build process"""
    
    print("🚀 Complete Pokok Kuning Build Process")
    print("=" * 60)
    
    # 1. Check environment
    if not check_environment():
        print("\n❌ Environment check failed!")
        return False
    
    # 2. Create files
    print("\n📝 Creating build files...")
    create_complete_spec_file()
    create_improved_hook()
    
    # 3. Clean and install
    clean_and_install()
    
    # 4. Build
    if not build_executable():
        print("\n❌ Build failed!")
        return False
    
    # 5. Post-build fixes
    post_build_fixes()
    
    # 6. Verify
    if not verify_build():
        print("\n❌ Verification failed!")
        return False
    
    # 7. Success!
    print("\n" + "=" * 60)
    print("🎉 BUILD COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nYour executable is ready:")
    print("📁 Location: dist/PokokKuningApp/PokokKuningApp.exe")
    print("\n🧪 Test CUDA functionality:")
    print("1. Double-click the executable")
    print("2. Check Device Specs for GPU detection")
    print("3. Set Device to 'cuda' for processing")
    print("\n🚀 CUDA should now work perfectly!")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)