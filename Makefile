.PHONY: help serve cli demo eval init-db test clean docker-build docker-up docker-down desktop desktop-dev desktop-build-mac desktop-build-win

help:
	@echo "╔════════════════════════════════════════════════════════════════════╗"
	@echo "║           PrismEra (棱镜纪) · 全球留学多智能体系统工程管理           ║"
	@echo "╚════════════════════════════════════════════════════════════════════╝"
	@echo "  make serve             一键初始化知识底座并拉起 Web + API 全栈一体化工作台"
	@echo "  make desktop           启动原生暗黑光学桌面客户端 (PyWebView 原生窗口)"
	@echo "  make desktop-dev       启动 Electron 桌面客户端开发模式"
	@echo "  make desktop-build-mac 编译打包 macOS 原生安装镜像 (.dmg)"
	@echo "  make desktop-build-win 编译打包 Windows 原生安装程序 (.exe)"
	@echo "  make cli               进入交互式彩色终端会话模式 (支持 /upload 导入)"
	@echo "  make demo              运行全流程端到端光学旅程演练"
	@echo "  make eval              运行 GraphRAG 28 个高危陷阱题量化评测基准并输出报告"
	@echo "  make init-db           重置并重新灌注全量种子知识图谱与同辈案例向量库"
	@echo "  make test              执行全套端到端与模块单元自动化测试 (Pytest)"
	@echo "  make docker-build      构建生产级 Docker 镜像"
	@echo "  make docker-up         使用 Docker Compose 后台启动全套容器服务"
	@echo "  make docker-down       停止并移除 Docker 容器"
	@echo "  make clean             清理临时 Python 缓存与 pytest 临时文件"

serve:
	python -m prismera serve --host 0.0.0.0 --port 8000

desktop:
	python -m prismera desktop

desktop-dev:
	cd desktop && npm start

desktop-build-mac:
	cd desktop && npm run dist:mac

desktop-build-win:
	cd desktop && npm run dist:win

cli:
	python -m prismera cli

demo:
	python -m prismera demo

eval:
	python -m prismera eval

init-db:
	python -m prismera init-db

test:
	PYTHONPATH=. pytest -v

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
