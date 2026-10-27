"""Scholar publication search and lab opening inspection tools for prism_resonator.

Queries GraphStore for Professor nodes, recent publications, and laboratory openings,
strictly upholding academic integrity.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional

from prismera.db.graph_store import get_graph_store

SCHOLARS_DB: Dict[str, Any] = {}


def fetch_scholar_recent_papers(
    scholar_name: str,
    institution: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fetch core research papers published in the last 3 years by the target scholar.

    If not found in the GraphStore, returns an empty list to uphold academic integrity.
    """
    gs = get_graph_store()
    prof = gs.find_professor_by_name(scholar_name)

    if prof and "recent_papers" in prof:
        return prof["recent_papers"]

    # Academic integrity rule: do not fabricate citations
    return []


def inspect_lab_openings(
    scholar_name: str,
    institution: Optional[str] = None
) -> Dict[str, Any]:
    """Inspect prospective student openings and funding status for the professor's laboratory."""
    gs = get_graph_store()
    prof = gs.find_professor_by_name(scholar_name)

    if prof:
        openings = prof.get("openings", {})
        return {
            "scholar_name": prof.get("name", scholar_name),
            "institution": prof.get("institution", institution or "Target Institution"),
            "lab_name": prof.get("lab", "Research Laboratory"),
            **openings
        }

    return {
        "scholar_name": scholar_name,
        "institution": institution or "Target Institution",
        "lab_name": "Research Group",
        "phd_fall_2027": "待官方邮件或导师主页更新确认",
        "funding_status": "建议在套磁信中主动礼貌询问",
        "lab_page": "https://scholar.google.com"
    }
