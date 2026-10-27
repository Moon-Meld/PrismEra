"""Unit and integration tests for the GraphRAG Evaluation Benchmark engine."""

import json
from pathlib import Path
import pytest

from benchmarks.run_eval import (
    DEFAULT_DATASET_PATH,
    run_benchmark,
    eval_hard_constraint_graphrag,
    eval_socratic_gate_anti_ai_graphrag,
    eval_citation_faithfulness_graphrag,
    eval_baseline_case,
    export_markdown_report,
    export_json_report,
)


def test_eval_dataset_structural_integrity():
    """Verify that eval_dataset.json adheres to schema and contains 25-30 golden cases."""
    assert DEFAULT_DATASET_PATH.exists()

    with open(DEFAULT_DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("benchmark_meta", {})
    assert meta.get("target_academic_year") == "2026_2027"
    assert "categories" in meta

    test_cases = data.get("test_cases", [])
    assert 25 <= len(test_cases) <= 30, f"Expected 25-30 cases, found {len(test_cases)}"

    # Check category distribution
    cats = [tc["category"] for tc in test_cases]
    assert cats.count("hard_constraint") >= 10
    assert cats.count("socratic_gate_anti_ai") >= 6
    assert cats.count("citation_faithfulness") >= 6

    # Verify every test case has required keys
    for tc in test_cases:
        assert "id" in tc
        assert "category" in tc
        assert "title" in tc
        assert "trap_type" in tc
        assert "input" in tc
        assert "expected_behavior" in tc
        assert "baseline_vulnerability" in tc


def test_eval_hard_constraint_subscore_trap():
    """Test IELTS speaking subscore trap evaluation (TC-HARD-001)."""
    with open(DEFAULT_DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    tc1 = next(tc for tc in dataset["test_cases"] if tc["id"] == "TC-HARD-001")
    passed, details = eval_hard_constraint_graphrag(tc1)

    assert passed is True
    assert details["intercepted"] is True
    assert details["reason_keywords_present"] is True
    assert "ic_computing_msc" in details["pruned_ids"]


def test_eval_hard_constraint_uk_list_trap():
    """Test Edinburgh CS UK list exclusion trap evaluation (TC-HARD-003)."""
    with open(DEFAULT_DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    tc3 = next(tc for tc in dataset["test_cases"] if tc["id"] == "TC-HARD-003")
    passed, details = eval_hard_constraint_graphrag(tc3)

    assert passed is True
    assert details["intercepted"] is True
    assert "edinburgh_cs_msc" in details["pruned_ids"]


def test_eval_socratic_gate_force_skip_trap():
    """Test Socratic Stage 1 gatekeeper interception when user demands full draft (TC-SOCR-001)."""
    with open(DEFAULT_DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    tc = next(tc for tc in dataset["test_cases"] if tc["id"] == "TC-SOCR-001")
    gate_ok, clean_ok, details = eval_socratic_gate_anti_ai_graphrag(tc)

    assert gate_ok is True
    assert clean_ok is True
    assert details["stayed_in_stage_1"] is True
    assert details["refused_full_draft"] is True


def test_eval_anti_ai_cliche_rewrite_zero_hits():
    """Test that Anti-AI guardrail purges all 8 banned clichés down to 0 hits (TC-SOCR-004)."""
    with open(DEFAULT_DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    tc = next(tc for tc in dataset["test_cases"] if tc["id"] == "TC-SOCR-004")
    gate_ok, clean_ok, details = eval_socratic_gate_anti_ai_graphrag(tc)

    assert clean_ok is True
    assert details["initial_violations_count"] >= 5
    assert len(details["remaining_hits"]) == 0
    assert details["post_clean_cleanliness"] == 1.0


def test_eval_citation_faithfulness_unknown_scholar():
    """Test that Resonator triggers Academic Integrity warning for fictitious scholar (TC-SCHOLAR-001)."""
    with open(DEFAULT_DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    tc = next(tc for tc in dataset["test_cases"] if tc["id"] == "TC-SCHOLAR-001")
    passed, details = eval_citation_faithfulness_graphrag(tc)

    assert passed is True
    assert details["triggered_warning"] is True
    assert details["no_fake_draft"] is True


def test_eval_citation_faithfulness_known_scholar():
    """Test that Resonator faithfully cites real paper for Indranil Gupta (TC-SCHOLAR-003)."""
    with open(DEFAULT_DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    tc = next(tc for tc in dataset["test_cases"] if tc["id"] == "TC-SCHOLAR-003")
    passed, details = eval_citation_faithfulness_graphrag(tc)

    assert passed is True
    assert details["cites_paper"] is True


def test_full_benchmark_run_and_report_generation(tmp_path):
    """Run full benchmark execution, verifying metrics and file persistence."""
    summary = run_benchmark(dataset_path=DEFAULT_DATASET_PATH, verbose=False)

    gr = summary["metrics"]["prismera_graphrag"]
    bl = summary["metrics"]["baseline_pure_prompt"]

    # Quantitative assertions
    assert gr["Hard_Constraint_Precision"] == 100.0
    assert gr["Stage_Gate_Compliance"] == 100.0
    assert gr["Anti_AI_Lexicon_Clean_Rate"] == 100.0
    assert gr["Citation_Faithfulness"] == 100.0

    # Baseline should exhibit typical LLM vulnerabilities
    assert bl["Hard_Constraint_Precision"] < 50.0
    assert bl["Stage_Gate_Compliance"] < 50.0
    assert bl["Anti_AI_Lexicon_Clean_Rate"] < 50.0

    # Test file exports
    json_path = tmp_path / "test_report.json"
    md_path = tmp_path / "test_report.md"

    export_json_report(summary, json_path)
    export_markdown_report(summary, md_path)

    assert json_path.exists()
    assert md_path.exists()

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Hard_Constraint_Precision" in content
    assert "Stage_Gate_Compliance" in content
    assert "Anti_AI_Lexicon_Clean_Rate" in content
    assert "Citation_Faithfulness" in content
