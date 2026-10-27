"""Unit tests for the Dual-Mode LLM Engine and Structured Output."""

import pytest
from pydantic import ValidationError
from prismera.config import is_offline_mock
from prismera.llm import (
    get_llm,
    MockLLM,
    call_luminary_structured,
    _clean_json_markdown,
)
from prismera.state import LuminaryDecision, create_initial_spectrum_profile


def test_dual_mode_default_offline_mock():
    """Verify that without API keys in environment, engine defaults to offline Mock mode."""
    assert is_offline_mock() is True
    llm = get_llm()
    assert isinstance(llm, MockLLM)
    assert llm.is_mock is True


def test_clean_json_markdown():
    wrapped = "```json\n{\"test\": 123}\n```"
    assert _clean_json_markdown(wrapped) == '{"test": 123}'

    wrapped_no_lang = "```\n{\"key\": \"val\"}\n```"
    assert _clean_json_markdown(wrapped_no_lang) == '{"key": "val"}'

    clean = '{"status": "ok"}'
    assert _clean_json_markdown(clean) == clean


def test_luminary_structured_output_schema():
    """Verify LuminaryDecision enforces Pydantic structured output with zero format errors."""
    decision = LuminaryDecision(
        luminary_thought="Testing structured output validation",
        state_updates={"undergrad_tier": "985", "gpa_raw": "88/100"},
        routing_decision="DELEGATE_TO_AGENT",
        target_agent_id="prism_locus",
        task_briefing="Execute locus positioning",
        message_to_user=None,
    )

    # Valid schema serialization
    dumped = decision.model_dump()
    assert dumped["routing_decision"] == "DELEGATE_TO_AGENT"
    assert dumped["target_agent_id"] == "prism_locus"
    assert dumped["state_updates"]["gpa_raw"] == "88/100"

    # Strict enum check: invalid routing decision must raise ValidationError
    with pytest.raises(ValidationError):
        LuminaryDecision(
            luminary_thought="Bad decision",
            routing_decision="INVALID_DECISION_TYPE",  # type: ignore
        )


def test_call_luminary_structured_mock():
    messages = [{"role": "user", "content": "你好，想了解一下留学规划"}]
    profile = create_initial_spectrum_profile()

    decision = call_luminary_structured(messages, profile)
    assert isinstance(decision, LuminaryDecision)
    assert decision.routing_decision == "DIRECT_ANSWER"
    assert "司光者" in (decision.message_to_user or "")
    assert decision.target_agent_id is None
