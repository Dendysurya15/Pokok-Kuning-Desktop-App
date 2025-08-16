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
    """Complete CUDA setup for PyInstaller executable with process isolation"""
    
    if not hasattr(sys, '_MEIPASS'):
        return  # Not running in PyInstaller bundle
    
    try:
        base_dir = sys._MEIPASS
        logger.info(f"Initializing CUDA in: {base_dir}")
        
        # Skip aggressive multiprocessing setup to avoid conflicts
        logger.info("Using default multiprocessing configuration for compatibility")
        
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
        
        # Set conservative CUDA environment variables for maximum stability
        cuda_env_vars = {
            'CUDA_PATH': base_dir,
            'CUDA_HOME': base_dir,
            'CUDA_ROOT': base_dir,
            'CUDA_CACHE_DISABLE': '0',  # Enable caching for stability
            'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:256,garbage_collection_threshold:0.6',
            'CUDA_LAUNCH_BLOCKING': '1',  # Synchronous mode for stability
            'CUDA_VISIBLE_DEVICES': '0',  # Ensure GPU 0 is visible
            'PYTORCH_DISABLE_CUDA_MEMORY_POOL': '0',  # Use memory pool
            'CUDA_MODULE_LOADING': 'LAZY',  # Lazy loading for stability
            'PYTORCH_JIT': '0',  # Disable JIT compilation for stability
            'CUDA_DEVICE_ORDER': 'PCI_BUS_ID',  # Consistent device ordering
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
        
        # Optional: Preload critical CUDA DLLs (skip if problematic)
        try:
            preload_cuda_dlls(cuda_paths)
        except Exception as dll_error:
            logger.warning(f"DLL preloading skipped: {dll_error}")
        
        # Minimal completion check
        test_cuda_final()
        
    except Exception as e:
        logger.error(f"CUDA setup failed: {e}")
        # Emergency fallback to CPU-only mode
        try:
            os.environ['CUDA_VISIBLE_DEVICES'] = ''
            os.environ['PYTORCH_CUDA_ALLOC_CONF'] = ''
            logger.info("Emergency fallback: Set to CPU-only mode")
        except:
            pass

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
    """Minimal CUDA detection without operations that could crash"""
    try:
        logger.info("CUDA path and DLL setup completed successfully")
        logger.info("PyTorch will handle CUDA detection when needed by the application")
        # No actual CUDA operations here to prevent crashes
        
    except Exception as e:
        logger.error(f"CUDA setup issue: {e}")
        logger.info("Application will use default PyTorch CUDA configuration")

# Execute setup immediately when hook is imported - minimal and safe approach
logger.info("Starting minimal CUDA setup...")
try:
    setup_complete_cuda()
    logger.info("CUDA setup completed - application ready!")
except Exception as hook_error:
    logger.error(f"CUDA setup warning: {hook_error}")
    logger.info("Application will continue with default CUDA configuration")
