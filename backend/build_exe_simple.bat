@echo off
REM Ultra-simple build - just the basics
echo Installing PyInstaller if needed...
pip install pyinstaller

echo.
echo Building exe (this takes 2-5 minutes)...
pyinstaller --onefile --name HackyeahBackend ^
    --exclude-module PyQt5 ^
    --exclude-module PyQt6 ^
    --exclude-module PySide2 ^
    --exclude-module PySide6 ^
    tray_backend.py

echo.
echo Done! Check the dist folder for HackyeahBackend.exe
pause

