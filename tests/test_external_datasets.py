"""Unit and Integration Tests for External Datasets Benchmark Suite.

Validates:
1. Kaggle Graduate Admissions (UCLA Benchmark):
   - Spearman rank correlation > 0.75
   - Strict monotonicity preservation (100%)
   - Prediction bounds validity
2. GradCafe Real Decision Data:
   - Data ingestion integrity and record parsing
3. Statement of Purpose (SOP) Real vs AI Corpus:
   - 100% zero banned words on authentic human admitted SOPs
   - Detection of AI clichés in vanilla AI essays
   - Number faithfulness on authentic vs hallucinated metrics
   - Gatekeeper and Pareto Hypervolume superiority
"""

import json
from pathlib import Path
import pytest
import numpy as np

from benchmarks.run_external_benchmarks import (
    evaluate_kaggle_admissions,
    evaluate_gradcafe_admissions,
    evaluate_real_vs_ai_sop_corpus,
)
from prismera.guardrails import AntiAIGuardrail
from prismera.ml.llm_finetune.eval_finetuned import check_number_faithfulness
from prismera.ml.llm_finetune.pareto_jury import get_pareto_jury


KAGGLE_CSV = "data/external/kaggle_graduate_admissions.csv"
GRADCAFE_CSV = "data/external/gradcafe_cs_sample.csv"
SOP_CORPUS = "data/external/real_vs_ai_sop_corpus.json"


def test_kaggle_admissions_benchmark_metrics():
    """Verify AdmitNet achieves high rank correlation and strict monotonicity on Kaggle dataset."""
    assert Path(KAGGLE_CSV).exists(), "Kaggle dataset must be downloaded"
    results = evaluate_kaggle_admissions(KAGGLE_CSV)

    assert results["total_records"] == 500
    assert results["spearman_rank_correlation"] >= 0.80, "Spearman rank correlation should exceed 0.80"
    assert results["monotonicity_compliance_rate"] == "100.0%", "Mathematical monotonicity must hold for all 500 records"
    assert results["mean_absolute_error"] < 0.30
    assert len(results["sample_comparison"]) > 0


def test_gradcafe_cs_data_integrity():
    """Verify GradCafe admissions decision parsing and categorization."""
    assert Path(GRADCAFE_CSV).exists(), "GradCafe dataset must exist"
    results = evaluate_gradcafe_admissions(GRADCAFE_CSV)

    assert results["total_records_analyzed"] >= 200
    decisions = results["decisions_breakdown"]
    assert "accepted" in decisions
    assert "rejected" in decisions
    assert len(results["target_institutions_breakdown"]) >= 5


def test_sop_corpus_guardrail_and_pareto_jury():
    """Verify Anti-AI purity and Pareto Jury separation between human admitted and AI vanilla essays."""
    assert Path(SOP_CORPUS).exists(), "SOP corpus JSON must exist"
    results = evaluate_real_vs_ai_sop_corpus(SOP_CORPUS)

    human = results["human_essays_summary"]
    ai = results["ai_vanilla_summary"]

    # 1. Human essays must have zero banned AI clichés
    assert human["banned_words_per_sample"] == 0.0

    # 2. AI essays must have multiple flagged banned words
    assert ai["banned_words_per_sample"] >= 3.0

    # 3. Gatekeeper score of human essays must strongly surpass vanilla AI
    assert human["avg_gatekeeper_score"] > ai["avg_gatekeeper_score"] + 30.0

    # 4. Scholar technical depth and Pareto Hypervolume
    assert human["avg_scholar_score"] > ai["avg_scholar_score"]
    assert human["avg_pareto_hypervolume"] > ai["avg_pareto_hypervolume"]


def test_number_faithfulness_on_external_corpus():
    """Verify that hallucinated numbers in prompt-less context are detected."""
    with open(SOP_CORPUS, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    hallucinated_item = next(item for item in corpus if item["id"] == "ai_hallucinated_metrics_03")
    is_faithful = check_number_faithfulness(hallucinated_item["prompt_context"], hallucinated_item["text"])
    assert not is_faithful, "Invented metrics (94.7%, 85,000 QPS) without prompt context must fail faithfulness check"

    human_item = next(item for item in corpus if item["id"] == "human_cmu_cs_01")
    human_faithful = check_number_faithfulness(human_item["prompt_context"], human_item["text"])
    assert human_faithful, "Compliant human essay should pass faithfulness check"
