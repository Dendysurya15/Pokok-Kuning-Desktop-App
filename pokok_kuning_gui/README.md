# Pokok Kuning Desktop Application

A GUI application for processing TIF images to detect and map pokok kuning (yellow trees) using YOLOv8.

## Features

- Load and process TIF image files
- Detect normal and abnormal trees using YOLOv8
- Convert detection results to GeoJSON, SHP, and KML formats
- Save annotated images with bounding boxes
- Configure detection parameters (confidence threshold, IOU threshold, etc.)
- Save and load configurations

## Installation

1. Make sure you have Python 3.8 or higher installed
2. Install the required dependencies:

```
pip install -r requirements.txt
```

3. Place your YOLOv8 model files (.pt) in the `model` directory

## Usage

1. Run the application:

```
python main.py
```

2. Use the "Tambah Folder Tif" button to select a folder containing TIF images
3. Configure the detection parameters as needed
4. Click "Convert to SHP" to process the images
5. View the results using the "Result Converted" button

## Command Line Usage

If you prefer to use the command line, you can run the core functionality directly:

```
python -m core.processor --folder "path/to/images" --weights "model/yolov8n-pokok-kuning.pt" --save-annotated --shp
```

Command line options:
- `--folder`: Path to the folder containing images (required)
- `--weights`: Path to the YOLO weights file (default: model/yolov8n-pokok-kuning.pt)
- `--imgsz`: Image size for YOLO model (default: 1280)
- `--conf`: Confidence threshold (default: 0.2)
- `--iou`: IoU threshold (default: 0.2)
- `--classes`: List of class indices to detect
- `--kml`: Convert GeoJSON to KML
- `--shp`: Convert GeoJSON to SHP
- `--skip-invalid`: Skip invalid images instead of stopping
- `--save-annotated`: Save annotated frames with bounding boxes

## Directory Structure

- `main.py`: Application entry point
- `ui/`: User interface components
- `core/`: Core processing functionality
- `utils/`: Utility functions
- `model/`: YOLOv8 model files (.pt)

## Requirements

See `requirements.txt` for a list of dependencies.
