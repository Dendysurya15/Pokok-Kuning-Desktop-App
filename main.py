import geojson
from shapely.geometry import Point, mapping
import os
import argparse
import time
from ultralytics import YOLO
from tqdm import tqdm
from fastkml import kml, geometry
import json
import geopandas as gpd
import sys
import gc  # For garbage collection
from PIL import Image
import numpy as np
import cv2

# Step 1: Image validation and preprocessing
def validate_and_preprocess_image(image_path):
    """Validate image and ensure consistent format"""
    try:
        with Image.open(image_path) as img:
            original_mode = img.mode
            width, height = img.size
            
            print(f"Processing {os.path.basename(image_path)}: {width}x{height}, mode: {original_mode}")
            
            # Handle different image modes
            if img.mode in ['RGBA', 'LA']:
                # Remove alpha channelni 
                img = img.convert('RGB')
                print(f"  Converted from {original_mode} to RGB (removed alpha channel)")
            elif img.mode in ['L', 'P']:
                # Convert grayscale or palette to RGB
                img = img.convert('RGB')
                print(f"  Converted from {original_mode} to RGB")
            elif img.mode == 'CMYK':
                # Convert CMYK to RGB
                img = img.convert('RGB')
                print(f"  Converted from {original_mode} to RGB")
            elif img.mode != 'RGB':
                # Any other mode, convert to RGB
                img = img.convert('RGB')
                print(f"  Converted from {original_mode} to RGB")
            
            # Save the converted image temporarily for YOLO processing
            temp_path = None
            if original_mode != 'RGB':
                base_name = os.path.splitext(image_path)[0]
                temp_path = base_name + "_temp_rgb.jpg"
                img.save(temp_path, 'JPEG', quality=95)
                print(f"  Saved RGB version to: {temp_path}")
            
            return True, width, height, img.mode, temp_path
                
    except Exception as e:
        print(f"Invalid image {image_path}: {e}")
        return False, 0, 0, None, None

# Step 2: Object Detection with YOLO (improved)
def load_yolo_model(weights_path):
    model = YOLO(weights_path)
    return model

def detect_objects(image_path, model, imgsz, conf, iou, classes=None, save_annotated=False, annotated_folder=None):
    """Improved object detection with error handling and optional annotation saving"""
    temp_image_path = None
    try:
        # Validate image first
        is_valid, width, height, mode, temp_path = validate_and_preprocess_image(image_path)
        if not is_valid:
            return None, {"abnormal_count": 0, "normal_count": 0, "error": "Invalid image"}
        
        # Use the temporary RGB image if one was created
        processing_path = temp_path if temp_path else image_path
        temp_image_path = temp_path  # Keep track for cleanup
        
        print(f"  Running YOLO inference on: {processing_path}")
        
        # Use smaller max_det to reduce memory usage
        results = model.predict(
            source=processing_path, 
            imgsz=imgsz, 
            conf=conf, 
            iou=iou, 
            classes=classes, 
            max_det=10000,  # Reduced from 12000
            verbose=False  # Reduce console output
        )
        
        abnormal_count = 0
        normal_count = 0

        for result in results:
            if result.boxes is not None:
                for detection in result.boxes:
                    class_id = int(detection.cls)
                    if class_id == 0:  # Assuming class 0 is abnormal
                        abnormal_count += 1
                    elif class_id == 1:  # Assuming class 1 is normal
                        normal_count += 1
        
        # Save annotated frame if requested
        if save_annotated and annotated_folder and results:
            save_annotated_frame(results[0], image_path, annotated_folder, model.names)
        
        progress = {
            "abnormal_count": abnormal_count,
            "normal_count": normal_count,
            "image_size": f"{width}x{height}",
            "image_mode": mode,
            "converted": temp_path is not None
        }

        return results, progress
        
    except Exception as e:
        error_progress = {
            "abnormal_count": 0,
            "normal_count": 0,
            "error": str(e)
        }
        return None, error_progress
    
    finally:
        # Clean up temporary file
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
                print(f"  Cleaned up temporary file: {temp_image_path}")
            except Exception as e:
                print(f"  Warning: Could not remove temporary file {temp_image_path}: {e}")

