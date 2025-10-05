@echo off
REM Hackyeah Launcher - Batch Version
REM This script launches the Hackyeah application with proper process cleanup

REM Hide the command window
if not "%1"=="am_admin" (powershell start -verb runas '%0' am_admin & exit /b)

REM Set working directory to the script location
cd /d "%~dp0"

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js is not installed or not in PATH.
    echo Please install Node.js first.
    timeout /t 5 >nul
    exit /b 1
)

REM Check if npm is available
npm --version >nul 2>&1
if errorlevel 1 (
    echo npm is not available.
    echo Please ensure Node.js is properly installed.
    timeout /t 5 >nul
    exit /b 1
)

REM Check if frontend directory exists
if not exist "frontend" (
    echo Frontend directory not found.
    echo Please run this script from the Hackyeah root directory.
    timeout /t 5 >nul
    exit /b 1
)

REM Check if package.json exists
if not exist "frontend\package.json" (
    echo package.json not found in frontend directory.
    timeout /t 5 >nul
    exit /b 1
)

REM Change to frontend directory
cd frontend

REM Check if node_modules exists, if not, install dependencies
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
    if errorlevel 1 (
        echo Failed to install npm dependencies.
        timeout /t 5 >nul
        exit /b 1
    )
)

REM Launch the application and capture the process ID
echo Starting Hackyeah...
start /b npm run dev
set /a PID=%ERRORLEVEL%

REM Wait for user to close the window
echo.
echo Hackyeah is running. Close this window to stop the application.
echo.
pause

REM Clean up processes when window is closed
echo Cleaning up processes...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *Hackyeah*" 2>nul
taskkill /F /IM electron.exe 2>nul
taskkill /F /IM node.exe /FI "COMMANDLINE eq *hackyeah*" 2>nul
taskkill /F /IM node.exe /FI "COMMANDLINE eq *frontend*" 2>nul
taskkill /F /IM node.exe /FI "COMMANDLINE eq *electron*" 2>nul

echo Application stopped.
