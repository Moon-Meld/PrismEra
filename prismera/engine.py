"""PrismEra LangGraph Orchestration Engine.

Compiles the 5 agents into a deterministic, state-machine driven StateGraph
with dynamic conditional routing and spectrum profile persistence.
"""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Literal, AsyncGenerator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from prismera.state import PrismEraState, create_initial_spectrum_profile
from prismera.agents.luminary import luminary_node
from prismera.agents.facet import facet_node
from prismera.agents.locus import locus_node
from prismera.agents.disperser import disperser_node
from prismera.agents.resonator import resonator_node
from prismera.agents.echo import echo_node

AGENT_METADATA = {
    "luminary": {
        "id": "luminary",
        "node_id": "prism_core",
        "name": "司光者",
        "badge": "The Luminary",
        "title": "中枢光轴 · 意图解析与总控路由",
        "color": "#F8FAFC",
        "glow": "rgba(248, 250, 252, 0.4)",
    },
    "facet": {
        "id": "facet",
        "node_id": "prism_facet",
        "name": "切面师",
        "badge": "The Facet",
        "title": "光谱分光仪 · 成绩单切面与先修课图谱",
        "color": "#06B6D4",
        "glow": "rgba(6, 182, 212, 0.4)",
        "tools": [
            {"name": "calculate_gpa_metrics", "desc": "正在执行确定性 GPA 标尺计算 (WES / 4.0 算法)..."},
            {"name": "check_prerequisite_graph", "desc": "正在对齐目标专业先修课知识图谱并诊断结构性暗区..."}
        ]
    },
    "locus": {
        "id": "locus",
        "node_id": "prism_locus",
        "name": "定焦师",
        "badge": "The Locus",
        "title": "全局透镜 · 知识图谱三步定焦与零幻觉矩阵",
        "color": "#F59E0B",
        "glow": "rgba(245, 158, 11, 0.4)",
        "tools": [
            {"name": "cypher_filter_programs", "desc": "正在执行知识图谱硬性剪枝 (Cypher Filter) 校验院校与语言标尺..."},
            {"name": "search_peer_admission_cases", "desc": "正在检索同辈录取案例与隐形录取偏好 (Vector RAG)..."}
        ]
    },
    "disperser": {
        "id": "disperser",
        "node_id": "prism_disperser",
        "name": "折光师",
        "badge": "The Disperser",
        "title": "暗室暗房 · 苏格拉底文书挖掘与去AI化淬炼",
        "color": "#A855F7",
        "glow": "rgba(168, 85, 247, 0.4)",
        "tools": [
            {"name": "get_program_ethos_and_courses", "desc": "正在调阅目标项目培养内核与特色课程大纲..."},
            {"name": "anti_ai_polishing", "desc": "正在校验反 AI 塑料词汇黑名单与工程现场感..."}
        ]
    },
    "resonator": {
        "id": "resonator",
        "node_id": "prism_resonator",
        "name": "共鸣者",
        "badge": "The Resonator",
        "title": "激光谐振腔 · 学术文献图谱共振与高信噪比套磁",
        "color": "#10B981",
        "glow": "rgba(16, 185, 129, 0.4)",
        "tools": [
            {"name": "fetch_scholar_recent_papers", "desc": "正在检索学者近 3 年学术图谱与最新预印本..."},
            {"name": "academic_integrity_check", "desc": "正在执行学术诚信红线验证与共振频率匹配..."}
        ]
    },
    "echo": {
        "id": "echo",
        "node_id": "prism_echo",
        "name": "回音壁",
        "badge": "The Echo",
        "title": "回声测试仪 · 模拟面试与网申护航官",
        "color": "#38BDF8",
        "glow": "rgba(56, 189, 248, 0.4)",
        "tools": [
            {"name": "retrieve_interview_question_bank", "desc": "正在调阅目标项目全真题库与考核维度 (Kira/校友/学术)..."},
            {"name": "generate_application_timeline", "desc": "正在生成精准网申倒计时看板、材料清单与推荐信催交节点..."}
        ]
    }
}

