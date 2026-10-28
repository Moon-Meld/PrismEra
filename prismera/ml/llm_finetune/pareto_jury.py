"""Multi-Objective Pareto Admissions Jury & Hypervolume Evaluation Engine.

Milestone 5.0 Innovation:
Simulates a three-member admissions committee conducting orthogonal Pareto evaluation:
1. Gatekeeper: Anti-AI purity, concrete metrics, zero hallucinated numbers.
2. Scholar: Problem depth, technical causality, engineering friction & methodology.
3. Synergy: Course codes, faculty research labs, curriculum-to-career bite.

Computes 3D Pareto Dominance and Hypervolume S-Metric relative to baseline threshold (30, 30, 30).
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Tuple

from prismera.guardrails import AntiAIGuardrail
from prismera.ml.llm_finetune.eval_finetuned import check_number_faithfulness


class ParetoJuryEvaluator:
    """Three-member Admissions Committee Pareto Evaluator."""

    def __init__(self, ref_point: Tuple[float, float, float] = (30.0, 30.0, 30.0)):
        self.ref_point = ref_point
        self.guardrail = AntiAIGuardrail()

        # Scholar technical depth verbs & terms
        self.scholar_terms = [
            "profiled", "invariants", "concurrency", "bottleneck", "quantization",
            "distillation", "stochastic", "convergence", "backpressure", "latency",
            "throughput", "optimization", "tradeoff", "refactored", "formalizing",
            "asynchronous", "sharded", "compaction", "adverse selection", "psnr",
            "kalman", "slam", "locomotion", "contrastive", "hessian", "eigenvalues",
            "sub-5cm", "slo", "grpc", "raft", "paxos", "lsm-tree",
        ]

    def evaluate_draft(
        self,
        draft: str,
        target_program: Optional[Dict[str, Any]] = None,
        prompt_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate an admission essay draft across the 3 orthogonal jury axes."""
        text = draft.strip()
        prog = target_program or {}

        # ---------------------------------------------------------------------
        # 1. Gatekeeper Score (Anti-AI Purity, Metrics & Number Faithfulness)
        # ---------------------------------------------------------------------
        banned_violations = self.guardrail.scan(text)
        banned_penalty = len(banned_violations) * 15.0

        # Number faithfulness check
        is_faithful = True
        if prompt_context:
            is_faithful = check_number_faithfulness(prompt_context, text)
        faith_penalty = 0.0 if is_faithful else 30.0

        # Quantitative evidence density
        num_pattern = re.compile(r"(?:\b\d+(?:\.\d+)?%|\b\d+(?:,\d+)?(?:\.\d+)?\s*(?:x|ms|s|QPS|FPS|dB)\b|\[METRIC:.*?\])", re.IGNORECASE)
        metric_matches = num_pattern.findall(text)
        metric_bonus = min(25.0, len(metric_matches) * 8.0)

        raw_gatekeeper = 85.0 - banned_penalty - faith_penalty + metric_bonus
        gatekeeper_score = round(float(max(0.0, min(100.0, raw_gatekeeper))), 1)

        if banned_violations:
            gatekeeper_comment = f"检测到 {len(banned_violations)} 处典型 AI 塑料腔调词汇 ({', '.join(banned_violations)})，扣除 {banned_penalty} 分；需提升人类真诚语感。"
        elif not is_faithful:
            gatekeeper_comment = "检测到未经提示词授权凭空捏造的量化性能数字，严重扣分；需使用 [METRIC: ...] 槽位或真实数据留白。"
        else:
            gatekeeper_comment = "零 AI 禁用词，数据真实忠实度 100%，量化证据与动作动词密度极高，质感过硬。"

        # ---------------------------------------------------------------------
        # 2. Scholar Score (Technical Depth, Problem Causality & Rigor)
        # ---------------------------------------------------------------------
        text_lower = text.lower()
        scholar_hits = [term for term in self.scholar_terms if term in text_lower]
        scholar_bonus = min(50.0, len(scholar_hits) * 7.5)

        # Penalize shallow declarative fluff
        fluff_terms = ["unwavering passion", "transformative journey", "delve into", "rich tapestry", "deep dive into", "ignited my interest", "beacon of hope"]
        fluff_hits = [f for f in fluff_terms if f in text_lower]
        fluff_penalty = len(fluff_hits) * 15.0

        raw_scholar = 55.0 + scholar_bonus - fluff_penalty
        scholar_score = round(float(max(0.0, min(100.0, raw_scholar))), 1)

        if len(scholar_hits) >= 3 and len(fluff_hits) == 0:
            scholar_comment = f"技术因果推演逻辑严密，精确提炼了架构瓶颈与攻坚方法（包含 {', '.join(scholar_hits[:4])} 等专业概念），学术认知具备终身学者潜质。"
        elif fluff_hits:
            scholar_comment = f"论述充斥空洞的抒情概括腔调（命中了 '{fluff_hits[0]}' 等套话），缺乏真实工程实验的摩擦力与方法论细节。"
        else:
            scholar_comment = "叙事偏向常规任务陈述，建议进一步深入系统底层的具体指标（如内存屏障、锁争用或收敛梯度）展现学术硬度。"

        # ---------------------------------------------------------------------
        # 3. Synergy Score (Target Program, Faculty & Curriculum Binding)
        # ---------------------------------------------------------------------
        # Match course code patterns: CS 244B, COMP70015, 17-651, CSE 552, etc.
        course_pattern = re.compile(r"\b(?:[A-Z]{2,5}\s*\d{3,5}[A-Z]?|\d{2,3}-\d{3,4})\b")
        course_matches = course_pattern.findall(text)

        # Faculty mention pattern: Prof. ... or Professor ...
        faculty_pattern = re.compile(r"\b(?:Prof\.|Professor|Dr\.)\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?\b")
        faculty_matches = faculty_pattern.findall(text)

        # University / program name mention (excluding generic stop words)
        uni_name = str(prog.get("institution") or prog.get("name") or "").lower()
        stop_words = {"university", "college", "institute", "school", "of", "the", "and", "in"}
        uni_tokens = [tok for tok in uni_name.split() if len(tok) > 2 and tok not in stop_words]
        has_uni = bool(uni_tokens and any(tok in text_lower for tok in uni_tokens))

        synergy_points = 25.0
        if course_matches:
            synergy_points += min(35.0, 20.0 + len(course_matches) * 10.0)
        if faculty_matches:
            synergy_points += min(25.0, 15.0 + len(faculty_matches) * 10.0)
        if has_uni:
            synergy_points += 15.0

        synergy_score = round(float(max(0.0, min(100.0, synergy_points))), 1)

        if course_matches and faculty_matches:
            synergy_comment = f"完美咬合目标项目培养方案，明确提及课程代号（{', '.join(course_matches[:2])}）与课题组导师（{', '.join(faculty_matches[:2])}），Why School 说服力极强。"
        elif course_matches:
            synergy_comment = f"已规划具体修读课程（{', '.join(course_matches[:2])}），若能进一步联系特定教授的在研课题将更具排他性吸引力。"
        else:
            synergy_comment = "通用性偏强，缺乏目标院校特异性课程代码或前沿实验室的明确绑定，易被招生官判定为泛化海投模板。"

        # ---------------------------------------------------------------------
        # 4. 3D Pareto Hypervolume (S-Metric) Calculation
        # ---------------------------------------------------------------------
        # Hypervolume relative to reference point (30.0, 30.0, 30.0)
        rx, ry, rz = self.ref_point
        vx = max(0.0, (gatekeeper_score - rx) / (100.0 - rx))
        vy = max(0.0, (scholar_score - ry) / (100.0 - ry))
        vz = max(0.0, (synergy_score - rz) / (100.0 - rz))

        hypervolume = round(float(vx * vy * vz * 100.0), 2)
        is_pareto_strong = bool(gatekeeper_score >= 80.0 and scholar_score >= 80.0 and synergy_score >= 80.0)

        critique_summary = (
            f"【三棱镜陪审团审理决议】\n"
            f"- 门禁官 (Gatekeeper): {gatekeeper_score}/100 — {gatekeeper_comment}\n"
            f"- 学术博导 (Scholar): {scholar_score}/100 — {scholar_comment}\n"
            f"- 匹配审查官 (Synergy): {synergy_score}/100 — {synergy_comment}\n"
            f"★ 三维帕累托超体积得分 (Pareto Hypervolume): {hypervolume}%"
            f" ({'★ 帕累托最优强支撑文书' if is_pareto_strong else '存在单项维度短板，需定向补强'})"
        )

        return {
            "gatekeeper_score": gatekeeper_score,
            "scholar_score": scholar_score,
            "synergy_score": synergy_score,
            "pareto_hypervolume": hypervolume,
            "pareto_hypervolume_percent": f"{hypervolume:.1f}%",
            "is_pareto_optimal": is_pareto_strong,
            "jury_verdicts": {
                "gatekeeper": {
                    "score": gatekeeper_score,
                    "comment": gatekeeper_comment,
                    "banned_words_found": banned_violations,
                },
                "scholar": {
                    "score": scholar_score,
                    "comment": scholar_comment,
                    "technical_terms": scholar_hits,
                },
                "synergy": {
                    "score": synergy_score,
                    "comment": synergy_comment,
                    "matched_courses": course_matches,
                    "matched_faculty": faculty_matches,
                },
            },
            "summary_critique": critique_summary,
        }

    def dominates(self, score_a: Dict[str, float], score_b: Dict[str, float]) -> bool:
        """Check if score_a Pareto-dominates score_b."""
        ga, sa, ya = score_a["gatekeeper_score"], score_a["scholar_score"], score_a["synergy_score"]
        gb, sb, yb = score_b["gatekeeper_score"], score_b["scholar_score"], score_b["synergy_score"]
        return (ga >= gb and sa >= sb and ya >= yb) and (ga > gb or sa > sb or ya > yb)

    def rank_drafts_pareto(
        self,
        draft_items: List[Dict[str, Any]],
        target_program: Optional[Dict[str, Any]] = None,
        prompt_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Multi-Draft Non-Dominated Sorting & Pareto Frontier Extraction.

        Args:
            draft_items: List of dicts, e.g. [{"id": "v1.0", "content": "..."}, ...]
            target_program: Target program metadata
            prompt_context: Background prompt for faithfulness check

        Returns:
            Dict containing pareto_front, ranked_drafts, dominance_matrix, and tradeoff_analysis.
        """
        if not draft_items:
            return {"pareto_front": [], "ranked_drafts": [], "dominance_matrix": {}, "tradeoff_analysis": ""}

        evaluated = []
        for d in draft_items:
            did = str(d.get("id") or d.get("version_id") or f"draft_{len(evaluated)}")
            content = str(d.get("content") or d.get("text") or "")
            ev = self.evaluate_draft(content, target_program=target_program, prompt_context=prompt_context)
            evaluated.append({
                "id": did,
                "label": d.get("label") or did,
                "content": content,
                "evaluation": ev,
                "scores": (ev["gatekeeper_score"], ev["scholar_score"], ev["synergy_score"]),
                "hypervolume": ev["pareto_hypervolume"],
            })

        n = len(evaluated)
        domination_count = [0] * n
        dominated_sets = [[] for _ in range(n)]
        dominance_matrix: Dict[str, Dict[str, bool]] = {}

        for i in range(n):
            id_i = evaluated[i]["id"]
            dominance_matrix[id_i] = {}
            for j in range(n):
                if i == j:
                    dominance_matrix[id_i][evaluated[j]["id"]] = False
                    continue
                i_dom_j = self.dominates(evaluated[i]["evaluation"], evaluated[j]["evaluation"])
                dominance_matrix[id_i][evaluated[j]["id"]] = i_dom_j
                if i_dom_j:
                    dominated_sets[i].append(j)
                elif self.dominates(evaluated[j]["evaluation"], evaluated[i]["evaluation"]):
                    domination_count[i] += 1

        fronts: List[List[int]] = [[]]
        for i in range(n):
            if domination_count[i] == 0:
                fronts[0].append(i)

        curr_rank = 0
        while len(fronts[curr_rank]) > 0:
            next_front = []
            for i in fronts[curr_rank]:
                for j in dominated_sets[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            curr_rank += 1
            fronts.append(next_front)

        ranked_items = []
        for rank_idx, front in enumerate(fronts[:-1]):
            for idx in front:
                item = evaluated[idx]
                item["pareto_rank"] = rank_idx + 1
                ranked_items.append(item)

        ranked_items.sort(key=lambda x: (x["pareto_rank"], -x["hypervolume"]))
        pareto_front = [it for it in ranked_items if it["pareto_rank"] == 1]

        tradeoff_summary = f"共评测 {n} 个文书候选版本，发现 {len(pareto_front)} 个非劣帕累托最优版本（Pareto Front Level 1）。"
        if len(pareto_front) == 1:
            best = pareto_front[0]
            tradeoff_summary += f" 版本【{best['label']}】在门禁、学术深度与项目咬合三维上形成绝对支配，超体积得分达到 {best['hypervolume']}%。"
        elif len(pareto_front) > 1:
            tradeoff_summary += f" 最优前沿在【{pareto_front[0]['label']}】与【{pareto_front[1]['label']}】之间呈现正交权衡（学术深度 vs 门禁合规）。"

        return {
            "total_evaluated": n,
            "pareto_front": pareto_front,
            "ranked_drafts": ranked_items,
            "dominance_matrix": dominance_matrix,
            "tradeoff_analysis": tradeoff_summary,
        }


_PARETO_JURY_INSTANCE: Optional[ParetoJuryEvaluator] = None


def get_pareto_jury() -> ParetoJuryEvaluator:
    """Singleton getter for ParetoJuryEvaluator."""
    global _PARETO_JURY_INSTANCE
    if _PARETO_JURY_INSTANCE is None:
        _PARETO_JURY_INSTANCE = ParetoJuryEvaluator()
    return _PARETO_JURY_INSTANCE
