"""Unit tests for the Anti-AI Lexicon Output Guardrail."""

import pytest
from prismera.guardrails import AntiAIGuardrail
from prismera.prompts.brand_voice import ANTI_AI_BANNED_WORDS
from prismera.agents.disperser import disperser_node
from prismera.state import create_initial_spectrum_profile, PrismEraState


def test_guardrail_detection_banned_words():
    guardrail = AntiAIGuardrail()
    sample_text = (
        "My journey in computer science is a testament to my unwavering passion. "
        "I hope to delve into the realm of distributed systems, creating a rich tapestry of microservices."
    )
    hits = guardrail.scan(sample_text)

    # Should detect the banned words
    assert "unwavering passion" in hits
    assert "testament to" in hits or "testament" in hits
    assert "delve into" in hits or "delve" in hits
    assert "realm" in hits
    assert "rich tapestry" in hits or "tapestry" in hits


def test_guardrail_clean_text_no_false_positives():
    guardrail = AntiAIGuardrail()
    clean_academic_text = (
        "We benchmarked the asynchronous ring buffer under simulated 15% packet drops, "
        "measuring a 28% decrease in failover latency across three nodes."
    )
    hits = guardrail.scan(clean_academic_text)
    assert len(hits) == 0

    cleansed, was_rewritten, violations = guardrail.apply(clean_academic_text)
    assert was_rewritten is False
    assert cleansed == clean_academic_text
    assert len(violations) == 0


def test_guardrail_deterministic_rewriting():
    guardrail = AntiAIGuardrail()
    violating_text = (
        "I decided to delve into distributed protocols. "
        "This experience became a testament to our perseverance in this realm."
    )
    hits = guardrail.scan(violating_text)
    assert len(hits) > 0

    cleansed, was_rewritten, violations = guardrail.apply(violating_text)
    assert was_rewritten is True

    # Check that none of the original violations remain in cleansed text
    remaining_hits = guardrail.scan(cleansed)
    assert "delve into" not in remaining_hits
    assert "testament to" not in remaining_hits
    assert "realm" not in remaining_hits


def test_disperser_stage3_guardrail_integration():
    """Ensure disperser_node Stage 3 draft passes through the Output Guardrail."""
    guardrail = AntiAIGuardrail()
    state: PrismEraState = {
        "messages": [
            {"role": "user", "content": "帮我写CMU软件工程SOP"},
            {"role": "assistant", "content": "折光师 Stage 1 访谈"},
            {"role": "user", "content": "我在项目中遇到并发瓶颈并优化了参数"},
            {"role": "assistant", "content": "折光师 Stage 2 大纲"},
            {"role": "user", "content": "确认大纲，请开始执笔成文"},
        ],
        "student_profile": {
            **create_initial_spectrum_profile(),
            "sop_stage": 2,
            "mined_story_fragments": ["在高并发丢包下重构调度器"],
        },
        "active_agent": "prism_disperser",
        "routing_decision": "DELEGATE_TO_AGENT",
        "luminary_thought": "推进文书",
        "task_briefing": None,
        "latest_response": None,
        "metadata": {},
    }

    result = disperser_node(state)
    latest_reply = result.get("latest_response", "")

    # Stage 3 response should be generated
    assert "Stage 3 执笔成文" in latest_reply

    # The generated draft must NOT contain any banned AI clichés
    hits = guardrail.scan(latest_reply)
    # Filter out mention of banned words inside explanation headers (like "全篇禁用 delve into...")
    # by checking the actual draft markdown block
    if "```markdown" in latest_reply:
        draft_block = latest_reply.split("```markdown")[1].split("```")[0]
        draft_hits = guardrail.scan(draft_block)
        assert len(draft_hits) == 0, f"Draft block contains banned words: {draft_hits}"