NODE_TO_AGENT = {
    "prism_core": "luminary",
    "prism_facet": "facet",
    "prism_locus": "locus",
    "prism_disperser": "disperser",
    "prism_resonator": "resonator",
    "prism_echo": "echo",
}


def route_luminary_decision(
    state: PrismEraState
) -> Literal["prism_facet", "prism_locus", "prism_disperser", "prism_resonator", "prism_echo", "__end__"]:
    """Conditional router analyzing the Luminary's decision."""
    decision = state.get("routing_decision")
    target = state.get("active_agent")

    if decision == "DELEGATE_TO_AGENT" and target in [
        "prism_facet", "prism_locus", "prism_disperser", "prism_resonator", "prism_echo"
    ]:
        return target  # type: ignore

    return "__end__"


def build_prismera_graph(use_memory: bool = True):
    """Build and compile the PrismEra LangGraph state graph.

    Graph Architecture:
          [ User Input ]
                │
                ▼
        ┌───────────────┐
        │  prism_core   │◄─── (Central Router & Memory)
        └───────┬───────┘
                │
         [Condition: routing_decision]
          ├── "ASK_FOR_CLARIFICATION" / "DIRECT_ANSWER" ──► [ END ]
          │
          └── "DELEGATE_TO_AGENT"
                ├──► prism_facet      ──► [ END ]
                ├──► prism_locus      ──► [ END ]
                ├──► prism_disperser  ──► [ END ]
                └──► prism_resonator  ──► [ END ]
    """
    workflow = StateGraph(PrismEraState)

    # 1. Add agent nodes
    workflow.add_node("prism_core", luminary_node)
    workflow.add_node("prism_facet", facet_node)
    workflow.add_node("prism_locus", locus_node)
    workflow.add_node("prism_disperser", disperser_node)
    workflow.add_node("prism_resonator", resonator_node)
    workflow.add_node("prism_echo", echo_node)

    # 2. Set entry point to central orchestrator
    workflow.set_entry_point("prism_core")

    # 3. Add dynamic conditional branching
    workflow.add_conditional_edges(
        "prism_core",
        route_luminary_decision,
        {
            "prism_facet": "prism_facet",
            "prism_locus": "prism_locus",
            "prism_disperser": "prism_disperser",
            "prism_resonator": "prism_resonator",
            "prism_echo": "prism_echo",
            "__end__": END,
        }
    )

    # 4. Leaf specialist agents return directly to caller
    workflow.add_edge("prism_facet", END)
    workflow.add_edge("prism_locus", END)
    workflow.add_edge("prism_disperser", END)
    workflow.add_edge("prism_resonator", END)
    workflow.add_edge("prism_echo", END)

    # 5. Compile with optional memory checkpointer
    checkpointer = MemorySaver() if use_memory else None
    app = workflow.compile(checkpointer=checkpointer)
    return app


# Global in-memory session registry shared across engine and API gateway
_SESSION_REGISTRY: Dict[str, PrismEraSession] = {}


class _PatchStateDispatcher:
    """Descriptor enabling PrismEraSession.patch_state(...) both on class and instances."""

    def __get__(self, obj, objtype=None):
        if obj is None:
            # Called on class: PrismEraSession.patch_state(session_id, state_patch)
            def class_call(session_id: str, state_patch: Dict[str, Any]):
                sess = objtype.get_session(session_id)
                return sess._patch_state_internal(state_patch)
            return class_call
        else:
            # Called on instance: session.patch_state(...)
            def instance_call(*args, **kwargs):
                if len(args) == 2 and isinstance(args[0], str):
                    return obj._patch_state_internal(args[1])
                elif len(args) == 1 and isinstance(args[0], dict):
                    return obj._patch_state_internal(args[0])
                elif "state_patch" in kwargs:
                    return obj._patch_state_internal(kwargs["state_patch"])
                raise ValueError("Invalid arguments passed to patch_state")
            return instance_call


