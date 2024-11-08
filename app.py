import dearpygui.dearpygui as dpg
import os
import subprocess
import json
import threading
import time  # Importing time for countdown functionality
import sys
import sqlite3

# Variables to hold the IDs for displaying the selected folder path and buttons
folder_path_id = None
select_folder_button_id = None
convert_button_id = None  # This button will be hidden initially
success_message_id = None
conversion_message_id = None
model_folder = ''
timer_running = False
start_time = 0
final_time = 0
total_processed = 0
total_file_tiff = 0
total_abnormal = 0
total_normal = 0
# Function to update the timer label
def update_timer():
    while timer_running:
        elapsed_time = time.time() - start_time
        if elapsed_time < 60:
            # Show only seconds if under 1 minute
            dpg.set_value("timer_label", f"{elapsed_time:.2f} detik")
        else:
            # Show in minutes:seconds format if 1 minute or more
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            dpg.set_value("timer_label", f"{minutes:02}:{seconds:02} menit")
        time.sleep(0.1)  # Update every 0.1 seconds

def setup_database(script_dir):
    if not os.path.exists('database.db'):
        setup_window = dpg.add_window(label="Database Setup", modal=True, width=300, height=100, pos=(250, 250))
        dpg.add_text("Setting up database...", parent=setup_window)
        dpg.add_loading_indicator(parent=setup_window)
           
        try:
            subprocess.run([sys.executable, os.path.join(script_dir, "setup_database.py")], check=True)
            dpg.delete_item(setup_window)  # Close the setup window
           
            # Show success message
            success_window = dpg.add_window(label="Success", modal=True, width=300, height=100, pos=(250, 250))
            dpg.add_text("Database setup completed successfully!", parent=success_window)
           
            # Create timer thread to close window
            def close_success_window():
                time.sleep(2)  # Wait 2 seconds
                dpg.delete_item(success_window)
               
            threading.Thread(target=close_success_window, daemon=True).start()
            
        except subprocess.CalledProcessError as e:
            dpg.delete_item(setup_window)
            error_window = dpg.add_window(label="Error", modal=True, width=300, height=100, pos=(250, 250))
            dpg.add_text(f"Error running setup_database.py: {e}", parent=error_window)
            dpg.add_button(label="Exit", callback=lambda: sys.exit(1), parent=error_window)

def load_config_from_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM configuration ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    
    # dapat dilihat untuk urutan di file setup_database.py
    config = {
        "model": row[1],
        "imgsz": row[2],
        "iou": row[3],
        "conf": row[4],
        "convert_shp": row[5],
        "convert_kml": row[6],
        "max_det": row[7],
        "line_width": row[8],
        "show_labels": row[9],
        "show_conf": row[10],
        "status_blok": row[11]
    }
    return config

dpg.create_context()
width, height, channels, data = dpg.load_image("C:\\Users\\DELL\\Downloads\\cbi-ho.jpeg")

with dpg.texture_registry():
    dpg.add_static_texture(width=width, height=height, default_value=data, tag="background")

# Add background image to viewport
with dpg.window(label="Background", no_title_bar=True, no_move=True, no_resize=True, no_scrollbar=True):
    dpg.add_image("background", width=1200, height=800)

# Create theme for semi-transparent window
with dpg.theme() as window_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (0, 0, 0, 100), category=dpg.mvThemeCat_Core)

# Create a theme for green buttons
with dpg.theme() as green_button_theme:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 150, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 200, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 100, 0))

# Create a theme for blue buttons 
with dpg.theme() as blue_button_theme:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 100, 150))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 150, 200))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 50, 100))

script_dir = os.path.dirname(os.path.abspath(__file__))
setup_database(script_dir)
config = load_config_from_db()


def get_model_names():
    global model_folder
    model_folder = os.path.join(os.getcwd(), "model")  # Path to your model folder
    if os.path.exists(model_folder):
        model_files = [f for f in os.listdir(model_folder) if f.endswith('.pt')]
        model_names = [os.path.splitext(f)[0] for f in model_files]  # Remove the extension
        return model_names
    return []

# Call the function to get model names
model_names = get_model_names()

