"""
brain.server
------------
FastAPI REST server exposing the ellocharlie brain engine.

Run with:
    uvicorn brain.server:app --port 7777 --reload

Or via the installed script:
    brain

Port: 7777
"""

from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .db import init_db
from .learning import after_task_hook, periodic_review
from .memory import (
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
    summarize_session,
)
from .skills import (
    create_skill,
    delete_skill,
    get_skill,
    improve_skill,
    list_skills,
    match_skill,
)
from .team import get_member, list_members

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ellocharlie Brain Engine",
    description=(
        "Hermes-style self-improving agent brain with persistent memory, "
        "autonomous skill creation, and a closed learning loop."
    ),
    version="0.1.0",
)


@app.on_event("startup")
async def startup() -> None:
    """Ensure the database and schema exist at startup."""
    init_db()


# ── Pydantic models ────────────────────────────────────────────────────────────


class MemoryIn(BaseModel):
    team_member: str
    content: str
    category: str


class SkillIn(BaseModel):
    name: str
    description: str
    trigger_pattern: str
    content: str


class SkillImproveFeedback(BaseModel):
    feedback: str


class DecisionIn(BaseModel):
    team_member: str
    context: str
    decision: str
    reasoning: str | None = None
    outcome: str | None = None


class SessionStartIn(BaseModel):
    team_member: str
    raw_log_path: str | None = None


class SessionEndIn(BaseModel):
    summary: str | None = None


class AfterTaskIn(BaseModel):
    team_member: str
    task_description: str
    outcome: str
    context: dict[str, Any] | None = None


# ── Health ─────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok", "version": "0.1.0"}


# ── Team ───────────────────────────────────────────────────────────────────────


@app.get("/team", tags=["Team"])
async def get_team() -> list[dict[str, Any]]:
    """List all team members (humans + agents)."""
    return list_members()


@app.get("/team/{member}", tags=["Team"])
async def get_team_member(member: str) -> dict[str, Any]:
    """Get a single team member's profile."""
    profile = get_member(member)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Team member '{member}' not found.")
    return {"id": member, **profile}


# ── Memory ─────────────────────────────────────────────────────────────────────


@app.post("/memory", tags=["Memory"], status_code=201)
async def create_memory(body: MemoryIn) -> dict[str, Any]:
    """Store a new memory."""
    try:
        return store_memory(body.team_member, body.content, body.category)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/memory/search", tags=["Memory"])
