import dearpygui.dearpygui as dpg
import os
import subprocess
import json
import threading
import time  # Importing time for countdown functionality

dpg.create_context()

# Variables to hold the IDs for displaying the selected folder path and buttons
folder_path_id = None
select_folder_button_id = None
convert_button_id = None  # This button will be hidden initially
success_message_id = None
conversion_message_id = None

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

# Function to get model names from the "model" folder
def get_model_names():
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
    model_weights = dpg.get_value("model_combo")
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
                # In the run_conversion function, modify the log line:
                dpg.set_value(activity_log_id, f"{current_file} - {abnormal_count} abnormal, {normal_count} normal - {status}\n" + dpg.get_value(activity_log_id))

            except json.JSONDecodeError:
                pass

    countdown(3, folder_path)
    
def stop_timer():
    global timer_running
    timer_running = False


def show_result_window():
    with dpg.window(label="Conversion Results", modal=True, width=400, height=200):
        if final_time < 60:
            time_display = f"{final_time:.2f} seconds"
        else:
            minutes = int(final_time // 60)
            seconds = int(final_time % 60)
            time_display = f"{minutes:02}:{seconds:02} minutes"
            
        dpg.add_text(f"Total Processing Time: {time_display}")
        dpg.add_separator()
        dpg.add_text(f"Total Images Processed: {total_processed}")
        dpg.add_text(f"Total Abnormal Trees: {total_abnormal}")
        dpg.add_text(f"Total Normal Trees: {total_normal}")
        dpg.add_button(label="Close", callback=lambda: dpg.delete_item(dpg.get_item_parent()))


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

with dpg.window(label="Configuration", width=800, height=600):

    # Model AI Folder Section
    with dpg.group(horizontal=True):
        select_folder_button_id = dpg.add_button(label="+ Tambah Folder Tif", callback=lambda: dpg.show_item("folder_dialog_id"))
    
    # Display selected folder path
    folder_path_id = dpg.add_text("Selected Folder: None", wrap=320)
    
    # Convert to SHP button, initially hidden, appears right after selected folder path
    with dpg.group(horizontal=True):
        convert_button_id = dpg.add_button(label="Convert to SHP", show=False, callback=convert_to_shp_callback)
        dpg.add_button(label="Result Converted", show=False, callback=show_result_window, tag="result_button")

     # Success message placeholder
    conversion_message_id = dpg.add_text("", color=(0, 255, 0), show=False)
    
    # Konfigurasi Sistem Section
    dpg.add_text("KONFIGURASI SISTEM", bullet=True)
    dpg.add_separator()

    # Model AI dropdown
    dpg.add_text("Model AI")
    dpg.add_combo(model_names, default_value=model_names[0] if model_names else "", tag="model_combo", width=150)
    dpg.add_separator()  # Line separator

    # Image Size dropdown
    dpg.add_text("Image Size")
    dpg.add_combo(["640", "1280", "1920"], default_value="1280", width=100)
    dpg.add_separator()  # Line separator

    # IOU Threshold Slider
    dpg.add_text("IOU Threshold")
    with dpg.group(horizontal=True):
        dpg.add_button(label="-", callback=lambda: dpg.set_value("iou_threshold_slider", max(0, dpg.get_value("iou_threshold_slider") - 0.1)))
        dpg.add_slider_float(tag="iou_threshold_slider", width=150, default_value=0.2, min_value=0.0, max_value=1.0)
        dpg.add_button(label="+", callback=lambda: dpg.set_value("iou_threshold_slider", min(1, dpg.get_value("iou_threshold_slider") + 0.1)))
    dpg.add_separator()  # Line separator

    # Status Blok Radio Buttons
    dpg.add_text("Status Blok")
    dpg.add_radio_button(("Full Blok", "Setengah Blok"), horizontal=True)
    dpg.add_separator()  # Line separator

    # Confidence Threshold Slider
    dpg.add_text("Confidence Threshold")
    with dpg.group(horizontal=True):
        dpg.add_button(label="-", callback=lambda: dpg.set_value("conf_threshold_slider", max(0, dpg.get_value("conf_threshold_slider") - 0.1)))
        dpg.add_slider_float(tag="conf_threshold_slider", width=150, default_value=0.2, min_value=0.0, max_value=1.0)
        dpg.add_button(label="+", callback=lambda: dpg.set_value("conf_threshold_slider", min(1, dpg.get_value("conf_threshold_slider") + 0.1)))
    dpg.add_separator()  # Line separator

    # Add KML and SHP checkboxes in the Konfigurasi Sistem section
    with dpg.group(horizontal=True):
        dpg.add_checkbox(label="Convert to KML", tag="kml_checkbox", default_value=False)
        dpg.add_checkbox(label="Convert to SHP", tag="shp_checkbox", default_value=False)

    dpg.add_separator()  # Line separator

    # Konfigurasi Save Annotated Image Section
    dpg.add_text("KONFIGURASI SAVE ANNOTATED IMAGE", bullet=True)
    dpg.add_separator()

    # Max Det input
    dpg.add_text("Max Det")
    dpg.add_input_int(default_value=12000, width=100)
    dpg.add_separator()  # Line separator

    # Line Width input
    dpg.add_text("Line Width")
    dpg.add_input_int(default_value=10, width=100)
    dpg.add_separator()  # Line separator

    # Show Labels and Show Threshold Checkboxes
    with dpg.group(horizontal=True):
        dpg.add_checkbox(label="Show Labels", default_value=True)
        dpg.add_checkbox(label="Show Threshold", default_value=True)
    dpg.add_separator()  # Line separator

with dpg.window(label="Progress", modal=True, show=False, tag="progress_popup", width=400, height=200):
    
    dpg.add_text("Elapsed Time: 0.00 seconds", tag="timer_label")
    dpg.add_separator()
    
    progress_bar_id = dpg.add_progress_bar(width=-1)
    with dpg.group():
        progress_text_id = dpg.add_text("0 of 0 images processed")
        dpg.add_text("Estimated Time Remaining: 0.00 seconds", tag="estimated_label", show=False)

    dpg.add_separator()
    activity_log_id = dpg.add_text("", wrap=400)

# Set up viewport
dpg.create_viewport(title='AI Configuration', width=800, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
