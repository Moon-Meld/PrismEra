"""Tests for new feature enhancements in PrismEra Milestone 9.

Tests:
1. Document upload endpoint (/api/profile/upload-document) with Base64 & text
2. Pure python document parsing with raw bytes
3. Programs listing and querying (/api/programs)
4. Facet prerequisite diagnosis endpoint (/api/facet/prerequisites)
5. Live interview answer evaluation (/api/echo/evaluate-answer)
6. Canvas patch-state with customized programs list
"""

import base64
import pytest
from fastapi.testclient import TestClient
from prismera.api.server import app, get_or_create_session
from prismera.tools.document_parser import parse_student_document


def test_document_parser_with_bytes():
    raw_content = b"""# \xe4\xb8\xaa\xe4\xba\xba\xe7\xae\x80\xe5\x8e\x86
- \xe6\x9c\xac\xe7\xa7\x91\xe9\x99\xa2\xe6\xa0\xa1: \xe5\x8c\x97\xe4\xba\xac\xe5\xa4\xa7\xe5\xad\xa6 (985)
- \xe4\xb8\x93\xe4\xb8\x9a: \xe8\xae\xa1\xe7\xae\x97\xe6\x9c\xba\xe7\xa7\x91\xe5\xad\xa6\xe4\xb8\x8e\xe6\x8a\x80\xe6\x9c\xaf
- \xe5\x9d\x87\xe5\x88\x86: 92.0/100
- \xe9\x9b\x85\xe6\x80\x9d: 8.0 (\xe5\x8f\xa3\xe8\xaf\xad 7.5)

## \xe6\xa0\xb8\xe5\xbf\x83\xe8\xaf\xbe\xe7\xa8\x8b
| \xe9\xab\x98\xe7\xad\x89\xe6\x95\xb0\xe5\xad\xa6 | 96 |
| \xe6\x95\xb0\xe6\x8d\xae\xe7\xbb\x93\xe6\x9e\x84\xe4\xb8\x8e\xe7\xae\x97\xe6\xb3\x95 | 98 |

## \xe7\xa7\x91\xe7\xa0\x94\xe7\xbb\x8f\xe5\x8e\x86
### \xe5\x88\x86\xe5\xb8\x83\xe5\xbc\x8f\xe6\xb6\x88\xe6\x81\xaf\xe9\x98\x9f\xe5\x88\x97
\xe5\x9c\xa8\xe9\xa1\xb9\xe7\x9b\xae\xe4\xb8\xad\xe8\xae\xbe\xe8\xae\xa1\xe4\xba\x86\xe5\x9f\xba\xe4\xba\x8e\xe7\x8e\xaf\xe5\xbd\xa2\xe7\xbc\x93\xe5\x86\xb2\xe5\x8c\xba\xe7\x9a\x84\xe8\x87\xaa\xe9\x80\x82\xe5\xba\x94\xe8\xb0\x83\xe5\xba\xa6\xe5\x99\xa8\xef\xbc\x8c\xe5\xbb\xb6\xe6\x97\xb6\xe9\x99\x8d\xe4\xbd\x8e\xe4\xba\x8632ms\xef\xbc\x8c\xe6\x94\xaf\xe6\x92\x9115000 QPS\xe3\x80\x82
"""
    parsed = parse_student_document(file_bytes=raw_content, file_name="resume.txt")
    assert parsed["undergrad_name"] == "北京大学"
    assert parsed["undergrad_tier"] == "985"
    assert parsed["gpa_raw"] == "92.0/100"
    assert "高等数学" in parsed["prerequisite_grades"]
    assert len(parsed["experiences"]) >= 1


def test_api_upload_document_endpoint():
    client = TestClient(app)
    session_id = "test_doc_enhancement_sess"

    doc_text = """# 申请者档案
- 本科院校: 浙江大学 (985)
- 专业: 软件工程
- GPA: 3.88/4.0
- 雅思: 7.5, 口语: 7.0

## 先修课成绩
| 高等数学 | 95 |
| 线性代数 | 92 |
| 数据结构与算法 | 96 |

## 实习经历
### 字节跳动系统架构实习
在基础架构组重构了RPC连接池，将连接建立时间缩短了30ms，保障万级QPS稳定吞吐。
"""

    resp = client.post(
        "/api/profile/upload-document",
        json={
            "session_id": session_id,
            "file_name": "student_resume.md",
            "file_type": "text/markdown",
            "text_content": doc_text
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["parsed"]["undergrad_name"] == "浙江大学"
    assert data["profile"]["undergrad_name"] == "浙江大学"
    assert "高等数学" in data["profile"]["prerequisite_grades"]
    assert len(data["experiences"]) >= 1


def test_api_programs_listing_and_filter():
    client = TestClient(app)

    # All programs
    resp_all = client.get("/api/programs")
    assert resp_all.status_code == 200
    all_data = resp_all.json()
    assert all_data["status"] == "success"
    assert all_data["count"] > 0

    # Query search: Carnegie Mellon
    resp_q = client.get("/api/programs?query=cmu")
    assert resp_q.status_code == 200
    q_data = resp_q.json()
    assert q_data["count"] >= 1
    assert any("cmu" in p["id"].lower() for p in q_data["programs"])

    # Region search: US
    resp_us = client.get("/api/programs?region=US")
    assert resp_us.status_code == 200
    us_data = resp_us.json()
    assert all(p.get("region") == "US" for p in us_data["programs"])


def test_api_facet_prerequisites():
    client = TestClient(app)
    session_id = "test_facet_prereq_sess"

    resp = client.get(f"/api/facet/prerequisites?session_id={session_id}&target_major=CS")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["target_major"] == "CS"
    assert len(data["alignment_table"]) >= 4
    assert "critical_advice" in data


def test_api_echo_evaluate_answer():
    client = TestClient(app)
    session_id = "test_echo_eval_sess"

    resp = client.post(
        "/api/echo/evaluate-answer",
        json={
            "session_id": session_id,
            "question_text": "Tell us about a time you handled a distributed timeout.",
            "answer_text": "When our queue lagged under 14% packet drops, I designed an asynchronous ring buffer to dynamically regulate backoff intervals, cutting recovery latency by 28% and sustaining 15000 QPS.",
            "interview_type": "kira_video",
            "program_id": "cmu_msit_se"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "evaluation" in data
    eval_res = data["evaluation"]
    assert "scores" in eval_res
    assert "refined_sample_answer" in eval_res
    assert eval_res["scores"]["composite"] > 60


def test_add_program_to_matrix_via_patch():
    client = TestClient(app)
    session_id = "test_matrix_patch_sess"

    # Patch new custom program into matrix
    custom_prog = {
        "id": "cmu_msit_se",
        "name_cn": "卡耐基梅隆大学 - 软件工程硕士",
        "name_en": "Carnegie Mellon University - MSIT-SE",
        "tier_bracket": "Reach",
        "university": "Carnegie Mellon University",
        "region": "US"
    }

    resp = client.post(
        "/api/canvas/patch-state",
        json={
            "session_id": session_id,
            "state_patch": {
                "shortlisted_programs": [custom_prog]
            }
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    progs = data["profile"]["shortlisted_programs"]
    assert len(progs) == 1
    assert progs[0]["id"] == "cmu_msit_se"
