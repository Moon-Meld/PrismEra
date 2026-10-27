"""Unit tests for Milestone 5: The Echo (prism_echo) mock interview and timeline pilot."""

import pytest
from prismera.tools.echo_tools import (
    retrieve_interview_question_bank,
    evaluate_interview_answer,
    generate_application_timeline,
)
from prismera.agents.echo import echo_node
from prismera.engine import PrismEraSession
from prismera.state import create_initial_spectrum_profile, PrismEraState
from fastapi.testclient import TestClient
from prismera.api.server import app


# =============================================================================
# 1. TOOL UNIT TESTS
# =============================================================================

def test_retrieve_interview_question_bank_types():
    """Verify question bank retrieval across Kira, alumni, and technical types."""
    # Kira video
    kira_qs = retrieve_interview_question_bank("cmu_msit_se", "kira_video")
    assert len(kira_qs) >= 2
    assert kira_qs[0]["interview_type"] == "kira_video"
    assert "Kira" in kira_qs[0]["type_label"]
    assert kira_qs[0]["prep_time_seconds"] == 45
    assert kira_qs[0]["response_time_seconds"] == 90
    assert "evaluation_rubric" in kira_qs[0]

    # Alumni behavioral
    alumni_qs = retrieve_interview_question_bank("cmu_msit_se", "alumni_behavioral")
    assert len(alumni_qs) >= 1
    assert alumni_qs[0]["interview_type"] == "alumni_behavioral"
    assert "校友" in alumni_qs[0]["type_label"]

    # Professor technical
    tech_qs = retrieve_interview_question_bank("uiuc_mcs", "professor_technical")
    assert len(tech_qs) >= 1
    assert tech_qs[0]["interview_type"] == "professor_technical"
    assert "学术" in tech_qs[0]["type_label"] or "技术" in tech_qs[0]["type_label"]

    # Fallback to general question bank for unknown program
    gen_qs = retrieve_interview_question_bank("unknown_univ_prog", "kira_video")
    assert len(gen_qs) > 0
    assert gen_qs[0]["interview_type"] == "kira_video"


def test_evaluate_interview_answer_dimensions():
    """Verify 3-dimensional evaluation: Content Relevance, STAR Completeness, and Fluency."""
    sample_q = {
        "id": "cmu_test_q1",
        "question": "Tell us about a time you solved an asynchronous network partition under high load.",
        "category": "Systems Resilience",
        "interview_type": "kira_video",
        "prep_time_seconds": 45,
        "response_time_seconds": 90,
    }

    # High-caliber technical answer
    good_answer = (
        "When our cluster experienced 14% packet drops during simulated cross-datacenter partition, "
        "our goal was to avoid cascading timeout loops. I engineered an adaptive scheduler with an "
        "asynchronous ring buffer in kernel space. By dynamically throttling retries based on RTT variance, "
        "I reduced failover latency by 28% and maintained 15,000 QPS."
    )

    profile = {
        "mined_story_fragments": ["eBPF自适应调度器与网络丢包容错 (28%延迟降低)"]
    }

    res = evaluate_interview_answer(sample_q, good_answer, student_profile=profile)

    assert "scores" in res
    scores = res["scores"]
    assert scores["content_relevance"] >= 80
    assert scores["star_structure"] >= 80
    assert scores["linguistic_authenticity"] >= 80
    assert scores["composite"] >= 80

    # STAR breakdown check
    star = res["star_breakdown"]
    assert star["Situation"]["present"] is True
    assert star["Action"]["present"] is True
    assert star["Result"]["present"] is True

    # Refined sample answer check
    assert "refined_sample_answer" in res
    assert len(res["refined_sample_answer"].split()) > 50
    assert res["estimated_speaking_seconds"] > 30


def test_evaluate_interview_answer_banned_ai_words():
    """Verify detection of AI cliches (delve into, pivotal, etc.) lowers linguistic score."""
    sample_q = "Why do you want to join this program?"
    banned_answer = (
        "I want to delve into this pivotal curriculum, which is a testament to academic excellence. "
        "It will ignite my interest in the realm of computing."
    )
    res = evaluate_interview_answer(sample_q, banned_answer)
    notes = " ".join(res["feedback"]["linguistic_authenticity"])
    assert "AI 塑料腔" in notes or "delve" in notes


