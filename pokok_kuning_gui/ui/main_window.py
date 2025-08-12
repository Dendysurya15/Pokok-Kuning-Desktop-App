from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QCheckBox, QProgressBar, QComboBox, QSlider, QGroupBox, 
    QRadioButton, QSpinBox, QMessageBox, QTextEdit, QDoubleSpinBox,
    QFrame, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QSize
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QLinearGradient, QPainter, QIcon
from PyQt5.QtSvg import QSvgWidget

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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
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
        title_layout.setSpacing(12)  # Added spacing between icon and title
        if self.icon_text:
            icon_label = QLabel(self.icon_text)
            icon_label.setStyleSheet("""
                QLabel {
                    font-size: 20px;
                    color: #2196F3;
                    margin-right: 10px;
                }
            """)
            title_layout.addWidget(icon_label)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
                margin-left: 5px;
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Create main content layout
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(16)  # Increased spacing between content elements
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.addLayout(title_layout)
        self.content_layout.addSpacing(20)  # Added more space after title
        
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
        
    def get_asset_path(self, filename):
        """Get the full path to an asset file"""
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            return os.path.join(sys._MEIPASS, 'assets', 'img', filename)
        else:
            # Running as script
            return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'img', filename)
        
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("Pokok Kuning Desktop App")
        self.setGeometry(100, 100, 1000, 800)
        self.setMinimumSize(800, 600)  # Set minimum window size
        
        # Set window icon
        icon_path = self.get_asset_path('logo.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Set background image
        bg_path = self.get_asset_path('background.jpg')
        if os.path.exists(bg_path):
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-image: url({bg_path});
                    background-repeat: no-repeat;
                    background-position: center;
                    background-attachment: fixed;
                }}
                QWidget {{
                    background-color: rgba(245, 245, 245, 0.9);
                }}
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f5;
                }
            """)
        
        # Create central widget and layout
        central_scroll = QScrollArea()
        central_scroll.setWidgetResizable(True)
        central_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        central_scroll.setWidget(central_widget)
        self.setCentralWidget(central_scroll)
        
        # Load configuration
        self.config = load_config()
        
        # Initialize selected folder
        self.selected_folder = None
        
        # Load last used folder if available (will be set after UI creation)
        self.last_folder_from_config = self.config.get("last_folder_path") if self.config.get("last_folder_path") and os.path.exists(self.config.get("last_folder_path")) else None
        
        # Create header
        self.create_header(main_layout)
        
        # Create main content area with cards - Responsive layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Left column
        left_column = QVBoxLayout()
        left_column.setSpacing(20)

        # Folder Selection Card
        self.create_folder_selection_card(left_column)

        # Annotation Settings Card
        self.create_annotation_settings_card(left_column)

        left_container = QWidget()
        left_container.setLayout(left_column)
        left_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        # Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(20)

        # AI Model Configuration Card
        self.create_ai_model_config_card(right_column)

        right_container = QWidget()
        right_container.setLayout(right_column)
        right_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        content_layout.addWidget(left_container, 1)
        content_layout.addWidget(right_container, 1)
        content_layout.setStretch(0, 1)
        content_layout.setStretch(1, 1)
        content_layout.setAlignment(Qt.AlignTop)

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
        
        # Initialize model path display
        self.update_model_path_display()
        
        # Add initial log message
        self.add_log_message("Application started successfully")
        self.add_log_message(f"Available models: {', '.join(get_model_names())}")
        
    def create_header(self, parent_layout):
        """Create modern header with gradient background and logo"""
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2196F3, stop:1 #1976D2);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        header_widget.setFixedHeight(120)  # Increased height for better spacing
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 20)
        header_layout.setSpacing(20)  # Added spacing between elements
        
        # Logo
        logo_path = self.get_asset_path('logo.png')
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            # Scale logo to fit header height with proper margins
            scaled_pixmap = pixmap.scaledToHeight(70, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setFixedWidth(80)  # Fixed width to prevent overlap
            header_layout.addWidget(logo_label)
        
        # App title with better spacing
        title_label = QLabel("Digital Architect — PT Sawit Sumbernan Sarana")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 26px;
                font-weight: bold;
                background-color: transparent;
                margin-left: 10px;
                margin-right: 10px;
            }
        """)
        title_label.setMinimumWidth(300)  # Ensure minimum width for title
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Show Log button with better positioning
        show_log_button = QPushButton("Show Progress")
        show_log_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
                min-height: 40px;
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
        
    def create_folder_selection_card(self, parent_layout):
        """Create modern folder selection card"""
        card = ModernCard("Folder Selection", "")
        
        # Folder input area with better spacing
        folder_input_layout = QHBoxLayout()
        folder_input_layout.setSpacing(15)  # Added spacing between elements
        
        # Initial folder display (will be updated later if there's a saved folder)
        self.folder_path_input = QLabel("No folder selected")
        self.folder_path_input.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                padding: 15px;
                background-color: #fafafa;
                color: #666666;
                min-height: 25px;
                font-size: 13px;
                margin-right: 10px;
            }
        """)
        self.folder_path_input.setWordWrap(True)  # Enable word wrapping for long paths
        folder_input_layout.addWidget(self.folder_path_input, 1)  # Give it more space
        
        browse_button = QPushButton("Browse")
        
        # Add folder icon to browse button
        folder_icon_path = self.get_asset_path('folder_icon.svg')
        if os.path.exists(folder_icon_path):
            browse_button.setIcon(QIcon(folder_icon_path))
            browse_button.setIconSize(QSize(18, 18))  # Slightly larger icon
        
        browse_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 25px;
                font-weight: bold;
                font-size: 13px;
                min-width: 100px;
                min-height: 25px;
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
        
        # Save annotated file checkbox with better spacing
        self.save_annotated_checkbox = QCheckBox("Save Annotated File")
        self.save_annotated_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #333333;
                spacing: 10px;
                margin-top: 15px;
                margin-bottom: 15px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
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
        
        # Results area with better visibility
        results_label = QLabel("Results will appear here after conversion")
        results_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                padding: 25px;
                background-color: #fafafa;
                color: #999999;
                text-align: center;
                min-height: 80px;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        results_label.setAlignment(Qt.AlignCenter)
        results_label.setWordWrap(True)  # Enable word wrapping
        card.add_content(results_label)
        
        parent_layout.addWidget(card)
        
    def create_ai_model_config_card(self, parent_layout):
        """Create modern AI model configuration card"""
        card = ModernCard("AI Model Configuration", "")
        
        # Model AI input area (similar to folder selection) with better spacing
        model_input_layout = QHBoxLayout()
        model_input_layout.setSpacing(15)  # Added spacing between elements
        
        # Model path display with better visibility
        self.model_path_input = QLabel("yolov8n-pokok-kuning.pt")
        self.model_path_input.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                padding: 15px;
                background-color: #fafafa;
                color: #666666;
                min-height: 25px;
                font-size: 13px;
                margin-right: 10px;
            }
        """)
        self.model_path_input.setWordWrap(True)  # Enable word wrapping for long paths
        model_input_layout.addWidget(self.model_path_input, 1)  # Give it more space
        
        # Browse button for model with better sizing
        browse_model_button = QPushButton("Browse")
        browse_model_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 25px;
                font-weight: bold;
                font-size: 13px;
                min-width: 100px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        browse_model_button.clicked.connect(self.select_model)
        model_input_layout.addWidget(browse_model_button)
        
        card.add_content(self.create_layout_widget(model_input_layout))
        
        # Model AI dropdown (kept for backward compatibility) with better spacing
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
                padding: 12px 16px;
                background-color: white;
                min-height: 25px;
                font-size: 13px;
                margin-top: 8px;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iIzMzMyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+);
            }
        """)
        # Connect model combo change to update model path display
        self.model_combo.currentTextChanged.connect(self.on_model_combo_changed)
        card.add_content(model_layout)
        
        # Status Blok radio buttons with better spacing
        status_label = QLabel("Status Blok")
        status_label.setStyleSheet("""
            font-weight: bold; 
            color: #333333; 
            margin-top: 20px; 
            margin-bottom: 10px;
            font-size: 14px;
        """)
        card.add_content(status_label)
        
        status_layout = QHBoxLayout()
        status_layout.setSpacing(20)  # Added spacing between radio buttons
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
                    spacing: 12px;
                    margin: 5px 0px;
                }
                QRadioButton::indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #2196F3;
                    border-radius: 10px;
                }
                QRadioButton::indicator:checked {
                    background-color: #2196F3;
                    border: 2px solid #2196F3;
                }
            """)
            status_layout.addWidget(radio)
        
        card.add_content(self.create_layout_widget(status_layout))
        
        # Image Size input with better spacing
        imgsize_layout = self.create_labeled_widget("Image Size", QSpinBox())
        self.imgsz_input = imgsize_layout.findChild(QSpinBox)
        self.imgsz_input.setRange(1000, 99999)
        self.imgsz_input.setValue(12800)  # Default value
        default_imgsz = int(self.config.get("imgsz")) if self.config.get("imgsz") else 12800
        if 1000 <= default_imgsz <= 99999:
            self.imgsz_input.setValue(default_imgsz)
        self.imgsz_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px 16px;
                background-color: white;
                min-height: 25px;
                font-size: 13px;
                margin-top: 8px;
            }
        """)
        card.add_content(imgsize_layout)
        
        # IOU Threshold with better spacing
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
                padding: 12px 16px;
                background-color: white;
                min-height: 25px;
                font-size: 13px;
                margin-top: 8px;
            }
        """)
        card.add_content(iou_layout)
        
        # Conversion checkboxes with better spacing
        conversion_layout = QHBoxLayout()
        conversion_layout.setSpacing(20)  # Added spacing between checkboxes
        
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
                    spacing: 12px;
                    margin: 8px 0px;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #2196F3;
                    border-radius: 4px;
                }
                QCheckBox::indicator:checked {
                    background-color: #2196F3;
                }
            """)
            conversion_layout.addWidget(checkbox)
        
        card.add_content(self.create_layout_widget(conversion_layout))
        
        # Confidence Threshold with better spacing
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
                padding: 12px 16px;
                background-color: white;
                min-height: 25px;
                font-size: 13px;
                margin-top: 8px;
            }
        """)
        card.add_content(conf_layout)
        
        # Settings buttons with better spacing
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(15)  # Added spacing between buttons
        
        save_settings_button = QPushButton("Save Settings")
        save_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 25px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
        """)
        save_settings_button.clicked.connect(self.save_settings)
        settings_layout.addWidget(save_settings_button)
        
        reset_settings_button = QPushButton("Reset Settings")
        reset_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 25px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:pressed {
                background-color: #B71C1C;
            }
        """)
        reset_settings_button.clicked.connect(self.reset_settings)
        settings_layout.addWidget(reset_settings_button)
        
        card.add_content(self.create_layout_widget(settings_layout))
        
        parent_layout.addWidget(card)
        
    def create_annotation_settings_card(self, parent_layout):
        """Create modern annotation settings card"""
        card = ModernCard("Annotation Settings", "")
        
        # Max Detection with better spacing
        max_det_layout = self.create_labeled_widget("Max Detection", QSpinBox())
        self.max_det_input = max_det_layout.findChild(QSpinBox)
        self.max_det_input.setRange(1, 50000)
        default_max_det = int(self.config.get("max_det", 10000))
        self.max_det_input.setValue(default_max_det)
        self.max_det_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px 16px;
                background-color: white;
                min-height: 25px;
                font-size: 13px;
                margin-top: 8px;
            }
        """)
        card.add_content(max_det_layout)
        
        # Line Width with better spacing
        line_width_layout = self.create_labeled_widget("Line Width", QSpinBox())
        self.line_width_input = line_width_layout.findChild(QSpinBox)
        self.line_width_input.setRange(1, 10)
        default_line_width = int(self.config.get("line_width", 3))
        self.line_width_input.setValue(default_line_width)
        self.line_width_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px 16px;
                background-color: white;
                min-height: 25px;
                font-size: 13px;
                margin-top: 8px;
            }
        """)
        card.add_content(line_width_layout)
        
        # Display checkboxes with better spacing
        display_layout = QHBoxLayout()
        display_layout.setSpacing(20)  # Added spacing between checkboxes
        
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
                    spacing: 12px;
                    margin: 8px 0px;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #2196F3;
                    border-radius: 4px;
                }
                QCheckBox::indicator:checked {
                    background-color: #2196F3;
                }
            """)
            display_layout.addWidget(checkbox)
        
        card.add_content(self.create_layout_widget(display_layout))
        
        # Start Processing button with better spacing and sizing
        start_button = QPushButton(" Start Processing")
        
        # Add rocket icon to start button
        rocket_icon_path = self.get_asset_path('rocket_icon.svg')
        if os.path.exists(rocket_icon_path):
            start_button.setIcon(QIcon(rocket_icon_path))
            start_button.setIconSize(QSize(22, 22))  # Slightly larger icon
        
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 18px 28px;
                font-size: 16px;
                font-weight: bold;
                margin-top: 20px;
                margin-bottom: 10px;
                min-height: 50px;
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
        layout.setSpacing(8)  # Added consistent spacing
        
        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333333;
                margin-bottom: 8px;
                font-size: 14px;
            }
        """)
        layout.addWidget(label)
        layout.addWidget(widget)
        
        return self.create_layout_widget(layout)
        
    def create_layout_widget(self, layout):
        """Create a widget from a layout"""
        widget = QWidget()
        widget.setLayout(layout)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
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
                # Truncate long folder paths for better display
                display_path = folder_path
                if len(folder_path) > 50:
                    display_path = "..." + folder_path[-47:]
                
                self.folder_path_input.setText(f"Selected Folder: {display_path}")
                self.folder_path_input.setToolTip(folder_path)  # Show full path on hover
                self.folder_path_input.setStyleSheet("""
                    QLabel {
                        border: 2px solid #2196F3;
                        border-radius: 8px;
                        padding: 15px;
                        background-color: #e3f2fd;
                        color: #1976D2;
                        min-height: 25px;
                        font-size: 13px;
                        margin-right: 10px;
                    }
                """)
                self.save_annotated_checkbox.setEnabled(True)
            else:
                self.folder_path_input.setText("The folder does not contain any .tif files.")
                self.folder_path_input.setToolTip("")  # Clear tooltip
                self.folder_path_input.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #cccccc;
                        border-radius: 8px;
                        padding: 15px;
                        background-color: #fafafa;
                        color: #666666;
                        min-height: 25px;
                        font-size: 13px;
                        margin-right: 10px;
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
        
        # Save Log button
        save_log_button = QPushButton("Save Log")
        save_log_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        save_log_button.clicked.connect(self.save_log)
        layout.addWidget(save_log_button)
        
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
    
    def create_logging_section(self):
        # This function is no longer needed as logging is integrated into the progress dialog
        pass
    
    def add_log_message(self, message):
        """Add a message to the activity log in the progress dialog"""
        timestamp = time.strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        
        # Add to activity log in the progress dialog
        self.activity_log.append(formatted_message)
        
        # Auto-scroll to bottom
        self.activity_log.verticalScrollBar().setValue(
            self.activity_log.verticalScrollBar().maximum()
        )
        
        # Also print to console for debugging
        print(formatted_message)
    
    def clear_log(self):
        """Clear the log display in the progress dialog"""
        self.activity_log.clear()
        self.activity_log.append("=== Digital Architect — PT Sawit Sumbernan Sarana - ACTIVITY LOG ===\n")
        self.activity_log.append(f"Cleared at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.activity_log.append("-" * 50 + "\n")

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
    
    def save_settings(self):
        """Save current settings to configuration"""
        try:
            current_config = self.get_current_config()
            save_config(current_config)
            QMessageBox.information(self, "Success", "Settings saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
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
                # Reset to default values
                self.model_combo.setCurrentText("yolov8n-pokok-kuning")
                self.imgsz_input.setValue(12800)
                self.iou_slider.setValue(0.2)
                self.conf_slider.setValue(0.2)
                self.kml_checkbox.setChecked(False)
                self.shp_checkbox.setChecked(True)
                self.status_full_radio.setChecked(True)
                self.status_half_radio.setChecked(False)
                
                # Update model path display
                self.update_model_path_display()
                
                QMessageBox.information(self, "Success", "Settings reset to default values!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset settings: {str(e)}")

    def select_model(self):
        """Open a file dialog to select a .pt model file."""
        print(f"🔍 [DEBUG] select_model() called")
        
        # Start from model directory if available
        model_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model")
        start_dir = model_folder if os.path.exists(model_folder) else ""
        print(f"🔍 [DEBUG] Start directory: {start_dir}")
        
        model_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File",
            start_dir,
            "Model Files (*.pt);;All Files (*)"
        )
        
        print(f"🔍 [DEBUG] Selected model path: {model_path}")
        
        if model_path:
            print(f"🔍 [DEBUG] Model path exists: {os.path.exists(model_path)}")
            
            # Update the model path display
            self.model_path_input.setText(model_path)
            
            # Extract model name without extension and update combo box
            model_name = os.path.splitext(os.path.basename(model_path))[0]
            print(f"🔍 [DEBUG] Extracted model name: {model_name}")
            
            # Add to combo box if not already there
            if self.model_combo.findText(model_path) == -1:
                self.model_combo.addItem(model_path)
                print(f"🔍 [DEBUG] Added custom model path to combo box: {model_path}")
            
            # Set as current selection
            self.model_combo.setCurrentText(model_path)
            print(f"🔍 [DEBUG] Set current model to: {model_path}")
            
            # Update display
            self.update_model_path_display()
            
            # Auto-save the model path
            current_config = self.get_current_config()
            current_config["model"] = model_path  # Save full path for custom models
            save_config(current_config)
            print(f"🔍 [DEBUG] Saved model path to config: {model_path}")
    
    def on_model_combo_changed(self, text):
        """Update the model path display when the model combo box changes."""
        print(f"🔍 [DEBUG] Model combo changed to: {text}")
        self.update_model_path_display()
    
    def update_model_path_display(self):
        """Update the model path display to show the currently selected model."""
        current_model_name = self.model_combo.currentText()
        print(f"🔍 [DEBUG] update_model_path_display() called with: {current_model_name}")
        
        # Check if it's a custom model (full path)
        if os.path.isabs(current_model_name) or current_model_name.startswith("C:"):
            print(f"🔍 [DEBUG] Custom model detected (full path): {current_model_name}")
            model_path = current_model_name
            
            if os.path.exists(model_path):
                print(f"🔍 [DEBUG] Custom model exists: {model_path}")
                # Truncate long paths for better display
                display_path = model_path
                if len(model_path) > 50:
                    display_path = "..." + model_path[-47:]
                
                self.model_path_input.setText(display_path)
                self.model_path_input.setToolTip(model_path)  # Show full path on hover
                # Reset to normal styling
                self.model_path_input.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #cccccc;
                        border-radius: 8px;
                        padding: 15px;
                        background-color: #fafafa;
                        color: #666666;
                        min-height: 25px;
                        font-size: 13px;
                        margin-right: 10px;
                    }
                """)
            else:
                print(f"🔍 [DEBUG] Custom model NOT found: {model_path}")
                self.model_path_input.setText(f"Model not found: {os.path.basename(model_path)}")
                self.model_path_input.setToolTip("")  # Clear tooltip
                # Show error styling
                self.model_path_input.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #f44336;
                        border-radius: 8px;
                        padding: 15px;
                        background-color: #ffebee;
                        color: #d32f2f;
                        min-height: 25px;
                        font-size: 13px;
                        margin-right: 10px;
                    }
                """)
        else:
            # It's a built-in model name, construct the path
            print(f"🔍 [DEBUG] Built-in model detected: {current_model_name}")
            # Use the same path resolution as get_model_names()
            model_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model")
            model_path = os.path.join(model_folder, f"{current_model_name}.pt")
            print(f"🔍 [DEBUG] Constructed model path: {model_path}")
            
            if os.path.exists(model_path):
                print(f"🔍 [DEBUG] Built-in model exists: {model_path}")
                self.model_path_input.setText(f"{current_model_name}.pt")
                self.model_path_input.setToolTip(model_path)  # Show full path on hover
                # Reset to normal styling
                self.model_path_input.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #cccccc;
                        border-radius: 8px;
                        padding: 15px;
                        background-color: #fafafa;
                        color: #666666;
                        min-height: 25px;
                        font-size: 13px;
                        margin-right: 10px;
                    }
                """)
            else:
                print(f"🔍 [DEBUG] Built-in model NOT found: {model_path}")
                self.model_path_input.setText(f"Model not found: {current_model_name}.pt")
                self.model_path_input.setToolTip("")  # Clear tooltip
                # Show error styling
                self.model_path_input.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #f44336;
                        border-radius: 8px;
                        padding: 15px;
                        background-color: #ffebee;
                        color: #d32f2f;
                        min-height: 25px;
                        font-size: 13px;
                        margin-right: 10px;
                    }
                """)
    
    def start_conversion(self):
        if not self.selected_folder:
            print("No folder selected for conversion")
            return
        
        print(f"Starting conversion for folder: {self.selected_folder}")
        
        # Add log message
        self.add_log_message(f"Starting conversion for folder: {self.selected_folder}")
        
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
        
        # Log configuration
        self.add_log_message(f"Using model: {config.get('model', 'Unknown')}")
        self.add_log_message(f"Image size: {config.get('imgsz', 'Unknown')}")
        self.add_log_message(f"Confidence threshold: {config.get('conf', 'Unknown')}")
        self.add_log_message(f"IOU threshold: {config.get('iou', 'Unknown')}")
        
        # Start timer
        self.start_time = time.time()
        self.timer_thread = QThread()
        self.timer_thread.started.connect(self.update_timer)
        self.timer_thread.start()
        
        # Start processing in a separate thread
        print("Creating processing thread...")
        self.add_log_message("Creating processing thread...")
        self.processing_thread = ProcessingThread(self.selected_folder, config)
        self.processing_thread.progress_update.connect(self.update_progress)
        self.processing_thread.processing_finished.connect(self.processing_complete)
        print("Starting processing thread...")
        self.add_log_message("Starting processing thread...")
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
        
        # Update activity log using new logging function
        log_message = f"Processing {current_file} - {abnormal_count} abnormal, {normal_count} normal - {status}"
        self.add_log_message(log_message)
        
        # Save total files count for results
        self.total_files = total
    
    def processing_complete(self, results):
        try:
            print("Processing completed, handling results...")
            self.add_log_message("Processing completed, handling results...")
            self.timer_thread.terminate()
            
            # Check if there was an error
            if "error" in results:
                error_msg = f"Processing failed with error: {results['error']}"
                print(error_msg)
                self.add_log_message(error_msg)
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
            
            completion_msg = f"Processing completed successfully: {self.total_processed}/{self.total_files} files"
            print(completion_msg)
            self.add_log_message(completion_msg)
            
            # Log final statistics
            self.add_log_message(f"Total processing time: {self.final_time:.2f} seconds")
            self.add_log_message(f"Total abnormal objects: {self.total_abnormal}")
            self.add_log_message(f"Total normal objects: {self.total_normal}")
            self.add_log_message("=" * 50)
            
            # Show completion message in a popup
            QMessageBox.information(self, "Conversion Complete", 
                                  f"The folder '{folder_name}' has been converted successfully!\n\n"
                                  f"Processed: {self.total_processed}/{self.total_files} files")
            
            # Hide progress dialog after 3 seconds
            QTimer.singleShot(3000, self.progress_dialog.hide)
            
        except Exception as e:
            error_msg = f"❌ Error in processing_complete: {str(e)}"
            print(error_msg)
            self.add_log_message(error_msg)
            import traceback
            traceback_msg = f"Traceback: {traceback.format_exc()}"
            print(traceback_msg)
            self.add_log_message(traceback_msg)
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
        self.imgsz_input.setValue(12800)
        
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
            "model_path": self.get_full_model_path(),  # Add full model path
            "imgsz": str(self.imgsz_input.value()),
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
    
    def get_full_model_path(self):
        """Get the full path to the currently selected model"""
        current_model_name = self.model_combo.currentText()
        print(f"🔍 [DEBUG] get_full_model_path() called with: {current_model_name}")
        
        # If it's already a full path, return it
        if os.path.isabs(current_model_name) or current_model_name.startswith("C:"):
            print(f"🔍 [DEBUG] Custom model path detected: {current_model_name}")
            if os.path.exists(current_model_name):
                print(f"🔍 [DEBUG] Custom model exists, returning: {current_model_name}")
                return current_model_name
            else:
                print(f"🔍 [DEBUG] Custom model NOT found: {current_model_name}")
                return current_model_name  # Return as is for error handling
        
        # Otherwise, construct the path to the model folder
        model_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model")
        model_path = os.path.join(model_folder, f"{current_model_name}.pt")
        print(f"🔍 [DEBUG] Constructed built-in model path: {model_path}")
        
        # Check if the model exists
        if os.path.exists(model_path):
            print(f"🔍 [DEBUG] Built-in model exists, returning: {model_path}")
            return model_path
        else:
            print(f"🔍 [DEBUG] Built-in model NOT found: {model_path}")
            # Return the model name as fallback
            return current_model_name

    def save_log(self):
        """Save the current activity log to a text file."""
        folder_path = self.selected_folder if self.selected_folder else "output"
        os.makedirs(folder_path, exist_ok=True)
        log_file_path = os.path.join(folder_path, "activity_log.txt")
        
        with open(log_file_path, "w") as f:
            f.write(self.activity_log.toPlainText())
        
        QMessageBox.information(self, "Log Saved", f"Activity log has been saved to:\n{log_file_path}")
        print(f"Activity log saved to: {log_file_path}")

    def toggle_progress_display(self):
        """Toggle the visibility of the progress dialog."""
        if self.progress_dialog.isHidden():
            self.progress_dialog.show()
            # Initialize log with header if it's empty
            if not self.activity_log.toPlainText().strip():
                self.activity_log.append("=== Digital Architect — PT Sawit Sumbernan Sarana - ACTIVITY LOG ===\n")
                self.activity_log.append(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.activity_log.append("-" * 50 + "\n")
        else:
            self.progress_dialog.hide()