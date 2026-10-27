"""PrismEra Graph Store with NetworkX and SQLite local persistence.

Supports real graph-traversal pruning, List verification, prerequisite subgraphs,
and optional Neo4j integration.
"""

from __future__ import annotations
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import networkx as nx

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_SEED_PATH = DEFAULT_DATA_DIR / "seed_graph_data.json"
DEFAULT_SQLITE_PATH = DEFAULT_DATA_DIR / "graph_store.sqlite"


class FilteredProgramList(list):
    """List of matched programs with attached pruning audit details."""

    def __init__(self, items: List[Dict[str, Any]], pruned_records: Optional[List[Dict[str, Any]]] = None):
        super().__init__(items)
        self.pruned_records: List[Dict[str, Any]] = pruned_records or []
        self.pruned_reasons: List[str] = [r.get("reason", "") for r in self.pruned_records]


class GraphStore:
    """NetworkX + SQLite hybrid graph knowledge base."""

    def __init__(
        self,
        sqlite_path: Optional[Union[str, Path]] = None,
        auto_load: bool = True
    ):
        self.sqlite_path = Path(sqlite_path) if sqlite_path else DEFAULT_SQLITE_PATH
        self.graph = nx.MultiDiGraph()
        self._last_pruned_records: List[Dict[str, Any]] = []

        if auto_load:
            if self.sqlite_path.exists():
                try:
                    self.load_from_sqlite(self.sqlite_path)
                except Exception as e:
                    logger.warning(f"Failed to load from SQLite ({e}), falling back to seed json.")
                    self.load_from_seed()
            elif DEFAULT_SEED_PATH.exists():
                self.load_from_seed(DEFAULT_SEED_PATH)
                try:
                    self.save_to_sqlite(self.sqlite_path)
                except Exception as e:
                    logger.warning(f"Could not persist to SQLite: {e}")

    # =========================================================================
    # Node & Edge CRUD
    # =========================================================================

    def add_node(self, node_id: str, label: str, properties: Optional[Dict[str, Any]] = None) -> None:
        props = properties.copy() if properties else {}
        props["label"] = label
        props["id"] = node_id
        self.graph.add_node(node_id, **props)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        if self.graph.has_node(node_id):
            return dict(self.graph.nodes[node_id])
        return None

    def get_nodes_by_label(self, label: str) -> List[Dict[str, Any]]:
        return [
            dict(data)
            for _, data in self.graph.nodes(data=True)
            if data.get("label") == label
        ]

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        props = properties.copy() if properties else {}
        props["rel_type"] = rel_type
        self.graph.add_edge(source_id, target_id, key=rel_type, **props)

    def get_outgoing_edges(
        self,
        source_id: str,
        rel_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.graph.has_node(source_id):
            return []
        edges = []
        for _, target, key, data in self.graph.out_edges(source_id, keys=True, data=True):
            if rel_type is None or key == rel_type:
                edge_info = dict(data)
                edge_info["source"] = source_id
                edge_info["target"] = target
                edge_info["rel_type"] = key
                edges.append(edge_info)
        return edges

    def get_incoming_edges(
        self,
        target_id: str,
        rel_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.graph.has_node(target_id):
            return []
        edges = []
        for source, _, key, data in self.graph.in_edges(target_id, keys=True, data=True):
            if rel_type is None or key == rel_type:
                edge_info = dict(data)
                edge_info["source"] = source
                edge_info["target"] = target
                edge_info["rel_type"] = key
                edges.append(edge_info)
        return edges

    # =========================================================================
    # Persistence: Seed JSON and SQLite
    # =========================================================================

    def load_from_seed(self, seed_path: Optional[Union[str, Path]] = None) -> None:
        path = Path(seed_path) if seed_path else DEFAULT_SEED_PATH
        if not path.exists():
            raise FileNotFoundError(f"Seed file not found at {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.graph.clear()

        for uni in data.get("universities", []):
            self.add_node(uni["id"], "University", uni)

        for tier in data.get("chinese_uni_tiers", []):
            self.add_node(tier["id"], "ChineseUniTier", tier)

        for course in data.get("courses", []):
            self.add_node(course["id"], "Course", course)

        for prof in data.get("professors", []):
            self.add_node(prof["id"], "Professor", prof)

        for prog in data.get("programs", []):
            self.add_node(prog["id"], "Program", prog)

        for edge in data.get("edges", []):
            self.add_edge(
                source_id=edge["source"],
                target_id=edge["target"],
                rel_type=edge["type"],
                properties=edge.get("properties", {})
            )

    def save_to_sqlite(self, sqlite_path: Optional[Union[str, Path]] = None) -> None:
        path = Path(sqlite_path) if sqlite_path else self.sqlite_path
        path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(path))
        try:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS nodes")
            cursor.execute("DROP TABLE IF EXISTS edges")

            cursor.execute("""
                CREATE TABLE nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT,
                    properties TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE edges (
                    source TEXT,
                    target TEXT,
                    rel_type TEXT,
                    properties TEXT
                )
            """)

            for node_id, data in self.graph.nodes(data=True):
                label = data.get("label", "Node")
                cursor.execute(
                    "INSERT INTO nodes (id, label, properties) VALUES (?, ?, ?)",
                    (node_id, label, json.dumps(data, ensure_ascii=False))
                )

            for u, v, k, data in self.graph.edges(keys=True, data=True):
                cursor.execute(
                    "INSERT INTO edges (source, target, rel_type, properties) VALUES (?, ?, ?, ?)",
                    (u, v, k, json.dumps(data, ensure_ascii=False))
                )

            conn.commit()
        finally:
            conn.close()

    def load_from_sqlite(self, sqlite_path: Optional[Union[str, Path]] = None) -> None:
        path = Path(sqlite_path) if sqlite_path else self.sqlite_path
        if not path.exists():
            raise FileNotFoundError(f"SQLite database not found at {path}")

        conn = sqlite3.connect(str(path))
        try:
            cursor = conn.cursor()
            self.graph.clear()

            cursor.execute("SELECT id, label, properties FROM nodes")
            for node_id, label, props_json in cursor.fetchall():
                props = json.loads(props_json)
                self.add_node(node_id, label, props)

            cursor.execute("SELECT source, target, rel_type, properties FROM edges")
            for source, target, rel_type, props_json in cursor.fetchall():
                props = json.loads(props_json)
                self.add_edge(source, target, rel_type, props)
        finally:
            conn.close()

    # =========================================================================
    # Graph Traversal Pruning & Admissions Logic
    # =========================================================================

    def query_programs_filtered(
        self,
        undergrad_tier: str,
        gpa: float,
        language_scores: Dict[str, float],
        target_regions: List[str],
        target_majors: List[str],
        budget_wan: Optional[int] = None
    ) -> FilteredProgramList:
        """Graph-traversal pruning simulating Cypher MATCH & WHERE constraints.

        Traverses (p:Program)-[:ACCEPTS_LIST]->(t:ChineseUniTier)
        and checks language subscores and major/region constraints.
        Returns matching programs and records granular reasons for pruned ones.
        """
        matched_programs: List[Dict[str, Any]] = []
        pruned_records: List[Dict[str, Any]] = []

        # Convert student GPA
        gpa_4 = gpa if gpa <= 4.0 else round(gpa / 25.0, 2)
        gpa_100 = gpa if gpa > 10.0 else round(gpa * 25.0, 1)

        # Normalize filter criteria
        norm_regions = [r.upper() for r in target_regions] if target_regions else []
        norm_majors = [m.upper() for m in target_majors] if target_majors else []

        # Parse student language scores
        ielts_total = float(language_scores.get("IELTS_total", language_scores.get("ielts", 0.0)))
        ielts_speaking = float(language_scores.get("speaking", language_scores.get("ielts_sub", 0.0)))
        ielts_listening = float(language_scores.get("listening", 0.0))
        ielts_reading = float(language_scores.get("reading", 0.0))
        ielts_writing = float(language_scores.get("writing", 0.0))

        toefl_total = float(language_scores.get("TOEFL_total", language_scores.get("toefl", 0.0)))
        toefl_sub = float(language_scores.get("toefl_sub", language_scores.get("speaking_toefl", 0.0)))

        all_programs = self.get_nodes_by_label("Program")

        for prog in all_programs:
            prog_id = prog["id"]
            prog_name = prog.get("name_cn", prog_id)
            pruned_reason: Optional[str] = None

            # 1. Region constraint
            if norm_regions and prog.get("region", "").upper() not in norm_regions:
                continue

            # 2. Major constraint
            if norm_majors and prog.get("major_category", "").upper() not in norm_majors:
                continue

            # 3. List constraints via graph edges (Program)-[:ACCEPTS_LIST]->(ChineseUniTier)
            accept_edges = self.get_outgoing_edges(prog_id, rel_type="ACCEPTS_LIST")
            if accept_edges:
                accepted_tiers_map = {
                    edge["target"]: edge.get("min_gpa_score", 0.0)
                    for edge in accept_edges
                }
                if undergrad_tier and undergrad_tier not in accepted_tiers_map:
                    accepted_names = list(accepted_tiers_map.keys())
                    pruned_reason = (
                        f"院校背景受限：该项目内地认可名单(List)仅限 [{', '.join(accepted_names)}]，"
                        f"当前为【{undergrad_tier}】"
                    )
                elif undergrad_tier:
                    required_min_gpa = accepted_tiers_map[undergrad_tier]
                    # Check whether student meets threshold
                    if required_min_gpa > 10.0:  # 100-scale requirement
                        if gpa_100 < required_min_gpa:
                            pruned_reason = (
                                f"均分未达标：该项目针对【{undergrad_tier}】均分门槛为 {required_min_gpa:.1f}分，"
                                f"当前均分为 {gpa_100:.1f}分"
                            )
                    else:  # 4.0-scale requirement
                        if gpa_4 < required_min_gpa:
                            pruned_reason = (
                                f"GPA未达标：该项目针对【{undergrad_tier}】最低GPA要求为 {required_min_gpa:.2f}，"
                                f"当前GPA为 {gpa_4:.2f}"
                            )

            # 4. Language constraints
            if not pruned_reason and ielts_total > 0:
                min_ielts = prog.get("min_ielts", {})
                req_ielts_total = min_ielts.get("total", 0.0)
                req_ielts_sub = min_ielts.get("subscore", min_ielts.get("speaking", 0.0))

                if req_ielts_total > 0 and ielts_total < req_ielts_total:
                    pruned_reason = (
                        f"雅思总分未达标：要求最低 {req_ielts_total:.1f}，"
                        f"当前总分为 {ielts_total:.1f}"
                    )
                elif req_ielts_sub > 0 and ielts_speaking > 0 and ielts_speaking < req_ielts_sub:
                    pruned_reason = (
                        f"雅思口语单项受阻：该项目严卡口语小分不低于 {req_ielts_sub:.1f}，"
                        f"当前口语分数为 {ielts_speaking:.1f}"
                    )
                elif req_ielts_sub > 0:
                    for sub_label, score_val in [
                        ("听力", ielts_listening),
                        ("阅读", ielts_reading),
                        ("写作", ielts_writing)
                    ]:
                        if score_val > 0 and score_val < req_ielts_sub:
                            pruned_reason = (
                                f"雅思{sub_label}单项受阻：要求单项不低于 {req_ielts_sub:.1f}，"
                                f"当前分数为 {score_val:.1f}"
                            )
                            break

            if not pruned_reason and toefl_total > 0:
                min_toefl = prog.get("min_toefl", {})
                req_toefl_total = min_toefl.get("total", 0.0)
                req_toefl_sub = min_toefl.get("subscore", 0.0)

                if req_toefl_total > 0 and toefl_total < req_toefl_total:
                    pruned_reason = (
                        f"托福总分未达标：要求最低 {req_toefl_total}分，"
                        f"当前总分为 {toefl_total}分"
                    )
                elif req_toefl_sub > 0 and toefl_sub > 0 and toefl_sub < req_toefl_sub:
                    pruned_reason = (
                        f"托福单项未达标：要求单项不低于 {req_toefl_sub}分，"
                        f"当前为 {toefl_sub}分"
                    )

            if pruned_reason:
                pruned_records.append({
                    "program_id": prog_id,
                    "program_name": prog_name,
                    "reason": pruned_reason
                })
            else:
                matched_programs.append(prog)

        self._last_pruned_records = pruned_records
        return FilteredProgramList(matched_programs, pruned_records)

    def get_last_pruning_audit(self) -> List[Dict[str, Any]]:
        """Retrieve the audit log of the most recent pruning execution."""
        return self._last_pruned_records

    # =========================================================================
    # Prerequisite Subgraph Queries
    # =========================================================================

    def get_prerequisites_for_program(self, program_id: str) -> List[Dict[str, Any]]:
        """Get course prerequisites for a given program."""
        edges = self.get_outgoing_edges(program_id, rel_type="REQUIRES_PREREQ")
        prereqs = []
        for edge in edges:
            course_id = edge["target"]
            course_node = self.get_node(course_id)
            if course_node:
                prereqs.append({
                    "course_id": course_id,
                    "name_cn": course_node.get("name_cn", course_id),
                    "name_en": course_node.get("name_en", course_id),
                    "aliases": course_node.get("aliases", []),
                    "level": edge.get("level", "mandatory"),
                    "category": course_node.get("category", "General")
                })
        return prereqs

    def get_prerequisites_for_major(self, major_category: str) -> List[Dict[str, Any]]:
        """Get representative prerequisite courses for a major category."""
        programs = [
            p for p in self.get_nodes_by_label("Program")
            if p.get("major_category", "").upper() == major_category.upper()
        ]
        seen_courses = set()
        major_prereqs = []

        for p in programs:
            for item in self.get_prerequisites_for_program(p["id"]):
                cid = item["course_id"]
                if cid not in seen_courses:
                    seen_courses.add(cid)
                    major_prereqs.append(item)

        return major_prereqs

    # =========================================================================
    # Scholar & Professor Queries
    # =========================================================================

    def find_professor_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Search professor by normalized name."""
        norm_query = name.lower().replace(".", "").replace(" ", "_").strip()
        all_profs = self.get_nodes_by_label("Professor")

        for prof in all_profs:
            p_id = prof["id"].lower()
            p_name = prof.get("name", "").lower().replace(".", "").replace(" ", "_").strip()
            if norm_query in p_id or p_id in norm_query or norm_query in p_name or p_name in norm_query:
                return prof
        return None

    def get_professors_for_program(self, program_id: str) -> List[Dict[str, Any]]:
        """Find professors affiliated with the target program."""
        edges = self.get_incoming_edges(program_id, rel_type="AFFILIATED_WITH")
        profs = []
        for edge in edges:
            prof_node = self.get_node(edge["source"])
            if prof_node:
                prof_data = dict(prof_node)
                prof_data["affiliation_title"] = edge.get("title", "Core Faculty")
                profs.append(prof_data)
        return profs


# Global singleton instance
_GLOBAL_GRAPH_STORE: Optional[GraphStore] = None


def get_graph_store() -> GraphStore:
    """Get or initialize the global GraphStore singleton."""
    global _GLOBAL_GRAPH_STORE
    if _GLOBAL_GRAPH_STORE is None:
        _GLOBAL_GRAPH_STORE = GraphStore()
    return _GLOBAL_GRAPH_STORE
