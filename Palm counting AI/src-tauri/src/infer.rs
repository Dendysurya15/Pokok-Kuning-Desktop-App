//! Spawn Python inference worker, orchestrate processing, emit progress/log.

use crate::annotate;
use crate::config::AppConfig;
use crate::geo;
use std::io::{BufRead, BufReader, Write};
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};

const IMAGE_EXT: [&str; 6] = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"];

fn infer_worker_path() -> std::path::PathBuf {
    let manifest = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".into());
    let base = Path::new(&manifest).parent().unwrap_or(Path::new("."));
    base.join("python_ai").join("infer_worker.py")
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
    if !worker.exists() {
        return Err(format!("Inference worker not found: {}", worker.display()).into());
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

    let python = which_python();
    let mut child = Command::new(&python)
        .arg(&worker)
        .current_dir(worker.parent().unwrap())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    let mut stdin = child.stdin.take().ok_or("stdin")?;
    let stdout = child.stdout.take().ok_or("stdout")?;
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
    let _ = child.wait();
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

fn which_python() -> String {
    if std::process::Command::new("python").arg("--version").output().is_ok() {
        return "python".into();
    }
    if std::process::Command::new("python3").arg("--version").output().is_ok() {
        return "python3".into();
    }
    "python".to_string()
}
