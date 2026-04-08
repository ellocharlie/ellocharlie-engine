"""
brain.skills
------------
Autonomous skill creation engine — Hermes-style (Nous Research).

Each skill is stored in two places simultaneously:
  1. SQLite ``skills`` table  — queryable, rankable, machine-readable
  2. Markdown file in brain/skills/ — human-readable, auditable, diffable

This dual-storage is a core Hermes principle: skills must be inspectable
by humans and easily exported/imported between brain instances.

Skill lifecycle
---------------
create_skill  →  stored in DB + .md file
match_skill   →  FTS search to find the best skill for a given context
improve_skill →  append feedback, bump version comment in .md
increment_usage → track how often each skill is exercised
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sqlite_utils

from .db import init_db

# ── Skills directory ───────────────────────────────────────────────────────────
_HERE = Path(__file__).parent.parent          # brain/ package root
SKILLS_DIR = _HERE / "skills"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db() -> sqlite_utils.Database:
    return init_db()


def _slug(name: str) -> str:
    """Convert a skill name to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")


# ── Markdown template ──────────────────────────────────────────────────────────

def _skill_to_markdown(row: dict[str, Any]) -> str:
    usage = row.get("usage_count", 0)
    last_used = row.get("last_used") or "never"
    created = (row.get("created_at") or _now())[:10]

    return (
        f"---\n"
        f"name: {row['name']}\n"
        f"trigger: \"{row.get('trigger_pattern', '')}\"\n"
        f"created: {created}\n"
        f"usage_count: {usage}\n"
        f"last_used: {last_used}\n"
        f"---\n\n"
        f"# {row['name']}\n\n"
        f"{row.get('description', '')}\n\n"
        f"## Skill Content\n\n"
        f"{row['skill_content']}\n"
    )


