//! Spawn Python inference worker, orchestrate processing, emit progress/log.
//! Supports both ONNX (Rust native) and PyTorch .pt (via Python worker).

use crate::annotate;
use crate::config::AppConfig;
use crate::geo;
use crate::yolo_onnx::YOLOInference;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

const IMAGE_EXT: [&str; 6] = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"];

fn infer_worker_path() -> std::path::PathBuf {
    // Hanya gunakan sidecar (tidak ada fallback ke Python script)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(exe_dir) = exe.parent() {
            // Sidecar biasanya di directory yang sama dengan executable
            let sidecar = exe_dir.join("infer_worker.exe");
            if sidecar.exists() {
                return sidecar;
            }
            // Atau di subdirectory binaries
            let sidecar_bin = exe_dir.join("binaries").join("infer_worker.exe");
            if sidecar_bin.exists() {
                return sidecar_bin;
            }
        }
    }
    
    // Jika tidak ditemukan, return path yang diharapkan (untuk error message)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(exe_dir) = exe.parent() {
            return exe_dir.join("infer_worker.exe");
        }
    }
    
    // Fallback (tidak akan digunakan karena akan error sebelumnya)
    PathBuf::from("infer_worker.exe")
}

fn list_images(folder: &Path) -> Vec<std::path::PathBuf> {
    let mut out = Vec::new();
    let Ok(entries) = std::fs::read_dir(folder) else { return out };
    for e in entries.flatten() {
        let p = e.path();
        if let Some(ext) = p.extension() {
            let ext = ext.to_string_lossy().to_lowercase();
            if IMAGE_EXT.iter().any(|e| e.trim_start_matches('.') == ext.as_str()) {
                out.push(p);
            }
        }
    }
    out.sort();
    out
}

fn tfw_path(image_path: &Path) -> std::path::PathBuf {
    image_path.with_extension("tfw")
}

#[derive(Clone, serde::Serialize)]
pub struct ProgressPayload {
    pub processed: usize,
    pub total: usize,
    pub current_file: String,
    pub status: String,
    pub abnormal_count: u32,
    pub normal_count: u32,
}

#[derive(Clone, serde::Serialize)]
pub struct DonePayload {
    pub successful: usize,
    pub failed: usize,
    pub total: usize,
    pub total_abnormal: u32,
    pub total_normal: u32,
}

