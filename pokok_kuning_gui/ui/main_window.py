from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QCheckBox, QProgressBar, QComboBox, QSlider, QGroupBox, 
    QRadioButton, QSpinBox, QMessageBox, QTextEdit, QDoubleSpinBox,
    QFrame, QSizePolicy, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QSize
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QLinearGradient, QPainter, QIcon

import os
import sys
import time
import json
import platform
import psutil

from utils.config_manager import load_config, save_config, get_model_names
from core.processor import ImageProcessor
from core.device_specs import (
    get_cpu_info, get_memory_info, get_disk_info, get_gpu_info, 
    get_network_info, get_battery_info, get_sensors_info, get_system_info,
    get_size
)

def get_system_specs():
    """Get detailed system specifications"""
    specs = {}
    
    try:
        # Basic system info
        specs['os'] = f"{platform.system()} {platform.release()}"
        specs['processor'] = platform.processor() or "Unknown"
        specs['architecture'] = platform.architecture()[0]
        
        # Memory info
        memory = psutil.virtual_memory()
        specs['total_ram'] = f"{memory.total / (1024**3):.1f} GB"
        specs['available_ram'] = f"{memory.available / (1024**3):.1f} GB"
        specs['ram_usage'] = f"{memory.percent:.1f}%"
        
        # CPU info
        specs['cpu_cores'] = psutil.cpu_count(logical=False)
        specs['cpu_threads'] = psutil.cpu_count(logical=True)
        specs['cpu_freq'] = f"{psutil.cpu_freq().current:.0f} MHz" if psutil.cpu_freq() else "Unknown"
        
        # GPU info
        try:
            import torch
            if torch.cuda.is_available():
                specs['gpu'] = torch.cuda.get_device_name(0)
                specs['gpu_memory'] = f"{torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
                specs['cuda_version'] = torch.version.cuda
            else:
                specs['gpu'] = "No CUDA GPU detected"
                specs['gpu_memory'] = "N/A"
                specs['cuda_version'] = "N/A"
        except ImportError:
            specs['gpu'] = "PyTorch not available"
            specs['gpu_memory'] = "N/A"
            specs['cuda_version'] = "N/A"
            
        # Python info
        specs['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
    except Exception as e:
        print(f"Error getting system specs: {e}")
        
    return specs


class StatusPanel(QFrame):
    """Status panel widget showing connection and system status"""
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #d1d9e6;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Status grid
        status_layout = QHBoxLayout()
        status_layout.setSpacing(15)
        
        # Left side - Status info
        left_panel = QVBoxLayout()
        left_panel.setSpacing(4)
        
        self.db_status = QLabel("Status Database : Connected")
        self.db_status.setStyleSheet("color: #28a745; font-weight: 500; font-size: 11px;")
        
        self.machine_status = QLabel("Status System : Ready")
        self.machine_status.setStyleSheet("color: #495057; font-size: 11px;")
        
        self.selected_folder = QLabel("Select Folder : ")
        self.selected_folder.setStyleSheet("color: #495057; font-size: 11px;")
        
        left_panel.addWidget(self.db_status)
        left_panel.addWidget(self.machine_status)
        left_panel.addWidget(self.selected_folder)
        status_layout.addLayout(left_panel)
        
        # Middle - Additional info
        middle_panel = QVBoxLayout()
        middle_panel.setSpacing(4)
        
        self.log_count = QLabel("Total Files : 0")
        self.log_count.setStyleSheet("color: #495057; font-size: 11px;")
        
        self.process_status = QLabel("Process Status : Standby")
        self.process_status.setStyleSheet("color: #495057; font-size: 11px;")
        
        self.model_info = QLabel("AI Model : yolov8n-pokok-kuning")
        self.model_info.setStyleSheet("color: #495057; font-size: 11px;")
        
        middle_panel.addWidget(self.log_count)
        middle_panel.addWidget(self.process_status)
        middle_panel.addWidget(self.model_info)
        status_layout.addLayout(middle_panel)
        
        # Right side - System specifications
        right_panel = QVBoxLayout()
        right_panel.setSpacing(4)
        
        # Get system specs
        specs = get_system_specs()
        
        # GPU info (most important)
        gpu = specs.get('gpu', 'Unknown')
        if len(gpu) > 35:  # Truncate long GPU names
            gpu = gpu[:35] + "..."
        gpu_memory = specs.get('gpu_memory', 'Unknown')
        self.gpu_info = QLabel(f"GPU : {gpu}")
        # Color code GPU status
        if "No CUDA" in specs.get('gpu', '') or "not available" in specs.get('gpu', ''):
            self.gpu_info.setStyleSheet("color: #dc3545; font-weight: 500; font-size: 11px;")  # Red for no GPU
        else:
            self.gpu_info.setStyleSheet("color: #28a745; font-weight: 500; font-size: 11px;")  # Green for GPU available
        
        # Memory info
        total_ram = specs.get('total_ram', 'Unknown')
        self.memory_info = QLabel(f"Memory : {total_ram}")
        self.memory_info.setStyleSheet("color: #495057; font-size: 11px;")
        
        # CPU cores
        cores = specs.get('cpu_cores', 'Unknown')
        threads = specs.get('cpu_threads', 'Unknown')
        self.cpu_info = QLabel(f"CPU : {cores}C/{threads}T")
        self.cpu_info.setStyleSheet("color: #495057; font-size: 11px;")
        
        right_panel.addWidget(self.gpu_info)
        right_panel.addWidget(self.memory_info)
        right_panel.addWidget(self.cpu_info)
        status_layout.addLayout(right_panel)
        
        layout.addLayout(status_layout)
    
    def refresh_system_specs(self):
        """Refresh system specifications display"""
        try:
            specs = get_system_specs()
            
            # Update GPU info
            gpu = specs.get('gpu', 'Unknown')
            if len(gpu) > 35:
                gpu = gpu[:35] + "..."
            self.gpu_info.setText(f"GPU : {gpu}")
            
            # Update GPU color based on availability
            if "No CUDA" in specs.get('gpu', '') or "not available" in specs.get('gpu', ''):
                self.gpu_info.setStyleSheet("color: #dc3545; font-weight: 500; font-size: 11px;")
            else:
                self.gpu_info.setStyleSheet("color: #28a745; font-weight: 500; font-size: 11px;")
            
            # Update memory info
            total_ram = specs.get('total_ram', 'Unknown')
            self.memory_info.setText(f"Memory : {total_ram}")
            
            # Update CPU info
            cores = specs.get('cpu_cores', 'Unknown')
            threads = specs.get('cpu_threads', 'Unknown')
            self.cpu_info.setText(f"CPU : {cores}C/{threads}T")
            
        except Exception as e:
            print(f"Error refreshing system specs: {e}")
    
    def refresh_status(self):
        """Refresh the status display"""
        # This method will be called when refresh button is clicked
        # The parent window can override this if needed
        pass

class ConfigurationTable(QTableWidget):
    """Table widget for displaying configuration settings"""
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # Set table properties
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Parameter", "Value", "Type", "Description"])
        
        # Style the table
        self.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #d1d9e6;
                border-radius: 6px;
                gridline-color: #e9ecef;
                selection-background-color: #e3f2fd;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #e9ecef;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px 6px;
                border: none;
                border-bottom: 1px solid #d1d9e6;
                font-weight: 600;
                color: #495057;
                font-size: 11px;
            }
        """)
        
        # Set column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Parameter
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Value
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Description
        
        # Add sample data
        self.populate_sample_data()
        
    def populate_sample_data(self):
        config_data = [
            ["Image Size", "12800", "Integer", "Image size for processing"],
            ["Confidence", "0.2", "Float", "Confidence threshold"],
            ["IOU Threshold", "0.2", "Float", "Intersection over Union threshold"],
            ["Max Detection", "10000", "Integer", "Maximum detections per image"],
            ["Line Width", "3", "Integer", "Annotation line width"],
            ["Device", "auto", "String", "Processing device: auto, cpu, or cuda"],
            ["Convert KML", "false", "Boolean", "Export to KML format"],
            ["Convert SHP", "true", "Boolean", "Export to Shapefile format"],
            ["Show Labels", "true", "Boolean", "Display class labels"],
            ["Show Confidence", "false", "Boolean", "Display confidence scores"]
        ]
        
        self.setRowCount(len(config_data))
        
        for row, data in enumerate(config_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))
                if col == 0:  # Parameter column - bold
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.setItem(row, col, item)

class FileManagementPanel(QFrame):
    """Panel for file management operations"""
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #d1d9e6;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("File Management")
        title.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #495057;
                margin-bottom: 8px;
                padding-bottom: 4px;
                border-bottom: 1px solid #e9ecef;
            }
        """)
        layout.addWidget(title)
        
        # Folder selection
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(8)
        
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select folder containing images...")
        self.folder_input.setReadOnly(True)
        self.folder_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
                background-color: #f8f9fa;
                color: #495057;
            }
        """)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 500;
                font-size: 11px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        browse_btn.clicked.connect(self.browse_folder)
        
        folder_layout.addWidget(self.folder_input, 1)
        folder_layout.addWidget(browse_btn)
        layout.addLayout(folder_layout)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.setSpacing(8)
        
        model_label = QLabel("AI Model:")
        model_label.setStyleSheet("font-size: 11px; color: #495057; min-width: 60px;")
        
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Select AI model file (.pt)...")
        self.model_input.setReadOnly(True)
        self.model_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
                background-color: #f8f9fa;
                color: #495057;
            }
        """)
        
        browse_model_btn = QPushButton("Browse")
        browse_model_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 500;
                font-size: 11px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        browse_model_btn.clicked.connect(self.browse_model)
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_input, 1)
        model_layout.addWidget(browse_model_btn)
        layout.addLayout(model_layout)
        
        # Device selection
        device_layout = QHBoxLayout()
        device_layout.setSpacing(8)
        
        device_label = QLabel("Device:")
        device_label.setStyleSheet("font-size: 11px; color: #495057; min-width: 60px;")
        
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu", "cuda"])
        self.device_combo.setCurrentText("auto")
        self.device_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
                background-color: white;
                color: #495057;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ced4da;
                background-color: white;
                selection-background-color: #e3f2fd;
            }
        """)
        self.device_combo.currentTextChanged.connect(self.on_device_changed)
        
        device_info_btn = QPushButton("Info")
        device_info_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 11px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        device_info_btn.clicked.connect(self.show_device_info)
        
        # Add Detailed Specs button
        detailed_specs_btn = QPushButton("Detailed")
        detailed_specs_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 11px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        detailed_specs_btn.clicked.connect(self.show_detailed_specs)
        
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo, 1)
        device_layout.addWidget(device_info_btn)
        device_layout.addWidget(detailed_specs_btn)
        layout.addLayout(device_layout)
        
        # File options
        options_layout = QHBoxLayout()
        options_layout.setSpacing(15)
        
        self.save_annotated = QCheckBox("Save Annotated Images")
        self.save_annotated.setChecked(True)
        self.save_annotated.setStyleSheet("""
            QCheckBox {
                font-size: 11px;
                color: #495057;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #ced4da;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #007bff;
                border-color: #007bff;
            }
        """)
        
        self.export_kml = QCheckBox("Export KML")
        self.export_kml.setStyleSheet(self.save_annotated.styleSheet())
        
        self.export_shp = QCheckBox("Export Shapefile")
        self.export_shp.setChecked(True)
        self.export_shp.setStyleSheet(self.save_annotated.styleSheet())
        
        options_layout.addWidget(self.save_annotated)
        options_layout.addWidget(self.export_kml)
        options_layout.addWidget(self.export_shp)
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        start_btn = QPushButton("Start Processing")
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 12px;
                min-width: 100px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        start_btn.clicked.connect(self.start_processing)
        
        settings_btn = QPushButton("Settings")
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: 500;
                font-size: 11px;
                min-width: 80px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        settings_btn.clicked.connect(self.open_settings)
        
        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: 500;
                font-size: 11px;
                min-width: 60px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        reset_btn.clicked.connect(self.reset_settings)
        
        action_layout.addWidget(start_btn)
        action_layout.addWidget(settings_btn)
        action_layout.addWidget(reset_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
    
    def browse_folder(self):
        """Open folder browser dialog"""
        if self.parent:
            self.parent.select_folder()
    
    def browse_model(self):
        """Open model browser dialog"""
        if self.parent:
            self.parent.select_model()
    
    def start_processing(self):
        """Start the image processing"""
        if self.parent:
            self.parent.start_conversion()
    
    def open_settings(self):
        """Open settings dialog"""
        if self.parent:
            self.parent.save_settings()
    
    def on_device_changed(self, device):
        """Handle device selection change"""
        if self.parent:
            self.parent.on_device_changed(device)
    
    def show_device_info(self):
        """Show device information dialog"""
        if self.parent:
            self.parent.show_device_info()
    
    def show_detailed_specs(self):
        """Show detailed device specifications"""
        if self.parent:
            self.parent.show_comprehensive_device_specs()
    
    def reset_settings(self):
        """Reset settings to default"""
        if self.parent:
            try:
                reply = QMessageBox.question(
                    self.parent, 
                    "Reset Settings", 
                    "Are you sure you want to reset all settings to default values?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # Reset file options
                    if hasattr(self.parent, 'file_panel'):
                        self.parent.file_panel.save_annotated.setChecked(True)
                        self.parent.file_panel.export_kml.setChecked(False)
                        self.parent.file_panel.export_shp.setChecked(True)
                    
                    # Reset model to default
                    default_model = "yolov8n-pokok-kuning"
                    self.parent.selected_model = default_model
                    if hasattr(self.parent, 'file_panel'):
                        self.parent.file_panel.model_input.setText(default_model)
                    self.parent.status_panel.model_info.setText(f"AI Model : {default_model}")
                    
                    # Update configuration table if available
                    if hasattr(self.parent, 'config_table'):
                        self.parent.config_table.populate_sample_data()
                    
                    # Synchronize UI with reset values
                    self.parent.sync_config_with_ui()
                    
                    QMessageBox.information(self.parent, "Success", "Settings reset to default values!")
                    self.parent.add_log_message("Settings reset to default values")
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to reset settings: {str(e)}")
                self.parent.add_log_message(f"❌ Failed to reset settings: {str(e)}")

class ProcessingThread(QThread):
    """Thread for running the image processing in the background"""
    progress_update = pyqtSignal(dict)
    processing_finished = pyqtSignal(dict)
    
    def __init__(self, folder_path, config):
        super().__init__()
        self.folder_path = folder_path
        self.config = config
        self.processor = ImageProcessor()
        
    def run(self):
        print(f"Processing thread started for: {self.folder_path}")
        try:
            start_time = time.time()
            results = self.processor.process_folder(
                self.folder_path, 
                self.config,
                progress_callback=self.progress_update.emit
            )
            end_time = time.time()
            
            results['total_time'] = end_time - start_time
            print("Processing thread finished successfully, emitting results...")
            self.processing_finished.emit(results)
            
        except Exception as e:
            print(f"❌ Critical error in processing thread: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            
            # Emit error result instead of crashing
            error_results = {
                "error": f"Processing failed: {str(e)}",
                "successful_processed": 0,
                "failed_processed": 0,
                "total_files": 0,
                "total_time": 0,
                "total_abnormal": 0,
                "total_normal": 0
            }
            self.processing_finished.emit(error_results)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def get_asset_path(self, filename):
        """Get the full path to an asset file"""
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            return os.path.join(sys._MEIPASS, 'assets', 'img', filename)
        else:
            # Running as script
            return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'img', filename)
    
    def get_model_class_names(self, model_name):
        """Get class names from the PT model without loading the full model"""
        try:
            # Try to get model path
            if os.path.isabs(model_name) or model_name.startswith("C:"):
                model_path = model_name
            else:
                # Construct the path
                script_dir = os.path.dirname(os.path.abspath(__file__))  # ui/
                parent_dir = os.path.dirname(script_dir)                 # pokok_kuning_gui/
                model_folder = os.path.join(parent_dir, "model")         # pokok_kuning_gui/model/
                model_path = os.path.join(model_folder, f"{model_name}.pt")
                
                # Check if exists, if not try PyInstaller path
                if not os.path.exists(model_path) and hasattr(sys, '_MEIPASS'):
                    model_path = os.path.join(sys._MEIPASS, "model", f"{model_name}.pt")
            
            if not os.path.exists(model_path):
                print(f"Model not found: {model_path}")
                return ["Class 0", "Class 1"]  # Default fallback
            
            # Import YOLO and get class names
            from ultralytics import YOLO
            model = YOLO(model_path)
            class_names = list(model.names.values()) if hasattr(model, 'names') and model.names else []
            
            # Clean up model to free memory
            del model
            
            if class_names:
                return class_names
            else:
                return ["Class 0", "Class 1"]  # Default fallback
                
        except Exception as e:
            print(f"Error getting class names: {e}")
            return ["Class 0", "Class 1"]  # Default fallback
        
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("Digital Architect — PT Sawit Sumbernan Sarana")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)
        
        # Set window icon
        icon_path = self.get_asset_path('logo.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Set modern styling similar to HRIS
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', 'Tahoma', sans-serif;
            }
            QWidget {
                font-size: 11px;
                color: #495057;
            }
            QLabel {
                font-size: 11px;
                color: #495057;
            }
        """)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        self.setCentralWidget(central_widget)
        
        # Load configuration
        self.config = load_config()
        
        # Initialize selected folder and model
        self.selected_folder = None
        self.selected_model = None
        
        # Create header
        self.create_header(main_layout)
        
        # Create status panel with system specs
        self.status_panel = StatusPanel()
        main_layout.addWidget(self.status_panel)
        
        # Create configuration table section
        self.create_config_section(main_layout)
        
        # Create file management section
        self.file_panel = FileManagementPanel(self)
        main_layout.addWidget(self.file_panel)
        
        # Create progress dialog (hidden initially)
        self.create_progress_section()
        
        # Initialize variables
        self.processing_thread = None
        self.total_processed = 0
        self.total_files = 0
        self.total_abnormal = 0
        self.total_normal = 0
        
        # Set initial model path
        self.set_initial_model_path()
        
        # Initialize selected device
        self.selected_device = "auto"
        
        # Synchronize configuration with UI
        self.sync_config_with_ui()
        
        # Add initial log message
        self.add_log_message("Application started successfully")
        self.add_log_message(f"Available models: {', '.join(get_model_names())}")
    
    def set_initial_model_path(self):
        """Set initial model path from config or default"""
        default_model = self.config.get("model", "yolov8n-pokok-kuning")
        if self.file_panel:
            self.file_panel.model_input.setText(default_model)
            self.selected_model = default_model

    def create_header(self, parent_layout):
        """Create modern header with gradient background and logo"""
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #007bff, stop:1 #0056b3);
                border-radius: 6px;
                padding: 15px;
            }
        """)
        header_widget.setFixedHeight(80)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_layout.setSpacing(15)
        
        # Logo
        logo_path = self.get_asset_path('logo.png')
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaledToHeight(50, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setFixedWidth(60)
            header_layout.addWidget(logo_label)
        
        # App title
        title_label = QLabel("Digital Architect — PT Sawit Sumbernan Sarana v2.0.0")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: 600;
                background-color: transparent;
                margin-left: 10px;
            }
        """)
        title_label.setMinimumWidth(300)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Device Specs button
        device_specs_button = QPushButton("🔍 Device Specs")
        device_specs_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 11px;
                min-width: 110px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.4);
            }
        """)
        device_specs_button.clicked.connect(self.show_comprehensive_device_specs)
        header_layout.addWidget(device_specs_button)
        
        # Show Log button
        show_log_button = QPushButton("Show Progress")
        show_log_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 11px;
                min-width: 100px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.4);
            }
        """)
        show_log_button.clicked.connect(self.toggle_progress_display)
        header_layout.addWidget(show_log_button)
        
        parent_layout.addWidget(header_widget)
        
    def create_config_section(self, parent_layout):
        """Create configuration section with table"""
        # Create group box for configuration
        config_group = QGroupBox("Configuration Settings")
        config_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: 600;
                color: #495057;
                border: 1px solid #d1d9e6;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px 0 6px;
                background-color: #f8f9fa;
            }
        """)
        
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(10)
        config_layout.setContentsMargins(10, 10, 10, 10)
        
        # Configuration table
        self.config_table = ConfigurationTable()
        config_layout.addWidget(self.config_table)
        
        parent_layout.addWidget(config_group)

    def create_progress_section(self):
        self.progress_dialog = QWidget(self)
        self.progress_dialog.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.progress_dialog.setWindowTitle("Processing Progress")
        self.progress_dialog.setGeometry(200, 200, 500, 400)
        self.progress_dialog.hide()
        
        # Apply consistent styling
        self.progress_dialog.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', 'Tahoma', sans-serif;
                font-size: 11px;
                color: #495057;
            }
        """)
        
        layout = QVBoxLayout(self.progress_dialog)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Timer label
        self.timer_label = QLabel("Elapsed Time: 0.00 seconds")
        self.timer_label.setStyleSheet("font-weight: 600; font-size: 12px;")
        layout.addWidget(self.timer_label)
        
        # Progress label
        progress_label = QLabel("Processing Progress:")
        progress_label.setStyleSheet("font-weight: 600; margin-top: 5px;")
        layout.addWidget(progress_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d1d9e6;
                border-radius: 4px;
                text-align: center;
                font-size: 11px;
                font-weight: 500;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Progress text
        self.progress_text = QLabel("0 of 0 images processed")
        self.progress_text.setStyleSheet("font-size: 11px; color: #6c757d;")
        layout.addWidget(self.progress_text)
        
        # Activity log
        log_label = QLabel("Activity Log:")
        log_label.setStyleSheet("font-weight: 600; margin-top: 10px;")
        layout.addWidget(log_label)
        
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d1d9e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                background-color: white;
            }
        """)
        layout.addWidget(self.activity_log)
        
        # Save Log button
        save_log_button = QPushButton("Save Log")
        save_log_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_log_button.clicked.connect(self.save_log)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        close_button.clicked.connect(self.close_progress_dialog)
        
        # Create horizontal layout for buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(save_log_button)
        button_layout.addWidget(close_button)
        button_layout.addStretch()  # Push buttons to the left
        
        layout.addLayout(button_layout)
    
    def add_log_message(self, message):
        """Add a message to the activity log"""
        timestamp = time.strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        
        # Add to activity log
        self.activity_log.append(formatted_message)
        
        # Auto-scroll to bottom
        self.activity_log.verticalScrollBar().setValue(
            self.activity_log.verticalScrollBar().maximum()
        )
        
        # Also print to console for debugging
        print(formatted_message)
    
    def clear_log(self):
        """Clear the log display"""
        self.activity_log.clear()
        self.activity_log.append("=== Pokok Kuning Detection System - ACTIVITY LOG ===\n")
        self.activity_log.append(f"Cleared at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.activity_log.append("-" * 50 + "\n")

    def toggle_progress_display(self):
        """Toggle the visibility of the progress dialog"""
        if self.progress_dialog.isHidden():
            self.progress_dialog.show()
            # Initialize log with header if it's empty
            if not self.activity_log.toPlainText().strip():
                self.activity_log.append("=== Pokok Kuning Detection System - ACTIVITY LOG ===\n")
                self.activity_log.append(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.activity_log.append("-" * 50 + "\n")
        else:
            self.progress_dialog.hide()

    def save_log(self):
        """Save the current activity log to a text file"""
        folder_path = "output"
        os.makedirs(folder_path, exist_ok=True)
        log_file_path = os.path.join(folder_path, "activity_log.txt")
        
        with open(log_file_path, "w") as f:
            f.write(self.activity_log.toPlainText())
        
        QMessageBox.information(self, "Log Saved", f"Activity log has been saved to:\n{log_file_path}")
        print(f"Activity log saved to: {log_file_path}")

    def close_progress_dialog(self):
        """Close the progress dialog"""
        self.progress_dialog.hide()
        self.progress_dialog.close()

    # Placeholder methods for compatibility with existing code
    def update_model_path_display(self):
        """Update model path display"""
        if self.selected_model and self.file_panel:
            self.file_panel.model_input.setText(self.selected_model)
    
    def update_class_selection_combo(self):
        """Placeholder method for class selection combo"""
        pass
    
    def start_conversion(self):
        """Start the image processing conversion"""
        if not self.selected_folder:
            QMessageBox.warning(self, "No Folder Selected", "Please select a folder containing images first.")
            return
        
        if not self.selected_model:
            QMessageBox.warning(self, "No Model Selected", "Please select an AI model first.")
            return
        
        # Get current configuration
        config = self.get_current_config()
        
        # Start processing thread
        self.processing_thread = ProcessingThread(self.selected_folder, config)
        self.processing_thread.progress_update.connect(self.update_progress)
        self.processing_thread.processing_finished.connect(self.processing_complete)
        self.processing_thread.start()
        
        # Show progress dialog
        self.toggle_progress_display()
        
        # Update status
        self.status_panel.process_status.setText("Process Status : Processing")
        self.add_log_message("Started processing images...")
    
    def update_progress(self, progress_data):
        """Update progress display"""
        if hasattr(self, 'progress_bar') and hasattr(self, 'progress_text'):
            if 'current' in progress_data and 'total' in progress_data:
                current = progress_data['current']
                total = progress_data['total']
                
                # Update progress bar
                self.progress_bar.setMaximum(total)
                self.progress_bar.setValue(current)
                
                # Update progress text
                self.progress_text.setText(f"{current} of {total} images processed")
                
                # Update status
                if hasattr(self, 'status_panel'):
                    self.status_panel.process_status.setText(f"Process Status : Processing ({current}/{total})")
                
                # Add to log
                if 'message' in progress_data:
                    self.add_log_message(progress_data['message'])
    
    def processing_complete(self, results):
        """Handle processing completion"""
        if 'error' in results:
            QMessageBox.critical(self, "Processing Error", f"Processing failed: {results['error']}")
            self.add_log_message(f"❌ Processing failed: {results['error']}")
        else:
            # Update status
            self.status_panel.process_status.setText("Process Status : Completed")
            
            # Show results
            message = f"""Processing completed successfully!

