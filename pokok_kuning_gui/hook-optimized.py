#!/usr/bin/env python3
"""
Optimized Runtime Hook - Minimal Setup for Stability
"""

import os
import sys
import logging
import datetime

# Create runtime log file
runtime_log_file = os.path.join(os.getcwd(), f"runtime_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(runtime_log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup minimal runtime environment"""
    logger.info("=== ENVIRONMENT SETUP ===")
    
    try:
        if hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
            
            # Add _internal to PATH
            internal_dir = os.path.join(base_dir, '_internal')
            if os.path.exists(internal_dir):
                current_path = os.environ.get('PATH', '')
                if internal_dir not in current_path:
                    os.environ['PATH'] = internal_dir + os.pathsep + current_path
                    logger.info(f"Added to PATH: {internal_dir}")
            
            # CUDA environment - minimal setup
            os.environ['CUDA_PATH'] = base_dir
            os.environ['CUDA_VISIBLE_DEVICES'] = '0'
            os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:256,garbage_collection_threshold:0.6'
            
            # torch.distributed environment - CRITICAL FIX
            os.environ['MASTER_ADDR'] = 'localhost'
            os.environ['MASTER_PORT'] = '12355'
            os.environ['RANK'] = '0' 
            os.environ['WORLD_SIZE'] = '1'
            logger.info("Set torch.distributed environment variables")
            
            # GDAL environment
            gdal_data_dir = os.path.join(base_dir, 'gdal_data')
            if os.path.exists(gdal_data_dir):
                os.environ['GDAL_DATA'] = gdal_data_dir
                logger.info(f"Set GDAL_DATA: {gdal_data_dir}")
            
            proj_data_dir = os.path.join(base_dir, 'proj_data')  
            if os.path.exists(proj_data_dir):
                os.environ['PROJ_LIB'] = proj_data_dir
                logger.info(f"Set PROJ_LIB: {proj_data_dir}")
        
        logger.info("Environment setup completed")
        
    except Exception as e:
        logger.error(f"Environment setup failed: {e}")

def test_critical_imports():
    """Test critical imports with minimal logging"""
    logger.info("=== IMPORT TESTING ===")
    
    import_tests = [
        ('torch', 'PyTorch'),
        ('torch.distributed', 'PyTorch Distributed'),
        ('ultralytics', 'Ultralytics'),
        ('cv2', 'OpenCV'), 
        ('geojson', 'GeoJSON'),
        ('PyQt5.QtCore', 'PyQt5')
    ]
    
    success_count = 0
    for module_name, display_name in import_tests:
        try:
            module = __import__(module_name)
            logger.info(f"{display_name}: OK")
            success_count += 1
                
        except ImportError as e:
            logger.error(f"{display_name} IMPORT FAILED: {e}")
        except Exception as e:
            logger.error(f"{display_name} ERROR: {e}")
    
    logger.info(f"Import test results: {success_count}/{len(import_tests)} successful")
    
    if success_count < len(import_tests):
        logger.error("CRITICAL: Some imports failed - application may crash")
    else:
        logger.info("All critical imports successful")

# Execute setup
try:
    setup_environment()
    test_critical_imports()
    logger.info("=== RUNTIME SETUP COMPLETED ===")
    logger.info(f"Runtime log saved to: {runtime_log_file}")
    
except Exception as e:
    logger.error(f"RUNTIME HOOK FAILED: {e}")
    logger.error("Application may crash - check this log file for details")
