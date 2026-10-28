"""Unit and Integration Tests for Milestone 5.0 Machine Learning & Algorithmic Innovations.

Validates:
  1. Submodular Portfolio Optimizer:
     - Correlated rejection risk modeling breaking independent Bernoulli assumption.
     - Submodular greedy optimization yielding diversified risk-hedging portfolios with higher Sharpe ratio.
  2. Graph Topological Diffuser:
     - Prior propagation via Graph Laplacian smoothing on sparse cases (N < 3).
     - Conformal error margin (MoE) shrinkage through topological info gain.
  3. Pareto Jury Evaluator:
     - Three-dimensional evaluation (Gatekeeper, Scholar, Synergy).
     - 3D Pareto dominance and Hypervolume S-Metric comparison.
  4. End-to-End API and Disperser Integration:
     - POST /api/ml/optimize-portfolio endpoint functionality.
     - Disperser Stage 4 Pareto Jury critique integration.
"""

import pytest
import numpy as np

from prismera.ml.portfolio_optimizer import (
    SubmodularPortfolioOptimizer,
    get_portfolio_optimizer,
)
from prismera.ml.admit_predictor import (
    get_admit_predictor,
    GraphTopologicalDiffuser,
)
from prismera.ml.llm_finetune.pareto_jury import (
    ParetoJuryEvaluator,
    get_pareto_jury,
)


# ==============================================================================
# 1. Submodular Portfolio Optimizer Tests
# ==============================================================================

def test_correlated_rejection_risk_superadditive():
    """Verify correlated risk modeling reveals hidden rejection risk compared to independent assumption."""
    optimizer = get_portfolio_optimizer()
    student = {
        "undergrad_tier": "985",
        "gpa_raw": "3.65/4.0",
        "major": "CS",
    }

    # Highly homogeneous portfolio: 4 US Top-10 Reach CS programs sharing same bottlenecks
    homogeneous_portfolio = [
        {"id": "cmu_msit_se", "institution": "cmu", "tier_bracket": "Reach", "admit_probability": 0.25, "region": "US", "selectivity_index": 0.95},
        {"id": "stanford_cs", "institution": "stanford", "tier_bracket": "Reach", "admit_probability": 0.18, "region": "US", "selectivity_index": 0.96},
        {"id": "columbia_cs", "institution": "columbia", "tier_bracket": "Reach", "admit_probability": 0.32, "region": "US", "selectivity_index": 0.92},
        {"id": "berkeley_eecs", "institution": "berkeley", "tier_bracket": "Reach", "admit_probability": 0.20, "region": "US", "selectivity_index": 0.95},
    ]

    homo_eval = optimizer.evaluate_portfolio(homogeneous_portfolio, student)

    # Correlated rejection risk must be strictly higher than independent rejection risk
    assert homo_eval["correlated_rejection_risk"] > homo_eval["independent_rejection_risk"]
    assert homo_eval["risk_underestimation_gap"] > 0.0
    assert homo_eval["average_correlation"] >= 0.40  # Strong positive bottleneck correlation

    # Diversified portfolio: spread across US, UK, SG, and EU across Reach/Match/Safety
    diversified_portfolio = [
        {"id": "cmu_msit_se", "institution": "cmu", "tier_bracket": "Reach", "admit_probability": 0.25, "region": "US", "selectivity_index": 0.95},
        {"id": "imperial_ai", "institution": "imperial", "tier_bracket": "Match", "admit_probability": 0.58, "region": "UK", "selectivity_index": 0.65},
        {"id": "nus_mcomp", "institution": "nus", "tier_bracket": "Match", "admit_probability": 0.65, "region": "SG", "selectivity_index": 0.55},
        {"id": "nyu_ds", "institution": "nyu", "tier_bracket": "Safety", "admit_probability": 0.88, "region": "US", "selectivity_index": 0.25},
    ]

    div_eval = optimizer.evaluate_portfolio(diversified_portfolio, student)

    # Diversified portfolio should have lower rejection risk and higher Sharpe ratio
    assert div_eval["correlated_rejection_risk"] < homo_eval["correlated_rejection_risk"]
    assert div_eval["prob_at_least_one_offer"] > homo_eval["prob_at_least_one_offer"]
    assert div_eval["portfolio_sharpe_ratio"] > homo_eval["portfolio_sharpe_ratio"]
    assert div_eval["average_correlation"] < homo_eval["average_correlation"]


