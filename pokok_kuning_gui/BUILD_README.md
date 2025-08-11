# Build Instructions untuk Pokok Kuning Desktop App

## Cara Membuat Executable (.exe)

### Method 1: Menggunakan Build Script (Recommended)

1. **Persiapan Environment**
   ```bash
   # Pastikan semua dependencies terinstall
   pip install -r requirements.txt
   ```

2. **Build menggunakan Script**
   ```bash
   # Windows
   build.bat
   
   # Atau manual
   python build_exe.py
   ```

3. **Hasil Build**
   - Executable akan tersedia di folder `dist/PokokKuningApp/`
   - File utama: `PokokKuningApp.exe`

### Method 2: Manual PyInstaller

1. **Install PyInstaller**
   ```bash
   pip install pyinstaller
   ```

2. **Build dengan Spec File**
   ```bash
   pyinstaller --clean pokok_kuning.spec
   ```

## Struktur Hasil Build

```
dist/
└── PokokKuningApp/
    ├── PokokKuningApp.exe      # File executable utama
    ├── model/                  # Model YOLO
    ├── torch/                  # PyTorch dependencies
    ├── ultralytics/           # Ultralytics library
    └── [various DLLs and dependencies]
```

## Troubleshooting

### Error: "Module not found"
- Pastikan semua dependencies dalam `requirements.txt` sudah terinstall
- Jalankan: `pip install -r requirements.txt`

### Error: "Failed to execute script"
- Periksa log error dengan menjalankan exe dari command prompt
- Pastikan model file (.pt) ada di folder yang benar

### File Size Terlalu Besar
- Executable akan sekitar 2-4 GB karena include PyTorch dan ultralytics
- Ini normal untuk aplikasi ML dengan dependencies besar

### Testing Build
1. Copy folder `dist/PokokKuningApp` ke komputer lain
2. Jalankan `PokokKuningApp.exe`
3. Pastikan aplikasi berjalan tanpa perlu install Python/dependencies

## Optimasi Build

### Mengurangi Size
- Edit `pokok_kuning.spec` untuk exclude modules yang tidak diperlukan
- Gunakan `excludes=['matplotlib', 'tkinter']` (sudah diset)

### Debug Mode
- Ubah `console=False` menjadi `console=True` di spec file untuk melihat output debug

## Distribusi

Untuk distribusi ke end user:
1. Zip folder `dist/PokokKuningApp`
2. Include README untuk user tentang cara menjalankan
3. Pastikan include model files dan semua dependencies

## System Requirements

**Minimum untuk menjalankan executable:**
- Windows 10/11 64-bit
- RAM: 4GB (8GB recommended)
- Storage: 5GB free space
- GPU: Optional (akan menggunakan CPU jika tidak ada GPU)

**Untuk development/building:**
- Python 3.8+
- Semua packages dalam requirements.txt
- PyInstaller
