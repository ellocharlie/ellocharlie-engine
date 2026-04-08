"""
brain.memory
------------
Memory engine for the ellocharlie brain.

Responsibilities
----------------
- Persist agent/human observations as structured memories
- FTS5-powered search across all stored knowledge
- Chronological recall per team member
- Session summarisation (LLM call placeholder)
- Periodic nudge generation to surface knowledge worth persisting
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

import sqlite_utils

from .db import fts_index_row, fts_search, init_db
from .team import validate_member

# ── Valid memory categories ────────────────────────────────────────────────────
CATEGORIES = frozenset(
    {
        "decision",
        "preference",
        "context",
        "learning",
        "customer_insight",
        "product_feedback",
        "metric",
        "relationship",
    }
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db() -> sqlite_utils.Database:
    return init_db()


# ── Core memory operations ─────────────────────────────────────────────────────

def store_memory(
    team_member: str,
    content: str,
    category: str,
) -> dict[str, Any]:
    """
    Persist a memory for *team_member*.

    Parameters
    ----------
    team_member : str
        Canonical team-member key (validated).
    content : str
        The knowledge to persist.
    category : str
        One of CATEGORIES.

    Returns
    -------
    dict
        The full inserted row including its generated ``id``.
    """
    member = validate_member(team_member)

    if category not in CATEGORIES:
        valid = ", ".join(sorted(CATEGORIES))
        raise ValueError(f"Invalid category '{category}'. Valid: {valid}")

    now = _now()
    db = _db()

    row_id = db["memories"].insert(
        {
            "team_member": member,
            "content": content,
            "category": category,
            "created_at": now,
            "updated_at": now,
        }
    ).last_pk

    # Index in FTS
    fts_index_row(db, "memories", row_id, member, content)

    return dict(db["memories"].get(row_id))


def search_memories(
    query: str,
    team_member: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Full-text search across all memories (and other indexed content).

    Parameters
    ----------
    query : str
        FTS5 match expression (plain keywords work fine).
    team_member : str | None
        Optional filter to a single member.
    limit : int
        Maximum number of results.

    Returns
    -------
    list[dict]
        Matched rows with source metadata and BM25 rank.
    """
    if team_member:
        team_member = validate_member(team_member)

    db = _db()
    hits = fts_search(db, query, team_member=team_member, limit=limit)

    # Enrich with full row data from the source table
    enriched: list[dict[str, Any]] = []
    for hit in hits:
        if hit["source_table"] == "memories":
            try:
                full_row = dict(db["memories"].get(hit["source_id"]))
                full_row["_rank"] = hit["rank"]
                full_row["_source"] = "memories"
                enriched.append(full_row)
            except Exception:
                pass
        elif hit["source_table"] == "sessions":
            try:
                full_row = dict(db["sessions"].get(hit["source_id"]))
                full_row["_rank"] = hit["rank"]
                full_row["_source"] = "sessions"
                enriched.append(full_row)
            except Exception:
                pass
        elif hit["source_table"] == "decisions":
            try:
                full_row = dict(db["decisions"].get(hit["source_id"]))
                full_row["_rank"] = hit["rank"]
                full_row["_source"] = "decisions"
                enriched.append(full_row)
            except Exception:
                pass

    return enriched


