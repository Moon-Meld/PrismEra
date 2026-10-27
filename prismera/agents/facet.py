"""prism_facet: The Facet (切面师) - Background diagnostic and prerequisite graph alignment."""

from __future__ import annotations
from typing import Dict, Any, List

from prismera.state import PrismEraState
from prismera.tools.gpa_tools import calculate_gpa_metrics
from prismera.tools.prerequisite_tools import check_prerequisite_graph


def facet_node(state: PrismEraState) -> Dict[str, Any]:
    """切面师 (prism_facet) 执行节点。

    调用确定性 GPA 计算与先修课图谱工具，输出三段式诊断报告。
    """
    profile = state.get("student_profile", {})
    gpa_raw = profile.get("gpa_raw") or "86.5/100"
    target_major = (profile.get("target_majors") or ["CS"])[0]

    # Mock completed courses from context or typical transcript
    sample_completed = [
        "高等数学 (Calculus)",
        "线性代数 (Linear Algebra)",
        "概率论与数理统计 (Probability)",
        "大学物理 (University Physics)",
        "面向对象程序设计 (Python / Java)",
        "数据结构与算法 (Data Structures)"
    ]

    # 1. 优先调用确定性工具
    gpa_res = calculate_gpa_metrics(gpa_raw)
    prereq_res = check_prerequisite_graph(target_major, sample_completed)

    # 2. 构建符合 Prompt 规范的三段式输出
    align_rows = []
    for item in prereq_res["alignment_table"]:
        align_rows.append(
            f"| {item['target_module']} | {item['completed_match']} | **{item['status']}** | {item['remedy_suggestion']} |"
        )
    align_table_str = "\n".join(align_rows)

    strengths_str = "\n".join(f"- {s}" for s in gpa_res.get("key_highlights", []))
    blindspots_str = "\n".join(f"- {b}" for b in gpa_res.get("structural_blindspots", []))

    response_markdown = f"""### 1. 原石切面诊断（Spectrum Diagnosis）

- **高光切面（Core Strengths）**：
  - 测定标准 4.0 GPA 为 **{gpa_res['overall_gpa_4_0']}**，经 WES 算法评估折算约为 **{gpa_res['wes_gpa_estimated']}**。
  - 专业核心硬课 GPA 表现强劲（**{gpa_res['core_subject_gpa']}**），整体呈现 **{gpa_res['trend_curve']}**。
{strengths_str}

- **结构性暗区（Structural Blindspots）**：
{blindspots_str}
  - 缺乏顶会/高水平学术论文或国家级竞赛核心获奖证明。

---

### 2. 先修课图谱对齐表（Prerequisite Alignment - 目标方向: {target_major}）

| 目标方向要求模块 | 学生已修对应课程 | 匹配状态 (完备/薄弱/缺失) | 补救方案建议 |
| :--- | :--- | :--- | :--- |
{align_table_str}

> 💡 **切面师深度提示**：{prereq_res['critical_advice']}

---

### 3. 倒计时打磨路线图（Refining Roadmap）

- **当下 1 个月内 (Immediate Priority)**：
  1. 锁定语言成绩攻坚，尤其针对口语小分（确保迈过英国/美研 6.5 或 24 分隐形卡线）；
  2. 梳理本校大四选修目录，如有先修课缺失模块，优先选择有官方学分的先修课。
- **1 - 3 个月 (Enhancement Window)**：
  1. 针对核心经历进行“高信噪比”文档重构，提炼出可被量化的工程指标；
  2. 若跨专业申 CS，建议完成 Coursera/edX 上知名高校的有学分专项课程（如 UCSD 数据结构专项）。
- **申请递交前 (Final Polish)**：
  1. 将全部代码与技术报告整理至 GitHub 干净仓库，附上清晰的 README 与演示链接；
  2. 移交【折光师】开启苏格拉底式故事挖掘，雕琢文书高光。
"""

    return {
        "latest_response": response_markdown,
        "active_agent": None,
    }
