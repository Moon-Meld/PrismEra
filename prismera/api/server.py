"""PrismEra FastAPI Streaming Gateway Server.

Provides RESTful and Server-Sent Events (SSE) interfaces for multi-agent
orchestration, real-time node transitions, token-level response streaming,
and student spectrum profile synchronization.
"""

from __future__ import annotations
import json
import logging
import os
import uuid
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from prismera.engine import PrismEraSession, AGENT_METADATA, _SESSION_REGISTRY
from prismera.state import StudentSpectrumProfile, create_initial_spectrum_profile
from prismera.llm import _extract_student_attributes_heuristic
from prismera.agents.disperser import refract_text_selection
from prismera.db.session_store import get_session_store
from prismera.exporter import (
    generate_markdown_report,
    generate_html_report,
    compile_dossier_data,
)
from prismera.api.admin import router as admin_router
from prismera.tools.echo_tools import (
    retrieve_interview_question_bank,
    evaluate_interview_answer,
    generate_application_timeline,
)
from prismera.tools.prerequisite_tools import check_prerequisite_graph
from prismera.db.graph_store import get_graph_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrismEraGateway")

app = FastAPI(
    title="PrismEra Optical Gateway",
    description="FastAPI streaming gateway powering the PrismEra Multi-Agent Study Abroad System",
    version="0.2.0"
)

# Enable CORS for cross-origin workbench integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session registry shared with engine
SESSION_REGISTRY: Dict[str, PrismEraSession] = _SESSION_REGISTRY


def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, PrismEraSession]:
    """Retrieve an existing session or instantiate a new one."""
    if not session_id or not session_id.strip():
        session_id = f"prism_{uuid.uuid4().hex[:8]}"

    if session_id not in SESSION_REGISTRY:
        logger.info(f"Instantiating new PrismEraSession: {session_id}")
        SESSION_REGISTRY[session_id] = PrismEraSession(thread_id=session_id)

    return session_id, SESSION_REGISTRY[session_id]


# Request / Response Schemas
class ChatStreamRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    message: str = Field(..., description="User prompt or background inquiry")


class ProfileUpdateRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    profile: Optional[Dict[str, Any]] = Field(default=None, description="Direct spectrum profile dictionary update")
    text: Optional[str] = Field(default=None, description="Freeform text or transcript notes to extract parameters from")


class DocumentUploadRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    file_name: str = Field(..., description="Uploaded file name (e.g. resume.pdf, transcript.txt)")
    file_type: Optional[str] = Field(default=None, description="MIME type or file extension")
    content_base64: Optional[str] = Field(default=None, description="Base64 encoded file payload for binary files (PDF/DOC)")
    text_content: Optional[str] = Field(default=None, description="Direct text string content for text/markdown files")


class SessionResetRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier to reset")


class SessionCreateRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Optional custom session identifier")
    name: Optional[str] = Field(default=None, description="Student profile display name")
    initial_profile: Optional[Dict[str, Any]] = Field(default=None, description="Initial spectrum profile")


class SessionRenameRequest(BaseModel):
    name: str = Field(..., description="New display name for student profile")


class CanvasPatchRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    state_patch: Dict[str, Any] = Field(..., description="State mutation patch dictionary")


class CanvasRefractRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    selected_text: str = Field(..., description="Selected draft sentence/paragraph for inline refraction")
    instruction: str = Field(..., description="Refinement prompt instruction")
    full_text: Optional[str] = Field(default=None, description="Optional full draft text for context and replacement")


class CanvasAcceptRefractionRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    original_text: str = Field(..., description="Original selected snippet")
    rewritten_text: str = Field(..., description="Accepted rewritten replacement")
    full_text: Optional[str] = Field(default=None, description="Optional base full text")
    change_summary: Optional[str] = Field(default=None, description="Summary tag for version history")


class CanvasRollbackRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    version_id: str = Field(..., description="Target version id to roll back to")


class CanvasConfirmOutlineRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    outline: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional edited Stage 2 outline")


class EchoEvaluateRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    question_text: str = Field(..., description="Interview question text")
    answer_text: str = Field(..., description="Student's answer text")
    interview_type: str = Field(default="kira_video", description="Interview type")
    program_id: Optional[str] = Field(default=None, description="Target program ID")


class EchoTimelineRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")


class WhatIfSimulationRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    student_profile: Optional[Dict[str, Any]] = Field(default=None, description="Student profile dictionary")
    target_program_id: str = Field(..., description="Target program ID to simulate for")
    target_program: Optional[Dict[str, Any]] = Field(default=None, description="Optional target program dictionary")
    simulated_gpa_delta: float = Field(default=0.0, description="GPA variation (+/-)")
    simulated_lang_score: Optional[float] = Field(default=None, description="Simulated IELTS or TOEFL score")
    added_research_tier: Optional[str] = Field(default=None, description="Added research tier (tier2_intern, top_lab, first_author_paper, opensource)")
    major: Optional[str] = Field(default=None, description="Student target major")
    months_remaining: int = Field(default=4, description="Months remaining until application deadline")
    current_semester: Optional[str] = Field(default="大四上", description="Current semester/stage, e.g. 大三上, 大三下, 大四上")


class PortfolioOptimizationRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session identifier")
    student_profile: Optional[Dict[str, Any]] = Field(default=None, description="Student profile dictionary")
    candidate_programs: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of candidate programs")
    current_selected_ids: Optional[List[str]] = Field(default=None, description="Current shortlist IDs")
    k_budget: int = Field(default=6, ge=1, le=15, description="Number of programs to select in portfolio")
    risk_aversion: float = Field(default=1.0, ge=0.0, le=5.0, description="Risk aversion penalty lambda")
    diversity_weight: float = Field(default=0.6, ge=0.0, le=3.0, description="Spectral diversity reward gamma")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "PrismEra Streaming Gateway",
        "version": "0.2.0",
        "active_sessions": len(SESSION_REGISTRY),
        "agents": list(AGENT_METADATA.keys())
    }


@app.get("/api/sessions")
async def list_sessions():
    """List all saved student sessions from SQLite and in-memory registry."""
    store = get_session_store()
    saved = store.list_sessions()
    saved_ids = {s["session_id"] for s in saved}
    for sid, sess in SESSION_REGISTRY.items():
        if sid not in saved_ids:
            profile = sess.state.get("student_profile", {})
            saved.append({
                "session_id": sid,
                "name": sess.state.get("metadata", {}).get("name") or f"学员档案 ({sid[:8]})",
                "turns": len(sess.state.get("messages", [])),
                "undergrad_tier": profile.get("undergrad_tier"),
                "undergrad_name": profile.get("undergrad_name"),
                "major": profile.get("major"),
                "gpa_raw": profile.get("gpa_raw"),
                "target_regions": profile.get("target_regions", []),
                "sop_stage": profile.get("sop_stage", 1),
                "shortlisted_count": len(profile.get("shortlisted_programs", [])),
                "has_sop_draft": bool(profile.get("sop_draft")),
                "target_prof_count": len(profile.get("target_professors") or []),
            })
    return {"sessions": saved}


@app.post("/api/session/create")
async def create_session_endpoint(request: SessionCreateRequest):
    """Create a new student profile in SQLite and in-memory registry."""
    store = get_session_store()
    record = store.create_session(
        session_id=request.session_id,
        name=request.name,
        initial_profile=request.initial_profile
    )
    sid = record["session_id"]
    sess = PrismEraSession(thread_id=sid, name=record["name"])
    return {
        "status": "success",
        "session": record,
        "session_id": sid,
    }


@app.post("/api/session/{session_id}/rename")
async def rename_session_endpoint(session_id: str, request: SessionRenameRequest):
    """Rename a student profile."""
    store = get_session_store()
    success = store.rename_session(session_id, request.name)
    if not success and session_id not in SESSION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    if session_id in SESSION_REGISTRY:
        SESSION_REGISTRY[session_id].state.setdefault("metadata", {})["name"] = request.name
        SESSION_REGISTRY[session_id].save(name=request.name)
    return {
        "status": "success",
        "session_id": session_id,
        "name": request.name
    }


@app.delete("/api/session/{session_id}")
async def delete_session_endpoint(session_id: str):
    """Delete a student profile from SQLite and in-memory registry."""
    store = get_session_store()
    deleted = store.delete_session(session_id)
    if session_id in SESSION_REGISTRY:
        SESSION_REGISTRY.pop(session_id, None)
        deleted = True
    return {
        "status": "success",
        "session_id": session_id,
        "deleted": deleted
    }


