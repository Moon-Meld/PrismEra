"""Interactive CLI for PrismEra (棱镜纪)."""

from __future__ import annotations
import os
import sys
import json
from prismera.engine import PrismEraSession
from prismera.prompts.brand_voice import ONBOARDING_MESSAGE

BANNER = r"""
  ____       _                 _____            
 |  _ \ _ __(_)___ _ __ ___   | ____|_ __ __ _ 
 | |_) | '__| / __| '_ ` _ \  |  _| | '__/ _` |
 |  __/| |  | \__ \ | | | | | | |___| | | (_| |
 |_|   |_|  |_|___/_| |_| |_| |_____|_|  \__,_|
         棱 镜 纪 · 全 球 留 学 多 智 能 体 阵 列
"""


def print_colored(text: str, color_code: str = "36"):
    """Print text with ANSI terminal color."""
    print(f"\033[{color_code}m{text}\033[0m")


def run_cli():
    print_colored(BANNER, "35")
    print_colored("─" * 68, "90")
    print_colored(ONBOARDING_MESSAGE, "37")
    print_colored("─" * 68, "90")
    print_colored(
        "💡 快捷指令: /upload <路径> (解析简历/成绩单) | /profile (查看档案) | /help (帮助) | exit (退出)\n",
        "33"
    )

    session = PrismEraSession()

    while True:
        try:
            user_input = input("\033[1;32m[Applicant 光源输入] > \033[0m").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", ":q"]:
                print_colored("\n[棱镜纪] 光束已归拢，祝你前程繁花璀璨，再会。\n", "35")
                break

            if user_input == "/profile":
                profile = session.state.get("student_profile", {})
                print_colored("\n--- 🌌 当前学生光谱档案 (Student Spectrum State) ---", "34")
                print(json.dumps(profile, ensure_ascii=False, indent=2))
                print_colored("--------------------------------------------------\n", "34")
                continue

            if user_input.startswith("/upload"):
                file_arg = user_input[7:].strip().strip("'\"")
                if not file_arg:
                    print_colored("💡 用法: /upload <简历或成绩单文件路径> (例如: /upload resume.pdf 或 /upload transcript.txt)", "33")
                    continue

                if not os.path.exists(file_arg):
                    print_colored(f"❌ 未找到文件: '{file_arg}'，请核对绝对路径或相对路径后重试。\n", "31")
                    continue

                print_colored(f"\n[棱镜文档解析器] 正在解析《{os.path.basename(file_arg)}》并进行 STAR 细节校准...", "90")
                parsed = session.upload_document(file_arg)

                print_colored("\n" + "═" * 68, "32")
                print_colored(f"📄 《{os.path.basename(file_arg)}》解析完毕，已自动填充至学生光谱档案！", "1;32")
                print_colored("═" * 68, "32")

                school_str = f"{parsed.get('undergrad_name') or '未识别院校'} ({parsed.get('undergrad_tier') or '未知层级'})"
                major_str = parsed.get("major") or "未识别专业"
                gpa_str = parsed.get("gpa_raw") or "未识别均分"
                print(f"🏫 本科背景: {school_str} | 专业: {major_str} | 均分/GPA: {gpa_str}")

                if parsed.get("language_scores"):
                    lang_items = [f"{k}: {v}" for k, v in parsed["language_scores"].items()]
                    print(f"🗣️ 语言成绩: {', '.join(lang_items)}")

                prereqs = parsed.get("prerequisite_grades", {})
                if prereqs:
                    print_colored(f"\n📚 核心先修课程提取 ({len(prereqs)} 门):", "36")
                    for c_name, c_info in prereqs.items():
                        print(f"  • {c_name}: {c_info.get('grade')} (匹配原名: {c_info.get('matched_name')})")

                exps = parsed.get("experiences", [])
                if exps:
                    print_colored(f"\n🔬 科研与实习经历提取 ({len(exps)} 项):", "36")
                    for i, exp in enumerate(exps, 1):
                        flag = "\033[33m[⚠️ 待折光挖掘 needs_mining=True]\033[0m" if exp.get("needs_mining") else "\033[32m[✅ STAR完备]\033[0m"
                        print(f"  {i}. {exp.get('title')} ({exp.get('period')}) {flag}")
                        print(f"     ↳ 诊断理由: {exp.get('mining_reason')}")

                print_colored("\n💡 建议下一步操作：", "33")
                print("   - 输入：“让切面师帮我诊断成绩单和先修课匹配度”")
                print("   - 输入：“让折光师深入追问挖掘我的未完备经历”")
                print("   - 输入：“我是上述背景，请定焦师推荐美研/英研CS项目”")
                print_colored("═" * 68 + "\n", "32")
                continue

            if user_input == "/help":
                print_colored("""
【棱镜纪五大智能体与常用指令】：
- /upload <路径>: 导入简历或成绩单 (支持 PDF/TXT/MD)，自动填充档案与先修课并标记待挖掘经历
- /profile: 查看当前累计的学生全局光谱档案 (Student Spectrum State)
- 诊断背景/GPA换算: 输入 "帮我诊断背景，均分87，目标转码CS"
- 选校硬核定位: 输入 "我是985高校计科专业，GPA 3.65/4.0，雅思7.0小分6.5，求美研/英研CS选校"
- 文书深度挖掘: 输入 "准备写SOP文书，目标CMU软件工程，不知道怎么开篇"
- 导师学术套磁: 输入 "想联系UIUC的Indranil Gupta教授，申请2027博士，帮忙写套磁信"
""", "36")
                continue

            print_colored("\n[司光者] 正在校准入射光线角度与意图...", "90")
            result_state = session.send_user_message(user_input)

            thought = result_state.get("luminary_thought")
            decision = result_state.get("routing_decision")
            target = result_state.get("active_agent")
            reply = result_state.get("latest_response")

            if thought:
                print_colored(f"↳ 司光者洞察: {thought}", "90")
            if target:
                print_colored(f"↳ 委派专职智能体: 【{target}】", "34")
            elif decision:
                print_colored(f"↳ 调度决策: {decision}", "33")

            print_colored("\n" + "═" * 68, "35")
            print(reply)
            print_colored("═" * 68 + "\n", "35")

        except (KeyboardInterrupt, EOFError):
            print_colored("\n[棱镜纪] 会话已中断。祝你顺利！\n", "35")
            break
        except Exception as e:
            print_colored(f"\n[错误] 处理请求时发生异常: {e}\n", "31")


