from ultralytics import YOLO
import argparse
import os
from pathlib import Path
import time
import json
import sys

def parse_args():
    parser = argparse.ArgumentParser(description='YOLO detection with custom parameters')
    parser.add_argument('--weights', type=str, required=True, help='Path to YOLO weights file')
    parser.add_argument('--folder', type=str, required=True, help='Path to source folder or URL')
    parser.add_argument('--line-width', type=int, default=2, help='Line width for bounding boxes')
    parser.add_argument('--show-conf', type=bool, default=True, help='Show confidence scores')
    parser.add_argument('--show-labels', type=bool, default=True, help='Show class labels')
    parser.add_argument('--max-det', type=int, default=7000, help='Maximum detections per image')
    parser.add_argument('--imgsz', type=int, default=1920, help='Image size for inference')
    parser.add_argument('--iou', type=float, default=0.2, help='NMS IoU threshold')
    parser.add_argument('--conf', type=float, default=0.2, help='Confidence threshold')
    return parser.parse_args()

def main():
    start_time = time.time()
    args = parse_args()
    
    model = YOLO(args.weights)
    
    valid_extensions = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')
    image_files = [f for f in Path(args.folder).rglob('*') if f.suffix.lower() in valid_extensions]
    total_files = len(image_files)
    processed = 0
    
    for img_path in image_files:
        processed += 1
        results = model(
            str(img_path),
            line_width=args.line_width,
            show_conf=args.show_conf,
            show_labels=args.show_labels,
            max_det=args.max_det,
            imgsz=args.imgsz,
            iou=args.iou,
            conf=args.conf,
            save=True
        )
        
        # Calculate average time per file
        elapsed_time = time.time() - start_time
        avg_time = elapsed_time / processed
        
        # Output progress as JSON
        progress_info = {
            "processed": processed,
            "total": total_files,
            "current_file": str(img_path.name),
            "status": "Saving annotated image",
            "avg_time_per_file": avg_time
        }
        print(json.dumps(progress_info), flush=True)
        sys.stdout.flush()

if __name__ == '__main__':
    main()
