"""Admission Knowledge Graph and Vector RAG tools for prism_locus.

Refactored to query real GraphStore (NetworkX/SQLite) and VectorStore (NumPy/SQLite).
Preserves 100% backward compatibility for agent signatures and return payloads.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional

from prismera.db.graph_store import get_graph_store, FilteredProgramList
from prismera.db.vector_store import get_vector_store


def _get_all_programs() -> List[Dict[str, Any]]:
    """Retrieve all programs from the GraphStore."""
    gs = get_graph_store()
    return gs.get_nodes_by_label("Program")


# Expose dynamic/cached list for any backward-compatible imports
PROGRAMS_KG = _get_all_programs()


def get_last_pruning_audit() -> List[Dict[str, Any]]:
    """Retrieve reasons for programs pruned in the last Cypher filter query."""
    return get_graph_store().get_last_pruning_audit()


def cypher_filter_programs(
    undergrad_tier: str,
    gpa: float,
    language_scores: Dict[str, float],
    target_regions: List[str],
    target_majors: List[str],
    budget_wan: Optional[int] = None
) -> FilteredProgramList:
    """Execute Cypher-style hard filtering on programs graph.

    Prunes non-matching programs by List constraints, language subscores, and GPA thresholds.
    Returns a FilteredProgramList (list subclass) containing matching programs
    and detailed audit reasons for pruned programs.
    """
    gs = get_graph_store()
    return gs.query_programs_filtered(
        undergrad_tier=undergrad_tier,
        gpa=gpa,
        language_scores=language_scores,
        target_regions=target_regions,
        target_majors=target_majors,
        budget_wan=budget_wan
    )


def search_peer_admission_cases(
    undergrad_tier: str,
    gpa: float,
    major: str,
    target_program_id: str,
    student_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Retrieve peer admission/rejection distributions from past 3 years.

    Dynamically calculates peer median GPA and acceptance rate range based on
    the student's tier and GPA position within the historical applicant pool,
    empowered by Prism-AdmitNet ML probability and feature attributions.
    """
    vs = get_vector_store()
    return vs.calculate_admission_metrics(
        target_program_id=target_program_id,
        undergrad_tier=undergrad_tier,
        gpa=gpa,
        major=major,
        student_profile=student_profile
    )


def retrieve_program_nuances(program_id: str) -> Dict[str, Any]:
    """Retrieve covert institutional preferences and operational nuances."""
    vs = get_vector_store()
    nuance_data = vs.search_program_nuance(program_id)

    if nuance_data:
        return {
            "program_id": program_id,
            "name": nuance_data.get("name", "Target Program"),
            "nuance_summary": nuance_data.get("nuance_summary", "暂无特别偏好说明"),
            "deadline": nuance_data.get("deadline", "待官网核实"),
            "gre_policy": nuance_data.get("gre_policy", "Optional / Not Required"),
            "stem_status": nuance_data.get("stem_status", "N/A"),
            "detailed_text": nuance_data.get("detailed_text", "")
        }

    # Fallback to GraphStore
    gs = get_graph_store()
    node = gs.get_node(program_id)
    if node:
        return {
            "program_id": program_id,
            "name": node.get("name_cn", program_id),
            "nuance_summary": node.get("nuance", "暂无特别偏好说明"),
            "deadline": node.get("deadline", "待官网核实"),
            "gre_policy": "Required" if node.get("gre_required") else "Optional / Not Required",
            "stem_status": "STEM-Designated (Eligible for 3-Year OPT)" if node.get("stem") else "N/A"
        }

    return {
        "program_id": program_id,
        "name": "待核验项目",
        "nuance_summary": "请依据学校官网最新招生页面与院系要求核实",
        "deadline": "待官网核实",
        "gre_policy": "待官网核实",
        "stem_status": "待官网核实"
    }
