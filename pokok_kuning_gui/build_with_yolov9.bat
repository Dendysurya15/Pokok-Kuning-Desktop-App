@echo off
echo =========================================
echo    Pokok Kuning Build Script
echo    Using YOLOv9 Anaconda Environment
echo =========================================
echo.

REM Check if Anaconda is available
where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Anaconda/Miniconda not found in PATH!
    echo Please install Anaconda or add it to your PATH.
    pause
    exit /b 1
)

REM Check if yolov9 environment exists
conda env list | findstr "yolov9" >nul
if %errorlevel% neq 0 (
    echo ERROR: yolov9 environment not found!
    echo Available environments:
    conda env list
    echo.
    echo Please create the yolov9 environment first or check the name.
    pause
    exit /b 1
)

echo Found yolov9 environment. Activating...
echo.

REM Activate yolov9 environment and run the build
call conda activate yolov9

REM Verify activation
if "%CONDA_DEFAULT_ENV%" neq "yolov9" (
    echo ERROR: Failed to activate yolov9 environment!
    echo Current environment: %CONDA_DEFAULT_ENV%
    pause
    exit /b 1
)

echo ✅ Successfully activated yolov9 environment
echo Current environment: %CONDA_DEFAULT_ENV%
echo Python path: %CONDA_PREFIX%
echo.

REM Run the build script
echo Starting build process...
python build_exe_old.py

if %errorlevel% equ 0 (
    echo.
    echo =========================================
    echo ✅ BUILD COMPLETED SUCCESSFULLY!
    echo =========================================
    echo.
    echo Your executable is located at:
    echo dist\PokokKuningApp\PokokKuningApp.exe
    echo.
    echo To test:
    echo 1. Open command prompt
    echo 2. Navigate to dist\PokokKuningApp\
    echo 3. Run PokokKuningApp.exe
    echo.
) else (
    echo.
    echo =========================================
    echo ❌ BUILD FAILED!
    echo =========================================
    echo Check the error messages above for details.
    echo.
)

echo Press any key to exit...
pause >nul
