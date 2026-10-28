"""PrismEra Milestone 8: Full-Stack End-to-End Acceptance Tests.

Validates the complete closed-loop lifecycle:
1. System Health Check & Static Workbench Hosting
2. Admin Console Lifecycle (Hot-switching, Connection Testing, Graph & Vector Ingestion, Benchmark Online Run)
3. Full Student Journey & 6 Optical Agents Streaming Dialog Routing
4. Canvas State Two-Way Mutation (Patching, Outline Confirmation, Refraction)
5. Multi-Format Dossier Report Export (HTML, Markdown, JSON Preview)
6. Session Reset & Lifecycle Cleanup
"""

import json
from fastapi.testclient import TestClient

from prismera.api.server import app, SESSION_REGISTRY
from prismera.config import get_current_config, update_llm_config


def test_fullstack_health_and_static_mount():
    """Verify system health and FastAPI single-port web static hosting."""
    client = TestClient(app)

    # 1. API Health Check
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert "version" in health_data
    assert len(health_data["agents"]) == 6
    assert "luminary" in health_data["agents"]
    assert "echo" in health_data["agents"]

    # 2. Single-Port Root Static Web Workbench Check
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "text/html" in root_resp.headers.get("content-type", "")
    assert "PrismEra" in root_resp.text
    assert "prism-console-modal" in root_resp.text
    assert "btn-open-console" in root_resp.text

    # 3. CSS & JS Asset Integrity Check
    css_resp = client.get("/css/style.css")
    assert css_resp.status_code == 200
    assert "btn-console-trigger" in css_resp.text

    js_resp = client.get("/js/app.js")
    assert js_resp.status_code == 200
    assert "prismConsoleModal" in js_resp.text


