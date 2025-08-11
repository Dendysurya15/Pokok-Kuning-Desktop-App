#!/usr/bin/env python3
"""
Script to setup database with correct configuration values
"""

from utils.config_manager import setup_database, save_config

if __name__ == "__main__":
    print("Setting up database...")
    setup_database()
    
    # Force save the correct configuration
    config = {
        "model": "yolov8n-pokok-kuning",
        "imgsz": "12800",        # Changed from 1280 to 12800 to match CLI version
        "iou": "0.2",
        "conf": "0.2",
        "convert_shp": "true",
        "convert_kml": "false",
        "max_det": "10000",      # Changed from 12000 to 10000 to match CLI version
        "line_width": "3",
        "show_labels": "false",
        "show_conf": "false",
        "status_blok": "Full Blok"
    }
    
    print("Saving configuration...")
    save_config(config)
    print("Database setup complete with CLI-compatible values!")
    print(f"Image Size: {config['imgsz']}")
    print(f"Max Detection: {config['max_det']}")
