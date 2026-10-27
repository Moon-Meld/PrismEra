"""PrismEra Administrative and Knowledge Graph Management API Router.

Provides endpoints for:
1. LLM & Inference Hot-Switching (Provider, Keys, Base URLs, Models, Latency Testing)
2. Online GraphStore & VectorStore Ingestion and Statistics
3. Benchmark Suite Online Inspection & Metric Dashboards
"""

from __future__ import annotations
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from prismera.config import get_current_config, update_llm_config, is_offline_mock
from prismera.db.graph_store import get_graph_store
from prismera.db.vector_store import get_vector_store, AdmissionCase
from benchmarks.run_eval import (
    run_benchmark,
    export_json_report,
    export_markdown_report,
    DEFAULT_JSON_REPORT_PATH,
    DEFAULT_MD_REPORT_PATH,
)

logger = logging.getLogger("PrismEraAdmin")

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class ConfigUpdateRequest(BaseModel):
    llm_provider: Optional[str] = Field(default=None, description="Provider: auto, mock, openai, deepseek, claude, ollama")
    api_key: Optional[str] = Field(default=None, description="API Key")
    base_url: Optional[str] = Field(default=None, description="API Base URL")
    model: Optional[str] = Field(default=None, description="Model identifier")
    temperature: Optional[float] = Field(default=None, description="Generation temperature (0.0 - 1.0)")
    offline_mock: Optional[bool] = Field(default=None, description="Explicitly force offline deterministic mock mode")


class ConfigTestRequest(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class AddGraphNodeRequest(BaseModel):
    node_type: str = Field(..., description="Node label, e.g. Program, University, Course, Professor")
    id: str = Field(..., description="Unique node ID (e.g. ucl_cs_msc, ucl)")
    name: str = Field(..., description="Display name / title")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Custom node properties")
    university_id: Optional[str] = Field(default=None, description="Affiliated university ID if adding a Program")


class AddAdmissionCaseRequest(BaseModel):
    id: Optional[str] = Field(default=None, description="Unique case ID, auto-generated if omitted")
    target_program_id: str = Field(..., description="Target program ID (e.g. cmu_msit_se, ic_computing_msc)")
    undergrad_name: str = Field(..., description="Applicant's undergraduate university")
    undergrad_tier: str = Field(..., description="Tier: 985, 211, 双非一本, 双非, 海本")
    gpa: float = Field(..., description="Applicant GPA or average mark (e.g. 3.8 or 88.5)")
    gpa_scale: str = Field(default="100", description="GPA scale: 100 or 4.0")
    major: str = Field(..., description="Undergraduate major")
    language: str = Field(..., description="Language test score description (e.g. 雅思 7.5 (口语 7.0))")
    background_summary: str = Field(..., description="Research, internship, or award summary")
    outcome: str = Field(default="ADMIT", description="Admission outcome: ADMIT / REJECT")
    outcome_type: str = Field(default="admit", description="Outcome classification: admit or reject")
    year: int = Field(default=2025, description="Admission cycle year")
    profile_text: Optional[str] = Field(default=None, description="Complete profile narrative")
    gre: Optional[str] = Field(default=None, description="GRE score if applicable")


# =============================================================================
# Tab A: LLM Hot-Switching & Testing
# =============================================================================

@router.get("/config")
async def get_system_config():
    """Retrieve current active LLM engine settings and provider details."""
    cfg = get_current_config()
    return {
        "status": "success",
        "config": cfg,
        "engine_mode": "Deterministic 离线引擎模式" if cfg["is_offline_mock"] else f"Live LLM 模式 ({cfg['llm_provider']})",
    }


@router.post("/config")
async def update_system_config(payload: ConfigUpdateRequest = Body(...)):
    """Hot-update LLM credentials, base URLs, model names, and engine modes."""
    updated = update_llm_config(
        provider=payload.llm_provider,
        api_key=payload.api_key,
        base_url=payload.base_url,
        model=payload.model,
        temperature=payload.temperature,
        offline_mock=payload.offline_mock,
    )
    logger.info(f"System LLM configuration hot-updated: provider={updated['llm_provider']}, mock={updated['is_offline_mock']}")
    return {
        "status": "success",
        "message": "系统配置已热更新并即时生效",
        "config": updated,
        "engine_mode": "Deterministic 离线引擎模式" if updated["is_offline_mock"] else f"Live LLM 模式 ({updated['llm_provider']})",
    }


@router.post("/config/test")
async def test_llm_connection(payload: Optional[ConfigTestRequest] = Body(default=None)):
    """Test LLM inference connectivity and measure round-trip latency."""
    cfg = get_current_config()
    target_provider = (payload.provider if payload and payload.provider else cfg["llm_provider"]).strip().lower()
    target_mock = target_provider == "mock" or (cfg["is_offline_mock"] and not (payload and payload.api_key))

    start_time = time.time()

    if target_mock:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "ok",
            "mode": "mock",
            "latency_ms": max(elapsed_ms, 0.5),
            "message": "离线 Deterministic 模拟引擎运行就绪（本地图谱与规则零网络依赖，100% 极速响应）",
            "provider": "mock",
            "model": "deterministic-mock-v1",
        }

    # Test Live LLM connection
    api_key = payload.api_key if payload and payload.api_key else ""
    if not api_key:
        # Check active provider in config
        if target_provider in ["openai", "auto"]:
            import prismera.config as pcfg
            api_key = pcfg.OPENAI_API_KEY
        elif target_provider == "deepseek":
            import prismera.config as pcfg
            api_key = pcfg.DEEPSEEK_API_KEY or pcfg.OPENAI_API_KEY
        elif target_provider in ["claude", "anthropic"]:
            import prismera.config as pcfg
            api_key = pcfg.ANTHROPIC_API_KEY

    base_url = (payload.base_url if payload and payload.base_url else cfg["openai_api_base"]).rstrip("/")
    model = payload.model if payload and payload.model else cfg["openai_model"]

    if not base_url:
        base_url = "https://api.openai.com/v1"

    if not api_key:
        return {
            "status": "error",
            "mode": "live",
            "latency_ms": 0,
            "message": "未配置 API Key，请在上方填入后重试测试，或切换至离线模式。",
            "provider": target_provider,
        }

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        test_payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=test_payload)
            elapsed_ms = round((time.time() - start_time) * 1000, 1)

            if resp.status_code == 200:
                data = resp.json()
                reply_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                return {
                    "status": "ok",
                    "mode": "live",
                    "latency_ms": elapsed_ms,
                    "message": f"连接成功！LLM API 响应正常 (HTTP {resp.status_code})",
                    "provider": target_provider,
                    "model": model,
                    "reply_sample": reply_text or "PONG",
                }
            else:
                return {
                    "status": "error",
                    "mode": "live",
                    "latency_ms": elapsed_ms,
                    "message": f"连接测试失败: HTTP {resp.status_code} - {resp.text[:200]}",
                    "provider": target_provider,
                    "model": model,
                }
    except Exception as exc:
        elapsed_ms = round((time.time() - start_time) * 1000, 1)
        return {
            "status": "error",
            "mode": "live",
            "latency_ms": elapsed_ms,
            "message": f"网络请求异常: {str(exc)}",
            "provider": target_provider,
            "model": model,
        }


