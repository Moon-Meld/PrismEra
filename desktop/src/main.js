/**
 * PrismEra Desktop Application Main Process (Electron).
 * Handles desktop window management, Python AI gateway lifecycle,
 * native menus, system tray, and cross-platform native behaviors.
 */

const { app, BrowserWindow, Menu, Tray, shell, dialog, ipcMain } = require('electron');
const path = require('path');
const http = require('http');
const { spawn, execSync } = require('child_process');
const fs = require('fs');

const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');
const PORT = process.env.PRISMERA_PORT || 8000;
const BACKEND_URL = `http://127.0.0.1:${PORT}`;

let mainWindow = null;
let splashWindow = null;
let tray = null;
let backendProcess = null;
let backendStartedByUs = false;
let isQuitting = false;

// Project root directory
const PROJECT_ROOT = app.isPackaged
  ? path.join(process.resourcesPath, 'app')
  : path.resolve(__dirname, '../..');

// Single Instance Lock
const gotSingleInstanceLock = app.requestSingleInstanceLock();
if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

/**
 * Perform HTTP GET check to test if PrismEra backend is running.
 */
function checkBackendHealth(timeoutMs = 1500) {
  return new Promise((resolve) => {
    const req = http.get(`${BACKEND_URL}/api/admin/config`, { timeout: timeoutMs }, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 400);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Locate Python binary across OS environments.
 */
function findPythonBinary() {
  const isWin = process.platform === 'win32';
  const venvPython = isWin
    ? path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')
    : path.join(PROJECT_ROOT, '.venv', 'bin', 'python');

  if (fs.existsSync(venvPython)) {
    return venvPython;
  }

  // Fallback to system python
  const candidates = isWin ? ['python.exe', 'py.exe'] : ['python3', 'python'];
  for (const cmd of candidates) {
    try {
      execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch {
      // ignore
    }
  }
  return isWin ? 'python.exe' : 'python3';
}

/**
 * Launch PrismEra FastAPI server if not already running.
 */
async function ensureBackendRunning() {
  const alreadyRunning = await checkBackendHealth();
  if (alreadyRunning) {
    console.log(`[PrismEra Desktop] Backend already running at ${BACKEND_URL}`);
    backendStartedByUs = false;
    return true;
  }

  console.log('[PrismEra Desktop] Starting embedded Python backend...');
  const pythonBin = findPythonBinary();
  console.log(`[PrismEra Desktop] Using Python binary: ${pythonBin}`);

  const env = {
    ...process.env,
    PYTHONPATH: PROJECT_ROOT,
    PYTHONUNBUFFERED: '1',
    HOST: '127.0.0.1',
    PORT: String(PORT)
  };

  try {
    backendProcess = spawn(pythonBin, ['-m', 'prismera', 'serve', '--host', '127.0.0.1', '--port', String(PORT)], {
      cwd: PROJECT_ROOT,
      env,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    backendStartedByUs = true;

    backendProcess.stdout.on('data', (data) => {
      console.log(`[PrismEngine stdout] ${data.toString().trim()}`);
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`[PrismEngine stderr] ${data.toString().trim()}`);
    });

    backendProcess.on('close', (code) => {
      console.log(`[PrismEngine] Process terminated with code ${code}`);
      if (!isQuitting && mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('desktop:backend-status', { running: false, code });
      }
    });

    // Poll until ready (max 30 seconds)
    const maxRetries = 60;
    for (let i = 0; i < maxRetries; i++) {
      await new Promise((r) => setTimeout(r, 500));
      const healthy = await checkBackendHealth();
      if (healthy) {
        console.log('[PrismEra Desktop] Python AI Gateway verified ready!');
        return true;
      }
    }

    throw new Error('Timeout waiting for PrismEra Gateway to initialize.');
  } catch (err) {
    console.error('[PrismEra Desktop] Failed to launch Python backend:', err);
    dialog.showErrorBox(
      '棱镜纪后台服务启动异常',
      `无法启动本地 Python 网关服务。\n错误信息: ${err.message}\n请确保 Python 虚拟环境与依赖已正确安装。`
    );
    return false;
  }
}

/**
 * Create splash loading window.
 */
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 440,
    height: 480,
    frame: false,
    transparent: true,
    resizable: false,
    center: true,
    alwaysOnTop: true,
    show: false,
    backgroundColor: '#00000000',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  splashWindow.loadFile(path.join(__dirname, 'splash.html'));
  splashWindow.once('ready-to-show', () => {
    splashWindow.show();
  });
}

/**
 * Create main workbench window.
 */
function createMainWindow() {
  const isMac = process.platform === 'darwin';
  const iconPath = path.join(__dirname, '../assets', isMac ? 'icon.icns' : 'icon.ico');

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 1080,
    minHeight: 700,
    title: 'PrismEra · 棱镜纪 - 全球留学多智能体桌面工作台',
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    show: false,
    backgroundColor: '#090d16',
    titleBarStyle: isMac ? 'hiddenInset' : 'default',
    trafficLightPosition: isMac ? { x: 18, y: 18 } : undefined,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: false
    }
  });

  mainWindow.loadURL(BACKEND_URL);

  mainWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    mainWindow.show();
    if (isDev) {
      mainWindow.webContents.openDevTools({ mode: 'detach' });
    }
  });

  mainWindow.on('close', (event) => {
    if (!isQuitting && process.platform === 'darwin') {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });
}

