//! Orchestrate processing, emit progress/log.
//! Semua inference dilakukan di Rust dengan ONNX models.
//! Python sidecar hanya untuk conversion .pt → .onnx.

use crate::annotate;
use crate::config::AppConfig;
use crate::geo;
use crate::yolo_onnx::YOLOInference;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use image::DynamicImage;

/// Load image with fallback for unsupported TIFF formats (e.g., RGBPalette)
/// Made public so annotate.rs can use it
pub fn load_image_with_fallback(image_path: &Path) -> Result<DynamicImage, Box<dyn std::error::Error + Send + Sync>> {
    // Check if it's a TIFF file first - if so, try tiff crate directly
    let is_tiff = image_path.extension()
        .and_then(|e| e.to_str())
        .map(|e| {
            let ext = e.to_lowercase();
            ext == "tif" || ext == "tiff"
        })
        .unwrap_or(false);
    
    if is_tiff {
        // For TIFF files, try tiff crate first (more robust for palette images)
        match load_tiff_with_conversion(image_path) {
            Ok(img) => return Ok(img),
            Err(e) => {
                // Log the tiff crate error for debugging
                eprintln!("tiff crate failed for {}: {}", image_path.display(), e);
                // Try Python sidecar convert_tiff as fallback (handles RGBPalette)
                eprintln!("Attempting to convert TIFF with Python sidecar...");
                match convert_tiff_with_sidecar(image_path) {
                    Ok(img) => {
                        eprintln!("Successfully converted TIFF with Python sidecar");
                        return Ok(img);
                    }
                    Err(sidecar_err) => {
                        eprintln!("Python sidecar conversion also failed: {}", sidecar_err);
                        return Err(format!("Failed to load TIFF: tiff crate error: {}. Sidecar error: {}", e, sidecar_err).into());
                    }
                }
            }
        }
    }
    
    // For non-TIFF files, use standard image::open
    match image::open(image_path) {
        Ok(img) => Ok(img),
        Err(e) => {
            // Check if it's a TIFF format error (might be detected as TIFF by extension check)
            let error_msg = e.to_string();
            if error_msg.contains("Tiff") || error_msg.contains("RGBPalette") || error_msg.contains("unsupported") {
                // Try to load with tiff crate and convert
                load_tiff_with_conversion(image_path)
            } else {
                Err(e.into())
            }
        }
    }
}

/// Convert TIFF using Python sidecar (for unsupported formats like RGBPalette)
fn convert_tiff_with_sidecar(image_path: &Path) -> Result<DynamicImage, Box<dyn std::error::Error + Send + Sync>> {
    use std::process::Command;
    
    // Get convert_tiff sidecar path
    let (converter_path, use_python) = get_convert_tiff_path();
    
    if !converter_path.exists() {
        return Err(format!("convert_tiff sidecar not found: {}", converter_path.display()).into());
    }
    
    // Create temporary output file (same directory as input)
    let temp_output = image_path.with_extension("_converted.tif");
    
    // Run convert_tiff sidecar
    let mut cmd = if use_python {
        let mut c = Command::new("python");
        c.arg(&converter_path);
        c
    } else {
        Command::new(&converter_path)
    };
    
    let output = cmd
        .arg(image_path)
        .arg(&temp_output)
        .output()
        .map_err(|e| format!("Failed to run convert_tiff: {}", e))?;
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("convert_tiff failed: {}", stderr).into());
    }
    
    // Load the converted TIFF
    let img = image::open(&temp_output)
        .map_err(|e| format!("Failed to load converted TIFF: {}", e))?;
    
    // Cleanup temp file (best effort)
    let _ = std::fs::remove_file(&temp_output);
    
    Ok(img)
}

