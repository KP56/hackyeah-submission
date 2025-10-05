const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const yaml = require('js-yaml');
const { spawn, exec } = require('child_process');
const isDev = process.env.ELECTRON_IS_DEV === '1';

let mainWindow;
let currentPort = 8002; // default port
let backendProcess = null;
let isShuttingDown = false;
let popupWindows = []; // Track popup windows

// Function to clean up Node.js processes
function cleanupNodeProcesses() {
  console.log('Cleaning up Node.js processes...');
  
  try {
    // On Windows
    if (process.platform === 'win32') {
      exec('taskkill /F /IM node.exe /FI "WINDOWTITLE eq *localhost:3000*" 2>nul', (error) => {
        if (error) console.log('No React dev server processes found');
      });
      
      exec('taskkill /F /IM node.exe /FI "COMMANDLINE eq *react-scripts*" 2>nul', (error) => {
        if (error) console.log('No react-scripts processes found');
      });
      
      exec('taskkill /F /IM node.exe /FI "COMMANDLINE eq *webpack*" 2>nul', (error) => {
        if (error) console.log('No webpack processes found');
      });
    } else {
      // On Unix-like systems
      exec('pkill -f "react-scripts" 2>/dev/null', (error) => {
        if (error) console.log('No react-scripts processes found');
      });
      
      exec('pkill -f "webpack" 2>/dev/null', (error) => {
        if (error) console.log('No webpack processes found');
      });
    }
    
    console.log('Node.js process cleanup completed');
  } catch (error) {
    console.error('Error during process cleanup:', error);
  }
}

// Helper function to get the current backend port
function getBackendPort() {
  try {
    const configPath = path.join(__dirname, '../../backend/config.yaml');
    if (fs.existsSync(configPath)) {
      const configFile = fs.readFileSync(configPath, 'utf8');
      const config = yaml.load(configFile);
      return config?.backend?.port || 8002;
    }
  } catch (e) {
    console.log('Using default port 8002');
  }
  return 8002;
}

// Helper function to get the API URL
function getApiUrl(endpoint = '') {
  const port = getBackendPort();
  return `http://127.0.0.1:${port}${endpoint}`;
}

// Function to check if backend is already running
async function isBackendRunning() {
  try {
    const url = getApiUrl('/');
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);
    
    const response = await fetch(url, { 
      method: 'GET',
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    return response.ok;
  } catch (error) {
    return false;
  }
}

// Function to start the backend process
async function startBackend() {
  if (backendProcess) {
    console.log('Backend already running');
    return;
  }

  // Check if backend is already running externally
  const isRunning = await isBackendRunning();
  if (isRunning) {
    console.log('Backend is already running externally - not starting new process');
    return;
  }

  const backendPath = path.join(__dirname, '../../backend');
  const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';
  
  console.log('Starting backend process with system tray...');
  console.log(`Backend path: ${backendPath}`);
  console.log(`Python command: ${pythonCommand}`);
  console.log('Look for the green circle with "H" in your system tray!');
  
  backendProcess = spawn(pythonCommand, ['main.py', '--tray'], {
    cwd: backendPath,
    stdio: 'pipe',
    shell: true // Use shell for better cross-platform compatibility
  });

  backendProcess.stdout.on('data', (data) => {
    const output = data.toString().trim();
    if (output) {
      console.log(`[Backend] ${output}`);
      
      // Check for tray icon creation message
      if (output.includes('Backend tray icon created')) {
        console.log('[Backend] ✅ System tray icon is now available!');
        console.log('[Backend] Right-click the green circle with "H" in your system tray to access the menu');
      }
    }
  });

  backendProcess.stderr.on('data', (data) => {
    const error = data.toString().trim();
    if (error) {
      console.error(`[Backend Error] ${error}`);
      
      // Check if it's a tray mode error
      if (error.includes('Tray mode not available') || error.includes('pystray') || error.includes('Pillow')) {
        console.log('[Backend] Tray mode failed, but backend should still work in normal mode');
        console.log('[Backend] To enable tray icon, run: pip install pystray pillow');
      }
    }
  });

  backendProcess.on('close', (code) => {
    console.log(`[Backend] Process exited with code ${code}`);
    backendProcess = null;
  });

  backendProcess.on('error', (err) => {
    console.error('[Backend] Failed to start backend process:', err);
    backendProcess = null;
    
    // Show error to user if main window is available
    if (mainWindow) {
      mainWindow.webContents.send('backend-error', {
        message: 'Failed to start backend process',
        error: err.message
      });
    }
  });

  // Monitor backend startup and send status updates
  backendProcess.on('spawn', () => {
    console.log('[Backend] Process spawned, waiting for startup...');
    if (mainWindow) {
      mainWindow.webContents.send('backend-status', {
        status: 'starting',
        message: 'Backend is starting up...'
      });
    }
  });

  // Give the backend a moment to start
  setTimeout(async () => {
    const isNowRunning = await isBackendRunning();
    if (isNowRunning) {
      console.log('[Backend] Successfully started and responding');
    } else {
      console.log('[Backend] Started but not yet responding - may still be starting up');
    }
  }, 2000);
}

function cleanupAndExit() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  
  console.log('Cleaning up and exiting...');
  
  // Stop backend if we started it
  if (backendProcess) {
    stopBackend();
  }
  
  // Force exit in development mode
  if (isDev) {
    console.log('Development mode: forcing process exit');
    process.exit(0);
  } else {
    app.quit();
  }
}

