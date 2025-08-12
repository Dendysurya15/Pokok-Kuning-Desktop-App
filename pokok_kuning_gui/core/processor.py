import os
import sys
import time
import json
import gc
from pathlib import Path
from PIL import Image
import numpy as np
import cv2
import geojson
from shapely.geometry import Point, mapping
import geopandas as gpd
from fastkml import kml, geometry

class ImageProcessor:
    def __init__(self):
        self.model = None
        self.config = None
    
    def process_folder(self, folder_path, config, progress_callback=None):
        """Process all images in the folder based on configuration"""
        start_time = time.time()
        
        # Store config
        self.config = config
        
        # Load model - Handle both development and executable environments
        # Try multiple possible model paths
        possible_paths = []
        
        # Method 1: From current script location (development)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dev_model_path = os.path.join(os.path.dirname(os.path.dirname(script_dir)), "model", f"{config['model']}.pt")
        possible_paths.append(dev_model_path)
        
        # Method 2: From executable directory (PyInstaller)
        if hasattr(sys, '_MEIPASS'):
            # Running in PyInstaller bundle
            exe_model_path = os.path.join(sys._MEIPASS, "model", f"{config['model']}.pt")
            possible_paths.append(exe_model_path)
        
        # Method 3: Relative to executable location
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        exe_relative_path = os.path.join(exe_dir, "model", f"{config['model']}.pt")
        possible_paths.append(exe_relative_path)
        
        # Method 4: In same directory as executable
        same_dir_path = os.path.join(exe_dir, f"{config['model']}.pt")
        possible_paths.append(same_dir_path)
        
        model_path = None
        for path in possible_paths:
            print(f"  Checking model path: {path}")
            sys.stdout.flush()
            if os.path.exists(path):
                model_path = path
                print(f"  ✓ Found model at: {model_path}")
                sys.stdout.flush()
                break
        
        if model_path is None:
            error_msg = f"Model {config['model']}.pt not found. Searched paths:\n"
            for path in possible_paths:
                error_msg += f"  - {path}\n"
            print(error_msg)
            return {
                "error": error_msg,
                "successful_processed": 0,
                "failed_processed": 0,
                "total_files": 0
            }
        
        try:
            print(f"  Loading YOLO model from: {model_path}")
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            print(f"  ✓ Model loaded successfully")
        except Exception as e:
            error_msg = f"Failed to load model: {str(e)}"
            print(f"  ✗ {error_msg}")
            return {
                "error": error_msg,
                "successful_processed": 0,
                "failed_processed": 0,
                "total_files": 0
            }
        
        # Get image files
        print(f"  Scanning folder: {folder_path}")
        image_extensions = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')
        image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(image_extensions)]
        total_files = len(image_files)
        print(f"  Found {total_files} image files to process")
        
        successful_processed = 0
        failed_processed = 0
        processing_times = []
        total_abnormal = 0
        total_normal = 0
        
        for index, image_file in enumerate(image_files):
            file_start_time = time.time()
            image_path = os.path.join(folder_path, image_file)
            print(f"  Processing [{index+1}/{total_files}]: {image_file}")
            sys.stdout.flush()
            
            try:
                # Detect objects
                detected_objects, counts = self.detect_objects(
                    image_path, 
                    int(config.get("imgsz", 12800)),  # Changed default from 1280 to 12800
                    float(config.get("conf", 0.2)), 
                    float(config.get("iou", 0.2)),
                    save_annotated=config.get("save_annotated") == "true",
                    annotated_folder=os.path.join(folder_path, "annotated") if config.get("save_annotated") == "true" else None
                )
                
                if detected_objects is None:
                    failed_processed += 1
                    continue
                
                # Load JGW file
                base_name = os.path.splitext(image_path)[0]
                jgw_file = base_name + ".tfw"
                jgw_params = self.read_jgw(jgw_file)
                
                if jgw_params is None:
                    failed_processed += 1
                    continue
                
                # Create and save GeoJSON
                labels = self.model.names
                feature_collection = self.create_geojson(detected_objects, jgw_params, labels)
                geojson_output_path = self.save_geojson(feature_collection, image_path)
                
                if geojson_output_path is None:
                    failed_processed += 1
                    continue
                
                # Convert to other formats if requested
                if config.get("convert_kml") == "true":
                    kml_output_path = geojson_output_path.replace('.geojson', '.kml')
                    self.convert_geojson_to_kml(geojson_output_path, kml_output_path)
                
                if config.get("convert_shp") == "true":
                    shp_output_path = geojson_output_path.replace('.geojson', '.shp')
                    self.convert_geojson_to_shp(geojson_output_path, shp_output_path)
                
                successful_processed += 1
                
                # Calculate timing
                file_end_time = time.time()
                file_duration = file_end_time - file_start_time
                processing_times.append(file_duration)
                avg_time = sum(processing_times) / len(processing_times)
                
                # Update abnormal and normal counts
                abnormal_count = counts.get("abnormal_count", 0)
                normal_count = counts.get("normal_count", 0)
                total_abnormal += abnormal_count
                total_normal += normal_count
                
                # Progress reporting
                if progress_callback:
                    progress = {
                        "processed": index + 1,
                        "total": total_files,
                        "successful": successful_processed,
                        "failed": failed_processed,
                        "current_file": image_file,
                        "status": "Processed successfully",
                        "file_duration": f"{file_duration:.2f}s",
                        "avg_time_per_file": f"{avg_time:.2f}s",
                        "abnormal_count": abnormal_count,
                        "normal_count": normal_count,
                        "image_info": counts.get("image_size", "unknown")
                    }
                    progress_callback(progress)
                
                # Aggressive memory cleanup for executable
                if (index + 1) % 5 == 0:  # More frequent cleanup
                    print(f"    Memory cleanup after {index + 1} files...")
                    sys.stdout.flush()
                    gc.collect()
                    
            except Exception as e:
                print(f"    ❌ Error processing {image_file}: {str(e)}")
                sys.stdout.flush()
                failed_processed += 1
                if progress_callback:
                    progress_callback({
                        "processed": index + 1,
                        "total": total_files,
                        "successful": successful_processed,
                        "failed": failed_processed,
                        "current_file": image_file,
                        "status": f"Error: {str(e)}",
                        "abnormal_count": 0,
                        "normal_count": 0
                    })
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n  Processing complete!")
        print(f"  Successfully processed: {successful_processed}/{total_files}")
        print(f"  Failed: {failed_processed}/{total_files}")
        print(f"  Total abnormal objects: {total_abnormal}")
        print(f"  Total normal objects: {total_normal}")
        print(f"  Total time: {total_time:.2f} seconds")
        
        return {
            "successful_processed": successful_processed,
            "failed_processed": failed_processed,
            "total_files": total_files,
            "total_time": total_time,
            "total_abnormal": total_abnormal,
            "total_normal": total_normal
        }
    
    def validate_and_preprocess_image(self, image_path):
        """Validate image and ensure consistent format"""
        try:
            with Image.open(image_path) as img:
                original_mode = img.mode
                width, height = img.size
                
                # Handle different image modes
                if img.mode in ['RGBA', 'LA']:
                    # Remove alpha channel
                    img = img.convert('RGB')
                elif img.mode in ['L', 'P']:
                    # Convert grayscale or palette to RGB
                    img = img.convert('RGB')
                elif img.mode == 'CMYK':
                    # Convert CMYK to RGB
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
                    # Any other mode, convert to RGB
                    img = img.convert('RGB')
                
                # Save the converted image temporarily for YOLO processing
                temp_path = None
                if original_mode != 'RGB':
                    base_name = os.path.splitext(image_path)[0]
                    temp_path = base_name + "_temp_rgb.jpg"
                    img.save(temp_path, 'JPEG', quality=95)
                
                return True, width, height, img.mode, temp_path
                    
        except Exception as e:
            return False, 0, 0, None, None
    
    def detect_objects(self, image_path, imgsz, conf, iou, classes=None, save_annotated=False, annotated_folder=None):
        """Object detection with error handling and optional annotation saving"""
        temp_image_path = None
        try:
            print(f"    Starting detection for: {os.path.basename(image_path)}")
            sys.stdout.flush()
            # Validate image first
            is_valid, width, height, mode, temp_path = self.validate_and_preprocess_image(image_path)
            if not is_valid:
                return None, {"abnormal_count": 0, "normal_count": 0, "error": "Invalid image"}
            
            # Use the temporary RGB image if one was created
            processing_path = temp_path if temp_path else image_path
            temp_image_path = temp_path  # Keep track for cleanup
            
            # Use smaller max_det to reduce memory usage
            # Get max_det from config if available
            max_det = 10000  # Default value
            if hasattr(self, 'config') and self.config and 'max_det' in self.config:
                try:
                    max_det = int(self.config['max_det'])
                except (ValueError, TypeError):
                    pass
                
            print(f"    Running YOLO prediction (imgsz={imgsz}, conf={conf}, iou={iou})...")
            sys.stdout.flush()
            
            results = self.model.predict(
                source=processing_path, 
                imgsz=imgsz, 
                conf=conf, 
                iou=iou, 
                classes=classes, 
                max_det=max_det,
                verbose=False,  # Reduce console output
                save=False  # We'll handle saving annotated images ourselves
            )
            
            print(f"    YOLO prediction completed successfully")
            sys.stdout.flush()
            
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
                print(f"    Saving annotated frame...")
                sys.stdout.flush()
                self.save_annotated_frame(results[0], image_path, annotated_folder, self.model.names)
            
            # Immediate memory cleanup after processing
            gc.collect()
            
            progress = {
                "abnormal_count": abnormal_count,
                "normal_count": normal_count,
                "image_size": f"{width}x{height}",
                "image_mode": mode,
                "converted": temp_path is not None
            }
            
            print(f"    Detection completed: {abnormal_count} abnormal, {normal_count} normal")
            sys.stdout.flush()
    
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
                except Exception:
                    pass
    
    def save_annotated_frame(self, result, original_image_path, annotated_folder, class_names):
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
                    
                    # Draw bounding box with line width from config (default 2)
                    line_width = 2
                    if hasattr(self, 'config') and self.config and 'line_width' in self.config:
                        try:
                            line_width = int(self.config['line_width'])
                        except (ValueError, TypeError):
                            pass
                    cv2.rectangle(image, (x1, y1), (x2, y2), color, line_width)
                    
                    # Prepare label text based on config settings
                    show_labels = True
                    show_conf = True
                    
                    if hasattr(self, 'config'):
                        if 'show_labels' in self.config:
                            show_labels = self.config['show_labels'] == "true"
                        if 'show_conf' in self.config:
                            show_conf = self.config['show_conf'] == "true"
                    
                    if show_labels and show_conf:
                        label = f"{class_name}: {confidence:.2f}"
                    elif show_labels:
                        label = f"{class_name}"
                    elif show_conf:
                        label = f"{confidence:.2f}"
                    else:
                        label = ""
                    
                    # Only draw label if not empty
                    if label:
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
    
    def read_jgw(self, jgw_file):
        """Read JGW file with error handling"""
        try:
            with open(jgw_file) as f:
                params = f.readlines()
            return [float(param.strip()) for param in params]
        except FileNotFoundError:
            return None
        except Exception:
            return None
    
    def image_to_map_coords(self, x, y, pixel_size_x, pixel_size_y, upper_left_x, upper_left_y):
        """Convert image coordinates to map coordinates"""
        map_x = upper_left_x + x * pixel_size_x
        map_y = upper_left_y + y * pixel_size_y
        return map_x, map_y
    
    def create_geojson(self, detected_objects, jgw_params, labels):
        """Create a GeoJSON feature collection from detected objects"""
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
                        map_x, map_y = self.image_to_map_coords(center_x, center_y, pixel_size_x, pixel_size_y, upper_left_x, upper_left_y)
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
                    except Exception:
                        continue
                        
        return geojson.FeatureCollection(features)
    
    def save_geojson(self, feature_collection, input_image_path):
        """Save GeoJSON to file"""
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
        except Exception:
            return None
    
    def convert_geojson_to_kml(self, geojson_path, kml_path):
        """Convert GeoJSON to KML"""
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
            return True
        except Exception:
            return False
    
    def convert_geojson_to_shp(self, geojson_path, shp_path):
        """Convert GeoJSON to SHP"""
        try:
            gdf = gpd.read_file(geojson_path)
            gdf.to_file(shp_path, driver='ESRI Shapefile')
            return True
        except Exception:
            return False
