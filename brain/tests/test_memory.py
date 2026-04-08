"""
Tests for brain.memory — store_memory, search_memories, get_recent_memories,
log_decision, search_decisions, nudge_check, session lifecycle, and nudge marking.
"""

from __future__ import annotations

import pytest

from brain.memory import (
    CATEGORIES,
    end_session,
    get_recent_memories,
    list_sessions,
    log_decision,
    mark_nudge_acted,
    nudge_check,
    pending_nudges,
    recent_decisions,
    search_decisions,
    search_memories,
    start_session,
    store_memory,
    update_decision_outcome,
)


# ---------------------------------------------------------------------------
# store_memory
# ---------------------------------------------------------------------------


def test_store_memory_returns_complete_row():
    """store_memory() must return a dict with all expected keys."""
    mem = store_memory("nicholas", "Customer prefers Slack over email for updates", "preference")
    assert mem["id"] is not None
    assert mem["team_member"] == "nicholas"
    assert mem["content"] == "Customer prefers Slack over email for updates"
    assert mem["category"] == "preference"
    assert mem["created_at"] is not None
    assert mem["updated_at"] is not None


def test_store_memory_all_valid_categories():
    """store_memory() must accept every category in CATEGORIES without raising."""
    for cat in CATEGORIES:
        mem = store_memory("ceo", f"Test memory for category {cat}", cat)
        assert mem["category"] == cat


def test_store_memory_invalid_category_raises():
    """store_memory() must raise ValueError for an invalid category."""
    with pytest.raises(ValueError, match="Invalid category"):
        store_memory("nicholas", "This has a bad category", "nonsense_category")


def test_store_memory_invalid_team_member_raises():
    """store_memory() must raise ValueError for an unknown team member."""
    with pytest.raises(ValueError, match="Unknown team member"):
        store_memory("ghost", "Some content", "learning")


def test_store_memory_assigns_unique_ids():
    """Each stored memory must receive a unique auto-incremented id."""
    m1 = store_memory("cto", "First observation about the system", "context")
    m2 = store_memory("cto", "Second observation about performance", "metric")
    assert m1["id"] != m2["id"]


def test_store_memory_normalises_team_member_case():
    """Team member name should be normalised to lowercase canonical key."""
    mem = store_memory("Nicholas", "Case test memory content here", "learning")
    assert mem["team_member"] == "nicholas"


# ---------------------------------------------------------------------------
# search_memories (FTS5)
# ---------------------------------------------------------------------------


def test_search_memories_finds_stored_content():
    """search_memories() must retrieve a memory by keyword."""
    store_memory("nicholas", "We decided to use PostgreSQL for the production database", "decision")
    results = search_memories("PostgreSQL")
    assert len(results) >= 1
    assert any("PostgreSQL" in r["content"] for r in results)


def test_search_memories_returns_rank():
    """search_memories() results must include a _rank field."""
    store_memory("ceo", "Quarterly revenue exceeded projections by 15 percent", "metric")
    results = search_memories("revenue")
    assert len(results) >= 1
    assert "_rank" in results[0]


def test_search_memories_filtered_by_team_member():
    """Filtering by team_member must exclude other members' memories."""
    store_memory("nicholas", "Nicholas thinks product-led growth is the way forward", "learning")
    store_memory("ceo", "CEO believes enterprise sales will dominate Q3", "learning")

    nicholas_results = search_memories("growth", team_member="nicholas")
    assert all(r["team_member"] == "nicholas" for r in nicholas_results)

    ceo_results = search_memories("enterprise", team_member="ceo")
    assert all(r["team_member"] == "ceo" for r in ceo_results)


