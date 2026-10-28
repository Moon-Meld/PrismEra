"""PrismEra Native Python Desktop Launcher.

Provides a lightweight, zero-node native desktop window mode for PrismEra
using PyWebView (with automated fallback to browser app mode) while running
the FastAPI gateway concurrently in a background daemon thread.
"""

from __future__ import annotations
import os
import sys
import time
import socket
import threading
import webbrowser
import logging
from typing import Optional

logger = logging.getLogger("PrismEraDesktop")


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if the given network port is already occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """Poll URL until server responds with 200 or timeout."""
    import urllib.request
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PrismEra-HealthCheck"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def run_fastapi_thread(host: str, port: int):
    """Run uvicorn server in a background thread."""
    import uvicorn
    from prismera.api.server import app

    uvicorn_config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()


def launch_desktop(
    host: str = "127.0.0.1",
    port: int = 8000,
    width: int = 1440,
    height: int = 940,
    title: str = "PrismEra · 棱镜纪 - 全球留学多智能体桌面工作台",
    auto_init: bool = True
):
    """Start backend gateway and open desktop window."""
    if auto_init:
        try:
            from scripts.init_knowledge_base import init_knowledge_base
            init_knowledge_base()
        except Exception as e:
            logger.warning(f"Knowledge base auto-init: {e}")

    server_url = f"http://{host}:{port}"

    # 1. Start server if not running
    if not is_port_in_use(port, host):
        logger.info(f"Starting PrismEra Gateway on {server_url} in background thread...")
        server_thread = threading.Thread(
            target=run_fastapi_thread,
            args=(host, port),
            daemon=True,
            name="PrismEra-Backend-Thread"
        )
        server_thread.start()

        # Wait for readiness
        if not wait_for_server(f"{server_url}/api/admin/config"):
            print("⚠️ 正在等待网关就绪...")
            wait_for_server(f"{server_url}/", timeout=10.0)
    else:
        logger.info(f"Existing PrismEra Gateway detected at {server_url}")

    # 2. Try native PyWebView first
    try:
        import webview
        print(f"✦ 启动 PyWebView 原生桌面窗口 ({width}x{height})...")
        window = webview.create_window(
            title=title,
            url=server_url,
            width=width,
            height=height,
            min_size=(1024, 700),
            background_color="#090d16",
        )
        webview.start(private_mode=False)
        return
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"PyWebView error ({e}), falling back to app browser mode.")

    # 3. Fallback: Launch browser in standalone app mode if Chrome/Edge available
    app_launched = False
    if sys.platform == "darwin":
        # macOS Google Chrome App Mode
        chrome_app = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(chrome_app):
            import subprocess
            subprocess.Popen([chrome_app, f"--app={server_url}"])
            app_launched = True
    elif sys.platform == "win32":
        # Windows Chrome or Edge App Mode
        for path in [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        ]:
            if os.path.exists(path):
                import subprocess
                subprocess.Popen([path, f"--app={server_url}"])
                app_launched = True
                break

    if not app_launched:
        print(f"✦ 打开默认浏览器访问: {server_url}")
        webbrowser.open(server_url)

    # Keep alive in fallback mode
    print("✦ PrismEra 桌面会话运行中，按 Ctrl+C 退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[棱镜纪] 桌面会话已终止。")


if __name__ == "__main__":
    launch_desktop()
