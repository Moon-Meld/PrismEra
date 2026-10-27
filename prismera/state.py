"""PrismEra Global State and Spectrum Profile definitions.

Defines the core data structures for multi-agent coordination,
maintaining the student's optical spectrum profile across conversation turns.
"""

from __future__ import annotations
from typing import TypedDict, List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field


class StudentSpectrumProfile(TypedDict):
    """The evolving spectrum profile of the applicant."""
    # 基础硬指标（由司光者与切面师维护）
    undergrad_tier: Optional[str]        # 如: "985", "211", "双非一本", "海本"
    undergrad_name: Optional[str]        # 具体本科院校名称（用于查英国/港新List）
    major: Optional[str]                 # 本科专业
    gpa_raw: Optional[str]               # 原始均分/GPA（如 "86.5/100" 或 "3.6/4.0"）
    language_scores: Dict[str, float]    # 如: {"IELTS_total": 7.0, "speaking": 5.5}
    gre_gmat: Optional[Dict[str, int]]   # GRE/GMAT 分数
    
    # 申请意向与边界
    target_regions: List[str]            # 如: ["UK", "HK", "SG", "US"]
    target_majors: List[str]             # 如: ["CS", "DS", "BA"]
    budget_rmb_wan: Optional[int]        # 预算上限（万元）
    
    # 动态工作流产物（由定焦师、折光师、共鸣者写入）
    shortlisted_programs: List[Dict[str, Any]]     # 已锁定的冲/稳/保项目列表
    sop_stage: int                                 # 文书状态机当前阶段 (1:挖掘, 2:大纲, 3:初稿, 4:审片)
    mined_story_fragments: List[str]               # 折光师采访挖掘出的独家故事细节碎片
    target_professors: List[Dict[str, Any]]        # 共鸣者锁定的套磁导师与论文匹配点


def create_initial_spectrum_profile() -> StudentSpectrumProfile:
    """Creates a blank StudentSpectrumProfile."""
    return {
        "undergrad_tier": None,
        "undergrad_name": None,
        "major": None,
        "gpa_raw": None,
        "language_scores": {},
        "gre_gmat": None,
        "target_regions": [],
        "target_majors": [],
        "budget_rmb_wan": None,
        "shortlisted_programs": [],
        "sop_stage": 1,
        "mined_story_fragments": [],
        "target_professors": [],
    }


class LuminaryDecision(BaseModel):
    """Structured decision output produced by prism_core (The Luminary)."""
    luminary_thought: str = Field(
        description="分析用户当前情绪、意图、档案完备度及路由逻辑"
    )
    state_updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="从对话中提取并需要更新到学生档案的字段"
    )
    routing_decision: Literal["ASK_FOR_CLARIFICATION", "DELEGATE_TO_AGENT", "DIRECT_ANSWER"] = Field(
        description="路由决断：追问缺失信息、委派专职智能体、或直接回答"
    )
    target_agent_id: Optional[Literal["prism_facet", "prism_locus", "prism_disperser", "prism_resonator"]] = Field(
        default=None,
        description="目标子智能体组件 ID"
    )
    task_briefing: Optional[str] = Field(
        default=None,
        description="向目标子Agent下达的精确上下文与执行要求"
    )
    message_to_user: Optional[str] = Field(
        default=None,
        description="当需要直接向用户追问或总结时展示的文本（保持PrismEra智性温和的语调）"
    )


class PrismEraState(TypedDict):
    """Global orchestrator state passed across nodes in the LangGraph graph."""
    messages: List[Dict[str, str]]             # [{'role': 'user'|'assistant'|'system', 'content': '...'}]
    student_profile: StudentSpectrumProfile    # 全局学生光谱档案
    active_agent: Optional[str]                # 当前正在执行或即将调度的 Agent ID
    routing_decision: Optional[str]            # 'ASK_FOR_CLARIFICATION' | 'DELEGATE_TO_AGENT' | 'DIRECT_ANSWER'
    luminary_thought: Optional[str]            # 司光者推理过程
    task_briefing: Optional[str]               # 司光者派发给子 Agent 的任务简报
    latest_response: Optional[str]             # 最新返回给用户的文本
    metadata: Dict[str, Any]                   # 调试或追踪上下文
