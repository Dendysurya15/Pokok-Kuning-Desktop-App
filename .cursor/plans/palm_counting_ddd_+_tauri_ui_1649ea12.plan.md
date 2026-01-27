---
name: Palm Counting DDD + Tauri UI
overview: Rebuild Palm Counting AI dengan arsitektur **hybrid** – Python minimal hanya untuk YOLO (.pt) inference; Rust untuk UI, config, geo export, specs, CLI, orchestration. Tauri + React + shadcn di frontend.
todos:
  - id: infer-worker
    content: Buat Python inference worker (stdin/stdout JSON), load .pt once, infer per image
    status: completed
  - id: rust-geo
    content: Rust – baca .tfw, GeoJSON/KML/SHP export, gambar annotated (image/opencv)
    status: completed
  - id: rust-config-specs
    content: Rust – config SQLite, yolo_models table, specs sysinfo/nvidia-smi, list/add/remove/set_active model
    status: completed
  - id: tauri-commands
    content: Tauri commands – select_folder, list/add/remove/set_active model, get_specs, config, run_processing
    status: completed
  - id: frontend-shadcn
    content: Frontend React + Tailwind + shadcn, menu Dashboard / YOLO Model / Settings, halaman utama
    status: in_progress
  - id: yolomodel-menu
    content: YOLO Model library UI (list, Add, Remove, Set default) + Rust add/remove/set_active_model
    status: pending
  - id: integration-test
    content: Integrasi end-to-end, test run processing, deploy
    status: pending
isProject: false
---

# Palm Counting AI – Rebuild Hybrid (Rust + Python Minimal)

## 1. Arsitektur hybrid

- **Python:** Hanya YOLO. Load `.pt` sekali, terima request per gambar lewat stdin (JSON), return detections (JSON) ke stdout. Subprocess **long-lived**.
- **Rust:** UI (Tauri), config, geo export, .tfw, annotated images, specs, CLI, orchestration. Rust spawn Python inference worker, kirim path gambar + config, terima detections, lakukan sisanya.
```mermaid
flowchart TB
  subgraph UI
    FolderPicker
    ModelSelect
    RunButton
    ProgressSection
    LogViewer
    StatusCard
  end

  subgraph Rust
    Commands[Tauri Commands]
    Config[Config SQLite]
    Specs[sysinfo / nvidia-smi]
    Geo[GeoJSON KML SHP]
    Tfw[Read .tfw]
    Annotate[Draw bbox save image]
    Orchestrator[Run processing loop]
  end

  subgraph Python
    InferWorker[Inference worker]
    YOLO[YOLO .pt]
  end

  RunButton --> Commands
  Commands --> Orchestrator
  Orchestrator -->|stdin JSON| InferWorker
  InferWorker --> YOLO
  InferWorker -->|stdout JSON| Orchestrator
  Orchestrator --> Tfw
  Orchestrator --> Geo
  Orchestrator --> Annotate
  Commands --> Config
  Commands --> Specs
  Commands --> ProgressSection
  Commands --> LogViewer
  Commands --> StatusCard
```


---

## 2. Target struktur folder

```
Palm counting AI/
├── python_ai/                    # Python minimal (inference only)
│   ├── infer_worker.py           # stdin/stdout JSON, load .pt, predict
│   └── requirements.txt          # ultralytics, torch, Pillow
├── models/                       # YOLO model library (user-addable .pt)
│   └── *.pt                      # salinan dari user; DB yolo_models simpan path
├── src/                          # Frontend Tauri (React + shadcn)
├── src-tauri/
│   └── src/
│       ├── lib.rs                # Tauri commands
│       ├── config.rs             # SQLite config + yolo_models
│       ├── specs.rs              # sysinfo, nvidia-smi
│       ├── geo.rs                # .tfw, GeoJSON, KML, SHP
│       ├── annotate.rs           # draw bbox, save image
│       └── infer.rs              # spawn Python worker, send/recv JSON
└── ...
```

**Tidak ada** `python_ai` DDD. Inference worker + `requirements.txt` saja. Model dipakai saat run = path dari library (`models/` + DB).

---

## 3. Python inference worker

### 3.1 Tanggung jawab

- Baca JSON lines dari **stdin**. Setiap baris = satu request.
- Request: `{"image": "/path/to.jpg", "model": "/path/model.pt", "imgsz": 1280, "conf": 0.2, "iou": 0.2, "device": "cuda"}`.
- Load model `.pt` **sekali** saat pertama dapat `model` path (atau saat startup).
- Untuk tiap request: `predict` → ambil boxes (x1,y1,x2,y2, class_id, conf) → tulis **satu** JSON line ke **stdout**.
- Response: `{"detections": [{"x1", "y1", "x2", "y2", "class_id", "conf"}, ...], "error": null}`. Jika gagal: `{"detections": [], "error": "..."}`.

### 3.2 Flow