# =============================================================================
# Tab B: Knowledge Graph & Case Ingestion + Real-time Statistics
# =============================================================================

def _compute_stats() -> Dict[str, Any]:
    gs = get_graph_store()
    vs = get_vector_store()

    unis = len(gs.get_nodes_by_label("University"))
    programs = len(gs.get_nodes_by_label("Program"))
    courses = len(gs.get_nodes_by_label("Course"))
    profs = len(gs.get_nodes_by_label("Professor"))
    tiers = len(gs.get_nodes_by_label("ChineseUniTier"))
    total_nodes = len(gs.graph.nodes)
    total_edges = len(gs.graph.edges)

    total_cases = len(vs.cases)
    total_nuances = len(vs.nuances)

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "universities_count": unis,
        "programs_count": programs,
        "courses_count": courses,
        "professors_count": profs,
        "chinese_tiers_count": tiers,
        "total_admission_cases": total_cases,
        "total_nuances": total_nuances,
        "graph_sqlite_path": str(gs.sqlite_path),
        "vector_sqlite_path": str(vs.sqlite_path),
    }


@router.get("/stats")
async def get_knowledge_base_stats():
    """Retrieve comprehensive statistical metrics across GraphStore and VectorStore."""
    stats = _compute_stats()
    return {
        "status": "success",
        "stats": stats,
    }