def save_annotated_frame(result, original_image_path, annotated_folder, class_names):
    """Save annotated frame with bounding boxes and labels"""
    try:
        # Create annotated folder if it doesn't exist
        os.makedirs(annotated_folder, exist_ok=True)
        
        # Load original image
        image = cv2.imread(original_image_path)
        if image is None:
            print(f"  Warning: Could not load image for annotation: {original_image_path}")
            return
        
        # Define colors for different classes (BGR format for OpenCV)
        colors = {
            0: (0, 0, 255),    # Red for abnormal
            1: (0, 255, 0),    # Green for normal
            2: (255, 0, 0),    # Blue for other classes
            3: (0, 255, 255),  # Cyan
            4: (255, 0, 255),  # Magenta
            5: (255, 255, 0),  # Yellow
        }
        
        # Draw bounding boxes and labels
        if result.boxes is not None:
            for detection in result.boxes:
                # Get coordinates
                x1, y1, x2, y2 = detection.xyxy[0].cpu().numpy().astype(int)
                
                # Get class info
                class_id = int(detection.cls)
                confidence = float(detection.conf)
                class_name = class_names.get(class_id, f"class_{class_id}")
                
                # Choose color
                color = colors.get(class_id, (128, 128, 128))  # Default gray
                
                # Draw bounding box
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                
                # Prepare label text
                label = f"{class_name}: {confidence:.2f}"
                
                # Get text size for background rectangle
                (text_width, text_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                
                # Draw background rectangle for text
                cv2.rectangle(
                    image, 
                    (x1, y1 - text_height - 10), 
                    (x1 + text_width, y1), 
                    color, 
                    -1
                )
                
                # Draw text
                cv2.putText(
                    image, 
                    label, 
                    (x1, y1 - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, 
                    (255, 255, 255), 
                    2
                )
        
        # Save annotated image
        base_name = os.path.splitext(os.path.basename(original_image_path))[0]
        output_path = os.path.join(annotated_folder, f"{base_name}_annotated.jpg")
        
        # Handle duplicate names
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(annotated_folder, f"{base_name}_annotated_{counter}.jpg")
            counter += 1
        
        # Save the image
        success = cv2.imwrite(output_path, image)
        if success:
            print(f"  Saved annotated frame: {output_path}")
        else:
            print(f"  Warning: Failed to save annotated frame: {output_path}")
            
    except Exception as e:
        print(f"  Error saving annotated frame: {e}")

# Step 3: Convert Image Coordinates to Map Coordinates
def read_jgw(jgw_file):
    """Read JGW file with error handling"""
    try:
        with open(jgw_file) as f:
            params = f.readlines()
        return [float(param.strip()) for param in params]
    except FileNotFoundError:
        print(f"Warning: JGW file not found: {jgw_file}")
        return None
    except Exception as e:
        print(f"Error reading JGW file {jgw_file}: {e}")
        return None

def image_to_map_coords(x, y, pixel_size_x, pixel_size_y, upper_left_x, upper_left_y):
    map_x = upper_left_x + x * pixel_size_x
    map_y = upper_left_y + y * pixel_size_y
    return map_x, map_y

# Step 4: Create a GeoJSON
def create_geojson(detected_objects, jgw_params, labels):
    if detected_objects is None or jgw_params is None:
        return geojson.FeatureCollection([])
        
    pixel_size_x, rotation_x, rotation_y, pixel_size_y, upper_left_x, upper_left_y = jgw_params
    features = []
    
    for result in detected_objects:
        if result.boxes is not None:
            for detection in result.boxes:
                try:
                    x1, y1, x2, y2 = detection.xyxy[0].cpu().numpy()
                    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
                    map_x, map_y = image_to_map_coords(center_x, center_y, pixel_size_x, pixel_size_y, upper_left_x, upper_left_y)
                    point = Point(map_x, map_y)
                    
                    class_id = int(detection.cls)
                    label = labels.get(class_id, f"class_{class_id}")
                    
                    feature = geojson.Feature(
                        geometry=mapping(point), 
                        properties={
                            "label": label,
                            "confidence": float(detection.conf.cpu().numpy()),
                            "class_id": class_id
                        }
                    )
                    features.append(feature)
                except Exception as e:
                    print(f"Error processing detection: {e}")
                    continue
                    
    return geojson.FeatureCollection(features)

# Step 5: Save output, handle duplicates
def save_geojson(feature_collection, input_image_path):
    base_name = os.path.splitext(os.path.basename(input_image_path))[0]
    output_path = os.path.join(os.path.dirname(input_image_path), base_name + ".geojson")
    
    counter = 1
    while os.path.exists(output_path):
        output_path = os.path.join(os.path.dirname(input_image_path), f"{base_name}_{counter}.geojson")
        counter += 1
    
    try:
        with open(output_path, "w") as f:
            geojson.dump(feature_collection, f)
        return output_path
    except Exception as e:
        print(f"Error saving GeoJSON: {e}")
        return None

# Step 6: Convert GeoJSON to KML
def convert_geojson_to_kml(geojson_path, kml_path):
    try:
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)

        k = kml.KML()
        ns = '{http://www.opengis.net/kml/2.2}'
        d = kml.Document(ns, 'docid', 'doc name', 'doc description')
        k.append(d)

        for feature in geojson_data['features']:
            coords = feature['geometry']['coordinates']
            properties = feature['properties']
            
            p = kml.Placemark(ns, 'id', properties.get('label', 'Unnamed'), 'description')
            p.geometry = geometry.Point(coords[0], coords[1])
            d.append(p)

        with open(kml_path, 'w') as f:
            f.write(k.to_string(prettyprint=True))
    except Exception as e:
        print(f"Error converting to KML: {e}")

# Step 7: Convert GeoJSON to SHP
def convert_geojson_to_shp(geojson_path, shp_path):
    try:
        gdf = gpd.read_file(geojson_path)
        gdf.to_file(shp_path, driver='ESRI Shapefile')
    except Exception as e:
        print(f"Error converting to SHP: {e}")

# Utility function to display duration
def display_duration(start_time, end_time):
    total_seconds = end_time - start_time
    minutes, seconds = divmod(total_seconds, 60)
    
    if minutes > 0:
        print(f"Total duration: {int(minutes)} minute(s) and {seconds:.2f} second(s)")
    else:
        print(f"Total duration: {seconds:.2f} second(s)")

# Main script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Object Detection and Mapping with YOLO")
    parser.add_argument("--folder", required=True, help="Path to the folder containing images")
    parser.add_argument("--weights", required=False, help="Path to the YOLO weights file", default=".\model\yolov8n-pokok-kuning.pt")
    parser.add_argument("--imgsz", type=int, required=False, help="Image size for YOLO model", default=12800)  # Reduced default
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
    print("Note: If you experience memory errors, try reducing --imgsz to 640 or 1280")
    
    start_time = time.time()
    processing_times = []

    try:
        model = load_yolo_model(args.weights)
        print(f"Model loaded successfully. Available classes: {model.names}")
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

    # Get image files
    image_extensions = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')
    image_files = [f for f in os.listdir(args.folder) if f.lower().endswith(image_extensions)]
    total_files = len(image_files)
    
    print(f"Found {total_files} image files to process")

    successful_processed = 0
    failed_processed = 0

    for index, image_file in enumerate(tqdm(image_files, desc="Processing images")):
        file_start_time = time.time()
        image_path = os.path.join(args.folder, image_file)
        
        try:
            # Detect objects
            detected_objects, counts = detect_objects(
                image_path, model, args.imgsz, args.conf, args.iou, 
                classes=args.classes, save_annotated=args.save_annotated, 
                annotated_folder=args.annotated_folder
            )
            
            if detected_objects is None:
                if args.skip_invalid:
                    failed_processed += 1
                    continue
                else:
                    print(f"Failed to process {image_file}: {counts.get('error', 'Unknown error')}")
                    continue

            # Load JGW file
            base_name = os.path.splitext(image_path)[0]
            jgw_file = base_name + ".tfw"
            jgw_params = read_jgw(jgw_file)
            
            if jgw_params is None:
                print(f"Warning: No valid JGW file for {image_file}, skipping...")
                failed_processed += 1
                continue
            
            # Create and save GeoJSON
            labels = model.names
            feature_collection = create_geojson(detected_objects, jgw_params, labels)
            geojson_output_path = save_geojson(feature_collection, image_path)
            
            if geojson_output_path is None:
                failed_processed += 1
                continue
            
            # Convert to other formats if requested
            if args.kml:
                kml_output_path = geojson_output_path.replace('.geojson', '.kml')
                convert_geojson_to_kml(geojson_output_path, kml_output_path)

            if args.shp:
                shp_output_path = geojson_output_path.replace('.geojson', '.shp')
                convert_geojson_to_shp(geojson_output_path, shp_output_path)
            
            successful_processed += 1
            
            # Calculate timing
            file_end_time = time.time()
            file_duration = file_end_time - file_start_time
            processing_times.append(file_duration)
            avg_time = sum(processing_times) / len(processing_times)
            
            # Progress reporting
            progress = {
                "processed": index + 1,
                "total": total_files,
                "successful": successful_processed,
                "failed": failed_processed,
                "current_file": image_file,
                "status": "Processed successfully",
                "file_duration": f"{file_duration:.2f}s",
                "avg_time_per_file": f"{avg_time:.2f}s",
                "abnormal_count": counts.get("abnormal_count", 0),
                "normal_count": counts.get("normal_count", 0),
                "image_info": counts.get("image_size", "unknown"),
                "annotated_saved": args.save_annotated
            }
            
            print(json.dumps(progress))
            sys.stdout.flush()
            
            # Memory cleanup every 10 files
            if (index + 1) % 10 == 0:
                gc.collect()
                
        except Exception as e:
            print(f"Unexpected error processing {image_file}: {e}")
            failed_processed += 1
            
            if not args.skip_invalid:
                print("Use --skip-invalid flag to continue processing other files")
                break

    end_time = time.time()
    
    # Final summary
    print(f"\nProcessing complete!")
    print(f"Successfully processed: {successful_processed}/{total_files}")
    print(f"Failed: {failed_processed}/{total_files}")
    if args.save_annotated:
        print(f"Annotated frames saved to: {args.annotated_folder}")
    display_duration(start_time, end_time)
    
    if failed_processed > 0:
        print(f"\nTips to reduce failures:")
        print(f"- Use --skip-invalid to skip problematic images")
        print(f"- Reduce --imgsz (try 640, 1280) if you have memory issues")
        print(f"- Check that all images have corresponding .tfw files")
        print(f"- Verify all images are valid and not corrupted")