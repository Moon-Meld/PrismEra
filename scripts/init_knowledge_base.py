"""PrismEra Knowledge Base Initialization Script.

Loads seed data, constructs GraphStore (NetworkX/SQLite) and VectorStore (NumPy/SQLite),
and verifies end-to-end graph traversal and semantic retrieval.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from prismera.db.graph_store import GraphStore, DEFAULT_SEED_PATH, DEFAULT_SQLITE_PATH
from prismera.db.vector_store import VectorStore, DEFAULT_VECTOR_SQLITE_PATH
from scripts.build_seed_data import build_seed_json


def init_knowledge_base():
    print("=" * 60)
    print("🚀 PrismEra GraphRAG 混合知识底座一键建库与初始化")
    print("=" * 60)

    # 1. Ensure seed data exists
    if not DEFAULT_SEED_PATH.exists():
        print(f"[*] 种子数据不存在，正在生成: {DEFAULT_SEED_PATH}")
        build_seed_json()
    else:
        print(f"[✓] 找到现有种子数据: {DEFAULT_SEED_PATH}")

    # 2. Build & Persist GraphStore
    print(f"\n[*] 正在构建知识图谱 (NetworkX + SQLite)...")
    gs = GraphStore(sqlite_path=DEFAULT_SQLITE_PATH, auto_load=False)
    gs.load_from_seed(DEFAULT_SEED_PATH)
    gs.save_to_sqlite(DEFAULT_SQLITE_PATH)

    uni_count = len(gs.get_nodes_by_label("University"))
    prog_count = len(gs.get_nodes_by_label("Program"))
    tier_count = len(gs.get_nodes_by_label("ChineseUniTier"))
    course_count = len(gs.get_nodes_by_label("Course"))
    prof_count = len(gs.get_nodes_by_label("Professor"))
    edge_count = len(gs.graph.edges)

    print(f"[✓] 图谱实体与关系持久化成功 -> {DEFAULT_SQLITE_PATH}")
    print(f"    - University 院校节点: {uni_count}")
    print(f"    - Program 项目节点: {prog_count}")
    print(f"    - ChineseUniTier 院校档次: {tier_count}")
    print(f"    - Course 先修课节点: {course_count}")
    print(f"    - Professor 学者节点: {prof_count}")
    print(f"    - 拓扑带权边 (Edges): {edge_count}")

    # 3. Build & Persist VectorStore
    print(f"\n[*] 正在构建向量库 (NumPy Cosine + SQLite)...")
    vs = VectorStore(sqlite_path=DEFAULT_VECTOR_SQLITE_PATH, auto_load=False)
    vs.load_from_seed(DEFAULT_SEED_PATH)
    vs.save_to_sqlite(DEFAULT_VECTOR_SQLITE_PATH)

    case_count = len(vs.cases)
    nuance_count = len(vs.nuances)
    print(f"[✓] 录取案例与隐形偏好向量库持久化成功 -> {DEFAULT_VECTOR_SQLITE_PATH}")
    print(f"    - AdmissionCase 录取/被拒案例: {case_count}")
    print(f"    - ProgramNuance 项目文书偏好: {nuance_count}")

    # 4. Diagnostic Self-Check
    print("\n" + "-" * 60)
    print("🔍 运行知识底座联调自检 (Diagnostic Sanity Checks)")
    print("-" * 60)

    # Test 4.1: Hard pruning on UK List and language subscore
    test_result = gs.query_programs_filtered(
        undergrad_tier="双非一本",
        gpa=82.0,
        language_scores={"IELTS_total": 6.5, "speaking": 5.5},
        target_regions=["UK"],
        target_majors=["CS"]
    )
    print(f"1. 双非 82分 雅思口语5.5 申请英国CS测试: 留存 {len(test_result)} 个项目, 剪枝 {len(test_result.pruned_records)} 个")
    for r in test_result.pruned_records:
        print(f"   ✖ [{r['program_id']}]: {r['reason']}")
    assert len(test_result) == 0, "双非82分口语5.5不应匹配帝国理工/爱丁堡"

    # Test 4.2: Qualified 985 candidate
    pass_result = gs.query_programs_filtered(
        undergrad_tier="985",
        gpa=89.0,
        language_scores={"IELTS_total": 7.5, "speaking": 7.0},
        target_regions=["UK"],
        target_majors=["CS"]
    )
    print(f"\n2. 985 89分 雅思7.5 申请英国CS测试: 留存 {len(pass_result)} 个项目 -> {[p['id'] for p in pass_result]}")
    assert len(pass_result) >= 3, "985高分候选人应顺利通过英国名校剪枝"

    # Test 4.3: Dynamic admission statistics
    metrics = vs.calculate_admission_metrics("cmu_msit_se", "985", 3.75, "CS")
    print(f"\n3. CMU MSIT-SE 同辈录取率动态测算测试:")
    print(f"   - 往年录取中位线 GPA: {metrics['peer_median_gpa']}")
    print(f"   - 动态录取率区间: {metrics['acceptance_rate_range']}")
    print(f"   - 智能定档建议: {metrics['bracket_recommendation']}")
    print(f"   - 同辈录取样本画像: “{metrics['admitted_sample'][0]['profile']}”")

    print("\n" + "=" * 60)
    print("🎉 Milestone 1 知识底座初始化完成，所有诊断测试全部通过！")
    print("=" * 60)


if __name__ == "__main__":
    init_knowledge_base()
