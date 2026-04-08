"""
Tests for brain.team — TEAM dict structure, member types, and helper functions.

These tests do not touch the database; they validate the static configuration
and the behaviour of the pure-Python helper functions.
"""

from __future__ import annotations

import pytest

from brain.team import (
    TEAM,
    agent_members,
    get_member,
    human_members,
    list_members,
    validate_member,
)

# ---------------------------------------------------------------------------
# TEAM dict — structure and completeness
# ---------------------------------------------------------------------------

EXPECTED_MEMBERS = {"nicholas", "kristine", "ceo", "cto", "growth", "cx-lead", "ops"}
EXPECTED_HUMANS = {"nicholas", "kristine"}
EXPECTED_AGENTS = {"ceo", "cto", "growth", "cx-lead", "ops"}


def test_team_has_exactly_seven_members():
    """TEAM must define exactly 7 members."""
    assert len(TEAM) == 7


def test_team_has_all_expected_keys():
    """TEAM must contain every expected member key."""
    assert set(TEAM.keys()) == EXPECTED_MEMBERS


def test_every_member_has_required_fields():
    """Every member profile must have 'role', 'type', 'focus', and 'schedule'."""
    for member_id, profile in TEAM.items():
        assert "role" in profile, f"'{member_id}' missing 'role'"
        assert "type" in profile, f"'{member_id}' missing 'type'"
        assert "focus" in profile, f"'{member_id}' missing 'focus'"
        assert "schedule" in profile, f"'{member_id}' missing 'schedule'"


def test_member_types_are_human_or_agent():
    """Every member's 'type' must be either 'human' or 'agent'."""
    for member_id, profile in TEAM.items():
        assert profile["type"] in {"human", "agent"}, (
            f"'{member_id}' has invalid type: {profile['type']!r}"
        )


def test_human_members_are_nicholas_and_kristine():
    """nicholas and kristine must be the only human-type members."""
    humans = {k for k, v in TEAM.items() if v["type"] == "human"}
    assert humans == EXPECTED_HUMANS


def test_agent_members_are_five():
    """There must be exactly five agent-type members."""
    agents = {k for k, v in TEAM.items() if v["type"] == "agent"}
    assert len(agents) == 5
    assert agents == EXPECTED_AGENTS


def test_agents_have_model_field():
    """Every agent-type member must declare a 'model' field."""
    for member_id, profile in TEAM.items():
        if profile["type"] == "agent":
            assert "model" in profile, f"Agent '{member_id}' is missing 'model'"


def test_humans_do_not_have_model_field():
    """Human members must not have a 'model' field (they're not LLM agents)."""
    for member_id, profile in TEAM.items():
        if profile["type"] == "human":
            assert "model" not in profile, f"Human '{member_id}' should not have 'model'"


def test_focus_is_a_non_empty_list():
    """Every member's 'focus' must be a non-empty list."""
    for member_id, profile in TEAM.items():
        assert isinstance(profile["focus"], list), f"'{member_id}' focus is not a list"
        assert len(profile["focus"]) > 0, f"'{member_id}' focus list is empty"


def test_roles_are_non_empty_strings():
    """Every role must be a non-empty string."""
    for member_id, profile in TEAM.items():
        assert isinstance(profile["role"], str), f"'{member_id}' role is not a string"
        assert profile["role"].strip(), f"'{member_id}' role is an empty string"


# ---------------------------------------------------------------------------
# get_member
# ---------------------------------------------------------------------------


def test_get_member_returns_profile():
    """get_member() must return the correct profile for a valid key."""
    profile = get_member("ceo")
    assert profile is not None
    assert profile["role"] == "Chief Executive Officer"
    assert profile["type"] == "agent"


def test_get_member_case_insensitive():
    """get_member() must handle mixed-case names gracefully."""
    assert get_member("Nicholas") == get_member("nicholas")
    assert get_member("CTO") == get_member("cto")
    assert get_member("CX-LEAD") == get_member("cx-lead")


def test_get_member_strips_whitespace():
    """get_member() must strip surrounding whitespace from the name."""
    assert get_member("  ops  ") == get_member("ops")


