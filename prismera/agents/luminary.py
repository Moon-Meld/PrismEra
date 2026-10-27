"""prism_core: The Luminary (司光者) - Central orchestrator and router."""

from __future__ import annotations
import json
import os
import re
from typing import Dict, Any, Optional

from prismera.state import PrismEraState, LuminaryDecision, StudentSpectrumProfile
from prismera.prompts.luminary import LUMINARY_SYSTEM_PROMPT


def _extract_student_attributes(text: str, current_profile: StudentSpectrumProfile) -> Dict[str, Any]:
    """Helper to heuristically extract applicant state updates from user input."""
    updates: Dict[str, Any] = {}
    
    # Undergrad tier / name
    if "985" in text:
        updates["undergrad_tier"] = "985"
    elif "211" in text:
        updates["undergrad_tier"] = "211"
    elif "双非" in text:
        updates["undergrad_tier"] = "双非一本"
    elif "海本" in text or "美本" in text or "英本" in text:
        updates["undergrad_tier"] = "海本"

    for school in ["清华", "北大", "浙江大学", "浙大", "复旦", "上海交大", "上交", "南京大学", "南大", "华中科技大学", "华科", "武汉大学", "武大", "哈工大", "北京航空航天大学", "北航", "同济大学", "同济", "西安交通大学", "西交", "东南大学", "中南大学", "中山大学", "电子科技大学", "成电", "北京邮电大学", "北邮", "西安电子科技大学", "西电"]:
        if school in text:
            updates["undergrad_name"] = school
            if "undergrad_tier" not in updates and not current_profile.get("undergrad_tier"):
                updates["undergrad_tier"] = "985" if school not in ["北邮", "西电"] else "211"
            break

    # Major
    for m in ["计算机", "软件工程", "计科", "cs", "computer science"]:
        if m in text.lower():
            updates["major"] = "计算机科学与技术 (CS)"
            break
    for m in ["数据科学", "ds", "data science"]:
        if m in text.lower():
            updates["major"] = "数据科学 (DS)"
            break
    for m in ["商业分析", "ba", "business analytics"]:
        if m in text.lower():
            updates["major"] = "商业分析 (BA)"
            break

    # GPA
    gpa_match = re.search(r"(\d{2}(?:\.\d+)?)\s*(?:分|/100|均分)", text)
    if gpa_match:
        updates["gpa_raw"] = f"{gpa_match.group(1)}/100"
    else:
        gpa_4_match = re.search(r"([34]\.\d{1,2})\s*(?:/4\.0|gpa)", text, re.IGNORECASE)
        if gpa_4_match:
            updates["gpa_raw"] = f"{gpa_4_match.group(1)}/4.0"

    # Language scores
    ielts_match = re.search(r"雅思\s*([678](?:\.[05])?)", text)
    if ielts_match:
        lang_dict = dict(current_profile.get("language_scores") or {})
        lang_dict["IELTS_total"] = float(ielts_match.group(1))
        # check subscores
        sub_match = re.search(r"口语\s*([5678](?:\.[05])?)", text)
        if sub_match:
            lang_dict["speaking"] = float(sub_match.group(1))
        updates["language_scores"] = lang_dict

    toefl_match = re.search(r"托福\s*(\d{2,3})", text)
    if toefl_match:
        lang_dict = dict(current_profile.get("language_scores") or {})
        lang_dict["TOEFL_total"] = float(toefl_match.group(1))
        sub_match = re.search(r"口语\s*(\d{1,2})", text)
        if sub_match:
            lang_dict["speaking"] = float(sub_match.group(1))
        updates["language_scores"] = lang_dict

    # Target regions
    regions = []
    if any(k in text for k in ["美国", "美研", "US", "USA"]):
        regions.append("US")
    if any(k in text for k in ["英国", "英研", "UK"]):
        regions.append("UK")
    if any(k in text for k in ["香港", "港校", "HK"]):
        regions.append("HK")
    if any(k in text for k in ["新加坡", "新二", "SG"]):
        regions.append("SG")
    if regions:
        current_regions = set(current_profile.get("target_regions") or [])
        current_regions.update(regions)
        updates["target_regions"] = list(current_regions)

    # Target majors
    target_m = []
    if any(k in text.lower() for k in ["cs", "计算机", "转码", "软件工程"]):
        target_m.append("CS")
    if any(k in text.lower() for k in ["ds", "数据科学"]):
        target_m.append("DS")
    if any(k in text.lower() for k in ["ba", "商业分析"]):
        target_m.append("BA")
    if target_m:
        current_m = set(current_profile.get("target_majors") or [])
        current_m.update(target_m)
        updates["target_majors"] = list(current_m)

    return updates


