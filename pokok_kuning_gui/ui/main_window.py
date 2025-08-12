from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QCheckBox, QProgressBar, QComboBox, QSlider, QGroupBox, 
    QRadioButton, QSpinBox, QMessageBox, QTextEdit, QDoubleSpinBox,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QLinearGradient, QPainter

import os
import sys
import time
import json

from utils.config_manager import load_config, save_config, get_model_names
from core.processor import ImageProcessor

class ModernCard(QFrame):
    """Custom modern card widget with rounded corners and shadow effect"""
    def __init__(self, title="", icon_text=""):
        super().__init__()
        self.title = title
        self.icon_text = icon_text
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        # Create title bar with icon
        title_layout = QHBoxLayout()
        if self.icon_text:
            icon_label = QLabel(self.icon_text)
            icon_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    color: #2196F3;
                    margin-right: 8px;
                }
            """)
            title_layout.addWidget(icon_label)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Create main content layout
        self.content_layout = QVBoxLayout()
        self.content_layout.addLayout(title_layout)
        self.content_layout.addSpacing(16)
        
        self.setLayout(self.content_layout)
    
    def add_content(self, widget):
        """Add content widget to the card"""
        self.content_layout.addWidget(widget)

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
        
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("Pokok Kuning Desktop App")
        self.setGeometry(100, 100, 1000, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
        """)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.setCentralWidget(central_widget)
        
        # Load configuration
        self.config = load_config()
        
        # Initialize selected folder
        self.selected_folder = None
        
        # Load last used folder if available (will be set after UI creation)
        self.last_folder_from_config = self.config.get("last_folder_path") if self.config.get("last_folder_path") and os.path.exists(self.config.get("last_folder_path")) else None
        
        # Create header
        self.create_header(main_layout)
        
        # Create main content area with cards
        content_layout = QHBoxLayout()
        
        # Left column
        left_column = QVBoxLayout()
        left_column.setSpacing(20)
        
        # Folder Selection Card
        self.create_folder_selection_card(left_column)
        
        # Annotation Settings Card
        self.create_annotation_settings_card(left_column)
        
        content_layout.addLayout(left_column)
        
        # Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(20)
        
        # AI Model Configuration Card
        self.create_ai_model_config_card(right_column)
        
        content_layout.addLayout(right_column)
        
        main_layout.addLayout(content_layout)
        
        # Create progress dialog (hidden initially)
        self.create_progress_section()
        
        # Initialize variables
        self.processing_thread = None
        self.total_processed = 0
        self.total_files = 0
        self.total_abnormal = 0
        self.total_normal = 0
        
        # Load last used folder after UI is fully created
        if self.last_folder_from_config:
            self.set_folder_path(self.last_folder_from_config)
        
    def create_header(self, parent_layout):
        """Create modern header with gradient background"""
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2196F3, stop:1 #1976D2);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        header_widget.setFixedHeight(80)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 20)
        
        # App title
        title_label = QLabel("Pokok Kuning Desktop App")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        parent_layout.addWidget(header_widget)
        
    def create_folder_selection_card(self, parent_layout):
        """Create modern folder selection card"""
        card = ModernCard("Folder Selection", "📁")
        
        # Folder input area
        folder_input_layout = QHBoxLayout()
        
        # Initial folder display (will be updated later if there's a saved folder)
        self.folder_path_input = QLabel("No folder selected")
        self.folder_path_input.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                padding: 12px;
                background-color: #fafafa;
                color: #666666;
                min-height: 20px;
            }
        """)
        folder_input_layout.addWidget(self.folder_path_input)
        
        browse_button = QPushButton("Browse")
        browse_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        browse_button.clicked.connect(self.select_folder)
        folder_input_layout.addWidget(browse_button)
        
        card.add_content(self.create_layout_widget(folder_input_layout))
        
        # Save annotated file checkbox
        self.save_annotated_checkbox = QCheckBox("Save Annotated File")
        self.save_annotated_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #333333;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2196F3;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }
        """)
        default_save_annotated = self.config.get("save_annotated") if self.config.get("save_annotated") else "true"
        self.save_annotated_checkbox.setChecked(default_save_annotated == "true")
        card.add_content(self.save_annotated_checkbox)
        
        # Results area
        results_label = QLabel("Results will appear here after conversion")
        results_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                padding: 20px;
                background-color: #fafafa;
                color: #999999;
                text-align: center;
                min-height: 60px;
            }
        """)
        results_label.setAlignment(Qt.AlignCenter)
        card.add_content(results_label)
        
        parent_layout.addWidget(card)
        
    def create_ai_model_config_card(self, parent_layout):
        """Create modern AI model configuration card"""
        card = ModernCard("AI Model Configuration", "🔧")
        
        # Model AI dropdown
        model_layout = self.create_labeled_widget("Model AI", QComboBox())
        self.model_combo = model_layout.findChild(QComboBox)
        model_names = get_model_names()
        self.model_combo.addItems(model_names)
        default_model = self.config.get("model") if self.config.get("model") else "yolov8n-pokok-kuning"
        if default_model in model_names:
            self.model_combo.setCurrentText(default_model)
        self.model_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iIzMzMyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+);
            }
        """)
        card.add_content(model_layout)
        
        # Status Blok radio buttons
        status_label = QLabel("Status Blok")
        status_label.setStyleSheet("font-weight: bold; color: #333333; margin-top: 16px;")
        card.add_content(status_label)
        
        status_layout = QHBoxLayout()
        self.status_full_radio = QRadioButton("Full Blok")
        self.status_half_radio = QRadioButton("Setengah Blok")
        
        default_status = self.config.get("status_blok") if self.config.get("status_blok") else "Full Blok"
        if default_status == "Full Blok":
            self.status_full_radio.setChecked(True)
        else:
            self.status_half_radio.setChecked(True)
            
        for radio in [self.status_full_radio, self.status_half_radio]:
            radio.setStyleSheet("""
                QRadioButton {
                    font-size: 14px;
                    color: #333333;
                    spacing: 8px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #2196F3;
                    border-radius: 9px;
                }
                QRadioButton::indicator:checked {
                    background-color: #2196F3;
                    border: 2px solid #2196F3;
                }
            """)
            status_layout.addWidget(radio)
        
        card.add_content(self.create_layout_widget(status_layout))
        
        # Image Size dropdown
        imgsize_layout = self.create_labeled_widget("Image Size", QComboBox())
        self.imgsz_combo = imgsize_layout.findChild(QComboBox)
        self.imgsz_combo.addItems(["640", "1280", "1920", "9024", "12800"])
        default_imgsz = self.config.get("imgsz") if self.config.get("imgsz") else "12800"
        if default_imgsz in ["640", "1280", "1920", "9024", "12800"]:
            self.imgsz_combo.setCurrentText(default_imgsz)
        self.imgsz_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                min-height: 20px;
            }
        """)
        card.add_content(imgsize_layout)
        
        # IOU Threshold
        iou_layout = self.create_labeled_widget("IOU Threshold", QDoubleSpinBox())
        self.iou_slider = iou_layout.findChild(QDoubleSpinBox)
        self.iou_slider.setRange(0.0, 1.0)
        self.iou_slider.setSingleStep(0.1)
        default_iou = float(self.config.get("iou", 0.2))
        self.iou_slider.setValue(default_iou)
        self.iou_slider.setStyleSheet("""
            QDoubleSpinBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                min-height: 20px;
            }
        """)
        card.add_content(iou_layout)
        
        # Conversion checkboxes
        conversion_layout = QHBoxLayout()
        
        self.kml_checkbox = QCheckBox("Convert to KML")
        default_kml = self.config.get("convert_kml") if self.config.get("convert_kml") else "false"
        self.kml_checkbox.setChecked(default_kml == "true")
        
        self.shp_checkbox = QCheckBox("Convert to SHP")
        default_shp = self.config.get("convert_shp") if self.config.get("convert_shp") else "true"
        self.shp_checkbox.setChecked(default_shp == "true")
        
        for checkbox in [self.kml_checkbox, self.shp_checkbox]:
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 14px;
                    color: #333333;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #2196F3;
                    border-radius: 4px;
                }
                QCheckBox::indicator:checked {
                    background-color: #2196F3;
                }
            """)
            conversion_layout.addWidget(checkbox)
        
        card.add_content(self.create_layout_widget(conversion_layout))
        
        # Confidence Threshold
        conf_layout = self.create_labeled_widget("Confidence Threshold", QDoubleSpinBox())
        self.conf_slider = conf_layout.findChild(QDoubleSpinBox)
        self.conf_slider.setRange(0.0, 1.0)
        self.conf_slider.setSingleStep(0.1)
        default_conf = float(self.config.get("conf", 0.2))
        self.conf_slider.setValue(default_conf)
        self.conf_slider.setStyleSheet("""
            QDoubleSpinBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                min-height: 20px;
            }
        """)
        card.add_content(conf_layout)
        
        # Settings buttons layout
        settings_buttons_layout = QHBoxLayout()
        
        # Save Settings button
        save_settings_button = QPushButton("💾 Save Settings")
        save_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
                margin-top: 16px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
        """)
        save_settings_button.clicked.connect(self.save_configuration)
        settings_buttons_layout.addWidget(save_settings_button)
        
        # Reset Settings button
        reset_settings_button = QPushButton("🔄 Reset Settings")
        reset_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
                margin-top: 16px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        reset_settings_button.clicked.connect(self.reset_to_defaults)
        settings_buttons_layout.addWidget(reset_settings_button)
        
        card.add_content(self.create_layout_widget(settings_buttons_layout))
        
        parent_layout.addWidget(card)
        
    def create_annotation_settings_card(self, parent_layout):
        """Create modern annotation settings card"""
        card = ModernCard("Annotation Settings", "✏️")
        
        # Max Detection
        max_det_layout = self.create_labeled_widget("Max Detection", QSpinBox())
        self.max_det_input = max_det_layout.findChild(QSpinBox)
        self.max_det_input.setRange(1, 50000)
        default_max_det = int(self.config.get("max_det", 10000))
        self.max_det_input.setValue(default_max_det)
        self.max_det_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                min-height: 20px;
            }
        """)
        card.add_content(max_det_layout)
        
        # Line Width
        line_width_layout = self.create_labeled_widget("Line Width", QSpinBox())
        self.line_width_input = line_width_layout.findChild(QSpinBox)
        self.line_width_input.setRange(1, 10)
        default_line_width = int(self.config.get("line_width", 3))
        self.line_width_input.setValue(default_line_width)
        self.line_width_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                min-height: 20px;
            }
        """)
        card.add_content(line_width_layout)
        
        # Display checkboxes
        display_layout = QHBoxLayout()
        
        self.show_labels_checkbox = QCheckBox("Show Labels")
        default_show_labels = self.config.get("show_labels") if self.config.get("show_labels") else "true"
        self.show_labels_checkbox.setChecked(default_show_labels == "true")
        
        self.show_conf_checkbox = QCheckBox("Show Threshold")
        default_show_conf = self.config.get("show_conf") if self.config.get("show_conf") else "false"
        self.show_conf_checkbox.setChecked(default_show_conf == "true")
        
        for checkbox in [self.show_labels_checkbox, self.show_conf_checkbox]:
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 14px;
                    color: #333333;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #2196F3;
                    border-radius: 4px;
                }
                QCheckBox::indicator:checked {
                    background-color: #2196F3;
                }
            """)
            display_layout.addWidget(checkbox)
        
        card.add_content(self.create_layout_widget(display_layout))
        
        # Start Processing button
        start_button = QPushButton("🚀 Start Processing")
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 16px 24px;
                font-size: 16px;
                font-weight: bold;
                margin-top: 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        start_button.clicked.connect(self.start_conversion)
        card.add_content(start_button)
        
        parent_layout.addWidget(card)
        
    def create_labeled_widget(self, label_text, widget):
        """Create a labeled widget with consistent styling"""
        layout = QVBoxLayout()
        
        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333333;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(label)
        layout.addWidget(widget)
        
        return self.create_layout_widget(layout)
        
    def create_layout_widget(self, layout):
        """Create a widget from a layout"""
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    def set_folder_path(self, folder_path):
        """Set folder path and update UI state properly"""
        if not folder_path or not os.path.exists(folder_path):
            return
            
        self.selected_folder = folder_path
        
        # Check if folder contains .tif files
        try:
            has_tiff_files = any(f.lower().endswith(('.tif', '.tiff')) for f in os.listdir(folder_path))
            
            if has_tiff_files:
                self.folder_path_input.setText(f"Selected Folder: {folder_path}")
                self.folder_path_input.setStyleSheet("""
                    QLabel {
                        border: 2px solid #2196F3;
                        border-radius: 8px;
                        padding: 12px;
                        background-color: #e3f2fd;
                        color: #1976D2;
                        min-height: 20px;
                    }
                """)
                self.save_annotated_checkbox.setEnabled(True)
            else:
                self.folder_path_input.setText("The folder does not contain any .tif files.")
                self.folder_path_input.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #cccccc;
                        border-radius: 8px;
                        padding: 12px;
                        background-color: #fafafa;
                        color: #666666;
                        min-height: 20px;
                    }
                """)
                self.save_annotated_checkbox.setEnabled(False)
                self.selected_folder = None  # Reset if no valid files
        except Exception as e:
            print(f"Error checking folder contents: {e}")
            self.selected_folder = None

    def create_progress_section(self):
        self.progress_dialog = QWidget(self)
        self.progress_dialog.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.progress_dialog.setWindowTitle("Progress Convert")
        self.progress_dialog.setGeometry(200, 200, 500, 400)
        self.progress_dialog.hide()
        
        layout = QVBoxLayout(self.progress_dialog)
        
        # Timer label
        self.timer_label = QLabel("Elapsed Time: 0.00 seconds")
        layout.addWidget(self.timer_label)
        
        layout.addWidget(QLabel("Processing Progress:"))
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Progress text
        self.progress_text = QLabel("0 of 0 images processed")
        layout.addWidget(self.progress_text)
        
        # Activity log
        layout.addWidget(QLabel("Activity Log:"))
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        layout.addWidget(self.activity_log)
        
        # Annotated progress section (initially hidden)
        self.annotated_group = QGroupBox("Saving Annotated Images")
        annotated_layout = QVBoxLayout()
        
        self.annotated_progress_bar = QProgressBar()
        annotated_layout.addWidget(self.annotated_progress_bar)
        
        self.annotated_progress_text = QLabel("0 of 0 images processed")
        annotated_layout.addWidget(self.annotated_progress_text)
        
        self.annotated_activity_log = QTextEdit()
        self.annotated_activity_log.setReadOnly(True)
        annotated_layout.addWidget(self.annotated_activity_log)
        
        self.annotated_group.setLayout(annotated_layout)
        layout.addWidget(self.annotated_group)
        self.annotated_group.hide()
    
    def select_folder(self):
        # Start from last used folder if available
        start_dir = self.selected_folder if self.selected_folder and os.path.exists(self.selected_folder) else ""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", start_dir)
        
        if folder_path:
            # Use the centralized method to set and validate folder
            self.set_folder_path(folder_path)
            
            # Auto-save the folder path if it's valid
            if self.selected_folder:  # Only save if validation passed
                current_config = self.get_current_config()
                current_config["last_folder_path"] = folder_path
                save_config(current_config)
    
    def start_conversion(self):
        if not self.selected_folder:
            print("No folder selected for conversion")
            return
        
        print(f"Starting conversion for folder: {self.selected_folder}")
        
        # Show progress dialog
        self.progress_dialog.show()
        self.progress_bar.setValue(0)
        self.progress_text.setText("Starting conversion...")
        self.activity_log.clear()
        
        # Show/hide annotated section based on checkbox
        if self.save_annotated_checkbox.isChecked():
            self.annotated_group.show()
        else:
            self.annotated_group.hide()
        
        # Get current configuration
        config = self.get_current_config()
        
        # Start timer
        self.start_time = time.time()
        self.timer_thread = QThread()
        self.timer_thread.started.connect(self.update_timer)
        self.timer_thread.start()
        
        # Start processing in a separate thread
        print("Creating processing thread...")
        self.processing_thread = ProcessingThread(self.selected_folder, config)
        self.processing_thread.progress_update.connect(self.update_progress)
        self.processing_thread.processing_finished.connect(self.processing_complete)
        print("Starting processing thread...")
        self.processing_thread.start()
    
    def update_timer(self):
        while self.processing_thread and self.processing_thread.isRunning():
            elapsed_time = time.time() - self.start_time
            if elapsed_time < 60:
                self.timer_label.setText(f"Elapsed Time: {elapsed_time:.2f} seconds")
            else:
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                self.timer_label.setText(f"Elapsed Time: {minutes:02}:{seconds:02} minutes")
            QThread.msleep(100)  # Update every 0.1 seconds
    
    def update_progress(self, progress_data):
        processed = progress_data.get("processed", 0)
        total = progress_data.get("total", 1)
        current_file = progress_data.get("current_file", "N/A")
        status = progress_data.get("status", "Processing")
        abnormal_count = progress_data.get("abnormal_count", 0)
        normal_count = progress_data.get("normal_count", 0)
        
        self.total_abnormal += abnormal_count
        self.total_normal += normal_count
        
        # Update progress bar
        progress = processed / total if total > 0 else 0
        self.progress_bar.setValue(int(progress * 100))
        self.progress_text.setText(f"{processed} of {total} images processed")
        
        # Update activity log
        self.activity_log.append(f"{current_file} - {abnormal_count} abnormal, {normal_count} normal - {status}")
        
        # Save total files count for results
        self.total_files = total
    
    def processing_complete(self, results):
        try:
            print("Processing completed, handling results...")
            self.timer_thread.terminate()
            
            # Check if there was an error
            if "error" in results:
                print(f"Processing failed with error: {results['error']}")
                # Show error message
                QMessageBox.critical(self, "Processing Error", 
                                   f"Processing failed:\n{results['error']}")
                self.progress_dialog.hide()
                return
            
            self.total_processed = results.get("successful_processed", 0)
            self.total_files = results.get("total_files", 0)
            self.final_time = results.get("total_time", 0)
            
            # Show completion message
            folder_name = os.path.basename(self.selected_folder)
            
            print(f"Processing completed successfully: {self.total_processed}/{self.total_files} files")
            
            # Show completion message in a popup
            QMessageBox.information(self, "Conversion Complete", 
                                  f"The folder '{folder_name}' has been converted successfully!\n\n"
                                  f"Processed: {self.total_processed}/{self.total_files} files")
            
            # Hide progress dialog after 3 seconds
            QTimer.singleShot(3000, self.progress_dialog.hide)
            
        except Exception as e:
            print(f"❌ Error in processing_complete: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Error handling results: {str(e)}")
            self.progress_dialog.hide()
    
    def show_results(self):
        msg = QMessageBox()
        msg.setWindowTitle("Conversion Results")
        
        # Format time display
        if self.final_time < 60:
            time_display = f"{self.final_time:.2f} seconds"
        else:
            minutes = int(self.final_time // 60)
            seconds = int(self.final_time % 60)
            time_display = f"{minutes:02}:{seconds:02} minutes"
        
        result_text = f"""
        Convert Time: {time_display}
        Images Processed: {self.total_processed} / {self.total_files}
        
        Pokok Normal: {self.total_normal}
        Pokok Abnormal: {self.total_abnormal}
        """
        
        msg.setText(result_text)
        msg.exec_()
    
    def save_configuration(self):
        config = self.get_current_config()
        if save_config(config):
            # Show success message in a popup
            QMessageBox.information(self, "Success", "Configuration has been saved successfully!")
    
    def reset_to_defaults(self):
        """Reset all settings to default values"""
        # Show confirmation dialog
        reply = QMessageBox.question(
            self, 
            "Reset Settings", 
            "Are you sure you want to reset all settings to default values?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset all UI elements to default values
            self.reset_ui_to_defaults()
            
            # Save default configuration to database
            default_config = self.get_default_config()
            if save_config(default_config):
                QMessageBox.information(self, "Reset Complete", "All settings have been reset to default values!")
    
    def reset_ui_to_defaults(self):
        """Reset all UI elements to their default values"""
        # Get available models
        model_names = get_model_names()
        default_model = model_names[0] if model_names else "yolov8n-pokok-kuning"
        
        # Reset Model AI
        if default_model in model_names:
            self.model_combo.setCurrentText(default_model)
        
        # Reset Status Blok
        self.status_full_radio.setChecked(True)
        self.status_half_radio.setChecked(False)
        
        # Reset Image Size
        self.imgsz_combo.setCurrentText("12800")
        
        # Reset IOU Threshold  
        self.iou_slider.setValue(0.2)
        
        # Reset conversion checkboxes
        self.kml_checkbox.setChecked(False)
        self.shp_checkbox.setChecked(True)
        
        # Reset Confidence Threshold
        self.conf_slider.setValue(0.2)
        
        # Reset Max Detection
        self.max_det_input.setValue(10000)
        
        # Reset Line Width
        self.line_width_input.setValue(3)
        
        # Reset display checkboxes
        self.show_labels_checkbox.setChecked(True)
        self.show_conf_checkbox.setChecked(False)
        
        # Reset Save Annotated File
        self.save_annotated_checkbox.setChecked(True)
        self.save_annotated_checkbox.setEnabled(False)
        
        # Clear folder selection
        self.selected_folder = None
        self.folder_path_input.setText("No folder selected")
        self.folder_path_input.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                padding: 12px;
                background-color: #fafafa;
                color: #666666;
                min-height: 20px;
            }
        """)
    
    def get_default_config(self):
        """Get default configuration values"""
        model_names = get_model_names()
        default_model = model_names[0] if model_names else "yolov8n-pokok-kuning"
        
        return {
            "model": default_model,
            "imgsz": "12800",
            "iou": "0.2",
            "conf": "0.2",
            "convert_shp": "true",
            "convert_kml": "false",
            "max_det": "10000",
            "line_width": "3",
            "show_labels": "true",
            "show_conf": "false",
            "status_blok": "Full Blok",
            "save_annotated": "true",
            "last_folder_path": None
        }
    
    def get_current_config(self):
        return {
            "model": self.model_combo.currentText(),
            "imgsz": self.imgsz_combo.currentText(),
            "iou": str(self.iou_slider.value()),
            "conf": str(self.conf_slider.value()),
            "convert_shp": "true" if self.shp_checkbox.isChecked() else "false",
            "convert_kml": "true" if self.kml_checkbox.isChecked() else "false",
            "max_det": str(self.max_det_input.value()),
            "line_width": str(self.line_width_input.value()),
            "show_labels": "true" if self.show_labels_checkbox.isChecked() else "false",
            "show_conf": "true" if self.show_conf_checkbox.isChecked() else "false",
            "status_blok": "Full Blok" if self.status_full_radio.isChecked() else "Setengah Blok",
            "save_annotated": "true" if self.save_annotated_checkbox.isChecked() else "false",
            "annotated_folder": os.path.join(self.selected_folder, "annotated") if self.selected_folder and self.save_annotated_checkbox.isChecked() else None,
            "last_folder_path": self.selected_folder
        }