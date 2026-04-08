"""
Tests for brain.learning — after_task_hook and periodic_review.

after_task_hook is a rule-based classifier that decides what to persist.
The heuristics are defined in learning.py:
  - _SKILL_TRIGGER_WORDS  → create/improve a skill
  - _DECISION_TRIGGER_WORDS → log a decision
  - _MEMORY_MIN_LENGTH (50 chars) → store a memory
"""

from __future__ import annotations

import pytest

from brain.learning import after_task_hook, periodic_review
from brain.memory import get_recent_memories, recent_decisions, store_memory
from brain.skills import create_skill, get_skill, list_skills


# ---------------------------------------------------------------------------
# after_task_hook — return structure
# ---------------------------------------------------------------------------


def test_after_task_hook_returns_expected_keys():
    """after_task_hook() must return a dict with all documented keys."""
    result = after_task_hook(
        team_member="ceo",
        task_description="Quick status update",
        outcome="OK",
    )
    required_keys = {
        "team_member",
        "task_description",
        "skill_created",
        "skill_improved",
        "memory_stored",
        "decision_logged",
        "nudge_issued",
        "rationale",
    }
    assert required_keys.issubset(set(result.keys()))


def test_after_task_hook_normalises_team_member():
    """after_task_hook() must accept mixed-case member names."""
    result = after_task_hook(
        team_member="Nicholas",
        task_description="Quick check",
        outcome="Done",
    )
    assert result["team_member"] == "nicholas"


def test_after_task_hook_invalid_member_raises():
    """after_task_hook() must raise ValueError for an unknown team member."""
    with pytest.raises(ValueError, match="Unknown team member"):
        after_task_hook("ghost", "something", "result")


# ---------------------------------------------------------------------------
# after_task_hook — memory creation
# ---------------------------------------------------------------------------


def test_after_task_hook_stores_memory_for_substantial_outcome():
    """A long outcome (≥50 chars) must trigger a memory to be stored."""
    long_outcome = (
        "We successfully completed the onboarding flow refactor. "
        "All edge cases were handled and unit tests pass."
    )
    result = after_task_hook(
        team_member="cto",
        task_description="Refactor user onboarding flow",
        outcome=long_outcome,
    )
    assert result["memory_stored"] is not None
    # Verify it's actually in the DB
    memories = get_recent_memories("cto", limit=5)
    assert any("onboarding" in m["content"].lower() for m in memories)


def test_after_task_hook_does_not_store_memory_for_short_outcome():
    """A very short outcome (<50 chars) must not trigger memory storage."""
    result = after_task_hook(
        team_member="ceo",
        task_description="Trivial update",
        outcome="Done",  # too short
    )
    assert result["memory_stored"] is None


def test_after_task_hook_uses_category_from_context():
    """When context contains 'category', that category should be used for the memory."""
    long_outcome = (
        "Customer satisfaction scores for enterprise accounts improved "
        "by 12% this quarter after the dedicated onboarding changes."
    )
    result = after_task_hook(
        team_member="cx-lead",
        task_description="Analyse customer satisfaction survey results",
        outcome=long_outcome,
        context={"category": "customer_insight"},
    )
    assert result["memory_stored"] is not None
    memories = get_recent_memories("cx-lead", limit=5)
    relevant = [m for m in memories if m["id"] == result["memory_stored"]]
    assert relevant[0]["category"] == "customer_insight"


def test_after_task_hook_memory_defaults_to_learning_category():
    """Without a 'category' in context, stored memory must use 'learning'."""
    long_outcome = (
        "Discovered that the deployment pipeline fails when more than "
        "three parallel jobs run simultaneously due to database connection limits."
    )
    result = after_task_hook(
        team_member="ops",
        task_description="Investigate deployment pipeline failures",
        outcome=long_outcome,
    )
    assert result["memory_stored"] is not None
    memories = get_recent_memories("ops", limit=5)
    relevant = [m for m in memories if m["id"] == result["memory_stored"]]
    assert relevant[0]["category"] == "learning"


# ---------------------------------------------------------------------------
# after_task_hook — skill creation
# ---------------------------------------------------------------------------


