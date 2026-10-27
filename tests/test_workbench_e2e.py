"""End-to-end integration tests for Milestone 2:
FastAPI Streaming Gateway and PrismEra Dark Optical Workbench.
"""

import json
from fastapi.testclient import TestClient
from prismera.api.server import app, SESSION_REGISTRY


def test_workbench_static_assets_serving():
    """Verify that Web Workbench static files (HTML, CSS, JS) are correctly served."""
    client = TestClient(app)

    # 1. Main HTML index
    resp_index = client.get("/")
    assert resp_index.status_code == 200
    assert "PrismEra" in resp_index.text
    assert "棱镜纪" in resp_index.text
    assert "left-pane-chat" in resp_index.text
    assert "right-pane-canvas" in resp_index.text
    assert "profile-switcher-wrapper" in resp_index.text
    assert "btn-export-dossier" in resp_index.text
    assert "export-dossier-modal" in resp_index.text

    # 2. Dark optical CSS
    resp_css = client.get("/css/style.css")
    assert resp_css.status_code == 200
    assert "text/css" in resp_css.headers.get("content-type", "")
    assert "--bg-deep-void: #090a0f;" in resp_css.text
    assert "c-luminary" in resp_css.text
    assert "c-facet" in resp_css.text
    assert "c-locus" in resp_css.text
    assert "c-disperser" in resp_css.text
    assert "c-resonator" in resp_css.text
    assert "btn-export-dossier" in resp_css.text
    assert "optic-modal-backdrop" in resp_css.text

    # 3. Dynamic client JS engine
    resp_js = client.get("/js/app.js")
    assert resp_js.status_code == 200
    assert "javascript" in resp_js.headers.get("content-type", "")
    assert "AGENT_CONFIGS" in resp_js.text
    assert "handleSseEvent" in resp_js.text
    assert "loadProfileList" in resp_js.text
    assert "openExportModal" in resp_js.text


def test_api_health_endpoint():
    """Verify gateway health check."""
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "luminary" in data["agents"]
    assert "locus" in data["agents"]
    assert "disperser" in data["agents"]


def test_sse_streaming_protocol_and_events():
    """Verify POST /api/chat/stream delivers the required SSE event contract."""
    client = TestClient(app)
    session_id = "e2e_stream_test_01"

    event_sequence = []
    tokens_received = []
    thoughts_received = []
    tools_called = []

    prompt = "我是浙江大学软件工程本科，目前均分88.5分，雅思总分7.5、口语7.0，目标是美研CS项目！"

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": session_id, "message": prompt}
    ) as response:
        assert response.status_code == 200
        current_event = None

        for line in response.iter_lines():
            line_str = line.strip()
            if line_str.startswith("event: "):
                current_event = line_str.replace("event: ", "").strip()
                event_sequence.append(current_event)
            elif line_str.startswith("data: ") and current_event:
                payload_str = line_str.replace("data: ", "").strip()
                try:
                    payload = json.loads(payload_str)
                    if current_event == "token":
                        tokens_received.append(payload.get("token", ""))
                    elif current_event == "thought":
                        thoughts_received.append(payload.get("thought", ""))
                    elif current_event == "tool_call":
                        tools_called.append(payload.get("tool", ""))
                except Exception:
                    pass

    # Verify key SSE events received
    assert "start" in event_sequence
    assert "agent_switch" in event_sequence
    assert "token" in event_sequence
    assert "profile_update" in event_sequence
    assert "done" in event_sequence

    # Verify tokens were streamed
    full_text = "".join(tokens_received)
    assert len(full_text) > 20

    # Verify spectrum state was updated
    spec_resp = client.get(f"/api/session/{session_id}/spectrum")
    assert spec_resp.status_code == 200
    spec = spec_resp.json()
    profile = spec["profile"]
    assert profile["undergrad_name"] == "浙江大学"
    assert profile["undergrad_tier"] == "985"
    assert "88.5" in (profile.get("gpa_raw") or "")
    assert profile["language_scores"].get("IELTS_total") == 7.5


def test_profile_upload_and_spectrum_query():
    """Verify manual profile updates and JSON synchronization."""
    client = TestClient(app)
    session_id = "e2e_profile_upload_02"

    # Direct manual update
    patch_payload = {
        "session_id": session_id,
        "profile": {
            "undergrad_name": "清华大学",
            "undergrad_tier": "985",
            "major": "计算机科学与技术 (CS)",
            "gpa_raw": "91.2/100",
            "language_scores": {"TOEFL_total": 110.0, "speaking": 27.0},
            "target_regions": ["US"],
            "target_majors": ["CS"]
        }
    }

    up_resp = client.post("/api/profile/upload", json=patch_payload)
    assert up_resp.status_code == 200
    up_data = up_resp.json()
    assert up_data["status"] == "success"
    assert up_data["profile"]["undergrad_name"] == "清华大学"
    assert up_data["profile"]["gpa_raw"] == "91.2/100"

    # Query spectrum
    query_resp = client.get(f"/api/session/{session_id}/spectrum")
    assert query_resp.status_code == 200
    q_data = query_resp.json()
    assert q_data["profile"]["undergrad_name"] == "清华大学"
    assert q_data["profile"]["language_scores"]["TOEFL_total"] == 110.0


def _consume_stream(client: TestClient, session_id: str, message: str) -> list[str]:
    """Helper to synchronously consume the entire SSE response."""
    events = []
    with client.stream("POST", "/api/chat/stream", json={"session_id": session_id, "message": message}) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("event: "):
                events.append(line.replace("event: ", "").strip())
    return events


def test_multi_turn_agent_handoff_and_stages():
    """Test full multi-turn optical workflow:
    Turn 1: Credential input & Locus school selection
    Turn 2: Disperser Socratic interview and story mining
    Turn 3: Blueprint generation
    """
    client = TestClient(app)
    session_id = "e2e_multi_turn_03"

    # Turn 1: Feed complete credentials and ask for school recommendations
    turn1_msg = "我是浙江大学软件工程本科，目前均分88.5分，雅思总分7.5、口语7.0，目标是美研CS项目！"
    _consume_stream(client, session_id, turn1_msg)

    spec1 = client.get(f"/api/session/{session_id}/spectrum").json()
    assert spec1["profile"]["undergrad_name"] == "浙江大学"

    # Turn 2: Request Disperser SOP assistance
    turn2_msg = "选校很清晰了，我想开始准备 CMU 软件工程项目的 SOP 文书，怎么写比较出彩？"
    _consume_stream(client, session_id, turn2_msg)

    spec2 = client.get(f"/api/session/{session_id}/spectrum").json()
    assert spec2["sop_stage"] >= 1

    # Turn 3: Reply with granular engineering challenge
    turn3_msg = (
        "我们在做分布式消息队列时，遇到网络分区下传统心跳算法导致雪崩的问题。"
        "我亲自编写了基于异步环形缓冲区的自适应调度器，调整了超时重试窗口，使系统在15%网络丢包下延迟降低了32ms。"
    )
    _consume_stream(client, session_id, turn3_msg)

    spec3 = client.get(f"/api/session/{session_id}/spectrum").json()
    # Mined fragments should now contain the story
    fragments = spec3["profile"].get("mined_story_fragments", [])
    assert len(fragments) >= 1
    assert any("网络分区" in f or "32ms" in f for f in fragments)
    assert spec3["sop_stage"] == 2
