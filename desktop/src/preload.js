/**
 * PrismEra Desktop Preload Script.
 * Provides safe context bridge APIs between Electron Main process and Web Workbench.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('prismeraDesktop', {
  isDesktop: true,
  platform: process.platform, // 'darwin' | 'win32' | 'linux'
  isMac: process.platform === 'darwin',
  isWindows: process.platform === 'win32',
  version: '0.2.0',

  // System actions
  openExternal: (url) => ipcRenderer.invoke('desktop:open-external', url),
  showItemInFolder: (fullPath) => ipcRenderer.invoke('desktop:show-in-folder', fullPath),
  selectFile: (options) => ipcRenderer.invoke('desktop:select-file', options),
  
  // Backend Engine control
  restartBackend: () => ipcRenderer.invoke('desktop:restart-backend'),
  getBackendStatus: () => ipcRenderer.invoke('desktop:get-backend-status'),
  
  // Event listeners
  onBackendStatus: (callback) => {
    const handler = (_event, status) => callback(status);
    ipcRenderer.on('desktop:backend-status', handler);
    return () => ipcRenderer.removeListener('desktop:backend-status', handler);
  }
});