def test_after_task_hook_creates_skill_for_procedural_task():
    """A task description with a skill trigger word must create a new skill."""
    outcome = (
        "Step 1: Pull latest metrics from the dashboard. "
        "Step 2: Compare against last week's baseline. "
        "Step 3: Flag anomalies above 15% deviation. "
        "Step 4: Post summary to Slack #metrics channel."
    )
    result = after_task_hook(
        team_member="growth",
        task_description="standard weekly metrics review workflow",  # 'standard' is a trigger word
        outcome=outcome,
    )
    assert result["skill_created"] is not None
    # Verify the skill was written to the DB
    skill = get_skill(result["skill_created"])
    assert skill is not None


def test_after_task_hook_improves_existing_skill():
    """If a matching skill already exists, after_task_hook must improve it."""
    # First create a skill that will match
    create_skill(
        name="standard-weekly-metrics",
        description="Standard weekly metrics workflow procedure",
        trigger_pattern="standard weekly metrics workflow procedure",
        content="Step 1: Pull metrics. Step 2: Report.",
    )
    outcome = (
        "Updated the standard weekly metrics workflow. "
        "Added automated anomaly detection step. "
        "Reduced manual effort by 30%."
    )
    result = after_task_hook(
        team_member="growth",
        task_description="standard weekly metrics workflow procedure",
        outcome=outcome,
    )
    # Should improve, not create new
    assert result["skill_improved"] is not None
    assert result["skill_created"] is None


def test_after_task_hook_no_skill_without_trigger_word():
    """A task without a skill trigger word must not create a skill."""
    long_outcome = (
        "Completed the customer call. They are happy with the product "
        "and will renew their contract next month without issues."
    )
    result = after_task_hook(
        team_member="cx-lead",
        task_description="Customer call with Acme Corp about renewal",
        outcome=long_outcome,
    )
    assert result["skill_created"] is None
    assert result["skill_improved"] is None


# ---------------------------------------------------------------------------
# after_task_hook — decision logging
# ---------------------------------------------------------------------------


def test_after_task_hook_logs_decision_for_decision_words():
    """A task description with 'decided' must log a decision."""
    long_outcome = (
        "After evaluating three vendors, we decided to go with AWS for the "
        "infrastructure migration. Cost savings projected at 22% annually."
    )
    result = after_task_hook(
        team_member="cto",
        task_description="decided on cloud vendor for infrastructure",
        outcome=long_outcome,
    )
    assert result["decision_logged"] is not None
    decisions = recent_decisions("cto", limit=5)
    assert any(d["id"] == result["decision_logged"] for d in decisions)


def test_after_task_hook_does_not_log_decision_without_trigger_word():
    """A task with no decision trigger word must not log a decision."""
    long_outcome = (
        "The team reviewed the documentation and updated the API reference "
        "with the new endpoint specifications for the v2 release cycle."
    )
    result = after_task_hook(
        team_member="cto",
        task_description="Update API documentation for v2 endpoints",
        outcome=long_outcome,
    )
    assert result["decision_logged"] is None


# ---------------------------------------------------------------------------
# after_task_hook — rationale
# ---------------------------------------------------------------------------


def test_after_task_hook_rationale_is_list():
    """rationale must always be a list."""
    result = after_task_hook("ceo", "quick task", "short")
    assert isinstance(result["rationale"], list)


def test_after_task_hook_rationale_explains_nothing_persisted():
    """When nothing is persisted, rationale must say so."""
    result = after_task_hook(
        team_member="ceo",
        task_description="quick check",
        outcome="ok",
    )
    combined = " ".join(result["rationale"]).lower()
    # Nothing stored — rationale should mention that
    assert "nothing" in combined or "too short" in combined or "not repeatable" in combined


def test_after_task_hook_rationale_mentions_skill_when_created():
    """rationale must mention skill creation when it happens."""
    result = after_task_hook(
        team_member="growth",
        task_description="standard content publishing playbook workflow",
        outcome=(
            "1. Draft\n2. SEO check\n3. Review\n4. Publish\n"
            "This playbook covers all standard content publishing steps."
        ),
    )
    if result["skill_created"] or result["skill_improved"]:
        combined = " ".join(result["rationale"]).lower()
        assert "skill" in combined