// Function to stop the backend process
function stopBackend() {
  if (backendProcess) {
    console.log('Stopping backend process...');
    backendProcess.kill('SIGTERM');
    
    // Force kill after 5 seconds if it doesn't stop gracefully
    setTimeout(() => {
      if (backendProcess && !backendProcess.killed) {
        console.log('Force killing backend process...');
        backendProcess.kill('SIGKILL');
      }
    }, 5000);
    
    backendProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 300,
    minHeight: 200,
    maxWidth: undefined, // No maximum width limit
    maxHeight: undefined, // No maximum height limit
    title: 'ProcessBot',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset',
    autoHideMenuBar: true,
    show: false,
    center: true,
    resizable: true,
    maximizable: true,
    minimizable: true,
    movable: true,
    closable: true,
    alwaysOnTop: false,
    fullscreenable: true,
    skipTaskbar: false
  });

  const startUrl = isDev 
    ? 'http://localhost:3000' 
    : `file://${path.join(__dirname, '../build/index.html')}`;
  
  mainWindow.loadURL(startUrl);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Remove the menu bar completely
  mainWindow.setMenu(null);

  // Developer tools are hidden by default
  // Uncomment the line below to show them in development
  // if (isDev) {
  //   mainWindow.webContents.openDevTools();
  // }

  mainWindow.on('closed', () => {
    mainWindow = null;
    // Clean up Node.js processes before quitting
    cleanupNodeProcesses();
    if (isDev) {
      process.exit(0);
    } else {
      app.quit();
    }
  });

}

app.whenReady().then(() => {
  createWindow();
  // Start the backend process when the app is ready
  startBackend();
});

