Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Change to the script directory
objShell.CurrentDirectory = strScriptPath

' Function to check if a command exists
Function CommandExists(command)
    On Error Resume Next
    intResult = objShell.Run(command & " --version", 0, True)
    CommandExists = (intResult = 0)
    On Error GoTo 0
End Function

' Function to download and install Python
Function InstallPython()
    MsgBox "Python is not installed. Please install Python 3.8 or higher from https://www.python.org/downloads/ and ensure 'Add Python to PATH' is checked during installation.", vbCritical, "Python Required"
    ' Try to open Python download page
    objShell.Run "start https://www.python.org/downloads/", 0, False
    InstallPython = False
End Function

' Function to download and install Node.js
Function InstallNodeJS()
    MsgBox "Node.js is not installed. Please install Node.js from https://nodejs.org/ and ensure npm is included.", vbCritical, "Node.js Required"
    ' Try to open Node.js download page
    objShell.Run "start https://nodejs.org/", 0, False
    InstallNodeJS = False
End Function

' Function to check if pip packages are installed
Function PipPackagesInstalled()
    ' Check if backend directory exists
    If Not objFSO.FolderExists(strScriptPath & "\backend") Then
        PipPackagesInstalled = False
        Exit Function
    End If
    
    ' Check if requirements.txt exists
    If Not objFSO.FileExists(strScriptPath & "\backend\requirements.txt") Then
        PipPackagesInstalled = False
        Exit Function
    End If
    
    ' Change to backend directory
    objShell.CurrentDirectory = strScriptPath & "\backend"
    
    ' Try to import key packages to check if they're installed
    On Error Resume Next
    intResult = objShell.Run("python -c ""import fastapi, uvicorn, pydantic, watchdog, nylas, google.generativeai""", 0, True)
    PipPackagesInstalled = (intResult = 0)
    On Error GoTo 0
    
    objShell.CurrentDirectory = strScriptPath
End Function

' Function to install pip packages
Function InstallPipPackages()
    MsgBox "Installing Python dependencies. This may take a few minutes.", vbInformation, "Installing Dependencies"
    
    ' Check if backend directory exists
    If Not objFSO.FolderExists(strScriptPath & "\backend") Then
        MsgBox "Backend directory not found.", vbCritical, "Hackyeah Launcher Error"
        Return False
    End If
    
    ' Check if requirements.txt exists
    If Not objFSO.FileExists(strScriptPath & "\backend\requirements.txt") Then
        MsgBox "requirements.txt not found in backend directory.", vbCritical, "Hackyeah Launcher Error"
        Return False
    End If
    
    ' Change to backend directory
    objShell.CurrentDirectory = strScriptPath & "\backend"
    
    ' Install pip packages
    On Error Resume Next
    intResult = objShell.Run("pip install -r requirements.txt", 1, True)
    If intResult <> 0 Then
        MsgBox "Failed to install Python dependencies. Please check your pip installation.", vbCritical, "Hackyeah Launcher Error"
        objShell.CurrentDirectory = strScriptPath
        InstallPipPackages = False
        Exit Function
    End If
    On Error GoTo 0
    
    objShell.CurrentDirectory = strScriptPath
    InstallPipPackages = True
End Function

