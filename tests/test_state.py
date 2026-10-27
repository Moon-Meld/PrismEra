"""Tests for PrismEra state structures."""

from prismera.state import create_initial_spectrum_profile, LuminaryDecision


def test_initial_spectrum_profile():
    profile = create_initial_spectrum_profile()
    assert profile["undergrad_tier"] is None
    assert profile["undergrad_name"] is None
    assert profile["major"] is None
    assert profile["gpa_raw"] is None
    assert profile["language_scores"] == {}
    assert profile["target_regions"] == []
    assert profile["target_majors"] == []
    assert profile["sop_stage"] == 1
    assert profile["shortlisted_programs"] == []


def test_luminary_decision_schema():
    decision = LuminaryDecision(
        luminary_thought="Testing orchestration",
        state_updates={"gpa_raw": "3.8/4.0"},
        routing_decision="DELEGATE_TO_AGENT",
        target_agent_id="prism_facet",
        task_briefing="Test briefing",
        message_to_user=None,
    )
    assert decision.target_agent_id == "prism_facet"
    assert decision.state_updates["gpa_raw"] == "3.8/4.0"