app.on('window-all-closed', () => {
  // Clean up Node.js processes before quitting
  cleanupNodeProcesses();
  // Don't stop backend when all windows are closed - just quit the frontend
  if (isDev) {
    process.exit(0);
  } else {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Handle app termination
app.on('before-quit', (event) => {
  // Clean up Node.js processes before quitting
  cleanupNodeProcesses();
  // Don't stop backend - let it keep running
  // Just quit the frontend
  if (isDev) {
    process.exit(0);
  } else {
    app.quit();
  }
});

// Handle process termination signals
process.on('SIGINT', () => {
  console.log('Received SIGINT, shutting down frontend...');
  cleanupNodeProcesses();
  if (isDev) {
    process.exit(0);
  } else {
    app.quit();
  }
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM, shutting down frontend...');
  cleanupNodeProcesses();
  if (isDev) {
    process.exit(0);
  } else {
    app.quit();
  }
});

// IPC handlers for backend communication
ipcMain.handle('stop-backend', async () => {
  console.log('Stopping backend by user request...');
  
  try {
    // First try to use the API shutdown endpoint
    const response = await fetch(getApiUrl('/shutdown'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (response.ok) {
      console.log('Backend shutdown requested via API');
      // Wait a moment for the backend to shut down
      setTimeout(() => {
        if (backendProcess) {
          console.log('Force killing backend process...');
          backendProcess.kill('SIGKILL');
          backendProcess = null;
        }
      }, 2000);
      return { success: true, message: 'Backend shutdown requested' };
    } else {
      throw new Error(`API shutdown failed: ${response.status}`);
    }
  } catch (error) {
    console.log('API shutdown failed, falling back to process kill:', error.message);
    // Fallback to the old method
    stopBackend();
    return { success: true, message: 'Backend stopped (fallback method)' };
  }
});

ipcMain.handle('is-backend-running', async () => {
  // Check if backend is actually running and responding
  const isRunning = await isBackendRunning();
  return { running: isRunning };
});

// Directory picker handler
ipcMain.handle('select-directory', async () => {
  const { dialog } = require('electron');
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory']
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    return { filePath: result.filePaths[0] };
  }
  return null;
});

ipcMain.handle('get-config', async () => {
  try {
    // First check if backend is healthy
    const healthResponse = await fetch(getApiUrl('/health'));
    if (!healthResponse.ok) {
      throw new Error('Backend not healthy');
    }
    
    // Then get config
    const response = await fetch(getApiUrl('/config'));
    if (!response.ok) {
      throw new Error('Failed to get config');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to get config:', error);
    throw error; // Re-throw to trigger error handling in frontend
  }
});

ipcMain.handle('update-config', async (event, config) => {
  try {
    const response = await fetch(getApiUrl('/config'), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config)
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to update config:', error);
    throw error;
  }
});

ipcMain.handle('get-accounts', async () => {
  try {
    const response = await fetch(getApiUrl('/accounts'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get accounts:', error);
    return { accounts: [] };
  }
});

ipcMain.handle('get-recent-actions', async () => {
  try {
    const response = await fetch(getApiUrl('/recent-actions'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get recent actions:', error);
    return { actions: [] };
  }
});

ipcMain.handle('get-detailed-actions', async () => {
  try {
    const response = await fetch(getApiUrl('/recent-actions/detailed'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get detailed actions:', error);
    return { actions: [] };
  }
});

ipcMain.handle('get-ai-interactions', async () => {
  try {
    const response = await fetch(getApiUrl('/ai-interactions'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get AI interactions:', error);
    return { interactions: [] };
  }
});

ipcMain.handle('get-automation-history', async () => {
  try {
    const response = await fetch(getApiUrl('/automation-history'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get automation history:', error);
    return { automations: [] };
  }
});

// Email account management
ipcMain.handle('add-email-account', async (event, emailData) => {
  try {
    const response = await fetch(getApiUrl('/accounts/email'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(emailData)
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to add email account:', error);
    throw error;
  }
});

ipcMain.handle('add-oauth-account', async () => {
  try {
    const response = await fetch(getApiUrl('/accounts/oauth'), {
      method: 'POST'
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to get OAuth URL:', error);
    throw error;
  }
});

ipcMain.handle('exchange-oauth-code', async (event, code) => {
  console.info("exchanging oauth code");
  try {
    const response = await fetch(getApiUrl('/accounts/oauth/exchange'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });
    console.log("resssponse status", response.status);
    if (response.status !== 200) {
      console.error("HTTP", response.status, "error");
      throw new Error("HTTP", response.status, "error exchanging OAuth code, response:", response);
    }
    console.log("Exchange OAuth response:", response);
    return await response.json();
  } catch (error) {
    console.error('Failed to exchange OAuth code:', error);
    throw error;
  }
});

ipcMain.handle('remove-account', async (event, accountId) => {
  try {
    const response = await fetch(getApiUrl(`/accounts/${accountId}`), {
      method: 'DELETE'
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to remove account:', error);
    throw error;
  }
});

// Open external URLs
ipcMain.handle('open-external', async (event, url) => {
  try {
    await shell.openExternal(url);
    return { success: true };
  } catch (error) {
    console.error('Failed to open external URL:', error);
    throw error;
  }
});

// Error management
ipcMain.handle('get-errors', async (event, limit = 50, source = null) => {
  try {
    const url = source ? getApiUrl(`/errors?source=${source}`) : getApiUrl(`/errors?limit=${limit}`);
    const response = await fetch(url);
    return await response.json();
  } catch (error) {
    console.error('Failed to get errors:', error);
    return { errors: [] };
  }
});

ipcMain.handle('clear-errors', async () => {
  try {
    const response = await fetch(getApiUrl('/errors'), {
      method: 'DELETE'
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to clear errors:', error);
    throw error;
  }
});

ipcMain.handle('get-error-count', async () => {
  try {
    const response = await fetch(getApiUrl('/errors/count'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get error count:', error);
    return { count: 0 };
  }
});

// Automation Agent handlers
ipcMain.handle('get-patterns', async () => {
  try {
    const response = await fetch(getApiUrl('/patterns'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get patterns:', error);
    return { patterns: [] };
  }
});

ipcMain.handle('generate-automation-plan', async (event, patternDescription) => {
  try {
    const response = await fetch(getApiUrl('/generate-automation-plan'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pattern_description: patternDescription })
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to generate automation plan:', error);
    throw error;
  }
});

ipcMain.handle('generate-script', async (event, patternDescription) => {
  try {
    const response = await fetch(getApiUrl('/generate-script'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pattern_description: patternDescription })
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to generate script:', error);
    throw error;
  }
});

ipcMain.handle('execute-script', async (event, script, scriptName) => {
  try {
    const response = await fetch(getApiUrl('/execute-script'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script: script, script_name: scriptName })
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to execute script:', error);
    throw error;
  }
});

ipcMain.handle('get-time-saved-stats', async () => {
  try {
    const response = await fetch(getApiUrl('/time-saved-stats'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get time saved stats:', error);
    return { 
      status: 'error', 
      stats: {
        total_time_saved: 0,
        daily_breakdown: [],
        predictions: [],
        automation_efficiency: 0
      }
    };
  }
});

ipcMain.handle('get-execution-history', async () => {
  try {
    const response = await fetch(getApiUrl('/execution-history'));
    
    if (!response.ok) {
      console.error('Failed to get execution history:', response.status, response.statusText);
      return { executions: [] };
    }
    
    const text = await response.text();
    try {
      return JSON.parse(text);
    } catch (parseError) {
      console.error('Failed to parse execution history JSON:', parseError);
      console.error('Response text:', text);
      return { executions: [] };
    }
  } catch (error) {
    console.error('Failed to get execution history:', error);
    return { executions: [] };
  }
});

// New Automation Workflow handlers
ipcMain.handle('get-pending-suggestions', async () => {
  try {
    const response = await fetch(getApiUrl('/automation/pending-suggestions'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get pending suggestions:', error);
    return { suggestions: [], count: 0 };
  }
});

ipcMain.handle('accept-suggestion', async (event, suggestionId) => {
  try {
    const response = await fetch(getApiUrl(`/automation/suggestion/${suggestionId}/accept`), {
      method: 'POST'
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to accept suggestion:', error);
    throw error;
  }
});

ipcMain.handle('reject-suggestion', async (event, suggestionId) => {
  try {
    const response = await fetch(getApiUrl(`/automation/suggestion/${suggestionId}/reject`), {
      method: 'POST'
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to reject suggestion:', error);
    throw error;
  }
});

ipcMain.handle('provide-explanation', async (event, suggestionId, explanation) => {
  try {
    const response = await fetch(getApiUrl(`/automation/suggestion/${suggestionId}/explain`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ explanation })
    });
    
    const result = await response.json();
    
    if (!response.ok) {
      throw new Error(result.detail || `HTTP ${response.status}`);
    }
    
    return result;
  } catch (error) {
    console.error('Failed to provide explanation:', error);
    throw error;
  }
});

ipcMain.handle('refine-script', async (event, suggestionId, refinement) => {
  try {
    const response = await fetch(getApiUrl(`/automation/suggestion/${suggestionId}/refine`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ refinement })
    });
    
    const result = await response.json();
    
    if (!response.ok) {
      throw new Error(result.detail || `HTTP ${response.status}`);
    }
    
    return result;
  } catch (error) {
    console.error('Failed to refine script:', error);
    throw error;
  }
});

ipcMain.handle('get-cursor-position', () => {
  const { screen } = require('electron');
  const point = screen.getCursorScreenPoint();
  return { x: point.x, y: point.y };
});

// Create desktop popup for automation suggestion
ipcMain.handle('show-automation-popup', async (event, suggestion) => {
  const { BrowserWindow, screen } = require('electron');
  
  // Get primary display
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;
  
  // Center on screen - 25% bigger
  const windowWidth = 1125;
  const windowHeight = 750;
  const x = Math.floor((width - windowWidth) / 2);
  const y = Math.floor((height - windowHeight) / 2);
  
  const popupWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: x,
    y: y,
    frame: true,
    transparent: false,
    alwaysOnTop: true,
    skipTaskbar: false,
    resizable: false,
    title: 'ProcessBot - Automation Suggestion',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  // Load popup HTML
  popupWindow.loadFile(path.join(__dirname, 'popup-window.html'));

  // Send suggestion data to popup
  popupWindow.webContents.on('did-finish-load', () => {
    popupWindow.webContents.send('set-suggestion', suggestion);
  });

  // Handle messages from popup
  ipcMain.on('popup-accept', (event, suggestionId) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('suggestion-accepted', suggestionId);
    }
  });

  ipcMain.on('popup-reject', (event, suggestionId) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('suggestion-rejected', suggestionId);
    }
  });

  ipcMain.on('open-main-window-automation', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.show();
      mainWindow.focus();
      // Send message to switch to automation tab
      mainWindow.webContents.send('switch-to-automation');
    }
  });

  ipcMain.on('popup-mute', async (event, minutes) => {
    try {
      const response = await fetch(getApiUrl('/automation/mute'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ minutes: minutes })
      });
      const result = await response.json();
      console.log(`Automation muted for ${minutes} minutes until ${result.muted_until}`);
    } catch (error) {
      console.error('Failed to mute automation:', error);
    }
  });

  // Track window
  popupWindows.push(popupWindow);

  // Auto-close after 30 seconds
  setTimeout(() => {
    if (!popupWindow.isDestroyed()) {
      popupWindow.close();
    }
  }, 30000);

  popupWindow.on('closed', () => {
    popupWindows = popupWindows.filter(w => w !== popupWindow);
  });

  return { success: true };
});

ipcMain.handle('confirm-and-execute', async (event, suggestionId) => {
  try {
    const response = await fetch(getApiUrl(`/automation/suggestion/${suggestionId}/confirm-and-execute`), {
      method: 'POST'
    });
    
    const result = await response.json();
    
    if (!response.ok) {
      throw new Error(result.detail || result.error || `HTTP ${response.status}`);
    }
    
    return result;
  } catch (error) {
    console.error('Failed to execute automation:', error);
    throw error;
  }
});

ipcMain.handle('get-all-suggestions', async () => {
  try {
    const response = await fetch(getApiUrl('/automation/suggestions/all'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get all suggestions:', error);
    return { suggestions: [], count: 0 };
  }
});

ipcMain.handle('get-action-registry-stats', async () => {
  try {
    const response = await fetch(getApiUrl('/automation/action-registry/stats'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get action registry stats:', error);
    return { error: 'Failed to load stats' };
  }
});

ipcMain.handle('get-action-registry-all', async (event, limit = 100) => {
  try {
    const response = await fetch(getApiUrl(`/automation/action-registry/all?limit=${limit}`));
    return await response.json();
  } catch (error) {
    console.error('Failed to get action registry all:', error);
    return { actions: [], count: 0 };
  }
});

ipcMain.handle('get-long-term-status', async () => {
  try {
    const response = await fetch(getApiUrl('/automation/long-term/status'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get long-term status:', error);
    return { status: 'not_available' };
  }
});

ipcMain.handle('get-time-saved', async () => {
  try {
    const response = await fetch(getApiUrl('/automation/time-saved'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get time saved:', error);
    return { display: '0h 0m 0s', total_seconds: 0 };
  }
});

ipcMain.handle('get-current-activity', async () => {
  try {
    const response = await fetch(getApiUrl('/automation/current-activity'));
    return await response.json();
  } catch (error) {
    console.error('Failed to get current activity:', error);
    return { 
      current_app: null, 
      current_window: null, 
      recent_keys: [], 
      recent_app_switches: [],
      keyboard_sequence: "" 
    };
  }
});

ipcMain.handle('get-execution-status', async (event, suggestionId) => {
  try {
    const response = await fetch(getApiUrl(`/automation/suggestion/${suggestionId}/status`));
    if (!response.ok) {
      console.error('Failed to get execution status:', response.status, response.statusText);
      return { status: 'unknown', error: 'Failed to fetch status' };
    }
    return await response.json();
  } catch (error) {
    console.error('Failed to get execution status:', error);
    return { status: 'unknown', error: error.message };
  }
});

// App Usage IPC handlers
ipcMain.handle('get-app-usage-today', async () => {
  try {
    const url = getApiUrl('/app-usage/today');
    console.log('📞 Fetching app usage today from:', url);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    
    console.log('📥 Response status:', response.status);
    const data = await response.json();
    console.log('📊 Today usage data:', data);
    return data;
  } catch (error) {
    console.error('❌ Failed to get today app usage:', error.message);
    return { date: new Date().toISOString().split('T')[0], usage: {}, total_minutes: 0 };
  }
});

ipcMain.handle('get-app-usage-week', async () => {
  try {
    const url = getApiUrl('/app-usage/week');
    console.log('📞 Fetching app usage week from:', url);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    
    console.log('📥 Response status:', response.status);
    const data = await response.json();
    console.log('📊 Week usage data keys:', Object.keys(data));
    return data;
  } catch (error) {
    console.error('❌ Failed to get week app usage:', error.message);
    return { week_usage: {} };
  }
});

ipcMain.handle('get-app-usage-hourly', async (event, date = null) => {
  try {
    const url = date ? getApiUrl(`/app-usage/hourly?date=${date}`) : getApiUrl('/app-usage/hourly');
    console.log('📞 Fetching app usage hourly from:', url);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    
    console.log('📥 Response status:', response.status);
    const data = await response.json();
    console.log('📊 Hourly usage data keys:', Object.keys(data));
    return data;
  } catch (error) {
    console.error('❌ Failed to get hourly app usage:', error.message);
    return { date: date || new Date().toISOString().split('T')[0], hourly_usage: {} };
  }
});

ipcMain.handle('get-app-usage-stats', async () => {
  try {
    const url = getApiUrl('/app-usage/stats');
    console.log('📞 Fetching app usage stats from:', url);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    
    console.log('📥 Response status:', response.status);
    const data = await response.json();
    console.log('📊 Stats data:', data);
    return data;
  } catch (error) {
    console.error('❌ Failed to get app usage stats:', error.message);
    return { 
      total_time_today_seconds: 0,
      total_time_today_minutes: 0,
      most_used_app_today: null,
      most_used_app_duration_seconds: 0,
      most_used_app_duration_minutes: 0,
      unique_apps_tracked: 0,
      current_app: null 
    };
  }
});

// Long-term summarization IPC handlers
ipcMain.handle('get-minute-summaries', async (event, limit = 100) => {
  try {
    const response = await fetch(getApiUrl(`/summaries/minute?limit=${limit}`));
    return await response.json();
  } catch (error) {
    console.error('Failed to get minute summaries:', error);
    return { summaries: [], count: 0 };
  }
});

ipcMain.handle('get-ten-minute-summaries', async (event, limit = 100) => {
  try {
    const response = await fetch(getApiUrl(`/summaries/ten-minute?limit=${limit}`));
    return await response.json();
  } catch (error) {
    console.error('Failed to get ten-minute summaries:', error);
    return { summaries: [], count: 0 };
  }
});

ipcMain.handle('delete-minute-summary', async (event, summaryId) => {
  try {
    const response = await fetch(getApiUrl(`/summaries/minute/${summaryId}`), {
      method: 'DELETE'
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to delete minute summary:', error);
    return { error: 'Failed to delete summary' };
  }
});

ipcMain.handle('delete-ten-minute-summary', async (event, summaryId) => {
  try {
    const response = await fetch(getApiUrl(`/summaries/ten-minute/${summaryId}`), {
      method: 'DELETE'
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to delete ten-minute summary:', error);
    return { error: 'Failed to delete summary' };
  }
});