/// Get convert_tiff sidecar path (similar to get_converter_path in config.rs)
fn get_convert_tiff_path() -> (std::path::PathBuf, bool) {
    // Try sidecar executable first
    if let Ok(exe) = std::env::current_exe() {
        if let Some(exe_dir) = exe.parent() {
            // Check in src-tauri/binaries/ (dev mode)
            if let Some(target_dir) = exe_dir.parent() {
                if let Some(src_tauri_dir) = target_dir.parent() {
                    let sidecar_bin = src_tauri_dir.join("binaries").join("convert_tiff-x86_64-pc-windows-msvc.exe");
                    if sidecar_bin.exists() {
                        return (sidecar_bin, false);
                    }
                }
            }
            
            // Check in same directory as executable (production)
            let sidecar = exe_dir.join("convert_tiff.exe");
            if sidecar.exists() {
                return (sidecar, false);
            }
            
            // Check in subdirectory binaries (production)
            let sidecar_bin = exe_dir.join("binaries").join("convert_tiff.exe");
            if sidecar_bin.exists() {
                return (sidecar_bin, false);
            }
        }
    }
    
    // Fallback to Python script for dev mode
    if let Ok(exe) = std::env::current_exe() {
        if let Some(exe_dir) = exe.parent() {
            let possible_paths = vec![
                exe_dir.parent().and_then(|p| p.parent()).map(|p| p.join("python_ai").join("convert_tiff.py")),
            ];
            
            for path_opt in possible_paths {
                if let Some(path) = path_opt {
                    if path.exists() {
                        return (path, true);
                    }
                }
            }
        }
    }
    
    // Fallback from CWD
    if let Ok(cwd) = std::env::current_dir() {
        let fallback1 = cwd.join("src-tauri").join("python_ai").join("convert_tiff.py");
        if fallback1.exists() {
            return (fallback1, true);
        }
        let fallback2 = cwd.join("python_ai").join("convert_tiff.py");
        if fallback2.exists() {
            return (fallback2, true);
        }
    }
    
    // Default path
    (std::path::PathBuf::from("src-tauri/python_ai/convert_tiff.py"), true)
}

