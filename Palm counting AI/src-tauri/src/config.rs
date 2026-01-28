//! SQLite config and YOLO model library.

use rusqlite::Connection;
use std::path::{Path, PathBuf};

fn app_dir() -> PathBuf {
    dirs::data_local_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("palm-counting-ai")
}

fn db_path() -> PathBuf {
    app_dir().join("database.db")
}

fn models_dir() -> PathBuf {
    app_dir().join("models")
}

fn open_db() -> Result<Connection, rusqlite::Error> {
    let p = db_path();
    std::fs::create_dir_all(p.parent().unwrap()).ok();
    let conn = Connection::open(&p)?;
    conn.execute_batch("PRAGMA foreign_keys = ON;")?;
    Ok(conn)
}

pub fn setup_db() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let conn = open_db()?;
    conn.execute(
        r#"
        CREATE TABLE IF NOT EXISTS configuration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT,
            imgsz TEXT,
            iou TEXT,
            conf TEXT,
            convert_shp TEXT,
            convert_kml TEXT,
            max_det TEXT,
            line_width TEXT,
            show_labels TEXT,
            show_conf TEXT,
            status_blok TEXT,
            save_annotated TEXT,
            last_folder_path TEXT,
            device TEXT,
            active_model_id INTEGER
        )
        "#,
        [],
    )?;

    conn.execute(
        r#"
        CREATE TABLE IF NOT EXISTS yolo_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        "#,
        [],
    )?;

    // Add columns if missing (migrations)
    let add_col = |name: &str, sql: &str| -> Result<(), rusqlite::Error> {
        let exists: bool = conn.query_row(
            "SELECT COUNT(1) FROM pragma_table_info('configuration') WHERE name = ?1",
            [name],
            |r| r.get(0),
        )?;
        if !exists {
            conn.execute(sql, [])?;
        }
        Ok(())
    };
    add_col("device", "ALTER TABLE configuration ADD COLUMN device TEXT DEFAULT 'auto'")?;
    add_col("active_model_id", "ALTER TABLE configuration ADD COLUMN active_model_id INTEGER")?;

    let count: i64 = conn.query_row("SELECT COUNT(*) FROM configuration", [], |r| r.get(0))?;
    if count == 0 {
        conn.execute(
            r#"
            INSERT INTO configuration (
                model, imgsz, iou, conf, convert_shp, convert_kml,
                max_det, line_width, show_labels, show_conf, status_blok, save_annotated,
                last_folder_path, device, active_model_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            "#,
            rusqlite::params![
                "",
                "12800",
                "0.2",
                "0.2",
                "true",
                "false",
                "10000",
                "3",
                "true",
                "false",
                "Full Blok",
                "true",
                None::<String>,
                "auto",
                None::<i64>,
            ],
        )?;
    }
    Ok(())
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct AppConfig {
    pub model: Option<String>,
    pub imgsz: String,
    pub iou: String,
    pub conf: String,
    pub convert_shp: String,
    pub convert_kml: String,
    pub max_det: String,
    pub line_width: String,
    pub show_labels: String,
    pub show_conf: String,
    pub status_blok: String,
    pub save_annotated: String,
    pub last_folder_path: Option<String>,
    pub device: String,
    pub active_model_id: Option<i64>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            model: None,
            imgsz: "12800".into(),
            iou: "0.2".into(),
            conf: "0.2".into(),
            convert_shp: "true".into(),
            convert_kml: "false".into(),
            max_det: "10000".into(),
            line_width: "3".into(),
            show_labels: "true".into(),
            show_conf: "false".into(),
            status_blok: "Full Blok".into(),
            save_annotated: "true".into(),
            last_folder_path: None,
            device: "auto".into(),
            active_model_id: None,
        }
    }
}

