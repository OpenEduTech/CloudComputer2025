const { contextBridge, ipcRenderer } = require('electron');
const fs = require('fs');
const { Blob } = require('buffer'); // Node.js 15+ 内置 Blob

contextBridge.exposeInMainWorld('electronAPI', {
  openFileDialog: () => ipcRenderer.invoke('dialog:openFile'),
  // 你可以在这里添加更多的API暴露
  getFileData: (filePath) => {
    // 使用 Node.js 的 fs 读取文件二进制数据
    const buffer = fs.readFileSync(filePath);
    return buffer;
  }
});