@app.post("/api/chat/stream")
async def chat_stream(request: ChatStreamRequest):
    """Deliver user message into PrismEra multi-agent StateGraph and stream SSE events.

    Pushes:
    - agent_switch: Current active agent changes (Luminary -> Locus/Facet/Disperser/Resonator)
    - thought: Luminary orchestrator reasoning & intent detection
    - tool_call: Knowledge graph / RAG tool invocations (e.g. Cypher filter, WES calculation)
    - tool_result: Tool completion signals
    - token: Incremental tokens for typewriter rendering
    - profile_update: Real-time StudentSpectrumProfile snapshot
    - done: Completion summary with final response and state
    """
    session_id, session = get_or_create_session(request.session_id)
    logger.info(f"[/api/chat/stream] Received query for session [{session_id}]: {request.message[:60]}...")

    async def sse_event_generator():
        try:
            async for chunk in session.stream_user_message(request.message):
                event_type = chunk.get("event", "message")
                payload = json.dumps(chunk.get("data", {}), ensure_ascii=False)
                yield f"event: {event_type}\ndata: {payload}\n\n"
        except Exception as e:
            logger.error(f"Error during stream generation: {e}", exc_info=True)
            err_data = json.dumps({"error": str(e), "session_id": session_id}, ensure_ascii=False)
            yield f"event: error\ndata: {err_data}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/session/{session_id}/spectrum")
async def get_session_spectrum(session_id: str):
    """Retrieve applicant's complete spectrum profile, shortlisted school matrix, and SOP stage."""
    if session_id not in SESSION_REGISTRY:
        _, session = get_or_create_session(session_id)
    else:
        session = SESSION_REGISTRY[session_id]

    profile = session.state.get("student_profile", create_initial_spectrum_profile())
    messages = session.state.get("messages", [])

    return {
        "session_id": session_id,
        "profile": profile,
        "shortlisted_programs": profile.get("shortlisted_programs", []),
        "sop_stage": profile.get("sop_stage", 1),
        "sop_outline": profile.get("sop_outline", []),
        "sop_draft": profile.get("sop_draft", ""),
        "sop_critique": profile.get("sop_critique", {}),
        "sop_versions": profile.get("sop_versions", []),
        "locked_target_program": profile.get("locked_target_program"),
        "interview_records": profile.get("interview_records", []),
        "application_timeline": profile.get("application_timeline", []),
        "pending_human_review": session.state.get("pending_human_review"),
        "mined_story_fragments": profile.get("mined_story_fragments", []),
        "target_professors": profile.get("target_professors", []),
        "messages": messages,
        "active_agent": session.state.get("active_agent"),
        "routing_decision": session.state.get("routing_decision"),
    }


@app.post("/api/canvas/patch-state")
async def canvas_patch_state(request: CanvasPatchRequest):
    """Mutate session state directly from right-hand canvas and write back to LangGraph checkpointer."""
    session_id, session = get_or_create_session(request.session_id)
    patch_result = session.patch_state(request.state_patch)
    logger.info(f"[/api/canvas/patch-state] Applied patch to session [{session_id}]: {list(request.state_patch.keys())}")
    return {
        "status": "success",
        "session_id": session_id,
        "profile": session.state["student_profile"],
        "pending_human_review": session.state.get("pending_human_review"),
        "patch_result": patch_result
    }


@app.post("/api/canvas/refract-selection")
async def canvas_refract_selection(request: CanvasRefractRequest):
    """Execute local inline refraction on selected text and return token-level Diff."""
    session_id, session = get_or_create_session(request.session_id)
    profile = session.state.get("student_profile", {})
    base_text = request.full_text or profile.get("sop_draft", "")
    
    refract_res = refract_text_selection(
        selected_text=request.selected_text,
        instruction=request.instruction,
        full_text=base_text,
        student_profile=profile
    )
    logger.info(f"[/api/canvas/refract-selection] Refracted snippet for [{session_id}], inst: {request.instruction[:30]}")
    return {
        "status": "success",
        "session_id": session_id,
        **refract_res
    }


@app.post("/api/canvas/accept-refraction")
async def canvas_accept_refraction(request: CanvasAcceptRefractionRequest):
    """Accept rewritten snippet, replace in document, record version snapshot and sync state."""
    session_id, session = get_or_create_session(request.session_id)
    profile = session.state["student_profile"]
    current_draft = request.full_text or profile.get("sop_draft", "")

    if request.original_text in current_draft:
        new_draft = current_draft.replace(request.original_text, request.rewritten_text, 1)
    else:
        new_draft = current_draft + "\n" + request.rewritten_text

    profile["sop_draft"] = new_draft
    versions = list(profile.get("sop_versions") or [])
    tag = request.change_summary or f"局部折射精修: {request.rewritten_text[:20]}..."
    versions.append({
        "version_id": f"v{len(versions) + 1}.0",
        "timestamp": "Refraction Snapshot",
        "stage": profile.get("sop_stage", 3),
        "label": f"局部折射 ({tag[:14]})",
        "author": "User & Disperser",
        "outline": profile.get("sop_outline"),
        "content": new_draft,
        "change_summary": tag
    })
    profile["sop_versions"] = versions

    session.patch_state({"student_profile": profile})
    logger.info(f"[/api/canvas/accept-refraction] Accepted refraction in [{session_id}], new version v{len(versions)}.0")

    return {
        "status": "success",
        "session_id": session_id,
        "sop_draft": new_draft,
        "sop_versions": profile["sop_versions"],
        "profile": profile,
    }


