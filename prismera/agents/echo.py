"""prism_echo: The Echo (回音壁) - Full-fidelity Mock Interview and Application Timeline Pilot."""

from __future__ import annotations
import re
from typing import Dict, Any, List, Optional

from prismera.state import PrismEraState
from prismera.tools.echo_tools import (
    retrieve_interview_question_bank,
    evaluate_interview_answer,
    generate_application_timeline,
)


def echo_node(state: PrismEraState) -> Dict[str, Any]:
    """回音壁 (prism_echo) 执行节点。

    核心职能：
    1. 全真靶向模拟面试 (Kira机面、校友行为面、导师学术面) 及多维三维评分与高分示范。
    2. 网申截止日期倒计时看板、推荐信 (RL) 阶梯式催交节律表与材料核查清单。
    """
    profile = state.get("student_profile", {})
    if "interview_records" not in profile or profile["interview_records"] is None:
        profile["interview_records"] = []
    if "application_timeline" not in profile or profile["application_timeline"] is None:
        profile["application_timeline"] = []

    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "").strip()
            break

    lower_query = last_user_msg.lower()

    # Intent Discrimination: Timeline vs. Interview
    timeline_keywords = ["时间轴", "timeline", "deadline", "截止", "倒计时", "推荐信", "催交", "材料清单", "网申清单", "清单", "护航日程"]
    is_asking_timeline = any(kw in lower_query for kw in timeline_keywords) and not any(kw in lower_query for kw in ["模拟面", "面经", "作答", "回答"])

    # -------------------------------------------------------------------------
    # BRANCH 1: 网申时间轴看板与材料/推荐信核查清单
    # -------------------------------------------------------------------------
    if is_asking_timeline:
        shortlisted = profile.get("shortlisted_programs") or []
        timeline_data = generate_application_timeline(shortlisted)
        profile["application_timeline"] = timeline_data

        prog_timeline = timeline_data[0]["items"]
        rl_milestones = timeline_data[1]["items"]
        materials = timeline_data[2]["items"]

        # Build Markdown
        programs_md = []
        for p in prog_timeline:
            programs_md.append(
                f"- **[{p['tier_bracket']} · 剩余 {p['days_remaining']} 天]** `{p['name_cn']}`\n"
                f"  - 英文全称: {p['name_en']}\n"
                f"  - 官方截点: **{p['deadline_raw']}** (紧迫度: {p['urgency']})\n"
                f"  - 推荐信预警目标: {p['rl_target_date']}"
            )

        rl_md = []
        for rl in rl_milestones:
            status_symbol = "✓ 已就绪" if rl["status"] == "completed" else "⏳ 推进中"
            actions = "\n".join(f"    - {act}" for act in rl["action_items"])
            rl_md.append(f"#### ✦ [{rl['stage']} · {rl['timeline_anchor']}] {rl['title']} ({status_symbol})\n{actions}")

        mat_md = []
        for cat in materials:
            item_lines = "\n".join(f"  - [{'✓' if it['status']=='ready' else '⏳'}] **{it['name']}** ({it['note']})" for it in cat["items"])
            mat_md.append(f"**{cat['category']}**:\n{item_lines}")

        response_markdown = f"""### 【回音壁 · 网申时间轴倒计时与材料护航看板】

根据你当前锁定的升学项目坐标与招生轮次，回音壁已为你校准并生成全局倒计时时间轴：

---

### 1. 项目截止日期（Deadline）矩阵与倒计时
{chr(10).join(programs_md)}

---

### 2. 推荐信（RL）四阶阶梯式催交节律表
{chr(10).join(rl_md)}

---

### 3. 网申必备材料核验清单 (Checklist)
{chr(10).join(mat_md)}

> 💡 **护航官提示**：
> 右侧画布 **Tab 4 [回音面试与网申日程]** 已同步更新可视看板！如需模拟目标院校面试，可随时向我发送：“开始 CMU MSIT-SE 的 Kira 模拟面试”。
"""
        return {
            "latest_response": response_markdown,
            "active_agent": "prism_echo",
            "student_profile": profile,
        }

    # -------------------------------------------------------------------------
    # BRANCH 2: 全真靶向模拟面试与三维作答复盘
    # -------------------------------------------------------------------------
    # Determine interview type
    interview_type = "kira_video"
    if any(k in lower_query for k in ["校友", "alumni", "行为面", "behavioral"]):
        interview_type = "alumni_behavioral"
    elif any(k in lower_query for k in ["导师", "教授", "学术面", "技术面", "professor", "technical"]):
        interview_type = "professor_technical"

    # Determine target program id
    target_program_id = "cmu_msit_se"
    if "uiuc" in lower_query:
        target_program_id = "uiuc_mcs"
    elif "ic" in lower_query or "imperial" in lower_query or "帝国理工" in lower_query:
        target_program_id = "ic_computing"
    elif profile.get("locked_target_program") and profile["locked_target_program"].get("id"):
        target_program_id = profile["locked_target_program"]["id"]
    elif profile.get("shortlisted_programs"):
        target_program_id = profile["shortlisted_programs"][0].get("id", "cmu_msit_se")

    # Fetch question bank
    question_pool = retrieve_interview_question_bank(target_program_id, interview_type)

    # Check if user is answering an ongoing question or asking to start
    records = profile.get("interview_records") or []
    has_pending_question = False
    pending_question: Optional[Dict[str, Any]] = None

    if records and records[-1].get("status") == "pending_answer":
        has_pending_question = True
        pending_question = records[-1]

    is_starting_interview = any(kw in lower_query for kw in [
        "开始", "发起", "出题", "第一题", "下一题", "换一题", "来一题", "题库", "练一下",
        "想练", "模拟一下", "模拟面试", "做个面试", "请出"
    ])
    is_answering = (has_pending_question and not is_starting_interview) or (
        not is_starting_interview and len(last_user_msg) >= 40 and not any(kw in lower_query for kw in ["请帮我", "请出", "请为我", "我想"])
    )

    if is_answering:
        # Perform Evaluation on user answer
        current_q = pending_question.get("question_data") if pending_question else question_pool[0]
        eval_result = evaluate_interview_answer(
            question_item=current_q,
            student_answer=last_user_msg,
            student_profile=profile,
            interview_type=interview_type
        )

        record_entry = {
            "record_id": f"rec_{len(records) + 1}",
            "program_id": target_program_id,
            "interview_type": interview_type,
            "status": "completed",
            "question_data": current_q,
            "evaluation": eval_result,
            "student_answer": last_user_msg,
        }

        if has_pending_question:
            records[-1] = record_entry
        else:
            records.append(record_entry)
        profile["interview_records"] = records

        scores = eval_result["scores"]
        star_breakdown = eval_result["star_breakdown"]
        feedback = eval_result["feedback"]

        response_markdown = f"""### 【回音壁 · 全真靶向模拟面试作答复盘】

你刚刚完成了一轮 **{current_q.get('type_label', '全真模拟面试')}** 的实战应答：
> **考核题目**：*{current_q.get('question')}*
> **题型归类**：{current_q.get('category')} | 限时建议: {current_q.get('response_time_seconds', 90)} 秒

---

### 1. 三维多维综合评分雷达
- 🎯 **【内容相关性 (Content Relevance)】**：`{scores['content_relevance']} / 100`
  - *复盘批注*：{' '.join(feedback['content_relevance'])}
- 🏛️ **【STAR结构完整度 (STAR Completeness)】**：`{scores['star_structure']} / 100`
  - *S (Situation)*: {'✓' if star_breakdown['Situation']['present'] else '✕'} {star_breakdown['Situation']['note']}
  - *T (Task)*: {'✓' if star_breakdown['Task']['present'] else '✕'} {star_breakdown['Task']['note']}
  - *A (Action)*: {'✓' if star_breakdown['Action']['present'] else '✕'} {star_breakdown['Action']['note']}
  - *R (Result)*: {'✓' if star_breakdown['Result']['present'] else '✕'} {star_breakdown['Result']['note']}
  - *复盘批注*：{feedback['star_structure']}
- 🗣️ **【语言地道度 (Linguistic Authenticity)】**：`{scores['linguistic_authenticity']} / 100`
  - *复盘批注*：{' '.join(feedback['linguistic_authenticity'])}
- 🏆 **综合判定指数**：`{scores['composite']} / 100` (达到优质申请者竞争力水位)

---

### 2. 高分示范回答 (Refined Sample Answer)
> **朗读时长预估**：约 {eval_result['sample_word_count']} 词 / {eval_result['estimated_speaking_seconds']} 秒（完美贴合 {current_q.get('response_time_seconds', 90)}s 限时标准）：

```text
{eval_result['refined_sample_answer']}
```

---

> 💡 **回音壁建议**：
> 这一段回答在右侧 **Tab 4 [回音面试与网申日程]** 已沉淀为永久复盘卡片。
> 回复 **“下一题”** 即可推进第二轮问答，或回复 **“生成时间轴”** 查看各院校网申进度。
"""
        return {
            "latest_response": response_markdown,
            "active_agent": "prism_echo",
            "student_profile": profile,
        }

    else:
        # User is initiating interview or requesting questions
        selected_question = question_pool[0]
        record_entry = {
            "record_id": f"rec_{len(records) + 1}",
            "program_id": target_program_id,
            "interview_type": interview_type,
            "status": "pending_answer",
            "question_data": selected_question,
            "evaluation": None,
            "student_answer": None,
        }
        records.append(record_entry)
        profile["interview_records"] = records

        rubric = selected_question.get("evaluation_rubric", {})
        prep_time = selected_question.get("prep_time_seconds", 45)
        resp_time = selected_question.get("response_time_seconds", 90)

        response_markdown = f"""### 【回音壁 · 全真模拟面试入场校准】

已为你调阅 **{selected_question.get('target_program_name', '目标项目')}** 的 **{selected_question.get('type_label')}** 真题库：

---

#### 🎙️ Question 01: [{selected_question.get('category')}]
> **"{selected_question.get('question')}"**
>
> *中文指引：{selected_question.get('question_cn', '')}*

- ⏱️ **录像倒计时规则**：
  - 准备时间：`{prep_time} 秒`（建议在草稿纸上速记 STAR 4 关键词）
  - 作答时间：`{resp_time} 秒`（建议语速 130-150 词/分钟）
- 🔍 **核心考核维度**：
  - **内容相关度**：{rubric.get('content_relevance', '结合真实技术经历')}
  - **STAR结构**：{rubric.get('star_structure', 'S-T-A-R 完整闭环')}
  - **语言纯正感**：{rubric.get('linguistic_authenticity', '杜绝 AI 假大空词汇')}

---

**请在下方直接输入你的拟作答内容（英文为佳，中文亦可）：**
我将即刻从【内容相关性】、【STAR结构完整度】、【语言地道度】三维为你打分并生成高分示范回答。
"""
        return {
            "latest_response": response_markdown,
            "active_agent": "prism_echo",
            "student_profile": profile,
        }