class PrismEraSession:
    """High-level interactive session manager for PrismEra."""

    patch_state = _PatchStateDispatcher()

    def __init__(self, thread_id: str = "default_session", name: Optional[str] = None):
        self.thread_id = thread_id
        self.app = build_prismera_graph(use_memory=True)
        from prismera.db.session_store import get_session_store
        self.store = get_session_store()

        saved_data = self.store.load_session_data(thread_id)
        if saved_data:
            self.state: PrismEraState = {
                "messages": saved_data.get("messages", []),
                "student_profile": saved_data.get("student_profile", create_initial_spectrum_profile()),
                "active_agent": saved_data.get("active_agent"),
                "routing_decision": saved_data.get("routing_decision"),
                "luminary_thought": saved_data.get("luminary_thought"),
                "task_briefing": saved_data.get("task_briefing"),
                "latest_response": saved_data.get("latest_response"),
                "pending_human_review": saved_data.get("pending_human_review"),
                "metadata": saved_data.get("metadata", {"thread_id": thread_id, "name": saved_data.get("name")}),
            }
            config = {"configurable": {"thread_id": self.thread_id}}
            try:
                self.app.update_state(
                    config,
                    {
                        "student_profile": self.state["student_profile"],
                        "pending_human_review": self.state.get("pending_human_review"),
                    }
                )
            except Exception:
                pass
        else:
            self.state: PrismEraState = {
                "messages": [],
                "student_profile": create_initial_spectrum_profile(),
                "active_agent": None,
                "routing_decision": None,
                "luminary_thought": None,
                "task_briefing": None,
                "latest_response": None,
                "pending_human_review": None,
                "metadata": {"thread_id": thread_id, "name": name or f"学员档案 ({thread_id[:8]})"}
            }
            self.store.save_session(self.thread_id, self.state, name=name)

        _SESSION_REGISTRY[thread_id] = self

    def save(self, name: Optional[str] = None) -> None:
        """Persist current session state to SQLite store."""
        if hasattr(self, "store") and self.store:
            self.store.save_session(self.thread_id, self.state, name=name)

    def rename(self, new_name: str) -> bool:
        """Rename the current session in SQLite store and metadata."""
        if hasattr(self, "store") and self.store:
            res = self.store.rename_session(self.thread_id, new_name)
            if res:
                self.state.setdefault("metadata", {})["name"] = new_name
            return res
        return False

    @classmethod
    def get_session(cls, session_id: str) -> PrismEraSession:
        """Retrieve existing session or create a new registered session."""
        if session_id not in _SESSION_REGISTRY:
            _SESSION_REGISTRY[session_id] = PrismEraSession(thread_id=session_id)
        return _SESSION_REGISTRY[session_id]

    def _patch_state_internal(self, state_patch: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate session state and synchronize write-back to LangGraph Checkpointer tree."""
        profile = self.state["student_profile"]

        # 1. Direct profile nested dictionary
        if "student_profile" in state_patch and isinstance(state_patch["student_profile"], dict):
            for k, v in state_patch["student_profile"].items():
                profile[k] = v

        # 2. Top-level profile attributes
        for k in [
            "shortlisted_programs", "sop_outline", "sop_draft", "sop_critique",
            "sop_versions", "locked_target_program", "sop_stage", "mined_story_fragments",
            "undergrad_tier", "undergrad_name", "major", "gpa_raw", "language_scores",
            "interview_records", "application_timeline"
        ]:
            if k in state_patch:
                profile[k] = state_patch[k]

        # 3. Top-level state fields
        if "pending_human_review" in state_patch:
            self.state["pending_human_review"] = state_patch["pending_human_review"]
        if "latest_response" in state_patch:
            self.state["latest_response"] = state_patch["latest_response"]
        if "messages" in state_patch and isinstance(state_patch["messages"], list):
            self.state["messages"].extend(state_patch["messages"])

        # 4. Synchronize write-back to LangGraph checkpointer
        config = {"configurable": {"thread_id": self.thread_id}}
        try:
            self.app.update_state(
                config,
                {
                    "student_profile": self.state["student_profile"],
                    "pending_human_review": self.state.get("pending_human_review"),
                }
            )
        except Exception:
            pass

        # 5. Persist to SQLite
        self.save()

        return {
            "session_id": self.thread_id,
            "status": "success",
            "student_profile": self.state["student_profile"],
            "pending_human_review": self.state.get("pending_human_review"),
        }

    def send_user_message(self, content: str) -> Dict[str, Any]:
        """Deliver user message into the graph and run execution cycle."""
        self.state["messages"].append({"role": "user", "content": content})
        config = {"configurable": {"thread_id": self.thread_id}}

        # Execute through the graph
        output_state = self.app.invoke(self.state, config=config)

        # Update local memory
        self.state = output_state
        latest_reply = output_state.get("latest_response", "")
        self.state["messages"].append({"role": "assistant", "content": latest_reply})

        # Persist to SQLite
        self.save()

        return output_state

    def upload_document(self, file_path_or_text: str) -> Dict[str, Any]:
        """Parse student document and synchronize directly into student spectrum profile."""
        import os
        from prismera.tools.document_parser import parse_student_document
        parsed = parse_student_document(file_path_or_text)

        profile = self.state["student_profile"]
        if parsed.get("undergrad_name"):
            profile["undergrad_name"] = parsed["undergrad_name"]
        if parsed.get("undergrad_tier"):
            profile["undergrad_tier"] = parsed["undergrad_tier"]
        if parsed.get("major"):
            profile["major"] = parsed["major"]
        if parsed.get("gpa_raw"):
            profile["gpa_raw"] = parsed["gpa_raw"]
        if parsed.get("language_scores"):
            profile["language_scores"].update(parsed["language_scores"])
        if parsed.get("gre_gmat"):
            profile["gre_gmat"] = parsed["gre_gmat"]
        if parsed.get("prerequisite_grades"):
            if "prerequisite_grades" not in profile or profile["prerequisite_grades"] is None:
                profile["prerequisite_grades"] = {}
            profile["prerequisite_grades"].update(parsed["prerequisite_grades"])
        if parsed.get("experiences"):
            profile["experiences"] = parsed["experiences"]

        doc_name = os.path.basename(file_path_or_text) if os.path.exists(file_path_or_text) else "Uploaded_Document"
        if "parsed_documents" not in profile or profile["parsed_documents"] is None:
            profile["parsed_documents"] = []
        profile["parsed_documents"].append(doc_name)

        upload_event = (
            f"【系统事件 · 档案导入】已完成《{doc_name}》解析，学生光谱档案硬指标已自动同步更新。"
        )
        self.state["messages"].append({"role": "system", "content": upload_event})
        self.save()
        return parsed

    async def stream_user_message(self, content: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream execution cycle with node switches, thoughts, tool events, tokens, and profile updates."""
        # 1. Start event
        yield {
            "event": "start",
            "data": {
                "session_id": self.thread_id,
                "user_message": content,
            }
        }

        # 2. Add user message
        self.state["messages"].append({"role": "user", "content": content})
        config = {"configurable": {"thread_id": self.thread_id}}

        # 3. Initially activate Luminary
        luminary_meta = AGENT_METADATA["luminary"]
        yield {
            "event": "agent_switch",
            "data": {
                "agent_id": "luminary",
                "name": luminary_meta["name"],
                "badge": luminary_meta["badge"],
                "title": luminary_meta["title"],
                "color": luminary_meta["color"],
                "status": "analyzing"
            }
        }
        await asyncio.sleep(0.02)

        # 4. Stream graph nodes
        final_response = ""
        last_active_agent = "luminary"

        for step in self.app.stream(self.state, config=config, stream_mode="updates"):
            for node_name, node_output in step.items():
                agent_id = NODE_TO_AGENT.get(node_name, node_name)
                last_active_agent = agent_id

                # Update internal state with node output
                for k, v in node_output.items():
                    self.state[k] = v

                # Handle Luminary specific outputs
                if node_name == "prism_core":
                    thought = node_output.get("luminary_thought")
                    if thought:
                        yield {
                            "event": "thought",
                            "data": {
                                "agent": "luminary",
                                "thought": thought
                            }
                        }
                        await asyncio.sleep(0.015)

                    # Yield current profile snapshot
                    yield {
                        "event": "profile_update",
                        "data": {
                            "student_profile": self.state["student_profile"]
                        }
                    }

                    # Check routing decision
                    routing = node_output.get("routing_decision")
                    target = node_output.get("active_agent")
                    if routing == "DELEGATE_TO_AGENT" and target:
                        target_key = NODE_TO_AGENT.get(target, target.replace("prism_", ""))
                        target_meta = AGENT_METADATA.get(target_key, {})
                        yield {
                            "event": "agent_switch",
                            "data": {
                                "agent_id": target_key,
                                "name": target_meta.get("name", target_key),
                                "badge": target_meta.get("badge", target_key),
                                "title": target_meta.get("title", ""),
                                "color": target_meta.get("color", "#FFFFFF"),
                                "status": "executing"
                            }
                        }
                        await asyncio.sleep(0.03)

                        # Emit tool call events for this agent
                        for tool in target_meta.get("tools", []):
                            yield {
                                "event": "tool_call",
                                "data": {
                                    "agent": target_key,
                                    "tool": tool["name"],
                                    "description": tool["desc"],
                                    "status": "executing"
                                }
                            }
                            await asyncio.sleep(0.03)
                            yield {
                                "event": "tool_result",
                                "data": {
                                    "agent": target_key,
                                    "tool": tool["name"],
                                    "description": tool["desc"],
                                    "status": "completed"
                                }
                            }
                            await asyncio.sleep(0.02)
                else:
                    # Specialist node finished
                    yield {
                        "event": "profile_update",
                        "data": {
                            "student_profile": self.state["student_profile"]
                        }
                    }

                # If this node produced a latest_response, stream its tokens!
                resp = node_output.get("latest_response")
                if resp:
                    final_response = resp
                    chunk_size = 6
                    for i in range(0, len(resp), chunk_size):
                        chunk = resp[i:i+chunk_size]
                        yield {
                            "event": "token",
                            "data": {
                                "agent": agent_id,
                                "token": chunk
                            }
                        }
                        await asyncio.sleep(0.005)

        # Append assistant response to messages history
        if final_response:
            self.state["messages"].append({"role": "assistant", "content": final_response})

        # Persist updated turn to SQLite store
        self.save()

        # Check if node suspended for Human-in-the-Loop review
        if self.state.get("pending_human_review"):
            yield {
                "event": "human_review_required",
                "data": {
                    "session_id": self.thread_id,
                    "review_type": self.state.get("pending_human_review"),
                    "agent": last_active_agent,
                    "sop_stage": self.state["student_profile"].get("sop_stage", 1),
                    "shortlisted_programs": self.state["student_profile"].get("shortlisted_programs", []),
                    "sop_outline": self.state["student_profile"].get("sop_outline"),
                }
            }

        # Final done event
        yield {
            "event": "done",
            "data": {
                "session_id": self.thread_id,
                "latest_response": final_response,
                "student_profile": self.state["student_profile"],
                "active_agent": last_active_agent,
                "sop_stage": self.state["student_profile"].get("sop_stage", 1),
                "shortlisted_programs": self.state["student_profile"].get("shortlisted_programs", []),
                "sop_outline": self.state["student_profile"].get("sop_outline"),
                "sop_draft": self.state["student_profile"].get("sop_draft"),
                "sop_versions": self.state["student_profile"].get("sop_versions", []),
                "locked_target_program": self.state["student_profile"].get("locked_target_program"),
                "interview_records": self.state["student_profile"].get("interview_records", []),
                "application_timeline": self.state["student_profile"].get("application_timeline", []),
                "pending_human_review": self.state.get("pending_human_review"),
            }
        }