async def memory_search(
    q: str = Query(..., description="FTS5 search query"),
    member: str | None = Query(None, description="Filter by team member"),
    limit: int = Query(10, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Full-text search across all persisted knowledge."""
    try:
        return search_memories(q, team_member=member, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/memory/recent/{member}", tags=["Memory"])
async def memory_recent(
    member: str,
    limit: int = Query(20, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Return the most recent memories for a team member."""
    try:
        return get_recent_memories(member, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Skills ─────────────────────────────────────────────────────────────────────


@app.post("/skills", tags=["Skills"], status_code=201)
async def create_skill_endpoint(body: SkillIn) -> dict[str, Any]:
    """Create (or update) a skill."""
    return create_skill(body.name, body.description, body.trigger_pattern, body.content)


@app.get("/skills", tags=["Skills"])
async def list_skills_endpoint(
    member: str | None = Query(None, description="Filter by team member (future use)")
) -> list[dict[str, Any]]:
    """List all skills ordered by usage frequency."""
    return list_skills(team_member=member)


@app.get("/skills/match", tags=["Skills"])
async def match_skill_endpoint(
    context: str = Query(..., description="Natural-language context to match against")
) -> dict[str, Any]:
    """Find the best matching skill for a given context."""
    skill = match_skill(context)
    if not skill:
        raise HTTPException(status_code=404, detail="No matching skill found.")
    return skill


@app.get("/skills/{name}", tags=["Skills"])
async def get_skill_endpoint(name: str) -> dict[str, Any]:
    """Retrieve a skill by name."""
    skill = get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found.")
    return skill


@app.put("/skills/{name}/improve", tags=["Skills"])
async def improve_skill_endpoint(
    name: str, body: SkillImproveFeedback
) -> dict[str, Any]:
    """Improve a skill with usage feedback."""
    try:
        return improve_skill(name, body.feedback)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/skills/{name}", tags=["Skills"])
async def delete_skill_endpoint(name: str) -> dict[str, bool]:
    """Delete a skill and its Markdown file."""
    deleted = delete_skill(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found.")
    return {"deleted": True}


# ── Decisions ──────────────────────────────────────────────────────────────────


@app.post("/decisions", tags=["Decisions"], status_code=201)
async def create_decision(body: DecisionIn) -> dict[str, Any]:
    """Log a decision with context and reasoning."""
    try:
        return log_decision(
            body.team_member,
            body.context,
            body.decision,
            body.reasoning,
            body.outcome,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/decisions/search", tags=["Decisions"])
async def decisions_search(
    q: str = Query(..., description="FTS5 query"),
    member: str | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Search decisions by full-text query."""
    try:
        return search_decisions(q, team_member=member, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/decisions/recent/{member}", tags=["Decisions"])
async def decisions_recent(
    member: str,
    limit: int = Query(20, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Return recent decisions for a team member."""
    try:
        return recent_decisions(member, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Nudges ─────────────────────────────────────────────────────────────────────


@app.post("/nudges/check/{member}", tags=["Nudges"], status_code=201)
async def trigger_nudge_check(member: str) -> list[dict[str, Any]]:
    """Trigger a nudge check for a team member."""
    try:
        return nudge_check(member)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/nudges/pending/{member}", tags=["Nudges"])
async def get_pending_nudges(member: str) -> list[dict[str, Any]]:
    """Get all unacted nudges for a team member."""
    try:
        return pending_nudges(member)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/nudges/{nudge_id}/act", tags=["Nudges"])
async def act_on_nudge(nudge_id: int) -> dict[str, Any]:
    """Mark a nudge as acted on."""
    try:
        return mark_nudge_acted(nudge_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Sessions ───────────────────────────────────────────────────────────────────


@app.post("/sessions", tags=["Sessions"], status_code=201)
async def create_session(body: SessionStartIn) -> dict[str, Any]:
    """Start a new session."""
    try:
        return start_session(body.team_member, body.raw_log_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.put("/sessions/{session_id}/end", tags=["Sessions"])
async def end_session_endpoint(
    session_id: int, body: SessionEndIn
) -> dict[str, Any]:
    """End a session with an optional summary."""
    try:
        return end_session(session_id, body.summary)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/sessions/{member}", tags=["Sessions"])
async def get_sessions(member: str) -> list[dict[str, Any]]:
    """List all sessions for a team member."""
    try:
        return list_sessions(member)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/sessions/{session_id}/summarize", tags=["Sessions"])
async def summarize_session_endpoint(session_id: int) -> dict[str, str]:
    """Generate (or regenerate) the summary for a session."""
    try:
        summary = summarize_session(session_id)
        return {"session_id": str(session_id), "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Learning loop ──────────────────────────────────────────────────────────────


@app.post("/learning/after-task", tags=["Learning"])
async def after_task_endpoint(body: AfterTaskIn) -> dict[str, Any]:
    """
    Trigger the after-task learning hook.
    The brain decides what (if anything) to persist.
    """
    try:
        return after_task_hook(
            body.team_member,
            body.task_description,
            body.outcome,
            body.context,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/learning/periodic-review/{member}", tags=["Learning"])
async def periodic_review_endpoint(member: str) -> dict[str, Any]:
    """
    Trigger a periodic review for a team member.
    Returns patterns, gaps, skill suggestions, and state-of-mind.
    """
    try:
        return periodic_review(member)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    """Start the brain API server on port 7777."""
    uvicorn.run(
        "brain.server:app",
        host="0.0.0.0",
        port=7777,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