def test_admin_console_api_lifecycle():
    """Verify Admin Console hot-switching, graph & vector ingestion, and online benchmark."""
    client = TestClient(app)

    # 1. Config Retrieval
    cfg_resp = client.get("/api/admin/config")
    assert cfg_resp.status_code == 200
    cfg_data = cfg_resp.json()
    assert cfg_data["status"] == "success"
    assert "config" in cfg_data
    assert "engine_mode" in cfg_data

    # 2. Config Hot-Update
    update_payload = {
        "offline_mock": True,
        "temperature": 0.15,
        "model": "gpt-4o-mini-test"
    }
    patch_resp = client.post("/api/admin/config", json=update_payload)
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["status"] == "success"
    assert patch_data["config"]["is_offline_mock"] is True

    # 3. Connection Test
    test_conn_resp = client.post("/api/admin/config/test", json={"provider": "mock"})
    assert test_conn_resp.status_code == 200
    test_data = test_conn_resp.json()
    assert test_data["status"] == "ok"
    assert test_data["mode"] == "mock"
    assert test_data["latency_ms"] >= 0

    # 4. Knowledge Base Statistics
    stats_resp = client.get("/api/admin/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    initial_programs = stats_data["stats"]["programs_count"]
    initial_cases = stats_data["stats"]["total_admission_cases"]
    assert initial_programs >= 10
    assert initial_cases >= 20

    # 5. Online Ingestion: GraphStore Node
    new_program_id = "test_e2e_cambridge_acs"
    node_payload = {
        "node_type": "Program",
        "id": new_program_id,
        "name": "MPhil in Advanced Computer Science (E2E Test)",
        "properties": {
            "degree": "Master",
            "region": "UK",
            "major_category": "CS",
            "min_gpa": 90.0,
            "min_ielts_total": 7.5,
            "tier_requirement": ["985", "211"]
        },
        "university_id": "cambridge"
    }
    node_resp = client.post("/api/admin/graph/node", json=node_payload)
    assert node_resp.status_code == 200
    node_data = node_resp.json()
    assert node_data["status"] == "success"
    assert node_data["stats"]["programs_count"] >= initial_programs

    # 6. Online Ingestion: VectorStore Case
    case_payload = {
        "target_program_id": new_program_id,
        "undergrad_name": "清华大学",
        "undergrad_tier": "985",
        "gpa": 91.2,
        "gpa_scale": "100",
        "major": "计算机科学与技术",
        "language": "雅思 8.0 (口语 7.5)",
        "background_summary": "E2E端到端验证录取案例，两篇OSDI一作",
        "outcome": "ADMIT",
        "outcome_type": "admit",
        "year": 2026
    }
    case_resp = client.post("/api/admin/cases", json=case_payload)
    assert case_resp.status_code == 200
    case_data = case_resp.json()
    assert case_data["status"] == "success"
    assert case_data["stats"]["total_admission_cases"] >= initial_cases + 1

    # 7. Online Benchmark Trigger & Inspection
    bench_resp = client.post("/api/admin/benchmark/run")
    assert bench_resp.status_code == 200
    bench_data = bench_resp.json()
    assert bench_data["status"] == "success"
    assert "report" in bench_data
    gr_metrics = bench_data["report"]["metrics"]["prismera_graphrag"]
    assert gr_metrics["Hard_Constraint_Precision"] == 100.0
    assert gr_metrics["Stage_Gate_Compliance"] == 100.0
    assert gr_metrics["Anti_AI_Lexicon_Clean_Rate"] == 100.0
    assert gr_metrics["Citation_Faithfulness"] == 100.0

    # 8. Retrieve Latest Benchmark Report
    latest_resp = client.get("/api/admin/benchmark/latest")
    assert latest_resp.status_code == 200
    assert latest_resp.json()["status"] == "success"


def test_e2e_student_lifecycle_and_multiagent_routing():
    """Verify full applicant lifecycle: resume ingestion -> agent routing -> canvas mutations -> export."""
    client = TestClient(app)
    session_id = "test_e2e_student_lifecycle_01"

    # 1. Create Student Session Profile
    create_resp = client.post("/api/session/create", json={
        "session_id": session_id,
        "name": "陆光 (E2E Test Applicant)",
        "initial_profile": {
            "undergrad_name": "浙江大学",
            "undergrad_tier": "985",
            "major": "计算机科学与技术 (CS)",
            "gpa_raw": "88.5/100",
            "language_scores": {"IELTS_total": 7.5, "speaking": 7.0},
            "target_regions": ["US", "UK"],
            "target_majors": ["CS"]
        }
    })
    assert create_resp.status_code == 200
    assert create_resp.json()["status"] == "success"

    # 2. Upload and Parse Document / Resume Text
    sample_resume = (
        "本科院校: 浙江大学 (985)\n"
        "专业: 计算机科学与技术 (CS)\n"
        "均分: 88.5/100\n"
        "雅思总分: 7.5, 口语: 7.0\n"
        "核心先修课: 数据结构与算法 95分，操作系统 92分，计算机网络 89分\n"
        "实习经历: 腾讯科技后台微服务架构开发，负责高并发环形缓冲区设计\n"
        "科研经历: eBPF 网络自适应重传调度，降低故障恢复延迟 28%"
    )
    upload_resp = client.post("/api/profile/upload", json={
        "session_id": session_id,
        "text": sample_resume
    })
    assert upload_resp.status_code == 200
    profile_data = upload_resp.json()["profile"]
    assert profile_data["undergrad_name"] == "浙江大学"
    assert profile_data["undergrad_tier"] == "985"

    # 3. Stream Interaction & Multi-Agent Routing
    # 3.1 Ironclad Rule Interception on Missing Params
    interception_events = []
    with client.stream("POST", "/api/chat/stream", json={
        "session_id": session_id,
        "message": "我想直接选校，帮我列个保底和冲刺清单？"
    }) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event: "):
                interception_events.append(line.replace("event: ", "").strip())

    assert "start" in interception_events
    assert "token" in interception_events
    assert "done" in interception_events

    # 3.2 Locus (定焦师) Routing with Full Parameters
    locus_events = []
    with client.stream("POST", "/api/chat/stream", json={
        "session_id": session_id,
        "message": "我是浙江大学软件工程本科，目前均分88.5分，雅思总分7.5、口语7.0，目标是美研和英研CS项目！"
    }) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event: "):
                locus_events.append(line.replace("event: ", "").strip())

    assert "agent_switch" in locus_events

    # Verify spectrum updated in state
    spec_resp = client.get(f"/api/session/{session_id}/spectrum")
    assert spec_resp.status_code == 200
    spec_json = spec_resp.json()
    assert spec_json["profile"]["undergrad_name"] == "浙江大学"
    assert spec_json["profile"]["undergrad_tier"] == "985"

    # 3.3 Facet (切面师) Prerequisite & Transcript Diagnosis
    facet_events = []
    with client.stream("POST", "/api/chat/stream", json={
        "session_id": session_id,
        "message": "定校很有底了！请切面师帮我深度诊断一下成绩单和先修课，看看是否有结构性暗区？"
    }) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event: "):
                facet_events.append(line.replace("event: ", "").strip())

    assert "agent_switch" in facet_events

    # 3.4 Disperser (折光师) Socratic SOP Co-creation
    disperser_events = []
    with client.stream("POST", "/api/chat/stream", json={
        "session_id": session_id,
        "message": "选校和背景都清晰了，我想开始准备 CMU 软件工程项目的 SOP 文书，怎么写比较出彩？"
    }) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event: "):
                disperser_events.append(line.replace("event: ", "").strip())

    assert "agent_switch" in disperser_events

    # 3.5 Resonator (共鸣者) Academic Cold Email & Paper Synergy
    resonator_events = []
    with client.stream("POST", "/api/chat/stream", json={
        "session_id": session_id,
        "message": "我还想申请 UIUC 分布式系统博士，想联系 Indranil Gupta 教授，请检索最新论文并帮我写套磁信。"
    }) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event: "):
                resonator_events.append(line.replace("event: ", "").strip())

    assert "agent_switch" in resonator_events

    # 3.6 Echo (回音壁) Kira Mock Interview Generation
    echo_events = []
    with client.stream("POST", "/api/chat/stream", json={
        "session_id": session_id,
        "message": "请回音壁为我发起卡耐基梅隆 MSIT-SE 项目的 Kira 模拟面试第一题。"
    }) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event: "):
                echo_events.append(line.replace("event: ", "").strip())

    assert "agent_switch" in echo_events

    # 4. Canvas State Two-Way Mutation
    # 4.1 State Patching
    patch_canvas_resp = client.post("/api/canvas/patch-state", json={
        "session_id": session_id,
        "state_patch": {
            "locked_program_id": "cmu_msit_se",
            "sop_stage": 2
        }
    })
    assert patch_canvas_resp.status_code == 200
    assert patch_canvas_resp.json()["status"] == "success"

    # 4.2 Outline Confirmation
    outline_resp = client.post("/api/canvas/confirm-outline", json={
        "session_id": session_id,
        "confirmed_points": {
            "hook": "以真实网络丢包下的分布式雪崩切入",
            "body": "阐述 eBPF 环形缓冲区自适应重传核心架构",
            "why_school": "CMU ISR 软件工程研究所的顶级系统实验环境"
        }
    })
    assert outline_resp.status_code == 200
    assert outline_resp.json()["profile"]["sop_stage"] in [3, 4]

    # 4.3 Text Refraction Diff
    refract_resp = client.post("/api/canvas/refract-selection", json={
        "session_id": session_id,
        "selected_text": "I was responsible for developing microservice backend modules.",
        "instruction": "去 AI 腔调，突出具体工程指标与攻坚细节"
    })
    assert refract_resp.status_code == 200
    assert refract_resp.json()["status"] == "success"
    assert "rewritten_text" in refract_resp.json()

    # 5. Export Dossier Report
    # 5.1 Preview Metadata
    preview_resp = client.get(f"/api/session/{session_id}/export/preview")
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    assert preview_data["session_id"] == session_id
    assert "markdown" in preview_data
    assert "html" in preview_data
    assert len(preview_data["markdown"]) > 100

    # 5.2 HTML Full Export
    html_resp = client.get(f"/api/session/{session_id}/export?format=html")
    assert html_resp.status_code == 200
    assert "text/html" in html_resp.headers["content-type"]
    assert "PrismEra" in html_resp.text
    assert "浙" in html_resp.text

    # 5.3 Markdown Full Export
    md_resp = client.get(f"/api/session/{session_id}/export?format=markdown")
    assert md_resp.status_code == 200
    assert "text/markdown" in md_resp.headers["content-type"]
    assert "《PrismEra 个人升学光谱全案报告》" in md_resp.text

    # 5.4 JSON Full Export
    json_resp = client.get(f"/api/session/{session_id}/export?format=json")
    assert json_resp.status_code == 200
    dossier_json = json_resp.json()
    assert "meta" in dossier_json
    assert "student_profile" in dossier_json

    # 6. Session Reset & Lifecycle Cleanup
    reset_resp = client.post("/api/session/reset", json={"session_id": session_id})
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "reset_successful"
