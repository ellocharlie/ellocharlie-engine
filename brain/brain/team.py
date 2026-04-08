"""
brain.team
----------
Team member profiles for the ellocharlie agent-driven company.

Two human founders (Nicholas, Cristine) + five specialised agents.
Each profile describes role, type (human | agent), areas of focus,
active schedule, and — for agents — the LLM model to use.
"""

from __future__ import annotations

from typing import Any

# ── Profiles ───────────────────────────────────────────────────────────────────

TEAM: dict[str, dict[str, Any]] = {
    "nicholas": {
        "role": "Founder",
        "type": "human",
        "focus": ["strategy", "product", "customers", "onboarding"],
        "schedule": "always",
    },
    "cristine": {
        "role": "Founder",
        "type": "human",
        "focus": ["enterprise", "partnerships", "operations", "last-mile"],
        "schedule": "always",
    },
    "ceo": {
        "role": "Chief Executive Officer",
        "type": "agent",
        "focus": ["strategy", "prioritization", "metrics", "investor-updates"],
        "schedule": "weekdays-9am",
        "model": "claude-sonnet-4-5",
    },
    "cto": {
        "role": "Chief Technology Officer",
        "type": "agent",
        "focus": ["architecture", "code-quality", "security", "tech-debt"],
        "schedule": "on-demand",
        "model": "claude-sonnet-4-5",
    },
    "growth": {
        "role": "Growth Lead",
        "type": "agent",
        "focus": ["content", "seo", "social", "acquisition"],
        "schedule": "mon-wed-fri",
        "model": "claude-sonnet-4-5",
    },
    "cx-lead": {
        "role": "CX Lead",
        "type": "agent",
        "focus": ["support", "retention", "onboarding", "health-scores"],
        "schedule": "always-on",
        "model": "claude-sonnet-4-5",
    },
    "ops": {
        "role": "Operations Engineer",
        "type": "agent",
        "focus": ["deploys", "monitoring", "infrastructure", "incidents"],
        "schedule": "always-on",
        "model": "claude-sonnet-4-5",
    },
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_member(name: str) -> dict[str, Any] | None:
    """
    Return the profile for *name* (case-insensitive, normalised).
    Returns None if the member does not exist.
    """
    return TEAM.get(name.lower().strip())


def list_members() -> list[dict[str, Any]]:
    """Return all team members as a list of dicts (with 'id' key added)."""
    return [{"id": k, **v} for k, v in TEAM.items()]


def validate_member(name: str) -> str:
    """
    Normalise *name* and raise ValueError if not found.
    Returns the canonical key.
    """
    key = name.lower().strip()
    if key not in TEAM:
        valid = ", ".join(TEAM.keys())
        raise ValueError(f"Unknown team member '{name}'. Valid members: {valid}")
    return key


def agent_members() -> list[str]:
    """Return the keys of all agent-type team members."""
    return [k for k, v in TEAM.items() if v["type"] == "agent"]


def human_members() -> list[str]:
    """Return the keys of all human team members."""
    return [k for k, v in TEAM.items() if v["type"] == "human"]