pub fn load_config() -> Result<AppConfig, Box<dyn std::error::Error + Send + Sync>> {
    setup_db()?;
    let conn = open_db()?;
    let mut stmt = conn.prepare(
        "SELECT model, imgsz, iou, conf, convert_shp, convert_kml, max_det, line_width,
                show_labels, show_conf, status_blok, save_annotated, last_folder_path, device, active_model_id
         FROM configuration ORDER BY id DESC LIMIT 1",
    )?;
    let row = stmt.query_row([], |r| {
        Ok(AppConfig {
            model: r.get(0).ok(),
            imgsz: r.get::<_, String>(1).unwrap_or_else(|_| "12800".into()),
            iou: r.get::<_, String>(2).unwrap_or_else(|_| "0.2".into()),
            conf: r.get::<_, String>(3).unwrap_or_else(|_| "0.2".into()),
            convert_shp: r.get::<_, String>(4).unwrap_or_else(|_| "true".into()),
            convert_kml: r.get::<_, String>(5).unwrap_or_else(|_| "false".into()),
            max_det: r.get::<_, String>(6).unwrap_or_else(|_| "10000".into()),
            line_width: r.get::<_, String>(7).unwrap_or_else(|_| "3".into()),
            show_labels: r.get::<_, String>(8).unwrap_or_else(|_| "true".into()),
            show_conf: r.get::<_, String>(9).unwrap_or_else(|_| "false".into()),
            status_blok: r.get::<_, String>(10).unwrap_or_else(|_| "Full Blok".into()),
            save_annotated: r.get::<_, String>(11).unwrap_or_else(|_| "true".into()),
            last_folder_path: r.get(12).ok(),
            device: r.get::<_, String>(13).unwrap_or_else(|_| "auto".into()),
            active_model_id: r.get(14).ok(),
        })
    });

    match row {
        Ok(c) => Ok(c),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(AppConfig::default()),
        Err(e) => Err(e.into()),
    }
}

pub fn save_config(c: &AppConfig) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    setup_db()?;
    let conn = open_db()?;
    conn.execute(
        r#"
        INSERT INTO configuration (
            model, imgsz, iou, conf, convert_shp, convert_kml,
            max_det, line_width, show_labels, show_conf, status_blok, save_annotated,
            last_folder_path, device, active_model_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#,
        rusqlite::params![
            c.model.as_deref().unwrap_or(""),
            &c.imgsz,
            &c.iou,
            &c.conf,
            &c.convert_shp,
            &c.convert_kml,
            &c.max_det,
            &c.line_width,
            &c.show_labels,
            &c.show_conf,
            &c.status_blok,
            &c.save_annotated,
            c.last_folder_path.as_deref(),
            &c.device,
            c.active_model_id,
        ],
    )?;
    Ok(())
}

#[derive(Debug, serde::Serialize)]
pub struct YoloModel {
    pub id: i64,
    pub name: String,
    pub path: String,
    pub is_active: bool,
}

pub fn list_models() -> Result<Vec<YoloModel>, Box<dyn std::error::Error + Send + Sync>> {
    setup_db()?;
    let conn = open_db()?;
    let active: Option<i64> = conn
        .query_row("SELECT active_model_id FROM configuration ORDER BY id DESC LIMIT 1", [], |r| {
            r.get(0)
        })
        .ok()
        .and_then(|x: Option<i64>| x);

    let mut stmt = conn.prepare("SELECT id, name, path FROM yolo_models ORDER BY id")?;
    let rows = stmt.query_map([], |r| {
        let id: i64 = r.get(0)?;
        let name: String = r.get(1)?;
        let path: String = r.get(2)?;
        Ok(YoloModel {
            id,
            name,
            path,
            is_active: active == Some(id),
        })
    })?;
    let out: Result<Vec<_>, _> = rows.collect();
    Ok(out?)
}

