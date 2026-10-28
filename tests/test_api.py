"""Tests for the PrismEra FastAPI Streaming Gateway."""

import json
from fastapi.testclient import TestClient
from prismera.api.server import app, SESSION_REGISTRY


def test_api_health():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "agents" in data


def test_chat_stream_and_spectrum():
    client = TestClient(app)
    session_id = "test_api_session_01"

    # 1. Post stream message
    events_received = []
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": session_id, "message": "你好，我想做留学规划"}
    ) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event: "):
                events_received.append(line.replace("event: ", "").strip())

    assert "start" in events_received
    assert "agent_switch" in events_received
    assert "token" in events_received
    assert "done" in events_received

    # 2. Get spectrum
    spec_resp = client.get(f"/api/session/{session_id}/spectrum")
    assert spec_resp.status_code == 200
    spec_data = spec_resp.json()
    assert spec_data["session_id"] == session_id
    assert "profile" in spec_data
    assert "messages" in spec_data
    assert len(spec_data["messages"]) >= 2


def test_profile_upload_and_manual_update():
    client = TestClient(app)
    session_id = "test_profile_session"

    # Direct structured update
    update_payload = {
        "session_id": session_id,
        "profile": {
            "undergrad_name": "浙江大学",
            "undergrad_tier": "985",
            "major": "计算机科学与技术 (CS)",
            "gpa_raw": "89.0/100",
            "language_scores": {"IELTS_total": 7.5, "speaking": 7.0},
            "target_regions": ["US", "UK"],
            "target_majors": ["CS"]
        }
    }
    resp = client.post("/api/profile/upload", json=update_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["profile"]["undergrad_name"] == "浙江大学"
    assert data["profile"]["gpa_raw"] == "89.0/100"

    # Heuristic text update
    resp_text = client.post(
        "/api/profile/upload",
        json={"session_id": session_id, "text": "我最近考出了托福105，口语25分"}
    )
    assert resp_text.status_code == 200
    text_data = resp_text.json()
    assert text_data["profile"]["language_scores"]["TOEFL_total"] == 105.0


def test_session_reset():
    client = TestClient(app)
    session_id = "test_reset_session"

    client.post("/api/profile/upload", json={
        "session_id": session_id,
        "profile": {"undergrad_name": "清华大学"}
    })

    reset_resp = client.post("/api/session/reset", json={"session_id": session_id})
    assert reset_resp.status_code == 200
    reset_data = reset_resp.json()
    assert reset_data["status"] == "reset_successful"
    assert reset_data["profile"]["undergrad_name"] is None


def test_upload_document_endpoint():
    import base64
    client = TestClient(app)
    session_id = "test_doc_upload_sess"

    resume_text = """# 个人简历
- 本科院校: 清华大学 (985)
- 专业: 计算机科学与技术
- 均分成绩: 91.5/100
- 雅思: 8.0, 口语: 7.5

## 核心先修课
| 课程 | 成绩 |
| 高等数学 | 98 |
| 线性代数 | 95 |

## 科研与实习经历
### 分布式缓存研发
在项目中针对高并发热点Key击穿，自研了基于双重检查锁与异步刷新的热点拦截器，将P99延时从120ms降低至18ms，支撑50000 QPS。
"""

    # 1. Test raw text content upload
    resp = client.post(
        "/api/profile/upload-document",
        json={
            "session_id": session_id,
            "file_name": "resume.md",
            "file_type": "text/markdown",
            "text_content": resume_text
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["parsed"]["undergrad_name"] == "清华大学"
    assert data["profile"]["gpa_raw"] == "91.5/100"
    assert "高等数学" in data["profile"]["prerequisite_grades"]
    assert len(data["experiences"]) >= 1

    # 2. Test base64 content upload
    b64_payload = base64.b64encode(resume_text.encode("utf-8")).decode("utf-8")
    resp_b64 = client.post(
        "/api/profile/upload-document",
        json={
            "session_id": session_id + "_b64",
            "file_name": "resume_b64.txt",
            "file_type": "text/plain",
            "content_base64": b64_payload
        }
    )
    assert resp_b64.status_code == 200
    data_b64 = resp_b64.json()
    assert data_b64["parsed"]["undergrad_name"] == "清华大学"


def test_list_programs_and_facet_prerequisites():
    client = TestClient(app)

    # 1. Programs list & search
    resp = client.get("/api/programs?query=cmu")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["count"] >= 1
    assert any("cmu" in p["id"].lower() or "carnegie" in p.get("name_en", "").lower() for p in data["programs"])

    # 2. Filter by region
    resp_uk = client.get("/api/programs?region=UK")
    assert resp_uk.status_code == 200
    data_uk = resp_uk.json()
    assert all(p.get("region") == "UK" for p in data_uk["programs"])

    # 3. Facet prerequisites endpoint
    resp_prereq = client.get("/api/facet/prerequisites?target_major=CS")
    assert resp_prereq.status_code == 200
    prereq_data = resp_prereq.json()
    assert prereq_data["status"] == "success"
    assert prereq_data["target_major"] == "CS"
    assert len(prereq_data["alignment_table"]) > 0
