# Cara Build Executable (.exe) untuk Pokok Kuning Desktop App

Dokumen ini menjelaskan cara mengubah aplikasi Python Pokok Kuning GUI menjadi file executable (.exe) yang bisa langsung dijalankan tanpa perlu menginstall Python atau dependencies lainnya.

## 🎯 Keuntungan

- **Portable**: User tidak perlu install Python atau library apapun
- **Standalone**: Semua dependencies sudah termasuk dalam satu folder
- **Easy Distribution**: Tinggal copy folder ke komputer lain dan jalankan
- **Professional**: Terlihat seperti aplikasi desktop biasa

## 🛠️ Tools yang Dibutuhkan

- Python 3.7+ (hanya untuk build, tidak untuk user)
- PyInstaller (akan diinstall otomatis)

## 📁 File yang Dibuat

1. **`build_exe.py`** - Script Python untuk build otomatis
2. **`pokok_kuning.spec`** - Konfigurasi PyInstaller
3. **`build.bat`** - Script batch untuk Windows
4. **`BUILD_README.md`** - File ini

## 🚀 Cara Build

### Opsi 1: Menggunakan Script Python (Recommended)

```bash
# Jalankan dari folder pokok_kuning_gui
python build_exe.py
```

Script ini akan:
- Install PyInstaller otomatis
- Buat file .spec
- Build executable
- Buat script installer

### Opsi 2: Menggunakan Script Batch

```bash
# Double click file build.bat
# Atau jalankan dari command prompt
build.bat
```

### Opsi 3: Manual dengan PyInstaller

```bash
# Install PyInstaller
pip install pyinstaller

# Build menggunakan spec file
pyinstaller --clean pokok_kuning.spec
```

## 📦 Output

Setelah build berhasil, Anda akan mendapatkan:

```
dist/
└── Pokok_Kuning_Desktop_App/
    ├── Pokok_Kuning_Desktop_App.exe  ← File utama
    ├── model/                         ← Model YOLO
    ├── ui/                           ← UI components
    ├── utils/                        ← Utilities
    ├── core/                         ← Core functions
    └── [dependencies lainnya]        ← Python libraries
```

## 📤 Distribusi ke User

### Cara 1: Copy Folder (Recommended)
1. Copy seluruh folder `Pokok_Kuning_Desktop_App` ke komputer user
2. User tinggal double-click file `.exe`
3. Tidak perlu install apapun

### Cara 2: Buat Installer
1. Jalankan `create_installer.bat` (dibuat otomatis oleh `build_exe.py`)
2. Folder `installer` akan dibuat
3. Copy folder tersebut ke user

### Cara 3: Archive/Compress
1. Zip folder `Pokok_Kuning_Desktop_App`
2. Kirim file zip ke user
3. User extract dan jalankan

## ⚠️ Troubleshooting

### Error: "Missing module"
- Pastikan semua dependencies ada di `requirements.txt`
- Cek `hiddenimports` di file `.spec`

### Error: "File not found"
- Pastikan struktur folder benar
- Cek `datas` di file `.spec`

### Executable tidak bisa dijalankan
- Pastikan build berhasil tanpa error
- Cek apakah ada antivirus yang memblokir
- Test di komputer yang bersih (tanpa Python)

### Ukuran file terlalu besar
- Ini normal untuk aplikasi dengan ML models
- Bisa mencapai 500MB-1GB
- Gunakan UPX compression (sudah diaktifkan)

## 🔧 Customization

### Ganti Nama Aplikasi
Edit file `.spec`:
```python
name='Nama_Aplikasi_Anda'
```

### Tambah Icon
1. Buat file `icon.ico`
2. Letakkan di folder yang sama dengan `.spec`
3. Icon akan otomatis digunakan

### Ganti Console Mode
Untuk debug, ubah di `.spec`:
```python
console=True  # Tampilkan console window
```

## 📋 Checklist Build

- [ ] Semua dependencies terinstall
- [ ] File `main.py` ada dan bisa dijalankan
- [ ] Model YOLO ada di folder `model/`
- [ ] Build berhasil tanpa error
- [ ] Test executable di komputer lain
- [ ] Semua fitur berfungsi normal

## 🎉 Selesai!

Setelah build berhasil, aplikasi Anda siap didistribusikan ke user tanpa perlu mereka menginstall Python atau library apapun. User tinggal copy folder dan jalankan file `.exe`!

---

**Note**: Build pertama kali mungkin memakan waktu lama (10-30 menit) karena PyInstaller perlu mengumpulkan semua dependencies. Build selanjutnya akan lebih cepat.
