"""Unit and integration tests for Knowledge Base Ingestion Pipeline (Pydantic V2 & GraphStore/VectorStore)."""

import pytest
from pydantic import ValidationError

from prismera.db.ingestor import (
    KnowledgeIngestor,
    ProgramIngestModel,
    ProfessorIngestModel,
    PaperModel,
    PrerequisiteCourseIngestModel,
    BatchIngestBundle,
    ListTierRequirement,
    LanguageRequirementsModel,
)
from prismera.db.graph_store import GraphStore
from prismera.db.vector_store import VectorStore
from prismera.tools.admission_tools import cypher_filter_programs
from prismera.tools.scholar_tools import fetch_scholar_recent_papers


@pytest.fixture
def isolated_ingestor(tmp_path):
    """Provides an isolated in-memory GraphStore and VectorStore ingestor."""
    graph_sqlite = tmp_path / "test_graph.sqlite"
    vector_sqlite = tmp_path / "test_vector.sqlite"

    gs = GraphStore(sqlite_path=graph_sqlite, auto_load=True)
    vs = VectorStore(sqlite_path=vector_sqlite, auto_load=True)

    ingestor = KnowledgeIngestor(graph_store=gs, vector_store=vs, auto_persist=False)
    return ingestor


def test_pydantic_schema_valid_program():
    """Verify valid ProgramIngestModel initialization and defaults."""
    valid_data = {
        "id": "cambridge_mphil_acs",
        "name_cn": "剑桥大学 · 高级计算机科学哲学硕士",
        "name_en": "MPhil in Advanced Computer Science",
        "institution": "University of Cambridge",
        "region": "UK",
        "major_category": "CS",
        "academic_year": "2026_2027",
        "duration": "9 Months",
        "tuition_gbp": 41500,
        "min_ielts": {"total": 7.5, "subscore": 7.0, "speaking": 7.0},
        "min_toefl": {"total": 107, "subscore": 25},
        "tier_bracket": "Reach",
        "stem": True,
        "gre_required": False,
        "deadline": "Round 1: Dec 05",
        "distinctive_courses": [{"code": "ACS-L48", "title": "Advanced Topics in Computer Systems"}],
        "accepted_tiers": [{"tier": "985", "min_gpa_score": 90.0}, {"tier": "211", "min_gpa_score": 92.0}],
        "required_prerequisites": [{"course_id": "course_dsa", "level": "mandatory"}],
    }

    model = ProgramIngestModel.model_validate(valid_data)
    assert model.id == "cambridge_mphil_acs"
    assert model.region == "UK"
    assert model.min_ielts.speaking == 7.0
    assert len(model.accepted_tiers) == 2


def test_pydantic_schema_invalid_region_or_major():
    """Verify that unsupported regions or major categories trigger ValidationError."""
    invalid_data = {
        "id": "invalid_prog",
        "name_cn": "测试项目",
        "name_en": "Test Program",
        "institution": "Test Uni",
        "region": "MARS",  # Invalid region
        "major_category": "CS",
        "academic_year": "2026_2027",
        "duration": "1 Year",
        "min_ielts": {"total": 7.0, "subscore": 6.5},
        "min_toefl": {"total": 100, "subscore": 22},
    }

    with pytest.raises(ValidationError) as exc_info:
        ProgramIngestModel.model_validate(invalid_data)
    assert "Invalid region 'MARS'" in str(exc_info.value)