Total files processed: {results.get('total_files', 0)}
Successful: {results.get('successful_processed', 0)}
Failed: {results.get('failed_processed', 0)}
Total time: {results.get('total_time', 0):.2f} seconds
Abnormal detections: {results.get('total_abnormal', 0)}
Normal detections: {results.get('total_normal', 0)}

Results saved to output folder."""
            
            QMessageBox.information(self, "Processing Complete", message)
            self.add_log_message("✅ Processing completed successfully")
            
            # Update counters
            self.total_processed = results.get('successful_processed', 0)
            self.total_abnormal = results.get('total_abnormal', 0)
            self.total_normal = results.get('total_normal', 0)
        
        # Reset progress bar
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(0)
    
    def update_timer(self):
        """Update timer display"""
        pass
    
    def get_current_config(self):
        """Get current configuration from UI elements"""
        config = {}
        
        # Get model path
        if self.selected_model:
            config["model"] = self.selected_model
        
        # Get file options
        if hasattr(self, 'file_panel'):
            config["save_annotated"] = str(self.file_panel.save_annotated.isChecked()).lower()
            config["convert_kml"] = str(self.file_panel.export_kml.isChecked()).lower()
            config["convert_shp"] = str(self.file_panel.export_shp.isChecked()).lower()
        
        # Get configuration from table if available
        if hasattr(self, 'config_table'):
            for row in range(self.config_table.rowCount()):
                param = self.config_table.item(row, 0).text()
                value = self.config_table.item(row, 1).text()
                # Map parameter names to config keys
                if param == "Image Size":
                    config["imgsz"] = value
                elif param == "Confidence":
                    config["conf"] = value
                elif param == "IOU Threshold":
                    config["iou"] = value
                elif param == "Max Detection":
                    config["max_det"] = value
                elif param == "Line Width":
                    config["line_width"] = value
                elif param == "Device":
                    config["device"] = value.lower()
                elif param == "Convert KML":
                    config["convert_kml"] = value.lower()
                elif param == "Convert SHP":
                    config["convert_shp"] = value.lower()
                elif param == "Show Labels":
                    config["show_labels"] = value.lower()
                elif param == "Show Confidence":
                    config["show_conf"] = value.lower()
        
        # Add default values for required keys if not present
        defaults = {
            "imgsz": "12800",
            "iou": "0.2",
            "conf": "0.2",
            "max_det": "10000",
            "line_width": "3",
            "device": self.selected_device,
            "show_labels": "true",
            "show_conf": "false",
            "status_blok": "Full Blok",
            "class_selection": "All Classes"
        }
        
        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value
        
        # Ensure required keys are present
        required_keys = ["model", "imgsz", "iou", "conf", "convert_shp", "convert_kml", 
                        "max_det", "line_width", "device", "show_labels", "show_conf", 
                        "status_blok", "save_annotated"]
        
        for key in required_keys:
            if key not in config:
                if key == "model":
                    config[key] = "yolov8n-pokok-kuning"
                elif key == "save_annotated":
                    config[key] = "true"
                elif key == "convert_shp":
                    config[key] = "true"
                elif key == "convert_kml":
                    config[key] = "false"
                elif key == "device":
                    config[key] = self.selected_device
                elif key == "status_blok":
                    config[key] = "Full Blok"
                else:
                    config[key] = defaults.get(key, "")
        
        return config
    
    def select_model(self):
        """Open model browser dialog and set selected model"""
        # Start from model directory if available
        script_dir = os.path.dirname(os.path.abspath(__file__))  # ui/
        parent_dir = os.path.dirname(script_dir)                 # pokok_kuning_gui/
        model_folder = os.path.join(parent_dir, "model")         # pokok_kuning_gui/model/
        start_dir = model_folder if os.path.exists(model_folder) else ""
        
        model_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File",
            start_dir,
            "Model Files (*.pt);;All Files (*)"
        )
        
        if model_path:
            if os.path.exists(model_path):
                self.selected_model = model_path
                self.file_panel.model_input.setText(model_path)
                self.status_panel.model_info.setText(f"AI Model : {os.path.basename(model_path)}")
                
                # Auto-save the model path
                current_config = self.get_current_config()
                current_config["model"] = model_path
                save_config(current_config)
                
                self.add_log_message(f"Selected model: {model_path}")
            else:
                QMessageBox.warning(self, "Invalid Model", "Please select a valid model file.")
    
    def save_settings(self):
        """Save current settings to configuration"""
        try:
            current_config = self.get_current_config()
            save_config(current_config)
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            self.add_log_message("Settings saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
            self.add_log_message(f"❌ Failed to save settings: {str(e)}")
    
    def reset_settings(self):
        """Reset settings to default values"""
        try:
            reply = QMessageBox.question(
                self, 
                "Reset Settings", 
                "Are you sure you want to reset all settings to default values?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Reset file options
                if hasattr(self, 'file_panel'):
                    self.file_panel.save_annotated.setChecked(True)
                    self.file_panel.export_kml.setChecked(False)
                    self.file_panel.export_shp.setChecked(True)
                
                # Reset model to default
                default_model = "yolov8n-pokok-kuning"
                self.selected_model = default_model
                if hasattr(self, 'file_panel'):
                    self.file_panel.model_input.setText(default_model)
                self.status_panel.model_info.setText(f"AI Model : {default_model}")
                
                # Update configuration table if available
                if hasattr(self, 'config_table'):
                    self.config_table.populate_sample_data()
                
                # Synchronize UI with reset values
                self.sync_config_with_ui()
                
                QMessageBox.information(self, "Success", "Settings reset to default values!")
                self.add_log_message("Settings reset to default values")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset settings: {str(e)}")
            self.add_log_message(f"❌ Failed to reset settings: {str(e)}")
    
    def select_folder(self):
        """Open folder browser dialog and set selected folder"""
        # Start from last used folder if available
        start_dir = self.selected_folder if self.selected_folder and os.path.exists(self.selected_folder) else ""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", start_dir)
        
        if folder_path:
            self.set_folder_path(folder_path)
            
            # Auto-save the folder path if it's valid
            if self.selected_folder:
                current_config = self.get_current_config()
                current_config["last_folder_path"] = folder_path
                save_config(current_config)
    
    def set_folder_path(self, folder_path):
        """Set and validate the selected folder path"""
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            self.selected_folder = folder_path
            self.file_panel.folder_input.setText(folder_path)
            self.status_panel.selected_folder.setText(f"Select Folder : {os.path.basename(folder_path)}")
            
            # Count files in folder
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
            files = [f for f in os.listdir(folder_path) 
                    if os.path.isfile(os.path.join(folder_path, f)) and 
                    any(f.lower().endswith(ext) for ext in image_extensions)]
            
            self.total_files = len(files)
            self.status_panel.log_count.setText(f"Total Files : {self.total_files}")
            
            self.add_log_message(f"Selected folder: {folder_path} ({self.total_files} image files)")
        else:
            QMessageBox.warning(self, "Invalid Folder", "Please select a valid folder.")
    
    def show_results(self):
        """Show processing results"""
        if not self.selected_folder:
            QMessageBox.information(self, "Info", "Please select a folder and process images first.")
            return
        
        # Check if output folder exists
        output_folder = os.path.join(self.selected_folder, "output")
        if os.path.exists(output_folder):
            # Open output folder in file explorer
            if sys.platform == "win32":
                os.startfile(output_folder)
            elif sys.platform == "darwin":
                os.system(f"open '{output_folder}'")
            else:
                os.system(f"xdg-open '{output_folder}'")
            
            self.add_log_message(f"Opened output folder: {output_folder}")
        else:
            QMessageBox.information(self, "No Results", "No output folder found. Please process images first.")
    
    def get_full_model_path(self):
        """Get the full path to the selected model"""
        if self.selected_model:
            if os.path.isabs(self.selected_model):
                return self.selected_model
            else:
                # Construct relative path
                script_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.dirname(script_dir)
                model_folder = os.path.join(parent_dir, "model")
                return os.path.join(model_folder, f"{self.selected_model}.pt")
        return ""
    
    def on_model_combo_changed(self, text):
        """Handle model combo box change"""
        if text and text != self.selected_model:
            self.selected_model = text
            if hasattr(self, 'file_panel'):
                self.file_panel.model_input.setText(text)
            self.status_panel.model_info.setText(f"AI Model : {os.path.basename(text)}")
            self.add_log_message(f"Model changed to: {text}")
    
    def on_device_changed(self, device):
        """Handle device selection change"""
        self.selected_device = device
        self.add_log_message(f"Device changed to: {device}")
        
        # Update GPU info in status panel based on selection
        if hasattr(self, 'status_panel'):
            self.status_panel.refresh_system_specs()
    
    def show_device_info(self):
        """Show basic device information dialog"""
        try:
            import torch
            
            info_text = "=== Device Information ===\n\n"
            
            # Current selection
            info_text += f"Selected Device: {self.selected_device}\n\n"
            
            # PyTorch info
            info_text += f"PyTorch Version: {torch.__version__}\n"
            info_text += f"CUDA Available: {torch.cuda.is_available()}\n"
            
            if torch.cuda.is_available():
                info_text += f"CUDA Version: {torch.version.cuda}\n"
                info_text += f"GPU Count: {torch.cuda.device_count()}\n"
                
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    info_text += f"\nGPU {i}: {props.name}\n"
                    info_text += f"  Memory: {props.total_memory / (1024**3):.1f} GB\n"
                    info_text += f"  Compute Capability: {props.major}.{props.minor}\n"
            else:
                info_text += "\nNo CUDA GPUs detected.\n"
                info_text += "Possible reasons:\n"
                info_text += "- NVIDIA GPU drivers not installed\n"
                info_text += "- CUDA toolkit not installed\n"
                info_text += "- PyTorch CPU-only version installed\n"
            
            # Show system specs
            specs = get_system_specs()
            info_text += f"\n=== System Specifications ===\n"
            info_text += f"OS: {specs.get('os', 'Unknown')}\n"
            info_text += f"CPU: {specs.get('processor', 'Unknown')}\n"
            info_text += f"Memory: {specs.get('total_ram', 'Unknown')}\n"
            
            # Create message box
            msg = QMessageBox(self)
            msg.setWindowTitle("Device Information")
            msg.setText(info_text)
            msg.setTextFormat(Qt.PlainText)
            msg.setIcon(QMessageBox.Information)
            msg.setStandardButtons(QMessageBox.Ok)
            
            # Make it resizable
            msg.setStyleSheet("""
                QMessageBox {
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 11px;
                }
                QLabel {
                    min-width: 500px;
                    min-height: 300px;
                }
            """)
            
            msg.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get device information: {str(e)}")
    
    def show_comprehensive_device_specs(self):
        """Show comprehensive device specifications in a dedicated window"""
        try:
            # Create a new window for device specs
            device_window = QWidget()
            device_window.setWindowTitle("Comprehensive Device Specifications")
            device_window.setGeometry(150, 150, 800, 600)
            device_window.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)
            
            # Apply consistent styling
            device_window.setStyleSheet("""
                QWidget {
                    background-color: #f8f9fa;
                    font-family: 'Segoe UI', 'Tahoma', sans-serif;
                    font-size: 11px;
                    color: #495057;
                }
                QTextEdit {
                    border: 1px solid #d1d9e6;
                    border-radius: 4px;
                    padding: 10px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 10px;
                    background-color: white;
                    line-height: 1.4;
                }
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 11px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QLabel {
                    font-weight: 600;
                    color: #495057;
                    font-size: 14px;
                    margin-bottom: 10px;
                }
            """)
            
            layout = QVBoxLayout(device_window)
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(15)
            
            # Title
            title = QLabel("🔍 Comprehensive Device Specifications")
            title.setStyleSheet("font-size: 16px; font-weight: 600; color: #495057; margin-bottom: 10px;")
            layout.addWidget(title)
            
            # Text area for specs
            specs_text = QTextEdit()
            specs_text.setReadOnly(True)
            layout.addWidget(specs_text)
            
            # Button layout
            button_layout = QHBoxLayout()
            
            refresh_btn = QPushButton("🔄 Refresh")
            refresh_btn.clicked.connect(lambda: self.populate_device_specs(specs_text))
            
            export_btn = QPushButton("📄 Export")
            export_btn.clicked.connect(lambda: self.export_device_specs(specs_text.toPlainText()))
            
            close_btn = QPushButton("❌ Close")
            close_btn.clicked.connect(device_window.close)
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 11px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            
            button_layout.addWidget(refresh_btn)
            button_layout.addWidget(export_btn)
            button_layout.addStretch()
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)
            
            # Populate initial specs
            self.populate_device_specs(specs_text)
            
            # Show the window
            device_window.show()
            
            # Keep reference to prevent garbage collection
            self.device_window = device_window
            
            self.add_log_message("Opened comprehensive device specifications window")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open device specifications: {str(e)}")
            self.add_log_message(f"❌ Failed to open device specs: {str(e)}")
    
    def populate_device_specs(self, text_widget):
        """Populate the device specs text widget with comprehensive information"""
        import io
        import contextlib
        from datetime import datetime
        
        try:
            # Capture output from device specs functions
            output = io.StringIO()
            
            with contextlib.redirect_stdout(output):
                print("🔍 COMPREHENSIVE DEVICE SPECIFICATIONS 🔍")
                print("="*80)
                print(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("="*80)
                print()
                
                # Call all device spec functions
                try:
                    get_system_info()
                    print()
                    get_cpu_info()
                    print()
                    get_memory_info()
                    print()
                    get_disk_info()
                    print()
                    get_gpu_info()
                    print()
                    get_network_info()
                    print()
                    get_battery_info()
                    print()
                    get_sensors_info()
                    print()
                except Exception as e:
                    print(f"Error collecting some specifications: {e}")
                
                print("="*80)
                print("✅ Device specification scan completed!")
                print("="*80)
            
            # Set the text content
            text_widget.setPlainText(output.getvalue())
            
            # Auto-scroll to top
            text_widget.verticalScrollBar().setValue(0)
            
        except Exception as e:
            error_msg = f"Error gathering device specifications: {str(e)}\n\n"
            error_msg += "This might be due to missing dependencies.\n"
            error_msg += "Try running: pip install psutil GPUtil py-cpuinfo"
            text_widget.setPlainText(error_msg)
    
    def export_device_specs(self, specs_text):
        """Export device specifications to a text file"""
        try:
            from datetime import datetime
            
            # Create output directory if it doesn't exist
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"device_specifications_{timestamp}.txt"
            filepath = os.path.join(output_dir, filename)
            
            # Write specifications to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(specs_text)
            
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Device specifications exported to:\n{os.path.abspath(filepath)}"
            )
            
            self.add_log_message(f"Device specifications exported to: {filepath}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export specifications: {str(e)}")
            self.add_log_message(f"❌ Failed to export device specs: {str(e)}")
    
    def refresh_status(self):
        """Refresh the status display"""
        try:
            # Refresh folder count if folder is selected
            if self.selected_folder and os.path.exists(self.selected_folder):
                image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
                files = [f for f in os.listdir(self.selected_folder) 
                        if os.path.isfile(os.path.join(self.selected_folder, f)) and 
                        any(f.lower().endswith(ext) for ext in image_extensions)]
                
                self.total_files = len(files)
                self.status_panel.log_count.setText(f"Total Files : {self.total_files}")
                self.status_panel.selected_folder.setText(f"Select Folder : {os.path.basename(self.selected_folder)}")
            
            # Refresh model info
            if self.selected_model:
                self.status_panel.model_info.setText(f"AI Model : {os.path.basename(self.selected_model)}")
            
            # Update process status
            if hasattr(self, 'processing_thread') and self.processing_thread and self.processing_thread.isRunning():
                self.status_panel.process_status.setText("Process Status : Processing")
            else:
                self.status_panel.process_status.setText("Process Status : Standby")
            
            # Refresh system specifications
            self.status_panel.refresh_system_specs()
            
            self.add_log_message("Status refreshed")
            
        except Exception as e:
            self.add_log_message(f"❌ Error refreshing status: {str(e)}")

    def update_config_table(self):
        """Update the configuration table with current values"""
        if hasattr(self, 'config_table'):
            # Update table with current config values
            current_config = self.get_current_config()
            
            for row in range(self.config_table.rowCount()):
                param = self.config_table.item(row, 0).text()
                if param == "Image Size":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("imgsz", "12800")))
                elif param == "Confidence":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("conf", "0.2")))
                elif param == "IOU Threshold":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("iou", "0.2")))
                elif param == "Max Detection":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("max_det", "10000")))
                elif param == "Line Width":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("line_width", "3")))
                elif param == "Device":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("device", "auto")))
                elif param == "Convert KML":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("convert_kml", "false")))
                elif param == "Convert SHP":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("convert_shp", "true")))
                elif param == "Show Labels":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("show_labels", "true")))
                elif param == "Show Confidence":
                    self.config_table.setItem(row, 1, QTableWidgetItem(current_config.get("show_conf", "false")))
    
    def sync_config_with_ui(self):
        """Synchronize configuration with UI elements"""
        # Update file panel options based on config
        if hasattr(self, 'file_panel') and hasattr(self, 'config'):
            self.file_panel.save_annotated.setChecked(self.config.get("save_annotated", "true") == "true")
            self.file_panel.export_kml.setChecked(self.config.get("convert_kml", "false") == "true")
            self.file_panel.export_shp.setChecked(self.config.get("convert_shp", "true") == "true")
        
        # Update configuration table
        self.update_config_table()
