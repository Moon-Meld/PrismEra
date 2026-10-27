"""prism_core: The Luminary (司光者) - Central orchestrator and router."""

from __future__ import annotations
from typing import Dict, Any

from prismera.state import PrismEraState, LuminaryDecision, StudentSpectrumProfile
from prismera.llm import call_luminary_structured


def luminary_node(state: PrismEraState) -> Dict[str, Any]:
    """司光者 (prism_core) 中枢执行节点。

    执行意图解析、四维基准指标前置校准、状态抽取与下游委派。
    深度绑定严格的 Pydantic Structured Output (LuminaryDecision)，
    实现零格式报错的状态提取与动态路由。
    """
    messages = state.get("messages", [])
    profile = state.get("student_profile", {})

    # 注入前置轮次路由决策上下文供状态机连续推理
    profile_context = dict(profile)
    profile_context["prev_routing_decision"] = state.get("routing_decision")

    # 通过双模 LLM 引擎调用结构化决策
    decision: LuminaryDecision = call_luminary_structured(messages, profile_context)

    # 合并抽取到的状态增量到全局学生光谱档案
    merged_profile: StudentSpectrumProfile = dict(profile)  # type: ignore
    if decision.state_updates:
        for k, v in decision.state_updates.items():
            merged_profile[k] = v  # type: ignore

    return {
        "student_profile": merged_profile,
        "active_agent": decision.target_agent_id,
        "routing_decision": decision.routing_decision,
        "luminary_thought": decision.luminary_thought,
        "task_briefing": decision.task_briefing,
        "latest_response": decision.message_to_user,
    }
