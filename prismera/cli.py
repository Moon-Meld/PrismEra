"""Interactive CLI for PrismEra (棱镜纪)."""

from __future__ import annotations
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
    print_colored("─" * 65, "90")
    print_colored(ONBOARDING_MESSAGE, "37")
    print_colored("─" * 65, "90")
    print_colored("💡 快捷指令: /profile (查看当前光谱档案) | /help (帮助) | exit / quit (退出)\n", "33")

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

            if user_input == "/help":
                print_colored("""
【棱镜纪五大智能体指令指引】：
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

            print_colored("\n" + "═" * 65, "35")
            print(reply)
            print_colored("═" * 65 + "\n", "35")

        except (KeyboardInterrupt, EOFError):
            print_colored("\n[棱镜纪] 会话已中断。祝你顺利！\n", "35")
            break
        except Exception as e:
            print_colored(f"\n[错误] 处理请求时发生异常: {e}\n", "31")


if __name__ == "__main__":
    run_cli()