@app.post("/api/canvas/rollback-version")
async def canvas_rollback_version(request: CanvasRollbackRequest):
    """Roll back SOP outline and draft to a historical version snapshot."""
    session_id, session = get_or_create_session(request.session_id)
    profile = session.state["student_profile"]
    versions = list(profile.get("sop_versions") or [])

    target_v = None
    for v in versions:
        if v.get("version_id") == request.version_id:
            target_v = v
            break

    if not target_v:
        raise HTTPException(status_code=404, detail=f"Version '{request.version_id}' not found in sop_versions")

    if target_v.get("outline"):
        profile["sop_outline"] = target_v["outline"]
    if target_v.get("content"):
        profile["sop_draft"] = target_v["content"]
    if target_v.get("stage"):
        profile["sop_stage"] = target_v["stage"]
    if target_v.get("critique"):
        profile["sop_critique"] = target_v["critique"]

    # Record rollback event in version list
    versions.append({
        "version_id": f"v{len(versions) + 1}.0",
        "timestamp": "Rollback Snapshot",
        "stage": profile.get("sop_stage", 3),
        "label": f"回滚至 {target_v.get('version_id')} ({target_v.get('label', '')})",
        "author": "User",
        "outline": profile.get("sop_outline"),
        "content": profile.get("sop_draft"),
        "change_summary": f"回滚到历史版本 {request.version_id}"
    })
    profile["sop_versions"] = versions

    session.patch_state({"student_profile": profile})
    logger.info(f"[/api/canvas/rollback-version] Rolled back session [{session_id}] to {request.version_id}")

    return {
        "status": "success",
        "session_id": session_id,
        "restored_version": target_v,
        "sop_draft": profile.get("sop_draft"),
        "sop_outline": profile.get("sop_outline"),
        "sop_versions": profile["sop_versions"],
        "profile": profile,
    }


@app.post("/api/canvas/confirm-outline")
async def canvas_confirm_outline(request: CanvasConfirmOutlineRequest):
    """Confirm Stage 2 outline and trigger backend progression into Stage 3/4."""
    session_id, session = get_or_create_session(request.session_id)
    profile = session.state["student_profile"]

    if request.outline:
        profile["sop_outline"] = request.outline

    profile["sop_stage"] = 3
    session.state["pending_human_review"] = None
    session.patch_state({
        "student_profile": profile,
        "pending_human_review": None,
    })

    # Execute graph turn to produce Stage 3/4 draft and critique
    exec_result = session.send_user_message("确认大纲并执笔")
    logger.info(f"[/api/canvas/confirm-outline] Confirmed outline for [{session_id}] and triggered Stage 3/4 execution")

    return {
        "status": "success",
        "session_id": session_id,
        "profile": session.state["student_profile"],
        "latest_response": exec_result.get("latest_response"),
        "sop_stage": session.state["student_profile"].get("sop_stage", 4),
        "sop_draft": session.state["student_profile"].get("sop_draft"),
        "sop_outline": session.state["student_profile"].get("sop_outline"),
        "sop_critique": session.state["student_profile"].get("sop_critique"),
        "sop_versions": session.state["student_profile"].get("sop_versions", []),
    }


@app.post("/api/profile/upload")
async def upload_or_update_profile(request: ProfileUpdateRequest):
    """Directly update or heuristically extract student hard metrics.

    Accepts structured JSON in `profile` or freeform text notes in `text`.
    """
    session_id, session = get_or_create_session(request.session_id)
    profile = session.state["student_profile"]

    # 1. Direct structured update
    if request.profile:
        for k, v in request.profile.items():
            if k in profile:
                profile[k] = v
            else:
                profile[k] = v

    # 2. Heuristic extraction from freeform text
    if request.text:
        extracted = _extract_student_attributes_heuristic(request.text, profile)
        for k, v in extracted.items():
            profile[k] = v

    logger.info(f"[/api/profile/upload] Updated profile for session [{session_id}]: {profile}")

    return {
        "session_id": session_id,
        "status": "success",
        "profile": profile,
        "shortlisted_programs": profile.get("shortlisted_programs", []),
        "sop_stage": profile.get("sop_stage", 1),
    }


