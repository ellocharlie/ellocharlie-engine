"""
brain.learning
--------------
Closed learning loop for the ellocharlie brain.

The loop has two entry points:

after_task_hook
    Called whenever a task completes.  Decides intelligently whether to:
    1. Create a new skill from the task
    2. Improve an existing skill
    3. Store a memory
    4. Log a decision
    5. Do nothing (not everything is worth persisting)

periodic_review
    Scheduled review (e.g. daily) that:
    1. Scans recent memories for patterns
    2. Identifies knowledge gaps
    3. Suggests skills to create
    4. Generates a "state of mind" summary

Both functions are currently rule-based stubs with clear LLM call hooks.
Swap ``_llm_call`` for a real provider (Anthropic, OpenAI, etc.) to
enable fully autonomous improvement.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .db import init_db
from .memory import (
    get_recent_memories,
    log_decision,
    nudge_check,
    recent_decisions,
    store_memory,
)
from .skills import create_skill, get_skill, improve_skill, increment_usage, list_skills, match_skill
from .team import validate_member


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── LLM call placeholder ───────────────────────────────────────────────────────

def _llm_call(prompt: str, model: str = "claude-sonnet-4-5") -> str:
    """
    Placeholder for an LLM call.

    Replace this function with a real implementation:

        import anthropic
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    The function signature must remain (prompt: str) -> str.
    """
    return (
        "[LLM call pending] "
        "Connect an LLM provider (Anthropic / OpenAI) to get real output.\n"
        f"Prompt was: {prompt[:200]}..."
    )


# ── Heuristics ─────────────────────────────────────────────────────────────────

_SKILL_TRIGGER_WORDS = [
    "always",
    "every time",
    "standard",
    "checklist",
    "flow",
    "process",
    "procedure",
    "template",
    "workflow",
    "pattern",
    "protocol",
    "playbook",
]

_DECISION_TRIGGER_WORDS = [
    "decided",
    "chose",
    "selected",
    "agreed",
    "rejected",
    "approved",
    "denied",
]

_MEMORY_MIN_LENGTH = 50   # characters


def _should_create_skill(task_description: str, outcome: str) -> bool:
    """Return True if the task looks like it produced a repeatable procedure."""
    text = (task_description + " " + outcome).lower()
    return any(word in text for word in _SKILL_TRIGGER_WORDS)


def _should_log_decision(task_description: str, outcome: str) -> bool:
    """Return True if the task description mentions a decision."""
    text = (task_description + " " + outcome).lower()
    return any(word in text for word in _DECISION_TRIGGER_WORDS)


def _should_store_memory(outcome: str) -> bool:
    """Return True if the outcome is substantial enough to persist."""
    return len(outcome.strip()) >= _MEMORY_MIN_LENGTH


# ── Public API ─────────────────────────────────────────────────────────────────

def after_task_hook(
    team_member: str,
    task_description: str,
    outcome: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Called after any task completes.

    Parameters
    ----------
    team_member : str
        Who performed the task.
    task_description : str
        A brief description of what the task was.
    outcome : str
        What happened / what was produced.
    context : dict | None
        Additional key-value pairs (e.g. customer_id, task_id, duration_s).

    Returns
    -------
    dict
        Summary of what actions were taken (persisted memory ids, skill names,
        decision ids, nudge ids).
    """
    member = validate_member(team_member)
    ctx = context or {}
    actions: dict[str, Any] = {
        "team_member": member,
        "task_description": task_description,
        "skill_created": None,
        "skill_improved": None,
        "memory_stored": None,
        "decision_logged": None,
        "nudge_issued": None,
        "rationale": [],
    }

    # ── 1. Should we create or improve a skill? ────────────────────────────
    if _should_create_skill(task_description, outcome):
        existing = match_skill(task_description)
        if existing:
            # Improve the existing skill with what we just learned
            improved = improve_skill(
                existing["name"],
                f"Updated from task on {_now()[:10]}: {outcome[:300]}",
            )
            increment_usage(existing["name"])
            actions["skill_improved"] = existing["name"]
            actions["rationale"].append(
                f"Improved existing skill '{existing['name']}' based on task outcome."
            )
        else:
            # Create a brand new skill
            skill_name = re.sub(r"[^a-z0-9]+", "-", task_description.lower().strip()[:50]).strip("-")
            new_skill = create_skill(
                name=skill_name,
                description=task_description[:200],
                trigger_pattern=task_description[:100],
                content=outcome,
            )
            actions["skill_created"] = skill_name
            actions["rationale"].append(
                f"Created new skill '{skill_name}' — task matches a repeatable procedure."
            )

    # ── 2. Should we log a decision? ──────────────────────────────────────
    if _should_log_decision(task_description, outcome):
        decision = log_decision(
            team_member=member,
            context=task_description,
            decision=outcome[:500],
            reasoning=ctx.get("reasoning"),
            outcome=ctx.get("outcome_detail"),
        )
        actions["decision_logged"] = decision["id"]
        actions["rationale"].append("Logged decision: task contained a decision-related keyword.")

    # ── 3. Should we store a memory? ──────────────────────────────────────
    if _should_store_memory(outcome):
        category = ctx.get("category", "learning")
        mem = store_memory(
            team_member=member,
            content=f"{task_description}\n\nOutcome: {outcome}"[:2000],
            category=category,
        )
        actions["memory_stored"] = mem["id"]
        actions["rationale"].append("Stored memory: outcome is substantial.")

    # ── 4. Nothing worth persisting ───────────────────────────────────────
    if not any(
        [
            actions["skill_created"],
            actions["skill_improved"],
            actions["decision_logged"],
            actions["memory_stored"],
        ]
    ):
        actions["rationale"].append(
            "Nothing persisted — task was too short or not repeatable."
        )

    return actions


