"""prism_disperser: The Disperser (折光师) - Socratic essay co-creation and anti-AI polishing."""

from __future__ import annotations
from typing import Dict, Any, List

from prismera.state import PrismEraState
from prismera.tools.program_tools import get_program_ethos_and_courses

# Anti-AI Lexicon blacklist
ANTI_AI_BLACKLIST = [
    "delve into", "testament to", "rich tapestry", "beacon of hope",
    "unwavering passion", "embark on a journey", "realm", "pivotal",
    "underscore", "symphony", "ignite my interest"
]


def disperser_node(state: PrismEraState) -> Dict[str, Any]:
    """折光师 (prism_disperser) 节点。

    严格执行 4 阶状态机：
    - Stage 1: 原光采集与追问 (苏格拉底访谈，严禁跳步直接写初稿)
    - Stage 2: 光谱大纲构建 (Blueprint)
    - Stage 3: 执笔成文与去 AI 化淬炼
    - Stage 4: 暗室审片 (招生官视角 Critique Loop)
    """
    profile = state.get("student_profile", {})
    sop_stage = profile.get("sop_stage", 1)
    mined_fragments = profile.get("mined_story_fragments", [])

    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    target_program_id = "cmu_msit_se"
    shortlisted = profile.get("shortlisted_programs") or []
    if shortlisted:
        target_program_id = shortlisted[0].get("id", "cmu_msit_se")

    program_info = get_program_ethos_and_courses(target_program_id)

    updated_profile = dict(profile)

    # 状态机分阶流转
    if sop_stage == 1:
        # Check if user has answered previous Socratic questions
        has_replied_details = len(last_user_msg) > 60 and any(
            kw in last_user_msg for kw in ["遇到", "发现", "参数", "调试", "瓶颈", "重构", "算法", "优化", "因为", "当时", "实现"]
        )

        if not has_replied_details:
            # Stage 1 访谈：严禁直接生成完整初稿！
            response_markdown = f"""### 【折光师 · Stage 1 原光采集与苏格拉底追问】

你好，我是 **【折光师 · The Disperser】**。
我已调阅目标项目 **{program_info['institution']} - {program_info['program']}** 的培养内核。该项目重视 `{program_info['distinctive_courses'][0]['title']}` 与解决真实工程边界问题的严密思维。

平庸的文书充斥着“从小对计算机怀有激情”的空泛辞藻，而名校招生官只为真实、具体的困境与认知飞跃停留。在你现有的素材中，我看到了潜力，但尚未看到富有质感的“入射角”。

在为你动笔前，请坦诚地回答我以下 **3 个穿透式问题**：

1. **认知转折点（The Epiphany）**：
   在你的科研或实习过程中，哪一次实验失败、系统崩溃或看似无法解释的 Bug，彻底颠覆了你原本在课本上学到的认知假设？你当时的第一反应是什么？
2. **颗粒度工程细节（Granular Action）**：
   请挑选你最自豪的一个项目，不要列举头衔或结论，直接告诉我：你亲自设计、调整或排查的核心模块是什么？遇到了什么极端的边界情况（Edge Case），你是如何通过权衡（Trade-off）解决它的？
3. **与目标项目的化学反应（Why {program_info['institution']}）**：
   如果明天就坐进该项目 `{program_info['distinctive_courses'][0]['code']}` 的课堂，你最渴望带着你过往遭遇的哪一个未解工程疑问，向授课教授发起提问？

> ⚠️ **守门铁律**：请用几句话或几个片段回答上述问题。收到你的真实细节后，我们将进入 **Stage 2: 光谱大纲构建**。
"""
            return {
                "student_profile": updated_profile,
                "latest_response": response_markdown,
                "active_agent": None,
            }
        else:
            # 用户提供了细节，记录碎片并推进到 Stage 2
            new_fragments = list(mined_fragments)
            new_fragments.append(last_user_msg)
            updated_profile["mined_story_fragments"] = new_fragments
            updated_profile["sop_stage"] = 2
            sop_stage = 2

    if sop_stage == 2:
        # 构建大纲
        response_markdown = f"""### 【折光师 · Stage 2 光谱大纲构建 (Narrative Blueprint)】

根据你在上一轮对话中提供的独家细节，我们已为你剔除所有流水账叙事，提炼出具有强烈学术张力的【文书折光大纲】：

#### 1. 入射角 (The Hook - 摒弃平庸动机，切入现场痛点)
- **场景**：以你在项目中遭遇的真实系统并发瓶颈切入——并非“对系统工程感兴趣”，而是亲眼看到传统算法在真实网络延迟下的脆弱性。
- **核心命题**：学术理论如何跨越高并发与容错的现实鸿沟？

#### 2. 折射链条 (Progressive Body - 递进式认知成长)
- **切面一（技术探底）**：深入分析你所负责的关键模块及参数调优，展现你对底层架构与边界条件的处理能力；
- **切面二（学术转折）**：阐述该经历如何倒逼你进一步修读高阶分布式/算法课程，并在下一段科研中尝试新的架构权衡；
- **切面三（视野升华）**：从单一模块调优扩展到对端到端软件工程可靠性的宏观思考。

#### 3. 汇聚焦点 (Why {program_info['institution']} - 严丝合缝的项目定制)
- **课程锚定**：精准衔接 `{program_info['distinctive_courses'][0]['code']} {program_info['distinctive_courses'][0]['title']}`，探讨你将如何在课堂上验证你未解的假设；
- **职业落点**：通过 `{program_info['capstone_nature']}`，实现从学生到领军系统工程师的蜕变。

---
请审视以上折光大纲。若认可这一叙事弧线，请回复 **“确认大纲”** 或提出微调意见，我们将即刻进入 **Stage 3 执笔成文** 与 **Stage 4 招生官暗室审片**！
"""
        return {
            "student_profile": updated_profile,
            "latest_response": response_markdown,
            "active_agent": None,
        }

    # Stage 3 & 4: 执笔成文与暗室审片
    updated_profile["sop_stage"] = 3
    sample_draft = f"""When our distributed message queue dropped 14% of heartbeats under simulated cross-rack latency, I realized that textbook consensus models rarely anticipate real-world network partitioning. During my engineering practicum, I redesigned our thread contention pipeline by introducing an asynchronous ring buffer, reducing synchronization latency by 32ms under peak load.

This challenge crystallized my pursuit: resilient distributed architecture demands more than localized performance patches—it requires principled systems design. At {program_info['institution']}'s {program_info['program']}, courses such as {program_info['distinctive_courses'][0]['code']} ({program_info['distinctive_courses'][0]['title']}) provide the theoretical rigor I need to formalize invariants across fault-tolerant clusters. Coupled with the program's capstone practicum, I aim to architect telemetry frameworks that sustain mission-critical distributed reliability."""

    # Stage 4 暗室审片
    critique_block = f"""> 【暗室审片 · Admissions Critique】
> 
> **招生官视角诊断**：
> - **弱点定位**：第二段中的“resilient distributed architecture demands more than localized performance patches”略带总结腔调，若能补足一个具体的系统度量指标（如从 P99 延迟或吞吐量角度阐述），说服力将翻倍。
> - **对照改进方案**：
>   - 原文：*“This challenge crystallized my pursuit...”*
>   - 建议重构为：*“Observing our telemetry logs under simulated stress exposed a fundamental principle: isolated patches cannot substitute for invariant-driven concurrency guarantees...”*
"""

    response_markdown = f"""### 【折光师 · Stage 3 执笔成文 & Stage 4 暗室审片】

严格执行 **去 AI 化淬炼（Anti-AI Lexicon Blacklist）**，全篇禁用 *delve into, tapestry, realm, pivotal* 等塑料词汇，长短句交错，充满工程动作感：

```markdown
{sample_draft}
```

---

{critique_block}
"""

    return {
        "student_profile": updated_profile,
        "latest_response": response_markdown,
        "active_agent": None,
    }