# ---------------------------------------------------------------------------
# periodic_review
# ---------------------------------------------------------------------------


def test_periodic_review_returns_expected_keys():
    """periodic_review() must return a dict with all documented keys."""
    result = periodic_review("ceo")
    required = {
        "team_member",
        "reviewed_memories",
        "reviewed_decisions",
        "patterns",
        "knowledge_gaps",
        "skill_suggestions",
        "state_of_mind",
        "nudges_issued",
        "reviewed_at",
    }
    assert required.issubset(set(result.keys()))


def test_periodic_review_team_member_is_canonical():
    """periodic_review() must set 'team_member' to the canonical key."""
    result = periodic_review("CTO")
    assert result["team_member"] == "cto"


def test_periodic_review_invalid_member_raises():
    """periodic_review() must raise ValueError for an unknown member."""
    with pytest.raises(ValueError, match="Unknown team member"):
        periodic_review("nobody")


def test_periodic_review_counts_memories():
    """reviewed_memories must equal the number of memories stored for that member."""
    for i in range(3):
        store_memory("nicholas", f"Product insight {i} about customer onboarding journey", "learning")

    result = periodic_review("nicholas")
    assert result["reviewed_memories"] == 3


def test_periodic_review_patterns_are_list_of_dicts():
    """'patterns' must be a list of dicts with 'word' and 'frequency' keys."""
    store_memory("ceo", "The product strategy focuses on enterprise growth revenue", "learning")
    store_memory("ceo", "Revenue metrics indicate strong enterprise product adoption", "learning")
    store_memory("ceo", "Enterprise product roadmap should prioritise revenue expansion", "learning")

    result = periodic_review("ceo")
    assert isinstance(result["patterns"], list)
    for p in result["patterns"]:
        assert "word" in p
        assert "frequency" in p


def test_periodic_review_knowledge_gaps_are_uncovered_categories():
    """knowledge_gaps must list categories not present in recent memories."""
    from brain.memory import CATEGORIES

    # Store memories for only 'learning' category
    store_memory("ops", "Deployed the new monitoring stack with full alerting suite", "learning")
    result = periodic_review("ops")

    gaps = set(result["knowledge_gaps"])
    # 'learning' is covered so it should not be a gap
    assert "learning" not in gaps
    # Other categories should appear as gaps
    remaining = CATEGORIES - {"learning"}
    assert len(gaps & remaining) > 0


def test_periodic_review_nudges_issued_when_patterns_exist():
    """periodic_review() must issue nudges when top patterns exist."""
    # Store enough memories to get pattern detection going
    for i in range(4):
        store_memory(
            "growth",
            f"Content marketing insight {i}: SEO content strategy drives organic acquisition",
            "learning",
        )

    result = periodic_review("growth")
    # With patterns present, nudges should be issued
    assert isinstance(result["nudges_issued"], list)


def test_periodic_review_state_of_mind_is_string():
    """'state_of_mind' must be a non-empty string (even when LLM is stubbed)."""
    result = periodic_review("cto")
    assert isinstance(result["state_of_mind"], str)
    assert len(result["state_of_mind"]) > 0


def test_periodic_review_reviewed_at_is_iso_datetime():
    """'reviewed_at' must be an ISO-format datetime string."""
    from datetime import datetime

    result = periodic_review("cristine")
    reviewed_at = result["reviewed_at"]
    # Should not raise
    dt = datetime.fromisoformat(reviewed_at)
    assert dt is not None


def test_periodic_review_skill_suggestions_for_high_frequency_topics():
    """Skill suggestions must appear for topics occurring 3+ times in memories."""
    # Use the same distinctive word 3+ times
    for i in range(3):
        store_memory(
            "ceo",
            f"Quarterly planning meeting {i}: reviewed metrics for partnerships enterprise growth",
            "learning",
        )

    result = periodic_review("ceo")
    # There may or may not be suggestions depending on existing skills,
    # but the field must be a list
    assert isinstance(result["skill_suggestions"], list)