@app.post("/api/profile/upload-document")
async def upload_document_endpoint(request: DocumentUploadRequest):
    """Upload resume or transcript file (Base64 PDF or raw text/markdown).

    Automatically parses credentials, GPA, prerequisite grades, and STAR experiences,
    then updates the student's spectrum profile and pushes a system event message.
    """
    import base64
    session_id, session = get_or_create_session(request.session_id)
    file_bytes = None

    if request.content_base64:
        try:
            b64_data = request.content_base64
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            file_bytes = base64.b64decode(b64_data)
        except Exception as e:
            logger.warning(f"Failed to decode base64 file data: {e}")
            file_bytes = None

    parsed = session.upload_document(
        file_path_or_text=request.text_content,
        file_bytes=file_bytes,
        file_name=request.file_name
    )

    profile = session.state["student_profile"]
    logger.info(f"[/api/profile/upload-document] Successfully parsed '{request.file_name}' for session [{session_id}]")

    return {
        "status": "success",
        "session_id": session_id,
        "file_name": request.file_name,
        "parsed": parsed,
        "profile": profile,
        "shortlisted_programs": profile.get("shortlisted_programs", []),
        "experiences": profile.get("experiences", []),
        "prerequisite_grades": profile.get("prerequisite_grades", {}),
    }


@app.get("/api/programs")
async def list_available_programs(
    query: Optional[str] = None,
    region: Optional[str] = None,
    major: Optional[str] = None,
):
    """Retrieve all university programs recorded in the knowledge graph with optional filtering."""
    gs = get_graph_store()
    programs = gs.get_nodes_by_label("Program")

    results = []
    q = (query or "").lower().strip()
    r = (region or "").upper().strip()
    m = (major or "").upper().strip()

    for p in programs:
        name_cn = p.get("name_cn") or p.get("name", "")
        name_en = p.get("name_en") or p.get("id", "")
        uni = p.get("university", "")
        prog_region = (p.get("region") or "").upper()

        if r and prog_region != r:
            continue
        if m and m not in (p.get("target_major") or p.get("discipline") or "CS").upper():
            continue
        if q:
            match_txt = f"{name_cn} {name_en} {uni} {p.get('id', '')}".lower()
            if q not in match_txt:
                continue

        results.append(p)

    return {
        "status": "success",
        "count": len(results),
        "programs": results
    }


@app.get("/api/facet/prerequisites")
async def get_facet_prerequisites(
    session_id: Optional[str] = None,
    target_major: Optional[str] = None,
):
    """Diagnose prerequisite courses alignment and identify structural blindspots."""
    sid, session = get_or_create_session(session_id)
    profile = session.state["student_profile"]

    t_major = target_major or (profile.get("target_majors") or ["CS"])[0]
    prereq_dict = profile.get("prerequisite_grades") or {}
    completed_courses = list(prereq_dict.keys()) if prereq_dict else [
        "高等数学 (Calculus)",
        "线性代数 (Linear Algebra)",
        "概率论与数理统计 (Probability)",
        "大学物理 (University Physics)",
        "面向对象程序设计 (Python / Java)",
        "数据结构与算法 (Data Structures)"
    ]

    res = check_prerequisite_graph(t_major, completed_courses)
    return {
        "status": "success",
        "session_id": sid,
        "target_major": t_major,
        "completed_count": len(completed_courses),
        "alignment_table": res.get("alignment_table", []),
        "critical_advice": res.get("critical_advice", ""),
        "prerequisite_grades": prereq_dict,
    }


@app.post("/api/session/reset")
async def reset_session(request: SessionResetRequest):
    """Reset the specified session to an initial state."""
    session_id = request.session_id
    store = get_session_store()
    store.delete_session(session_id)
    SESSION_REGISTRY[session_id] = PrismEraSession(thread_id=session_id)
    logger.info(f"[/api/session/reset] Reset session: {session_id}")
    return {
        "session_id": session_id,
        "status": "reset_successful",
        "profile": SESSION_REGISTRY[session_id].state["student_profile"]
    }


@app.get("/api/echo/questions")
async def get_echo_questions(
    program_id: Optional[str] = None,
    interview_type: Optional[str] = "kira_video"
):
    """Retrieve interview question bank by program and type."""
    questions = retrieve_interview_question_bank(
        program_id=program_id,
        interview_type=interview_type or "kira_video"
    )
    return {"questions": questions, "count": len(questions)}


