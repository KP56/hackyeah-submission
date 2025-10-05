# Hackyeah Launcher - PowerShell Version with Proper Process Management
# This script launches the Hackyeah application and properly cleans up processes

param(
    [switch]$Hidden = $true
)

# Set execution policy for this session only
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Hide the PowerShell window if requested
if ($Hidden) {
    try {
        Add-Type -Name Window -Namespace Console -MemberDefinition '
        [DllImport("Kernel32.dll")]
        public static extern IntPtr GetConsoleWindow();
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, Int32 nCmdShow);
        '
        $consolePtr = [Console.Window]::GetConsoleWindow()
        [Console.Window]::ShowWindow($consolePtr, 0) # 0 = SW_HIDE
    } catch {
        # If hiding fails, continue without hiding
        Write-Host "Could not hide console window, continuing..."
    }
}

# Get the directory where this script is located
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptPath

# Function to show error message
function Show-Error {
    param([string]$Message)
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($Message, "Hackyeah Launcher Error", "OK", "Error")
}

# Function to cleanup processes
function Cleanup-Processes {
    Write-Host "Cleaning up processes..."
    
    # Kill Node.js processes related to this project
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*hackyeah*" -or 
        $_.CommandLine -like "*frontend*" -or
        $_.CommandLine -like "*electron*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Kill Electron processes
    Get-Process -Name "electron" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Kill any remaining Node.js processes that might be related
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "*Hackyeah*" -or
        $_.MainWindowTitle -like "*Electron*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Host "Process cleanup completed."
}

# Register cleanup function to run on script exit
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Cleanup-Processes
}

# Check if Node.js is installed
try {
    $nodeVersion = node --version 2>$null
    if (-not $nodeVersion) {
        Show-Error "Node.js is not installed or not in PATH. Please install Node.js first."
        exit 1
    }
} catch {
    Show-Error "Node.js is not installed or not in PATH. Please install Node.js first."
    exit 1
}

# Check if npm is available
try {
    $npmVersion = npm --version 2>$null
    if (-not $npmVersion) {
        Show-Error "npm is not available. Please ensure Node.js is properly installed."
        exit 1
    }
} catch {
    Show-Error "npm is not available. Please ensure Node.js is properly installed."
    exit 1
}

# Check if frontend directory exists
if (-not (Test-Path "frontend")) {
    Show-Error "Frontend directory not found. Please run this script from the Hackyeah root directory."
    exit 1
}

# Check if package.json exists
if (-not (Test-Path "frontend\package.json")) {
    Show-Error "package.json not found in frontend directory."
    exit 1
}

# Change to frontend directory
Set-Location "frontend"

# Check if node_modules exists, if not, install dependencies
if (-not (Test-Path "node_modules")) {
    if (-not $Hidden) {
        Write-Host "Installing dependencies for the first time. This may take a few minutes..."
    }
    
    try {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Show-Error "Failed to install npm dependencies."
            exit 1
        }
    } catch {
        Show-Error "Error installing dependencies: $($_.Exception.Message)"
        exit 1
    }
}

# Launch the application
try {
    if (-not $Hidden) {
        Write-Host "Starting Hackyeah..."
    }
    
    # Start the process and capture it
    $process = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -PassThru -WindowStyle Hidden
    
    # Wait for the process to complete
    $process.WaitForExit()
    
    # Clean up any remaining processes
    Cleanup-Processes
    
} catch {
    Show-Error "Error starting application: $($_.Exception.Message)"
    Cleanup-Processes
    exit 1
}
