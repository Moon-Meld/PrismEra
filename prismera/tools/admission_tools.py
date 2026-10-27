"""Admission Knowledge Graph and Vector RAG tools for prism_locus."""

from __future__ import annotations
from typing import Dict, Any, List, Optional


# Deterministic KG Program Database
PROGRAMS_KG = [
    {
        "id": "cmu_msit_se",
        "name_cn": "卡耐基梅隆大学 - 软件工程硕士 (MSIT-SE)",
        "name_en": "Carnegie Mellon University - MS in Information Technology - Software Engineering",
        "region": "US",
        "major_category": "CS",
        "duration": "1.5 年",
        "tuition_usd": 54000,
        "gpa_min_4_0": 3.6,
        "min_undergrad_tier": ["985", "211", "海本"],
        "min_ielts": {"total": 7.5, "subscore": 7.0},
        "min_toefl": {"total": 102, "subscore": 25},
        "gre_required": False,
        "deadline": "2027-01-15 (Final Round)",
        "tier_bracket": "Reach",
        "nuance": "极其看重系统级编程经历与高信噪比开源代码，偏好有一年左右高含金量工程实习的学生。"
    },
    {
        "id": "uiuc_mcs",
        "name_cn": "伊利诺伊大学香槟分校 - 计算机科学硕士 (MCS)",
        "name_en": "UIUC - Master of Computer Science",
        "region": "US",
        "major_category": "CS",
        "duration": "1.5 年",
        "tuition_usd": 42000,
        "gpa_min_4_0": 3.4,
        "min_undergrad_tier": ["985", "211", "双非一本", "海本"],
        "min_ielts": {"total": 7.0, "subscore": 6.5},
        "min_toefl": {"total": 100, "subscore": 24},
        "gre_required": False,
        "deadline": "2027-01-30",
        "tier_bracket": "Match",
        "nuance": "对双非顶尖学霸友好（GPA>=88），核心看算法与硬核专业课均分，就业导向明显。"
    },
    {
        "id": "usc_cs37",
        "name_cn": "南加州大学 - 计算机科学（计算机科学家培养计划 37学分）",
        "name_en": "USC - MS in Computer Science (Scientists and Engineers - 37 Units)",
        "region": "US",
        "major_category": "CS",
        "duration": "2 年",
        "tuition_usd": 58000,
        "gpa_min_4_0": 3.2,
        "min_undergrad_tier": ["985", "211", "双非一本", "海本"],
        "min_ielts": {"total": 6.5, "subscore": 6.0},
        "min_toefl": {"total": 90, "subscore": 20},
        "gre_required": False,
        "deadline": "2027-02-15",
        "tier_bracket": "Safety",
        "nuance": "跨专业/转码第一神项目，招生规模大，标化控（GPA和语言过线即大概率录取），容错率高。"
    },
    {
        "id": "ic_computing_msc",
        "name_cn": "帝国理工学院 - 计算机理学硕士",
        "name_en": "Imperial College London - MSc Computing Science (Specialist)",
        "region": "UK",
        "major_category": "CS",
        "duration": "1 年",
        "tuition_gbp": 39400,
        "gpa_min_100": 85.0,
        "min_undergrad_tier": ["985", "211"],  # 严卡内地List
        "min_ielts": {"total": 7.0, "subscore": 6.5},
        "min_toefl": {"total": 100, "subscore": 22},
        "gre_required": False,
        "deadline": "2027-03-01 (Rolling)",
        "tier_bracket": "Reach",
        "nuance": "严卡 211/985 院校名单，均分建议 88+，对纯双非直接系统秒拒，强烈看重数学推导能力与第一作者论文。"
    },
    {
        "id": "ucl_cs_msc",
        "name_cn": "伦敦大学学院 - 计算机科学理学硕士",
        "name_en": "UCL - MSc Computer Science",
        "region": "UK",
        "major_category": "CS",
        "duration": "1 年",
        "tuition_gbp": 35000,
        "gpa_min_100": 85.0,
        "min_undergrad_tier": ["985", "211", "双非一本", "海本"],
        "min_ielts": {"total": 7.0, "subscore": 6.5},
        "min_toefl": {"total": 100, "subscore": 24},
        "gre_required": False,
        "deadline": "2027-03-31",
        "tier_bracket": "Match",
        "nuance": "UCL Group A List 要求 85+，Group B 要求 90+。文书重合度检测严格，看重跨学科创新应用。"
    },
    {
        "id": "edinburgh_cs_msc",
        "name_cn": "爱丁堡大学 - 计算机科学硕士",
        "name_en": "University of Edinburgh - MSc Computer Science",
        "region": "UK",
        "major_category": "CS",
        "duration": "1 年",
        "tuition_gbp": 38500,
        "gpa_min_100": 82.0,
        "min_undergrad_tier": ["985", "211", "海本"],
        "min_ielts": {"total": 7.0, "subscore": 6.5},
        "min_toefl": {"total": 100, "subscore": 23},
        "gre_required": False,
        "deadline": "2026-12-10 (Round 1)",
        "tier_bracket": "Match",
        "nuance": "List 内 Band A/B 严格卡均分，且雅思口语单项严卡 6.5，小分不达标系统自动阻断。"
    },
    {
        "id": "nus_mcomp",
        "name_cn": "新加坡国立大学 - 计算硕士 (MComp)",
        "name_en": "National University of Singapore - Master of Computing",
        "region": "SG",
        "major_category": "CS",
        "duration": "1.5 年",
        "tuition_sgd": 56000,
        "gpa_min_100": 85.0,
        "min_undergrad_tier": ["985", "211", "海本"],
        "min_ielts": {"total": 6.5, "subscore": 6.0},
        "min_toefl": {"total": 90, "subscore": 22},
        "gre_required": False,
        "deadline": "2027-02-28",
        "tier_bracket": "Reach",
        "nuance": "亚洲顶级计算机殿堂，优先录取 985/211 顶尖梯队（87+）或海本一等学位，转专业需具备极强代码作品集。"
    },
    {
        "id": "hku_msc_cs",
        "name_cn": "香港大学 - 计算机科学理学硕士",
        "name_en": "The University of Hong Kong - MSc in Computer Science",
        "region": "HK",
        "major_category": "CS",
        "duration": "1 年",
        "tuition_hkd": 288000,
        "gpa_min_100": 83.0,
        "min_undergrad_tier": ["985", "211", "双非一本", "海本"],
        "min_ielts": {"total": 6.0, "subscore": 5.5},
        "min_toefl": {"total": 80, "subscore": 18},
        "gre_required": False,
        "deadline": "2027-01-31",
        "tier_bracket": "Match",
        "nuance": "语言门槛较低，但实际录取池水涨船高，对大厂实习与技术岗经历权重极高。"
    }
]


