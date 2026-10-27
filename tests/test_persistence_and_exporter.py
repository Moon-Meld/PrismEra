"""Tests for Milestone 7: SQLite Session Persistence and Comprehensive Dossier Exporter."""

import json
import pytest
from fastapi.testclient import TestClient

from prismera.api.server import app, SESSION_REGISTRY
from prismera.db.session_store import SessionStore, get_session_store
from prismera.engine import PrismEraSession
from prismera.exporter import (
    compile_dossier_data,
    generate_markdown_report,
    generate_html_report,
)


def test_sqlite_session_store_crud(tmp_path):
    """Verify SQLite SessionStore create, save, load, rename, delete."""
    db_file = tmp_path / "test_sessions.sqlite"
    store = SessionStore(sqlite_path=db_file)

    # 1. Create a session
    created = store.create_session(
        session_id="test_student_zju",
        name="浙大学长 CS 档案",
        initial_profile={
            "undergrad_name": "浙江大学",
            "undergrad_tier": "985",
            "major": "软件工程",
            "gpa_raw": "88.5/100"
        }
    )
    assert created["session_id"] == "test_student_zju"
    assert created["name"] == "浙大学长 CS 档案"
    assert created["student_profile"]["undergrad_name"] == "浙江大学"

    # 2. List sessions
    sessions = store.list_sessions()
    assert len(sessions) >= 1
    target = next((s for s in sessions if s["session_id"] == "test_student_zju"), None)
    assert target is not None
    assert target["name"] == "浙大学长 CS 档案"
    assert target["undergrad_name"] == "浙江大学"

    # 3. Rename session
    renamed = store.rename_session("test_student_zju", "张同学 · 浙大 CS 顶申档案")
    assert renamed is True
    loaded = store.load_session_data("test_student_zju")
    assert loaded["name"] == "张同学 · 浙大 CS 顶申档案"

    # 4. Save updated state
    loaded["student_profile"]["target_regions"] = ["US", "UK"]
    loaded["messages"].append({"role": "user", "content": "我想申请 CMU"})
    store.save_session("test_student_zju", loaded)

    reloaded = store.load_session_data("test_student_zju")
    assert reloaded["student_profile"]["target_regions"] == ["US", "UK"]
    assert len(reloaded["messages"]) == 1

    # 5. Delete session
    deleted = store.delete_session("test_student_zju")
    assert deleted is True
    assert store.load_session_data("test_student_zju") is None


def test_engine_cross_session_persistence(tmp_path):
    """Verify that PrismEraSession state seamlessly survives engine restarts."""
    db_file = tmp_path / "engine_persist.sqlite"
    store = SessionStore(sqlite_path=db_file)

    session_id = "cross_session_applicant_007"

    # First session interaction
    sess1 = PrismEraSession(thread_id=session_id)
    sess1.store = store
    sess1.patch_state({
        "undergrad_name": "清华大学",
        "undergrad_tier": "985",
        "major": "计算机科学与技术",
        "gpa_raw": "91.2/100"
    })
    sess1.state["messages"].append({"role": "user", "content": "我的均分是91.2分"})
    sess1.save()

    # Clear memory registry simulation
    if session_id in SESSION_REGISTRY:
        del SESSION_REGISTRY[session_id]

    # Instantiate new session with the same thread_id
    sess2 = PrismEraSession(thread_id=session_id)
    sess2.store = store
    # Reload from store
    data = store.load_session_data(session_id)
    assert data is not None
    sess2.state = data

    assert sess2.state["student_profile"]["undergrad_name"] == "清华大学"
    assert sess2.state["student_profile"]["gpa_raw"] == "91.2/100"
    assert len(sess2.state["messages"]) == 1
    assert sess2.state["messages"][0]["content"] == "我的均分是91.2分"