pub fn run_processing(
    folder: &str,
    config: &AppConfig,
    model_path: &str,
    cancel: &AtomicBool,
    mut on_log: impl FnMut(&str),
    mut on_progress: impl FnMut(&ProgressPayload),
    mut on_done: impl FnMut(&DonePayload),
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let folder = Path::new(folder);
    if !folder.is_dir() {
        return Err("Folder not found".into());
    }

    let images = list_images(folder);
    let total = images.len();
    if total == 0 {
        on_log("No images found in folder.");
        on_done(&DonePayload {
            successful: 0,
            failed: 0,
            total: 0,
            total_abnormal: 0,
            total_normal: 0,
        });
        return Ok(());
    }

    let worker = infer_worker_path();
    let is_sidecar = worker.extension().map(|e| e == "exe").unwrap_or(false);
    
    if !worker.exists() {
        return Err(format!(
            "Python sidecar tidak ditemukan: {}\n\n\
            Untuk production: jalankan 'npm run build:sidecar' untuk build sidecar.\n\
            Sidecar harus ada di: {} atau {}/binaries/infer_worker.exe",
            worker.display(),
            if let Ok(exe) = std::env::current_exe() {
                exe.parent().map(|p| p.display().to_string()).unwrap_or_else(|| "executable directory".to_string())
            } else {
                "executable directory".to_string()
            },
            if let Ok(exe) = std::env::current_exe() {
                exe.parent().map(|p| p.display().to_string()).unwrap_or_else(|| "executable directory".to_string())
            } else {
                "executable directory".to_string()
            }
        ).into());
    }
    
    // Deteksi apakah sidecar valid (bukan placeholder)
    // Placeholder biasanya sangat kecil (< 1KB), sedangkan real sidecar > 100MB
    if is_sidecar {
        if let Ok(metadata) = std::fs::metadata(&worker) {
            let size = metadata.len();
            // Jika file terlalu kecil (< 1MB), kemungkinan placeholder
            if size < 1_000_000 {
                return Err(format!(
                    "Sidecar tidak valid (terlalu kecil: {} bytes). Kemungkinan placeholder.\n\n\
                    Untuk production: jalankan 'npm run build:sidecar' untuk build sidecar yang benar.",
                    size
                ).into());
            }
        }
    }

    let imgsz: i32 = config.imgsz.parse().unwrap_or(1280);
    let conf: f64 = config.conf.parse().unwrap_or(0.2);
    let iou: f64 = config.iou.parse().unwrap_or(0.2);
    let max_det: i32 = config.max_det.parse().unwrap_or(10000);
    let device = config.device.as_str();
    let device = if device.is_empty() { "auto" } else { device };
    let convert_kml = config.convert_kml.eq_ignore_ascii_case("true");
    let convert_shp = config.convert_shp.eq_ignore_ascii_case("true");
    let save_annotated = config.save_annotated.eq_ignore_ascii_case("true");
    let line_width: u32 = config.line_width.parse().unwrap_or(3).max(1);

    // Verify model file exists
    let model_path_buf = Path::new(model_path);
    if !model_path_buf.is_file() {
        return Err(format!("Model file not found: {}", model_path).into());
    }
    
    // Check if model is ONNX or PyTorch
    let is_onnx = model_path_buf.extension()
        .and_then(|e| e.to_str())
        .map(|e| e.eq_ignore_ascii_case("onnx"))
        .unwrap_or(false);
    
    // If ONNX, use native Rust inference
    if is_onnx {
        return run_processing_onnx(
            folder,
            config,
            model_path,
            cancel,
            on_log,
            on_progress,
            on_done,
        );
    }
    
    // Otherwise, use Python worker (PyTorch .pt)
    // Hanya support sidecar, tidak ada fallback ke Python sistem
    if !is_sidecar {
        return Err(format!(
            "Python sidecar tidak ditemukan atau tidak valid: {}\n\n\
            Untuk production: jalankan 'npm run build:sidecar' untuk build sidecar.\n\
            Sidecar harus ada di: {} atau {}/binaries/infer_worker.exe",
            worker.display(),
            if let Ok(exe) = std::env::current_exe() {
                exe.parent().map(|p| p.display().to_string()).unwrap_or_else(|| "executable directory".to_string())
            } else {
                "executable directory".to_string()
            },
            if let Ok(exe) = std::env::current_exe() {
                exe.parent().map(|p| p.display().to_string()).unwrap_or_else(|| "executable directory".to_string())
            } else {
                "executable directory".to_string()
            }
        ).into());
    }
    
    on_log(&format!("Using Python sidecar: {}", worker.display()));
    let mut cmd = Command::new(&worker);
    
    let mut child = cmd
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    let mut stdin = child.stdin.take().ok_or("stdin")?;
    let stdout = child.stdout.take().ok_or("stdout")?;
    let stderr = child.stderr.take().ok_or("stderr")?;
    
    // Spawn thread to read stderr and collect in shared buffer
    let stderr_buffer: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
    let stderr_buffer_clone = Arc::clone(&stderr_buffer);
    let stderr_handle = thread::spawn(move || {
        let reader = BufReader::new(stderr);
        let mut error_lines = Vec::new();
        for line in reader.lines() {
            if let Ok(l) = line {
                error_lines.push(l.clone());
                if let Ok(mut buf) = stderr_buffer_clone.lock() {
                    buf.push(l);
                }
            }
        }
    });
    
    let mut reader = BufReader::new(stdout);

    let mut successful = 0_usize;
    let mut failed = 0_usize;
    let mut total_abnormal = 0_u32;
    let mut total_normal = 0_u32;
    let annotated_dir = folder.join("annotated");

    for (idx, image_path) in images.iter().enumerate() {
        if cancel.load(Ordering::Relaxed) {
            on_log("Cancelled.");
            break;
        }

        let name = image_path.file_name().and_then(|s| s.to_str()).unwrap_or("?");
        on_log(&format!("Processing {} ({}/{})", name, idx + 1, total));

        let tfw_path = tfw_path(image_path);
        let Some(tfw) = geo::read_tfw(&tfw_path) else {
            on_log(&format!("  Skip: no .tfw for {}", name));
            failed += 1;
            on_progress(&ProgressPayload {
                processed: idx + 1,
                total,
                current_file: name.to_string(),
                status: "Skip (no .tfw)".to_string(),
                abnormal_count: 0,
                normal_count: 0,
            });
            continue;
        };

        let req = serde_json::json!({
            "image": image_path.to_string_lossy(),
            "model": model_path,
            "imgsz": imgsz,
            "conf": conf,
            "iou": iou,
            "max_det": max_det,
            "device": device,
        });
        if writeln!(stdin, "{}", req).is_err() {
            on_log("  Error writing to worker.");
            failed += 1;
            break;
        }
        stdin.flush()?;

        let mut line = String::new();
        if reader.read_line(&mut line)? == 0 {
            on_log("  Worker closed stdout.");
            // Check for stderr messages collected so far
            if let Ok(buf) = stderr_buffer.lock() {
                if !buf.is_empty() {
                    let err_msg = buf.join("\n");
                    on_log(&format!("  Worker stderr: {}", err_msg));
                }
            }
            failed += 1;
            break;
        }
        let line = line.trim();
        let resp: serde_json::Value = match serde_json::from_str(line) {
            Ok(v) => v,
            Err(_) => {
                on_log(&format!("  Invalid JSON: {}", &line[..line.len().min(80)]));
                failed += 1;
                on_progress(&ProgressPayload {
                    processed: idx + 1,
                    total,
                    current_file: name.to_string(),
                    status: "Parse error".to_string(),
                    abnormal_count: 0,
                    normal_count: 0,
                });
                continue;
            }
        };

        let err_msg = resp.get("error").and_then(|v| v.as_str());
        if let Some(e) = err_msg {
            on_log(&format!("  Inference error: {}", e));
            failed += 1;
            on_progress(&ProgressPayload {
                processed: idx + 1,
                total,
                current_file: name.to_string(),
                status: format!("Error: {}", e),
                abnormal_count: 0,
                normal_count: 0,
            });
            continue;
        }

        let detections: Vec<geo::Detection> = match resp.get("detections") {
            Some(serde_json::Value::Array(arr)) => arr
                .iter()
                .filter_map(|v| serde_json::from_value(v.clone()).ok())
                .collect(),
            _ => vec![],
        };

        let mut abn = 0u32;
        let mut nor = 0u32;
        for d in &detections {
            if d.class_id == 0 {
                abn += 1;
            } else if d.class_id == 1 {
                nor += 1;
            }
        }
        total_abnormal += abn;
        total_normal += nor;

        let fc = geo::create_geojson(&detections, &tfw);
        let out_dir = folder;
        if let Some(geojson_path) = geo::save_geojson(&fc, image_path, out_dir) {
            if convert_kml {
                let kml_path = geojson_path.with_extension("kml");
                let _ = geo::write_kml(&detections, &tfw, &kml_path);
            }
            if convert_shp {
                let shp_path = geojson_path.with_extension("shp");
                let _ = geo::write_shp(&detections, &tfw, &shp_path);
            }
        }

        if save_annotated && !detections.is_empty() {
            let _ = annotate::save_annotated(image_path, &detections, &annotated_dir, line_width);
        }

        successful += 1;
        on_progress(&ProgressPayload {
            processed: idx + 1,
            total,
            current_file: name.to_string(),
            status: "OK".to_string(),
            abnormal_count: abn,
            normal_count: nor,
        });
    }

    drop(stdin);
    let status = child.wait();
    // Wait for stderr thread to finish
    let _ = stderr_handle.join();
    // Get final stderr messages
    if let Ok(buf) = stderr_buffer.lock() {
        if !buf.is_empty() {
            let err_msg = buf.join("\n");
            on_log(&format!("Worker stderr: {}", err_msg));
        }
    }
    if let Ok(exit_status) = status {
        if !exit_status.success() {
            on_log(&format!("Worker exited with code: {:?}", exit_status.code()));
        }
    }
    on_log(&format!(
        "Done. {} succeeded, {} failed.",
        successful, failed
    ));
    on_done(&DonePayload {
        successful,
        failed,
        total,
        total_abnormal,
        total_normal,
    });
    Ok(())
}

