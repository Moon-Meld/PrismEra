"""Integration tests for Milestone 4: LangGraph Human-in-the-Loop (HITL) breakpoints,
state mutation write-back, and canvas inline refraction with version rollback.
"""

from fastapi.testclient import TestClient
from prismera.engine import PrismEraSession
from prismera.api.server import app, SESSION_REGISTRY
from prismera.agents.disperser import refract_text_selection, compute_word_diff


def test_word_diff_computation():
    """Verify compute_word_diff generates high-contrast <ins> and <del> tags and structured ops."""
    old_s = "I realized that textbook consensus models rarely anticipate real-world failure."
    new_s = "I observed that theoretical models collapse under real-world network partitions."
    diff_html, ops = compute_word_diff(old_s, new_s)

    assert '<del class="diff-del">' in diff_html
    assert '<ins class="diff-ins">' in diff_html
    assert any(op["op"] == "delete" for op in ops)
    assert any(op["op"] == "insert" for op in ops)


def test_refract_text_selection_deterministic():
    """Verify refract_text_selection rewrites selected snippet, enforces Anti-AI and returns preview."""
    selected = "During my engineering practicum, I redesigned our thread contention pipeline by introducing an asynchronous ring buffer."
    instruction = "结合我刚补充的腾讯实习指标强化这一句"
    full_doc = f"Heading\n{selected}\nConclusion"

    res = refract_text_selection(
        selected_text=selected,
        instruction=instruction,
        full_text=full_doc,
        student_profile={"major": "CS"}
    )

    assert res["original_text"] == selected
    assert "Tencent" in res["rewritten_text"] or "腾讯" in res["rewritten_text"] or "QPS" in res["rewritten_text"]
    assert '<ins class="diff-ins">' in res["diff_html"]
    assert res["full_text_preview"] is not None
    assert selected not in res["full_text_preview"]
    assert res["rewritten_text"] in res["full_text_preview"]


def test_locus_breakpoint_and_state_patching():
    """Verify Locus triggers locus_matrix breakpoint and patch_state writes back to Checkpointer."""
    session = PrismEraSession(thread_id="test_hitl_locus")
    # Trigger locus
    msg = "我是浙江大学计算机本科，均分88.5分，雅思7.5口语7.0，目标美研CS项目，请帮我定校"
    res = session.send_user_message(msg)

    assert res["pending_human_review"] == "locus_matrix"
    profile = res["student_profile"]
    programs = profile["shortlisted_programs"]
    assert len(programs) >= 2

    # User interacts with canvas:
    # 1. Modify tier bracket of first program
    first_prog = programs[0]
    first_prog_id = first_prog["id"]
    original_bracket = first_prog.get("tier_bracket", "Reach")
    new_bracket = "Safety" if original_bracket != "Safety" else "Reach"

    modified_programs = list(programs)
    modified_programs[0]["tier_bracket"] = new_bracket

    # 2. Lock target program for SOP
    target_lock = dict(modified_programs[0])

    patch_payload = {
        "shortlisted_programs": modified_programs,
        "locked_target_program": target_lock,
        "pending_human_review": None,  # User confirmed matrix
    }

    # Test patch_state called on class
    patch_res = PrismEraSession.patch_state("test_hitl_locus", patch_payload)
    assert patch_res["status"] == "success"
    assert session.state["student_profile"]["shortlisted_programs"][0]["tier_bracket"] == new_bracket
    assert session.state["student_profile"]["locked_target_program"]["id"] == first_prog_id
    assert session.state["pending_human_review"] is None

    # Verify state written back into LangGraph Checkpointer
    config = {"configurable": {"thread_id": "test_hitl_locus"}}
    checkpointed = session.app.get_state(config)
    assert checkpointed.values["student_profile"]["shortlisted_programs"][0]["tier_bracket"] == new_bracket
    assert checkpointed.values["pending_human_review"] is None