pub fn add_model(name: String, source_path: &Path) -> Result<YoloModel, Box<dyn std::error::Error + Send + Sync>> {
    setup_db()?;
    std::fs::create_dir_all(models_dir())?;
    
    let is_pt = source_path.extension()
        .and_then(|e| e.to_str())
        .map(|e| e.eq_ignore_ascii_case("pt"))
        .unwrap_or(false);
    
    let is_onnx = source_path.extension()
        .and_then(|e| e.to_str())
        .map(|e| e.eq_ignore_ascii_case("onnx"))
        .unwrap_or(false);
    
    let final_path = if is_pt {
        // Auto-convert .pt to .onnx
        let base = source_path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("model");
        let onnx_dest = models_dir().join(format!("{}.onnx", base));
        let onnx_dest = unique_path_with_ext(&onnx_dest, "onnx");
        
        // Copy .pt first (keep original)
        let pt_dest = models_dir().join(format!("{}.pt", base));
        let pt_dest = unique_path_with_ext(&pt_dest, "pt");
        std::fs::copy(source_path, &pt_dest)?;
        
        // Convert to ONNX using Python sidecar
        let imgsz = load_config()
            .map(|c| c.imgsz.parse::<u32>().unwrap_or(1280))
            .unwrap_or(1280);
        
        // Try to use sidecar Python worker for conversion
        let (converter_path, use_python) = get_converter_path();
        eprintln!("Converter path: {} (use_python: {})", converter_path.display(), use_python);
        eprintln!("Converter exists: {}", converter_path.exists());
        
        let conversion_success = if converter_path.exists() {
            // Use sidecar Python worker with --convert mode
            let mut cmd = if use_python {
                // Fallback to Python script for dev mode
                eprintln!("Using Python command: python {}", converter_path.display());
                let mut c = std::process::Command::new("python");
                c.arg(&converter_path);
                c
            } else {
                // Use sidecar executable
                eprintln!("Using sidecar executable: {}", converter_path.display());
                std::process::Command::new(&converter_path)
            };
            
            let output = cmd
                .arg("--convert")
                .arg(&pt_dest)
                .arg(&onnx_dest)
                .arg(&imgsz.to_string())
                .output();
            
            match output {
                Ok(o) if o.status.success() && onnx_dest.exists() => {
                    eprintln!("Conversion successful!");
                    true
                }
                Ok(o) => {
                    // Log stderr if available
                    let stdout = String::from_utf8_lossy(&o.stdout);
                    let stderr = String::from_utf8_lossy(&o.stderr);
                    eprintln!("Conversion failed. Exit code: {}", o.status.code().unwrap_or(-1));
                    if !stdout.is_empty() {
                        eprintln!("Conversion stdout: {}", stdout);
                    }
                    if !stderr.is_empty() {
                        eprintln!("Conversion stderr: {}", stderr);
                    }
                    false
                }
                Err(e) => {
                    eprintln!("Failed to run converter for conversion: {}", e);
                    false
                }
            }
        } else {
            eprintln!("Converter path does not exist: {}", converter_path.display());
            false
        };
        
        if conversion_success {
            onnx_dest.to_string_lossy().into_owned()
        } else {
            // Conversion failed, use .pt
            pt_dest.to_string_lossy().into_owned()
        }
    } else if is_onnx {
        // Already ONNX, just copy
        let base = source_path
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("model");
        let dest = models_dir().join(base);
        let dest = unique_path(&dest);
        std::fs::copy(source_path, &dest)?;
        dest.to_string_lossy().into_owned()
    } else {
        // Unknown format, copy as-is
        let base = source_path
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("model");
        let dest = models_dir().join(base);
        let dest = unique_path(&dest);
        std::fs::copy(source_path, &dest)?;
        dest.to_string_lossy().into_owned()
    };

    let conn = open_db()?;
    conn.execute("INSERT INTO yolo_models (name, path) VALUES (?1, ?2)", [&name, &final_path])?;
    let id = conn.last_insert_rowid();
    let active: Option<i64> = conn
        .query_row("SELECT active_model_id FROM configuration ORDER BY id DESC LIMIT 1", [], |r| {
            r.get(0)
        })
        .ok()
        .and_then(|x: Option<i64>| x);
    Ok(YoloModel {
        id,
        name,
        path: final_path,
        is_active: active == Some(id),
    })
}

