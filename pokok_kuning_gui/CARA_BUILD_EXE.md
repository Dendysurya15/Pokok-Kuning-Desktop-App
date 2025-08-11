# 🚀 Cara Membuat Executable (.exe) Pokok Kuning Desktop App

## 📋 Langkah-langkah Build

### 1. Persiapan Environment

Pastikan Python sudah terinstall (Python 3.8 atau lebih baru):
```bash
python --version
```

### 2. Install Dependencies

```bash
# Install semua packages yang diperlukan
pip install -r requirements.txt

# Atau check dependencies dulu
python check_dependencies.py
```

### 3. Build Executable

**Option A: Menggunakan Batch File (Termudah)**
```bash
# Double-click file ini atau jalankan di command prompt
build.bat
```

**Option B: Menggunakan Python Script**
```bash
python build_exe.py
```

**Option C: Manual dengan PyInstaller**
```bash
pip install pyinstaller
pyinstaller --clean pokok_kuning.spec
```

### 4. Hasil Build

Setelah build selesai, executable akan tersedia di:
```
dist/
└── PokokKuningApp/
    ├── PokokKuningApp.exe  # ← File ini yang dijalankan user
    ├── model/              # Model YOLO
    └── [dependencies lainnya]
```

## 📦 Distribusi ke End User

1. **Copy folder lengkap** `dist/PokokKuningApp/` 
2. **Zip folder tersebut** untuk distribusi
3. User tinggal **extract dan jalankan** `PokokKuningApp.exe`

## ⚠️ Hal Penting

### Size File
- Executable akan berukuran **2-4 GB** (ini normal!)
- Besar karena include PyTorch, OpenCV, dan dependencies ML lainnya
- User tidak perlu install Python atau library apapun

### Testing
Untuk memastikan exe berfungsi:
1. Copy folder `dist/PokokKuningApp` ke komputer lain yang TIDAK ada Python
2. Jalankan `PokokKuningApp.exe`
3. Aplikasi harus bisa berjalan normal

### System Requirements untuk End User
- **OS**: Windows 10/11 64-bit
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 5GB free space
- **GPU**: Optional (akan pakai CPU jika tidak ada)

## 🐛 Troubleshooting

### Error "Module not found"
```bash
# Install ulang dependencies
pip install --upgrade -r requirements.txt
python check_dependencies.py
```

### Error saat build
```bash
# Clean dan build ulang
rm -rf dist build
python build_exe.py
```

### Error saat run exe
1. Jalankan exe dari command prompt untuk lihat error message
2. Pastikan semua file model (.pt) ada di folder `model/`
3. Cek apakah antivirus memblok exe

### Exe terlalu lambat
- Ini normal untuk pertama kali karena loading semua dependencies
- Startup berikutnya akan lebih cepat

## 🎯 Tips Optimasi

### Mengurangi Size (Advanced)
Edit file `pokok_kuning.spec`:
- Tambah package ke `excludes` jika tidak diperlukan
- Remove unused torch models

### Debug Mode
Ubah di `pokok_kuning.spec`:
```python
console=True  # Akan show console window untuk debugging
```

### Custom Icon
1. Siapkan file `icon.ico`
2. Edit `pokok_kuning.spec`:
```python
icon='icon.ico'
```

## 📞 Support

Jika ada masalah:
1. Cek error message di console
2. Pastikan semua dependencies terinstall dengan benar
3. Test di environment yang bersih

---

**Note**: Build pertama akan memakan waktu 10-30 menit tergantung spek komputer. Build selanjutnya akan lebih cepat karena PyInstaller meng-cache dependencies.
