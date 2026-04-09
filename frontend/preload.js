const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.invoke('minimize'),
  jumpToTerminal: () => ipcRenderer.invoke('jump-to-terminal'),
  getSessions: () => ipcRenderer.invoke('get-sessions'),
  getPendingPermissions: () => ipcRenderer.invoke('get-pending-permissions'),
  approvePermission: (id) => ipcRenderer.invoke('approve-permission', id),
  denyPermission: (id) => ipcRenderer.invoke('deny-permission', id)
});
