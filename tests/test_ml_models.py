"""Unit and Integration Tests for Milestone 4 Machine Learning and LLM Fine-Tuning Module.

Validates:
  1. Prism-AdmitNet: Feature extraction, training, JSON persistence, strict GPA monotonicity,
     and feature attribution breakdown.
  2. Prism-DeAI Essay DPO Dataset: Format compliance, Show-Don't-Tell quality, and strict Anti-AI zero-violation check.
  3. Prism-Luminary Router SFT Dataset: Instruction format compliance and Pydantic LuminaryDecision parsing.
  4. Training Pipeline: Dry-run LoRA parameter calculation and adapter persistence.
  5. End-to-end Integration: Verification of search_peer_admission_cases and locus_node with ML scoring.
"""

import json
import os
import tempfile
from pathlib import Path
import pytest
import numpy as np

from prismera.ml.admit_predictor import (
    PrismAdmitPredictor,
    get_admit_predictor,
    FEATURE_NAMES,
)
from prismera.guardrails import AntiAIGuardrail
from prismera.state import LuminaryDecision
from prismera.tools.admission_tools import search_peer_admission_cases
from prismera.agents.locus import locus_node
from prismera.ml.llm_finetune.train_lora_dpo import execute_dry_run, validate_dataset


# ==============================================================================
# 1. Prism-AdmitNet Tests
# ==============================================================================

def test_admit_net_feature_extraction():
    """Verify feature extractor transforms raw applicant profile into 7-dim structured vector."""
    predictor = get_admit_predictor()
    student = {
        "undergrad_tier": "985",
        "undergrad_name": "清华大学",
        "gpa_raw": "3.85/4.0",
        "major": "计算机科学与技术",
        "language_scores": {"IELTS_total": 7.5, "speaking": 7.0},
        "research_experiences": ["微软STCA实习", "分布式系统一作论文在投"],
    }
    program = {
        "id": "cmu_msit_se",
        "university_id": "cmu",
        "major_category": "CS",
        "gpa_min_4_0": 3.6,
        "min_ielts": {"total": 7.5, "subscore": 7.0},
        "tier_bracket": "Reach",
    }

    feat = predictor.extract_features(student, program)
    assert isinstance(feat, np.ndarray)
    assert feat.shape == (7,)
    assert feat[0] == 1.0  # Tsinghua -> tier score 1.0
    assert 0.95 <= feat[1] <= 1.0  # 3.85 / 4.0 = 0.9625
    assert feat[2] > 0.0  # GPA exceeds minimum
    assert feat[3] == 0.0  # Language exactly matches min requirement
    assert feat[4] > 0.90  # CS -> CS major high prereq coverage
    assert feat[5] > 0.70  # Microsoft intern + first-author paper boost
    assert feat[6] > 0.90  # CMU reach selectivity