def folder_callback(sender, app_data, user_data):
    global folder_path_id, select_folder_button_id, convert_button_id
    folder_path = app_data['current_path']  # Get only the current_path

    # Check if the folder contains any .tif files
    has_tiff_files = any(f.endswith('.tif') for f in os.listdir(folder_path))

    if has_tiff_files:
        dpg.set_value(folder_path_id, f"Selected Folder: {folder_path}")
        dpg.set_item_label(select_folder_button_id, "Change Folder Tif")
        # Show the "Convert to SHP" button after confirming there are .tif files
        dpg.show_item(convert_button_id)
    else:
        dpg.set_value(folder_path_id, "The folder does not contain any .tif files.")
        dpg.set_item_label(select_folder_button_id, "+ Tambah Folder Tif")
        # Hide the button if no .tif files are found
        dpg.hide_item(convert_button_id)

def convert_to_shp_callback(sender, app_data, user_data):
    # Show the progress popup window
    global timer_running, start_time
    dpg.show_item("progress_popup")

    # Initialize progress bar and activity log
    dpg.set_value(progress_bar_id, 0.0)
    dpg.set_value(progress_text_id, "Starting conversion...")
    dpg.set_value(activity_log_id, "")

     # Start the timer
    timer_running = True
    start_time = time.time()
    threading.Thread(target=update_timer, daemon=True).start()
    
    threading.Thread(target=run_conversion).start()

