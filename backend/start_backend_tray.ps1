# Hackyeah Backend Tray Starter
Write-Host "Starting Hackyeah Backend with System Tray..." -ForegroundColor Green
Write-Host ""
Write-Host "The backend will run in the system tray." -ForegroundColor Yellow
Write-Host "Right-click the tray icon to access the menu." -ForegroundColor Yellow
Write-Host ""

# Change to the script directory
Set-Location $PSScriptRoot

# Start the backend with tray
try {
    python main.py --tray
} catch {
    Write-Host "Error starting backend: $_" -ForegroundColor Red
    Write-Host "Make sure Python and required packages are installed." -ForegroundColor Yellow
    Write-Host "Run: pip install -r requirements.txt" -ForegroundColor Yellow
}

Read-Host "Press Enter to exit"
