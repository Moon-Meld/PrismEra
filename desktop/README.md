# PrismEra Desktop · 棱镜纪原生桌面客户端

PrismEra (棱镜纪) 桌面工作台，支持 macOS (.dmg) 与 Windows (.exe / 便携版)，提供比纯 Web 浏览器更具生产力的本地光学工作环境。

## 🌟 核心特性

- 🖥️ **跨平台原生桌面环境**：
  - **macOS**：完美适配 Apple Silicon (M1/M2/M3/M4) 与 Intel 架构，支持暗黑毛玻璃外观 (`hiddenInset` 标题栏) 与菜单快捷键。
  - **Windows**：提供 NSIS 经典向导安装包与便携绿色版，自动注册系统快捷方式。
- ⚡ **本地常驻与零外网延迟**：本地 SQLite 知识底座、混合向量库与先修课图谱毫秒级检索。
- 🔒 **隐私沙盒与安全隔离**：全案简历与成绩单解析在本地受控环境中进行，零数据泄露风险。
- 🛡️ **双模模型支持**：支持在线大模型 (OpenAI / DeepSeek / Claude / Qwen) 及本地离线模型 (Ollama / vLLM / LM Studio)。
- 🔄 **后台引擎生命周期自洽**：启动客户端时自动唤醒本地 Python 网关，退出客户端时安全释放端口与资源。

## 📦 目录结构

```
desktop/
├── assets/                  # 应用图标资源
│   ├── icon.icns            # macOS 图标包
│   ├── icon.ico             # Windows 多分辨率图标
│   ├── icon.png             # 高清 PNG 图标
│   └── tray.png             # 系统托盘图标
├── build/
│   └── entitlements.mac.plist # macOS Hardened Runtime 权限清单
├── src/
│   ├── main.js              # Electron 主进程 (生命周期、窗口与进程管理)
│   ├── preload.js           # 安全上下文预加载脚本
│   ├── splash.html          # 原生暗黑光学启动加载页
│   └── splash.css           # 启动加载页样式
├── electron-builder.yml     # 跨平台打包配置文件
└── package.json             # 依赖与打包脚本
```

## 🛠️ 本地开发与调试

### 前置要求

- Node.js >= 18
- Python >= 3.10 (已安装项目依赖 `pip install -r requirements.txt`)

### 启动开发环境

```bash
# 1. 进入 desktop 目录
cd desktop

# 2. 安装 Electron 依赖
npm install

# 3. 启动开发模式
npm start
```

## 🚀 跨平台打包构建

### 构建 macOS 安装包 (.dmg & .zip)

```bash
# 构建当前 Mac 架构 (Apple Silicon 或 Intel)
npm run dist:mac

# 构建 Apple Silicon 专用包 (M 系列芯片)
npm run dist:mac-arm64

# 构建 Intel 专用包
npm run dist:mac-x64
```

产物输出目录：`desktop/dist/`
- `PrismEra-0.2.0-mac-arm64.dmg`
- `PrismEra-0.2.0-mac-x64.dmg`

### 构建 Windows 安装包 (.exe & 便携版)

```bash
# 构建 NSIS 安装包与免安装便携版
npm run dist:win
```

产物输出目录：`desktop/dist/`
- `PrismEra-Setup-0.2.0.exe` (NSIS 安装包)
- `PrismEra-Portable-0.2.0.exe` (便携绿色单文件)

---

💡 **提示**：项目已提供 GitHub Actions CI/CD 流水线模版文件 (`desktop/desktop-release.yml`)。若需在云端全自动并行构建 Windows 与 macOS 的可执行安装包并自动发布 Release，可将该文件复制至仓库 `.github/workflows/desktop-release.yml`（需确保 GitHub Token 具有 `workflow` 写入权限）。
