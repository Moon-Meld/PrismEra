"""PrismEra LangGraph Orchestration Engine.

Compiles the 5 agents into a deterministic, state-machine driven StateGraph
with dynamic conditional routing and spectrum profile persistence.
"""

from __future__ import annotations
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from prismera.state import PrismEraState, create_initial_spectrum_profile
from prismera.agents.luminary import luminary_node
from prismera.agents.facet import facet_node
from prismera.agents.locus import locus_node
from prismera.agents.disperser import disperser_node
from prismera.agents.resonator import resonator_node


def route_luminary_decision(
    state: PrismEraState
) -> Literal["prism_facet", "prism_locus", "prism_disperser", "prism_resonator", "__end__"]:
    """Conditional router analyzing the Luminary's decision."""
    decision = state.get("routing_decision")
    target = state.get("active_agent")

    if decision == "DELEGATE_TO_AGENT" and target in [
        "prism_facet", "prism_locus", "prism_disperser", "prism_resonator"
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
            "__end__": END,
        }
    )

    # 4. Leaf specialist agents return directly to caller
    workflow.add_edge("prism_facet", END)
    workflow.add_edge("prism_locus", END)
    workflow.add_edge("prism_disperser", END)
    workflow.add_edge("prism_resonator", END)

    # 5. Compile with optional memory checkpointer
    checkpointer = MemorySaver() if use_memory else None
    app = workflow.compile(checkpointer=checkpointer)
    return app


class PrismEraSession:
    """High-level interactive session manager for PrismEra."""

    def __init__(self, thread_id: str = "default_session"):
        self.thread_id = thread_id
        self.app = build_prismera_graph(use_memory=True)
        self.state: PrismEraState = {
            "messages": [],
            "student_profile": create_initial_spectrum_profile(),
            "active_agent": None,
            "routing_decision": None,
            "luminary_thought": None,
            "task_briefing": None,
            "latest_response": None,
            "metadata": {"thread_id": thread_id}
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

        return output_state