def test_submodular_greedy_optimization_selection():
    """Verify submodular greedy optimization selects optimal K-program risk-hedging portfolio."""
    optimizer = get_portfolio_optimizer()
    student = {
        "undergrad_tier": "985",
        "gpa_raw": "3.70/4.0",
        "major": "CS",
    }

    candidate_pool = [
        {"id": "cmu_msit_se", "name": "CMU MSIT-SE", "institution": "cmu", "tier_bracket": "Reach", "admit_probability": 0.28, "region": "US", "selectivity_index": 0.95},
        {"id": "stanford_cs", "name": "Stanford MSCS", "institution": "stanford", "tier_bracket": "Reach", "admit_probability": 0.16, "region": "US", "selectivity_index": 0.97},
        {"id": "columbia_cs", "name": "Columbia MSCS", "institution": "columbia", "tier_bracket": "Match", "admit_probability": 0.50, "region": "US", "selectivity_index": 0.70},
        {"id": "imperial_ai", "name": "Imperial MSc AI", "institution": "imperial", "tier_bracket": "Match", "admit_probability": 0.62, "region": "UK", "selectivity_index": 0.65},
        {"id": "nus_mcomp", "name": "NUS MComp", "institution": "nus", "tier_bracket": "Match", "admit_probability": 0.68, "region": "SG", "selectivity_index": 0.55},
        {"id": "eth_robotics", "name": "ETH Zurich RSC", "institution": "eth", "tier_bracket": "Reach", "admit_probability": 0.35, "region": "EU", "selectivity_index": 0.90},
        {"id": "nyu_ds", "name": "NYU MSDS", "institution": "nyu", "tier_bracket": "Safety", "admit_probability": 0.86, "region": "US", "selectivity_index": 0.30},
        {"id": "ucl_comp", "name": "UCL MSc CS", "institution": "ucl", "tier_bracket": "Safety", "admit_probability": 0.82, "region": "UK", "selectivity_index": 0.35},
    ]

    k = 5
    res = optimizer.optimize_portfolio(candidate_pool, student_profile=student, k_budget=k)

    optimal_list = res["optimal_portfolio"]
    assert len(optimal_list) == k

    # Ensure no duplicates
    opt_ids = [p["id"] for p in optimal_list]
    assert len(set(opt_ids)) == k

    # Verify balanced portfolio (should not be all Reach or all Safety)
    brackets = [p["tier_bracket"] for p in optimal_list]
    assert "Reach" in brackets
    assert "Match" in brackets
    assert "Safety" in brackets

    # Verify metrics
    metrics = res["optimal_metrics"]
    assert metrics["prob_at_least_one_offer"] >= 0.90
    assert metrics["portfolio_sharpe_ratio"] >= 1.5
    assert len(res["optimization_trace"]) == k
    assert "次模对冲黄金组合配置" in res["recommendations"]


# ==============================================================================
# 2. Graph Topological Diffuser Tests
# ==============================================================================

def test_graph_topological_diffuser_sparse_nodes():
    """Verify Graph Laplacian prior diffusion on cold-start sparse nodes (N < 3)."""
    predictor = get_admit_predictor()
    student = {
        "undergrad_tier": "985",
        "gpa_raw": "3.80/4.0",
        "major": "CS",
    }
    program = {
        "id": "cmu_msit_se",
        "name_cn": "卡耐基梅隆大学 - 软件工程理学硕士",
        "institution": "cmu",
        "major_category": "CS",
        "tier_bracket": "Reach",
        "selectivity_index": 0.95,
    }

    # Case 1: Sparse node with 0 historical cases
    res_sparse = predictor.explain_admission(student, program, matched_case_count=0)
    assert res_sparse["graph_diffusion_applied"] is True
    assert res_sparse["effective_case_count"] > 0
    assert len(res_sparse["diffusion_source_neighbors"]) > 0
    assert res_sparse["moe_reduction"] > 0.0

    # Diffused error margin must be strictly lower than raw non-diffused margin
    raw_moe_0 = 0.09 / np.sqrt(0 + 1) + 0.05 * float(np.linalg.norm(np.array(res_sparse["feature_vector"]) - predictor.baseline_profile))
    assert res_sparse["margin_of_error_val"] < raw_moe_0

    # Case 2: Dense node with 12 historical cases -> no diffusion needed
    res_dense = predictor.explain_admission(student, program, matched_case_count=12)
    assert res_dense["graph_diffusion_applied"] is False
    assert res_dense["effective_case_count"] == 12.0
    assert len(res_dense["diffusion_source_neighbors"]) == 0
    assert res_dense["moe_reduction"] == 0.0


