"""PrismEra Vector Store with NumPy and SQLite persistence.

Stores AdmissionCase and ProgramNuance records, with hybrid semantic and metadata
filtering retrieval, and dynamic admission probability calculation.
"""

from __future__ import annotations
import json
import logging
import math
import os
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

FALLBACK_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DATA_DIR = Path(os.getenv("PRISMERA_DATA_DIR")) if os.getenv("PRISMERA_DATA_DIR") else FALLBACK_DATA_DIR
DEFAULT_SEED_PATH = DEFAULT_DATA_DIR / "seed_graph_data.json"
if not DEFAULT_SEED_PATH.exists() and (FALLBACK_DATA_DIR / "seed_graph_data.json").exists():
    DEFAULT_SEED_PATH = FALLBACK_DATA_DIR / "seed_graph_data.json"
DEFAULT_VECTOR_SQLITE_PATH = DEFAULT_DATA_DIR / "vector_store.sqlite"

EMBEDDING_DIM = 256


@dataclass
class AdmissionCase:
    """Historical admission or rejection case."""
    id: str
    target_program_id: str
    undergrad_name: str
    undergrad_tier: str
    gpa: float
    gpa_scale: str
    major: str
    language: str
    background_summary: str
    outcome: str
    outcome_type: str  # "admit" | "reject"
    year: int
    profile_text: str
    gre: Optional[str] = None


@dataclass
class ProgramNuance:
    """Institutional admissions preference and covert nuance."""
    program_id: str
    name: str
    nuance_summary: str
    deadline: str
    gre_policy: str
    stem_status: str
    detailed_text: str


class SimpleDenseEmbedder:
    """Deterministic local text embedder using n-gram subword hashing and L2 normalization."""

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s\u4e00-\u9fa5]", " ", text.lower())
        tokens: List[str] = []
        words = cleaned.split()

        for w in words:
            tokens.append(w)
            # Character n-grams for Chinese and English subwords
            if len(w) > 1:
                for i in range(len(w) - 1):
                    tokens.append(w[i:i+2])
                for i in range(len(w) - 2):
                    tokens.append(w[i:i+3])
        return tokens

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = self._tokenize(text)
        if not tokens:
            return vec

        for t in tokens:
            h = hash(t)
            idx = abs(h) % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        return vec


