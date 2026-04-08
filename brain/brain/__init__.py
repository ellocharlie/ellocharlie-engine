"""
ellocharlie-brain
-----------------
Self-improving brain engine for the ellocharlie agent-driven company.

A Hermes-style (Nous Research) autonomous agent brain with:
  - Persistent memory (FTS5 full-text search over SQLite)
  - Autonomous skill creation (skills stored as SQLite rows + Markdown files)
  - Closed learning loop (after-task hooks, periodic review)
  - Team-member profiles (human + agent)
  - REST API (FastAPI on port 7777)
"""

__version__ = "0.1.0"