def test_pydantic_schema_invalid_tier():
    """Verify that non-standard tier names trigger ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ListTierRequirement(tier="RandomTier", min_gpa_score=85.0)
    assert "Invalid tier name 'RandomTier'" in str(exc_info.value)


def test_pydantic_professor_and_paper_validation():
    """Verify ProfessorIngestModel and PaperModel validation."""
    valid_prof = {
        "id": "anthony_fox",
        "name": "Anthony Fox",
        "institution": "University of Cambridge",
        "lab": "Automated Reasoning Group",
        "research_areas": ["Formal Verification", "ISA Semantics"],
        "academic_year": "2026_2027",
        "openings": {
            "phd_fall_2027": "Open (1 funded PhD position in Arm Verification)",
            "funding_status": "EPSRC Research Grant",
        },
        "recent_papers": [
            {
                "title": "Machine-Checked Verification of Arm Architecture Specifications",
                "year": 2025,
                "venue": "CAV 2025",
                "abstract": "We mechanize instruction semantics in HOL4 and verify memory consistency.",
                "future_work_bottleneck": "Automating equivalence checking across microarchitectural speculation barriers.",
                "academic_year": "2026_2027",
            }
        ],
    }

    model = ProfessorIngestModel.model_validate(valid_prof)
    assert model.name == "Anthony Fox"
    assert len(model.recent_papers) == 1
    assert model.recent_papers[0].year == 2025


def test_ingest_program_incremental_and_query(isolated_ingestor):
    """Test hot incremental ingestion of a new program and live query."""
    new_prog = {
        "id": "oxford_msc_se",
        "name_cn": "牛津大学 · 软件工程理学硕士",
        "name_en": "MSc in Software Engineering",
        "institution": "University of Oxford",
        "region": "UK",
        "major_category": "SE",
        "academic_year": "2026_2027",
        "duration": "1 Year",
        "tuition_gbp": 38000,
        "min_ielts": {"total": 7.5, "subscore": 7.0, "speaking": 7.0},
        "min_toefl": {"total": 110, "subscore": 25},
        "tier_bracket": "Reach",
        "stem": True,
        "gre_required": False,
        "deadline": "Jan 10",
        "accepted_tiers": [
            {"tier": "985", "min_gpa_score": 88.0},
            {"tier": "211", "min_gpa_score": 90.0},
        ],
        "required_prerequisites": [
            {"course_id": "course_dsa", "level": "mandatory"}
        ],
        "nuance": "偏好具有大型企业软件工程架构经验的申请人",
    }

    res = isolated_ingestor.ingest_program(new_prog)
    assert res["status"] == "success"
    assert res["id"] == "oxford_msc_se"

    # Verify GraphStore node exists
    node = isolated_ingestor.graph_store.get_node("oxford_msc_se")
    assert node is not None
    assert node["name_cn"] == "牛津大学 · 软件工程理学硕士"

    # Verify ACCEPTS_LIST edge exists
    edges = isolated_ingestor.graph_store.get_outgoing_edges("oxford_msc_se", rel_type="ACCEPTS_LIST")
    assert len(edges) == 2

    # Verify VectorStore nuance was synchronized
    nuance = isolated_ingestor.vector_store.search_program_nuance("oxford_msc_se")
    assert nuance is not None
    assert "大型企业软件工程架构经验" in nuance["nuance_summary"]


def test_ingest_professor_incremental(isolated_ingestor):
    """Test hot incremental ingestion of a faculty member and papers."""
    prof_data = {
        "id": "samir_khuller",
        "name": "Samir Khuller",
        "institution": "Northwestern University",
        "lab": "Theoretical Computer Science Group",
        "research_areas": ["Approximation Algorithms", "Graph Theory"],
        "academic_year": "2026_2027",
        "openings": {
            "phd_fall_2027": "Open (2 positions in Combinatorial Optimization)",
            "funding_status": "NSF Algorithm Grant",
        },
        "recent_papers": [
            {
                "title": "Bicriteria Approximation Bounds for Energy-Aware Job Scheduling",
                "year": 2025,
                "venue": "ACM STOC 2025",
                "abstract": "We formulate LP relaxation rounding techniques for parallel machine scheduling.",
                "future_work_bottleneck": "Dynamic online scheduling under stochastic arrival distributions.",
                "academic_year": "2026_2027",
            }
        ],
    }

    res = isolated_ingestor.ingest_professor(prof_data)
    assert res["status"] == "success"
    assert res["id"] == "samir_khuller"

    # Query GraphStore directly
    prof_node = isolated_ingestor.graph_store.find_professor_by_name("Samir Khuller")
    assert prof_node is not None
    assert len(prof_node["recent_papers"]) == 1
    assert prof_node["recent_papers"][0]["venue"] == "ACM STOC 2025"


def test_ingest_batch_bundle_and_inspection(isolated_ingestor):
    """Test batch bundle ingestion and health inspection audit."""
    bundle = {
        "academic_year": "2026_2027",
        "universities": [
            {
                "id": "cambridge",
                "name_cn": "剑桥大学",
                "name_en": "University of Cambridge",
                "region": "UK",
                "qs_ranking": 2,
            }
        ],
        "courses": [
            {
                "id": "course_compiler",
                "name_cn": "编译原理与程序分析",
                "name_en": "Compilers & Program Analysis",
                "major_category": "CS",
                "aliases": ["编译原理", "compiler design"],
                "importance": "High",
                "academic_year": "2026_2027",
            }
        ],
        "programs": [
            {
                "id": "cambridge_msc_ai",
                "name_cn": "剑桥大学 · 机器智能哲学硕士",
                "name_en": "MPhil in Machine Learning and Machine Intelligence",
                "institution": "University of Cambridge",
                "region": "UK",
                "major_category": "AI",
                "academic_year": "2026_2027",
                "duration": "1 Year",
                "min_ielts": {"total": 7.5, "subscore": 7.0},
                "min_toefl": {"total": 107, "subscore": 25},
                "accepted_tiers": [{"tier": "985", "min_gpa_score": 90.0}],
            }
        ],
    }

    batch_res = isolated_ingestor.ingest_batch(bundle)
    assert batch_res["status"] == "success"
    assert batch_res["ingested_counts"]["universities"] == 1
    assert batch_res["ingested_counts"]["courses"] == 1
    assert batch_res["ingested_counts"]["programs"] == 1

    # Audit knowledge base
    audit = isolated_ingestor.inspect_knowledge_base()
    assert audit["programs_count"] >= 19
    assert audit["courses_count"] >= 11
    assert audit["universities_count"] >= 16
    assert "UK" in audit["programs_by_region"]