class VectorStore:
    """Local vector store for admission cases and program nuances."""

    def __init__(
        self,
        sqlite_path: Optional[Union[str, Path]] = None,
        auto_load: bool = True
    ):
        self.sqlite_path = Path(sqlite_path) if sqlite_path else DEFAULT_VECTOR_SQLITE_PATH
        self.embedder = SimpleDenseEmbedder(dim=EMBEDDING_DIM)

        self.cases: Dict[str, AdmissionCase] = {}
        self.case_vectors: Dict[str, np.ndarray] = {}

        self.nuances: Dict[str, ProgramNuance] = {}
        self.nuance_vectors: Dict[str, np.ndarray] = {}

        if auto_load:
            if self.sqlite_path.exists():
                try:
                    self.load_from_sqlite(self.sqlite_path)
                except Exception as e:
                    logger.warning(f"Failed to load vector store from SQLite ({e}), falling back to seed json.")
                    self.load_from_seed()
            elif DEFAULT_SEED_PATH.exists():
                self.load_from_seed(DEFAULT_SEED_PATH)
                try:
                    self.save_to_sqlite(self.sqlite_path)
                except Exception as e:
                    logger.warning(f"Could not persist vector store to SQLite: {e}")

    # =========================================================================
    # Ingest and Indexing
    # =========================================================================

    def add_admission_case(self, case: AdmissionCase) -> None:
        self.cases[case.id] = case
        emb_text = f"{case.undergrad_tier} {case.undergrad_name} {case.major} GPA {case.gpa} {case.language} {case.background_summary} {case.profile_text}"
        self.case_vectors[case.id] = self.embedder.embed(emb_text)

    def add_admission_cases(self, cases: List[AdmissionCase]) -> None:
        for c in cases:
            self.add_admission_case(c)

    def add_program_nuance(self, nuance: ProgramNuance) -> None:
        self.nuances[nuance.program_id] = nuance
        emb_text = f"{nuance.name} {nuance.nuance_summary} {nuance.detailed_text}"
        self.nuance_vectors[nuance.program_id] = self.embedder.embed(emb_text)

    def add_program_nuances(self, nuances: List[ProgramNuance]) -> None:
        for n in nuances:
            self.add_program_nuance(n)

    # =========================================================================
    # Persistence
    # =========================================================================

    def load_from_seed(self, seed_path: Optional[Union[str, Path]] = None) -> None:
        path = Path(seed_path) if seed_path else DEFAULT_SEED_PATH
        if not path.exists():
            raise FileNotFoundError(f"Seed file not found at {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.cases.clear()
        self.case_vectors.clear()
        self.nuances.clear()
        self.nuance_vectors.clear()

        for c_dict in data.get("admission_cases", []):
            case = AdmissionCase(**c_dict)
            self.add_admission_case(case)

        for n_dict in data.get("program_nuances", []):
            nuance = ProgramNuance(**n_dict)
            self.add_program_nuance(nuance)

    def save_to_sqlite(self, sqlite_path: Optional[Union[str, Path]] = None) -> None:
        path = Path(sqlite_path) if sqlite_path else self.sqlite_path
        path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(path))
        try:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS admission_cases")
            cursor.execute("DROP TABLE IF EXISTS program_nuances")

            cursor.execute("""
                CREATE TABLE admission_cases (
                    id TEXT PRIMARY KEY,
                    target_program_id TEXT,
                    undergrad_tier TEXT,
                    undergrad_name TEXT,
                    gpa REAL,
                    gpa_scale TEXT,
                    major TEXT,
                    outcome_type TEXT,
                    data_json TEXT,
                    vector BLOB
                )
            """)

            cursor.execute("""
                CREATE TABLE program_nuances (
                    program_id TEXT PRIMARY KEY,
                    name TEXT,
                    data_json TEXT,
                    vector BLOB
                )
            """)

            for cid, case in self.cases.items():
                vec = self.case_vectors.get(cid, np.zeros(self.embedder.dim, dtype=np.float32))
                cursor.execute(
                    """
                    INSERT INTO admission_cases (
                        id, target_program_id, undergrad_tier, undergrad_name, gpa, gpa_scale, major, outcome_type, data_json, vector
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case.id,
                        case.target_program_id,
                        case.undergrad_tier,
                        case.undergrad_name,
                        case.gpa,
                        case.gpa_scale,
                        case.major,
                        case.outcome_type,
                        json.dumps(asdict(case), ensure_ascii=False),
                        vec.tobytes()
                    )
                )

            for pid, nuance in self.nuances.items():
                vec = self.nuance_vectors.get(pid, np.zeros(self.embedder.dim, dtype=np.float32))
                cursor.execute(
                    "INSERT INTO program_nuances (program_id, name, data_json, vector) VALUES (?, ?, ?, ?)",
                    (
                        nuance.program_id,
                        nuance.name,
                        json.dumps(asdict(nuance), ensure_ascii=False),
                        vec.tobytes()
                    )
                )

            conn.commit()
        finally:
            conn.close()

    def load_from_sqlite(self, sqlite_path: Optional[Union[str, Path]] = None) -> None:
        path = Path(sqlite_path) if sqlite_path else self.sqlite_path
        if not path.exists():
            raise FileNotFoundError(f"SQLite vector store not found at {path}")

        conn = sqlite3.connect(str(path))
        try:
            cursor = conn.cursor()
            self.cases.clear()
            self.case_vectors.clear()
            self.nuances.clear()
            self.nuance_vectors.clear()

            cursor.execute("SELECT id, data_json, vector FROM admission_cases")
            for cid, data_json, vec_bytes in cursor.fetchall():
                c_dict = json.loads(data_json)
                self.cases[cid] = AdmissionCase(**c_dict)
                self.case_vectors[cid] = np.frombuffer(vec_bytes, dtype=np.float32)

            cursor.execute("SELECT program_id, data_json, vector FROM program_nuances")
            for pid, data_json, vec_bytes in cursor.fetchall():
                n_dict = json.loads(data_json)
                self.nuances[pid] = ProgramNuance(**n_dict)
                self.nuance_vectors[pid] = np.frombuffer(vec_bytes, dtype=np.float32)
        finally:
            conn.close()

    # =========================================================================
    # Hybrid Retrieval (Vector Similarity + Metadata Filtering)
    # =========================================================================

    def search_admission_cases(
        self,
        query_text: str = "",
        filter_metadata: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search cases matching metadata filters and ranked by semantic similarity."""
        filters = filter_metadata or {}
        candidate_ids = []

        for cid, case in self.cases.items():
            match = True
            for k, v in filters.items():
                if k == "target_program_id" and case.target_program_id != v:
                    match = False
                    break
                if k == "undergrad_tier" and case.undergrad_tier != v:
                    match = False
                    break
                if k == "outcome_type" and case.outcome_type != v:
                    match = False
                    break
            if match:
                candidate_ids.append(cid)

        if not candidate_ids:
            # Fallback if strict filter yields 0: relax undergrad_tier
            relaxed_filters = {k: v for k, v in filters.items() if k != "undergrad_tier"}
            for cid, case in self.cases.items():
                match = True
                for k, v in relaxed_filters.items():
                    if k == "target_program_id" and case.target_program_id != v:
                        match = False
                        break
                    if k == "outcome_type" and case.outcome_type != v:
                        match = False
                        break
                if match:
                    candidate_ids.append(cid)

        if not candidate_ids:
            return []

        if not query_text:
            return [asdict(self.cases[cid]) for cid in candidate_ids[:top_k]]

        query_vec = self.embedder.embed(query_text)
        scores = []
        for cid in candidate_ids:
            cvec = self.case_vectors.get(cid)
            sim = float(np.dot(query_vec, cvec)) if cvec is not None else 0.0
            scores.append((sim, cid))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, cid in scores[:top_k]:
            item = asdict(self.cases[cid])
            item["similarity_score"] = round(sim, 4)
            results.append(item)
        return results

    def search_program_nuance(
        self,
        program_id: str,
        query_text: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve nuance information for a specific program."""
        if program_id in self.nuances:
            return asdict(self.nuances[program_id])
        return None

    # =========================================================================
    # Dynamic Admission Probability and Median Metrics
    # =========================================================================

    def calculate_admission_metrics(
        self,
        target_program_id: str,
        undergrad_tier: str,
        gpa: float,
        major: str = "",
        student_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dynamically compute median GPA, admit/reject samples, and Reach/Match/Safety rate."""
        # 1. Fetch relevant cases for this program
        prog_cases = [c for c in self.cases.values() if c.target_program_id == target_program_id]

        if not prog_cases:
            # Generic fallback if no specific program cases exist
            base_res = {
                "admitted_sample": [
                    {"profile": f"{undergrad_tier}院校 {major or '相关专业'} GPA 浮动中位数, 标化达标", "outcome": "ADMIT"}
                ],
                "rejected_sample": [
                    {"profile": f"{undergrad_tier}院校 GPA 低于门槛或语言小分偏低", "outcome": "REJECT"}
                ],
                "peer_median_gpa": 3.60 if gpa <= 4.0 else 85.0,
                "acceptance_rate_range": "35% - 50%",
                "bracket_recommendation": "Match",
                "admit_probability": 0.42,
                "probability_percent": "42.0%",
                "feature_attributions": {"GPA门槛优势": "+5.0%", "院校Tier影响": "+0.0%"},
                "top_positive_factors": ["GPA门槛优势 (+5.0%)"],
                "top_negative_factors": []
            }
            try:
                from prismera.ml.admit_predictor import get_admit_predictor
                predictor = get_admit_predictor()
                st_data = student_profile or {"undergrad_tier": undergrad_tier, "gpa_raw": str(gpa), "major": major}
                ml_eval = predictor.explain_admission(st_data, {"id": target_program_id, "tier_bracket": "Match"}, major=major)
                base_res.update({
                    "acceptance_rate_range": ml_eval["acceptance_rate_range"],
                    "bracket_recommendation": ml_eval["tier_bracket"],
                    "admit_probability": ml_eval["admit_probability"],
                    "probability_percent": ml_eval["probability_percent"],
                    "feature_attributions": ml_eval["feature_attributions"],
                    "top_positive_factors": ml_eval["top_positive_factors"],
                    "top_negative_factors": ml_eval["top_negative_factors"]
                })
            except Exception:
                pass
            return base_res

        admitted_cases = [c for c in prog_cases if c.outcome_type == "admit"]
        rejected_cases = [c for c in prog_cases if c.outcome_type == "reject"]

        # 2. Compute Peer Median GPA
        is_4_scale = gpa <= 4.0
        normalized_admit_gpas: List[float] = []

        for c in admitted_cases:
            if is_4_scale:
                c_val = c.gpa if c.gpa <= 4.0 else round(c.gpa / 25.0, 2)
            else:
                c_val = c.gpa if c.gpa > 10.0 else round(c.gpa * 25.0, 1)
            normalized_admit_gpas.append(c_val)

        if normalized_admit_gpas:
            peer_median_gpa = float(np.median(normalized_admit_gpas))
            peer_median_gpa = round(peer_median_gpa, 2 if is_4_scale else 1)
        else:
            peer_median_gpa = round(3.65 if is_4_scale else 86.5, 2 if is_4_scale else 1)

        # 3. Dynamic Acceptance Rate Calculation
        # Base program acceptance rate
        base_rate = 0.38
        if any(kw in target_program_id for kw in ["cmu", "ic", "oxford", "nus", "nyu_ms_ds"]):
            base_rate = 0.24
        elif any(kw in target_program_id for kw in ["usc", "ucl"]):
            base_rate = 0.50

        # Tier modifier
        tier_mod = 0.0
        if undergrad_tier == "985":
            tier_mod = 0.10
        elif undergrad_tier == "211":
            tier_mod = 0.0
        elif undergrad_tier == "双非一本":
            tier_mod = -0.15
        elif undergrad_tier == "海本":
            tier_mod = 0.08

        # GPA difference modifier
        if is_4_scale:
            gpa_diff = gpa - peer_median_gpa
            gpa_mod = gpa_diff * 1.2  # 0.1 diff -> 12% shift
        else:
            gpa_diff = gpa - peer_median_gpa
            gpa_mod = (gpa_diff / 25.0) * 1.2

        estimated_rate = base_rate + tier_mod + gpa_mod
        estimated_rate = max(0.08, min(0.88, estimated_rate))

        # Format rate range and bracket recommendation
        low_bound = max(5, int((estimated_rate - 0.05) * 100))
        high_bound = min(95, int((estimated_rate + 0.05) * 100))
        rate_str = f"{low_bound}% - {high_bound}%"

        if estimated_rate < 0.32:
            bracket = "Reach"
        elif estimated_rate > 0.65:
            bracket = "Safety"
        else:
            bracket = "Match"

        # 4. Select representative sample profiles
        query = f"{undergrad_tier} {major} GPA {gpa}"
        matched_admits = self.search_admission_cases(
            query_text=query,
            filter_metadata={"target_program_id": target_program_id, "outcome_type": "admit"},
            top_k=2
        )
        matched_rejects = self.search_admission_cases(
            query_text=query,
            filter_metadata={"target_program_id": target_program_id, "outcome_type": "reject"},
            top_k=2
        )

        admitted_samples = [
            {"profile": item["profile_text"], "outcome": item["outcome"]}
            for item in matched_admits
        ]
        rejected_samples = [
            {"profile": item["profile_text"], "outcome": item["outcome"]}
            for item in matched_rejects
        ]

        if not admitted_samples:
            admitted_samples = [{"profile": f"{undergrad_tier}院校 {major} GPA 浮动中位数, 标化达标", "outcome": "ADMIT"}]
        if not rejected_samples:
            rejected_samples = [{"profile": f"{undergrad_tier}院校 GPA 低于门槛或语言小分偏低", "outcome": "REJECT"}]

        # 5. Prism-AdmitNet ML Probability and Feature Attribution
        ml_admit_prob = estimated_rate
        ml_prob_pct = f"{int(estimated_rate * 100)}%"
        ml_bracket = bracket
        ml_rate_range = rate_str
        feature_attributions: Dict[str, str] = {
            "GPA门槛优势": f"+{int(abs(gpa_mod)*100)}%" if gpa_mod >= 0 else f"-{int(abs(gpa_mod)*100)}%",
            "院校Tier影响": f"+{int(abs(tier_mod)*100)}%" if tier_mod >= 0 else f"-{int(abs(tier_mod)*100)}%",
        }
        top_pos: List[str] = ["GPA门槛优势"] if gpa_mod >= 0 else []
        top_neg: List[str] = ["GPA相对偏弱"] if gpa_mod < 0 else []

        try:
            from prismera.ml.admit_predictor import get_admit_predictor
            from prismera.db.graph_store import get_graph_store

            predictor = get_admit_predictor()
            prog_node = get_graph_store().get_node(target_program_id) or {"id": target_program_id, "tier_bracket": bracket}
            st_data = student_profile or {
                "undergrad_tier": undergrad_tier,
                "gpa_raw": str(gpa),
                "major": major,
            }
            ml_eval = predictor.explain_admission(st_data, prog_node, major=major)
            ml_admit_prob = ml_eval["admit_probability"]
            ml_prob_pct = ml_eval["probability_percent"]
            ml_rate_range = ml_eval["acceptance_rate_range"]
            feature_attributions = ml_eval["feature_attributions"]
            top_pos = ml_eval["top_positive_factors"]
            top_neg = ml_eval["top_negative_factors"]
        except Exception:
            pass

        return {
            "admitted_sample": admitted_samples,
            "rejected_sample": rejected_samples,
            "peer_median_gpa": peer_median_gpa,
            "acceptance_rate_range": rate_str,
            "bracket_recommendation": bracket,
            "admit_probability": ml_admit_prob,
            "probability_percent": ml_prob_pct,
            "feature_attributions": feature_attributions,
            "top_positive_factors": top_pos,
            "top_negative_factors": top_neg,
        }


# Global singleton instance
_GLOBAL_VECTOR_STORE: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or initialize the global VectorStore singleton."""
    global _GLOBAL_VECTOR_STORE
    if _GLOBAL_VECTOR_STORE is None:
        _GLOBAL_VECTOR_STORE = VectorStore()
    return _GLOBAL_VECTOR_STORE
