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
