#!/usr/bin/env python3
"""PrismEra Desktop Distribution Packager.

Automates the build and packaging of macOS (.dmg) and Windows (.exe NSIS/Portable)
installers using Electron & Electron Builder, generating cryptographic checksums
and preparing release assets.
"""

from __future__ import annotations
import os
import sys
import shutil
import hashlib
import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESKTOP_DIR = PROJECT_ROOT / "desktop"
ASSETS_DIR = DESKTOP_DIR / "assets"
DIST_DIR = DESKTOP_DIR / "dist"


def print_banner(msg: str, color_code: str = "36"):
    print(f"\033[1;{color_code}m{msg}\033[0m")


def check_prerequisites():
    """Verify Node, npm, and required build tools."""
    print_banner("✦ 检查构建环境与前置依赖...", "34")
    
    # Check node
    try:
        node_ver = subprocess.check_output(["node", "-v"], text=True).strip()
        print(f"  ✓ Node.js 运行时: {node_ver}")
    except Exception:
        print_banner("❌ 未检测到 Node.js，请先安装 Node.js (>= 18)。", "31")
        sys.exit(1)

    # Check npm
    try:
        npm_ver = subprocess.check_output(["npm", "-v"], text=True).strip()
        print(f"  ✓ npm 包管理器:  v{npm_ver}")
    except Exception:
        print_banner("❌ 未检测到 npm，请先配置环境。", "31")
        sys.exit(1)

    # Check icons
    required_assets = ["icon.png", "icon.icns", "icon.ico"]
    for asset in required_assets:
        asset_path = ASSETS_DIR / asset
        if not asset_path.exists():
            print_banner(f"⚠️ 警告: 资源文件 {asset} 不存在于 {ASSETS_DIR}，正在自动同步...", "33")
            if (PROJECT_ROOT / "assets" / "logo.png").exists():
                shutil.copy2(PROJECT_ROOT / "assets" / "logo.png", asset_path)
        else:
            print(f"  ✓ 图标资源:     {asset} ({asset_path.stat().st_size // 1024} KB)")


def install_desktop_deps():
    """Install npm dependencies in desktop/ directory."""
    node_modules = DESKTOP_DIR / "node_modules"
    if not node_modules.exists():
        print_banner("✦ 正在安装 Electron 及桌面打包工具链依赖 (npm install)...", "35")
        subprocess.run(["npm", "install"], cwd=DESKTOP_DIR, check=True)
    else:
        print("  ✓ desktop/node_modules 依赖库已就绪。")


def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_macos(arch: str = "both"):
    """Run electron-builder to compile macOS .dmg packages."""
    print_banner(f"\n🍏 开始构建 macOS 原生安装镜像 (.dmg) [架构: {arch}]...", "32")
    install_desktop_deps()

    commands = []
    if arch in ["arm64", "both"]:
        commands.append(["npm", "run", "dist:mac-arm64"])
    if arch in ["x64", "both"]:
        commands.append(["npm", "run", "dist:mac-x64"])

    for cmd in commands:
        print_banner(f"✦ 执行: {' '.join(cmd)}", "90")
        subprocess.run(cmd, cwd=DESKTOP_DIR, check=True)


def build_windows():
    """Run electron-builder to compile Windows NSIS installer and portable exe."""
    print_banner("\n🪟 开始构建 Windows 可执行安装包 (.exe / 便携版)...", "32")
    install_desktop_deps()

    cmd = ["npm", "run", "dist:win"]
    print_banner(f"✦ 执行: {' '.join(cmd)}", "90")
    subprocess.run(cmd, cwd=DESKTOP_DIR, check=True)


def print_artifacts_summary():
    """Scan dist directory, compute checksums, and display release summary."""
    if not DIST_DIR.exists():
        return

    artifacts = []
    for f in DIST_DIR.iterdir():
        if f.suffix in [".dmg", ".exe", ".zip", ".msi"] and not f.name.endswith(".blockmap"):
            size_mb = f.stat().st_size / (1024 * 1024)
            sha256 = calculate_sha256(f)
            artifacts.append((f.name, f"{size_mb:.1f} MB", sha256))

    if artifacts:
        print_banner("\n" + "=" * 76, "35")
        print_banner("🎉 PrismEra 原生桌面客户端分发包构建成功！产物清单与指纹：", "1;32")
        print_banner("=" * 76, "35")
        for name, size, sha in artifacts:
            print(f"📦 文件名:  {name}")
            print(f"   大小:    {size}")
            print(f"   SHA256:  {sha}")
            print("-" * 76)
        print_banner(f"📂 产物存储目录: {DIST_DIR}\n", "36")


def main():
    parser = argparse.ArgumentParser(description="PrismEra Desktop Packager (macOS DMG & Windows EXE)")
    parser.add_argument(
        "--target",
        choices=["mac", "win", "all", "current"],
        default="current",
        help="Target platform to build for (default: current OS)"
    )
    parser.add_argument(
        "--mac-arch",
        choices=["arm64", "x64", "both"],
        default="both",
        help="macOS target architecture (default: both arm64 and x64)"
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip npm install check"
    )

    args = parser.parse_args()

    check_prerequisites()

    target = args.target
    if target == "current":
        target = "mac" if sys.platform == "darwin" else ("win" if sys.platform == "win32" else "all")

    if target in ["mac", "all"]:
        if sys.platform != "darwin" and target == "mac":
            print_banner("⚠️ 提示: macOS DMG 构建需要在 macOS 环境下运行。", "33")
        else:
            build_macos(arch=args.mac_arch)

    if target in ["win", "all"]:
        build_windows()

    print_artifacts_summary()


if __name__ == "__main__":
    main()
