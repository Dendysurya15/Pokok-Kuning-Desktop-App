@echo off
echo ========================================
echo BUILD POKOK KUNING DESKTOP APP
echo ========================================
echo.

REM Install PyInstaller jika belum ada
echo Installing PyInstaller...
python -m pip install pyinstaller

REM Build menggunakan spec file
echo.
echo Building executable...
pyinstaller --clean pokok_kuning.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo BUILD BERHASIL!
    echo ========================================
    echo Executable tersedia di: dist\Pokok_Kuning_Desktop_App\
    echo.
    echo User bisa copy folder tersebut ke komputer mereka
    echo dan jalankan file .exe langsung tanpa install apapun
    echo ========================================
) else (
    echo.
    echo ========================================
    echo BUILD GAGAL!
    echo ========================================
    echo Silakan cek error di atas
)

pause
