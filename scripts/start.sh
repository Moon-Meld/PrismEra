#!/usr/bin/env bash
# ==============================================================================
# PrismEra · 棱镜纪 - FastAPI 流式网关与暗黑光学工作台启动脚本
# ==============================================================================

set -e

# 定位项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 环境与解释器检测
if [ -d ".venv" ]; then
  PYTHON_BIN=".venv/bin/python"
  UVICORN_BIN=".venv/bin/uvicorn"
elif command -v python3 &> /dev/null; then
  PYTHON_BIN="python3"
  UVICORN_BIN="uvicorn"
else
  PYTHON_BIN="python"
  UVICORN_BIN="uvicorn"
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo -e "\033[1;35m"
echo "  ____       _                 _____            "
echo " |  _ \ _ __(_)___ _ __ ___   | ____|_ __ __ _ "
echo " | |_) | '__| / __| '_ \` _ \  |  _| | '__/ _\` |"
echo " |  __/| |  | \__ \ | | | | | | |___| | | (_| |"
echo " |_|   |_|  |_|___/_| |_| |_| |_____|_|  \__,_|"
echo "         棱 镜 纪 · 暗 黑 光 学 工 作 台 网 关"
echo -e "\033[0m"
echo -e "\033[90m────────────────────────────────────────────────────────────────────\033[0m"
echo -e "\033[1;36m✦ 正在拉起 FastAPI 异步流式引擎 (PrismEra Streaming Gateway)...\033[0m"
echo -e "\033[1;32m✦ Web 工作台入口:   http://${HOST}:${PORT}/\033[0m"
echo -e "\033[33m✦ SSE 流式接口:     http://${HOST}:${PORT}/api/chat/stream\033[0m"
echo -e "\033[34m✦ 光谱档案接口:     http://${HOST}:${PORT}/api/session/{id}/spectrum\033[0m"
echo -e "\033[37m✦ API 文档 (Swagger): http://${HOST}:${PORT}/docs\033[0m"
echo -e "\033[90m────────────────────────────────────────────────────────────────────\033[0m"
echo ""

export PYTHONPATH="$PROJECT_ROOT"

exec "$PYTHON_BIN" -m prismera serve --host "$HOST" --port "$PORT"