def test_admit_net_training_and_persistence():
    """Verify AdmitNet trains cleanly, achieves high metrics, and persists to JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_weights = os.path.join(tmpdir, "test_admit_net.json")
        predictor = PrismAdmitPredictor(weights_path=tmp_weights)
        metrics = predictor.train_and_save(save_path=tmp_weights, epochs=150)

        assert os.path.exists(tmp_weights)
        assert metrics["accuracy"] >= 0.80
        assert metrics["roc_auc"] >= 0.85

        # Verify weights can be reloaded
        reloaded = PrismAdmitPredictor(weights_path=tmp_weights)
        assert reloaded.is_trained
        assert len(reloaded.weights) in [7, 8]
        assert reloaded.weights[6] < 0  # Selectivity weight is strictly negative
        assert all(w > 0 for w in reloaded.weights[:6])  # Positive features have positive weights
        if len(reloaded.weights) > 7:
            assert reloaded.weights[7] > 0  # Synergy weight is strictly positive


def test_admit_net_strict_gpa_monotonicity():
    """Verify that holding all other features fixed, higher GPA strictly increases admit probability."""
    predictor = get_admit_predictor()
    base_feat = np.array([0.88, 3.0 / 4.0, (3.0 - 3.5) / 4.0, 0.0, 0.85, 0.60, 0.80])

    gpa_ladder = [3.0, 3.2, 3.4, 3.6, 3.8, 4.0]
    probabilities = []

    for gpa in gpa_ladder:
        feat = np.copy(base_feat)
        feat[1] = gpa / 4.0
        feat[2] = (gpa - 3.5) / 4.0
        p = predictor.predict_proba(feat)
        probabilities.append(p)

    # Monotonicity assertion: every step must be strictly increasing
    for i in range(len(probabilities) - 1):
        assert probabilities[i + 1] > probabilities[i], (
            f"Monotonicity violated: GPA {gpa_ladder[i]} ({probabilities[i]}) >= "
            f"GPA {gpa_ladder[i+1]} ({probabilities[i+1]})"
        )


def test_admit_net_feature_attribution_output():
    """Verify feature attribution produces interpretable percentage impacts and top factors."""
    predictor = get_admit_predictor()
    student = {
        "undergrad_tier": "985",
        "undergrad_name": "浙江大学",
        "gpa_raw": "3.82/4.0",
        "major": "CS",
        "language_scores": {"IELTS_total": 7.5, "speaking": 7.0},
        "research_experiences": ["微软实习", "开源项目核心贡献者"],
    }
    program = {
        "id": "cmu_msit_se",
        "tier_bracket": "Reach",
        "gpa_min_4_0": 3.6,
        "min_ielts": {"total": 7.5, "subscore": 7.0},
    }

    res = predictor.explain_admission(student, program)
    assert "admit_probability" in res
    assert "probability_percent" in res
    assert "tier_bracket" in res
    assert "feature_attributions" in res
    assert "top_positive_factors" in res
    assert "top_negative_factors" in res

    # Probability percent should end with %
    assert res["probability_percent"].endswith("%")
    # Attributions should contain positive signs for student's strong credentials
    attrs = res["feature_attributions"]
    assert any(k in attrs for k in ["院校Tier优势", "GPA门槛优势", "科研与工程实习优势"])
    for val in attrs.values():
        assert val.startswith("+") or val.startswith("-")


# ==============================================================================
# 2. DPO & SFT Dataset Tests
# ==============================================================================

def test_dpo_dataset_integrity_and_anti_ai_guardrail():
    """Verify DPO dataset format, sample count, and zero-tolerance Anti-AI compliance."""
    dpo_path = Path("data/finetune/disperser_dpo_train.jsonl")
    assert dpo_path.exists(), "disperser_dpo_train.jsonl does not exist"

    guardrail = AntiAIGuardrail()
    count = 0

    with open(dpo_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            assert "prompt" in data and len(data["prompt"]) > 20
            assert "chosen" in data and len(data["chosen"]) > 20
            assert "rejected" in data and len(data["rejected"]) > 20

            # Chosen MUST have ZERO banned words
            chosen_hits = guardrail.scan(data["chosen"])
            assert len(chosen_hits) == 0, f"Sample {idx} chosen contains banned words: {chosen_hits}"

            # Rejected MUST contain at least one banned AI cliché
            rejected_hits = guardrail.scan(data["rejected"])
            assert len(rejected_hits) > 0, f"Sample {idx} rejected is missing banned AI words"

            count += 1

    assert count >= 200, f"Expected >= 200 DPO samples, got {count}"


def test_router_sft_dataset_schema_compliance():
    """Verify Router SFT dataset messages format and valid LuminaryDecision JSON parsing."""
    sft_path = Path("data/finetune/luminary_sft_train.jsonl")
    assert sft_path.exists(), "luminary_sft_train.jsonl does not exist"

    count = 0
    decisions_seen = set()

    with open(sft_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            assert "messages" in data
            messages = data["messages"]
            assert len(messages) == 3
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            assert messages[2]["role"] == "assistant"

            # Assistant content MUST parse strictly into LuminaryDecision
            assistant_content = messages[2]["content"]
            decision = LuminaryDecision.model_validate_json(assistant_content)
            assert decision.routing_decision in ["ASK_FOR_CLARIFICATION", "DELEGATE_TO_AGENT", "DIRECT_ANSWER"]
            decisions_seen.add(decision.routing_decision)

            count += 1

    assert count >= 200, f"Expected >= 200 SFT samples, got {count}"
    assert "DELEGATE_TO_AGENT" in decisions_seen
    assert "ASK_FOR_CLARIFICATION" in decisions_seen


# ==============================================================================
# 3. Training Script Dry-Run Tests
# ==============================================================================

def test_training_pipeline_dry_run():
    """Verify execute_dry_run parameter calculations and adapter configuration saving."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test DPO dry-run
        dpo_summary = execute_dry_run(
            stage="dpo",
            model_name="Qwen/Qwen2.5-7B-Instruct",
            train_file="data/finetune/disperser_dpo_train.jsonl",
            output_dir=os.path.join(tmpdir, "dpo"),
            lora_rank=16,
            lora_alpha=32,
            epochs=3,
            batch_size=2,
            learning_rate=5e-6,
        )
        assert dpo_summary["status"] == "DRY_RUN_SUCCESS"
        assert dpo_summary["stage"] == "DPO"
        assert os.path.exists(os.path.join(tmpdir, "dpo", "adapter_config.json"))

        # Test SFT dry-run
        sft_summary = execute_dry_run(
            stage="sft",
            model_name="Qwen/Qwen2.5-1.5B-Instruct",
            train_file="data/finetune/luminary_sft_train.jsonl",
            output_dir=os.path.join(tmpdir, "sft"),
            lora_rank=16,
            lora_alpha=32,
            epochs=3,
            batch_size=4,
            learning_rate=1e-4,
        )
        assert sft_summary["status"] == "DRY_RUN_SUCCESS"
        assert sft_summary["stage"] == "SFT"
        assert os.path.exists(os.path.join(tmpdir, "sft", "adapter_config.json"))