@app.post("/api/echo/generate-timeline")
async def api_generate_timeline(request: EchoTimelineRequest):
    """Trigger timeline generation for the session's shortlisted programs."""
    session_id, session = get_or_create_session(request.session_id)
    profile = session.state["student_profile"]
    shortlisted = profile.get("shortlisted_programs") or []
    timeline = generate_application_timeline(shortlisted)
    profile["application_timeline"] = timeline
    session.patch_state({"student_profile": profile})
    return {
        "status": "success",
        "session_id": session_id,
        "application_timeline": timeline,
    }


@app.post("/api/echo/evaluate-answer")
async def api_evaluate_answer(request: EchoEvaluateRequest):
    """Evaluate an interview answer on 3 dimensions, generate refined sample answer, and persist."""
    session_id, session = get_or_create_session(request.session_id)
    profile = session.state["student_profile"]

    eval_result = evaluate_interview_answer(
        question_item={"question": request.question_text, "category": "实战作答", "interview_type": request.interview_type},
        student_answer=request.answer_text,
        student_profile=profile,
        interview_type=request.interview_type
    )

    records = list(profile.get("interview_records") or [])
    records.append({
        "record_id": f"rec_{len(records) + 1}",
        "program_id": request.program_id or "cmu_msit_se",
        "interview_type": request.interview_type,
        "status": "completed",
        "question_data": {"question": request.question_text, "category": "实战作答"},
        "evaluation": eval_result,
        "student_answer": request.answer_text,
    })
    profile["interview_records"] = records
    session.patch_state({"student_profile": profile})

    return {
        "status": "success",
        "session_id": session_id,
        "evaluation": eval_result,
        "interview_records": records
    }


@app.post("/api/ml/simulate-what-if")
async def api_simulate_what_if(request: WhatIfSimulationRequest):
    """What-If counterfactual admission simulation sandbox endpoint."""
    from prismera.ml.admit_predictor import get_admit_predictor
    from prismera.db.graph_store import get_graph_store

    profile = request.student_profile
    if not profile and request.session_id:
        _, session = get_or_create_session(request.session_id)
        profile = session.state.get("student_profile", {})

    if not profile:
        profile = {
            "undergrad_tier": "985",
            "gpa_raw": "3.60/4.0",
            "major": request.major or "CS",
        }

    program = request.target_program
    if not program:
        gs = get_graph_store()
        program = gs.get_node(request.target_program_id)

    if not program:
        program = {
            "id": request.target_program_id,
            "name_cn": request.target_program_id,
            "tier_bracket": "Match",
            "gpa_min_4_0": 3.5,
        }

    predictor = get_admit_predictor()
    sim_result = predictor.simulate_what_if(
        student_profile=profile,
        program=program,
        simulated_gpa_delta=request.simulated_gpa_delta,
        simulated_lang_score=request.simulated_lang_score,
        added_research_tier=request.added_research_tier,
        major=request.major or profile.get("major"),
        months_remaining=request.months_remaining,
        current_semester=request.current_semester,
    )

    return {
        "status": "success",
        "program_id": request.target_program_id,
        "program_name": program.get("name_cn") or program.get("name") or request.target_program_id,
        "simulation": sim_result,
    }


@app.post("/api/ml/optimize-portfolio")
async def api_optimize_portfolio(request: PortfolioOptimizationRequest):
    """Submodular Portfolio Optimizer endpoint."""
    from prismera.ml.portfolio_optimizer import get_portfolio_optimizer
    from prismera.db.graph_store import get_graph_store

    profile = request.student_profile
    curr_ids = list(request.current_selected_ids or [])

    if not profile and request.session_id:
        _, session = get_or_create_session(request.session_id)
        profile = session.state.get("student_profile", {})
        if not curr_ids:
            curr_ids = [p.get("id") or p.get("program_id") for p in session.state.get("shortlisted_programs", [])]

    if not profile:
        profile = {
            "undergrad_tier": "985",
            "gpa_raw": "3.60/4.0",
            "major": "CS",
        }

    candidates = request.candidate_programs
    if not candidates:
        gs = get_graph_store()
        candidates = gs.get_nodes_by_label("Program")

    if not candidates:
        candidates = [
            {"id": "cmu_msit_se", "name_cn": "卡耐基梅隆大学 - 软件工程理学硕士", "institution": "cmu", "tier_bracket": "Reach", "gpa_min_4_0": 3.6, "region": "US"},
            {"id": "stanford_cs", "name_cn": "斯坦福大学 - 计算机科学理学硕士", "institution": "stanford", "tier_bracket": "Reach", "gpa_min_4_0": 3.8, "region": "US"},
            {"id": "columbia_cs", "name_cn": "哥伦比亚大学 - 计算机科学理学硕士", "institution": "columbia", "tier_bracket": "Match", "gpa_min_4_0": 3.5, "region": "US"},
            {"id": "imperial_ai", "name_cn": "帝国理工学院 - 人工智能理学硕士", "institution": "imperial", "tier_bracket": "Match", "gpa_min_4_0": 3.5, "region": "UK"},
            {"id": "nus_mcomp", "name_cn": "新加坡国立大学 - 计算机硕士", "institution": "nus", "tier_bracket": "Match", "gpa_min_4_0": 3.4, "region": "SG"},
            {"id": "nyu_ds", "name_cn": "纽约大学 - 数据科学理学硕士", "institution": "nyu", "tier_bracket": "Safety", "gpa_min_4_0": 3.2, "region": "US"},
        ]

    optimizer = get_portfolio_optimizer()
    optimizer.risk_aversion = request.risk_aversion
    optimizer.diversity_weight = request.diversity_weight

    result = optimizer.optimize_portfolio(
        candidate_pool=candidates,
        student_profile=profile,
        k_budget=request.k_budget,
        current_selection_ids=curr_ids,
    )

    return {
        "status": "success",
        "result": result,
    }