1. Rust spawn `python python_ai/infer_worker.py` (atau `python -m python_ai.infer_worker`).
2. Rust kirim N request (satu per gambar); worker baca stdin, infer, tulis stdout.
3. Rust baca stdout line-by-line, parse JSON, lanjut ke .tfw → geo → annotate.

### 3.3 Referensi

- Logika detect dari [processor.py](pokok_kuning_gui/core/processor.py) `detect_objects` (tanpa geo, tanpa config DB). Hanya YOLO load + predict + format output.

---

## 4. Rust – config, specs, geo, annotate

### 4.1 Config

- **Storage:** SQLite di app data. Schema: `configuration` (imgsz, iou, conf, device, convert_kml, convert_shp, save_annotated, last_folder_path, max_det, line_width, show_labels, show_conf, **active_model_id**); **`yolo_models`** (id, name, path, created_at).
- **Crate:** `rusqlite`. Commands `load_config`, `save_config`; model library pakai `yolo_models` + `active_model_id`.

### 4.2 Specs

- **CPU / RAM:** `sysinfo`.
- **GPU:** Parse `nvidia-smi` atau pakai crate yang wrap. Tauri command `get_system_specs` return JSON untuk StatusCard.

### 4.3 Geo

- **.tfw:** Baca 6 float dari file. Pixel → map: `map_x = ulx + x * px_w`, `map_y = uly + y * py_h` (ikuti [processor](pokok_kuning_gui/core/processor.py) `image_to_map_coords`).
- **GeoJSON:** Crate `geojson`. Dari detections (center bbox) + .tfw → FeatureCollection → write file.
- **KML:** Crate atau tulis manual (format sederhana).
- **Shapefile:** Crate `geozero`, `shapefile`, atau equivalent. GeoJSON → Shapefile jika `convert_shp` true.

### 4.4 Annotated images

- **Rust:** Load image (`image` crate atau `opencv`), gambar rectangle + label dari detections, simpan ke `folder/annotated/`. Pakai `line_width`, `show_labels`, `show_conf` dari config.

### 4.5 YOLO Model Library (bukan sekadar list)

- **Konsep:** User punya **library model** yang dia isi sendiri. Bisa tambah banyak `.pt`, simpan, lalu pilih mana yang dipakai untuk run. Dinamis.
- **Storage:** 
  - Folder app `models/` (atau path library dari config): simpan salinan `.pt` yang user tambah. Atau simpan **path** saja kalau user pilih "link external" (opsional).
  - DB/config: tabel `yolo_models` — `id`, `name` (display), `path`, `is_active` / `active_model_id` di config.
- **CRUD:** `add_model` (browse .pt → copy ke library + insert), `remove_model`, `list_models` (dari library). `set_active_model(id)` simpan ke config.
- **UI:** Menu **YOLO Model** — list model, tombol Add, Remove, Set as default. Saat run, pakai model yang aktif.

---

## 5. Tauri commands

| Command | Implementasi |

|--------|---------------|

| `select_folder` | Dialog pilih folder. Return path. |

| `select_model_file` | Dialog pilih file `.pt`. Return path (untuk Add model). |

| `list_models` | Dari library (DB + `models/`). Return list `{id, name, path, isActive}`. |

| `add_model` | Browse .pt → copy ke `models/` (atau simpan path) → insert DB. Return model. |

| `remove_model` | Hapus dari DB; optional hapus file di `models/` jika kita yang copy. |

| `set_active_model` | Set `active_model_id` di config. Saat run pakai ini. |

| `get_system_specs` | Rust `sysinfo` + GPU. Return JSON. |

| `load_config` | Rust SQLite. Return config (termasuk `active_model_id`). |

| `save_config` | Rust simpan ke SQLite. |

| `run_processing` | Spawn Python worker, pakai model aktif dari library, loop gambar → .tfw → geo → annotate. Emit progress + log. |

**Tidak ada** invoke Python untuk config, specs, atau model library. Hanya `run_processing` yang pakai Python.

---

## 6. Contract JSON (Rust ↔ Python)

**Rust → Python (per gambar):**

```json
{"image": "C:/data/a1.jpg", "model": "C:/app/model/yolov8n-pokok-kuning.pt", "imgsz": 1280, "conf": 0.2, "iou": 0.2, "device": "cuda"}
```

**Python → Rust:**

```json
{"detections": [{"x1": 100, "y1": 200, "x2": 150, "y2": 250, "class_id": 0, "conf": 0.92}], "error": null}
```

Rust hitung center dari bbox, pakai .tfw → koordinat peta, buat GeoJSON/KML/SHP dan optional annotated image.

---

## 7. UI (Tauri + React + shadcn)

### 7.1 Stack

- **Frontend:** React + TypeScript + Vite. Ganti Preact → React.
- **Styling:** Tailwind v4 + shadcn/ui (`pnpm dlx shadcn@latest init`).
- **Tauri:** [src-tauri](Palm counting AI/src-tauri/); commands di atas.