def cypher_filter_programs(
    undergrad_tier: str,
    gpa: float,
    language_scores: Dict[str, float],
    target_regions: List[str],
    target_majors: List[str],
    budget_wan: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Execute Cypher-style hard filtering on programs graph.

    Prunes non-matching programs by List constraints, language subscores, and GPA thresholds.
    """
    results = []
    ielts_total = language_scores.get("IELTS_total", language_scores.get("ielts", 0.0))
    ielts_sub = language_scores.get("speaking", language_scores.get("ielts_sub", 6.0))
    toefl_total = language_scores.get("TOEFL_total", language_scores.get("toefl", 0.0))

    # Convert GPA to 100-scale and 4.0-scale approximations
    gpa_4 = gpa if gpa <= 4.0 else round(gpa / 25.0, 2)
    gpa_100 = gpa if gpa > 10.0 else round(gpa * 25.0, 1)

    norm_regions = [r.upper() for r in target_regions] if target_regions else ["US", "UK", "SG", "HK"]
    norm_majors = [m.upper() for m in target_majors] if target_majors else ["CS"]

    for p in PROGRAMS_KG:
        # Check region
        if norm_regions and p["region"] not in norm_regions:
            continue
        # Check major
        if norm_majors and p["major_category"] not in norm_majors:
            continue
        # Check List tier constraint
        if undergrad_tier and undergrad_tier not in p["min_undergrad_tier"]:
            continue
        # Check GPA constraint
        if "gpa_min_4_0" in p and gpa_4 < p["gpa_min_4_0"] - 0.2:
            continue
        if "gpa_min_100" in p and gpa_100 < p["gpa_min_100"] - 3.0:
            continue
        # Check IELTS subscore constraint if IELTS is provided
        if ielts_total > 0:
            if ielts_total < p["min_ielts"]["total"] - 0.5:
                continue
            if ielts_sub > 0 and ielts_sub < p["min_ielts"]["subscore"] - 0.5:
                continue

        results.append(p)

    return results


def search_peer_admission_cases(
    undergrad_tier: str,
    gpa: float,
    major: str,
    target_program_id: str
) -> Dict[str, Any]:
    """Retrieve peer admission/rejection distributions from past 3 years."""
    # Representative vector RAG lookup
    cases_lookup = {
        "cmu_msit_se": {
            "admitted_sample": [
                {"profile": "985高校 软件工程 GPA 3.78, 托福 106, 微软STCA实习", "outcome": "ADMIT (Offer)"},
                {"profile": "海本Top40 CS GPA 3.72, GRE 328, 顶级开源项目贡献者", "outcome": "ADMIT (Offer)"}
            ],
            "rejected_sample": [
                {"profile": "211高校 计算机 GPA 3.65, 托福 101, 无高含金量工程产出", "outcome": "REJECT"},
                {"profile": "985高校 自动化跨申 GPA 3.52, 托福 98, 缺少系统核心课", "outcome": "REJECT"}
            ],
            "peer_median_gpa": 3.75,
            "acceptance_rate_range": "22% - 28%"
        },
        "uiuc_mcs": {
            "admitted_sample": [
                {"profile": "双非一本Top软件工程 GPA 89.2, 托福 102, 字节跳动后端实习", "outcome": "ADMIT (Offer)"},
                {"profile": "211高校 计科 GPA 3.61, 托福 104, 区域程序设计竞赛一等奖", "outcome": "ADMIT (Offer)"}
            ],
            "rejected_sample": [
                {"profile": "双非一本 GPA 84.0, 托福 96, 无实习无竞赛", "outcome": "REJECT"}
            ],
            "peer_median_gpa": 3.65,
            "acceptance_rate_range": "45% - 55%"
        },
        "ic_computing_msc": {
            "admitted_sample": [
                {"profile": "C9/985 软件工程 GPA 88.5, 雅思 7.5 (6.5), 顶级学术夏校", "outcome": "ADMIT (Offer)"},
                {"profile": "中流985 计科 GPA 89.1, 雅思 7.0 (6.5), 一作CCF-C在投", "outcome": "ADMIT (Offer)"}
            ],
            "rejected_sample": [
                {"profile": "头部双非 计科 GPA 91.0, 雅思 7.5 (不在List内)", "outcome": "REJECT (Out of List)"},
                {"profile": "211 软件工程 GPA 83.5, 雅思 7.0 (未达到85分门槛)", "outcome": "REJECT"}
            ],
            "peer_median_gpa": 88.2,
            "acceptance_rate_range": "18% - 25%"
        }
    }

    return cases_lookup.get(target_program_id, {
        "admitted_sample": [
            {"profile": f"{undergrad_tier}院校 {major} GPA 浮动中位数, 标化达标", "outcome": "ADMIT"}
        ],
        "rejected_sample": [
            {"profile": f"{undergrad_tier}院校 GPA 低于门槛或语言小分偏低", "outcome": "REJECT"}
        ],
        "peer_median_gpa": 3.60,
        "acceptance_rate_range": "35% - 50%"
    })


def retrieve_program_nuances(program_id: str) -> Dict[str, Any]:
    """Retrieve covert institutional preferences and operational nuances."""
    for p in PROGRAMS_KG:
        if p["id"] == program_id:
            return {
                "program_id": program_id,
                "name": p["name_cn"],
                "nuance_summary": p.get("nuance", "暂无特别偏好说明"),
                "deadline": p.get("deadline", "待官网核实"),
                "gre_policy": "Optional / Not Required" if not p.get("gre_required") else "Required",
                "stem_status": "STEM-Designated (Eligible for 3-Year OPT)" if p.get("region") == "US" else "N/A"
            }
    return {
        "program_id": program_id,
        "name": "待核验项目",
        "nuance_summary": "请依据学校官网最新招生页面与院系要求核实",
        "deadline": "待官网核实",
        "gre_policy": "待官网核实",
        "stem_status": "待官网核实"
    }