/**
 * Configure application menus.
 */
function setupMenu() {
  const isMac = process.platform === 'darwin';

  const template = [
    ...(isMac
      ? [
          {
            label: 'PrismEra',
            submenu: [
              { label: '关于 PrismEra (棱镜纪)', role: 'about' },
              { type: 'separator' },
              {
                label: '检查更新...',
                click: () => {
                  shell.openExternal('https://github.com/prism-era/prismera/releases');
                }
              },
              { type: 'separator' },
              { label: '隐藏 PrismEra', role: 'hide' },
              { label: '隐藏其他', role: 'hideOthers' },
              { label: '显示全部', role: 'unhide' },
              { type: 'separator' },
              { label: '退出 PrismEra', role: 'quit' }
            ]
          }
        ]
      : []),
    {
      label: '文件',
      submenu: [
        {
          label: '开启新规划会话',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.executeJavaScript(
                'document.getElementById("new-session-btn")?.click()'
              );
            }
          }
        },
        {
          label: '导出个人升学报告 (Dossier)',
          accelerator: 'CmdOrCtrl+E',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.executeJavaScript(
                'document.getElementById("btn-export-dossier")?.click()'
              );
            }
          }
        },
        { type: 'separator' },
        isMac ? { label: '关闭窗口', role: 'close' } : { label: '退出', role: 'quit' }
      ]
    },
    {
      label: '编辑',
      submenu: [
        { label: '撤销', role: 'undo' },
        { label: '重做', role: 'redo' },
        { type: 'separator' },
        { label: '剪切', role: 'cut' },
        { label: '复制', role: 'copy' },
        { label: '粘贴', role: 'paste' },
        { label: '全选', role: 'selectAll' }
      ]
    },
    {
      label: '视图',
      submenu: [
        { label: '重新加载工作台', accelerator: 'CmdOrCtrl+R', role: 'reload' },
        { label: '强制重新加载', accelerator: 'CmdOrCtrl+Shift+R', role: 'forceReload' },
        { type: 'separator' },
        { label: '放大', role: 'zoomIn' },
        { label: '缩小', role: 'zoomOut' },
        { label: '重置缩放', role: 'resetZoom' },
        { type: 'separator' },
        { label: '全屏模式', role: 'togglefullscreen' },
        { label: '开发者工具 (DevTools)', accelerator: 'Alt+CmdOrCtrl+I', role: 'toggleDevTools' }
      ]
    },
    {
      label: '引擎与控制台',
      submenu: [
        {
          label: '打开棱镜系统控制台',
          accelerator: 'CmdOrCtrl+Shift+C',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.executeJavaScript(
                'document.getElementById("btn-open-console")?.click()'
              );
            }
          }
        },
        {
          label: '在默认浏览器中打开 Web 版',
          click: () => {
            shell.openExternal(BACKEND_URL);
          }
        },
        {
          label: '查看 OpenAPI / Swagger 交互文档',
          click: () => {
            shell.openExternal(`${BACKEND_URL}/docs`);
          }
        },
        { type: 'separator' },
        {
          label: '重启本地光学 AI 网关',
          click: async () => {
            await restartBackend();
          }
        }
      ]
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '官方项目主页 (GitHub)',
          click: () => {
            shell.openExternal('https://github.com/prism-era/prismera');
          }
        },
        {
          label: '客户端安装与使用手册',
          click: () => {
            shell.openExternal('https://github.com/prism-era/prismera/blob/main/docs/DESKTOP_INSTALL.md');
          }
        },
        {
          label: '报告缺陷与建议 (Issues)',
          click: () => {
            shell.openExternal('https://github.com/prism-era/prismera/issues');
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

/**
 * Configure system tray icon.
 */
function setupTray() {
  const trayIconPath = path.join(__dirname, '../assets/tray.png');
  if (!fs.existsSync(trayIconPath)) return;

  try {
    tray = new Tray(trayIconPath);
    tray.setToolTip('PrismEra (棱镜纪) · 全球留学多智能体桌面工作台');

    const contextMenu = Menu.buildFromTemplate([
      {
        label: '显示工作台窗口',
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        }
      },
      {
        label: '在浏览器中打开 Web 端',
        click: () => {
          shell.openExternal(BACKEND_URL);
        }
      },
      { type: 'separator' },
      {
        label: '重启 AI 网关引擎',
        click: async () => {
          await restartBackend();
        }
      },
      { type: 'separator' },
      {
        label: '退出 PrismEra',
        click: () => {
          isQuitting = true;
          app.quit();
        }
      }
    ]);

    tray.setContextMenu(contextMenu);
    tray.on('double-click', () => {
      if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
      }
    });
  } catch (err) {
    console.warn('[PrismEra Desktop] Tray initialization skipped:', err);
  }
}

