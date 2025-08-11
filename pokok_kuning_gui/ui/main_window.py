from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QCheckBox, QProgressBar, QComboBox, QSlider, QGroupBox, 
    QRadioButton, QSpinBox, QMessageBox, QTextEdit, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor

import os
import sys
import time
import json

from utils.config_manager import load_config, save_config, get_model_names
from core.processor import ImageProcessor

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
        start_time = time.time()
        results = self.processor.process_folder(
            self.folder_path, 
            self.config,
            progress_callback=self.progress_update.emit
        )
        end_time = time.time()
        
        results['total_time'] = end_time - start_time
        self.processing_finished.emit(results)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("Pokok Kuning Desktop App")
        self.setGeometry(100, 100, 900, 700)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Load configuration
        self.config = load_config()
        
        # Create UI components
        self.create_folder_selection_section(main_layout)
        self.create_configuration_section(main_layout)
        self.create_annotated_section(main_layout)
        self.create_save_config_button(main_layout)
        
        # Create progress dialog (hidden initially)
        self.create_progress_section()
        
        # Initialize variables
        self.selected_folder = None
        self.processing_thread = None
        self.total_processed = 0
        self.total_files = 0
        self.total_abnormal = 0
        self.total_normal = 0
        
    def create_folder_selection_section(self, parent_layout):
        group = QGroupBox("Folder Selection")
        layout = QVBoxLayout()
        
        # Folder selection button and path display
        button_layout = QHBoxLayout()
        self.select_folder_button = QPushButton("Change Folder Tif")
        self.select_folder_button.clicked.connect(self.select_folder)
        button_layout.addWidget(self.select_folder_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.folder_path_label = QLabel("Selected Folder: None")
        layout.addWidget(self.folder_path_label)
        
        # Conversion options
        options_layout = QHBoxLayout()
        self.convert_button = QPushButton("Convert to SHP")
        self.convert_button.clicked.connect(self.start_conversion)
        self.convert_button.setEnabled(False)
        options_layout.addWidget(self.convert_button)
        
        self.save_annotated_checkbox = QCheckBox("Save Annotated File")
        default_save_annotated = self.config.get("save_annotated") if self.config.get("save_annotated") else "true"
        self.save_annotated_checkbox.setChecked(default_save_annotated == "true")
        options_layout.addWidget(self.save_annotated_checkbox)
        
        self.result_button = QPushButton("Result Converted")
        self.result_button.clicked.connect(self.show_results)
        self.result_button.setEnabled(False)
        options_layout.addWidget(self.result_button)
        
        layout.addLayout(options_layout)
        
        self.conversion_message = QLabel("")
        self.conversion_message.setStyleSheet("color: green;")
        layout.addWidget(self.conversion_message)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_configuration_section(self, parent_layout):
        group = QGroupBox("KONFIGURASI SISTEM")
        layout = QHBoxLayout()
        
        # Column 1: Model and Status
        col1_layout = QVBoxLayout()
        
        # Model selection
        model_layout = QVBoxLayout()
        model_layout.addWidget(QLabel("Model AI"))
        self.model_combo = QComboBox()
        model_names = get_model_names()
        self.model_combo.addItems(model_names)
        default_model = self.config.get("model") if self.config.get("model") else "yolov8n-pokok-kuning"
        if default_model in model_names:
            self.model_combo.setCurrentText(default_model)
        model_layout.addWidget(self.model_combo)
        col1_layout.addLayout(model_layout)
        
        col1_layout.addSpacing(10)
        
        # Status Blok
        status_layout = QVBoxLayout()
        status_layout.addWidget(QLabel("Status Blok"))
        self.status_full_radio = QRadioButton("Full Blok")
        self.status_half_radio = QRadioButton("Setengah Blok")
        
        default_status = self.config.get("status_blok") if self.config.get("status_blok") else "Full Blok"
        if default_status == "Full Blok":
            self.status_full_radio.setChecked(True)
        else:
            self.status_half_radio.setChecked(True)
            
        status_layout.addWidget(self.status_full_radio)
        status_layout.addWidget(self.status_half_radio)
        col1_layout.addLayout(status_layout)
        
        layout.addLayout(col1_layout)
        
        # Column 2: Image Size and KML
        col2_layout = QVBoxLayout()
        
        # Image size
        imgsize_layout = QVBoxLayout()
        imgsize_layout.addWidget(QLabel("Image Size"))
        self.imgsz_combo = QComboBox()
        self.imgsz_combo.addItems(["640", "1280", "1920", "9024", "12800"])
        default_imgsz = self.config.get("imgsz") if self.config.get("imgsz") else "12800"
        if default_imgsz in ["640", "1280", "1920", "9024", "12800"]:
            self.imgsz_combo.setCurrentText(default_imgsz)
        imgsize_layout.addWidget(self.imgsz_combo)
        col2_layout.addLayout(imgsize_layout)
        
        col2_layout.addSpacing(10)
        
        # KML checkbox
        self.kml_checkbox = QCheckBox("Convert to KML")
        default_kml = self.config.get("convert_kml") if self.config.get("convert_kml") else "false"
        self.kml_checkbox.setChecked(default_kml == "true")
        col2_layout.addWidget(self.kml_checkbox)
        
        layout.addLayout(col2_layout)
        
        # Column 3: IOU Threshold and SHP
        col3_layout = QVBoxLayout()
        
        # IOU Threshold
        iou_layout = QVBoxLayout()
        iou_layout.addWidget(QLabel("IOU Threshold"))
        iou_slider_layout = QHBoxLayout()
        
        self.iou_slider = QDoubleSpinBox()
        self.iou_slider.setRange(0.0, 1.0)
        self.iou_slider.setSingleStep(0.1)
        default_iou = float(self.config.get("iou", 0.2))
        self.iou_slider.setValue(default_iou)
        
        iou_slider_layout.addWidget(self.iou_slider)
        iou_layout.addLayout(iou_slider_layout)
        col3_layout.addLayout(iou_layout)
        
        col3_layout.addSpacing(10)
        
        # SHP checkbox
        self.shp_checkbox = QCheckBox("Convert to SHP")
        default_shp = self.config.get("convert_shp") if self.config.get("convert_shp") else "true"
        self.shp_checkbox.setChecked(default_shp == "true")
        col3_layout.addWidget(self.shp_checkbox)
        
        layout.addLayout(col3_layout)
        
        # Column 4: Confidence Threshold
        col4_layout = QVBoxLayout()
        
        # Confidence Threshold
        conf_layout = QVBoxLayout()
        conf_layout.addWidget(QLabel("Confidence Threshold"))
        
        self.conf_slider = QDoubleSpinBox()
        self.conf_slider.setRange(0.0, 1.0)
        self.conf_slider.setSingleStep(0.1)
        default_conf = float(self.config.get("conf", 0.2))
        self.conf_slider.setValue(default_conf)
        
        conf_layout.addWidget(self.conf_slider)
        col4_layout.addLayout(conf_layout)
        
        layout.addLayout(col4_layout)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_annotated_section(self, parent_layout):
        group = QGroupBox("KONFIGURASI SAVE ANNOTATED IMAGE")
        layout = QHBoxLayout()
        
        # Max Det
        max_det_layout = QVBoxLayout()
        max_det_layout.addWidget(QLabel("Max Det"))
        self.max_det_input = QSpinBox()
        self.max_det_input.setRange(1, 50000)
        default_max_det = int(self.config.get("max_det", 10000))
        self.max_det_input.setValue(default_max_det)
        max_det_layout.addWidget(self.max_det_input)
        layout.addLayout(max_det_layout)
        
        # Line Width
        line_width_layout = QVBoxLayout()
        line_width_layout.addWidget(QLabel("Line Width"))
        self.line_width_input = QSpinBox()
        self.line_width_input.setRange(1, 10)
        default_line_width = int(self.config.get("line_width", 3))
        self.line_width_input.setValue(default_line_width)
        line_width_layout.addWidget(self.line_width_input)
        layout.addLayout(line_width_layout)
        
        # Show Labels
        self.show_labels_checkbox = QCheckBox("Show Labels")
        default_show_labels = self.config.get("show_labels") if self.config.get("show_labels") else "true"
        self.show_labels_checkbox.setChecked(default_show_labels == "true")
        layout.addWidget(self.show_labels_checkbox)
        
        # Show Threshold
        self.show_conf_checkbox = QCheckBox("Show Threshold")
        default_show_conf = self.config.get("show_conf") if self.config.get("show_conf") else "false"
        self.show_conf_checkbox.setChecked(default_show_conf == "true")
        layout.addWidget(self.show_conf_checkbox)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_save_config_button(self, parent_layout):
        layout = QHBoxLayout()
        
        self.save_config_button = QPushButton("Simpan Konfigurasi")
        self.save_config_button.clicked.connect(self.save_configuration)
        layout.addWidget(self.save_config_button)
        
        self.save_message = QLabel("")
        self.save_message.setStyleSheet("color: green;")
        layout.addWidget(self.save_message)
        
        layout.addStretch()
        
        parent_layout.addLayout(layout)
    
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
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.selected_folder = folder_path
            
            # Check if folder contains .tif files
            has_tiff_files = any(f.lower().endswith(('.tif', '.tiff')) for f in os.listdir(folder_path))
            
            if has_tiff_files:
                self.folder_path_label.setText(f"Selected Folder: {folder_path}")
                self.select_folder_button.setText("Change Folder Tif")
                self.convert_button.setEnabled(True)
            else:
                self.folder_path_label.setText("The folder does not contain any .tif files.")
                self.select_folder_button.setText("Change Folder Tif")
                self.convert_button.setEnabled(False)
    
    def start_conversion(self):
        if not self.selected_folder:
            return
        
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
        self.processing_thread = ProcessingThread(self.selected_folder, config)
        self.processing_thread.progress_update.connect(self.update_progress)
        self.processing_thread.processing_finished.connect(self.processing_complete)
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
        self.timer_thread.terminate()
        
        self.total_processed = results.get("successful_processed", 0)
        self.total_files = results.get("total_files", 0)
        self.final_time = results.get("total_time", 0)
        
        # Show completion message
        folder_name = os.path.basename(self.selected_folder)
        self.conversion_message.setText(f"The folder '{folder_name}' has been converted successfully.")
        
        # Enable the result button
        self.result_button.setEnabled(True)
        
        # Hide progress dialog after 3 seconds
        QThread.sleep(3)
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
            self.save_message.setText("Configuration has been saved successfully!")
            
            # Hide message after 3 seconds
            QTimer.singleShot(3000, lambda: self.save_message.setText(""))
    
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
            "annotated_folder": os.path.join(self.selected_folder, "annotated") if self.selected_folder and self.save_annotated_checkbox.isChecked() else None
        }