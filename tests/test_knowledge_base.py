"""Comprehensive tests for PrismEra GraphRAG Hybrid Knowledge Base (Milestone 1).

Tests:
1. Seed data schema and node/edge completeness (18+ programs across US, UK, SG, HK).
2. GraphStore CRUD, SQLite persistence, and real graph traversal pruning with audit reasons.
3. Prerequisite subgraphs and scholar academic integrity.
4. VectorStore semantic embedding, hybrid metadata filtering, and dynamic admission statistics.
5. Deterministic tool backward compatibility.
"""

import os
import tempfile
import pytest

from prismera.db.graph_store import GraphStore, get_graph_store, FilteredProgramList
from prismera.db.vector_store import (
    VectorStore,
    get_vector_store,
    AdmissionCase,
    ProgramNuance,
)
from prismera.tools.admission_tools import (
    cypher_filter_programs,
    search_peer_admission_cases,
    retrieve_program_nuances,
    get_last_pruning_audit,
)
from prismera.tools.prerequisite_tools import check_prerequisite_graph
from prismera.tools.program_tools import get_program_ethos_and_courses
from prismera.tools.scholar_tools import fetch_scholar_recent_papers, inspect_lab_openings


def test_seed_data_completeness():
    gs = get_graph_store()
    programs = gs.get_nodes_by_label("Program")
    assert len(programs) >= 18, f"Expected at least 18 programs, got {len(programs)}"

    regions = {p.get("region") for p in programs}
    assert {"US", "UK", "SG", "HK"}.issubset(regions), "Must cover US, UK, SG, HK"

    majors = {p.get("major_category") for p in programs}
    assert {"CS", "DS", "BA", "FIN"}.issubset(majors), "Must cover CS, DS, BA, FIN"

    universities = gs.get_nodes_by_label("University")
    assert len(universities) >= 12

    professors = gs.get_nodes_by_label("Professor")
    assert len(professors) >= 6

    courses = gs.get_nodes_by_label("Course")
    assert len(courses) >= 8

    tiers = gs.get_nodes_by_label("ChineseUniTier")
    assert len(tiers) >= 4


def test_graph_store_sqlite_roundtrip():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        gs1 = GraphStore(sqlite_path=tmp_path, auto_load=False)
        gs1.load_from_seed()
        gs1.save_to_sqlite(tmp_path)

        # Reload from sqlite
        gs2 = GraphStore(sqlite_path=tmp_path, auto_load=True)
        assert len(gs2.graph.nodes) == len(gs1.graph.nodes)
        assert len(gs2.graph.edges) == len(gs1.graph.edges)
        assert gs2.get_node("cmu_msit_se") is not None
        assert gs2.get_node("ic_computing_msc") is not None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_graph_traversal_hard_pruning_double_non():
    """Test precise pruning: Double-non student with GPA 82 and speaking 5.5."""
    gs = get_graph_store()

    res = gs.query_programs_filtered(
        undergrad_tier="双非一本",
        gpa=82.0,
        language_scores={"IELTS_total": 6.5, "speaking": 5.5},
        target_regions=["UK"],
        target_majors=["CS"]
    )

    # In the UK, IC doesn't accept double-non, UCL requires 90, Edinburgh requires 88+ and speaking 6.5
    assert len(res) == 0
    assert len(res.pruned_records) >= 3

    pruned_programs = {r["program_id"]: r["reason"] for r in res.pruned_records}

    # IC prunes due to List
    assert "ic_computing_msc" in pruned_programs
    assert "院校背景受限" in pruned_programs["ic_computing_msc"]

    # UCL prunes due to GPA < 90 for double-non
    assert "ucl_cs_msc" in pruned_programs
    assert "均分未达标" in pruned_programs["ucl_cs_msc"] or "雅思口语单项受阻" in pruned_programs["ucl_cs_msc"]

    # Edinburgh prunes due to List or speaking 5.5
    assert "edinburgh_cs_msc" in pruned_programs
    assert ("院校背景受限" in pruned_programs["edinburgh_cs_msc"] or
            "雅思口语单项受阻" in pruned_programs["edinburgh_cs_msc"])


def test_graph_traversal_speaking_subscore_pruning():
    """Test that a 211 student with GPA 85 is pruned from Edinburgh if speaking is 5.5."""
    gs = get_graph_store()

    res = gs.query_programs_filtered(
        undergrad_tier="211",
        gpa=85.0,
        language_scores={"IELTS_total": 7.0, "speaking": 5.5},
        target_regions=["UK"],
        target_majors=["CS"]
    )

    pruned_programs = {r["program_id"]: r["reason"] for r in res.pruned_records}
    assert "edinburgh_cs_msc" in pruned_programs
    assert "口语" in pruned_programs["edinburgh_cs_msc"]


