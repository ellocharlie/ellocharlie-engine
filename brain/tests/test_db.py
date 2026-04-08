"""
Tests for brain.db — schema creation, FTS5 virtual table, and core helpers.

The temp_db fixture in conftest.py ensures every test runs against a
freshly initialised SQLite database.
"""

from __future__ import annotations

import brain.db as db_mod
from brain.db import fts_index_row, fts_search, init_db


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_init_db_creates_all_tables():
    """init_db() must create all five regular tables."""
    db = init_db()
    tables = set(db.table_names())
    expected = {"memories", "sessions", "skills", "decisions", "nudges", "fts_index"}
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_init_db_creates_fts5_virtual_table():
    """brain_fts FTS5 virtual table must exist after init_db()."""
    db = init_db()
    conn = db.conn
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='brain_fts'"
    ).fetchone()
    assert result is not None, "brain_fts virtual table not created"


def test_init_db_is_idempotent():
    """Calling init_db() twice should not raise or duplicate anything."""
    db1 = init_db()
    db2 = init_db()
    # Both calls should return the same set of tables
    assert set(db1.table_names()) == set(db2.table_names())


def test_memories_table_columns():
    """memories table must have the correct columns."""
    db = init_db()
    col_names = {col.name for col in db["memories"].columns}
    assert col_names == {"id", "team_member", "content", "category", "created_at", "updated_at"}


def test_sessions_table_columns():
    """sessions table must have the correct columns."""
    db = init_db()
    col_names = {col.name for col in db["sessions"].columns}
    assert col_names == {"id", "team_member", "summary", "raw_log_path", "created_at", "ended_at"}


def test_skills_table_columns():
    """skills table must have the correct columns."""
    db = init_db()
    col_names = {col.name for col in db["skills"].columns}
    assert col_names == {
        "id", "name", "description", "trigger_pattern", "skill_content",
        "usage_count", "last_used", "created_at", "updated_at",
    }


def test_decisions_table_columns():
    """decisions table must have the correct columns."""
    db = init_db()
    col_names = {col.name for col in db["decisions"].columns}
    assert col_names == {
        "id", "team_member", "context", "decision", "reasoning", "outcome", "created_at",
    }


def test_nudges_table_columns():
    """nudges table must have the correct columns."""
    db = init_db()
    col_names = {col.name for col in db["nudges"].columns}
    assert col_names == {"id", "team_member", "content", "acted_on", "created_at"}


# ---------------------------------------------------------------------------
# FTS helpers
# ---------------------------------------------------------------------------


def test_fts_index_row_inserts():
    """fts_index_row() must insert a row searchable by fts_search()."""
    db = init_db()
    fts_index_row(db, "memories", 42, "nicholas", "quarterly review metrics dashboard")
    results = fts_search(db, "quarterly")
    assert len(results) == 1
    assert results[0]["source_table"] == "memories"
    assert results[0]["source_id"] == 42
    assert results[0]["team_member"] == "nicholas"


def test_fts_search_returns_correct_structure():
    """fts_search() must return dicts with the expected keys."""
    db = init_db()
    fts_index_row(db, "decisions", 7, "ceo", "chose FastAPI over Flask for the brain server")
    results = fts_search(db, "FastAPI")
    assert len(results) >= 1
    keys = set(results[0].keys())
    assert keys == {"source_table", "source_id", "team_member", "content", "rank"}


def test_fts_search_filtered_by_team_member():
    """fts_search() with team_member filter must only return that member's rows."""
    db = init_db()
    fts_index_row(db, "memories", 1, "nicholas", "customer onboarding strategy")
    fts_index_row(db, "memories", 2, "ceo", "customer acquisition funnel optimisation")

    results_nicholas = fts_search(db, "customer", team_member="nicholas")
    assert all(r["team_member"] == "nicholas" for r in results_nicholas)

    results_ceo = fts_search(db, "customer", team_member="ceo")
    assert all(r["team_member"] == "ceo" for r in results_ceo)


def test_fts_search_limit():
    """fts_search() must respect the limit parameter."""
    db = init_db()
    for i in range(10):
        fts_index_row(db, "memories", i, "nicholas", f"product insight number {i} about growth")

    results = fts_search(db, "product", limit=3)
    assert len(results) <= 3


def test_fts_search_no_results_for_unknown_term():
    """fts_search() must return an empty list when nothing matches."""
    db = init_db()
    fts_index_row(db, "memories", 1, "nicholas", "quarterly revenue review")
    results = fts_search(db, "supercalifragilistic")
    assert results == []


def test_fts_index_row_multiple_sources():
    """Rows from different source tables must coexist in the FTS index."""
    db = init_db()
    fts_index_row(db, "memories", 1, "cto", "refactoring the authentication module")
    fts_index_row(db, "decisions", 2, "cto", "decided to refactor authentication for security")
    fts_index_row(db, "sessions", 3, "cto", "session about refactoring plans")

    results = fts_search(db, "refactor", limit=10)
    sources = {r["source_table"] for r in results}
    assert "memories" in sources
    assert "decisions" in sources


# ---------------------------------------------------------------------------
# Basic CRUD via sqlite-utils
# ---------------------------------------------------------------------------


def test_memories_insert_and_get():
    """Direct sqlite-utils insert/get round-trip on memories table."""
    db = init_db()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    row_id = db["memories"].insert(
        {
            "team_member": "nicholas",
            "content": "Customers prefer weekly check-ins over monthly",
            "category": "preference",
            "created_at": now,
            "updated_at": now,
        }
    ).last_pk
    row = dict(db["memories"].get(row_id))
    assert row["team_member"] == "nicholas"
    assert row["category"] == "preference"
    assert "Customers" in row["content"]


def test_skills_name_unique_index():
    """Inserting two skills with the same name should raise an IntegrityError."""
    import pytest
    db = init_db()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    def _insert():
        db["skills"].insert(
            {
                "name": "duplicate-skill",
                "description": "test",
                "trigger_pattern": "test",
                "skill_content": "do things",
                "usage_count": 0,
                "last_used": None,
                "created_at": now,
                "updated_at": now,
            }
        )

    _insert()
    with pytest.raises(Exception):
        _insert()
