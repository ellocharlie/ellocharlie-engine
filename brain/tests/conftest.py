"""
Shared pytest fixtures for the brain test suite.

Each test gets a fresh SQLite database in a temp directory. We monkeypatch
the DB_PATH attributes on every module that caches it at import time, then
call init_db() to create the schema in that temp path.

We also redirect the skills SKILLS_DIR so markdown files don't pollute the
real skills/ directory during tests.
"""

from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    """Use a temporary database and skills directory for every test."""
    db_path = tmp_path / "test_brain.db"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Patch DB_PATH on every module that references it as a module-level name.
    # sqlite_utils.Database and our code read DB_PATH at call time, so
    # pointing these attributes is sufficient.
    import brain.db as db_mod
    import brain.memory as memory_mod
    import brain.skills as skills_mod
    import brain.learning as learning_mod

    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setattr(memory_mod, "DB_PATH", db_path, raising=False)
    monkeypatch.setattr(skills_mod, "DB_PATH", db_path, raising=False)
    monkeypatch.setattr(learning_mod, "DB_PATH", db_path, raising=False)

    # Patch the data directory so get_db() doesn't try to create brain/data/
    monkeypatch.setattr(db_mod, "DATA_DIR", tmp_path)

    # Patch the skills markdown directory
    monkeypatch.setattr(skills_mod, "SKILLS_DIR", skills_dir)

    # Now initialise the schema in the temp database
    db_mod.init_db()

    yield db_path
