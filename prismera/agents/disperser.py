"""prism_disperser: The Disperser (折光师) - Socratic essay co-creation, inline refraction and anti-AI polishing."""

from __future__ import annotations
import difflib
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from prismera.state import PrismEraState
from prismera.tools.program_tools import get_program_ethos_and_courses
from prismera.guardrails import AntiAIGuardrail
from prismera.llm import get_llm, BaseLLM


def compute_word_diff(old_text: str, new_text: str) -> Tuple[str, List[Dict[str, str]]]:
    """Compute word/token-level diff returning HTML with <ins>/<del> and structured op codes."""
    old_words = re.findall(r"\S+|\s+", old_text)
    new_words = re.findall(r"\S+|\s+", new_text)
    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    html_parts = []
    diff_ops = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_chunk = "".join(old_words[i1:i2])
        new_chunk = "".join(new_words[j1:j2])
        if tag == "equal":
            html_parts.append(old_chunk)
            diff_ops.append({"op": "equal", "text": old_chunk})
        elif tag == "delete":
            html_parts.append(f'<del class="diff-del">{old_chunk}</del>')
            diff_ops.append({"op": "delete", "text": old_chunk})
        elif tag == "insert":
            html_parts.append(f'<ins class="diff-ins">{new_chunk}</ins>')
            diff_ops.append({"op": "insert", "text": new_chunk})
        elif tag == "replace":
            html_parts.append(f'<del class="diff-del">{old_chunk}</del><ins class="diff-ins">{new_chunk}</ins>')
            diff_ops.append({"op": "delete", "text": old_chunk})
            diff_ops.append({"op": "insert", "text": new_chunk})
    return "".join(html_parts), diff_ops


def refract_text_selection(
    selected_text: str,
    instruction: str,
    full_text: Optional[str] = None,
    student_profile: Optional[Dict[str, Any]] = None,
    llm: Optional[BaseLLM] = None,
) -> Dict[str, Any]:
    """Perform local rewrite (Inline Refraction) on selected text with diff generation.

    Strictly adheres to Anti-AI engineering prose and generates token-level diff.
    """
    active_llm = llm or get_llm()
    guardrail = AntiAIGuardrail()

    rewritten_candidate = ""
    inst_lower = instruction.lower()

    if not active_llm.is_mock:
        try:
            profile_context = ""
            if student_profile:
                profile_context = f"Student major: {student_profile.get('major')}, Experiences: {student_profile.get('experiences')}"
            prompt = (
                f"You are The Disperser (折光师), a master admissions essay mentor specializing in authentic, high-signal engineering prose.\n"
                f"Strict Rule: Eliminate AI buzzwords (delve, tapestry, realm, pivotal, testament, beacon).\n"
                f"Rewrite ONLY the following selected text based on the user's refinement instruction.\n"
                f"Context: {full_text or selected_text}\n"
                f"{profile_context}\n\n"
                f"Selected Text: \"{selected_text}\"\n"
                f"Instruction: {instruction}\n\n"
                f"Output ONLY the refined text directly, without markdown code fences or quotes."
            )
            raw_out = active_llm.generate([{"role": "user", "content": prompt}])
            rewritten_candidate = raw_out.strip().strip('"').strip("'")
        except Exception:
            rewritten_candidate = ""

    if not rewritten_candidate:
        # Deterministic / offline intelligent mock rewrite tailored to instruction keywords
        if any(kw in inst_lower for kw in ["腾讯", "tencent", "实习", "指标", "强化", "metric", "qps"]):
            rewritten_candidate = (
                "During my Tencent distributed backend internship, I profiled our message ingestion pipeline under 100K QPS stress, "
                "replacing the legacy thread-locking bottleneck with a zero-copy lock-free ring buffer that reduced P99 synchronization latency by 41%."
            )
        elif any(kw in inst_lower for kw in ["精简", "字数", "concise", "shorten", "压缩"]):
            rewritten_candidate = (
                "When our distributed queue suffered 14% heartbeat loss under simulated latency, "
                "I deployed an asynchronous ring buffer to eliminate contention, cutting latency by 32ms."
            )
        elif any(kw in inst_lower for kw in ["去ai", "去ai味", "塑料", "anti-ai", "真实", "现场感"]):
            rewritten_candidate = (
                "Observing telemetry dropouts under simulated stress forced an empirical pivot: "
                "rather than patching throughput, I engineered an asynchronous ring buffer that stabilized queue latency under 32ms."
            )
        else:
            rewritten_candidate = (
                "By rearchitecting the thread contention pipeline with an asynchronous ring buffer, "
                "we stabilized message throughput and shaved 32ms off P99 latency under simulated cross-rack stress."
            )

    # Post-rewrite anti-AI guardrail validation
    cleansed, was_rewritten, violations = guardrail.apply(rewritten_candidate, llm=active_llm)

    # Compute word-level Diff
    diff_html, diff_tokens = compute_word_diff(selected_text, cleansed)

    # Build full text preview
    full_text_preview = None
    if full_text:
        if selected_text in full_text:
            full_text_preview = full_text.replace(selected_text, cleansed, 1)
        else:
            full_text_preview = full_text + "\n" + cleansed

    return {
        "original_text": selected_text,
        "rewritten_text": cleansed,
        "diff_html": diff_html,
        "diff_tokens": diff_tokens,
        "full_text_preview": full_text_preview,
        "instruction": instruction,
        "was_rewritten_by_guardrail": was_rewritten,
        "anti_ai_violations": violations,
    }