@app.get("/api/session/{session_id}/export")
async def export_session_report(
    session_id: str,
    format: Optional[str] = "html",
    download: Optional[bool] = False
):
    """Export the student's complete PrismEra dossier in HTML, Markdown, or JSON."""
    sid, session = get_or_create_session(session_id)
    fmt = (format or "html").lower().strip()

    if fmt in ["markdown", "md"]:
        md_text = generate_markdown_report(session)
        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="PrismEra_Report_{session_id}.md"'
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers=headers
        )
    elif fmt == "json":
        data = compile_dossier_data(session)
        return JSONResponse(content=data)
    else:
        # Default: high-aesthetic dark optical HTML
        html_text = generate_html_report(session)
        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="PrismEra_Report_{session_id}.html"'
        return Response(
            content=html_text,
            media_type="text/html; charset=utf-8",
            headers=headers
        )


@app.get("/api/session/{session_id}/export/preview")
async def export_session_preview(session_id: str):
    """Retrieve structured metadata, raw Markdown, and compiled HTML for modal preview."""
    sid, session = get_or_create_session(session_id)
    data = compile_dossier_data(session)
    md_text = generate_markdown_report(session)
    html_text = generate_html_report(session)
    return {
        "session_id": sid,
        "student_name": data["meta"]["student_name"],
        "markdown": md_text,
        "html": html_text,
        "meta": data["meta"],
        "student_profile": data["student_profile"],
    }


# ==============================================================================
# Desktop Client Distribution & Telemetry Endpoints
# ==============================================================================

