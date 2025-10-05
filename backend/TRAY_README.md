# Backend System Tray

The Hackyeah Automation Backend can now run with a system tray icon for easy management.

## Features

- **System Tray Icon**: Green circle with 'H' when running, red when stopped
- **Right-Click Menu**: Access backend controls without opening a terminal
- **Status Display**: Shows current backend status and port
- **Restart Option**: Restart the backend server without closing the tray app
- **Easy Exit**: Quit the backend completely from the tray menu

## Usage

### Option 1: Using Batch File (Windows)
```bash
# Double-click or run:
start_backend_tray.bat
```

### Option 2: Using PowerShell Script
```powershell
# Run in PowerShell:
.\start_backend_tray.ps1
```

### Option 3: Direct Python Command
```bash
# Run with tray mode:
python main.py --tray

# Or run the dedicated tray script:
python tray_backend.py
```

## Installation

Make sure you have the required packages installed:

```bash
pip install -r requirements.txt
```

The tray functionality requires:
- `pystray` - System tray integration
- `Pillow` - Image processing for the icon

## Tray Menu Options

Right-click the tray icon to access:

1. **Backend Status** - Shows current status and port
2. **Restart Backend** - Restarts the backend server
3. **Exit** - Completely quits the backend and tray app

## Icon Colors

- 🟢 **Green**: Backend is running and healthy
- 🔴 **Red**: Backend is stopped or has an error
- ⚪ **Gray**: Backend is starting up

## Troubleshooting

If the tray icon doesn't appear:
1. Make sure you have the required packages installed
2. Check that your system supports system tray icons
3. Try running as administrator if needed

If you get import errors:
```bash
pip install pystray pillow
```

## Normal Mode

To run without the tray icon (normal terminal mode):
```bash
python main.py
```

