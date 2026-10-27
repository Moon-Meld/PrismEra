"""Prerequisite knowledge graph comparison tool for prism_facet.

Queries GraphStore for prerequisite course nodes and requirement edges,
performing topological course alignment against student transcripts.
"""

from __future__ import annotations
from typing import Dict, Any, List

from prismera.db.graph_store import get_graph_store

# Built-in fallback ontology in case GraphStore is uninitialized
DEFAULT_PREREQUISITE_KG = {
    "CS": [
        {
            "module": "离散数学与逻辑 (Discrete Mathematics)",
            "aliases": ["离散数学", "discrete math", "discrete mathematics"],
            "importance": "Mandatory"
        },
        {
            "module": "数据结构与算法 (Data Structures & Algorithms)",
            "aliases": ["数据结构", "算法", "data structures", "algorithms"],
            "importance": "Mandatory"
        },
        {
            "module": "计算机系统/体系结构 (Computer Systems / Architecture)",
            "aliases": ["计算机组成原理", "操作系统", "computer architecture", "operating systems", "systems"],
            "importance": "Mandatory"
        },
        {
            "module": "高等微积分与线性代数 (Calculus & Linear Algebra)",
            "aliases": ["微积分", "高等数学", "线性代数", "calculus", "linear algebra"],
            "importance": "Mandatory"
        },
        {
            "module": "概率论与数理统计 (Probability & Statistics)",
            "aliases": ["概率论", "数理统计", "probability", "statistics"],
            "importance": "High"
        }
    ],
    "DS": [
        {
            "module": "高级程序设计 (Python / C++ Programming)",
            "aliases": ["程序设计", "python", "c++", "object-oriented programming"],
            "importance": "Mandatory"
        },
        {
            "module": "多元微积分与线性代数 (Multivariable Calculus & Linear Algebra)",
            "aliases": ["微积分", "高等数学", "线性代数", "calculus", "linear algebra"],
            "importance": "Mandatory"
        },
        {
            "module": "概率论与数理统计 (Probability & Statistics)",
            "aliases": ["概率论", "数理统计", "probability", "statistics"],
            "importance": "Mandatory"
        },
        {
            "module": "数据结构与数据管理 (Data Structures & Databases)",
            "aliases": ["数据结构", "数据库", "data structures", "sql", "database systems"],
            "importance": "High"
        }
    ],
    "BA": [
        {
            "module": "微积分与线性代数 (Calculus & Linear Algebra)",
            "aliases": ["微积分", "高等数学", "线性代数", "calculus"],
            "importance": "Mandatory"
        },
        {
            "module": "商业统计或计量经济学 (Statistics / Econometrics)",
            "aliases": ["统计学", "应用统计", "计量经济学", "econometrics", "business statistics"],
            "importance": "Mandatory"
        },
        {
            "module": "编程基础 (Python / R / SQL)",
            "aliases": ["python", "r", "sql", "数据库", "编程"],
            "importance": "High"
        }
    ],
    "FIN": [
        {
            "module": "微观与宏观经济学基础 (Micro & Macroeconomics)",
            "aliases": ["微观经济学", "宏观经济学", "经济学", "microeconomics", "macroeconomics"],
            "importance": "Mandatory"
        },
        {
            "module": "财务会计与公司金融 (Accounting & Finance)",
            "aliases": ["会计学", "公司金融", "财务管理", "accounting", "finance"],
            "importance": "Mandatory"
        },
        {
            "module": "微积分与线性代数 (Calculus & Linear Algebra)",
            "aliases": ["微积分", "高等数学", "线性代数", "calculus"],
            "importance": "Mandatory"
        },
        {
            "module": "计量经济学与统计 (Econometrics & Statistics)",
            "aliases": ["商业统计", "计量经济学", "统计学", "econometrics"],
            "importance": "Mandatory"
        }
    ]
}


def check_prerequisite_graph(
    target_major: str,
    completed_courses: List[str]
) -> Dict[str, Any]:
    """Check completed courses against the target program's prerequisite subgraph.

    Args:
        target_major: Target field abbreviation, e.g. 'CS', 'DS', 'BA', 'FIN'.
        completed_courses: List of courses completed or in progress.

    Returns:
        Structured prerequisite alignment table and remediation recommendations.
    """
    key = target_major.upper()

    # Attempt to load from GraphStore
    gs = get_graph_store()
    graph_prereqs = gs.get_prerequisites_for_major(key)

    requirements = []
    if graph_prereqs:
        for p in graph_prereqs:
            importance = "Mandatory" if p.get("level") == "mandatory" else "High"
            requirements.append({
                "module": f"{p['name_cn']} ({p['name_en']})",
                "aliases": p.get("aliases", []),
                "importance": importance
            })
    else:
        req_key = key if key in DEFAULT_PREREQUISITE_KG else "CS"
        requirements = DEFAULT_PREREQUISITE_KG[req_key]

    alignment_table: List[Dict[str, str]] = []
    has_missing = False

    for req in requirements:
        mod_name = req["module"]
        aliases = req["aliases"]

        matched = []
        for c in completed_courses:
            c_low = c.lower()
            if any(alias in c_low for alias in aliases):
                matched.append(c)

        if matched:
            status = "完备"
            remedy = "无需补课，可考虑在文书中强调其高阶应用"
            matched_str = "、".join(matched)
        else:
            if req["importance"] == "Mandatory":
                status = "缺失 (关键)"
                remedy = "大四上学期本校选修 / 参加 Coursera (UIUC/JHU) 有学分认证专项 / 美本暑校"
                has_missing = True
            else:
                status = "薄弱"
                remedy = "通过在线网课补充或在科研/实习项目中展现相关代码产出"
            matched_str = "暂无匹配"

        alignment_table.append({
            "target_module": mod_name,
            "completed_match": matched_str,
            "status": status,
            "remedy_suggestion": remedy
        })

    return {
        "target_major": key,
        "is_fully_aligned": not has_missing,
        "alignment_table": alignment_table,
        "critical_advice": (
            "跨专业先修课预警：存在核心硬门槛先修课缺失，建议优先锁定对转专业友好的项目（如 UPenn MCIT、NEU Align CS），并在递交网申前补充官方认证学分课。"
            if has_missing else
            "先修课图谱完备：学生已修读全部核心先修课程，具备直接冲刺顶尖直系 CS/DS 项目的硬核背景！"
        )
    }
