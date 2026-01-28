mod annotate;
mod config;
mod geo;
mod infer;
mod specs;
mod yolo_onnx;

use tauri::Emitter;

use config::{add_model as config_add_model, load_config, remove_model as config_remove_model, save_config, set_active_model, list_models, get_active_model_path, AppConfig};
use specs::get_system_specs;
use std::sync::atomic::AtomicBool;

#[tauri::command]
fn get_specs() -> Result<specs::SystemSpecs, String> {
    Ok(get_system_specs())
}

#[tauri::command]
fn load_config_cmd() -> Result<AppConfig, String> {
    load_config().map_err(|e| e.to_string())
}

#[tauri::command]
fn save_config_cmd(c: AppConfig) -> Result<(), String> {
    save_config(&c).map_err(|e| e.to_string())
}

#[tauri::command]
fn list_models_cmd() -> Result<Vec<config::YoloModel>, String> {
    list_models().map_err(|e| e.to_string())
}

#[tauri::command]
async fn add_model_cmd(
    window: tauri::Window,
    source_path: String,
    name: Option<String>,
) -> Result<config::YoloModel, String> {
    let path = std::path::Path::new(&source_path).to_path_buf();
    let name = name.unwrap_or_else(|| {
        path.file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("model")
            .to_string()
    });
    
    // Check if conversion is needed
    let needs_conversion = path.extension()
        .and_then(|e| e.to_str())
        .map(|e| e.eq_ignore_ascii_case("pt"))
        .unwrap_or(false);
    
    if needs_conversion {
        // Emit conversion start event
        let _ = window.emit("model-conversion-start", &format!("Converting {} to ONNX...", name));
    }
    
    // Run in background thread to avoid blocking UI
    let window_clone = window.clone();
    let name_clone = name.clone();
    let path_clone = path.clone();
    
    // Use async runtime to wait for thread result
    let (tx, rx) = std::sync::mpsc::channel();
    
    std::thread::spawn(move || {
        let result = config_add_model(name_clone.clone(), &path_clone);
        let _ = tx.send(result);
    });
    
    // Wait for result - this will block the async task but not the UI thread
    // Tauri's async runtime will handle this properly
    let result = rx.recv().map_err(|e| format!("Thread error: {}", e))?;
    
    match result {
        Ok(model) => {
            if needs_conversion {
                let _ = window_clone.emit("model-conversion-done", &format!("Successfully converted {}", name));
            }
            Ok(model)
        }
        Err(e) => {
            if needs_conversion {
                let _ = window_clone.emit("model-conversion-error", &format!("Conversion failed: {}", e));
            }
            Err(e.to_string())
        }
    }
}

#[tauri::command]
fn remove_model_cmd(id: i64) -> Result<(), String> {
    config_remove_model(id).map_err(|e| e.to_string())
}

#[tauri::command]
fn set_active_model_cmd(id: i64) -> Result<(), String> {
    set_active_model(id).map_err(|e| e.to_string())
}

static PROCESSING_CANCEL: AtomicBool = AtomicBool::new(false);

#[tauri::command]
fn run_processing_cmd(
    window: tauri::Window,
    folder: String,
) -> Result<(), String> {
    let model_path = get_active_model_path()
        .map_err(|e| e.to_string())?
        .ok_or("No active model. Add and select a YOLO model first.")?;
    let config = load_config().map_err(|e| e.to_string())?;
    let cancel = &PROCESSING_CANCEL;
    cancel.store(false, std::sync::atomic::Ordering::Relaxed);

    std::thread::spawn(move || {
        let on_log = |s: &str| {
            let _ = window.emit("processing-log", s);
        };
        let on_progress = |p: &infer::ProgressPayload| {
            let _ = window.emit("processing-progress", p);
        };
        let on_done = |d: &infer::DonePayload| {
            let _ = window.emit("processing-done", d);
        };
        if let Err(e) = infer::run_processing(
            &folder,
            &config,
            &model_path,
            cancel,
            on_log,
            on_progress,
            on_done,
        ) {
            let _ = window.emit("processing-log", &format!("Error: {}", e));
            let _ = window.emit(
                "processing-done",
                &infer::DonePayload {
                    successful: 0,
                    failed: 0,
                    total: 0,
                    total_abnormal: 0,
                    total_normal: 0,
                },
            );
        }
    });
    Ok(())
}

#[tauri::command]
fn cancel_processing() {
    PROCESSING_CANCEL.store(true, std::sync::atomic::Ordering::Relaxed);
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            get_specs,
            load_config_cmd,
            save_config_cmd,
            list_models_cmd,
            add_model_cmd,
            remove_model_cmd,
            set_active_model_cmd,
            run_processing_cmd,
            cancel_processing,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
