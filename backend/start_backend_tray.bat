@echo off
echo Starting Hackyeah Backend with System Tray...
echo.
echo The backend will run in the system tray.
echo Right-click the tray icon to access the menu.
echo.

cd /d "%~dp0"
python main.py --tray

pause
