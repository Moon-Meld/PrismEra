"""Tests for PrismEra deterministic tools."""

from prismera.tools.gpa_tools import calculate_gpa_metrics
from prismera.tools.prerequisite_tools import check_prerequisite_graph
from prismera.tools.admission_tools import (
    cypher_filter_programs,
    search_peer_admission_cases,
    retrieve_program_nuances,
)
from prismera.tools.program_tools import get_program_ethos_and_courses
from prismera.tools.scholar_tools import fetch_scholar_recent_papers, inspect_lab_openings


def test_gpa_calculation():
    res = calculate_gpa_metrics("88/100")
    assert "overall_gpa_4_0" in res
    assert res["overall_gpa_4_0"] > 3.0
    assert "wes_gpa_estimated" in res


def test_prerequisite_graph():
    # CS target with standard courses
    courses = ["高等数学 (Calculus)", "线性代数", "数据结构与算法"]
    res = check_prerequisite_graph("CS", courses)
    assert res["target_major"] == "CS"
    assert len(res["alignment_table"]) > 0


def test_admission_filtering_and_nuances():
    programs = cypher_filter_programs(
        undergrad_tier="985",
        gpa=3.7,
        language_scores={"IELTS_total": 7.5, "speaking": 7.0},
        target_regions=["US", "UK"],
        target_majors=["CS"]
    )
    assert len(programs) > 0
    prog_id = programs[0]["id"]

    peer_cases = search_peer_admission_cases("985", 3.7, "CS", prog_id)
    assert "peer_median_gpa" in peer_cases

    nuance = retrieve_program_nuances(prog_id)
    assert "nuance_summary" in nuance


def test_scholar_tools_academic_integrity():
    # Real professor in cache
    papers = fetch_scholar_recent_papers("Indranil Gupta")
    assert len(papers) > 0
    assert "Adaptive Gossip Consensus" in papers[0]["title"]

    openings = inspect_lab_openings("Indranil Gupta")
    assert openings["scholar_name"] == "Indranil Gupta"

    # Fabricated / unknown professor should return empty to protect academic integrity
    fake_papers = fetch_scholar_recent_papers("NonExistent Professor")
    assert len(fake_papers) == 0
