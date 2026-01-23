# Pokok Kuning Desktop App - GUI Version

## Persyaratan Sistem

### 1. Install Python

**Python versi yang dibutuhkan: Python 3.8 atau lebih tinggi (disarankan Python 3.10+)**

- Download Python dari: https://www.python.org/downloads/
- Pastikan saat install, centang opsi **"Add Python to PATH"**
- Verifikasi instalasi:
  ```bash
  python --version
  ```

### 2. Install Anaconda/Miniconda (Optional tapi Recommended)

Untuk memudahkan manajemen environment dan dependencies, disarankan menggunakan Anaconda atau Miniconda:

- Download Anaconda: https://www.anaconda.com/download
- Atau Miniconda: https://docs.conda.io/en/latest/miniconda.html

### 3. Setup Conda Environment

Buat dan aktifkan conda environment bernama `yolov9`:

```bash
# Buat environment baru
conda create -n yolov9 python=3.10

# Aktifkan environment
conda activate yolov9
```

**Catatan:** Build script memerlukan environment conda dengan nama `yolov9`. Jika menggunakan nama environment berbeda, edit `build_exe.py` atau gunakan environment `yolov9`.

### 4. Install Requirements

Install semua dependencies yang diperlukan:

```bash
# Pastikan sudah di folder project
cd pokok_kuning_gui

# Install requirements
pip install -r requirements.txt
```

**Dependencies yang akan diinstall:**
- PyQt5 (GUI framework)
- ultralytics (YOLO model)
- torch & torchvision (PyTorch dengan CUDA support)
- opencv-python (Computer vision)
- geopandas (Geospatial data)
- pyinstaller (Untuk build exe)
- Dan dependencies lainnya

**Catatan:** Jika menggunakan GPU dengan CUDA, pastikan install PyTorch dengan CUDA support:
```bash
# Contoh untuk CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 5. Build menjadi EXE

Setelah semua dependencies terinstall, jalankan script build:

```bash
# Pastikan environment yolov9 aktif
conda activate yolov9

# Jalankan build script
python build_exe.py
```

**Proses build akan:**
- ✅ Memeriksa environment (pastikan di conda `yolov9`)
- ✅ Membuat spec file dan hook file secara otomatis
- ✅ Membersihkan build sebelumnya
- ✅ Membangun executable dengan optimasi
- ✅ Memverifikasi hasil build

**Waktu build:** 10-30 menit (tergantung spesifikasi PC)

### 6. Hasil Build

Setelah build selesai, executable akan berada di:

```
dist/PokokKuningApp/PokokKuningApp.exe
```

**Untuk menjalankan aplikasi:**
```bash
cd dist/PokokKuningApp
PokokKuningApp.exe
```

**Atau double-click file `PokokKuningApp.exe`**

## Alternatif: Menggunakan Batch File

Jika ingin lebih mudah, gunakan batch file yang akan mengaktifkan environment secara otomatis:

```bash
# Double-click atau jalankan di terminal
build_with_yolov9.bat
```

## Troubleshooting

### Error: "Not in 'yolov9' environment!"
- Pastikan environment `yolov9` sudah dibuat dan aktif
- Aktifkan dengan: `conda activate yolov9`

### Error: "PyTorch not installed!"
- Install PyTorch: `pip install torch torchvision`
- Untuk CUDA support, install versi dengan CUDA

### Error saat build
- Pastikan semua dependencies terinstall: `pip install -r requirements.txt`
- Pastikan PyInstaller terinstall: `pip install pyinstaller`
- Check log file untuk detail error

### Aplikasi tidak jalan setelah build
- Check log file `runtime_*.log` di folder `dist/PokokKuningApp`
- Pastikan semua file di folder `dist/PokokKuningApp` ikut saat distribusi

## Catatan Penting

- ⚠️ Build memerlukan environment conda dengan nama `yolov9`
- ⚠️ Pastikan CUDA dan PyTorch sudah terinstall dengan benar
- ⚠️ Build membutuhkan waktu beberapa menit (10-30 menit)
- ⚠️ Ukuran hasil build cukup besar karena termasuk model dan dependencies
- ⚠️ Untuk distribusi, kirimkan seluruh folder `dist/PokokKuningApp`, bukan hanya file `.exe`