def test_disperser_stage2_breakpoint_and_outline_co_creation():
    """Verify Disperser Stage 2 outline breakpoint, outline manual edit and progression to Stage 3."""
    session = PrismEraSession(thread_id="test_hitl_disperser")

    # Step 1: Trigger Disperser
    session.send_user_message("帮我写CMU软件工程硕士的SOP文书")

    # Step 2: Answer Socratic questions with engineering details
    details = (
        "我们在做分布式消息队列时，遇到网络分区下传统心跳算法导致雪崩的问题。"
        "我亲自编写了基于异步环形缓冲区的自适应调度器，调整了超时重试窗口，使系统在15%网络丢包下延迟降低了32ms。"
    )
    res2 = session.send_user_message(details)

    # Must be at Stage 2 and suspended for HITL review
    assert res2["pending_human_review"] == "disperser_outline"
    profile = res2["student_profile"]
    assert profile["sop_stage"] == 2
    assert "sop_outline" in profile
    assert len(profile["sop_outline"]) == 3
    assert len(profile["sop_versions"]) >= 1
    assert profile["sop_versions"][0]["stage"] == 2

    # Step 3: User edits outline on the canvas (e.g. adds custom point to Hook)
    outline = list(profile["sop_outline"])
    outline[0]["points"].append("自定义工程要点：实测单机吞吐瓶颈达到12万QPS时的GC停顿排查。")

    session.patch_state({"sop_outline": outline})
    assert len(session.state["student_profile"]["sop_outline"][0]["points"]) == 3

    # Step 4: User confirms outline and requests drafting
    res3 = session.send_user_message("确认大纲并执笔")
    assert res3["pending_human_review"] is None
    profile3 = res3["student_profile"]
    assert profile3["sop_stage"] in [3, 4]
    assert profile3["sop_draft"] != ""
    assert "distributed message queue" in profile3["sop_draft"]
    assert len(profile3["sop_versions"]) >= 2
    assert profile3["sop_versions"][-1]["stage"] == 3


def test_api_canvas_refract_accept_and_rollback():
    """Integration test for API endpoints: /api/canvas/refract-selection, accept, and rollback."""
    client = TestClient(app)
    session_id = "test_api_canvas_full"

    # 1. Initialize session with a draft and version v1.0
    initial_draft = (
        "When our distributed message queue dropped 14% of heartbeats under simulated latency, "
        "I realized that textbook consensus models rarely anticipate real-world failure."
    )
    init_patch = {
        "session_id": session_id,
        "state_patch": {
            "student_profile": {
                "sop_stage": 3,
                "sop_draft": initial_draft,
                "sop_versions": [
                    {
                        "version_id": "v1.0",
                        "stage": 3,
                        "label": "初始初稿",
                        "content": initial_draft,
                        "change_summary": "初始版本"
                    }
                ]
            }
        }
    }
    patch_resp = client.post("/api/canvas/patch-state", json=init_patch)
    assert patch_resp.status_code == 200

    # 2. Call /api/canvas/refract-selection
    refract_resp = client.post(
        "/api/canvas/refract-selection",
        json={
            "session_id": session_id,
            "selected_text": "I realized that textbook consensus models rarely anticipate real-world failure.",
            "instruction": "结合我刚补充的腾讯实习指标强化这一句",
            "full_text": initial_draft,
        }
    )
    assert refract_resp.status_code == 200
    refract_data = refract_resp.json()
    assert refract_data["status"] == "success"
    assert "rewritten_text" in refract_data
    assert "<ins" in refract_data["diff_html"]

    rewritten_text = refract_data["rewritten_text"]

    # 3. Call /api/canvas/accept-refraction
    accept_resp = client.post(
        "/api/canvas/accept-refraction",
        json={
            "session_id": session_id,
            "original_text": "I realized that textbook consensus models rarely anticipate real-world failure.",
            "rewritten_text": rewritten_text,
            "full_text": initial_draft,
            "change_summary": "强化腾讯实习指标"
        }
    )
    assert accept_resp.status_code == 200
    accept_data = accept_resp.json()
    assert accept_data["status"] == "success"
    assert rewritten_text in accept_data["sop_draft"]
    assert len(accept_data["sop_versions"]) == 2

    # 4. Call /api/canvas/rollback-version to v1.0
    rollback_resp = client.post(
        "/api/canvas/rollback-version",
        json={
            "session_id": session_id,
            "version_id": "v1.0"
        }
    )
    assert rollback_resp.status_code == 200
    rb_data = rollback_resp.json()
    assert rb_data["status"] == "success"
    assert rb_data["sop_draft"] == initial_draft
    # Version record appended for the rollback action
    assert len(rb_data["sop_versions"]) == 3