' Function to check if npm packages are installed
Function NpmPackagesInstalled()
    ' Check if frontend directory exists
    If Not objFSO.FolderExists(strScriptPath & "\frontend") Then
        Return False
    End If
    
    ' Check if node_modules directory exists
    If Not objFSO.FolderExists(strScriptPath & "\frontend\node_modules") Then
        Return False
    End If
    
    ' Check if package.json exists
    If Not objFSO.FileExists(strScriptPath & "\frontend\package.json") Then
        Return False
    End If
    
    ' Change to frontend directory and check if key packages exist
    objShell.CurrentDirectory = strScriptPath & "\frontend"
    
    ' Check if key packages are installed by looking for their directories
    Dim keyPackages
    keyPackages = Array("react", "electron", "axios", "tailwindcss")
    
    Dim packageExists
    packageExists = True
    
    For Each package In keyPackages
        If Not objFSO.FolderExists(strScriptPath & "\frontend\node_modules\" & package) Then
            packageExists = False
            Exit For
        End If
    Next
    
    objShell.CurrentDirectory = strScriptPath
    NpmPackagesInstalled = packageExists
End Function

' Function to install npm packages
Function InstallNpmPackages()
    MsgBox "Installing Node.js dependencies. This may take a few minutes.", vbInformation, "Installing Dependencies"
    
    ' Check if frontend directory exists
    If Not objFSO.FolderExists(strScriptPath & "\frontend") Then
        MsgBox "Frontend directory not found.", vbCritical, "Hackyeah Launcher Error"
        Return False
    End If
    
    ' Check if package.json exists
    If Not objFSO.FileExists(strScriptPath & "\frontend\package.json") Then
        MsgBox "package.json not found in frontend directory.", vbCritical, "Hackyeah Launcher Error"
        Return False
    End If
    
    ' Change to frontend directory
    objShell.CurrentDirectory = strScriptPath & "\frontend"
    
    ' Install npm packages
    On Error Resume Next
    intResult = objShell.Run("npm install", 1, True)
    If intResult <> 0 Then
        MsgBox "Failed to install npm dependencies.", vbCritical, "Hackyeah Launcher Error"
        objShell.CurrentDirectory = strScriptPath
        InstallNpmPackages = False
        Exit Function
    End If
    On Error GoTo 0
    
    objShell.CurrentDirectory = strScriptPath
    InstallNpmPackages = True
End Function

' Function to check if backend is already running
Function BackendRunning()
    ' Check if backend port is in use (port 8002 from config.yaml)
    On Error Resume Next
    intResult = objShell.Run("netstat -an | findstr :8002", 0, True)
    BackendRunning = (intResult = 0)
    On Error GoTo 0
End Function

' Function to start backend
Function StartBackend()
    ' Check if backend directory exists
    If Not objFSO.FolderExists(strScriptPath & "\backend") Then
        MsgBox "Backend directory not found.", vbCritical, "Hackyeah Launcher Error"
        StartBackend = False
        Exit Function
    End If
    
    ' Check if backend is already running
    If BackendRunning() Then
        MsgBox "Backend server is already running.", vbInformation, "Hackyeah Launcher"
        StartBackend = True
        Exit Function
    End If
    
    MsgBox "Starting backend server...", vbInformation, "Hackyeah Launcher"
    
    ' Change to backend directory
    objShell.CurrentDirectory = strScriptPath & "\backend"
    
    ' Start backend in tray mode
    On Error Resume Next
    intResult = objShell.Run("python tray_backend.py", 0, False)
    If intResult <> 0 Then
        ' Try alternative method
        intResult = objShell.Run("python main.py --tray", 0, False)
        If intResult <> 0 Then
            MsgBox "Failed to start backend server.", vbCritical, "Hackyeah Launcher Error"
            objShell.CurrentDirectory = strScriptPath
            StartBackend = False
            Exit Function
        End If
    End If
    On Error GoTo 0
    
    objShell.CurrentDirectory = strScriptPath
    
    ' Wait a moment for backend to start
    WScript.Sleep 3000
    StartBackend = True
End Function

' Function to start frontend
Function StartFrontend()
    ' Check if frontend directory exists
    If Not objFSO.FolderExists(strScriptPath & "\frontend") Then
        MsgBox "Frontend directory not found.", vbCritical, "Hackyeah Launcher Error"
        StartFrontend = False
        Exit Function
    End If
    
    ' Check if package.json exists
    If Not objFSO.FileExists(strScriptPath & "\frontend\package.json") Then
        MsgBox "package.json not found in frontend directory.", vbCritical, "Hackyeah Launcher Error"
        StartFrontend = False
        Exit Function
    End If
    
    ' Change to frontend directory
    objShell.CurrentDirectory = strScriptPath & "\frontend"
    
    ' Launch the application using npm run dev
    On Error Resume Next
    intResult = objShell.Run("npm run dev", 0, False)
    If intResult <> 0 Then
        MsgBox "Failed to start frontend application.", vbCritical, "Hackyeah Launcher Error"
        objShell.CurrentDirectory = strScriptPath
        StartFrontend = False
        Exit Function
    End If
    On Error GoTo 0
    
    objShell.CurrentDirectory = strScriptPath
    StartFrontend = True
End Function

' Main execution starts here
MsgBox "Hackyeah Launcher - Checking system requirements...", vbInformation, "Hackyeah Launcher"

' Check if Python is installed
If Not CommandExists("python") Then
    If Not InstallPython() Then
        WScript.Quit 1
    End If
    ' Check again after installation attempt
    If Not CommandExists("python") Then
        MsgBox "Python installation failed or not found in PATH. Please install Python manually and try again.", vbCritical, "Hackyeah Launcher Error"
        WScript.Quit 1
    End If
End If

' Check if Node.js is installed
If Not CommandExists("node") Then
    If Not InstallNodeJS() Then
        WScript.Quit 1
    End If
    ' Check again after installation attempt
    If Not CommandExists("node") Then
        MsgBox "Node.js installation failed or not found in PATH. Please install Node.js manually and try again.", vbCritical, "Hackyeah Launcher Error"
        WScript.Quit 1
    End If
End If

' Check if npm is available
If Not CommandExists("npm") Then
    MsgBox "npm is not available. Please ensure Node.js is properly installed with npm.", vbCritical, "Hackyeah Launcher Error"
    WScript.Quit 1
End If

' Install Python dependencies if needed
If Not PipPackagesInstalled() Then
    If Not InstallPipPackages() Then
        WScript.Quit 1
    End If
Else
    MsgBox "Python dependencies already installed.", vbInformation, "Hackyeah Launcher"
End If

' Install npm dependencies if needed
If Not NpmPackagesInstalled() Then
    If Not InstallNpmPackages() Then
        WScript.Quit 1
    End If
Else
    MsgBox "Node.js dependencies already installed.", vbInformation, "Hackyeah Launcher"
End If

' Start backend server
If Not StartBackend() Then
    WScript.Quit 1
End If

' Start frontend application
If Not StartFrontend() Then
    WScript.Quit 1
End If

MsgBox "Hackyeah Automation Assistant is starting up!" & vbCrLf & vbCrLf & "Backend is running in system tray." & vbCrLf & "Frontend will open in a new window.", vbInformation, "Hackyeah Launcher"
