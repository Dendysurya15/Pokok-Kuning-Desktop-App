# Pokok Kuning Desktop App - GUI Version

## Perbedaan dengan Versi CLI (source/main.py)

### Masalah yang Ditemukan:
1. **Image Size (imgsz)**: 
   - CLI version: **12800** (default)
   - GUI version: **1280** (default) ❌
   - **Perbedaan 10x!** Ini menyebabkan hasil deteksi yang sangat berbeda

2. **Max Detection Limit**:
   - CLI version: **10000** (default)
   - GUI version: **12000** (default) ❌

3. **Model Path**:
   - CLI version: `"..\model\yolov8n-pokok-kuning.pt"`
   - GUI version: `"model/{config['model']}.pt"` ❌

### Solusi yang Sudah Diterapkan:

1. **Database Configuration Updated**:
   - `imgsz`: 1280 → **12800** ✅
   - `max_det`: 12000 → **10000** ✅
   - Model path: Fixed to match CLI version ✅

2. **Code Changes**:
   - `config_manager.py`: Default values updated
   - `processor.py`: Default fallback values updated
   - `main_window.py`: QThread.singleShot error fixed

### Cara Menggunakan:

1. **Setup Database** (jika belum):
   ```bash
   cd pokok_kuning_gui
   python setup_db.py
   ```

2. **Jalankan GUI**:
   ```bash
   python main.py
   ```

3. **Verifikasi Konfigurasi**:
   - Image Size harus menunjukkan **12800**
   - Max Det harus menunjukkan **10000**

### Hasil yang Diharapkan:

Setelah perbaikan ini, hasil GUI seharusnya **sama** dengan hasil CLI:
```bash
# CLI version
python source/main.py --folder "C:\Users\jaja.valentino\Desktop\Python\E026_B - Copy" --save-annotated --shp

# GUI version (setelah perbaikan)
python pokok_kuning_gui/main.py
```

### Troubleshooting:

Jika GUI masih menampilkan nilai lama:
1. Hapus `database.db`
2. Jalankan `python setup_db.py`
3. Restart GUI

### Catatan Penting:

- **Image Size 12800** memberikan deteksi yang lebih detail dan akurat
- **Image Size 1280** memberikan deteksi yang kasar dan kurang akurat
- Perbedaan ini menyebabkan jumlah deteksi yang sangat berbeda antara CLI dan GUI
