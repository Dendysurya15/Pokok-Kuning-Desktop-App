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

def safe_print(message):
    """Safe print function that works in both console and windowed modes"""
    try:
        print(message)
        # Safe flush - only flush if stdout exists and has flush method
        if hasattr(sys.stdout, 'flush') and sys.stdout is not None:
            sys.stdout.flush()
    except (AttributeError, OSError):
        # If print fails, just continue silently
        pass

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
        
        # Check if config['model'] is already a full path
        model_name = config['model']
        if os.path.isabs(model_name) or model_name.startswith("C:"):
            # It's already a full path, use it directly
            if os.path.exists(model_name):
                model_path = model_name
                safe_print(f"  ✓ Using custom model path: {model_path}")
            else:
                error_msg = f"Custom model path not found: {model_name}"
                safe_print(f"  ✗ {error_msg}")
                return {
                    "error": error_msg,
                    "successful_processed": 0,
                    "failed_processed": 0,
                    "total_files": 0
                }
        else:
            # It's a model name, construct the path
            # Use the EXACT same path resolution as main_window.py
            # From ui/main_window.py: os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model")
            script_dir = os.path.dirname(os.path.abspath(__file__))  # core/
            parent_dir = os.path.dirname(script_dir)                 # pokok_kuning_gui/
            model_folder = os.path.join(parent_dir, "model")         # pokok_kuning_gui/model/
            dev_model_path = os.path.join(model_folder, f"{model_name}.pt")
            possible_paths.append(dev_model_path)
            
            # Method 2: From executable directory (PyInstaller)
            if hasattr(sys, '_MEIPASS'):
                # Running in PyInstaller bundle
                exe_model_path = os.path.join(sys._MEIPASS, "model", f"{model_name}.pt")
                possible_paths.append(exe_model_path)
            
            # Method 3: Relative to executable location
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            exe_relative_path = os.path.join(exe_dir, "model", f"{model_name}.pt")
            possible_paths.append(exe_relative_path)
            
            # Method 4: In same directory as executable
            same_dir_path = os.path.join(exe_dir, f"{model_name}.pt")
            possible_paths.append(same_dir_path)
            
            model_path = None
            for path in possible_paths:
                safe_print(f"  Checking model path: {path}")
                if os.path.exists(path):
                    model_path = path
                    safe_print(f"  ✓ Found model at: {model_path}")
                    break
            
            if model_path is None:
                error_msg = f"Model {model_name}.pt not found. Searched paths:\n"
                for path in possible_paths:
                    error_msg += f"  - {path}\n"
                safe_print(error_msg)
                return {
                    "error": error_msg,
                    "successful_processed": 0,
                    "failed_processed": 0,
                    "total_files": 0
                }
        
        try:
            safe_print(f"  Loading YOLO model from: {model_path}")
            # ✅ Better isolation for PyInstaller - import YOLO with proper guards
            if getattr(sys, 'frozen', False):
                # Running in PyInstaller bundle - use more careful import
                import multiprocessing
                multiprocessing.freeze_support()
            
            from ultralytics import YOLO
            
            # ✅ Add explicit device detection for both development and executable
            import torch
            device = "cpu"  # Default fallback
            
            if torch.cuda.is_available():
                device = "cuda"
                safe_print(f"  ✓ CUDA detected: {torch.cuda.get_device_name(0)}")
                safe_print(f"  ✓ CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            else:
                safe_print(f"  ⚠️  CUDA not available, using CPU")
                
            # Set environment variables for better GPU detection in PyInstaller
            if getattr(sys, 'frozen', False) and torch.cuda.is_available():
                os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # Ensure GPU 0 is visible
                
            safe_print(f"  Using device: {device}")
            
            # Load model with explicit device
            self.model = YOLO(model_path)
            
            # Move model to GPU if available
            if device == "cuda":
                try:
                    self.model.to(device)
                    safe_print(f"  ✓ Model moved to GPU successfully")
                except Exception as e:
                    safe_print(f"  ⚠️  Could not move model to GPU: {e}, using CPU")
                    device = "cpu"
            
            safe_print(f"  ✓ Model loaded successfully on {device}")
        except Exception as e:
            error_msg = f"Failed to load model: {str(e)}"
            safe_print(f"  ✗ {error_msg}")
            return {
                "error": error_msg,
                "successful_processed": 0,
                "failed_processed": 0,
                "total_files": 0
            }
        
        # Get image files
        safe_print(f"  Scanning folder: {folder_path}")
        image_extensions = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')
        image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(image_extensions)]
        total_files = len(image_files)
        safe_print(f"  Found {total_files} image files to process")
        
        successful_processed = 0
        failed_processed = 0
        processing_times = []
        total_abnormal = 0
        total_normal = 0
        
        for index, image_file in enumerate(image_files):
            file_start_time = time.time()
            image_path = os.path.join(folder_path, image_file)
            safe_print(f"  Processing [{index+1}/{total_files}]: {image_file}")
            
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
                    safe_print(f"    Memory cleanup after {index + 1} files...")
                    gc.collect()
                    
            except Exception as e:
                safe_print(f"    ❌ Error processing {image_file}: {str(e)}")
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
        
        safe_print(f"\n  Processing complete!")
        safe_print(f"  Successfully processed: {successful_processed}/{total_files}")
        safe_print(f"  Failed: {failed_processed}/{total_files}")
        safe_print(f"  Total abnormal objects: {total_abnormal}")
        safe_print(f"  Total normal objects: {total_normal}")
        safe_print(f"  Total time: {total_time:.2f} seconds")
        
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
            # Import torch for device detection
            import torch
            
            safe_print(f"    Starting detection for: {os.path.basename(image_path)}")
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
                
            # Get device for inference
            inference_device = "cuda" if torch.cuda.is_available() else "cpu"
            safe_print(f"    Running YOLO prediction (imgsz={imgsz}, conf={conf}, iou={iou}, device={inference_device})...")
            
            results = self.model.predict(
                source=processing_path, 
                imgsz=imgsz, 
                conf=conf, 
                iou=iou, 
                classes=classes, 
                max_det=max_det,
                device=inference_device,  # Explicitly set device for inference
                verbose=False,  # Reduce console output
                save=False  # We'll handle saving annotated images ourselves
            )
            
            safe_print(f"    YOLO prediction completed successfully")
            
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
                safe_print(f"    Saving annotated frame...")
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
            
            safe_print(f"    Detection completed: {abnormal_count} abnormal, {normal_count} normal")
    
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
                safe_print(f"  Warning: Could not load image for annotation: {original_image_path}")
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
                safe_print(f"  Saved annotated frame: {output_path}")
            else:
                safe_print(f"  Warning: Failed to save annotated frame: {output_path}")
                
        except Exception as e:
            safe_print(f"  Error saving annotated frame: {e}")
    
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
