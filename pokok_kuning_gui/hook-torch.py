#!/usr/bin/env python3
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
        
        # Set comprehensive CUDA environment variables for executable stability
        cuda_env_vars = {
            'CUDA_PATH': base_dir,
            'CUDA_HOME': base_dir,
            'CUDA_ROOT': base_dir,
            'CUDA_CACHE_DISABLE': '1',
            'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:256,garbage_collection_threshold:0.7',
            'CUDA_LAUNCH_BLOCKING': '1',  # Better error reporting
            'CUDA_VISIBLE_DEVICES': '0',  # Ensure GPU 0 is visible
            'PYTORCH_DISABLE_CUDA_MEMORY_POOL': '0',  # Use memory pool
            'CUDA_MODULE_LOADING': 'LAZY',  # Lazy loading for stability
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
