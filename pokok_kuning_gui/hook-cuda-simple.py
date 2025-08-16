#!/usr/bin/env python3
"""
Simple CUDA hook - only environment variables, no aggressive testing
"""

import os
import sys

# Only run in PyInstaller bundle
if hasattr(sys, '_MEIPASS'):
    try:
        # Set basic CUDA environment variables for detection
        base_dir = sys._MEIPASS
        
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
        
        print("CUDA Hook: Basic CUDA environment setup completed")
        
    except Exception as e:
        print(f"CUDA Hook: Setup failed, continuing anyway: {e}")
        # Continue execution - don't crash if CUDA setup fails
