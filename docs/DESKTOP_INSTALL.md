# PrismEra (棱镜纪) · 桌面客户端安装与使用手册 (Windows & macOS)

本文档面向所有使用 **PrismEra 原生桌面客户端** 的学员、留学顾问与开发者，详细介绍 Windows 与 macOS 下载安装、权限配置、离线模型集成与本地源码构建流程。

---

## 目录

1. [桌面客户端与 Web 网页端特性对比](#1-桌面客户端与-web-网页端特性对比)
2. [macOS 下载与安装指南 (.dmg)](#2-macos-下载与安装指南-dmg)
3. [Windows 下载与安装指南 (.exe / 便携版)](#3-windows-下载与安装指南-exe--便携版)
4. [本地完全离线与大模型加速配置 (Ollama / vLLM)](#4-本地完全离线与大模型加速配置-ollama--vllm)
5. [开发者从源码打包构建](#5-开发者从源码打包构建)
6. [常见问题与故障排查 (FAQ)](#6-常见问题与故障排查-faq)

---

## 1. 桌面客户端与 Web 网页端特性对比

PrismEra 桌面客户端基于跨平台原生框架打造，内嵌暗黑光学流式渲染核心与本地知识底座，具备以下原生优势：

| 能力维度 | Web 网页端 (`http://localhost:8000`) | PrismEra 桌面端 (macOS / Windows) |
| :--- | :--- | :--- |
| **运行时独立性** | 依赖 Chrome/Edge/Safari 浏览器多标签页 | 专属独立原生窗口，零标签页干扰，硬件加速流畅运行 |
| **数据安全性与隐私** | 浏览器缓存机制可能被意外清空 | 本地 SQLite 强隔离加密存储，成绩单与文书绝对不出本地沙盒 |
| **离线大模型适配** | 需配置浏览器端跨域 (CORS) 访问本地端口 | 原生无缝打通本地 Ollama、vLLM、LM Studio 离线模型 |
| **系统级深度融合** | 无法驻留系统托盘 | 支持 macOS 菜单栏与 Windows 任务栏托盘常驻守护 |
| **文档与成绩单导入** | 需通过 Web 上传组件逐个拾取 | 支持将 PDF/Word 简历、成绩单直接拖拽至窗口秒级解析 |
| **后台生命周期** | 需要终端常驻运行命令行后台 | 打开客户端自动唤醒后台，退出应用自动释放资源与端口 |

---

## 2. macOS 下载与安装指南 (.dmg)

### 2.1 芯片架构选型

PrismEra 为 Mac 用户提供针对不同处理器的优化架构构建包：

- **Apple Silicon 版本 (`PrismEra-0.2.0-mac-arm64.dmg`)**：
  - 适用：搭载 **M1 / M2 / M3 / M4** 系列及其 Pro / Max / Ultra 芯片的所有 Mac（MacBook Air/Pro、Mac mini、Mac Studio、iMac）。
  - 特性：ARM64 纯原生指令集，启动极速，发热低且功耗更优。
- **Intel 架构版本 (`PrismEra-0.2.0-mac-x64.dmg`)**：
  - 适用：早期搭载 Intel Core 酷睿处理器的 Mac 机型。

### 2.2 安装步骤

1. 在 Web 工作台点击顶部 **【💻 桌面客户端】** 或前往 [GitHub Releases 页面](https://github.com/prism-era/prismera/releases/latest) 下载对应的 `.dmg` 镜像文件。
2. 双击装载下载的 `.dmg` 文件。
3. 在弹出的窗口中，将 **PrismEra** 图标直接拖拽到右侧的 **Applications（应用程序）** 文件夹中。
4. 在启动台（Launchpad）或访达应用程序列表中，点击 **PrismEra** 即可启动。

### 2.3 首次启动安全提示拦截处理 (Gatekeeper)

因为开源软件未捆绑高昂的商业数字证书签名，macOS Gatekeeper 安全机制可能会弹出如下提示：
> *“无法打开 PrismEra，因为无法验证开发者。”* 或 *“PrismEra 来源不明”*

**三种官方推荐解决方式（任选其一即可）：**

- **方式一（最简便）**：按住键盘上的 <kbd>Control</kbd> 键，右键点击 `/Applications/PrismEra.app`，在弹出右键菜单中点击 **【打开】**，随后在确认弹窗中再次点击 **【打开】** 即可永久信任。
- **方式二（系统设置授权）**：打开 macOS **【系统设置】** -> **【隐私与安全性】**，向下滑动找到安全性区域，点击 **【仍要打开】** 按钮。
- **方式三（终端一键清除隔离属性）**：打开 Mac 终端，执行以下命令：
  ```bash
  sudo xattr -rd com.apple.quarantine /Applications/PrismEra.app
  ```

---

## 3. Windows 下载与安装指南 (.exe / 便携版)

### 3.1 版本说明

- **NSIS 安装向导版 (`PrismEra-Setup-0.2.0.exe`) - 推荐**：
  - 标准 Windows 安装向导，支持自定义安装路径，自动创建桌面快捷方式与开始菜单磁贴，支持在 Windows【设置 -> 应用】中一键卸载。
- **便携绿色免安装版 (`PrismEra-Portable-0.2.0.zip`)**：
  - 绿色便携，无需管理员权限，解压即用。数据和配置可随 U 盘随身携带。

### 3.2 安装向导版步骤

1. 下载 `PrismEra-Setup-0.2.0.exe`。
2. 双击启动安装向导程序。
3. 选择安装目标文件夹（例如 `D:\PrismEra` 或默认 `C:\Users\<用户名>\AppData\Local\Programs\PrismEra`）。
4. 勾选“创建桌面快捷方式”，点击【安装】。
5. 安装完成后点击【完成】，立即拉起 PrismEra 桌面工作台。

### 3.3 Windows Defender SmartScreen 拦截提示处理

首次运行非商店下载的可执行程序时，Windows Defender 可能弹出蓝色全屏拦截提示：
> *“Windows 已保护你的电脑 · Microsoft Defender SmartScreen 已阻止启动一个未识别的应用。”*

**处理步骤：**
1. 点击弹窗中的 **【更多信息】**（More info）下划线链接。
2. 此时底部会显示 **【仍要运行】**（Run anyway）按钮，点击该按钮即可正常启动。

---

## 4. 本地完全离线与大模型加速配置 (Ollama / vLLM)

桌面客户端支持完全脱离外网运行，将学术隐私与升学档案保护到极致：

### 4.1 配合本地 Ollama 运行

1. 本地启动 Ollama 服务并拉取中英文能力强劲的大语言模型：
   ```bash
   # 安装运行千问或 LLaMA3 模型
   ollama run qwen2.5:14b
   ```
2. 打开 PrismEra 桌面客户端，点击右上角 **【⚙️ 系统控制台】**。
3. 进入 **【模型与引擎配置】** 选项卡：
   - **模型供应商 (Provider)**：选择 `Custom / OpenAI Compatible`
   - **大模型名称 (Model)**：输入 `qwen2.5:14b`
   - **API 接口地址 (Base URL)**：输入 `http://127.0.0.1:11434/v1`
   - **API 密钥 (API Key)**：输入任意字符串（如 `ollama`）
4. 点击 **【测试模型连通性】**，提示“连通性验证成功”后点击 **【保存当前配置】**。
5. 整套选校智能体、文书折光师访谈与图谱诊断将完全由本地显卡算力推理，零外网流量产生！

---

## 5. 开发者从源码打包构建

如果你希望为定制化的 PrismEra 私有版本打出专属的 Windows 或 macOS 分发包：

### 5.1 构建依赖准备

- Node.js >= 18.0.0
- Python >= 3.10
- npm >= 9.0.0

```bash
# 克隆代码仓库并安装后端依赖
git clone https://github.com/prism-era/prismera.git
cd prismera
python3 -m venv .venv
source .venv/bin/activate  # Windows 用户运行: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5.2 编译打包指令

```bash
# 进入桌面端目录并安装 Electron 构建工具链
cd desktop
npm install

# 🍎 构建 macOS 安装包 (.dmg)
npm run dist:mac-arm64     # 仅构建 Apple Silicon (M系列芯片)
npm run dist:mac-x64       # 仅构建 Intel 架构
npm run dist:mac           # 同时构建两者

# 🪟 构建 Windows 安装包 (.exe)
npm run dist:win           # 编译生成 NSIS 安装包与免安装 Portable 版
```

产物将输出在 `desktop/dist/` 目录下：
- `PrismEra-0.2.0-mac-arm64.dmg`
- `PrismEra-0.2.0-mac-x64.dmg`
- `PrismEra-Setup-0.2.0.exe`
- `PrismEra-Portable-0.2.0.exe`

### 5.3 跨平台一键打包脚本

项目提供了自动化打包脚本 `scripts/build_desktop.py`，支持环境检测、图标校验与自动计算 SHA256 校验和：

```bash
python scripts/build_desktop.py --target current
```

---

## 6. 常见问题与故障排查 (FAQ)

### Q1: 提示端口 8000 已被占用导致无法启动？
- **解答**：若本地已有其他进程占用了 8000 端口，可通过环境变量指定自定义端口：
  - macOS: `PRISMERA_PORT=8088 open /Applications/PrismEra.app`
  - Windows: 在命令行执行 `set PRISMERA_PORT=8088 && PrismEra.exe`
  - 或者直接关闭占用 8000 端口的进程：`lsof -ti:8000 | xargs kill -9`。

### Q2: 桌面客户端的日志文件保存在哪里？
- **macOS**：`~/Library/Logs/PrismEra/`
- **Windows**：`%APPDATA%\PrismEra\logs\`

### Q3: 桌面客户端与 Web 网页端可以同时打开吗？
- **解答**：完全可以。桌面客户端在本地运行后，你随时可以在 Chrome/Safari 中输入 `http://127.0.0.1:8000` 访问同步的 Web 工作台，两者数据共享本地 SQLite 底座。

---

© 2026 PrismEra Team. Released under the MIT License.