def test_dossier_exporter_four_sections():
    """Verify that Dossier exporter compiles all 4 core sections in Markdown & HTML."""
    profile_data = {
        "undergrad_name": "浙江大学",
        "undergrad_tier": "985",
        "major": "软件工程",
        "gpa_raw": "88.5/100",
        "language_scores": {"IELTS_total": 7.5, "speaking": 7.0},
        "target_regions": ["US", "UK"],
        "target_majors": ["CS"],
        "shortlisted_programs": [
            {
                "id": "cmu_msse",
                "name_cn": "卡内基梅隆大学 · 软件工程硕士",
                "name_en": "MS in Software Engineering",
                "university": "Carnegie Mellon University",
                "region": "US",
                "duration": "1.5年",
                "tuition_usd": 54000,
                "tier_bracket": "Reach",
                "deadline": "12月15日",
                "min_ielts": {"total": 7.5, "subscore": 7.0},
                "min_toefl": {"total": 102},
                "peer_cases": {
                    "peer_median_gpa": "88.8/100",
                    "admitted_sample": [{"profile": "985 软件工程 89分 雅思7.5"}]
                },
                "nuance_data": {
                    "nuance_summary": "极度看重系统工程代码实践与并发底层掌控力",
                    "gre_policy": "Optional"
                }
            }
        ],
        "sop_stage": 4,
        "mined_story_fragments": [
            "分布式异步环形缓冲区调度优化",
            "解决 15% 极端丢包网络分区故障雪崩"
        ],
        "sop_draft": "When our distributed message queue dropped 14% of heartbeats...",
        "target_professors": [
            {
                "scholar_name": "Prof. Indranil Gupta",
                "institution": "UIUC",
                "lab": "DPRG",
                "paper_title": "SWIM Membership Protocol",
                "hook": "弱一致性成员状态传播与故障检测"
            }
        ]
    }

    mock_session = {
        "session_id": "test_dossier_applicant",
        "profile": profile_data,
        "metadata": {"name": "张同学 · 浙大软件工程"}
    }

    # 1. Dossier Data Compilation
    dossier = compile_dossier_data(mock_session)
    assert "section_1_facet" in dossier
    assert "section_2_locus" in dossier
    assert "section_3_disperser" in dossier
    assert "section_4_resonator" in dossier

    # Check Section 1: Facet
    sec1 = dossier["section_1_facet"]
    assert "gpa_metrics" in sec1
    assert "prerequisite_alignment" in sec1
    assert len(sec1["refining_roadmap"]) >= 3

    # Check Section 2: Locus
    sec2 = dossier["section_2_locus"]
    assert len(sec2["shortlisted_programs"]) >= 1
    assert len(sec2["deadlines"]) >= 1

    # Check Section 3: Disperser
    sec3 = dossier["section_3_disperser"]
    assert len(sec3["mined_fragments"]) >= 2
    assert "sop_draft" in sec3
    assert len(sec3["sop_draft"]) > 10

    # Check Section 4: Resonator
    sec4 = dossier["section_4_resonator"]
    assert len(sec4["target_professors"]) >= 1
    assert "cold_email_draft" in sec4
    assert "Gupta" in sec4["cold_email_draft"]

    # 2. Markdown Report
    md = generate_markdown_report(mock_session)
    assert "# 《PrismEra 个人升学光谱全案报告》" in md
    assert "## 1. 个人原石光谱与切面诊断报告" in md
    assert "## 2. 三维选校定焦矩阵全表" in md
    assert "## 3. 定稿文书资产包" in md
    assert "## 4. 学术套磁信与导师匹配清单" in md
    assert "卡内基梅隆大学" in md
    assert "Indranil Gupta" in md

    # 3. HTML Report
    html = generate_html_report(mock_session)
    assert "<!DOCTYPE html>" in html
    assert "《PrismEra 个人升学光谱全案报告》" in html
    assert "Dark Optical Aesthetic" in html
    assert "sec-facet" in html
    assert "sec-locus" in html
    assert "sec-disperser" in html
    assert "sec-resonator" in html
    assert "window.print()" in html


def test_api_session_management_and_export():
    """Verify REST API endpoints for session CRUD and dossier export."""
    client = TestClient(app)

    # 1. Create session
    create_resp = client.post("/api/session/create", json={
        "name": "李同学 · 清华交叉信息院",
        "initial_profile": {
            "undergrad_name": "清华大学",
            "undergrad_tier": "985",
            "major": "计算机科学与技术",
            "gpa_raw": "90.5/100"
        }
    })
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["status"] == "success"
    session_id = create_data["session_id"]
    assert create_data["session"]["name"] == "李同学 · 清华交叉信息院"

    # 2. List sessions
    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    all_sessions = list_resp.json()["sessions"]
    found = next((s for s in all_sessions if s["session_id"] == session_id), None)
    assert found is not None
    assert found["name"] == "李同学 · 清华交叉信息院"

    # 3. Rename session
    rename_resp = client.post(f"/api/session/{session_id}/rename", json={
        "name": "李同学 · 清华姚班顶申档案"
    })
    assert rename_resp.status_code == 200
    assert rename_resp.json()["name"] == "李同学 · 清华姚班顶申档案"

    # 4. Export as Markdown
    exp_md = client.get(f"/api/session/{session_id}/export?format=markdown")
    assert exp_md.status_code == 200
    assert "text/markdown" in exp_md.headers.get("content-type", "")
    assert "《PrismEra 个人升学光谱全案报告》" in exp_md.text
    assert "第一切面：个人原石光谱与切面诊断报告" in exp_md.text
    assert "第二透镜：三维选校定焦矩阵全表" in exp_md.text

    # 5. Export as HTML
    exp_html = client.get(f"/api/session/{session_id}/export?format=html")
    assert exp_html.status_code == 200
    assert "text/html" in exp_html.headers.get("content-type", "")
    assert "<!DOCTYPE html>" in exp_html.text
    assert "PrismEra" in exp_html.text

    # 6. Export Preview JSON
    exp_prev = client.get(f"/api/session/{session_id}/export/preview")
    assert exp_prev.status_code == 200
    prev_data = exp_prev.json()
    assert "markdown" in prev_data
    assert "html" in prev_data
    assert prev_data["session_id"] == session_id

    # 7. Delete session
    del_resp = client.delete(f"/api/session/{session_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True
