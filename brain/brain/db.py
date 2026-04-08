"""
brain.db
--------
Database layer for the brain engine.

Tables
------
memories   — persisted agent/human observations, decisions, learnings
sessions   — conversation/task sessions with summaries
skills     — reusable procedural knowledge (Hermes-style)
decisions  — logged decisions with context and reasoning
nudges     — self-generated prompts to persist knowledge

Full-text search is provided by an FTS5 virtual table that aggregates
content from memories, sessions, and decisions.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import sqlite_utils

# ── Path resolution ────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent.parent          # brain/ package root
DATA_DIR = _HERE / "data"
DB_PATH = DATA_DIR / "brain.db"


def get_db() -> sqlite_utils.Database:
    """Return a sqlite-utils Database handle (creates the file if needed)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite_utils.Database(DB_PATH)
    return db


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_db() -> sqlite_utils.Database:
    """
    Create all tables and FTS5 indexes.
    Safe to call on an already-initialised database (idempotent).
    """
    db = get_db()

    # ── memories ──────────────────────────────────────────────────────────────
    if "memories" not in db.table_names():
        db["memories"].create(
            {
                "id": int,
                "team_member": str,
                "content": str,
                "category": str,
                "created_at": str,
                "updated_at": str,
            },
            pk="id",
            not_null={"team_member", "content", "category"},
        )
        db["memories"].create_index(["team_member"])
        db["memories"].create_index(["category"])

    # ── sessions ──────────────────────────────────────────────────────────────
    if "sessions" not in db.table_names():
        db["sessions"].create(
            {
                "id": int,
                "team_member": str,
                "summary": str,
                "raw_log_path": str,
                "created_at": str,
                "ended_at": str,
            },
            pk="id",
            not_null={"team_member"},
        )
        db["sessions"].create_index(["team_member"])

    # ── skills ────────────────────────────────────────────────────────────────
    if "skills" not in db.table_names():
        db["skills"].create(
            {
                "id": int,
                "name": str,
                "description": str,
                "trigger_pattern": str,
                "skill_content": str,
                "usage_count": int,
                "last_used": str,
                "created_at": str,
                "updated_at": str,
            },
            pk="id",
            not_null={"name", "skill_content"},
        )
        db["skills"].create_index(["name"], unique=True)

    # ── decisions ─────────────────────────────────────────────────────────────
    if "decisions" not in db.table_names():
        db["decisions"].create(
            {
                "id": int,
                "team_member": str,
                "context": str,
                "decision": str,
                "reasoning": str,
                "outcome": str,
                "created_at": str,
            },
            pk="id",
            not_null={"team_member", "decision"},
        )
        db["decisions"].create_index(["team_member"])

    # ── nudges ────────────────────────────────────────────────────────────────
    if "nudges" not in db.table_names():
        db["nudges"].create(
            {
                "id": int,
                "team_member": str,
                "content": str,
                "acted_on": int,          # boolean stored as 0/1
                "created_at": str,
            },
            pk="id",
            not_null={"team_member", "content"},
        )
        db["nudges"].create_index(["team_member"])
        db["nudges"].create_index(["acted_on"])

    # ── FTS5 virtual table ────────────────────────────────────────────────────
    # We maintain a single fts_index table that mirrors content from memories,
    # sessions, and decisions.  Each row stores the source table + row id so
    # callers can fetch the full record.
    if "fts_index" not in db.table_names():
        db["fts_index"].create(
            {
                "rowid": int,
                "source_table": str,
                "source_id": int,
                "team_member": str,
                "content": str,
            },
            pk="rowid",
        )

    _ensure_fts5(db)
    return db


def _ensure_fts5(db: sqlite_utils.Database) -> None:
    """
    Create the FTS5 virtual table brain_fts if it doesn't already exist.
    This is done via raw SQL because sqlite-utils doesn't yet expose FTS5
    content-table semantics.
    """
    conn: sqlite3.Connection = db.conn
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "brain_fts" not in existing:
        conn.execute(
            """
            CREATE VIRTUAL TABLE brain_fts
            USING fts5(
                source_table,
                source_id UNINDEXED,
                team_member,
                content,
                tokenize = 'porter ascii'
            )
            """
        )
        conn.commit()


# ── FTS helpers ────────────────────────────────────────────────────────────────

def fts_index_row(
    db: sqlite_utils.Database,
    source_table: str,
    source_id: int,
    team_member: str,
    content: str,
) -> None:
    """Insert or replace a row in the FTS index."""
    db.conn.execute(
        """
        INSERT INTO brain_fts (source_table, source_id, team_member, content)
        VALUES (?, ?, ?, ?)
        """,
        (source_table, source_id, team_member, content),
    )
    db.conn.commit()


def fts_search(
    db: sqlite_utils.Database,
    query: str,
    team_member: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Full-text search across all indexed content.
    Returns a list of dicts with keys: source_table, source_id, team_member,
    content, rank.
    """
    if team_member:
        rows = db.conn.execute(
            """
            SELECT source_table, source_id, team_member, content,
                   rank
            FROM brain_fts
            WHERE brain_fts MATCH ?
              AND team_member = ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, team_member, limit),
        ).fetchall()
    else:
        rows = db.conn.execute(
            """
            SELECT source_table, source_id, team_member, content,
                   rank
            FROM brain_fts
            WHERE brain_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()

    return [
        {
            "source_table": r[0],
            "source_id": r[1],
            "team_member": r[2],
            "content": r[3],
            "rank": r[4],
        }
        for r in rows
    ]
