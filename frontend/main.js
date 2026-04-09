const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const http = require('http');

let mainWindow;

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: 64,  // Collapsed width
    height: 200,
    x: 0,
    y: Math.floor((height - 200) / 2),  // Vertically centered
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.loadFile('index.html');

  // Handle window blur - when focus is lost, allow click-through to activate terminal
  mainWindow.on('blur', () => {
    // Window lost focus
  });

  mainWindow.webContents.on('did-finish-load', () => {
    console.log('Window loaded successfully');
  });
}

// IPC handlers
ipcMain.handle('minimize', () => {
  if (mainWindow) mainWindow.hide();
});

ipcMain.handle('jump-to-terminal', async () => {
  console.log('Jump to terminal requested');
  try {
    // Call backend API to activate terminal
    const result = await fetchAPI('/api/terminal/activate', 'POST');
    console.log('Terminal activation result:', result);
    return result;
  } catch (err) {
    console.error('Failed to activate terminal:', err);
    return { success: false, message: err.message };
  }
});

ipcMain.handle('get-sessions', async () => {
  return fetchAPI('/api/sessions');
});

ipcMain.handle('get-pending-permissions', async () => {
  return fetchAPI('/api/permissions/pending');
});

ipcMain.handle('approve-permission', async (event, id) => {
  return fetchAPI(`/api/permissions/${id}/approve`, 'POST');
});

ipcMain.handle('deny-permission', async (event, id) => {
  return fetchAPI(`/api/permissions/${id}/deny`, 'POST');
});

ipcMain.handle('get-terminal-sessions', async () => {
  return fetchAPI('/api/terminal/sessions');
});

function fetchAPI(endpoint, method = 'GET') {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: '127.0.0.1',
      port: 8080,
      path: endpoint,
      method: method,
      headers: method === 'POST' ? { 'Content-Type': 'application/json' } : {}
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(data);
        }
      });
    });

    req.on('error', reject);
    req.end();
  });
}

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

app.whenReady().then(() => {
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
