@echo off
title Pokok Kuning Quick Build
color 0A

echo.
echo ========================================
echo    Pokok Kuning Desktop App Builder
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] Checking dependencies...
python check_dependencies.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ Dependencies check failed!
    pause
    exit /b 1
)

echo.
echo [2/4] Installing PyInstaller...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo.
    echo ❌ Failed to install PyInstaller!
    pause
    exit /b 1
)

echo.
echo [3/4] Building executable...
echo This may take 10-30 minutes...
python build_exe.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ Build failed!
    pause
    exit /b 1
)

echo.
echo [4/4] Build completed!
echo.
echo ✅ Success! Your executable is ready.
echo.
echo Location: dist\PokokKuningApp\PokokKuningApp.exe
echo.
echo To test:
echo 1. Go to dist\PokokKuningApp\
echo 2. Double-click PokokKuningApp.exe
echo.

pause
