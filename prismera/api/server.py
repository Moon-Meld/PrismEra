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
from fastapi.responses import StreamingResponse, JSONResponse, Response
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


# Include administrative router
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])


# Mount static files for the Web workbench if web directory exists
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if os.path.exists(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web_workbench")