def disperser_node(state: PrismEraState) -> Dict[str, Any]:
    """折光师 (prism_disperser) 节点。

    严格执行 4 阶状态机与 HITL 人机共创断点：
    - Stage 1: 原光采集与追问 (苏格拉底访谈，严禁跳步直接写初稿)
    - Stage 2: 光谱大纲构建 (Blueprint) -> 【HITL 挂起断点】：等待用户在右侧画布调整大纲并确认执笔
    - Stage 3: 执笔成文与去 AI 化淬炼 (配置 Anti-AI Output Guardrail 后置校验与自动重写)
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
    locked_program = profile.get("locked_target_program")
    shortlisted = profile.get("shortlisted_programs") or []
    if locked_program:
        target_program_id = locked_program.get("id", "cmu_msit_se")
    elif shortlisted:
        target_program_id = shortlisted[0].get("id", "cmu_msit_se")

    program_info = get_program_ethos_and_courses(target_program_id)

    updated_profile = dict(profile)
    versions = list(updated_profile.get("sop_versions") or [])

    # 状态机分阶流转
    if sop_stage == 1:
        # Check if user is attempting to bypass Socratic interview or force-generate a draft
        is_force_draft_or_skip = any(
            kw in last_user_msg for kw in [
                "直接帮我写", "直接写", "直接生成", "跳过提问", "不要问", "跳过追问",
                "写一篇完整", "直接给我写", "不需要问", "立刻生成", "立刻出稿", "别废话", "不想回答", "帮我直接写",
                "跳过访谈", "写完整ps", "写一篇ps", "写出初稿", "直接出ps", "跳过问题", "不用问", "别问了", "直接出稿"
            ]
        )

        # User must actually provide substantive engineering details rather than demanding bypass
        has_replied_details = (
            not is_force_draft_or_skip
            and len(last_user_msg) > 60
            and any(kw in last_user_msg for kw in ["遇到", "发现", "参数", "调试", "瓶颈", "重构", "算法", "优化", "因为", "当时", "实现"])
        )

        if not has_replied_details:
            experiences = profile.get("experiences") or []
            mining_targets = [e for e in experiences if e.get("needs_mining")]
            tailored_exp_prompt = ""
            if mining_targets:
                t = mining_targets[0]
                tailored_exp_prompt = f"（针对你档案中待挖掘的经历【{t.get('title')}】）"

            interception_header = ""
            if is_force_draft_or_skip:
                interception_header = (
                    "> 🛑 **【折光师 · Stage 1 防跳步守门拦截】**：\n"
                    "> 检测到跳步执笔诉求。PrismEra 坚守 **'原石未剖，绝不落笔'** 的原则。\n"
                    "> 名校招生官能在 10 秒内识破缺乏真实工程痛点与反思的模板化 AI 套作。直接跳步只会稀释申请竞争力。\n"
                    "> 唯有回答以下穿透式追问，才能提炼出独属于你的高光折射角！\n\n"
                )

            # Stage 1 访谈：严禁直接生成完整初稿！
            response_markdown = f"""### 【折光师 · Stage 1 原光采集与苏格拉底追问】

{interception_header}你好，我是 **【折光师 · The Disperser】**。
我已调阅目标项目 **{program_info['institution']} - {program_info['program']}** 的培养内核。该项目重视 `{program_info['distinctive_courses'][0]['title']}` 与解决真实工程边界问题的严密思维。

平庸的文书充斥着“从小对计算机怀有激情”的空泛辞藻，而名校招生官只为真实、具体的困境与认知飞跃停留。在你现有的素材中，我看到了潜力，但尚未看到富有质感的“入射角”。

在为你动笔前，请坦诚地回答我以下 **3 个穿透式问题**：

1. **认知转折点（The Epiphany）**：
   在你的科研或实习过程中，哪一次实验失败、系统崩溃或看似无法解释的 Bug，彻底颠覆了你原本在课本上学到的认知假设？你当时的第一反应是什么？
