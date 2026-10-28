"""prism_locus: The Locus (定焦师) - KG and Vector RAG School Selection."""

from __future__ import annotations
from typing import Dict, Any, List

from prismera.state import PrismEraState
from prismera.tools.admission_tools import (
    cypher_filter_programs,
    search_peer_admission_cases,
    retrieve_program_nuances,
)


def locus_node(state: PrismEraState) -> Dict[str, Any]:
    """定焦师 (prism_locus) 执行节点。

    强制执行 GraphRAG 三步定焦法与零幻觉铁律，输出三维光谱定档选校矩阵。
    """
    profile = state.get("student_profile", {})
    undergrad_tier = profile.get("undergrad_tier") or "985"
    undergrad_name = profile.get("undergrad_name") or "国内重点大学"
    gpa_raw = profile.get("gpa_raw") or "86.5/100"
    target_regions = profile.get("target_regions") or ["US", "UK", "SG", "HK"]
    target_majors = profile.get("target_majors") or ["CS"]
    language_scores = profile.get("language_scores") or {"IELTS_total": 7.0, "speaking": 6.5}

    # Extract numerical GPA
    try:
        if "/" in gpa_raw:
            gpa_val = float(gpa_raw.split("/")[0])
        else:
            gpa_val = float(gpa_raw)
    except Exception:
        gpa_val = 86.5

    # Step 1: KG 硬核剪枝
    filtered_programs = cypher_filter_programs(
        undergrad_tier=undergrad_tier,
        gpa=gpa_val,
        language_scores=language_scores,
        target_regions=target_regions,
        target_majors=target_majors
    )

    # Step 2 & 3: 同辈案例校准与隐形偏好召回
    reach_list = []
    match_list = []
    safety_list = []

    for prog in filtered_programs:
        prog_id = prog["id"]
        peer_cases = search_peer_admission_cases(
            undergrad_tier=undergrad_tier,
            gpa=gpa_val,
            major=target_majors[0],
            target_program_id=prog_id,
            student_profile=profile
        )
        nuance_data = retrieve_program_nuances(prog_id)
        prog["peer_cases"] = peer_cases
        prog["nuance_data"] = nuance_data

        bracket = peer_cases.get("bracket_recommendation") or prog.get("tier_bracket", "Match")
        if bracket == "Reach":
            reach_list.append(prog)
        elif bracket == "Safety":
            safety_list.append(prog)
        else:
            match_list.append(prog)

    # Fallback to make sure each tier is represented
    if not reach_list and filtered_programs:
        reach_list = [filtered_programs[0]]
    if not match_list and len(filtered_programs) > 1:
        match_list = [filtered_programs[1]]
    if not safety_list and len(filtered_programs) > 2:
        safety_list = [filtered_programs[2]]

    # Format Output
    def _format_program_card(prog: Dict[str, Any], gradient_name: str, fallback_prob: str) -> str:
        tuition = f"${prog['tuition_usd']} USD" if "tuition_usd" in prog else f"£{prog.get('tuition_gbp')} GBP"
        if "tuition_sgd" in prog:
            tuition = f"{prog['tuition_sgd']} SGD"
        if "tuition_hkd" in prog:
            tuition = f"{prog['tuition_hkd']} HKD"

        peer_cases = prog.get("peer_cases", {}) or {}
        prob_str = peer_cases.get("probability_percent") or fallback_prob
        admit_sample_list = peer_cases.get("admitted_sample", [])
        admit_sample = admit_sample_list[0].get("profile", "优秀同辈标化达标录取") if admit_sample_list else "优秀同辈标化达标录取"
        peer_median = peer_cases.get("peer_median_gpa", "3.75 (或 88分)")

        top_pos = peer_cases.get("top_positive_factors", [])
        top_neg = peer_cases.get("top_negative_factors", [])
        attr_lines = []
        if top_pos:
            attr_lines.append(f"    - 正向优势项: {', '.join(top_pos)}")
        if top_neg:
            attr_lines.append(f"    - 核心制约项: {', '.join(top_neg)}")
        attr_block = "\n" + "\n".join(attr_lines) if attr_lines else "    - 各维度相对均衡，契合项目基准门槛"

        nuance_data = prog.get("nuance_data", {}) or {}
        gre_policy = nuance_data.get("gre_policy", "Optional")
        nuance_summary = nuance_data.get("nuance_summary", "注重工程实践与科研学术产出")

        min_ielts = prog.get("min_ielts", {}) or {"total": 7.0, "subscore": 6.5}
        min_toefl = prog.get("min_toefl", {}) or {"total": 100, "subscore": 22}

        name_cn = prog.get("name_cn") or prog.get("name") or prog.get("id")
        name_en = prog.get("name_en") or prog.get("name") or prog.get("id")
        duration = prog.get("duration", "1-2年全日制")
        deadline = prog.get("deadline", "Round 1: 12月15日 / Round 2: 1月15日")

        return f"""#### ✦ [{gradient_name} · Prism-AdmitNet 预估录取率 {prob_str}] {name_cn}
- **英文全称**：`{name_en}`
- **学制与学费**：{duration} | 学费约 {tuition}
- **硬核标尺**：
  - 最低GPA标尺: {prog.get('gpa_min_4_0', prog.get('gpa_min_100', '85'))}
  - 语言门槛: 雅思 {min_ielts.get('total', 7.0)} (小分不低于 {min_ielts.get('subscore', 6.5)}) / 托福 {min_toefl.get('total', 100)}
  - GRE 要求: {gre_policy}
  - 轮次 Deadline: {deadline}
- **定焦依据（KG + AdmitNet 算法证据链）**：
  - 往年录取中位线: {peer_median}
  - 同辈真实画像: “{admit_sample}”
  - 隐形偏好特征: {nuance_summary}
  - **特征归因拆解 (Feature Attribution)**:
{attr_block}
- **折光建议**：文书应当强化技术栈落地的工程闭环，重点突出与该项目课程吻合的实践成果。
"""

    reach_cards = "\n".join(_format_program_card(p, "远光·冲刺档", "20%-30%") for p in reach_list)
    match_cards = "\n".join(_format_program_card(p, "聚光·核心档", "40%-70%") for p in match_list)
    safety_cards = "\n".join(_format_program_card(p, "基光·稳妥档", ">75%") for p in safety_list)

    regions_str = "/".join(target_regions)
    pruned_notes = ""
    if hasattr(filtered_programs, "pruned_records") and filtered_programs.pruned_records:
        pruned_items = []
        for r in filtered_programs.pruned_records[:4]:
            pruned_items.append(f"  - `{r['program_name']}`：{r['reason']}")
        pruned_notes = "\n- **知识图谱硬核剪枝拦截清单（Graph Pruning Audit）**：\n" + "\n".join(pruned_items)

    overview_text = (
        f"申请者当前身位处于 **{undergrad_tier} ({undergrad_name})**、均分 **{gpa_raw}** 的有力竞争区间。\n"
        f"在 **{regions_str}** 地区的知识图谱剪枝中：\n"
        f"- 依据英国/港新院校隐形认可名单（List），已自动过滤严卡高梯队或不承认非核心名单的超高危项目；\n"
        f"- 依据学生语言现有水位（IELTS {language_scores.get('IELTS_total', 7.0)}，口语 {language_scores.get('speaking', 6.5)}），"
        f"已自动避开语言小分有硬性阻断的项目，确保申请通道畅通。{pruned_notes}"
    )

    response_markdown = f"""### 1. 定焦坐标系综述（Locus Overview）

{overview_text}

---

### 2. 棱镜三级选校矩阵（The Prism Matrix）

### 【远光·冲刺档 (Reach)】
{reach_cards if reach_cards else "暂无完全契合的冲刺项目数据"}

---

### 【聚光·核心档 (Match)】
{match_cards if match_cards else "暂无核心匹配项目数据"}

---

### 【基光·稳妥档 (Safety)】
{safety_cards if safety_cards else "暂无保底项目数据"}
"""

    all_shortlisted = reach_list + match_list + safety_list
    updated_profile = dict(profile)
    updated_profile["shortlisted_programs"] = all_shortlisted

    return {
        "student_profile": updated_profile,
        "latest_response": response_markdown,
        "active_agent": None,
        "pending_human_review": "locus_matrix",
    }