def luminary_node(state: PrismEraState) -> Dict[str, Any]:
    """司光者 (prism_core) 中枢执行节点。

    执行意图解析、四维基准指标前置校准、状态抽取与下游委派。
    """
    messages = state.get("messages", [])
    profile = state.get("student_profile", {})
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # 1. 抽取最新背景更新
    updates = _extract_student_attributes(last_user_msg, profile)
    merged_profile: StudentSpectrumProfile = dict(profile) # type: ignore
    for k, v in updates.items():
        merged_profile[k] = v # type: ignore

    user_query = last_user_msg.lower()

    # 2. 检查意图与四维基准参数
    # 消除否定句与完成态干扰（例如“定校很有底了”、“先不选校”）
    locus_keywords = ["选校", "定位", "定校", "定焦", "能申", "录取概率", "冲刺", "择校", "保底", "list"]
    is_asking_locus = any(kw in user_query for kw in locus_keywords)
    if any(neg in user_query for neg in ["定校很有底", "选校很有底", "先不定校", "不用选校", "已经定校"]):
        is_asking_locus = False

    is_asking_facet = any(kw in user_query for kw in ["切面", "成绩单", "gpa", "换算", "背景提升", "诊断", "先修课", "补课", "跨考", "暗区"])
    is_asking_disperser = any(kw in user_query for kw in ["折光", "文书", "sop", "ps", "个人陈述", "简历", "cv", "故事", "润色", "写作", "大纲"])
    is_asking_resonator = any(kw in user_query for kw in ["共鸣", "套磁", "导师", "教授", "论文", "phd", "博士", "科研", "邮件", "rp", "cold email"])

    # 检查状态机与上下文延续：
    # 场景 A: 上一轮司光者因缺少四项硬指标发起追问，本轮用户补全了数据 -> 自动激活定焦师
    prev_decision = state.get("routing_decision")
    has_tier = bool(merged_profile.get("undergrad_tier") or merged_profile.get("undergrad_name"))
    has_gpa = bool(merged_profile.get("gpa_raw"))
    has_major = bool(merged_profile.get("major"))
    has_target = bool(merged_profile.get("target_regions") and merged_profile.get("target_majors"))
    all_baseline_ready = has_tier and has_gpa and has_major and has_target

    if prev_decision == "ASK_FOR_CLARIFICATION" and all_baseline_ready and not (is_asking_facet or is_asking_disperser or is_asking_resonator):
        is_asking_locus = True

    # 场景 B: 正在进行折光师文书共创流程（上一轮 assistant 是折光师，或回答了细节）
    last_assistant_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            last_assistant_msg = msg.get("content", "")
            break

    is_continuing_sop = (
        ("折光师" in last_assistant_msg or "SOP" in last_assistant_msg or profile.get("sop_stage", 1) in [1, 2, 3])
        and not (is_asking_locus or is_asking_facet or is_asking_resonator)
        and (len(last_user_msg) > 30 or "确认" in user_query or "大纲" in user_query)
    )
    if is_continuing_sop:
        is_asking_disperser = True

    # 调度决策优先级判断
    if is_asking_facet:
        thought = "用户提出背景评估或课程比对诉求，委派切面师 (prism_facet) 测定优势切面与结构性暗区。"
        decision = LuminaryDecision(
            luminary_thought=thought,
            state_updates=updates,
            routing_decision="DELEGATE_TO_AGENT",
            target_agent_id="prism_facet",
            task_briefing="对学生成绩单及先修课进行图谱诊断，输出高光切面、暗区及打磨路线图。",
            message_to_user=None
        )

    elif is_asking_locus:
        missing_fields = []
        if not has_tier:
            missing_fields.append("本科院校（名称或层级，如 985/211/双非/海本）")
        if not has_gpa:
            missing_fields.append("当前均分或GPA（如 86/100 或 3.6/4.0）")
        if not has_major:
            missing_fields.append("当前本科所学专业")
        if not has_target:
            missing_fields.append("目标申请地区（美/英/港/新）与期望专业方向（如 CS/DS/BA）")

        if missing_fields:
            # 严格拦截：严禁直接路由给 prism_locus
            thought = f"用户请求选校定位，但核心硬指标缺失: {', '.join(missing_fields)}。遵循调度铁律第一条，执行前置校准拦截。"
            message = (
                "为了在万千学府中为你锁定不失真的落点焦距，定焦师（The Locus）需要几组核心基准参数进行硬核剪枝。\n\n"
                "请告诉我：\n" +
                "\n".join(f"{i+1}. 你的{field}" for i, field in enumerate(missing_fields[:3])) +
                "\n\n只需轻点回复，光学阵列便会立刻为你校准全球学府坐标。"
            )
            decision = LuminaryDecision(
                luminary_thought=thought,
                state_updates=updates,
                routing_decision="ASK_FOR_CLARIFICATION",
                target_agent_id=None,
                task_briefing=None,
                message_to_user=message
            )
        else:
            thought = "四项基准硬指标均已校准完备，正式委派定焦师 (prism_locus) 调用图谱与案例库定焦。"
            decision = LuminaryDecision(
                luminary_thought=thought,
                state_updates=updates,
                routing_decision="DELEGATE_TO_AGENT",
                target_agent_id="prism_locus",
                task_briefing="请依托全球留学知识图谱与同辈案例库，执行三步定焦并输出三维光谱定档矩阵。",
                message_to_user=None
            )

    elif is_asking_facet:
        thought = "用户提出背景评估或课程比对诉求，委派切面师 (prism_facet) 测定优势切面与结构性暗区。"
        decision = LuminaryDecision(
            luminary_thought=thought,
            state_updates=updates,
            routing_decision="DELEGATE_TO_AGENT",
            target_agent_id="prism_facet",
            task_briefing="对学生成绩单及先修课进行图谱诊断，输出高光切面、暗区及打磨路线图。",
            message_to_user=None
        )

    elif is_asking_disperser:
        thought = "用户进入文书共创阶段，委派折光师 (prism_disperser) 启动四阶状态机深度挖掘独家叙事。"
        decision = LuminaryDecision(
            luminary_thought=thought,
            state_updates=updates,
            routing_decision="DELEGATE_TO_AGENT",
            target_agent_id="prism_disperser",
            task_briefing="启动 Stage 1 苏格拉底访谈，提出具有穿透力的转折点与技术细节追问，严禁直接生成完整初稿。",
            message_to_user=None
        )

    elif is_asking_resonator:
        thought = "用户咨询学术套磁与导师联系，委派共鸣者 (prism_resonator) 检索论文瓶颈与招生动态。"
        decision = LuminaryDecision(
            luminary_thought=thought,
            state_updates=updates,
            routing_decision="DELEGATE_TO_AGENT",
            target_agent_id="prism_resonator",
            task_briefing="寻找导师论文与学生过往经历的学术共振频率，打造 220 词高信噪比套磁信。",
            message_to_user=None
        )

    else:
        # 通用对话或首屏引导
        thought = "用户尚未提出特定单向需求，司光者以温和智性语调进行承接，指引光学阵列的职能。"
        message = (
            "我是 **PrismEra（棱镜纪）** 的中枢主控——**【司光者 · The Luminary】**。\n\n"
            "整座光学阵列已为你校准就绪：\n"
            "- 想要诊断成绩单切面与先修课？唤起 **【切面师】**；\n"
            "- 想要依托知识图谱硬核定校？告诉我们基准指标，**【定焦师】** 为你精确投射；\n"
            "- 想要雕琢文书独家叙事？**【折光师】** 与你开启苏格拉底式故事挖掘；\n"
            "- 想要与海外顶尖学者共振？**【共鸣者】** 为你检索最新文献并定制高回复率邮件。\n\n"
            "告诉我你目前的学术背景或正在思索的问题，我们即刻启程。"
        )
        decision = LuminaryDecision(
            luminary_thought=thought,
            state_updates=updates,
            routing_decision="DIRECT_ANSWER",
            target_agent_id=None,
            task_briefing=None,
            message_to_user=message
        )

    return {
        "student_profile": merged_profile,
        "active_agent": decision.target_agent_id,
        "routing_decision": decision.routing_decision,
        "luminary_thought": decision.luminary_thought,
        "task_briefing": decision.task_briefing,
        "latest_response": decision.message_to_user,
    }