# ==============================================================================
# 4. Toolchain & Agent Integration Tests
# ==============================================================================

def test_search_peer_admission_cases_with_ml_evaluation():
    """Verify search_peer_admission_cases delivers ML probabilities and feature attributions."""
    peer_data = search_peer_admission_cases(
        undergrad_tier="985",
        gpa=3.80,
        major="CS",
        target_program_id="cmu_msit_se",
    )
    assert "peer_median_gpa" in peer_data
    assert "acceptance_rate_range" in peer_data
    assert "bracket_recommendation" in peer_data
    assert "admit_probability" in peer_data
    assert "probability_percent" in peer_data
    assert "feature_attributions" in peer_data
    assert isinstance(peer_data["feature_attributions"], dict)


def test_locus_node_with_admit_net_cards():
    """Verify locus_node renders Prism-AdmitNet probabilities and feature attributions in cards."""
    state = {
        "student_profile": {
            "undergrad_tier": "985",
            "undergrad_name": "浙江大学",
            "gpa_raw": "3.82/4.0",
            "target_regions": ["US", "UK"],
            "target_majors": ["CS"],
            "language_scores": {"IELTS_total": 7.5, "speaking": 7.0},
            "research_experiences": ["微软实习", "分布式系统科研"],
        }
    }
    result = locus_node(state)
    latest_resp = result["latest_response"]

    assert "Prism-AdmitNet 预估录取率" in latest_resp
    assert "特征归因拆解 (Feature Attribution)" in latest_resp
    assert "棱镜三级选校矩阵" in latest_resp


# ==============================================================================
# 5. Milestone 4.5: Exact Additivity, What-If Sandbox & Evaluation Tests
# ==============================================================================