# ==============================================================================
# 3. Pareto Jury Evaluator Tests
# ==============================================================================

def test_pareto_jury_three_axes_and_dominance():
    """Verify Admissions Committee 3D Pareto evaluation and Hypervolume S-Metric."""
    jury = get_pareto_jury()

    target_program = {
        "institution": "Carnegie Mellon University",
        "program": "MS in Information Technology - Software Engineering (MSIT-SE)",
    }

    # High-quality grounded draft (Show-Don't-Tell, course codes, active systems verbs)
    strong_draft = (
        "In engineering our Raft-replicated key-value store, I profiled lock contention across asynchronous "
        "gRPC channels, achieving 34% tail latency reduction under 10,000 QPS load. When scaling the benchmark "
        "cluster across 8 nodes, I refactored the concurrent ring buffer to avoid lock contention. At Carnegie Mellon "
        "University's MSIT-SE, I intend to build upon this empirical foundation through 17-651 (Models of Software Systems), "
        "formalizing distributed invariants under the guidance of Prof. David Garlan."
    )

    strong_eval = jury.evaluate_draft(strong_draft, target_program=target_program)
    assert strong_eval["gatekeeper_score"] >= 85.0
    assert strong_eval["scholar_score"] >= 80.0
    assert strong_eval["synergy_score"] >= 80.0
    assert strong_eval["pareto_hypervolume"] >= 30.0
    assert strong_eval["is_pareto_optimal"] is True

    # Cliché-heavy plastic AI draft (banned words, no technical rigor, no course codes)
    weak_draft = (
        "My unwavering passion for computer science inspired me to embark on a transformative journey to delve into "
        "the rich tapestry of software engineering. This endeavor stands as a shining testament to my ambition. "
        "At this esteemed university, I desire to immerse myself in the profound realm of research."
    )

    weak_eval = jury.evaluate_draft(weak_draft, target_program=target_program)
    assert weak_eval["gatekeeper_score"] < 50.0
    assert weak_eval["scholar_score"] < 50.0
    assert weak_eval["synergy_score"] < 50.0
    assert weak_eval["pareto_hypervolume"] < 5.0
    assert weak_eval["is_pareto_optimal"] is False

    # Dominance assertion
    assert jury.dominates(strong_eval, weak_eval) is True
    assert jury.dominates(weak_eval, strong_eval) is False


# ==============================================================================
# 4. API Endpoint Integration Test
# ==============================================================================

