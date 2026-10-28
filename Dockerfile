# ==============================================================================
# PrismEra (棱镜纪) · 生产级全栈多智能体工作台 Dockerfile
# ==============================================================================
FROM python:3.11-slim

# 环境变量配置
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# 安装基础依赖与健康检测工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 核心依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码与静态资源
COPY prismera /app/prismera
COPY web /app/web
COPY benchmarks /app/benchmarks
COPY scripts /app/scripts
COPY demo.py /app/demo.py
COPY Makefile /app/Makefile
COPY .env.example /app/.env.example

# 确保持久化数据目录存在并拷贝初始种子
RUN mkdir -p /app/data /app/prismera/data && \
    cp /app/prismera/data/seed_graph_data.json /app/data/seed_graph_data.json 2>/dev/null || true

# 暴露单端口服务
EXPOSE 8000

# 容器健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动一体化全栈 Web + API 统一网关服务
CMD ["python", "-m", "prismera", "serve", "--host", "0.0.0.0", "--port", "8000"]