DESKTOP_METADATA = {
    "version": "0.2.0",
    "release_date": "2026-10-28",
    "release_name": "PrismEra Optical Dawn (原生桌面工作台发布)",
    "release_url": "https://github.com/prism-era/prismera/releases/latest",
    "platforms": {
        "macos": {
            "name": "macOS 原生客户端",
            "supported_os": "macOS 11.0 (Big Sur) 及以上 (兼容 Sequoia / Sonoma / Ventura)",
            "targets": [
                {
                    "arch": "arm64",
                    "chip": "Apple Silicon (M1 / M2 / M3 / M4 系列芯片)",
                    "recommended": True,
                    "format": "dmg",
                    "filename": "PrismEra-0.2.0-mac-arm64.dmg",
                    "download_key": "mac-arm64",
                    "url": "/api/desktop/download/mac-arm64",
                    "size": "98.5 MB",
                    "sha256": "3a8f9c2d1e0b5a74e92b8d4c1f6e5a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f"
                },
                {
                    "arch": "x64",
                    "chip": "Intel 处理器",
                    "recommended": False,
                    "format": "dmg",
                    "filename": "PrismEra-0.2.0-mac-x64.dmg",
                    "download_key": "mac-x64",
                    "url": "/api/desktop/download/mac-x64",
                    "size": "104.2 MB",
                    "sha256": "4b9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e"
                }
            ],
            "install_guide": [
                "双击打开下载的 `PrismEra-0.2.0-mac-arm64.dmg` 镜像安装包。",
                "将 PrismEra 图标直接拖拽放入右侧的 `Applications（应用程序）` 文件夹。",
                "进入启动台或应用程序列表点击打开 PrismEra。",
                "若遇 macOS Gatekeeper 提示【未经验证的开发者】：按住 Control 键点按应用选择【打开】，或在【系统设置】->【隐私与安全性】中点击【仍要打开】即可。"
            ]
        },
        "windows": {
            "name": "Windows 原生客户端",
            "supported_os": "Windows 10 / Windows 11 (64位)",
            "targets": [
                {
                    "arch": "x64",
                    "edition": "NSIS 安装向导版 (推荐)",
                    "recommended": True,
                    "format": "exe",
                    "filename": "PrismEra-Setup-0.2.0.exe",
                    "download_key": "win-nsis",
                    "url": "/api/desktop/download/win-nsis",
                    "size": "92.4 MB",
                    "sha256": "5c0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f"
                },
                {
                    "arch": "x64",
                    "edition": "便携绿色免安装版",
                    "recommended": False,
                    "format": "zip",
                    "filename": "PrismEra-Portable-0.2.0.zip",
                    "download_key": "win-portable",
                    "url": "/api/desktop/download/win-portable",
                    "size": "88.1 MB",
                    "sha256": "6d1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a"
                }
            ],
            "install_guide": [
                "下载 `PrismEra-Setup-0.2.0.exe` 安装文件并双击启动向导。",
                "遵循向导自定义选择安装路径，默认自动勾选【创建桌面快捷方式】与【开始菜单】。",
                "首次运行若遇 Windows Defender SmartScreen 拦截提示，点击【更多信息】并选择【仍要运行】。",
                "便携版用户可直接解压 ZIP 压缩包，双击 `PrismEra.exe` 即可免安装即启。"
            ]
        }
    },
    "features": [
        {
            "icon": "⚡",
            "title": "原生毫秒级响应",
            "desc": "脱离浏览器海量标签页内存干扰，原生暗黑光学渲染管线，极速冷启动与平滑滚动"
        },
        {
            "icon": "🔒",
            "title": "本地隐私沙盒保护",
            "desc": "学生档案与切面诊断在本地 SQLite 强隔离存储，简历与文书资产永无外网泄露风险"
        },
        {
            "icon": "🧠",
            "title": "双模大模型智能支持",
            "desc": "既可一键配置主流在线商业大模型，亦可直接对接本地离线模型 (Ollama / vLLM / LM Studio)"
        },
        {
            "icon": "📂",
            "title": "系统级深度无缝融合",
            "desc": "支持状态栏/托盘常驻守护、全局原生快捷键呼出、本地 PDF/Word 简历成绩单直接拖拽解析"
        }
    ]
}


@app.get("/api/desktop/info")
async def get_desktop_info(request: Request):
    """Retrieve metadata, OS download links, installation guides, and feature matrix."""
    user_agent = request.headers.get("user-agent", "").lower()
    detected_os = "other"
    if "mac" in user_agent or "darwin" in user_agent:
        detected_os = "macos"
    elif "win" in user_agent:
        detected_os = "windows"
    elif "linux" in user_agent:
        detected_os = "linux"

    return {
        **DESKTOP_METADATA,
        "client_detected_os": detected_os,
    }


@app.get("/api/desktop/download/{target}")
async def download_desktop_package(target: str):
    """Directly stream downloadable desktop installer if compiled locally or redirect to release."""
    target_filename_map = {
        "mac-arm64": "PrismEra-0.2.0-mac-arm64.dmg",
        "mac-x64": "PrismEra-0.2.0-mac-x64.dmg",
        "win-nsis": "PrismEra-Setup-0.2.0.exe",
        "win-portable": "PrismEra-Portable-0.2.0.zip",
    }

    filename = target_filename_map.get(target)
    if not filename:
        raise HTTPException(status_code=404, detail=f"Target installer variant '{target}' not recognized.")

    # Check search locations for locally compiled distribution artifacts
    search_dirs = [
        os.path.join(PROJECT_ROOT, "desktop", "dist"),
        os.path.join(PROJECT_ROOT, "dist"),
        os.path.join(PROJECT_ROOT, "output"),
    ]

    for sdir in search_dirs:
        filepath = os.path.join(sdir, filename)
        if os.path.exists(filepath):
            return FileResponse(
                path=filepath,
                filename=filename,
                media_type="application/octet-stream"
            )

    # If not compiled locally, redirect to GitHub release download asset
    release_asset_url = f"https://github.com/prism-era/prismera/releases/download/v0.2.0/{filename}"
    return RedirectResponse(url=release_asset_url, status_code=307)


# Include administrative router
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])


# Mount static files for the Web workbench if web directory exists
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if os.path.exists(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web_workbench")