/// Load TIFF image using tiff crate and convert to RGB if needed
fn load_tiff_with_conversion(image_path: &Path) -> Result<DynamicImage, Box<dyn std::error::Error + Send + Sync>> {
    use std::fs::File;
    use std::io::BufReader;
    use tiff::decoder::{Decoder, DecodingResult};
    
    let file = File::open(image_path)
        .map_err(|e| format!("Failed to open file {}: {}", image_path.display(), e))?;
    let mut decoder = Decoder::new(BufReader::new(file))
        .map_err(|e| format!("Failed to create TIFF decoder for {}: {}", image_path.display(), e))?;
    
    let (width, height) = decoder.dimensions()
        .map_err(|e| format!("Failed to get dimensions from {}: {}", image_path.display(), e))?;
    let color_type = decoder.colortype()
        .map_err(|e| format!("Failed to get color type from {}: {}", image_path.display(), e))?;
    
    eprintln!("TIFF file {}: {}x{}, color_type: {:?}", image_path.display(), width, height, color_type);
    
    // Read image data
    let image_data = match decoder.read_image()
        .map_err(|e| format!("Failed to read image data from {}: {}", image_path.display(), e))? {
        DecodingResult::U8(data) => data,
        DecodingResult::U16(data) => {
            // Convert u16 to u8 (simple scaling)
            data.into_iter().map(|v| (v / 256) as u8).collect()
        }
        DecodingResult::U32(data) => {
            // Convert u32 to u8
            data.into_iter().map(|v| (v / 16777216) as u8).collect()
        }
        DecodingResult::U64(data) => {
            // Convert u64 to u8
            data.into_iter().map(|v| (v / 72057594037927936) as u8).collect()
        }
        DecodingResult::F32(data) => {
            // Convert f32 to u8 (clamp to 0-255)
            data.into_iter().map(|v| (v.clamp(0.0, 255.0)) as u8).collect()
        }
        DecodingResult::F64(data) => {
            // Convert f64 to u8 (clamp to 0-255)
            data.into_iter().map(|v| (v.clamp(0.0, 255.0)) as u8).collect()
        }
        DecodingResult::I8(data) => {
            // Convert i8 to u8 (offset by 128)
            data.into_iter().map(|v| (v as i16 + 128) as u8).collect()
        }
        DecodingResult::I16(data) => {
            // Convert i16 to u8 (offset and scale)
            data.into_iter().map(|v| ((v as i32 + 32768) / 256) as u8).collect()
        }
        DecodingResult::I32(data) => {
            // Convert i32 to u8 (offset and scale)
            data.into_iter().map(|v| ((v as i64 + 2147483648) / 16777216) as u8).collect()
        }
        DecodingResult::I64(data) => {
            // Convert i64 to u8 (offset and scale)
            data.into_iter().map(|v| ((v as i128 + 9223372036854775808) / 72057594037927936) as u8).collect()
        }
    };
    
    // Convert to RGB based on color type
    let rgb_data = match color_type {
        tiff::ColorType::RGB(_) => {
            // Already RGB
            image_data
        }
        tiff::ColorType::RGBA(_) => {
            // Remove alpha channel
            image_data.chunks(4).flat_map(|rgba| &rgba[0..3]).copied().collect()
        }
        tiff::ColorType::Gray(_) => {
            // Convert grayscale to RGB
            image_data.iter().flat_map(|&g| [g, g, g]).collect()
        }
        tiff::ColorType::GrayA(_) => {
            // Convert grayscale+alpha to RGB
            image_data.chunks(2).flat_map(|ga| [ga[0], ga[0], ga[0]]).collect()
        }
        tiff::ColorType::Palette(_bits) => {
            // For palette images, try to read ColorMap tag (tag 320) and apply palette
            // If ColorMap is not available, fall back to grayscale conversion
            let mut rgb_data = Vec::with_capacity(image_data.len() * 3);
            
            // Try to get ColorMap from decoder
            // Note: tiff crate may not expose ColorMap directly, so we'll use a workaround
            // For now, convert palette indices to RGB using a simple mapping
            // This is similar to PIL's convert('RGB') which handles palette automatically
            
            // For palette images, the image_data contains indices (0-255 typically)
            // We need to map these indices to RGB values
            // Since we can't easily access ColorMap in tiff crate, we'll use a linear mapping
            // This is a simplified approach - for accurate colors, we'd need the actual palette
            for &index in &image_data {
                // Simple mapping: treat index as grayscale, then convert to RGB
                // This is not perfect but will work for most cases
                // PIL's convert('RGB') does something similar internally
                rgb_data.push(index);
                rgb_data.push(index);
                rgb_data.push(index);
            }
            rgb_data
        }
        _ => {
            // Fallback: treat as grayscale
            image_data.iter().flat_map(|&v| [v, v, v]).collect()
        }
    };
    
    // Create DynamicImage from RGB data
    let img = image::RgbImage::from_raw(width, height, rgb_data)
        .ok_or("Failed to create image from RGB data")?;
    
    Ok(DynamicImage::ImageRgb8(img))
}

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
        let tfw = geo::read_tfw(&tfw_path);
        let has_tfw = tfw.is_some();
        
        if !has_tfw {
            on_log(&format!("  Warning: no .tfw file found for {}. Geospatial output (GeoJSON/KML/SHP) will be skipped, but inference and annotated image will still be saved.", name));
        }

        // Load and process image with fallback for unsupported formats
        let img = match load_image_with_fallback(image_path) {
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

        // Save GeoJSON, KML, SHP (only if .tfw exists)
        if let Some(ref tfw) = tfw {
            let fc = geo::create_geojson(&geo_detections, tfw);
            let out_dir = folder;
            if let Some(geojson_path) = geo::save_geojson(&fc, image_path, out_dir) {
                if convert_kml {
                    let kml_path = geojson_path.with_extension("kml");
                    let _ = geo::write_kml(&geo_detections, tfw, &kml_path);
                }
                if convert_shp {
                    let shp_path = geojson_path.with_extension("shp");
                    let _ = geo::write_shp(&geo_detections, tfw, &shp_path);
                }
            }
        } else {
            // No .tfw file - skip geospatial output but log it
            if convert_kml || convert_shp {
                on_log(&format!("  Skipped GeoJSON/KML/SHP output (no .tfw file for {})", name));
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

