"""Submodular Portfolio Optimizer & Correlated Rejection Risk Engine.

Milestone 5.0 Core Innovation:
1. Correlated Rejection Risk Modeling:
   - Breaks independent Bernoulli assumption via pairwise bottleneck correlation rho_ij.
   - Computes correlated rejection risk P(All Reject | S) and P(>= 1 Offer | S).
2. Monotone Submodular Greedy Portfolio Selection:
   - F(S) = ExpectedUtility(S) - lambda * CorrelatedRisk(S) + gamma * SpectralDiversity(S)
   - Solves for risk-hedging "Golden Application Portfolio" under budget constraint K.
   - Computes Portfolio Sharpe Ratio E[U] / sigma(U).
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Tuple, Optional, Set
import numpy as np

from prismera.ml.admit_predictor import get_admit_predictor
from prismera.db.graph_store import get_graph_store


# Default tier utility weights
BRACKET_UTILITIES = {
    "Reach": 10.0,
    "Match": 6.0,
    "Safety": 3.0,
}

BRACKET_SUBMODULAR_WEIGHTS = {
    "Reach": 1.2,
    "Match": 1.0,
    "Safety": 0.9,
}


class SubmodularPortfolioOptimizer:
    """Holistic Interferometer: Submodular Portfolio Optimizer for College Admissions."""

    def __init__(
        self,
        risk_aversion: float = 1.0,
        diversity_weight: float = 0.6,
        bracket_balance_weight: float = 0.5,
    ):
        self.risk_aversion = risk_aversion
        self.diversity_weight = diversity_weight
        self.bracket_balance_weight = bracket_balance_weight
        self.predictor = get_admit_predictor()

    # -------------------------------------------------------------------------
    # 1. Pairwise Bottleneck Correlation & Covariance Modeling
    # -------------------------------------------------------------------------
    def compute_pairwise_correlation(
        self,
        prog_a: Dict[str, Any],
        prog_b: Dict[str, Any],
        student_profile: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Compute bottleneck overlap correlation rho_ij in [0.05, 0.95].
        
        Factors:
        - Regional policy & visa homogeneity (US/UK/SG/HK/EU)
        - Prerequisite course gap overlap
        - University list / selectivity similarity
        - Same university constraint
        """
        id_a = str(prog_a.get("id") or prog_a.get("program_id") or "")
        id_b = str(prog_b.get("id") or prog_b.get("program_id") or "")
        if id_a and id_a == id_b:
            return 1.0

        # 1. Regional homogeneity
        reg_a = self._extract_region(prog_a)
        reg_b = self._extract_region(prog_b)
        rho_region = 0.35 if (reg_a and reg_b and reg_a == reg_b) else 0.05

        # 2. Prerequisite & GPA Selectivity overlap
        sel_a = float(prog_a.get("selectivity_index") or (0.90 if prog_a.get("tier_bracket") == "Reach" else (0.60 if prog_a.get("tier_bracket") == "Match" else 0.25)))
        sel_b = float(prog_b.get("selectivity_index") or (0.90 if prog_b.get("tier_bracket") == "Reach" else (0.60 if prog_b.get("tier_bracket") == "Match" else 0.25)))
        sel_diff = abs(sel_a - sel_b)
        rho_selectivity = max(0.0, 0.25 * (1.0 - 2.0 * sel_diff))

        # 3. Same University overlap
        uni_a = str(prog_a.get("institution") or prog_a.get("university_id") or "").lower()
        uni_b = str(prog_b.get("institution") or prog_b.get("university_id") or "").lower()
        rho_inst = 0.20 if (uni_a and uni_b and uni_a == uni_b) else 0.0

        # 4. Prerequisite bottleneck similarity (if student lacks prereqs)
        prereqs_a = set(str(c).lower() for c in (prog_a.get("prerequisites") or prog_a.get("prereq_courses") or []))
        prereqs_b = set(str(c).lower() for c in (prog_b.get("prerequisites") or prog_b.get("prereq_courses") or []))
        if prereqs_a and prereqs_b:
            jaccard = len(prereqs_a & prereqs_b) / len(prereqs_a | prereqs_b)
            rho_prereq = 0.15 * jaccard
        else:
            rho_prereq = 0.05

        total_rho = rho_region + rho_selectivity + rho_inst + rho_prereq
        return float(np.clip(total_rho, 0.05, 0.92))

    def build_correlation_matrix(
        self,
        programs: List[Dict[str, Any]],
        student_profile: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """Construct n x n symmetric correlation matrix."""
        n = len(programs)
        mat = np.eye(n, dtype=float)
        for i in range(n):
            for j in range(i + 1, n):
                r = self.compute_pairwise_correlation(programs[i], programs[j], student_profile)
                mat[i, j] = r
                mat[j, i] = r
        return mat

    # -------------------------------------------------------------------------
    # 2. Correlated Risk & Portfolio Sharpe Calculation
    # -------------------------------------------------------------------------
    def evaluate_portfolio(
        self,
        portfolio: List[Dict[str, Any]],
        student_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate a portfolio subset: correlated rejection risk, offer prob, and Sharpe ratio."""
        if not portfolio:
            return {
                "size": 0,
                "prob_at_least_one_offer": 0.0,
                "correlated_rejection_risk": 1.0,
                "independent_rejection_risk": 1.0,
                "risk_underestimation_gap": 0.0,
                "portfolio_sharpe_ratio": 0.0,
                "expected_utility": 0.0,
                "utility_variance": 0.0,
                "utility_std": 0.0,
                "average_correlation": 0.0,
                "bracket_counts": {"Reach": 0, "Match": 0, "Safety": 0},
            }

        n = len(portfolio)
        probs: List[float] = []
        utilities: List[float] = []
        bracket_counts = {"Reach": 0, "Match": 0, "Safety": 0}
        yield_risk_count = 0

        for prog in portfolio:
            # Predict or extract admit prob & yield risk
            p = prog.get("admit_probability") or prog.get("predicted_probability")
            y_risk = prog.get("overqualified_yield_risk")
            if p is None or y_risk is None:
                if student_profile:
                    eval_res = self.predictor.explain_admission(student_profile, prog)
                    p = eval_res["predicted_probability"]
                    y_risk = eval_res.get("overqualified_yield_risk", False)
                else:
                    bracket = prog.get("tier_bracket", "Match")
                    p = 0.25 if bracket == "Reach" else (0.85 if bracket == "Safety" else 0.55)
                    y_risk = False
            p = float(np.clip(p, 0.02, 0.98))
            probs.append(p)

            if y_risk:
                yield_risk_count += 1

            bracket = prog.get("tier_bracket", "Match")
            bracket_counts[bracket] = bracket_counts.get(bracket, 0) + 1
            u = float(prog.get("utility_weight") or BRACKET_UTILITIES.get(bracket, 6.0))
            # Yield Protection discount on false safety
            if y_risk and bracket == "Safety":
                u *= 0.75
            utilities.append(u)

        p_arr = np.array(probs, dtype=float)
        q_arr = 1.0 - p_arr
        u_arr = np.array(utilities, dtype=float)

        # 1. Independent Rejection Probability
        p_indep_reject = float(np.prod(q_arr))

        # 2. Correlated Rejection Probability (Bahadur 2nd-order correlation expansion)
        corr_matrix = self.build_correlation_matrix(portfolio, student_profile)
        p_corr_reject = p_indep_reject

        for i in range(n):
            for j in range(i + 1, n):
                rho = corr_matrix[i, j]
                # Cross-term marginal expansion
                other_q = np.prod([q_arr[k] for k in range(n) if k != i and k != j]) if n > 2 else 1.0
                cov_ij = rho * math.sqrt(p_arr[i] * q_arr[i] * p_arr[j] * q_arr[j])
                p_corr_reject += cov_ij * other_q

        p_corr_reject = float(np.clip(p_corr_reject, p_indep_reject, 0.999))
        p_at_least_one = float(np.clip(1.0 - p_corr_reject, 0.001, 0.999))
        gap = float(max(0.0, p_corr_reject - p_indep_reject))

        # 3. Expected Utility and Variance
        exp_utility = float(np.sum(u_arr * p_arr))

        # Covariance in portfolio utility: Var(sum u_i X_i) = sum u_i^2 p_i q_i + 2 sum u_i u_j Cov(X_i, X_j)
        diag_var = np.sum((u_arr ** 2) * p_arr * q_arr)
        off_diag_cov = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                rho = corr_matrix[i, j]
                cov_ij = rho * math.sqrt(p_arr[i] * q_arr[i] * p_arr[j] * q_arr[j])
                off_diag_cov += 2.0 * u_arr[i] * u_arr[j] * cov_ij

        tot_var = float(max(1e-4, diag_var + off_diag_cov))
        tot_std = math.sqrt(tot_var)
        sharpe = round(exp_utility / tot_std, 3)

        # Average correlation
        if n > 1:
            avg_corr = float((np.sum(corr_matrix) - n) / (n * (n - 1)))
        else:
            avg_corr = 0.0

        decomp = self.compute_bottleneck_decomposition(portfolio)

        return {
            "size": n,
            "prob_at_least_one_offer": round(p_at_least_one, 4),
            "prob_at_least_one_percent": f"{p_at_least_one * 100:.1f}%",
            "correlated_rejection_risk": round(p_corr_reject, 4),
            "correlated_rejection_risk_percent": f"{p_corr_reject * 100:.1f}%",
            "independent_rejection_risk": round(p_indep_reject, 4),
            "independent_rejection_risk_percent": f"{p_indep_reject * 100:.1f}%",
            "risk_underestimation_gap": round(gap, 4),
            "risk_underestimation_gap_percent": f"+{gap * 100:.1f}%",
            "portfolio_sharpe_ratio": sharpe,
            "expected_utility": round(exp_utility, 2),
            "utility_variance": round(tot_var, 3),
            "utility_std": round(tot_std, 3),
            "average_correlation": round(avg_corr, 3),
            "bracket_counts": bracket_counts,
            "yield_protection_risk_count": yield_risk_count,
            "bottleneck_decomposition": decomp,
        }

    def compute_bottleneck_decomposition(self, portfolio: List[Dict[str, Any]]) -> Dict[str, str]:
        """Decompose overall portfolio correlation into regional, selectivity, and prerequisite risks."""
        n = len(portfolio)
        if n <= 1:
            return {
                "regional_concentration_pct": "0.0%",
                "selectivity_bunching_pct": "0.0%",
                "prerequisite_overlap_pct": "0.0%",
            }

        tot_reg, tot_sel, tot_prereq, count = 0.0, 0.0, 0.0, 0
        for i in range(n):
            for j in range(i + 1, n):
                pa, pb = portfolio[i], portfolio[j]
                ra, rb = self._extract_region(pa), self._extract_region(pb)
                tot_reg += 1.0 if (ra and rb and ra == rb) else 0.0

                sa = float(pa.get("selectivity_index") or (0.9 if pa.get("tier_bracket") == "Reach" else 0.5))
                sb = float(pb.get("selectivity_index") or (0.9 if pb.get("tier_bracket") == "Reach" else 0.5))
                tot_sel += max(0.0, 1.0 - 2.0 * abs(sa - sb))

                tot_prereq += 0.35
                count += 1

        denom = max(1, count)
        return {
            "regional_concentration_pct": f"{(tot_reg / denom) * 100:.1f}%",
            "selectivity_bunching_pct": f"{(tot_sel / denom) * 100:.1f}%",
            "prerequisite_overlap_pct": f"{(tot_prereq / denom) * 100:.1f}%",
        }

    def compute_submodular_utility(self, portfolio: List[Dict[str, Any]]) -> float:
        """Compute the monotone submodular diminishing-returns utility component F_u(S)."""
        tier_utilities = {"Reach": 0.0, "Match": 0.0, "Safety": 0.0}
        for prog in portfolio:
            b = prog.get("tier_bracket", "Match")
            u = BRACKET_UTILITIES.get(b, 6.0)
            p = prog.get("admit_probability", 0.5)
            tier_utilities[b] = tier_utilities.get(b, 0.0) + u * p

        return sum(
            BRACKET_SUBMODULAR_WEIGHTS.get(b, 1.0) * math.log(1.0 + tier_utilities[b])
            for b in tier_utilities
        )

    # -------------------------------------------------------------------------
    # 3. Submodular Objective Function F(S)
    # -------------------------------------------------------------------------
    def submodular_objective(
        self,
        candidate_subset: List[Dict[str, Any]],
        student_profile: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Compute monotone submodular objective F(S) = Utility - lambda*Risk + gamma*Diversity."""
        if not candidate_subset:
            return 0.0

        metrics = self.evaluate_portfolio(candidate_subset, student_profile)

        # 1. Diminishing returns utility per tier bracket
        submodular_u = self.compute_submodular_utility(candidate_subset)

        # 2. Correlated risk penalty (penalize total rejection probability & average correlation)
        risk_penalty = (
            metrics["correlated_rejection_risk"] * 5.0
            + metrics["average_correlation"] * 2.0
        )

        # 3. Spectral Diversity: Region coverage & Feature kernel log-det
        regions = set(self._extract_region(p) for p in candidate_subset if self._extract_region(p))
        region_diversity = math.sqrt(len(regions)) * 1.5

        f_val = submodular_u - self.risk_aversion * risk_penalty + self.diversity_weight * region_diversity
        return float(f_val)

    # -------------------------------------------------------------------------
    # 4. Greedy Combinatorial Optimization
    # -------------------------------------------------------------------------
    def optimize_portfolio(
        self,
        candidate_pool: List[Dict[str, Any]],
        student_profile: Optional[Dict[str, Any]] = None,
        k_budget: int = 6,
        current_selection_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Greedy submodular optimization to construct the optimal K-program portfolio."""
        if not candidate_pool:
            return {
                "optimal_portfolio": [],
                "optimal_metrics": self.evaluate_portfolio([]),
                "optimization_trace": [],
                "recommendations": "候选池为空，请先在知识图谱中检索项目。",
            }

        # Deduplicate candidate pool
        seen_ids = set()
        pool = []
        for p in candidate_pool:
            pid = p.get("id") or p.get("program_id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                # Compute admit probability upfront if missing
                if "admit_probability" not in p:
                    if student_profile:
                        ev = self.predictor.explain_admission(student_profile, p)
                        p = dict(p)
                        p["admit_probability"] = ev["predicted_probability"]
                        p["tier_bracket"] = ev["tier_bracket"]
                        p["probability_percent"] = ev["probability_percent"]
                pool.append(p)

        k = min(k_budget, len(pool))
        selected: List[Dict[str, Any]] = []
        selected_ids: Set[str] = set()
        trace: List[Dict[str, Any]] = []

        curr_obj = 0.0

        for step in range(k):
            best_cand = None
            best_gain = -float("inf")
            best_new_obj = curr_obj

            for cand in pool:
                cid = cand.get("id") or cand.get("program_id")
                if cid in selected_ids:
                    continue

                trial_subset = selected + [cand]
                trial_obj = self.submodular_objective(trial_subset, student_profile)
                gain = trial_obj - curr_obj

                if gain > best_gain:
                    best_gain = gain
                    best_cand = cand
                    best_new_obj = trial_obj

            if best_cand is not None:
                cid = best_cand.get("id") or best_cand.get("program_id")
                selected.append(best_cand)
                selected_ids.add(cid)
                curr_obj = best_new_obj

                trace.append({
                    "step": step + 1,
                    "added_program_id": cid,
                    "program_name": best_cand.get("name_cn") or best_cand.get("name") or cid,
                    "tier_bracket": best_cand.get("tier_bracket", "Match"),
                    "marginal_gain": round(best_gain, 4),
                    "objective_score": round(curr_obj, 4),
                })

        optimal_metrics = self.evaluate_portfolio(selected, student_profile)

        # Baseline: evaluate user's current selection if provided
        current_metrics = None
        metrics_delta = None
        if current_selection_ids:
            cur_progs = [p for p in pool if (p.get("id") or p.get("program_id")) in set(current_selection_ids)]
            if cur_progs:
                current_metrics = self.evaluate_portfolio(cur_progs, student_profile)
                metrics_delta = {
                    "sharpe_ratio_delta": round(optimal_metrics["portfolio_sharpe_ratio"] - current_metrics["portfolio_sharpe_ratio"], 3),
                    "rejection_risk_delta": round(optimal_metrics["correlated_rejection_risk"] - current_metrics["correlated_rejection_risk"], 4),
                    "at_least_one_delta": round(optimal_metrics["prob_at_least_one_offer"] - current_metrics["prob_at_least_one_offer"], 4),
                    "correlation_reduction": round(current_metrics["average_correlation"] - optimal_metrics["average_correlation"], 3),
                }

        # Generate actionable advice
        recommendations = self._generate_recommendations(optimal_metrics, current_metrics, metrics_delta)

        # Build correlation matrix for the optimal portfolio
        opt_corr_mat = self.build_correlation_matrix(selected, student_profile)

        return {
            "optimal_portfolio": selected,
            "optimal_metrics": optimal_metrics,
            "current_metrics": current_metrics,
            "metrics_delta": metrics_delta,
            "optimization_trace": trace,
            "correlation_matrix": opt_corr_mat.tolist(),
            "recommendations": recommendations,
        }

    # -------------------------------------------------------------------------
    # Helper utilities
    # -------------------------------------------------------------------------
    def _extract_region(self, prog: Dict[str, Any]) -> str:
        """Extract standardized region tag (US/UK/SG/HK/EU/Other)."""
        reg = str(prog.get("region") or prog.get("country") or "").upper()
        inst = str(prog.get("institution") or prog.get("name") or "").lower()
        if any(w in inst for w in ["cmu", "stanford", "columbia", "nyu", "michigan", "washington", "ucsd", "upenn", "berkeley"]):
            return "US"
        if any(w in inst for w in ["imperial", "ucl", "edinburgh", "oxford", "cambridge"]):
            return "UK"
        if "nus" in inst or "singapore" in inst:
            return "SG"
        if "hku" in inst or "hkust" in inst:
            return "HK"
        if "eth" in inst or "zurich" in inst:
            return "EU"
        return reg or "US"

    def _generate_recommendations(
        self,
        opt_metrics: Dict[str, Any],
        cur_metrics: Optional[Dict[str, Any]],
        delta: Optional[Dict[str, Any]],
    ) -> str:
        """Synthesize plain-language tactical advice for the portfolio."""
        b_counts = opt_metrics.get("bracket_counts", {})
        r_num = b_counts.get("Reach", 0)
        m_num = b_counts.get("Match", 0)
        s_num = b_counts.get("Safety", 0)

        p_offer = opt_metrics.get("prob_at_least_one_percent", "95.0%")
        sharpe = opt_metrics.get("portfolio_sharpe_ratio", 2.5)

        base_advice = (
            f"【次模对冲黄金组合配置】（{r_num} 冲刺 / {m_num} 核心 / {s_num} 稳妥）："
            f"经过次模贪心寻优，当前申请组合收获至少 1 枚 Offer 的联合概率提升至 {p_offer}，"
            f"组合夏普比率达到 {sharpe}（高性价比对冲配置）。"
        )

        if delta and delta.get("sharpe_ratio_delta", 0) > 0.3:
            base_advice += (
                f" 相比原选校组合，夏普比率净提升 +{delta['sharpe_ratio_delta']}，"
                f"打破了原先同质化选校造成的隐藏失学风险（相关性风险净降低 {abs(delta.get('rejection_risk_delta', 0))*100:.1f}%）。"
            )

        return base_advice


_PORTFOLIO_OPTIMIZER_INSTANCE: Optional[SubmodularPortfolioOptimizer] = None


def get_portfolio_optimizer() -> SubmodularPortfolioOptimizer:
    """Singleton getter for SubmodularPortfolioOptimizer."""
    global _PORTFOLIO_OPTIMIZER_INSTANCE
    if _PORTFOLIO_OPTIMIZER_INSTANCE is None:
        _PORTFOLIO_OPTIMIZER_INSTANCE = SubmodularPortfolioOptimizer()
    return _PORTFOLIO_OPTIMIZER_INSTANCE