def start_web_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False, auto_init: bool = True):
    """Launch the PrismEra Optical Workbench FastAPI Gateway."""
    import uvicorn
    from prismera.db.graph_store import DEFAULT_SQLITE_PATH
    from prismera.db.vector_store import DEFAULT_VECTOR_SQLITE_PATH

    print_colored(BANNER, "35")
    print_colored("─" * 68, "90")

    if auto_init and (not DEFAULT_SQLITE_PATH.exists() or not DEFAULT_VECTOR_SQLITE_PATH.exists()):
        print_colored("⚙️ 检测到本地知识图谱或向量数据库未初始化，正在执行极速种子数据灌注...", "33")
        try:
            from scripts.init_knowledge_base import init_knowledge_base
            init_knowledge_base()
            print_colored("✓ 混合知识底座自动初始化完毕！\n", "32")
        except Exception as e:
            print_colored(f"⚠️ 自动初始化警告: {e}\n", "33")

    print_colored("✦ 棱镜纪 (PrismEra) 暗黑光学全栈工作台正在启动...", "1;36")
    print_colored(f"✦ 访问前端工作台地址: http://localhost:{port} (或 http://127.0.0.1:{port})", "1;32")
    print_colored(f"✦ 系统控制台管理端点: http://localhost:{port}/api/admin/config", "33")
    print_colored(f"✦ RESTful & SSE 流式端点: http://localhost:{port}/api/chat/stream", "33")
    print_colored("─" * 68, "90")
    uvicorn.run("prismera.api.server:app", host=host, port=port, reload=reload)


def main():
    """PrismEra Universal CLI dispatcher supporting serve, cli, demo, eval, and init-db."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m prismera",
        description="PrismEra (棱镜纪) · 全球留学多智能体阵列统一命令行主控入口"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. serve (Web + API gateway)
    serve_parser = subparsers.add_parser("serve", aliases=["web", "server"], help="一键初始化并拉起全栈 Web + API 统一网关服务")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Binding host (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload during development")
    serve_parser.add_argument("--no-init", action="store_true", help="Skip automatic DB existence check")

    # 2. cli (Interactive terminal)
    subparsers.add_parser("cli", aliases=["terminal", "chat"], help="进入交互式彩色终端会话模式")

    # 3. demo (End-to-end simulated run)
    subparsers.add_parser("demo", help="运行全流程端到端光学旅程演练")

    # 4. eval (GraphRAG Benchmark)
    eval_parser = subparsers.add_parser("eval", aliases=["benchmark"], help="运行 GraphRAG 28 个高危陷阱题量化评测基准并输出报告")
    eval_parser.add_argument("--dataset", type=str, default=None, help="Path to golden test cases dataset JSON")
    eval_parser.add_argument("--output-json", type=str, default=None, help="Path for output JSON report")
    eval_parser.add_argument("--output-report", type=str, default=None, help="Path for output Markdown report")
    eval_parser.add_argument("--mode", type=str, choices=["graphrag", "baseline", "both"], default="both", help="Evaluation mode")

    # 5. init-db (Database seeding)
    subparsers.add_parser("init-db", aliases=["init_db", "initdb"], help="重置并重新灌注全量种子知识图谱与案例向量库")

    args = parser.parse_args()

    if args.command in ["serve", "web", "server"]:
        start_web_server(host=args.host, port=args.port, reload=args.reload, auto_init=not args.no_init)
    elif args.command in ["cli", "terminal", "chat"]:
        run_cli()
    elif args.command == "demo":
        from demo import run_demo
        run_demo()
    elif args.command in ["eval", "benchmark"]:
        from benchmarks.run_eval import run_benchmark, export_json_report, export_markdown_report, DEFAULT_DATASET_PATH, DEFAULT_JSON_REPORT_PATH, DEFAULT_MD_REPORT_PATH
        dataset_path = args.dataset or str(DEFAULT_DATASET_PATH)
        json_path = args.output_json or str(DEFAULT_JSON_REPORT_PATH)
        md_path = args.output_report or str(DEFAULT_MD_REPORT_PATH)
        summary = run_benchmark(dataset_path=dataset_path, mode=args.mode, verbose=True)
        export_json_report(summary, json_path)
        export_markdown_report(summary, md_path)
    elif args.command in ["init-db", "init_db", "initdb"]:
        from scripts.init_knowledge_base import init_knowledge_base
        init_knowledge_base()
    else:
        # Default: print banner and help
        print_colored(BANNER, "35")
        parser.print_help()


if __name__ == "__main__":
    main()
