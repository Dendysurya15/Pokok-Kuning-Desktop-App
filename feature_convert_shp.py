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
import sys  # Import sys to use flush
# Step 1: Object Detection with YOLO
def load_yolo_model(weights_path):
    model = YOLO(weights_path)
    return model
global_abnormal_count = 0
global_normal_count = 0

def detect_objects(image_path, model, imgsz, conf, iou, classes=None):
    global global_abnormal_count, global_normal_count
    results = model.predict(source=image_path, imgsz=imgsz, conf=conf, iou=iou, classes=classes, max_det=12000)
    
    for result in results:
        for detection in result.boxes:
            class_id = int(detection.cls)
            if class_id == 0:  # Assuming class 0 is abnormal
                global_abnormal_count += 1
            elif class_id == 1:  # Assuming class 1 is normal
                global_normal_count += 1
    
    return results

# Step 2: Convert Image Coordinates to Map Coordinates
def read_jgw(jgw_file):
    with open(jgw_file) as f:
        params = f.readlines()
    return [float(param.strip()) for param in params]

def image_to_map_coords(x, y, pixel_size_x, pixel_size_y, upper_left_x, upper_left_y):
    map_x = upper_left_x + x * pixel_size_x
    map_y = upper_left_y + y * pixel_size_y
    return map_x, map_y

# Step 3: Create a GeoJSON
def create_geojson(detected_objects, jgw_params, labels):
    pixel_size_x, rotation_x, rotation_y, pixel_size_y, upper_left_x, upper_left_y = jgw_params
    features = []
    for result in detected_objects:
        for detection in result.boxes:
            x1, y1, x2, y2 = detection.xyxy[0].cpu().numpy()  # Convert to CPU and NumPy
            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
            map_x, map_y = image_to_map_coords(center_x, center_y, pixel_size_x, pixel_size_y, upper_left_x, upper_left_y)
            point = Point(map_x, map_y)
            feature = geojson.Feature(geometry=mapping(point), properties={"label": labels[int(detection.cls)]})
            features.append(feature)
    return geojson.FeatureCollection(features)

# Step 4: Save output, handle duplicates
def save_geojson(feature_collection, input_image_path):
    base_name = os.path.splitext(os.path.basename(input_image_path))[0]
    output_path = os.path.join(os.path.dirname(input_image_path), base_name + ".geojson")
    
    counter = 1
    while os.path.exists(output_path):
        output_path = os.path.join(os.path.dirname(input_image_path), f"{base_name}_{counter}.geojson")
        counter += 1
    
    with open(output_path, "w") as f:
        geojson.dump(feature_collection, f)
    return output_path

# Step 5: Convert GeoJSON to KML
def convert_geojson_to_kml(geojson_path, kml_path):
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

# Step 6: Convert GeoJSON to SHP
def convert_geojson_to_shp(geojson_path, shp_path):
    gdf = gpd.read_file(geojson_path)
    gdf.to_file(shp_path, driver='ESRI Shapefile')

# Utility function to display duration in minutes, seconds, and full seconds
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
    parser.add_argument("--weights", required=True, help="Path to the YOLO weights file")
    parser.add_argument("--imgsz", type=int, required=False, help="Image size for YOLO model", default=9024)
    parser.add_argument("--conf", type=float, required=False, help="Confidence threshold for YOLO model", default=0.2)
    parser.add_argument("--iou", type=float, required=False, help="IoU threshold for YOLO model", default=0.2)
    parser.add_argument("--classes", type=int, nargs='+', help="List of class indices to detect")
    parser.add_argument("--kml", action="store_true", help="Convert GeoJSON to KML after detection")
    parser.add_argument("--shp", action="store_true", help="Convert GeoJSON to SHP after detection")
    # parser.add_argument("--save", type=bool, required=False, help="IoU threshold for YOLO model", default=False)

    args = parser.parse_args()

    start_time = time.time()

    processing_times = []

    model = load_yolo_model(args.weights)
    # total_files = len(image_files)
    # Loop over all images in the folder
    image_files = [f for f in os.listdir(args.folder) if f.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))]
    total_files = len(image_files)

    for index, image_file in enumerate(tqdm(image_files, desc="Processing images")):
        image_path = os.path.join(args.folder, image_file)
        
        # print(f"Converting {image_file} to GeoJSON...")
        
        # In the main processing loop
        detected_objects = detect_objects(image_path, model, args.imgsz, args.conf, args.iou, classes=args.classes)

        # Load the correspoanding JGW file
        base_name = os.path.splitext(image_path)[0]
        jgw_file = base_name + ".tfw"
        jgw_params = read_jgw(jgw_file)
        
        # Create GeoJSON
        labels = model.names  # Get labels directly from the YOLO model
        feature_collection = create_geojson(detected_objects, jgw_params, labels)
        
        # Save GeoJSON
        geojson_output_path = save_geojson(feature_collection, image_path)
        # print(f"GeoJSON saved to {geojson_output_path}")
        
        # Convert to KML if --kml flag is active
        if args.kml:
            # print(f"Converting {image_file} to KML...")
            kml_output_path = geojson_output_path.replace('.geojson', '.kml')
            convert_geojson_to_kml(geojson_output_path, kml_output_path)
            # print(f"KML saved to {kml_output_path}")

        # Convert to SHP if --shp flag is active
        if args.shp:
            # print(f"Converting {image_file} to SHP...")
            shp_output_path = geojson_output_path.replace('.geojson', '.shp')
            convert_geojson_to_shp(geojson_output_path, shp_output_path)
            # print(f"SHP saved to {shp_output_path}")
        
        current_time = time.time()
        iteration_time = current_time - start_time
        processing_times.append(iteration_time)
        avg_time = sum(processing_times) / len(processing_times)
       
        progress = {
            
            "abnormal_count": global_abnormal_count,
            "normal_count": global_normal_count,
            "processed": index + 1,
            "total": total_files,
            "current_file": image_file,
            "status": "Processed successfully",
            "avg_time_per_file": f"{avg_time:.2f}",
        }
        print(json.dumps(progress))  # Print the progress in JSON format
        sys.stdout.flush()  # Flush the output
        
    end_time = time.time()

    # Display total processing duration
    display_duration(start_time, end_time)
