# Building ProcessBot to .exe

## Quick Start (Easiest Method)

Simply double-click:
```
build_electron.bat
```

The script will:
1. Build your React app
2. Package it with Electron into a Windows installer
3. Create an `.exe` file in `frontend/dist/`

## Manual Method

If you prefer to run commands yourself:

```bash
# Step 1: Navigate to frontend folder
cd frontend

# Step 2: Build the React app
npm run build

# Step 3: Build the Electron .exe
npm run build-electron
```

## Output Location

After building, you'll find:
- **Installer**: `frontend/dist/ProcessBot Setup 1.0.0.exe`
- This is an NSIS installer that users can run to install your app

## What Gets Built

The build process creates:
- A Windows installer (.exe)
- The installer allows users to:
  - Choose installation directory
  - Create desktop shortcut
  - Create Start Menu shortcut
  - Uninstall the app later

## Distributing Your App

Simply share the `ProcessBot Setup 1.0.0.exe` file with others. They can:
1. Double-click the installer
2. Follow the installation wizard
3. Run ProcessBot from their Start Menu or Desktop

## Build Configuration

The build settings are in `package.json` under the `"build"` section. You can customize:
- App name
- Icons
- Installation options
- Target platforms

## Troubleshooting

**Build fails?**
- Make sure all dependencies are installed: `npm install`
- Check that you're in the `frontend` directory
- Ensure no other instances of the app are running

**Need a portable .exe (no installer)?**
- Change the target in `package.json` from `"nsis"` to `"portable"`

**Want to change the app name or version?**
- Update `"productName"` and `"version"` in `package.json`