def get_recent_memories(
    team_member: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Return the most-recent memories for *team_member* in reverse chronological order.
    """
    member = validate_member(team_member)
    db = _db()
    rows = list(
        db["memories"].rows_where(
            "team_member = ?",
            [member],
            order_by="created_at DESC",
            limit=limit,
        )
    )
    return rows


# ── Session operations ─────────────────────────────────────────────────────────

def start_session(team_member: str, raw_log_path: str | None = None) -> dict[str, Any]:
    """Create a new session record and return it."""
    member = validate_member(team_member)
    now = _now()
    db = _db()

    row_id = db["sessions"].insert(
        {
            "team_member": member,
            "summary": None,
            "raw_log_path": raw_log_path,
            "created_at": now,
            "ended_at": None,
        }
    ).last_pk

    return dict(db["sessions"].get(row_id))


def end_session(session_id: int, summary: str | None = None) -> dict[str, Any]:
    """
    Mark a session as ended.  If *summary* is not provided, a placeholder
    is stored; call ``summarize_session`` afterward to generate a real one.
    """
    db = _db()
    now = _now()
    session = dict(db["sessions"].get(session_id))
    resolved_summary = summary or f"[session {session_id} — summary pending]"

    db["sessions"].update(
        session_id,
        {
            "ended_at": now,
            "summary": resolved_summary,
        },
    )

    # Index the summary for future FTS queries
    if summary:
        fts_index_row(
            db, "sessions", session_id, session["team_member"], summary
        )

    return dict(db["sessions"].get(session_id))


def summarize_session(session_id: int) -> str:
    """
    Generate a summary for session *session_id*.

    This is a placeholder for an LLM call.  In production this method would:
      1. Read the raw_log_path file
      2. Chunk the conversation turns
      3. Call the team member's configured LLM with a summarisation prompt
      4. Persist the result and update the FTS index

    For now it returns a deterministic stub so the rest of the system can
    integrate against a stable interface.
    """
    db = _db()
    session = dict(db["sessions"].get(session_id))
    team_member = session["team_member"]
    created_at = session["created_at"]

    summary = (
        f"[LLM summary pending] Session {session_id} for {team_member} "
        f"started at {created_at}. "
        "Connect an LLM provider to generate a real summary."
    )

    db["sessions"].update(session_id, {"summary": summary})
    fts_index_row(db, "sessions", session_id, team_member, summary)

    return summary


def list_sessions(team_member: str) -> list[dict[str, Any]]:
    """Return all sessions for *team_member* newest-first."""
    member = validate_member(team_member)
    db = _db()
    return list(
        db["sessions"].rows_where(
            "team_member = ?",
            [member],
            order_by="created_at DESC",
        )
    )


# ── Decision operations ────────────────────────────────────────────────────────

def log_decision(
    team_member: str,
    context: str,
    decision: str,
    reasoning: str | None = None,
    outcome: str | None = None,
) -> dict[str, Any]:
    """Persist a decision record and index it for search."""
    member = validate_member(team_member)
    now = _now()
    db = _db()

    row_id = db["decisions"].insert(
        {
            "team_member": member,
            "context": context,
            "decision": decision,
            "reasoning": reasoning,
            "outcome": outcome,
            "created_at": now,
        }
    ).last_pk

    fts_index_row(
        db,
        "decisions",
        row_id,
        member,
        f"{context} {decision} {reasoning or ''} {outcome or ''}".strip(),
    )

    return dict(db["decisions"].get(row_id))


def update_decision_outcome(decision_id: int, outcome: str) -> dict[str, Any]:
    """Update the outcome field on an existing decision."""
    db = _db()
    db["decisions"].update(decision_id, {"outcome": outcome})
    return dict(db["decisions"].get(decision_id))


def recent_decisions(team_member: str, limit: int = 20) -> list[dict[str, Any]]:
    """Return recent decisions for *team_member* newest-first."""
    member = validate_member(team_member)
    db = _db()
    return list(
        db["decisions"].rows_where(
            "team_member = ?",
            [member],
            order_by="created_at DESC",
            limit=limit,
        )
    )


def search_decisions(query: str, team_member: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """FTS search limited to decision rows."""
    if team_member:
        team_member = validate_member(team_member)
    db = _db()
    hits = fts_search(db, query, team_member=team_member, limit=limit * 2)
    results = []
    for hit in hits:
        if hit["source_table"] == "decisions":
            try:
                row = dict(db["decisions"].get(hit["source_id"]))
                row["_rank"] = hit["rank"]
                results.append(row)
            except Exception:
                pass
        if len(results) >= limit:
            break
    return results


# ── Nudge operations ───────────────────────────────────────────────────────────

def nudge_check(team_member: str) -> list[dict[str, Any]]:
    """
    Periodic nudge: review recent activity for *team_member* and suggest
    what knowledge is worth persisting.

    This is a placeholder for an LLM-driven analysis.  In production:
      1. Fetch last N memories and sessions
      2. Call LLM: "What important facts from the last 24 h should be remembered?"
      3. For each suggestion, insert a nudge row and return it

    Currently returns a single stub nudge so the interface is testable.
    """
    member = validate_member(team_member)
    now = _now()
    db = _db()

    recent = get_recent_memories(member, limit=5)
    count = len(recent)

    nudge_text = (
        f"[Auto-nudge] You have {count} recent memories. "
        "Consider reviewing them and creating skills for any repeated patterns. "
        "(Connect an LLM provider to get specific, context-aware suggestions.)"
    )

    row_id = db["nudges"].insert(
        {
            "team_member": member,
            "content": nudge_text,
            "acted_on": 0,
            "created_at": now,
        }
    ).last_pk

    return [dict(db["nudges"].get(row_id))]


def pending_nudges(team_member: str) -> list[dict[str, Any]]:
    """Return all unacted nudges for *team_member*."""
    member = validate_member(team_member)
    db = _db()
    return list(
        db["nudges"].rows_where(
            "team_member = ? AND acted_on = 0",
            [member],
            order_by="created_at DESC",
        )
    )


def mark_nudge_acted(nudge_id: int) -> dict[str, Any]:
    """Mark nudge *nudge_id* as acted on."""
    db = _db()
    db["nudges"].update(nudge_id, {"acted_on": 1})
    return dict(db["nudges"].get(nudge_id))