### 7.2 Menu (navigasi utama)

Layout: **sidebar** atau **tab** untuk ganti halaman. Menu:

| Menu | Isi |

|------|-----|

| **Dashboard** | Processing utama: FolderPicker, quick model picker (dropdown dari library), Device, ProcessingSettings, Run, Progress, Log. StatusCard (specs, folder, status). |

| **YOLO Model** | Library model: list model (nama, path, mana yang aktif), tombol **Add model** (browse .pt → simpan), **Remove**, **Set as default**. User bisa ganti-ganti model yang dipakai. |

| **Settings** | Form pengaturan: imgsz, conf, iou, max_det, device, convert_kml, convert_shp, save_annotated, line_width, show_labels, show_conf. Simpan ke config. |

| **Log** | (Opsional) Bisa digabung di Dashboard saja. Kalau terpisah: history log / export log. |

Ringkas: **Dashboard** (run + progress + log), **YOLO Model** (kelola library), **Settings** (parameter).

### 7.3 Komponen per menu

- **Dashboard:** Header, StatusCard, FolderPicker, ModelSelect (dropdown dari `list_models`, tampilkan active), DeviceSelect, ProcessingSettings, RunButton, ProgressSection, LogViewer.
- **YOLO Model:** Header, tabel/list model, Add, Remove, Set default. Pakai `list_models`, `add_model`, `remove_model`, `set_active_model`.
- **Settings:** Form fields + Save. Pakai `load_config`, `save_config`.
- Alias `@/` → `./src`, shadcn di `src/components/ui/`.

### 7.4 Alur

- **Run:** Pakai model aktif dari library. Frontend invoke `run_processing(folder, config_json)`. Tauri spawn Python worker, orchestrate di Rust, emit progress + log.
- **Config / specs / model library:** Semua dari Rust; tidak ada Python.

---

## 8. Langkah implementasi (urutan)

1. **Python inference worker**

   - Buat `python_ai/infer_worker.py` + `requirements.txt` (ultralytics, torch, Pillow).
   - Loop stdin → JSON request → predict → stdout JSON. Load model sekali.

2. **Rust – geo + annotate**

   - Modul `tfw`, `geo` (GeoJSON, KML, SHP), `annotate` (draw bbox, save). Unit test pakai sample image + .tfw.

3. **Rust – config + specs + list_models**

   - `config.rs` (SQLite), `specs.rs` (sysinfo, GPU), `list_models` (list dir). Expose via Tauri commands.

4. **Tauri – run_processing**

   - Spawn worker, kirim request per gambar, terima response, panggil geo + annotate, emit progress/log. Integrasi dengan `infer.rs`.

5. **Frontend – React + Tailwind + shadcn**

   - Init shadcn, komponen UI, layout. Hook `run_processing`, `load_config`, `save_config`, `get_system_specs`, `list_models`, folder/model pickers.

6. **Integration & deploy**

   - Test run processing end-to-end. Build Tauri app. Pastikan Python + deps tersedia di mesin user (atau bundle jika pakai sidecar).

---

## 9. File kunci

| File | Aksi |

|------|------|

| `Palm counting AI/python_ai/infer_worker.py` | Stdin/stdout JSON, YOLO infer only. |

| `Palm counting AI/python_ai/requirements.txt` | ultralytics, torch, Pillow. |

| `Palm counting AI/models/` | Library .pt (user add via Add model). |

| `Palm counting AI/src-tauri/src/lib.rs` | Tauri commands (termasuk add/remove/set_active model). |

| `Palm counting AI/src-tauri/src/infer.rs` | Spawn worker, send/recv JSON. |

| `Palm counting AI/src-tauri/src/config.rs` | SQLite config + `yolo_models` table. |

| `Palm counting AI/src-tauri/src/specs.rs` | sysinfo, nvidia-smi. |

| `Palm counting AI/src-tauri/src/geo.rs` | .tfw, GeoJSON, KML, SHP. |

| `Palm counting AI/src-tauri/src/annotate.rs` | Draw bbox, save image. |

| `Palm counting AI/package.json` | React, Tailwind, shadcn; hapus Preact. |

| `Palm counting AI/vite.config.ts` | React, Tailwind, alias `@`. |

| `Palm counting AI/src/App.tsx` | Layout + routing (Dashboard / YOLO Model / Settings). |

---

## 10. Ringkasan

- **Python:** Hanya inference worker. Input/output JSON via stdin/stdout. Model .pt tetap.
- **Rust:** Config, specs, list models, geo export, annotated images, orchestration, Tauri commands. Tidak ada DDD di Python.
- **Con:** User tetap butuh Python + PyTorch/ultralytics. **Pro:** Tidak ubah model ke ONNX; Python minimal dan terisolasi.