def test_graph_traversal_qualified_student_passes():
    """Test that a 985 student with GPA 89.0 and IELTS 7.5 (7.0) passes top UK CS programs."""
    gs = get_graph_store()

    res = gs.query_programs_filtered(
        undergrad_tier="985",
        gpa=89.0,
        language_scores={"IELTS_total": 7.5, "speaking": 7.0},
        target_regions=["UK"],
        target_majors=["CS"]
    )

    matched_ids = [p["id"] for p in res]
    assert "ic_computing_msc" in matched_ids
    assert "ucl_cs_msc" in matched_ids
    assert "edinburgh_cs_msc" in matched_ids
    assert "oxford_msc_cs" in matched_ids


def test_prerequisite_subgraph_query():
    gs = get_graph_store()
    cs_prereqs = gs.get_prerequisites_for_program("cmu_msit_se")
    assert len(cs_prereqs) > 0

    course_names = [p["course_id"] for p in cs_prereqs]
    assert "course_dsa" in course_names

    # Test tool wrapper
    res = check_prerequisite_graph("CS", ["数据结构与算法", "微积分与线性代数"])
    assert res["target_major"] == "CS"
    assert len(res["alignment_table"]) > 0


def test_scholar_integrity_in_graph_store():
    papers = fetch_scholar_recent_papers("Indranil Gupta")
    assert len(papers) > 0
    assert any("Gossip" in p["title"] for p in papers)

    openings = inspect_lab_openings("Indranil Gupta")
    assert openings["scholar_name"] == "Indranil Gupta"
    assert "dprg" in openings.get("lab_page", "")

    # Fabricated scholar must return empty list (Academic integrity rule)
    fake_papers = fetch_scholar_recent_papers("Ghost NonExistent Professor")
    assert len(fake_papers) == 0


def test_vector_store_crud_and_persistence():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        vs1 = VectorStore(sqlite_path=tmp_path, auto_load=False)
        vs1.load_from_seed()
        vs1.save_to_sqlite(tmp_path)

        vs2 = VectorStore(sqlite_path=tmp_path, auto_load=True)
        assert len(vs2.cases) == len(vs1.cases)
        assert len(vs2.nuances) == len(vs1.nuances)

        # Test semantic search with metadata filter
        results = vs2.search_admission_cases(
            query_text="字节跳动实习 竞赛一等奖",
            filter_metadata={"target_program_id": "uiuc_mcs"},
            top_k=2
        )
        assert len(results) > 0
        assert results[0]["target_program_id"] == "uiuc_mcs"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_dynamic_admission_metrics_calculation():
    vs = get_vector_store()

    # Top student applying to CMU
    metrics_top = vs.calculate_admission_metrics("cmu_msit_se", "985", 3.85, "CS")
    assert "peer_median_gpa" in metrics_top
    assert metrics_top["peer_median_gpa"] > 3.6
    assert metrics_top["bracket_recommendation"] in ["Match", "Safety"]
    assert len(metrics_top["admitted_sample"]) > 0
    assert len(metrics_top["rejected_sample"]) > 0

    # Double-non student applying to competitive program
    metrics_low = vs.calculate_admission_metrics("cmu_msit_se", "双非一本", 3.3, "CS")
    assert metrics_low["bracket_recommendation"] == "Reach"
    assert "%" in metrics_low["acceptance_rate_range"]


def test_tools_backward_compatibility():
    # 1. cypher_filter_programs
    progs = cypher_filter_programs(
        undergrad_tier="985",
        gpa=3.7,
        language_scores={"IELTS_total": 7.5, "speaking": 7.0},
        target_regions=["US", "UK"],
        target_majors=["CS"]
    )
    assert isinstance(progs, list)
    assert len(progs) > 0
    assert hasattr(progs, "pruned_records")

    first_prog = progs[0]
    assert "id" in first_prog
    assert "name_cn" in first_prog
    assert "deadline" in first_prog
    assert "min_ielts" in first_prog

    # 2. search_peer_admission_cases
    cases = search_peer_admission_cases("985", 3.7, "CS", first_prog["id"])
    assert "peer_median_gpa" in cases
    assert "acceptance_rate_range" in cases
    assert len(cases["admitted_sample"]) > 0

    # 3. retrieve_program_nuances
    nuance = retrieve_program_nuances(first_prog["id"])
    assert "nuance_summary" in nuance
    assert "gre_policy" in nuance

    # 4. get_program_ethos_and_courses
    ethos = get_program_ethos_and_courses("cmu_msit_se")
    assert ethos["institution"] == "Carnegie Mellon University"
    assert len(ethos["distinctive_courses"]) > 0