def periodic_review(team_member: str) -> dict[str, Any]:
    """
    Scheduled review that scans recent activity and generates improvement
    suggestions.

    Returns
    -------
    dict
        Containing:
        - ``patterns`` — repeated themes spotted in memories
        - ``gaps`` — knowledge areas with few memories
        - ``skill_suggestions`` — new skills worth creating
        - ``state_of_mind`` — brief narrative summary (LLM placeholder)
        - ``nudges_issued`` — nudge row ids created
    """
    member = validate_member(team_member)

    memories = get_recent_memories(member, limit=50)
    decisions = recent_decisions(member, limit=20)
    all_skills = list_skills()

    # ── Pattern detection (simple frequency analysis) ─────────────────────
    word_freq: dict[str, int] = {}
    for m in memories:
        words = re.findall(r"\b[a-z]{4,}\b", m["content"].lower())
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1

    top_patterns = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    # ── Knowledge gap detection ────────────────────────────────────────────
    from .memory import CATEGORIES

    covered_categories: set[str] = {m["category"] for m in memories}
    gaps = sorted(CATEGORIES - covered_categories)

    # ── Skill suggestions ──────────────────────────────────────────────────
    existing_skill_names = {s["name"] for s in all_skills}
    suggestions: list[str] = []

    # Heuristic: if a topic appears 3+ times in memories but no skill exists
    for pattern_word, freq in top_patterns:
        if freq >= 3:
            candidate_name = f"{member}-{pattern_word}"
            if candidate_name not in existing_skill_names:
                suggestions.append(
                    f"Consider creating skill '{candidate_name}' — "
                    f"the topic '{pattern_word}' appears {freq} times in recent memories."
                )

    # ── State of mind (LLM placeholder) ───────────────────────────────────
    prompt = (
        f"You are the brain of team member '{member}'. "
        f"Summarise their current state of mind based on {len(memories)} recent memories "
        f"and {len(decisions)} recent decisions. "
        f"Top recurring themes: {[p[0] for p in top_patterns[:5]]}. "
        f"Knowledge gaps: {gaps}. "
        "Be concise (2-3 sentences)."
    )
    state_of_mind = _llm_call(prompt)

    # ── Issue a nudge if patterns are strong ──────────────────────────────
    nudges_issued: list[int] = []
    if top_patterns:
        nudges = nudge_check(member)
        nudges_issued = [n["id"] for n in nudges]

    return {
        "team_member": member,
        "reviewed_memories": len(memories),
        "reviewed_decisions": len(decisions),
        "patterns": [{"word": w, "frequency": f} for w, f in top_patterns],
        "knowledge_gaps": gaps,
        "skill_suggestions": suggestions,
        "state_of_mind": state_of_mind,
        "nudges_issued": nudges_issued,
        "reviewed_at": _now(),
    }
