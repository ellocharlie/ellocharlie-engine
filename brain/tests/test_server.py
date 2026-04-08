"""
Tests for brain.server — FastAPI endpoints via httpx AsyncClient.

The temp_db fixture (autouse) in conftest.py ensures each test starts with a
fresh, initialised SQLite database, so endpoint tests are fully isolated.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from brain.server import app


# ---------------------------------------------------------------------------
# Client fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async HTTPX client wired directly to the FastAPI ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health_returns_200(client):
    """GET /health must return HTTP 200."""
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_health_response_body(client):
    """GET /health must return {status: 'ok', version: '0.1.0'}."""
    resp = await client.get("/health")
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


# ---------------------------------------------------------------------------
# /team
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_team_returns_200(client):
    """GET /team must return HTTP 200."""
    resp = await client.get("/team")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_get_team_returns_seven_members(client):
    """GET /team must return exactly 7 team members."""
    resp = await client.get("/team")
    data = resp.json()
    assert len(data) == 7


@pytest.mark.anyio
async def test_get_team_all_have_required_fields(client):
    """Every member in GET /team must have id, role, type, focus, schedule."""
    resp = await client.get("/team")
    for member in resp.json():
        assert "id" in member
        assert "role" in member
        assert "type" in member
        assert "focus" in member


@pytest.mark.anyio
async def test_get_team_member_valid(client):
    """GET /team/{member} must return the correct profile for a valid key."""
    resp = await client.get("/team/ceo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "ceo"
    assert data["role"] == "Chief Executive Officer"


@pytest.mark.anyio
async def test_get_team_member_not_found(client):
    """GET /team/{member} must return 404 for an unknown member."""
    resp = await client.get("/team/nobody")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /memory
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_memory_creates_record(client):
    """POST /memory must return 201 and the stored memory."""
    payload = {
        "team_member": "nicholas",
        "content": "Customers in the fintech vertical respond well to compliance-first messaging",
        "category": "customer_insight",
    }
    resp = await client.post("/memory", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["team_member"] == "nicholas"
    assert data["category"] == "customer_insight"


@pytest.mark.anyio
async def test_post_memory_invalid_category_returns_422(client):
    """POST /memory with an invalid category must return HTTP 422."""
    payload = {
        "team_member": "nicholas",
        "content": "Some content to store in the system",
        "category": "invalid_category_name",
    }
    resp = await client.post("/memory", json=payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_post_memory_invalid_member_returns_422(client):
    """POST /memory with an unknown team member must return HTTP 422."""
    payload = {
        "team_member": "ghost",
        "content": "Content by unknown person",
        "category": "learning",
    }
    resp = await client.post("/memory", json=payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_memory_search_retrieves_stored(client):
    """POST /memory then GET /memory/search must find the stored content."""
    # Store a memory with a unique keyword
    payload = {
        "team_member": "ceo",
        "content": "The xylophone metaphor is our internal word for a cascading failure",
        "category": "context",
    }
    await client.post("/memory", json=payload)

    # Search for it
    resp = await client.get("/memory/search", params={"q": "xylophone"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert any("xylophone" in r.get("content", "") for r in results)


@pytest.mark.anyio
async def test_memory_search_filtered_by_member(client):
    """GET /memory/search with member param must filter results."""
    await client.post("/memory", json={
        "team_member": "cto",
        "content": "Kumquat is our test keyword stored for cto only",
        "category": "learning",
    })
    await client.post("/memory", json={
        "team_member": "ops",
        "content": "Kumquat appears here too but for ops",
        "category": "learning",
    })

    resp = await client.get("/memory/search", params={"q": "Kumquat", "member": "cto"})
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["team_member"] == "cto" for r in results)


@pytest.mark.anyio
async def test_memory_recent_returns_list(client):
    """GET /memory/recent/{member} must return a list."""
    await client.post("/memory", json={
        "team_member": "growth",
        "content": "Organic search traffic doubled after the content refresh last month",
        "category": "metric",
    })
    resp = await client.get("/memory/recent/growth")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_memory_recent_invalid_member_returns_404(client):
    """GET /memory/recent/{member} with unknown member must return 404."""
    resp = await client.get("/memory/recent/ghost")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /skills
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_skills_creates_skill(client):
    """POST /skills must return 201 and the created skill."""
    payload = {
        "name": "api-versioning",
        "description": "How to version APIs correctly",
        "trigger_pattern": "api versioning strategy upgrade",
        "content": "Use /v1/, /v2/ prefixes. Never break backward compat without a major bump.",
    }
    resp = await client.post("/skills", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "api-versioning"
    assert data["id"] is not None


@pytest.mark.anyio
async def test_get_skills_lists_all(client):
    """GET /skills must return a list including all created skills."""
    await client.post("/skills", json={
        "name": "list-skill-a",
        "description": "skill a",
        "trigger_pattern": "trigger a",
        "content": "content a",
    })
    await client.post("/skills", json={
        "name": "list-skill-b",
        "description": "skill b",
        "trigger_pattern": "trigger b",
        "content": "content b",
    })

    resp = await client.get("/skills")
    assert resp.status_code == 200
    names = {s["name"] for s in resp.json()}
    assert "list-skill-a" in names
    assert "list-skill-b" in names


@pytest.mark.anyio
async def test_get_skill_by_name(client):
    """GET /skills/{name} must return the correct skill."""
    await client.post("/skills", json={
        "name": "onboarding-flow",
        "description": "Customer onboarding procedure",
        "trigger_pattern": "onboarding customer new user setup",
        "content": "1. Send welcome\n2. Schedule call\n3. Set up account",
    })
    resp = await client.get("/skills/onboarding-flow")
    assert resp.status_code == 200
    assert resp.json()["name"] == "onboarding-flow"


@pytest.mark.anyio
async def test_get_skill_not_found(client):
    """GET /skills/{name} for a non-existent skill must return 404."""
    resp = await client.get("/skills/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_put_skill_improve(client):
    """PUT /skills/{name}/improve must append feedback to skill content."""
    await client.post("/skills", json={
        "name": "deploy-flow",
        "description": "Deployment flow",
        "trigger_pattern": "deploy production flow checklist",
        "content": "1. Run tests\n2. Deploy",
    })
    resp = await client.put("/skills/deploy-flow/improve", json={
        "feedback": "Add rollback step after deployment"
    })
    assert resp.status_code == 200
    assert "rollback" in resp.json()["skill_content"].lower()


@pytest.mark.anyio
async def test_put_skill_improve_not_found(client):
    """PUT /skills/ghost/improve must return 404."""
    resp = await client.put("/skills/ghost-skill/improve", json={"feedback": "test"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_skill(client):
    """DELETE /skills/{name} must return {deleted: True} and remove the skill."""
    await client.post("/skills", json={
        "name": "temp-del-skill",
        "description": "Will be deleted",
        "trigger_pattern": "delete me",
        "content": "temporary",
    })
    del_resp = await client.delete("/skills/temp-del-skill")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    get_resp = await client.get("/skills/temp-del-skill")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_delete_skill_not_found(client):
    """DELETE /skills/{name} for a non-existent skill must return 404."""
    resp = await client.delete("/skills/phantom-skill")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_skills_match_endpoint(client):
    """GET /skills/match must return the best-matching skill for a context query."""
    await client.post("/skills", json={
        "name": "retro-playbook",
        "description": "Sprint retrospective playbook",
        "trigger_pattern": "sprint retro retrospective agile process",
        "content": "Gather team, reflect on sprint, create action items",
    })
    resp = await client.get("/skills/match", params={"context": "sprint retro process"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "retro-playbook"


@pytest.mark.anyio
async def test_skills_match_no_match_returns_404(client):
    """GET /skills/match when there are no skills must return 404."""
    resp = await client.get("/skills/match", params={"context": "xyzzy frob unknown"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /decisions
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_decision_creates_record(client):
    """POST /decisions must return 201 and the stored decision."""
    payload = {
        "team_member": "ceo",
        "context": "Q2 planning session",
        "decision": "Approved the enterprise expansion into EMEA",
        "reasoning": "Market research shows strong demand signal",
        "outcome": None,
    }
    resp = await client.post("/decisions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["decision"] == "Approved the enterprise expansion into EMEA"


@pytest.mark.anyio
async def test_post_decision_invalid_member_returns_422(client):
    """POST /decisions with an unknown team_member must return 422."""
    payload = {
        "team_member": "unknown_agent",
        "context": "some context",
        "decision": "some decision",
    }
    resp = await client.post("/decisions", json=payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_decisions_search_finds_stored(client):
    """POST /decisions then GET /decisions/search must find it by keyword."""
    await client.post("/decisions", json={
        "team_member": "cto",
        "context": "architecture review",
        "decision": "Migrated authentication to JWT tokens for stateless sessions",
        "reasoning": "Scalability and stateless architecture benefits",
    })
    resp = await client.get("/decisions/search", params={"q": "JWT"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1


@pytest.mark.anyio
async def test_decisions_search_filtered_by_member(client):
    """GET /decisions/search with member param must filter by team_member."""
    await client.post("/decisions", json={
        "team_member": "ceo",
        "context": "pricing review",
        "decision": "Raised enterprise plan price by 10 percent",
    })
    await client.post("/decisions", json={
        "team_member": "cto",
        "context": "tech review",
        "decision": "Chose PostgreSQL over MySQL for primary storage",
    })

    resp = await client.get("/decisions/search", params={"q": "enterprise", "member": "ceo"})
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["team_member"] == "ceo" for r in results)


@pytest.mark.anyio
async def test_decisions_recent_returns_list(client):
    """GET /decisions/recent/{member} must return a list."""
    await client.post("/decisions", json={
        "team_member": "ops",
        "context": "infra",
        "decision": "Decided to upgrade Kubernetes to 1.29",
    })
    resp = await client.get("/decisions/recent/ops")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# /sessions
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_sessions_creates_session(client):
    """POST /sessions must return 201 and a session with id."""
    resp = await client.post("/sessions", json={"team_member": "nicholas"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["team_member"] == "nicholas"


@pytest.mark.anyio
async def test_put_sessions_end(client):
    """PUT /sessions/{id}/end must close the session with a summary."""
    create_resp = await client.post("/sessions", json={"team_member": "kristine"})
    session_id = create_resp.json()["id"]

    end_resp = await client.put(
        f"/sessions/{session_id}/end",
        json={"summary": "Reviewed enterprise pipeline with Kristine"}
    )
    assert end_resp.status_code == 200
    data = end_resp.json()
    assert data["ended_at"] is not None
    assert data["summary"] == "Reviewed enterprise pipeline with Kristine"


@pytest.mark.anyio
async def test_get_sessions_for_member(client):
    """GET /sessions/{member} must return the list of sessions for that member."""
    await client.post("/sessions", json={"team_member": "ceo"})
    await client.post("/sessions", json={"team_member": "ceo"})

    resp = await client.get("/sessions/ceo")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert all(s["team_member"] == "ceo" for s in data)


# ---------------------------------------------------------------------------
# /nudges
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_nudge_check_creates_nudge(client):
    """POST /nudges/check/{member} must return 201 and a list of nudges."""
    resp = await client.post("/nudges/check/nicholas")
    assert resp.status_code == 201
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["team_member"] == "nicholas"


@pytest.mark.anyio
async def test_get_pending_nudges(client):
    """GET /nudges/pending/{member} must return unacted nudges."""
    await client.post("/nudges/check/ceo")
    resp = await client.get("/nudges/pending/ceo")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all(n["acted_on"] == 0 for n in data)


@pytest.mark.anyio
async def test_put_nudge_act(client):
    """PUT /nudges/{id}/act must mark the nudge as acted on."""
    nudges_resp = await client.post("/nudges/check/cto")
    nudge_id = nudges_resp.json()[0]["id"]

    act_resp = await client.put(f"/nudges/{nudge_id}/act")
    assert act_resp.status_code == 200
    assert act_resp.json()["acted_on"] == 1


# ---------------------------------------------------------------------------
# /learning
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_after_task_endpoint(client):
    """POST /learning/after-task must return 200 with actions dict."""
    payload = {
        "team_member": "growth",
        "task_description": "standard weekly content publishing workflow",
        "outcome": (
            "Published three blog posts. Updated SEO metadata. "
            "Scheduled social posts for the week."
        ),
        "context": None,
    }
    resp = await client.post("/learning/after-task", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "team_member" in data
    assert "rationale" in data


@pytest.mark.anyio
async def test_after_task_endpoint_invalid_member(client):
    """POST /learning/after-task with unknown member must return 422."""
    payload = {
        "team_member": "ghost",
        "task_description": "something",
        "outcome": "something else happened",
    }
    resp = await client.post("/learning/after-task", json=payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_periodic_review_endpoint(client):
    """POST /learning/periodic-review/{member} must return 200 with review dict."""
    resp = await client.post("/learning/periodic-review/ceo")
    assert resp.status_code == 200
    data = resp.json()
    assert "team_member" in data
    assert data["team_member"] == "ceo"
    assert "patterns" in data
    assert "knowledge_gaps" in data


@pytest.mark.anyio
async def test_periodic_review_endpoint_invalid_member(client):
    """POST /learning/periodic-review/{member} with unknown member must return 404."""
    resp = await client.post("/learning/periodic-review/ghost")
    assert resp.status_code == 404