/// Run processing using ONNX (native Rust)
fn run_processing_onnx(
    folder: &Path,
    config: &AppConfig,
    model_path: &str,
    cancel: &AtomicBool,
    mut on_log: impl FnMut(&str),
    mut on_progress: impl FnMut(&ProgressPayload),
    mut on_done: impl FnMut(&DonePayload),
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let imgsz: u32 = config.imgsz.parse().unwrap_or(1280);
    let conf: f32 = config.conf.parse().unwrap_or(0.2) as f32;
    let iou: f32 = config.iou.parse().unwrap_or(0.2) as f32;
    let max_det: i32 = config.max_det.parse().unwrap_or(10000);
    let convert_kml = config.convert_kml.eq_ignore_ascii_case("true");
    let convert_shp = config.convert_shp.eq_ignore_ascii_case("true");
    let save_annotated = config.save_annotated.eq_ignore_ascii_case("true");
    let line_width: u32 = config.line_width.parse().unwrap_or(3).max(1);

    on_log(&format!("Loading ONNX model: {}", model_path));
    let yolo = YOLOInference::new(Path::new(model_path), imgsz)?;
    on_log("ONNX model loaded successfully.");

    let images = list_images(folder);
    let total = images.len();
    if total == 0 {
        on_log("No images found in folder.");
        on_done(&DonePayload {
            successful: 0,
            failed: 0,
            total: 0,
            total_abnormal: 0,
            total_normal: 0,
        });
        return Ok(());
    }

    let mut successful = 0_usize;
    let mut failed = 0_usize;
    let mut total_abnormal = 0_u32;
    let mut total_normal = 0_u32;
    let annotated_dir = folder.join("annotated");

    for (idx, image_path) in images.iter().enumerate() {
        if cancel.load(Ordering::Relaxed) {
            on_log("Cancelled.");
            break;
        }

        let name = image_path.file_name().and_then(|s| s.to_str()).unwrap_or("?");
        on_log(&format!("Processing {} ({}/{})", name, idx + 1, total));

        let tfw_path = tfw_path(image_path);
        let Some(tfw) = geo::read_tfw(&tfw_path) else {
            on_log(&format!("  Skip: no .tfw for {}", name));
            failed += 1;
            on_progress(&ProgressPayload {
                processed: idx + 1,
                total,
                current_file: name.to_string(),
                status: "Skip (no .tfw)".to_string(),
                abnormal_count: 0,
                normal_count: 0,
            });
            continue;
        };

        // Load and process image
        let img = match image::open(image_path) {
            Ok(img) => img,
            Err(e) => {
                on_log(&format!("  Error loading image: {}", e));
                failed += 1;
                continue;
            }
        };

        // Run inference
        let detections = match yolo.predict(&img, conf, iou, max_det) {
            Ok(dets) => dets,
            Err(e) => {
                on_log(&format!("  Inference error: {}", e));
                failed += 1;
                on_progress(&ProgressPayload {
                    processed: idx + 1,
                    total,
                    current_file: name.to_string(),
                    status: format!("Error: {}", e),
                    abnormal_count: 0,
                    normal_count: 0,
                });
                continue;
            }
        };

        // Convert to geo::Detection format (already compatible)
        let geo_detections: Vec<geo::Detection> = detections
            .into_iter()
            .map(|d| geo::Detection {
                x1: d.x1,
                y1: d.y1,
                x2: d.x2,
                y2: d.y2,
                class_id: d.class_id,
                conf: d.conf,
            })
            .collect();

        let mut abn = 0u32;
        let mut nor = 0u32;
        for d in &geo_detections {
            if d.class_id == 0 {
                abn += 1;
            } else if d.class_id == 1 {
                nor += 1;
            }
        }
        total_abnormal += abn;
        total_normal += nor;

        // Save GeoJSON, KML, SHP
        let fc = geo::create_geojson(&geo_detections, &tfw);
        let out_dir = folder;
        if let Some(geojson_path) = geo::save_geojson(&fc, image_path, out_dir) {
            if convert_kml {
                let kml_path = geojson_path.with_extension("kml");
                let _ = geo::write_kml(&geo_detections, &tfw, &kml_path);
            }
            if convert_shp {
                let shp_path = geojson_path.with_extension("shp");
                let _ = geo::write_shp(&geo_detections, &tfw, &shp_path);
            }
        }

        // Save annotated image
        if save_annotated && !geo_detections.is_empty() {
            let _ = annotate::save_annotated(image_path, &geo_detections, &annotated_dir, line_width);
        }

        successful += 1;
        on_progress(&ProgressPayload {
            processed: idx + 1,
            total,
            current_file: name.to_string(),
            status: "OK".to_string(),
            abnormal_count: abn,
            normal_count: nor,
        });
    }

    on_log(&format!(
        "Done. {} succeeded, {} failed.",
        successful, failed
    ));
    on_done(&DonePayload {
        successful,
        failed,
        total,
        total_abnormal,
        total_normal,
    });
    Ok(())
}

