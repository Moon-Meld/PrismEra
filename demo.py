"""PrismEra End-to-End Optical Journey Demonstration.

Simulates an applicant's complete progression through the 5 PrismEra agents:
1. Onboarding & Central Luminary Greeting
2. Pre-calibration parameter interception (Ironclad Rule 1)
3. GraphRAG School Selection with The Locus (定焦师)
4. Transcript & Prerequisite KG diagnosis with The Facet (切面师)
5. Socratic SOP co-creation with The Disperser (折光师)
6. Academic paper synergy & cold email with The Resonator (共鸣者)
"""

from prismera.engine import PrismEraSession
from prismera.cli import print_colored, BANNER


def run_demo():
    print_colored(BANNER, "35")
    print_colored("✦✦✦ PrismEra (棱镜纪) 全流程多智能体旅程演示 ✦✦✦\n", "36")

    session = PrismEraSession(thread_id="demo_applicant_001")

    steps = [
        (
            "Step 1: 首次触达与原光汇聚",
            "你好，我是大三学生，想了解一下留学规划。"
        ),
        (
            "Step 2: 意图触发与前置校准拦截 (调度铁律测试)",
            "我想直接做选校定位，帮我看看能申哪些好学校？"
        ),
        (
            "Step 3: 补齐四维基准指标，定焦师 (prism_locus) 启动 GraphRAG 三步定焦",
            "我是浙江大学软件工程本科，目前均分88.5分，雅思总分7.5、口语7.0，目标是美研和英研CS项目！"
        ),
        (
            "Step 4: 切面师 (prism_facet) 开展成绩单切面诊断与先修课图谱核查",
            "定校很有底了！请切面师帮我深度诊断一下成绩单和先修课，看看是否有结构性暗区？"
        ),
        (
            "Step 5: 折光师 (prism_disperser) 启动 Stage 1 苏格拉底追问 (严禁跳步代写)",
            "选校和背景都清晰了，我想开始准备 CMU 软件工程项目的 SOP 文书，怎么写比较出彩？"
        ),
        (
            "Step 6: 提供真实工程细节，折光师推进至 Stage 2 大纲构建",
            "我们在做分布式消息队列时，遇到网络分区下传统心跳算法导致雪崩的问题。我亲自编写了基于异步环形缓冲区的自适应调度器，调整了超时重试窗口，使系统在15%网络丢包下延迟降低了32ms。"
        ),
        (
            "Step 7: 共鸣者 (prism_resonator) 寻找学术共振并撰写 220 词黄金标准套磁信",
            "我还想申请 UIUC 的分布式系统博士，想联系 Indranil Gupta 教授，请检索他的最新论文并帮我写一封高信噪比套磁信。"
        )
    ]

    for title, prompt in steps:
        print_colored(f"\n{'='*70}", "33")
        print_colored(f"▶ {title}", "1;33")
        print_colored(f"[Applicant 提问] {prompt}", "32")
        print_colored(f"{'='*70}", "33")

        result = session.send_user_message(prompt)

        thought = result.get("luminary_thought")
        target = result.get("active_agent")
        decision = result.get("routing_decision")
        reply = result.get("latest_response")

        if thought:
            print_colored(f"↳ [司光者洞察] {thought}", "90")
        if target:
            print_colored(f"↳ [调度专职智能体] 【{target}】", "34")
        elif decision:
            print_colored(f"↳ [调度决策] {decision}", "35")

        print("\n" + reply + "\n")


if __name__ == "__main__":
    run_demo()