def test_api_optimize_portfolio_endpoint():
    """Verify POST /api/ml/optimize-portfolio HTTP endpoint returns submodular results."""
    from fastapi.testclient import TestClient
    from prismera.api.server import app

    client = TestClient(app)
    payload = {
        "student_profile": {
            "undergrad_tier": "985",
            "gpa_raw": "3.75/4.0",
            "major": "CS",
        },
        "candidate_programs": [
            {"id": "cmu_msit_se", "name_cn": "卡耐基梅隆大学", "institution": "cmu", "tier_bracket": "Reach", "admit_probability": 0.28, "region": "US"},
            {"id": "imperial_ai", "name_cn": "帝国理工学院", "institution": "imperial", "tier_bracket": "Match", "admit_probability": 0.60, "region": "UK"},
            {"id": "nus_mcomp", "name_cn": "新加坡国立大学", "institution": "nus", "tier_bracket": "Match", "admit_probability": 0.68, "region": "SG"},
            {"id": "nyu_ds", "name_cn": "纽约大学", "institution": "nyu", "tier_bracket": "Safety", "admit_probability": 0.88, "region": "US"},
        ],
        "k_budget": 3,
        "risk_aversion": 1.2,
        "diversity_weight": 0.7,
    }

    response = client.post("/api/ml/optimize-portfolio", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    res = data["result"]
    assert len(res["optimal_portfolio"]) == 3
    assert "prob_at_least_one_offer" in res["optimal_metrics"]
    assert "correlated_rejection_risk" in res["optimal_metrics"]
    assert "portfolio_sharpe_ratio" in res["optimal_metrics"]
    assert len(res["optimization_trace"]) == 3
    assert isinstance(res["correlation_matrix"], list)


# ==============================================================================
# 5. Disperser Stage 4 Pareto Jury Integration Test
# ==============================================================================

def test_disperser_stage4_pareto_jury_critique():
    """Verify Disperser Stage 4 incorporates Pareto Jury critique block and profile state."""
    from prismera.agents.disperser import disperser_node

    initial_state = {
        "student_profile": {
            "undergrad_tier": "985",
            "major": "CS",
            "target_program": "cmu_msit_se",
            "sop_stage": 2,
            "mined_story_fragments": ["分布式系统锁争用优化经历"],
        },
        "messages": [
            {"role": "user", "content": "确认大纲并执笔，开始写初稿"}
        ],
    }

    res = disperser_node(initial_state)
    profile = res["student_profile"]
    assert profile["sop_stage"] == 4
    assert "sop_critique" in profile

    critique = profile["sop_critique"]
    assert "pareto_jury" in critique

    jury_eval = critique["pareto_jury"]
    assert "gatekeeper_score" in jury_eval
    assert "scholar_score" in jury_eval
    assert "synergy_score" in jury_eval
    assert "pareto_hypervolume" in jury_eval

    # Response markdown must contain the Pareto Jury section
    resp_text = res["latest_response"]
    assert "三棱镜陪审团" in resp_text
    assert "门禁官 (Gatekeeper)" in resp_text
    assert "学术博导 (Scholar)" in resp_text
    assert "匹配审查官 (Synergy)" in resp_text
    assert "Pareto Hypervolume" in resp_text


def test_submodular_objective_diminishing_marginal_returns():
    """Verify submodularity: marginal gain of adding item to subset A >= adding to superset B."""
    optimizer = get_portfolio_optimizer()

    prog_a = {"id": "cmu_msit_se", "institution": "cmu", "tier_bracket": "Reach", "admit_probability": 0.28, "region": "US"}
    prog_b = {"id": "columbia_cs", "institution": "columbia", "tier_bracket": "Reach", "admit_probability": 0.32, "region": "US"}
    cand_x = {"id": "stanford_cs", "institution": "stanford", "tier_bracket": "Reach", "admit_probability": 0.18, "region": "US"}

    # Set A has 1 Reach item, Set B = A + {prog_b} (2 Reach items)
    set_a = [prog_a]
    set_b = [prog_a, prog_b]

    gain_a = optimizer.compute_submodular_utility(set_a + [cand_x]) - optimizer.compute_submodular_utility(set_a)
    gain_b = optimizer.compute_submodular_utility(set_b + [cand_x]) - optimizer.compute_submodular_utility(set_b)

    # Diminishing marginal returns: adding cand_x to smaller set A yields higher marginal utility than adding to larger set B
    assert gain_a > gain_b



def test_pareto_hypervolume_monotonicity():
    """Verify Pareto Hypervolume strictly increases when orthogonal jury scores improve."""
    jury = get_pareto_jury()

    base_draft = (
        "In our key-value store, I resolved lock contention, achieving [METRIC: 填入吞吐量提升%]. "
        "At Carnegie Mellon University's MSIT-SE, I will take 17-651 under Prof. David Garlan."
    )
    augmented_draft = (
        "In our Raft-replicated key-value store, I profiled lock contention across asynchronous "
        "gRPC channels, achieving 34% tail latency reduction under 10,000 QPS load. When scaling "
        "the cluster, I refactored the concurrent ring buffer to formalize distributed invariants. "
        "At Carnegie Mellon University's MSIT-SE, I will study 17-651 under Prof. David Garlan."
    )

    ev_base = jury.evaluate_draft(base_draft, target_program={"institution": "Carnegie Mellon University"})
    ev_aug = jury.evaluate_draft(augmented_draft, target_program={"institution": "Carnegie Mellon University"})

    assert ev_aug["scholar_score"] >= ev_base["scholar_score"]
    assert ev_aug["pareto_hypervolume"] >= ev_base["pareto_hypervolume"]


def test_expected_calibration_error_computation():
    """Verify Expected Calibration Error (ECE) metric computation and model calibration quality."""
    from prismera.ml.admit_predictor import compute_expected_calibration_error

    # Case 1: Perfectly calibrated predictions
    y_true = np.array([1, 1, 1, 1, 0, 0, 0, 0, 1, 0])
    y_prob_ideal = np.array([0.9, 0.9, 0.9, 0.9, 0.1, 0.1, 0.1, 0.1, 0.5, 0.5])
    ece_ideal = compute_expected_calibration_error(y_true, y_prob_ideal, n_bins=5)
    assert ece_ideal <= 0.10

    # Case 2: Overconfident miscalibrated predictions
    y_prob_bad = np.array([0.1, 0.1, 0.1, 0.1, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9])
    ece_bad = compute_expected_calibration_error(y_true, y_prob_bad, n_bins=5)
    assert ece_bad > 0.50

    # Case 3: Trained AdmitNet ECE in metrics
    predictor = get_admit_predictor()
    assert "expected_calibration_error" in predictor.metrics
    assert predictor.metrics["expected_calibration_error"] <= 0.08


def test_portfolio_yield_risk_discount_and_decomposition():
    """Verify Yield Protection hedging and bottleneck risk decomposition in portfolio optimizer."""
    optimizer = get_portfolio_optimizer()

    portfolio = [
        {"id": "cmu_msit_se", "institution": "cmu", "tier_bracket": "Reach", "admit_probability": 0.25, "region": "US"},
        {"id": "columbia_cs", "institution": "columbia", "tier_bracket": "Match", "admit_probability": 0.55, "region": "US"},
        {"id": "local_it", "institution": "local", "tier_bracket": "Safety", "admit_probability": 0.88, "region": "US", "overqualified_yield_risk": True},
    ]

    res = optimizer.evaluate_portfolio(portfolio)
    assert res["yield_protection_risk_count"] == 1
    assert "bottleneck_decomposition" in res
    decomp = res["bottleneck_decomposition"]
    assert "regional_concentration_pct" in decomp
    assert "selectivity_bunching_pct" in decomp


def test_multi_draft_pareto_non_dominated_ranking():
    """Verify Goldberg Fast Non-Dominated Sorting across multiple draft versions."""
    jury = get_pareto_jury()

    draft_v1_cliche = (
        "My unwavering passion has inspired me to embark on a transformative journey to delve into the rich "
        "tapestry of computer science. This stands as a shining testament to my dedication."
    )
    draft_v2_strong = (
        "In our Raft-replicated key-value store, I profiled lock contention across asynchronous gRPC channels, "
        "achieving 34% tail latency reduction under 10,000 QPS load. When scaling across 8 nodes, I refactored the "
        "concurrent ring buffer to formalize invariants under Prof. David Garlan in 17-651."
    )
    draft_v3_moderate = (
        "During my internship, I resolved thread lock contention, achieving [METRIC: 填入延迟降低%]. "
        "I plan to study 17-651 at Carnegie Mellon University."
    )

    items = [
        {"id": "v1.0", "label": "初稿 (Plastic AI)", "content": draft_v1_cliche},
        {"id": "v2.0", "label": "二稿 (Show-Don't-Tell)", "content": draft_v2_strong},
        {"id": "v3.0", "label": "三稿 (Balanced Outline)", "content": draft_v3_moderate},
    ]

    ranking = jury.rank_drafts_pareto(items, target_program={"institution": "Carnegie Mellon University"})
    assert ranking["total_evaluated"] == 3
    assert len(ranking["pareto_front"]) >= 1

    # v2.0 should be Level 1 Pareto optimal
    front_ids = [d["id"] for d in ranking["pareto_front"]]
    assert "v2.0" in front_ids

    # Dominance matrix verification
    matrix = ranking["dominance_matrix"]
    assert matrix["v2.0"]["v1.0"] is True   # v2.0 strictly dominates v1.0
    assert matrix["v1.0"]["v2.0"] is False  # v1.0 cannot dominate v2.0
    assert "tradeoff_analysis" in ranking