def test_admit_net_exact_additivity_identity():
    """Verify mathematical identity: round(base_probability + sum(attributions.values()), 4) == round(predicted_probability, 4)."""
    predictor = get_admit_predictor()

    test_cases = [
        # 1. 985 top applicant
        (
            {"undergrad_tier": "985", "gpa_raw": "3.88/4.0", "major": "CS", "language_scores": {"IELTS_total": 8.0, "speaking": 7.5}},
            {"id": "cmu_msit_se", "tier_bracket": "Reach", "gpa_min_4_0": 3.6}
        ),
        # 2. 211 moderate applicant
        (
            {"undergrad_tier": "211", "gpa_raw": "3.55/4.0", "major": "DS", "language_scores": {"IELTS_total": 7.0, "speaking": 6.5}},
            {"id": "nyu_ms_ds", "tier_bracket": "Match", "gpa_min_4_0": 3.5}
        ),
        # 3. Double-non applicant
        (
            {"undergrad_tier": "双非一本", "gpa_raw": "3.30/4.0", "major": "EE", "language_scores": {"IELTS_total": 6.5, "speaking": 6.0}},
            {"id": "usc_cs37", "tier_bracket": "Match", "gpa_min_4_0": 3.4}
        ),
        # 4. Overseas applicant
        (
            {"undergrad_tier": "海本", "gpa_raw": "3.75/4.0", "major": "CS", "language_scores": {"IELTS_total": 7.5}},
            {"id": "oxford_msc_cs", "tier_bracket": "Reach", "gpa_min_4_0": 3.7}
        )
    ]

    for student, program in test_cases:
        eval_res = predictor.explain_admission(student, program)
        base_p = eval_res["base_probability"]
        pred_p = eval_res["predicted_probability"]
        attrs = eval_res["attributions"]

        # Exact Additivity Mathematical Identity Check
        reconstructed = round(base_p + sum(attrs.values()), 4)
        assert reconstructed == round(pred_p, 4), (
            f"Additivity failed for {student['undergrad_tier']} -> {program['id']}: "
            f"base ({base_p}) + sum(attrs) ({sum(attrs.values())}) = {reconstructed} != {pred_p}"
        )


def test_admit_net_confidence_level_and_margin():
    """Verify confidence level categorization and margin of error formatting."""
    predictor = get_admit_predictor()
    student = {
        "undergrad_tier": "985",
        "gpa_raw": "3.80/4.0",
        "major": "CS",
        "language_scores": {"IELTS_total": 7.5, "speaking": 7.0},
    }
    program = {"id": "cmu_msit_se", "tier_bracket": "Reach"}

    res = predictor.explain_admission(student, program, matched_case_count=12)
    assert res["confidence_level"] in ["high", "medium", "low"]
    assert res["margin_of_error"].startswith("±")
    assert "%" in res["margin_of_error"]

    ci = res["confidence_interval"]
    assert len(ci) == 2
    assert 0.0 <= ci[0] <= ci[1] <= 1.0