def test_get_member_returns_none_for_unknown():
    """get_member() must return None for an unknown member key."""
    assert get_member("ghost") is None
    assert get_member("") is None
    assert get_member("marketing") is None


# ---------------------------------------------------------------------------
# list_members
# ---------------------------------------------------------------------------


def test_list_members_returns_all_seven():
    """list_members() must return exactly 7 dicts."""
    members = list_members()
    assert len(members) == 7


def test_list_members_each_has_id_key():
    """Every dict from list_members() must include an 'id' key."""
    for m in list_members():
        assert "id" in m


def test_list_members_ids_match_team_keys():
    """The 'id' values in list_members() must match the keys in TEAM."""
    ids = {m["id"] for m in list_members()}
    assert ids == EXPECTED_MEMBERS


def test_list_members_includes_profile_fields():
    """Each dict from list_members() must include 'role', 'type', 'focus'."""
    for m in list_members():
        assert "role" in m
        assert "type" in m
        assert "focus" in m


# ---------------------------------------------------------------------------
# validate_member
# ---------------------------------------------------------------------------


def test_validate_member_returns_canonical_key():
    """validate_member() must return the normalised lowercase key."""
    assert validate_member("nicholas") == "nicholas"
    assert validate_member("CTO") == "cto"
    assert validate_member("  ops  ") == "ops"
    assert validate_member("CX-LEAD") == "cx-lead"


def test_validate_member_raises_for_unknown():
    """validate_member() must raise ValueError for an unknown name."""
    with pytest.raises(ValueError, match="Unknown team member"):
        validate_member("ghost")


def test_validate_member_error_includes_valid_list():
    """The ValueError message must list all valid member keys."""
    with pytest.raises(ValueError) as exc_info:
        validate_member("nobody")
    error_msg = str(exc_info.value)
    for key in TEAM.keys():
        assert key in error_msg, f"Expected '{key}' in error message"


# ---------------------------------------------------------------------------
# agent_members / human_members
# ---------------------------------------------------------------------------


def test_agent_members_returns_five_keys():
    """agent_members() must return exactly 5 keys."""
    agents = agent_members()
    assert len(agents) == 5
    assert set(agents) == EXPECTED_AGENTS


def test_human_members_returns_two_keys():
    """human_members() must return exactly 2 keys."""
    humans = human_members()
    assert len(humans) == 2
    assert set(humans) == EXPECTED_HUMANS


def test_agent_members_are_all_agents():
    """Every key from agent_members() must have type='agent' in TEAM."""
    for key in agent_members():
        assert TEAM[key]["type"] == "agent"


def test_human_members_are_all_humans():
    """Every key from human_members() must have type='human' in TEAM."""
    for key in human_members():
        assert TEAM[key]["type"] == "human"


def test_agents_and_humans_are_disjoint():
    """agent_members() and human_members() must not overlap."""
    agents = set(agent_members())
    humans = set(human_members())
    assert agents.isdisjoint(humans)


def test_agents_and_humans_cover_all_members():
    """agent_members() ∪ human_members() must equal all TEAM keys."""
    all_members = set(agent_members()) | set(human_members())
    assert all_members == EXPECTED_MEMBERS


# ---------------------------------------------------------------------------
# Specific member properties
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("member_id,expected_role", [
    ("nicholas", "Founder"),
    ("kristine", "Founder"),
    ("ceo", "Chief Executive Officer"),
    ("cto", "Chief Technology Officer"),
    ("growth", "Growth Lead"),
    ("cx-lead", "CX Lead"),
    ("ops", "Operations Engineer"),
])
def test_member_roles(member_id, expected_role):
    """Each member must have the correct role string."""
    assert TEAM[member_id]["role"] == expected_role


@pytest.mark.parametrize("member_id,expected_type", [
    ("nicholas", "human"),
    ("kristine", "human"),
    ("ceo", "agent"),
    ("cto", "agent"),
    ("growth", "agent"),
    ("cx-lead", "agent"),
    ("ops", "agent"),
])
def test_member_types(member_id, expected_type):
    """Each member must have the correct type."""
    assert TEAM[member_id]["type"] == expected_type