/// Get converter path (sidecar atau Python script untuk dev mode)
/// Returns (path, use_python_command)
fn get_converter_path() -> (PathBuf, bool) {
    // Cari sidecar yang valid terlebih dahulu
    // Untuk dev mode, executable di target/debug/, sidecar di src-tauri/binaries/
    if let Ok(exe) = std::env::current_exe() {
        if let Some(exe_dir) = exe.parent() {
            // Cek di src-tauri/binaries/ (untuk dev mode)
            // target/debug/ -> target/ -> src-tauri/ -> binaries/
            if let Some(target_dir) = exe_dir.parent() {
                if let Some(src_tauri_dir) = target_dir.parent() {
                    let sidecar_bin = src_tauri_dir.join("binaries").join("infer_worker-x86_64-pc-windows-msvc.exe");
                    if sidecar_bin.exists() {
                        if let Ok(metadata) = std::fs::metadata(&sidecar_bin) {
                            if metadata.len() > 1_000_000 {
                                eprintln!("Using valid sidecar: {}", sidecar_bin.display());
                                return (sidecar_bin, false);
                            }
                        }
                    }
                }
            }
            
            // Cek di directory yang sama dengan executable (untuk production)
            let sidecar = exe_dir.join("infer_worker.exe");
            if sidecar.exists() {
                if let Ok(metadata) = std::fs::metadata(&sidecar) {
                    if metadata.len() > 1_000_000 {
                        eprintln!("Using valid sidecar: {}", sidecar.display());
                        return (sidecar, false);
                    }
                }
            }
            
            // Cek di subdirectory binaries (untuk production)
            let sidecar_bin = exe_dir.join("binaries").join("infer_worker.exe");
            if sidecar_bin.exists() {
                if let Ok(metadata) = std::fs::metadata(&sidecar_bin) {
                    if metadata.len() > 1_000_000 {
                        eprintln!("Using valid sidecar: {}", sidecar_bin.display());
                        return (sidecar_bin, false);
                    }
                }
            }
        }
    }
    
    // Fallback ke Python script untuk dev mode
    // Cari python_ai/infer_worker.py di src-tauri/ (karena sudah dipindah ke src-tauri/)
    // Untuk dev mode, executable di target/debug/, src-tauri/ adalah parent dari target/
    if let Ok(exe) = std::env::current_exe() {
        if let Some(exe_dir) = exe.parent() {
            // target/debug/ -> target/ -> src-tauri/
            let possible_paths = vec![
                // Dari target/debug/ -> target/ -> src-tauri/ -> python_ai/
                exe_dir.parent().and_then(|p| p.parent()).map(|p| p.join("python_ai").join("infer_worker.py")),
            ];
            
            for path_opt in possible_paths {
                if let Some(path) = path_opt {
                    if path.exists() {
                        eprintln!("Using Python script for conversion: {}", path.display());
                        return (path, true);
                    }
                }
            }
        }
    }
    
    // Fallback: coba dari current working directory (biasanya project root saat dev)
    // Tapi sekarang python_ai ada di src-tauri/, jadi coba src-tauri/python_ai/
    if let Ok(cwd) = std::env::current_dir() {
        // Coba dari project root -> src-tauri/python_ai/
        let fallback1 = cwd.join("src-tauri").join("python_ai").join("infer_worker.py");
        if fallback1.exists() {
            eprintln!("Using Python script for conversion (from CWD/src-tauri): {}", fallback1.display());
            return (fallback1, true);
        }
        // Atau langsung dari CWD jika CWD adalah src-tauri/
        let fallback2 = cwd.join("python_ai").join("infer_worker.py");
        if fallback2.exists() {
            eprintln!("Using Python script for conversion (from CWD): {}", fallback2.display());
            return (fallback2, true);
        }
    }
    
    // Jika tidak ditemukan, return path yang diharapkan (untuk error message)
    eprintln!("WARNING: No converter found, will try Python script from src-tauri/python_ai/");
    if let Ok(exe) = std::env::current_exe() {
        if let Some(exe_dir) = exe.parent() {
            if let Some(target_dir) = exe_dir.parent() {
                if let Some(src_tauri_dir) = target_dir.parent() {
                    let python_script = src_tauri_dir.join("python_ai").join("infer_worker.py");
                    return (python_script, true);
                }
            }
        }
    }
    
    (PathBuf::from("src-tauri/python_ai/infer_worker.py"), true)
}

fn unique_path_with_ext(p: &PathBuf, ext: &str) -> PathBuf {
    if !p.exists() {
        return p.clone();
    }
    let stem = p.file_stem().and_then(|s| s.to_str()).unwrap_or("model");
    let parent = p.parent().unwrap();
    for n in 1..10000 {
        let candidate = parent.join(format!("{}_{}.{}", stem, n, ext));
        if !candidate.exists() {
            return candidate;
        }
    }
    parent.join(format!("{}_{}.{}", stem, 0, ext))
}

fn unique_path(p: &PathBuf) -> PathBuf {
    if !p.exists() {
        return p.clone();
    }
    let stem = p.file_stem().and_then(|s| s.to_str()).unwrap_or("model");
    let ext = p.extension().and_then(|s| s.to_str()).unwrap_or("pt");
    let parent = p.parent().unwrap();
    for n in 1..10000 {
        let candidate = parent.join(format!("{}_{}.{}", stem, n, ext));
        if !candidate.exists() {
            return candidate;
        }
    }
    parent.join(format!("{}_{}.{}", stem, 0, ext))
}

pub fn remove_model(id: i64) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    setup_db()?;
    let conn = open_db()?;
    let path: Option<String> = conn.query_row("SELECT path FROM yolo_models WHERE id = ?1", [id], |r| r.get(0))?;
    conn.execute("DELETE FROM yolo_models WHERE id = ?1", [id])?;
    if let Some(p) = path {
        let _ = std::fs::remove_file(&p);
    }
    Ok(())
}

pub fn set_active_model(id: i64) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let mut c = load_config()?;
    c.active_model_id = Some(id);
    save_config(&c)
}

pub fn get_active_model_path() -> Result<Option<String>, Box<dyn std::error::Error + Send + Sync>> {
    let c = load_config()?;
    let aid = match c.active_model_id {
        Some(x) => x,
        None => return Ok(None),
    };
    let conn = open_db()?;
    let path: Option<String> = conn.query_row("SELECT path FROM yolo_models WHERE id = ?1", [aid], |r| r.get(0))?;
    Ok(path)
}
