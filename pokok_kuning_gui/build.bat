@echo off
echo ================================================
echo        Pokok Kuning Desktop App Builder
echo ================================================
echo.

cd /d "%~dp0"

echo Installing required packages...
pip install pyinstaller

echo.
echo Building executable...
python build_exe.py

echo.
echo Build process completed!
echo Check the dist/PokokKuningApp folder for the executable.
pause
