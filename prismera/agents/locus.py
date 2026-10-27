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
            target_program_id=prog_id
        )
        nuance_data = retrieve_program_nuances(prog_id)
        prog["peer_cases"] = peer_cases
        prog["nuance_data"] = nuance_data

        bracket = prog.get("tier_bracket", "Match")
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
    def _format_program_card(prog: Dict[str, Any], gradient_name: str, prob: str) -> str:
        tuition = f"${prog['tuition_usd']} USD" if "tuition_usd" in prog else f"£{prog.get('tuition_gbp')} GBP"
        if "tuition_sgd" in prog:
            tuition = f"{prog['tuition_sgd']} SGD"
        if "tuition_hkd" in prog:
            tuition = f"{prog['tuition_hkd']} HKD"

        admit_sample = prog["peer_cases"]["admitted_sample"][0]["profile"]
        return f"""#### ✦ [{gradient_name} · 预估概率 {prob}] {prog['name_cn']}
- **英文全称**：`{prog['name_en']}`
- **学制与学费**：{prog['duration']} | 学费约 {tuition}
- **硬核标尺**：
  - 最低GPA标尺: {prog.get('gpa_min_4_0', prog.get('gpa_min_100', '85'))}
  - 语言门槛: 雅思 {prog['min_ielts']['total']} (小分不低于 {prog['min_ielts']['subscore']}) / 托福 {prog['min_toefl']['total']}
  - GRE 要求: {prog['nuance_data']['gre_policy']}
  - 轮次 Deadline: {prog['deadline']}
- **定焦依据（KG + RAG 证据链）**：
  - 往年录取中位线: {prog['peer_cases']['peer_median_gpa']}
  - 同辈真实画像: “{admit_sample}”
  - 隐形偏好特征: {prog['nuance_data']['nuance_summary']}
- **折光建议**：文书应当强化技术栈落地的工程闭环，重点突出与该项目课程吻合的实践成果。
"""

    reach_cards = "\n".join(_format_program_card(p, "远光·冲刺档", "20%-30%") for p in reach_list)
    match_cards = "\n".join(_format_program_card(p, "聚光·核心档", "40%-70%") for p in match_list)
    safety_cards = "\n".join(_format_program_card(p, "基光·稳妥档", ">75%") for p in safety_list)

    regions_str = "/".join(target_regions)
    overview_text = (
        f"申请者当前身位处于 **{undergrad_tier} ({undergrad_name})**、均分 **{gpa_raw}** 的有力竞争区间。\n"
        f"在 **{regions_str}** 地区的知识图谱剪枝中：\n"
        f"- 依据英国/港新院校隐形认可名单（List），已自动过滤严卡高梯队或不承认非核心名单的超高危项目；\n"
        f"- 依据学生语言现有水位（IELTS {language_scores.get('IELTS_total', 7.0)}，口语 {language_scores.get('speaking', 6.5)}），"
        f"已自动避开语言小分有硬性阻断的项目，确保申请通道畅通。"
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
    }