@router.post("/graph/node")
async def add_graph_node(payload: AddGraphNodeRequest = Body(...)):
    """Visually insert or augment a node in GraphStore with SQLite persistence."""
    node_id = payload.id.strip()
    node_name = payload.name.strip()
    node_type = payload.node_type.strip()

    if not node_id:
        raise HTTPException(status_code=400, detail="Node id cannot be empty.")
    if not node_name:
        raise HTTPException(status_code=400, detail="Node name cannot be empty.")

    gs = get_graph_store()

    props = payload.properties.copy()
    props["name"] = node_name

    # Add or update node
    gs.add_node(node_id, label=node_type, properties=props)

    # If program and university_id provided, create affiliation edge
    if node_type == "Program" and payload.university_id:
        uni_id = payload.university_id.strip()
        if gs.graph.has_node(uni_id):
            gs.add_edge(uni_id, node_id, "OFFERS_PROGRAM", properties={"program_name": node_name})
        else:
            # Auto-create university stub if missing
            gs.add_node(uni_id, label="University", properties={"name": uni_id.upper()})
            gs.add_edge(uni_id, node_id, "OFFERS_PROGRAM", properties={"program_name": node_name})

    try:
        gs.save_to_sqlite()
    except Exception as e:
        logger.error(f"Failed to persist graph to SQLite: {e}")
        raise HTTPException(status_code=500, detail=f"Database persistence error: {e}")

    stats = _compute_stats()
    return {
        "status": "success",
        "message": f"成功录入图谱节点 [{node_type}] {node_name} ({node_id})",
        "node_id": node_id,
        "node_type": node_type,
        "stats": stats,
    }


@router.post("/cases")
async def add_admission_case(payload: AddAdmissionCaseRequest = Body(...)):
    """Visually ingest a peer admission or rejection case into VectorStore with SQLite persistence."""
    case_id = payload.id.strip() if payload.id and payload.id.strip() else f"case_user_{uuid.uuid4().hex[:8]}"
    prog_id = payload.target_program_id.strip()
    school = payload.undergrad_name.strip()
    tier = payload.undergrad_tier.strip()
    major = payload.major.strip()

    if not prog_id or not school or not major:
        raise HTTPException(status_code=400, detail="target_program_id, undergrad_name, and major are required.")

    profile_text = payload.profile_text
    if not profile_text or not profile_text.strip():
        profile_text = (
            f"申请者本科毕业于{school} ({tier})，专业为{major}，"
            f"GPA 为 {payload.gpa}/{payload.gpa_scale}，标化语言成绩为 {payload.language}。"
            f"背景概况：{payload.background_summary}"
        )

    case = AdmissionCase(
        id=case_id,
        target_program_id=prog_id,
        undergrad_name=school,
        undergrad_tier=tier,
        gpa=float(payload.gpa),
        gpa_scale=str(payload.gpa_scale),
        major=major,
        language=payload.language.strip(),
        background_summary=payload.background_summary.strip(),
        outcome=payload.outcome.strip(),
        outcome_type=payload.outcome_type.strip().lower(),
        year=int(payload.year),
        profile_text=profile_text.strip(),
        gre=payload.gre.strip() if payload.gre else None,
    )

    vs = get_vector_store()
    vs.add_admission_case(case)

    try:
        vs.save_to_sqlite()
    except Exception as e:
        logger.error(f"Failed to persist vector store to SQLite: {e}")
        raise HTTPException(status_code=500, detail=f"Database persistence error: {e}")

    stats = _compute_stats()
    return {
        "status": "success",
        "message": f"同辈案例已成功向量化并存入向量库: [{case.outcome_type.upper()}] {school} -> {prog_id}",
        "case_id": case_id,
        "stats": stats,
    }


# =============================================================================
# Tab C: Benchmark Online Inspection & Dashboard
# =============================================================================

@router.get("/benchmark/latest")
async def get_latest_benchmark_report():
    """Retrieve the most recent GraphRAG benchmark execution results."""
    report_file = Path(DEFAULT_JSON_REPORT_PATH)
    if not report_file.exists():
        return {
            "status": "empty",
            "message": "尚未运行过评测基准，请点击上方按钮触发在线巡检。",
            "report": None,
        }

    try:
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "status": "success",
            "report": data,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read benchmark report: {exc}")


@router.post("/benchmark/run")
async def run_benchmark_online():
    """Trigger a full online evaluation across all 28 golden trap cases."""
    start_time = time.time()
    try:
        summary = run_benchmark(mode="both", verbose=False)
        export_json_report(summary, DEFAULT_JSON_REPORT_PATH)
        export_markdown_report(summary, DEFAULT_MD_REPORT_PATH)
        elapsed_sec = round(time.time() - start_time, 2)
        logger.info(f"Online benchmark inspection completed in {elapsed_sec}s.")
        return {
            "status": "success",
            "message": f"在线巡检执行完毕，28 个高危陷阱题评测全通（耗时 {elapsed_sec}s）",
            "report": summary,
        }
    except Exception as exc:
        logger.error(f"Error executing online benchmark: {exc}")
        raise HTTPException(status_code=500, detail=f"Benchmark execution failed: {exc}")
