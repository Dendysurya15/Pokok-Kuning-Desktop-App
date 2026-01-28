//! Orchestrate processing, emit progress/log.
//! Semua inference dilakukan di Rust dengan ONNX models.
//! Python sidecar hanya untuk conversion .pt → .onnx.

use crate::annotate;
use crate::config::AppConfig;
use crate::geo;
use crate::yolo_onnx::YOLOInference;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};

const IMAGE_EXT: [&str; 6] = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"];

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
    on_progress: impl FnMut(&ProgressPayload),
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

    // Python sidecar hanya untuk conversion, tidak untuk inference
    // Semua inference dilakukan di Rust dengan ONNX

    // Verify model file exists
    let model_path_buf = Path::new(model_path);
    if !model_path_buf.is_file() {
        return Err(format!("Model file not found: {}", model_path).into());
    }
    
    // Check if model is ONNX
    let is_onnx = model_path_buf.extension()
        .and_then(|e| e.to_str())
        .map(|e| e.eq_ignore_ascii_case("onnx"))
        .unwrap_or(false);
    
    // Hanya support ONNX models (semua inference di Rust)
    if !is_onnx {
        return Err(format!(
            "Model format tidak didukung: {}\n\n\
            Hanya model ONNX (.onnx) yang didukung untuk inference.\n\
            Model .pt harus di-convert ke .onnx terlebih dahulu.\n\n\
            Saat add model .pt via UI, akan otomatis convert ke .onnx.\n\
            Jika conversion gagal, pastikan sidecar Python sudah di-build: 'npm run build:sidecar'",
            model_path
        ).into());
    }
    
    // Gunakan native Rust inference dengan ONNX
    run_processing_onnx(
        folder,
        config,
        model_path,
        cancel,
        on_log,
        on_progress,
        on_done,
    )
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