def _write_skill_file(row: dict[str, Any]) -> Path:
    """Write (or overwrite) the Markdown file for a skill row."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = SKILLS_DIR / f"{_slug(row['name'])}.md"
    path.write_text(_skill_to_markdown(row), encoding="utf-8")
    return path


def _read_skill_file(name: str) -> str | None:
    """Read raw Markdown content for *name*. Returns None if not found."""
    path = SKILLS_DIR / f"{_slug(name)}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


# ── CRUD ───────────────────────────────────────────────────────────────────────

def create_skill(
    name: str,
    description: str,
    trigger_pattern: str,
    content: str,
) -> dict[str, Any]:
    """
    Create a new skill.

    Parameters
    ----------
    name : str
        Unique skill identifier (e.g. "onboarding-flow").
    description : str
        One-sentence description for listing / matching.
    trigger_pattern : str
        Natural-language phrase that should trigger this skill.
    content : str
        Full skill procedure (Markdown prose, numbered steps, etc.).

    Returns
    -------
    dict
        The persisted skill row.
    """
    db = _db()
    now = _now()

    # Upsert — if the skill already exists, update it
    existing = list(db["skills"].rows_where("name = ?", [name]))
    if existing:
        row_id = existing[0]["id"]
        db["skills"].update(
            row_id,
            {
                "description": description,
                "trigger_pattern": trigger_pattern,
                "skill_content": content,
                "updated_at": now,
            },
        )
    else:
        row_id = db["skills"].insert(
            {
                "name": name,
                "description": description,
                "trigger_pattern": trigger_pattern,
                "skill_content": content,
                "usage_count": 0,
                "last_used": None,
                "created_at": now,
                "updated_at": now,
            }
        ).last_pk

    row = dict(db["skills"].get(row_id))
    _write_skill_file(row)
    return row


def get_skill(name: str) -> dict[str, Any] | None:
    """
    Retrieve a skill by name.  Returns None if not found.
    The returned dict includes a ``markdown_path`` key pointing to the .md file.
    """
    db = _db()
    rows = list(db["skills"].rows_where("name = ?", [name]))
    if not rows:
        return None
    row = dict(rows[0])
    row["markdown_path"] = str(SKILLS_DIR / f"{_slug(name)}.md")
    return row


def list_skills(team_member: str | None = None) -> list[dict[str, Any]]:
    """
    List all skills.

    ``team_member`` filter is not stored on the skill itself but is provided
    for interface consistency — pass None to list all.  Future versions may
    tag skills to specific members.
    """
    db = _db()
    rows = list(db["skills"].rows_where(order_by="usage_count DESC"))
    # Attach markdown path to each row
    for r in rows:
        r["markdown_path"] = str(SKILLS_DIR / f"{_slug(r['name'])}.md")
    return rows


def improve_skill(name: str, feedback: str) -> dict[str, Any]:
    """
    Self-improve a skill based on usage feedback.

    In production this would call the team member's LLM to rewrite the
    skill_content incorporating the feedback.  Currently it appends the
    feedback as a structured comment section so the loop is auditable.
    """
    db = _db()
    rows = list(db["skills"].rows_where("name = ?", [name]))
    if not rows:
        raise ValueError(f"Skill '{name}' not found.")

    row = dict(rows[0])
    now = _now()

    improvement_note = (
        f"\n\n---\n"
        f"## Improvement Note ({now[:10]})\n\n"
        f"{feedback}\n\n"
        f"<!-- TODO: LLM-rewrite skill_content incorporating the above feedback -->\n"
    )

    new_content = row["skill_content"] + improvement_note

    db["skills"].update(
        row["id"],
        {
            "skill_content": new_content,
            "updated_at": now,
        },
    )

    updated = dict(db["skills"].get(row["id"]))
    _write_skill_file(updated)
    return updated


def match_skill(context: str) -> dict[str, Any] | None:
    """
    Find the best-matching skill for a given natural-language *context*.

    Strategy:
    1. Try a full phrase LIKE match first (fast, exact).
    2. Fall back to per-word scoring — count how many words from the context
       appear in each skill's trigger_pattern or description, then return the
       skill with the highest overlap score.

    Returns the best-matching skill row or None if nothing is found.
    """
    db = _db()

    # ── Phase 1: exact phrase match ───────────────────────────────────────
    try:
        cursor = db.conn.execute(
            """
            SELECT s.*
            FROM skills s
            WHERE s.trigger_pattern LIKE ?
               OR s.description LIKE ?
               OR s.skill_content LIKE ?
            ORDER BY s.usage_count DESC
            LIMIT 1
            """,
            (f"%{context}%", f"%{context}%", f"%{context}%"),
        )
        col_names = [d[0] for d in cursor.description]
        raw_rows = cursor.fetchall()
        if raw_rows:
            row = dict(zip(col_names, raw_rows[0]))
            row["markdown_path"] = str(SKILLS_DIR / f"{_slug(row['name'])}.md")
            return row
    except Exception:
        pass

    # ── Phase 2: per-word scoring ─────────────────────────────────────────
    # Split context into lowercase words of length ≥ 3
    words = [w.lower() for w in re.split(r"[^a-z0-9]+", context.lower()) if len(w) >= 3]
    if not words:
        return None

    try:
        all_skills_cursor = db.conn.execute(
            "SELECT s.* FROM skills s ORDER BY usage_count DESC"
        )
        all_col_names = [d[0] for d in all_skills_cursor.description]
        all_rows = all_skills_cursor.fetchall()

        best_row = None
        best_score = 0

        for raw in all_rows:
            row = dict(zip(all_col_names, raw))
            haystack = (
                (row.get("trigger_pattern") or "") + " " +
                (row.get("description") or "") + " " +
                (row.get("skill_content") or "")
            ).lower()
            score = sum(1 for w in words if w in haystack)
            if score > best_score:
                best_score = score
                best_row = row

        if best_row and best_score > 0:
            best_row["markdown_path"] = str(SKILLS_DIR / f"{_slug(best_row['name'])}.md")
            return best_row
    except Exception:
        pass

    return None


def increment_usage(name: str) -> dict[str, Any]:
    """Record that skill *name* was used and update its last_used timestamp."""
    db = _db()
    rows = list(db["skills"].rows_where("name = ?", [name]))
    if not rows:
        raise ValueError(f"Skill '{name}' not found.")

    row = dict(rows[0])
    now = _now()

    db["skills"].update(
        row["id"],
        {
            "usage_count": (row["usage_count"] or 0) + 1,
            "last_used": now,
            "updated_at": now,
        },
    )

    updated = dict(db["skills"].get(row["id"]))
    _write_skill_file(updated)
    return updated


def delete_skill(name: str) -> bool:
    """
    Remove a skill from the database and delete its .md file.
    Returns True if the skill existed, False otherwise.
    """
    db = _db()
    rows = list(db["skills"].rows_where("name = ?", [name]))
    if not rows:
        return False

    db["skills"].delete(rows[0]["id"])

    md_path = SKILLS_DIR / f"{_slug(name)}.md"
    if md_path.exists():
        md_path.unlink()

    return True
