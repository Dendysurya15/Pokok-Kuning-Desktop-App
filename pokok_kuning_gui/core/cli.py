import argparse
import time
import json
import os
import sys

from .processor import ImageProcessor

def display_duration(start_time, end_time):
    """Display the duration in a human-readable format"""
    total_seconds = end_time - start_time
    minutes, seconds = divmod(total_seconds, 60)
    
    if minutes > 0:
        print(f"Total duration: {int(minutes)} minute(s) and {seconds:.2f} second(s)")
    else:
        print(f"Total duration: {seconds:.2f} second(s)")

def progress_callback(progress):
    """Callback function to display progress"""
    print(json.dumps(progress))
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description="Object Detection and Mapping with YOLO")
    parser.add_argument("--folder", required=True, help="Path to the folder containing images")
    parser.add_argument("--weights", required=False, help="Path to the YOLO weights file", default="model/yolov8n-pokok-kuning.pt")
    parser.add_argument("--imgsz", type=int, required=False, help="Image size for YOLO model", default=1280)
    parser.add_argument("--conf", type=float, required=False, help="Confidence threshold", default=0.2)
    parser.add_argument("--iou", type=float, required=False, help="IoU threshold", default=0.2)
    parser.add_argument("--classes", type=int, nargs='+', help="List of class indices to detect")
    parser.add_argument("--kml", action="store_true", help="Convert GeoJSON to KML")
    parser.add_argument("--shp", action="store_true", help="Convert GeoJSON to SHP")
    parser.add_argument("--skip-invalid", action="store_true", help="Skip invalid images instead of stopping")
    parser.add_argument("--save-annotated", action="store_true", help="Save annotated frames with bounding boxes")
    parser.add_argument("--annotated-folder", type=str, help="Folder to save annotated frames (default: 'annotated' subfolder)")

    args = parser.parse_args()

    # Set default annotated folder if not specified
    if args.save_annotated and not args.annotated_folder:
        args.annotated_folder = os.path.join(args.folder, "annotated")

    print(f"Starting processing with image size: {args.imgsz}")
    if args.save_annotated:
        print(f"Annotated frames will be saved to: {args.annotated_folder}")
    
    start_time = time.time()
    
    # Create configuration from arguments
    config = {
        "model": os.path.splitext(os.path.basename(args.weights))[0],
        "imgsz": str(args.imgsz),
        "iou": str(args.iou),
        "conf": str(args.conf),
        "convert_shp": "true" if args.shp else "false",
        "convert_kml": "true" if args.kml else "false",
        "save_annotated": args.save_annotated,
        "annotated_folder": args.annotated_folder,
        "classes": args.classes,
        "skip_invalid": args.skip_invalid
    }
    
    # Process the folder
    processor = ImageProcessor()
    results = processor.process_folder(args.folder, config, progress_callback)
    
    end_time = time.time()
    
    # Final summary
    print(f"\nProcessing complete!")
    print(f"Successfully processed: {results['successful_processed']}/{results['total_files']}")
    print(f"Failed: {results['failed_processed']}/{results['total_files']}")
    if args.save_annotated:
        print(f"Annotated frames saved to: {args.annotated_folder}")
    display_duration(start_time, end_time)
    
    if results['failed_processed'] > 0:
        print(f"\nTips to reduce failures:")
        print(f"- Use --skip-invalid to skip problematic images")
        print(f"- Reduce --imgsz (try 640, 1280) if you have memory issues")
        print(f"- Check that all images have corresponding .tfw files")
        print(f"- Verify all images are valid and not corrupted")

if __name__ == "__main__":
    main()