def test_search_memories_invalid_member_raises():
    """search_memories() with an invalid team member must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown team member"):
        search_memories("anything", team_member="unknown_person")


def test_search_memories_empty_when_no_match():
    """search_memories() must return [] when nothing matches."""
    store_memory("cto", "Deploying the new microservice architecture", "learning")
    results = search_memories("supercalifragilistic")
    assert results == []


def test_search_memories_limit_respected():
    """search_memories() must respect the limit parameter."""
    for i in range(8):
        store_memory("ops", f"Infrastructure event {i} caused a deployment spike", "metric")
    results = search_memories("deployment", limit=3)
    assert len(results) <= 3


# ---------------------------------------------------------------------------
# get_recent_memories
# ---------------------------------------------------------------------------


def test_get_recent_memories_returns_correct_member():
    """get_recent_memories() must only return memories for the requested member."""
    store_memory("growth", "SEO traffic increased 20% after content refresh", "metric")
    store_memory("ceo", "Investor meeting went well, term sheet expected", "context")

    growth_mems = get_recent_memories("growth")
    assert all(m["team_member"] == "growth" for m in growth_mems)


def test_get_recent_memories_reverse_chronological_order():
    """Memories must come back newest-first."""
    store_memory("nicholas", "First memory about onboarding", "learning")
    store_memory("nicholas", "Second memory about churn prevention", "learning")
    store_memory("nicholas", "Third memory about product roadmap", "learning")

    mems = get_recent_memories("nicholas", limit=10)
    # Timestamps are ISO strings — lexicographic comparison works
    timestamps = [m["created_at"] for m in mems]
    assert timestamps == sorted(timestamps, reverse=True)


def test_get_recent_memories_limit():
    """get_recent_memories() must not return more rows than the limit."""
    for i in range(10):
        store_memory("cto", f"Code review finding {i} in auth module", "learning")
    mems = get_recent_memories("cto", limit=4)
    assert len(mems) <= 4


def test_get_recent_memories_empty_for_new_member():
    """A team member with no memories should return an empty list."""
    mems = get_recent_memories("ops")
    assert mems == []


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------


def test_log_decision_stores_and_returns_row():
    """log_decision() must persist the row and return it with an id."""
    dec = log_decision(
        team_member="ceo",
        context="Q3 planning session with founders",
        decision="Prioritise enterprise over SMB for next quarter",
        reasoning="Higher ACV and lower churn in enterprise segment",
        outcome=None,
    )
    assert dec["id"] is not None
    assert dec["team_member"] == "ceo"
    assert dec["decision"] == "Prioritise enterprise over SMB for next quarter"


def test_log_decision_optional_fields_nullable():
    """log_decision() must work without reasoning or outcome."""
    dec = log_decision(
        team_member="cto",
        context="Architecture review",
        decision="Switch from monolith to services",
    )
    assert dec["reasoning"] is None
    assert dec["outcome"] is None


def test_update_decision_outcome():
    """update_decision_outcome() must persist the new outcome."""
    dec = log_decision(
        team_member="ceo",
        context="Feature rollout decision",
        decision="Enable dark mode by default",
    )
    updated = update_decision_outcome(dec["id"], "Users responded positively — NPS up 4 points")
    assert updated["outcome"] == "Users responded positively — NPS up 4 points"


def test_search_decisions_finds_by_keyword():
    """search_decisions() must find a decision by keyword in its text."""
    log_decision(
        team_member="ceo",
        context="Annual pricing review",
        decision="Increase enterprise tier price by 15 percent",
        reasoning="Market analysis shows we are underpriced versus competitors",
    )
    results = search_decisions("pricing")
    assert len(results) >= 1
    decision_texts = " ".join(r.get("decision", "") + r.get("context", "") for r in results)
    assert "pricing" in decision_texts.lower() or "price" in decision_texts.lower()


def test_recent_decisions_newest_first():
    """recent_decisions() must return decisions in reverse chronological order."""
    log_decision("ops", "infra context", "Deployed v2.0 to production")
    log_decision("ops", "infra context", "Rolled back v2.0 due to memory leak")
    log_decision("ops", "infra context", "Re-deployed v2.1 with fix applied")

    decs = recent_decisions("ops", limit=10)
    timestamps = [d["created_at"] for d in decs]
    assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def test_start_session_creates_row():
    """start_session() must return a dict with id and team_member."""
    session = start_session("nicholas", raw_log_path="/tmp/log.txt")
    assert session["id"] is not None
    assert session["team_member"] == "nicholas"
    assert session["raw_log_path"] == "/tmp/log.txt"
    assert session["ended_at"] is None


def test_end_session_sets_ended_at_and_summary():
    """end_session() must populate ended_at and summary."""
    session = start_session("cristine")
    ended = end_session(session["id"], summary="Reviewed enterprise pipeline with Cristine")
    assert ended["ended_at"] is not None
    assert ended["summary"] == "Reviewed enterprise pipeline with Cristine"


def test_end_session_without_summary_uses_placeholder():
    """end_session() without a summary must use the placeholder text."""
    session = start_session("ceo")
    ended = end_session(session["id"])
    assert "summary pending" in ended["summary"]


def test_list_sessions_returns_correct_member():
    """list_sessions() must only return sessions for the requested member."""
    start_session("growth")
    start_session("ceo")
    growth_sessions = list_sessions("growth")
    assert all(s["team_member"] == "growth" for s in growth_sessions)


# ---------------------------------------------------------------------------
# Nudges
# ---------------------------------------------------------------------------


def test_nudge_check_returns_nudge_for_member():
    """nudge_check() must create and return at least one nudge."""
    nudges = nudge_check("nicholas")
    assert len(nudges) >= 1
    assert nudges[0]["team_member"] == "nicholas"
    assert nudges[0]["acted_on"] == 0


def test_nudge_check_content_mentions_memory_count():
    """nudge_check() should mention the count of recent memories."""
    store_memory("ceo", "Revenue is growing steadily this quarter with new deals closing", "metric")
    store_memory("ceo", "Product adoption metrics are improving week over week for enterprise", "metric")
    nudges = nudge_check("ceo")
    # The nudge text should include the count
    assert any(char.isdigit() for char in nudges[0]["content"])


def test_nudge_check_invalid_member_raises():
    """nudge_check() with an unknown member must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown team member"):
        nudge_check("ghost")


def test_pending_nudges_returns_unacted():
    """pending_nudges() must return only unacted (acted_on=0) nudges."""
    nudge_check("cto")
    nudges = pending_nudges("cto")
    assert all(n["acted_on"] == 0 for n in nudges)


def test_mark_nudge_acted_flips_flag():
    """mark_nudge_acted() must set acted_on to 1."""
    created = nudge_check("ops")[0]
    updated = mark_nudge_acted(created["id"])
    assert updated["acted_on"] == 1


def test_pending_nudges_excludes_acted_nudges():
    """After marking a nudge as acted, it should not appear in pending_nudges()."""
    nudge_check("cx-lead")
    all_nudges = pending_nudges("cx-lead")
    assert len(all_nudges) >= 1

    mark_nudge_acted(all_nudges[0]["id"])
    remaining = pending_nudges("cx-lead")
    acted_ids = {all_nudges[0]["id"]}
    assert all(n["id"] not in acted_ids for n in remaining)