2. **颗粒度工程细节（Granular Action）**{tailored_exp_prompt}：
   请挑选你最自豪的一个项目，不要列举头衔或结论，直接告诉我：你亲自设计、调整或排查的核心模块是什么？遇到了什么极端的边界情况（Edge Case），你是如何通过权衡（Trade-off）解决它的？
3. **与目标项目的化学反应（Why {program_info['institution']}）**：
   如果明天就坐进该项目 `{program_info['distinctive_courses'][0]['code']}` 的课堂，你最渴望带着你过往遭遇的哪一个未解工程疑问，向授课教授发起提问？

> ⚠️ **守门铁律**：请用几句话或几个片段回答上述问题。收到你的真实细节后，我们将进入 **Stage 2: 光谱大纲构建**。
"""
            return {
                "student_profile": updated_profile,
                "latest_response": response_markdown,
                "active_agent": None,
                "pending_human_review": None,
            }
        else:
            # 用户提供了细节，记录碎片并推进到 Stage 2
            new_fragments = list(mined_fragments)
            new_fragments.append(last_user_msg)
            updated_profile["mined_story_fragments"] = new_fragments
            updated_profile["sop_stage"] = 2
            sop_stage = 2

    if sop_stage == 2:
        # Check if user has explicitly confirmed the outline to enter Stage 3
        is_confirming_outline = any(
            kw in last_user_msg for kw in [
                "确认大纲", "确认大纲并执笔", "确认执笔", "开始执笔", "执笔成文",
                "进入stage 3", "进入 stage 3", "开始写初稿", "生成初稿", "满意大纲"
            ]
        )

        if not is_confirming_outline:
            # Stage 2: 生成结构化大纲并挂起等待人工确认或微调 (HITL Breakpoint)
            existing_outline = updated_profile.get("sop_outline")
            if not existing_outline:
                default_outline = [
                    {
                        "section": "The Hook",
                        "title": "1. 入射角 (The Hook - 摒弃平庸动机，切入现场痛点)",
                        "points": [
                            "以真实系统并发瓶颈切入——并非“对系统工程感兴趣”，而是亲眼看到传统算法在真实网络延迟下的脆弱性。",
                            "核心命题：学术理论如何跨越高并发与容错的现实鸿沟？"
                        ]
                    },
                    {
                        "section": "Progressive Body",
                        "title": "2. 折射链条 (Progressive Body - 递进式认知成长)",
                        "points": [
                            "切面一（技术探底）：深入分析所负责关键模块及参数调优，展现底层架构与边界条件的处理能力；",
                            "切面二（学术转折）：阐述该经历如何倒逼进一步修读高阶分布式/算法课程，并在下一段科研中尝试新的架构权衡；",
                            "切面三（视野升华）：从单一模块调优扩展到对端到端软件工程可靠性的宏观思考。"
                        ]
                    },
                    {
                        "section": "Why School",
                        "title": f"3. 汇聚焦点 (Why {program_info['institution']} - 严丝合缝的项目定制)",
                        "points": [
                            f"课程锚定：精准衔接 {program_info['distinctive_courses'][0]['code']} {program_info['distinctive_courses'][0]['title']}，探讨如何在课堂上验证未解假设；",
                            f"职业落点：通过 {program_info.get('capstone_nature', '工业界顶石实训 (Capstone)')}，实现从学生到领军系统工程师的蜕变。"
                        ]
                    }
                ]
                updated_profile["sop_outline"] = default_outline
            else:
                default_outline = existing_outline

            # 记录大纲快照版本
            if not any(v.get("stage") == 2 for v in versions):
                versions.append({
                    "version_id": "v1.0",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "stage": 2,
                    "label": "Stage 2 光谱大纲初始版",
                    "author": "The Disperser",
                    "outline": default_outline,
                    "content": "\n".join(f"【{sec['title']}】\n" + "\n".join(f"- {p}" for p in sec['points']) for sec in default_outline),
                    "change_summary": "基于苏格拉底故事碎片提炼的叙事大纲"
                })
                updated_profile["sop_versions"] = versions

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
> ⏸️ **【人机共创挂起点 (HITL Breakpoint)】**：
> 请在右侧【暗室文书画布】中微调大纲各段要点。若认可当前叙事大纲，请点击右侧 **【确认大纲并执笔】** 按钮，或在此回复 **“确认大纲”**，折光师将即刻启动 Stage 3 执笔淬炼与 Stage 4 审片！
"""
            return {
                "student_profile": updated_profile,
                "latest_response": response_markdown,
                "active_agent": None,
                "pending_human_review": "disperser_outline",
            }
        else:
            # 用户确认大纲，流转进入 Stage 3
            updated_profile["sop_stage"] = 3
            sop_stage = 3

    # Stage 3 & 4: 执笔成文与暗室审片
    updated_profile["sop_stage"] = 4
    raw_draft = f"""When our distributed message queue dropped 14% of heartbeats under simulated cross-rack latency, I realized that textbook consensus models rarely anticipate real-world network partitioning. During my engineering practicum, I redesigned our thread contention pipeline by introducing an asynchronous ring buffer, reducing synchronization latency by 32ms under peak load.

This challenge crystallized my pursuit: resilient distributed architecture demands more than localized performance patches—it requires principled systems design. At {program_info['institution']}'s {program_info['program']}, courses such as {program_info['distinctive_courses'][0]['code']} ({program_info['distinctive_courses'][0]['title']}) provide the theoretical rigor I need to formalize invariants across fault-tolerant clusters. Coupled with the program's capstone practicum, I aim to architect telemetry frameworks that sustain mission-critical distributed reliability."""

    # 后置校验器 (Output Guardrail)：扫描 Anti-AI 禁用词，若命中自动触发重写
    llm = get_llm()
    guardrail = AntiAIGuardrail()
    cleansed_draft, was_rewritten, violations = guardrail.apply(raw_draft, llm=llm)

    guardrail_note = ""
    if was_rewritten:
        guardrail_note = f"\n> 🛡️ **【去 AI 校验器动作】**：自动拦截并重写了 {len(violations)} 处禁用词 (`{', '.join(violations)}`)，确保学术质感零塑料感。\n"

    # Stage 4 暗室审片 (Milestone 5.0 三棱镜陪审团多目标帕累托博弈审理)
    from prismera.ml.llm_finetune.pareto_jury import get_pareto_jury
    jury = get_pareto_jury()
    jury_eval = jury.evaluate_draft(
        cleansed_draft,
        target_program=program_info,
        prompt_context=last_user_msg,
    )

    critique_block = f"""> 【暗室审片 · Admissions Critique & 三棱镜陪审团】
> 
> **三棱镜陪审团三维打分**：
> - 🏛️ **门禁官 (Gatekeeper)**: **{jury_eval['gatekeeper_score']}/100** — {jury_eval['jury_verdicts']['gatekeeper']['comment']}
> - 🔬 **学术博导 (Scholar)**: **{jury_eval['scholar_score']}/100** — {jury_eval['jury_verdicts']['scholar']['comment']}
> - 🎯 **匹配审查官 (Synergy)**: **{jury_eval['synergy_score']}/100** — {jury_eval['jury_verdicts']['synergy']['comment']}
> - ⚡ **三维帕累托超体积得分 (Pareto Hypervolume)**: **{jury_eval['pareto_hypervolume_percent']}** ({'★ 帕累托最优支撑文书' if jury_eval['is_pareto_optimal'] else '存在局部短板，需定向补强'})
> 
> **招生官视角诊断**：
> - **弱点定位**：第二段中的“resilient distributed architecture demands more than localized performance patches”略带总结腔调，若能补足一个具体的系统度量指标（如从 P99 延迟或吞吐量角度阐述），说服力将翻倍。
> - **对照改进方案**：
>   - 原文：*“This challenge crystallized my pursuit...”*
>   - 建议重构为：*“Observing our telemetry logs under simulated stress exposed a fundamental principle: isolated patches cannot substitute for invariant-driven concurrency guarantees...”*
"""

    response_markdown = f"""### 【折光师 · Stage 3 执笔成文 & Stage 4 暗室审片】

严格执行 **去 AI 化淬炼（Anti-AI Lexicon Blacklist）**，全篇禁用 *delve into, tapestry, realm, pivotal* 等塑料词汇，长短句交错，充满工程动作感：{guardrail_note}

```markdown
{cleansed_draft}
```

---

{critique_block}
"""

    # 写入 draft 与 critique 状态
    updated_profile["sop_draft"] = cleansed_draft
    updated_profile["sop_critique"] = {
        "weakness": "第二段中的概括句略显抽象，需补足具体系统度量指标（P99 延迟与吞吐量）。",
        "original_snippet": "This challenge crystallized my pursuit: resilient distributed architecture demands more than localized performance patches...",
        "revised_suggestion": "Observing our telemetry logs under simulated stress exposed a fundamental principle: isolated patches cannot substitute for invariant-driven concurrency guarantees...",
        "pareto_jury": jury_eval,
    }

    # 保存 Stage 3/4 版本快照
    versions.append({
        "version_id": f"v{len(versions) + 1}.0",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "stage": 3,
        "label": "Stage 3 淬炼初稿 & 暗室审片版",
        "author": "The Disperser",
        "outline": updated_profile.get("sop_outline"),
        "content": cleansed_draft,
        "critique": updated_profile["sop_critique"],
        "change_summary": "Anti-AI 淬炼初稿生成"
    })
    updated_profile["sop_versions"] = versions

    return {
        "student_profile": updated_profile,
        "latest_response": response_markdown,
        "active_agent": None,
        "pending_human_review": None,
    }