def run_conversion():
    global total_file_tiff, total_abnormal, total_normal
    folder_path = dpg.get_value(folder_path_id).replace("Selected Folder: ", "")

    model_name = dpg.get_value("model_combo")  # Get model name from the combo box
    model_weights = os.path.join(model_folder, model_name + ".pt")
    conf_threshold = dpg.get_value("conf_threshold_slider")
    iou_threshold = dpg.get_value("iou_threshold_slider")
    kml_option = dpg.get_value("kml_checkbox")
    shp_option = dpg.get_value("shp_checkbox")
    time.sleep(5)

    command = [
        "python", "feature_convert_shp.py",
        "--folder", folder_path,
        "--weights", model_weights,
        "--conf", str(conf_threshold),
        "--iou", str(iou_threshold),
    ]

    if kml_option:
        command.append("--kml")
    if shp_option:
        command.append("--shp")

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            stripped_output = output.strip()
        
            try:
                json_output = json.loads(stripped_output)
                processed = json_output.get("processed", 0)
                total_file_tiff = json_output.get("total", 1)
                current_file = json_output.get("current_file", "N/A")
                status = json_output.get("status", "Processing")
                avg_time = json_output.get("avg_time_per_file", 0)
                abnormal_count  = json_output.get('abnormal_count', 0)
                total_abnormal += abnormal_count
                normal_count  = json_output.get('normal_count', 0)
                total_normal += normal_count
                
                remaining_files = total_file_tiff - processed
                estimated_seconds = float(avg_time) * remaining_files
                
                if estimated_seconds > 0:
                    dpg.show_item("estimated_label")
                    if estimated_seconds < 60:
                        estimated_display = f"{estimated_seconds:.2f} detik"
                    else:
                        estimated_minutes = int(estimated_seconds // 60)
                        estimated_secs = int(estimated_seconds % 60)
                        estimated_display = f"{estimated_minutes}:{estimated_secs:02d} menit"
                    dpg.set_value("estimated_label", f"Estimated Time Remaining: {estimated_display}")

                progress = processed / total_file_tiff if total_file_tiff > 0 else 0
                dpg.set_value(progress_bar_id, progress)
                dpg.set_value(progress_text_id, f"{processed} of {total_file_tiff} images processed")
        
                dpg.set_value(activity_log_id, f"{current_file} - {abnormal_count} abnormal, {normal_count} normal - {status}\n" + dpg.get_value(activity_log_id))

            except json.JSONDecodeError:
                pass

    countdown(3, folder_path)
    
def stop_timer():
    global timer_running
    timer_running = False


def show_result_window():
    with dpg.window(label="Conversion Results", modal=True, width=500, height=250, pos=[400, 300]) as result_window:

        with dpg.group(horizontal=True):
            with dpg.group(horizontal=False):
                dpg.add_text("Convert Time")
                dpg.add_spacer(width=10)
                if final_time < 60:
                    time_display = f"{final_time:.2f} seconds"
                else:
                    minutes = int(final_time // 60)
                    seconds = int(final_time % 60)
                    time_display = f"{minutes:02}:{seconds:02} minutes"
                dpg.add_text(time_display)

            
            
            with dpg.group(horizontal=False):
                dpg.add_text("Images Blok")
                dpg.add_spacer(width=10)
                dpg.add_text(f"{total_processed}")
        
        dpg.add_spacer(width=20)
        dpg.add_separator()
        # Tree counts section
        with dpg.group(horizontal=True):
            with dpg.group(horizontal=False):
                
                dpg.add_text("Pokok Normal")
                dpg.add_text(f"{total_normal}")
        
                dpg.add_spacer(width=10)

            with dpg.group(horizontal=False):
                dpg.add_text("Pokok Abnormal")
                dpg.add_text(f"{total_abnormal}")
        
        dpg.add_spacer(height=20)
        dpg.add_button(label="Close", callback=lambda: dpg.delete_item(result_window), width=480)


def save_configuration():
    config_to_save = {
        "model": dpg.get_value("model_combo"),
        "imgsz": dpg.get_value("imgsz_combo"),
        "iou": str(dpg.get_value("iou_threshold_slider")),
        "conf": str(dpg.get_value("conf_threshold_slider")),
        "convert_shp": "true" if dpg.get_value("shp_checkbox") else "false",
        "convert_kml": "true" if dpg.get_value("kml_checkbox") else "false",
        "max_det": str(dpg.get_value("max_det_input")),
        "line_width": str(dpg.get_value("line_width_input")),
        "show_labels": "true" if dpg.get_value("show_labels_checkbox") else "false",
        "show_conf": "true" if dpg.get_value("show_conf_checkbox") else "false",
        "status_blok": dpg.get_value("status_blok")
    }
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO configuration (
                model, imgsz, iou, conf, convert_shp, convert_kml,
                max_det, line_width, show_labels, show_conf, status_blok
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            config_to_save["model"], config_to_save["imgsz"], 
            config_to_save["iou"], config_to_save["conf"],
            config_to_save["convert_shp"], config_to_save["convert_kml"],
            config_to_save["max_det"], config_to_save["line_width"],
            config_to_save["show_labels"], config_to_save["show_conf"],
            config_to_save["status_blok"]
        ))
        
        conn.commit()
        dpg.show_item("save_message")
        
        def countdown_message():
            for i in range(4, 0, -1):
                dpg.set_value("save_message", f"Configuration has been saved successfully! Message will disappear in {i}...")
                time.sleep(1)
            dpg.hide_item("save_message")
            
        threading.Thread(target=countdown_message, daemon=True).start()
        
    except Exception as e:
        dpg.set_value("save_message", f"Error saving configuration: {str(e)}")
        dpg.show_item("save_message")
    
    conn.close()


def countdown(seconds, folder_path):
    global final_time, total_processed
    stop_timer()
    final_time = time.time() - start_time
    total_processed = total_file_tiff
    for i in range(seconds, 0, -1):
        dpg.set_value(progress_text_id, f"Conversion complete! Closing in {i}...")
        time.sleep(1)
    dpg.hide_item("progress_popup")

    # Show completion message above the "Convert to SHP" button
    dpg.set_value(conversion_message_id, f"The folder '{os.path.basename(folder_path)}' has been converted successfully.")
    dpg.show_item(conversion_message_id)

    dpg.show_item("result_button")  # Show the result button

    for i in range(4, 0, -1):
        dpg.set_value(conversion_message_id, f"The folder '{os.path.basename(folder_path)}' has been converted successfully. This message will disappear in {i}...")
        time.sleep(1)
    dpg.hide_item(conversion_message_id)

# Create a file dialog for folder selection
with dpg.file_dialog(directory_selector=True, show=False, callback=folder_callback, id="folder_dialog_id", width=700, height=400):
    dpg.add_file_extension("", color=(150, 255, 150, 255))


with dpg.window(label="App", width=800, height=600, pos=[200, 100]):
    dpg.bind_item_theme(dpg.last_container(), window_theme)
    with dpg.group(horizontal=True):
        select_folder_button_id = dpg.add_button(label="+ Tambah Folder Tif", callback=lambda: dpg.show_item("folder_dialog_id"))
        dpg.bind_item_theme(select_folder_button_id, green_button_theme)
    
    folder_path_id = dpg.add_text("Selected Folder: None", wrap=320)
    
    with dpg.group(horizontal=True):
        convert_button_id = dpg.add_button(label="Convert to SHP", show=False, callback=convert_to_shp_callback)
        dpg.bind_item_theme(convert_button_id, green_button_theme)
        dpg.add_button(label="Result Converted", show=False, callback=show_result_window, tag="result_button")

    conversion_message_id = dpg.add_text("", color=(0, 255, 0), show=False)

    dpg.add_spacer(height=10)  # Adds vertical spacing of 10 pixels    
    dpg.add_text("KONFIGURASI SISTEM", bullet=True)
    dpg.add_separator()

    with dpg.group(horizontal=True):
        with dpg.group(horizontal=False):
            with dpg.group():
                dpg.add_text("Model AI")
                dpg.add_combo(model_names, default_value=config["model"], tag="model_combo", width=150)

            dpg.add_spacer(height=10)  # Adds vertical spacing of 10 pixels
        
            with dpg.group():
                dpg.add_text("Status Blok")
                dpg.add_radio_button(("Full Blok", "Setengah Blok"), default_value=config["status_blok"], horizontal=False, tag="status_blok")            
        
        with dpg.group(horizontal=False):
            with dpg.group():
                dpg.add_text("Image Size")
                dpg.add_combo(["640", "1280", "1920"], default_value=config["imgsz"], tag="imgsz_combo", width=100)

            dpg.add_spacer(height=10)  # Adds vertical spacing of 10 pixels
            dpg.add_checkbox(label="Convert to KML", tag="kml_checkbox", default_value=config["convert_kml"] == "true")
                
        with dpg.group(horizontal=False):
            
            dpg.add_text("IOU Threshold")
            with dpg.group(horizontal=True):
                dpg.add_button(label="-", callback=lambda: dpg.set_value("iou_threshold_slider", max(0, dpg.get_value("iou_threshold_slider") - 0.1)))
                dpg.add_slider_float(tag="iou_threshold_slider", width=150, default_value=float(config["iou"]), min_value=0.0, max_value=1.0)
                dpg.add_button(label="+", callback=lambda: dpg.set_value("iou_threshold_slider", min(1, dpg.get_value("iou_threshold_slider") + 0.1)))
            
            dpg.add_spacer(height=10)  # Adds vertical spacing of 10 pixels
            dpg.add_checkbox(label="Convert to SHP", tag="shp_checkbox", default_value=config["convert_shp"] == "true")

        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_text("Confidence Threshold")
                with dpg.group(horizontal=True):
                    dpg.add_button(label="-", callback=lambda: dpg.set_value("conf_threshold_slider", max(0, dpg.get_value("conf_threshold_slider") - 0.1)))
                    dpg.add_slider_float(tag="conf_threshold_slider", width=150, default_value=float(config["conf"]), min_value=0.0, max_value=1.0)
                    dpg.add_button(label="+", callback=lambda: dpg.set_value("conf_threshold_slider", min(1, dpg.get_value("conf_threshold_slider") + 0.1)))
    
        


    dpg.add_spacer(height=10)  # Adds vertical spacing of 10 pixels    
    dpg.add_text("KONFIGURASI SAVE ANNOTATED IMAGE", bullet=True)
    dpg.add_separator()

    # Show Labels and Show Threshold Checkboxes
    with dpg.group(horizontal=True):

        with dpg.group(horizontal=False):
            with dpg.group():
                dpg.add_text("Max Det")
                dpg.add_input_int(tag="max_det_input", default_value=int(config["max_det"]), width=100)

        with dpg.group(horizontal=False):
            with dpg.group():
                
                dpg.add_text("Line Width")
                dpg.add_input_int(tag="line_width_input", default_value=int(config["line_width"]), width=100)

        dpg.add_checkbox(label="Show Labels", tag="show_labels_checkbox", default_value=config["show_labels"] == "true")
        dpg.add_checkbox(label="Show Threshold", tag="show_conf_checkbox", default_value=config["show_conf"] == "true")
    
    dpg.add_spacer(height=10)  # Add some space before the button
    
    with dpg.group(horizontal=True):
        save_config_button = dpg.add_button(label="Simpan Konfigurasi", callback=save_configuration, width=150)
        dpg.bind_item_theme(save_config_button, blue_button_theme)

    dpg.add_text("", color=(0, 255, 0), show=False, tag="save_message")


with dpg.window(label="Progress Convert", modal=True, show=False, tag="progress_popup", width=400, height=200):
    
    dpg.add_text("Elapsed Time: 0.00 seconds", tag="timer_label")
    dpg.add_separator()
    
    progress_bar_id = dpg.add_progress_bar(width=-1)
    with dpg.group():
        progress_text_id = dpg.add_text("0 of 0 images processed")
        dpg.add_text("Estimated Time Remaining: 0.00 seconds", tag="estimated_label", show=False)

    dpg.add_separator()
    activity_log_id = dpg.add_text("", wrap=400)

# Set up viewport
dpg.create_viewport(title='Desktop App Pokok Kuning Converting Tools With AI', width=1200, height=800)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