def test_what_if_simulation_endpoint():
    """Verify POST /api/ml/simulate-what-if returns valid delta, transition and attribution changes."""
    from fastapi.testclient import TestClient
    from prismera.api.server import app

    client = TestClient(app)
    payload = {
        "student_profile": {
            "undergrad_tier": "211",
            "undergrad_name": "北京邮电大学",
            "gpa_raw": "3.50/4.0",
            "major": "CS",
            "language_scores": {"IELTS_total": 6.5, "speaking": 6.0},
            "research_experiences": []
        },
        "target_program_id": "cmu_msit_se",
        "simulated_gpa_delta": 0.35,
        "simulated_lang_score": 7.5,
        "added_research_tier": "top_lab"
    }

    response = client.post("/api/ml/simulate-what-if", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    sim = data["simulation"]
    assert sim["simulated_probability"] > sim["original_probability"]
    assert sim["probability_delta"] > 0
    assert sim["probability_delta_percent"].startswith("+")

    transition = sim["bracket_transition"]
    assert "from_bracket" in transition
    assert "to_bracket" in transition
    assert isinstance(transition["is_promoted"], bool)

    changes = sim["attribution_changes"]
    assert len(changes) > 0
    for dim_data in changes.values():
        assert "old" in dim_data
        assert "new" in dim_data
        assert "delta" in dim_data


def test_eval_finetuned_benchmarking_tool():
    """Verify eval_finetuned comparative benchmarking and report generation."""
    from prismera.ml.llm_finetune.eval_finetuned import (
        evaluate_router_models,
        evaluate_deai_dpo_models,
        run_comprehensive_evaluation,
    )

    router_eval = evaluate_router_models("data/finetune/luminary_sft_train.jsonl", num_samples=20)
    assert router_eval["sft_model"]["schema_valid_rate"] >= 95.0
    assert router_eval["sft_model"]["avg_latency_ms"] < router_eval["baseline_model"]["avg_latency_ms"]

    dpo_eval = evaluate_deai_dpo_models("data/finetune/disperser_dpo_train.jsonl", num_samples=20)
    assert dpo_eval["dpo_model"]["deai_win_rate"] >= 80.0
    assert dpo_eval["dpo_model"]["banned_words_per_sample"] == 0.0

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_comprehensive_evaluation(output_dir=tmpdir, num_samples=15)
        assert os.path.exists(os.path.join(tmpdir, "eval_finetuned_report.json"))
        assert os.path.exists(os.path.join(tmpdir, "EVAL_FINETUNED.md"))
        assert report["router_evaluation"]["sft_model"]["schema_valid_rate"] >= 95.0


# ==============================================================================
# 5. Milestone 4.8 Tests: Conformal MoE, Recourse & Anti-Hallucination
# ==============================================================================

def test_continuous_conformal_moe_bounds():
    """Verify continuous conformal margin of error formula and interval clamping [0.02, 0.15]."""
    predictor = get_admit_predictor()
    student = {
        "undergrad_tier": "985",
        "gpa_raw": "3.65/4.0",
        "major": "CS",
        "language_scores": {"IELTS_total": 7.0},
    }
    program = {
        "id": "cmu_msit_se",
        "tier_bracket": "Reach",
        "gpa_min_4_0": 3.6,
        "selectivity_index": 0.92,
    }

    # Test across various sample counts N
    for n_cases in [0, 5, 25, 100]:
        res = predictor.explain_admission(student, program, matched_case_count=n_cases)
        moe_str = res["margin_of_error"]
        assert moe_str.startswith("±") and moe_str.endswith("%")
        moe_val = float(moe_str[1:-1]) / 100.0

        # Must strictly adhere to [0.02, 0.15]
        assert 0.02 <= moe_val <= 0.15, f"MoE {moe_val} outside [0.02, 0.15]"

        ci = res["confidence_interval"]
        assert 0.0 <= ci[0] <= ci[1] <= 1.0

    # With higher case count N, margin of error should decrease
    res_sparse = predictor.explain_admission(student, program, matched_case_count=0)
    res_dense = predictor.explain_admission(student, program, matched_case_count=50)
    moe_sparse = float(res_sparse["margin_of_error"][1:-1])
    moe_dense = float(res_dense["margin_of_error"][1:-1])
    assert moe_dense < moe_sparse


def test_overqualified_yield_risk_detection():
    """Verify Yield Protection risk is flagged when high-profile student targets safety program."""
    predictor = get_admit_predictor()

    high_profile_student = {
        "undergrad_tier": "985",
        "undergrad_name": "清华大学",
        "gpa_raw": "3.92/4.0",
        "major": "CS",
        "language_scores": {"IELTS_total": 8.0},
        "research_experiences": ["微软实习", "CCF-A论文一作在投"],
    }
    low_selectivity_program = {
        "id": "safety_univ_it",
        "name": "Local State University MSIT",
        "tier_bracket": "Safety",
        "gpa_min_4_0": 3.0,
        "selectivity_index": 0.25,
    }

    res = predictor.explain_admission(high_profile_student, low_selectivity_program)
    assert res["overqualified_yield_risk"] is True
    assert res["yield_risk_warning"] is not None
    assert "Yield Protection" in res["yield_risk_warning"]

    # Normal reach program should NOT trigger overqualified yield risk
    reach_program = {
        "id": "cmu_msit_se",
        "name": "CMU MSIT-SE",
        "tier_bracket": "Reach",
        "gpa_min_4_0": 3.7,
        "selectivity_index": 0.95,
    }
    res_reach = predictor.explain_admission(high_profile_student, reach_program)
    assert res_reach["overqualified_yield_risk"] is False
    assert res_reach["yield_risk_warning"] is None


def test_what_if_physical_feasibility_and_recourse_roi():
    """Verify What-If recourse planner enforces credit limits and produces sorted time-ROI priority."""
    predictor = get_admit_predictor()
    student = {
        "undergrad_tier": "211",
        "gpa_raw": "3.50/4.0",
        "major": "CS",
        "language_scores": {"IELTS_total": 6.5},
        "research_experiences": [],
    }
    program = {
        "id": "cmu_msit_se",
        "tier_bracket": "Reach",
        "gpa_min_4_0": 3.6,
        "selectivity_index": 0.90,
    }

    # Senior student with only 15% credits remaining cannot physically increase GPA by +0.30
    sim = predictor.simulate_what_if(
        student_profile=student,
        program=program,
        simulated_gpa_delta=0.30,
        simulated_lang_score=7.5,
        added_research_tier="first_author_paper",
        months_remaining=2,  # Only 2 months left
        current_semester="大四上",
    )

    # 1. Feasibility warnings triggered
    assert len(sim["feasibility_warnings"]) >= 2
    assert any("物理上限" in w for w in sim["feasibility_warnings"])
    assert any("周期通常需" in w or "时间不足" in w for w in sim["feasibility_warnings"])
    assert sim["max_feasible_gpa_delta"] <= 0.10

    # 2. Actionable Recourse Marginal Time ROI priority is calculated and sorted
    recourse_list = sim["recommended_action_priority"]
    assert len(recourse_list) >= 3
    # Check sorted strictly descending
    for i in range(len(recourse_list) - 1):
        assert recourse_list[i]["roi_score"] >= recourse_list[i + 1]["roi_score"]
        assert "time_cost_months" in recourse_list[i]
        assert "roi_label" in recourse_list[i]


def test_dpo_number_faithfulness_and_structured_slots():
    """Verify anti-hallucination metric checker and structured evidence slot validation."""
    from prismera.ml.llm_finetune.eval_finetuned import check_number_faithfulness

    # Case 1: Prompt provides explicit metrics -> faithful repetition is valid
    prompt_with_metric = "学生主导完成系统优化，成果包括 34% tail latency reduction under 10,000 QPS load。"
    resp_faithful = "In engineering our store, I achieved 34% tail latency reduction under 10,000 QPS load."
    assert check_number_faithfulness(prompt_with_metric, resp_faithful) is True

    # Case 2: Prompt omits metric, response uses compliant slot -> valid
    prompt_without_metric = "学生参与分布式系统重构，攻坚锁竞争。目前未提供实测性能指标。"
    resp_with_slot = "I resolved multi-threaded lock contention, achieving [METRIC: 填入吞吐量提升%与压测基准]."
    assert check_number_faithfulness(prompt_without_metric, resp_with_slot) is True

    # Case 3: Prompt omits metric, response hallucinates fake metric -> flagged unfaithful
    resp_hallucinated = "I resolved multi-threaded lock contention, achieving 99.4% throughput surge under 50,000 QPS."
    assert check_number_faithfulness(prompt_without_metric, resp_hallucinated) is False