/**
 * Terminate backend process cleanly.
 */
function terminateBackend() {
  if (backendProcess && backendStartedByUs) {
    console.log('[PrismEra Desktop] Terminating backend process...');
    try {
      if (process.platform === 'win32') {
        execSync(`taskkill /pid ${backendProcess.pid} /T /F`);
      } else {
        backendProcess.kill('SIGINT');
        setTimeout(() => {
          try {
            backendProcess.kill('SIGKILL');
          } catch {
            // ignore
          }
        }, 1500);
      }
    } catch {
      // Process might already be dead
    }
    backendProcess = null;
  }
}

/**
 * Restart the backend process.
 */
async function restartBackend() {
  terminateBackend();
  await new Promise((r) => setTimeout(r, 1000));
  await ensureBackendRunning();
  if (mainWindow) {
    mainWindow.reload();
  }
}

// IPC Handlers
ipcMain.handle('desktop:open-external', (_event, url) => shell.openExternal(url));
ipcMain.handle('desktop:show-in-folder', (_event, fullPath) => shell.showItemInFolder(fullPath));
ipcMain.handle('desktop:select-file', async (_event, options) => {
  if (!mainWindow) return null;
  return await dialog.showOpenDialog(mainWindow, options || {});
});
ipcMain.handle('desktop:restart-backend', async () => {
  await restartBackend();
  return true;
});
ipcMain.handle('desktop:get-backend-status', async () => {
  const healthy = await checkBackendHealth(500);
  return {
    running: healthy,
    port: PORT,
    url: BACKEND_URL,
    startedByDesktop: backendStartedByUs
  };
});

// App Lifecycle
app.whenReady().then(async () => {
  createSplashWindow();
  setupMenu();
  setupTray();

  const success = await ensureBackendRunning();
  if (success) {
    createMainWindow();
  } else {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

app.on('before-quit', () => {
  isQuitting = true;
  terminateBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
