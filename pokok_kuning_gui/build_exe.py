#!/usr/bin/env python3
"""
Script untuk build aplikasi Pokok Kuning GUI menjadi executable (.exe)
Menggunakan PyInstaller dengan konfigurasi yang sudah dioptimalkan
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """Install PyInstaller jika belum ada"""
    try:
        import PyInstaller
        print("✓ PyInstaller sudah terinstall")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller berhasil diinstall")

def create_spec_file():
    """Buat file .spec untuk PyInstaller"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Data files yang perlu diinclude
datas = [
    ('model/yolov8n-pokok-kuning.pt', 'model'),
    ('ui', 'ui'),
    ('utils', 'utils'),
    ('core', 'core'),
]

# Hidden imports yang diperlukan
hiddenimports = [
    'PyQt5.QtCore',
    'PyQt5.QtWidgets',
    'PyQt5.QtGui',
    'ultralytics',
    'ultralytics.yolo',
    'ultralytics.yolo.v8',
    'ultralytics.yolo.v8.detect',
    'ultralytics.yolo.v8.segment',
    'ultralytics.yolo.v8.classify',
    'ultralytics.yolo.v8.pose',
    'ultralytics.yolo.utils',
    'ultralytics.yolo.utils.ops',
    'ultralytics.yolo.utils.plotting',
    'ultralytics.yolo.utils.torch_utils',
    'ultralytics.yolo.utils.checks',
    'ultralytics.yolo.utils.files',
    'ultralytics.yolo.utils.tal',
    'ultralytics.yolo.utils.loss',
    'ultralytics.yolo.utils.metrics',
    'ultralytics.yolo.utils.plotting',
    'ultralytics.yolo.utils.torch_utils',
    'ultralytics.yolo.utils.checks',
    'ultralytics.yolo.utils.files',
    'ultralytics.yolo.utils.tal',
    'ultralytics.yolo.utils.loss',
    'ultralytics.yolo.utils.metrics',
    'numpy',
    'cv2',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'geojson',
    'shapely',
    'shapely.geometry',
    'shapely.ops',
    'fastkml',
    'geopandas',
    'tqdm',
    'sqlite3',
    'json',
    'os',
    'sys',
    'pathlib',
    'datetime',
    'time',
    'threading',
    'queue',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Pokok_Kuning_Desktop_App',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # False untuk GUI app (tidak ada console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Pokok_Kuning_Desktop_App',
)
'''
    
    with open('pokok_kuning.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✓ File pokok_kuning.spec berhasil dibuat")

def build_executable():
    """Build executable menggunakan PyInstaller"""
    print("Building executable...")
    
    # Hapus folder dist dan build jika ada
    for folder in ['dist', 'build']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"✓ Folder {folder} dihapus")
    
    # Jalankan PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "pokok_kuning.spec"
    ]
    
    print("Menjalankan PyInstaller...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Build berhasil!")
        print("Executable tersedia di folder 'dist/Pokok_Kuning_Desktop_App/'")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build gagal: {e}")
        print(f"Error output: {e.stderr}")
        return False
    
    return True

def create_installer_script():
    """Buat script untuk membuat installer sederhana"""
    installer_script = '''@echo off
echo Membuat installer untuk Pokok Kuning Desktop App...
echo.

REM Buat folder installer
if not exist "installer" mkdir installer
if not exist "installer\\Pokok_Kuning_Desktop_App" mkdir installer\\Pokok_Kuning_Desktop_App

REM Copy executable dan dependencies
xcopy /E /I /Y "dist\\Pokok_Kuning_Desktop_App" "installer\\Pokok_Kuning_Desktop_App"

REM Buat shortcut di desktop
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%USERPROFILE%\\Desktop\\Pokok Kuning Desktop App.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%CD%\\installer\\Pokok_Kuning_Desktop_App\\Pokok_Kuning_Desktop_App.exe" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%CD%\\installer\\Pokok_Kuning_Desktop_App" >> CreateShortcut.vbs
echo oLink.Description = "Pokok Kuning Desktop Application" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs

cscript CreateShortcut.vbs
del CreateShortcut.vbs

echo.
echo Installer berhasil dibuat di folder 'installer'!
echo User bisa copy folder 'Pokok_Kuning_Desktop_App' ke komputer mereka
echo dan jalankan file .exe langsung tanpa install apapun
pause
'''
    
    with open('create_installer.bat', 'w', encoding='utf-8') as f:
        f.write(installer_script)
    
    print("✓ Script create_installer.bat berhasil dibuat")

def main():
    """Main function"""
    print("=" * 60)
    print("BUILD EXECUTABLE POKOK KUNING DESKTOP APP")
    print("=" * 60)
    print()
    
    # Pastikan kita di folder yang benar
    if not os.path.exists('main.py'):
        print("❌ Error: File main.py tidak ditemukan!")
        print("Pastikan script ini dijalankan dari folder pokok_kuning_gui")
        return
    
    # Install PyInstaller
    install_pyinstaller()
    print()
    
    # Buat file .spec
    create_spec_file()
    print()
    
    # Build executable
    if build_executable():
        print()
        create_installer_script()
        print()
        print("=" * 60)
        print("BUILD SELESAI!")
        print("=" * 60)
        print("Executable tersedia di: dist/Pokok_Kuning_Desktop_App/")
        print("Jalankan create_installer.bat untuk membuat installer")
        print("=" * 60)
    else:
        print("❌ Build gagal, silakan cek error di atas")

if __name__ == "__main__":
    main()
