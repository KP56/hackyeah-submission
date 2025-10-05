@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo Building ProcessBot Electron App to .exe
echo ================================================
echo.
echo Working directory: %CD%
echo.

echo Step 1: Building React app...
call npm run build
if errorlevel 1 (
    echo ERROR: React build failed!
    pause
    exit /b 1
)
echo.

echo Step 2: Building Electron executable...
echo Clearing electron-builder cache to fix signing issues...
rmdir /s /q "%LOCALAPPDATA%\electron-builder\Cache\winCodeSign" 2>nul
echo.
echo Building without code signing...
set CSC_IDENTITY_AUTO_DISCOVERY=false
set WIN_CSC_LINK=
set CSC_LINK=
call node_modules\.bin\electron-builder.cmd --win --projectDir="%CD%"
if errorlevel 1 (
    echo ERROR: Electron build failed!
    pause
    exit /b 1
)
echo.

echo ================================================
echo SUCCESS! Your .exe is ready!
echo ================================================
echo.
echo Location: frontend\dist\ProcessBot.exe
echo.
echo This is a PORTABLE .exe that you can:
echo - Run directly without installation
echo - Copy to any Windows computer and run
echo - Distribute easily without an installer
echo.
pause

