#!/usr/bin/env python3
"""
PyInstaller runtime hook untuk PyTorch dan CUDA
"""

import os
import sys

def setup_torch_paths():
    """Setup PyTorch and CUDA paths for PyInstaller executable"""
    try:
        # Get the executable directory
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            base_dir = sys._MEIPASS
            
            # Add torch lib and bin directories to PATH
            torch_paths = [
                os.path.join(base_dir, 'torch', 'lib'),
                os.path.join(base_dir, 'torch', 'bin'),
            ]
            
            for torch_path in torch_paths:
                if os.path.exists(torch_path):
                    # Add to PATH for Windows DLL discovery
                    current_path = os.environ.get('PATH', '')
                    if torch_path not in current_path:
                        os.environ['PATH'] = torch_path + os.pathsep + current_path
                        print(f"PyTorch runtime hook: Added {torch_path} to PATH")
            
            # Set CUDA environment variables
            torch_lib_dir = os.path.join(base_dir, 'torch', 'lib')
            if os.path.exists(torch_lib_dir):
                os.environ['CUDA_PATH'] = torch_lib_dir
                os.environ['CUDA_HOME'] = torch_lib_dir
                
                # Set additional CUDA environment variables
                os.environ['CUDA_CACHE_PATH'] = os.path.join(base_dir, 'cuda_cache')
                os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
                
                # Ensure CUDA is visible
                if 'CUDA_VISIBLE_DEVICES' not in os.environ:
                    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
            
            # Ensure CUDA libraries are discoverable
            cuda_lib_paths = [
                os.path.join(base_dir, 'torch', 'lib'),
                os.path.join(base_dir, 'torch', 'bin'),
                os.path.join(base_dir, 'nvidia'),
                os.path.join(base_dir, 'Library', 'bin'),
                os.path.join(base_dir, 'nvidia', 'cudnn', 'bin'),
                os.path.join(base_dir, 'nvidia', 'cublas', 'bin'),
                os.path.join(base_dir, 'nvidia', 'curand', 'bin'),
                os.path.join(base_dir, 'nvidia', 'cufft', 'bin'),
                os.path.join(base_dir, 'nvidia', 'cusparse', 'bin'),
                os.path.join(base_dir, 'nvidia', 'cusolver', 'bin'),
                os.path.join(base_dir, 'nvidia', 'nvrtc', 'bin'),
            ]
            
            for cuda_path in cuda_lib_paths:
                if os.path.exists(cuda_path):
                    current_path = os.environ.get('PATH', '')
                    if cuda_path not in current_path:
                        os.environ['PATH'] = cuda_path + os.pathsep + current_path
                        print(f"PyTorch runtime hook: Added CUDA path {cuda_path}")
            
            # Try to add system CUDA paths if they exist
            system_cuda_paths = [
                r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin',
                r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0\bin',
                r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin',
                r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.2\bin',
                r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.3\bin',
                r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin',
                r'C:\Program Files\NVIDIA Corporation\NVSMI',
            ]
            
            for cuda_path in system_cuda_paths:
                if os.path.exists(cuda_path):
                    current_path = os.environ.get('PATH', '')
                    if cuda_path not in current_path:
                        os.environ['PATH'] = cuda_path + os.pathsep + current_path
                        print(f"PyTorch runtime hook: Added system CUDA path {cuda_path}")
        
    except Exception as e:
        print(f"PyTorch runtime hook error: {e}")

# Setup paths when this hook is imported
setup_torch_paths()