def test_generate_application_timeline_chronological():
    """Verify timeline sorts by deadline ascending and includes RL milestones & checklist."""
    shortlisted = [
        {
            "id": "prog_feb",
            "name_cn": "二月截止项目",
            "name_en": "February Program",
            "deadline": "2027-02-15",
            "tier_bracket": "Match",
        },
        {
            "id": "prog_dec",
            "name_cn": "十二月早申项目",
            "name_en": "December Program",
            "deadline": "2026-12-01 (Priority)",
            "tier_bracket": "Reach",
        },
        {
            "id": "prog_jan",
            "name_cn": "一月常规项目",
            "name_en": "January Program",
            "deadline": "2027-01-15 (Regular)",
            "tier_bracket": "Safety",
        }
    ]

    timeline_data = generate_application_timeline(shortlisted)
    assert len(timeline_data) == 3

    # Section 1: programs timeline
    assert timeline_data[0]["type"] == "programs_timeline"
    progs = timeline_data[0]["items"]
    assert len(progs) == 3
    # Strictly sorted in ascending date order
    assert progs[0]["deadline_date"] <= progs[1]["deadline_date"] <= progs[2]["deadline_date"]
    assert progs[0]["name_cn"] == "十二月早申项目"

    # Section 2: RL chasing milestones
    assert timeline_data[1]["type"] == "rl_chasing_milestones"
    rl_items = timeline_data[1]["items"]
    assert len(rl_items) == 4
    stages = [item["stage"] for item in rl_items]
    assert stages == ["T-60d", "T-30d", "T-14d", "T-3d"]

    # Section 3: materials checklist
    assert timeline_data[2]["type"] == "materials_checklist"
    cats = timeline_data[2]["items"]
    assert len(cats) >= 3


# =============================================================================
# 2. AGENT NODE & ROUTING TESTS
# =============================================================================

def test_echo_node_timeline_branch():
    """Verify echo_node handles timeline requests and updates application_timeline."""
    state: PrismEraState = {
        "messages": [{"role": "user", "content": "请帮我梳理当前锁定项目的网申时间轴、倒计时及推荐信催交节点。"}],
        "student_profile": create_initial_spectrum_profile(),
        "active_agent": "prism_echo",
        "routing_decision": "DELEGATE_TO_AGENT",
        "luminary_thought": "Delegating to echo",
        "task_briefing": "Generate timeline",
        "latest_response": None,
        "pending_human_review": None,
        "metadata": {},
    }
    state["student_profile"]["shortlisted_programs"] = [
        {"id": "cmu_msit_se", "name_cn": "CMU MSIT-SE", "deadline": "2027-01-15", "tier_bracket": "Reach"}
    ]

    output = echo_node(state)
    assert "网申时间轴倒计时" in output["latest_response"]
    assert "推荐信（RL）" in output["latest_response"]
    assert len(output["student_profile"]["application_timeline"]) > 0


