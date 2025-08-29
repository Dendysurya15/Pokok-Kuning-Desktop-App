#!/usr/bin/env python3
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
        yolov9_env_path = r"C:\Users\jaja.valentino\AppData\Local\anaconda3\envs\yolov9"
        
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
        print(f"CUDA Hook: Using environment from {yolov9_env_path}")
        
    except Exception as e:
        print(f"CUDA Hook: Setup failed, continuing anyway: {e}")
        # Continue execution - don't crash if CUDA setup fails