def test_echo_node_interview_question_and_answer_cycle():
    """Verify echo_node starts interview, records pending question, and evaluates student reply."""
    profile = create_initial_spectrum_profile()

    # Turn 1: Start interview
    state1: PrismEraState = {
        "messages": [{"role": "user", "content": "请回音壁为我发起卡耐基梅隆 MSIT-SE 项目的 Kira 模拟面试第一题。"}],
        "student_profile": profile,
        "active_agent": "prism_echo",
        "routing_decision": "DELEGATE_TO_AGENT",
        "luminary_thought": None,
        "task_briefing": None,
        "latest_response": None,
        "pending_human_review": None,
        "metadata": {},
    }

    out1 = echo_node(state1)
    assert "全真模拟面试入场校准" in out1["latest_response"]
    assert "Question 01" in out1["latest_response"]
    records = out1["student_profile"]["interview_records"]
    assert len(records) == 1
    assert records[0]["status"] == "pending_answer"

    # Turn 2: User answers the question
    student_reply = (
        "In our distributed message queue project, when the network dropped 14% of heartbeat packets, "
        "I was responsible for stabilizing failovers. I engineered an adaptive scheduler with an asynchronous "
        "ring buffer to throttle packet retries dynamically. We achieved a 28% recovery latency reduction."
    )
    state2: PrismEraState = {
        "messages": [
            {"role": "user", "content": "请发起模拟面"},
            {"role": "assistant", "content": out1["latest_response"]},
            {"role": "user", "content": student_reply}
        ],
        "student_profile": out1["student_profile"],
        "active_agent": "prism_echo",
        "routing_decision": "DELEGATE_TO_AGENT",
        "luminary_thought": None,
        "task_briefing": None,
        "latest_response": None,
        "pending_human_review": None,
        "metadata": {},
    }

    out2 = echo_node(state2)
    assert "全真靶向模拟面试作答复盘" in out2["latest_response"]
    assert "三维多维综合评分雷达" in out2["latest_response"]
    assert "高分示范回答 (Refined Sample Answer)" in out2["latest_response"]

    updated_records = out2["student_profile"]["interview_records"]
    assert len(updated_records) == 1
    assert updated_records[0]["status"] == "completed"
    assert updated_records[0]["evaluation"]["scores"]["composite"] > 70


# =============================================================================
# 3. END-TO-END SESSION & API TESTS
# =============================================================================

def test_session_e2e_echo_routing():
    """Verify Luminary routes mock interview and timeline queries to prism_echo."""
    session = PrismEraSession(thread_id="test_echo_e2e")

    # Query 1: Interview routing
    res1 = session.send_user_message("我想练一下卡耐基梅隆 MSIT-SE 的 Kira 模拟面试")
    assert res1["active_agent"] in ["echo", "prism_echo"]
    assert "回音壁" in res1["latest_response"] or "模拟面试" in res1["latest_response"]
    assert len(session.state["student_profile"]["interview_records"]) > 0

    # Query 2: Timeline routing
    res2 = session.send_user_message("帮我排一下当前选校的网申时间轴与推荐信催交节点")
    assert res2["active_agent"] in ["echo", "prism_echo"]
    assert "时间轴" in res2["latest_response"]
    assert len(session.state["student_profile"]["application_timeline"]) > 0


def test_echo_api_gateway_endpoints():
    """Verify REST API endpoints for Echo question bank, timeline, and answer evaluation."""
    client = TestClient(app)

    # 1. Question bank endpoint
    resp_q = client.get("/api/echo/questions?program_id=cmu_msit_se&interview_type=kira_video")
    assert resp_q.status_code == 200
    q_data = resp_q.json()
    assert q_data["count"] >= 2
    assert q_data["questions"][0]["interview_type"] == "kira_video"

    # 2. Timeline generation endpoint
    resp_tl = client.post("/api/echo/generate-timeline", json={"session_id": "test_echo_api"})
    assert resp_tl.status_code == 200
    tl_data = resp_tl.json()
    assert tl_data["status"] == "success"
    assert len(tl_data["application_timeline"]) == 3

    # 3. Answer evaluation endpoint
    eval_payload = {
        "session_id": "test_echo_api",
        "question_text": "Describe a production bug you fixed.",
        "answer_text": "When cross-rack latency spiked, I decoupled the write path using an asynchronous ring buffer, decreasing P99 latency by 35ms.",
        "interview_type": "kira_video",
        "program_id": "cmu_msit_se"
    }
    resp_eval = client.post("/api/echo/evaluate-answer", json=eval_payload)
    assert resp_eval.status_code == 200
    eval_json = resp_eval.json()
    assert eval_json["status"] == "success"
    assert "scores" in eval_json["evaluation"]
    assert eval_json["evaluation"]["scores"]["composite"] > 70

    # 4. Spectrum retrieval includes interview_records and application_timeline
    resp_spec = client.get("/api/session/test_echo_api/spectrum")
    assert resp_spec.status_code == 200
    spec_data = resp_spec.json()
    assert "interview_records" in spec_data
    assert "application_timeline" in spec_data
    assert len(spec_data["interview_records"]) > 0
