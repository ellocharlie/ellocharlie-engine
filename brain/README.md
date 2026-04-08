# ellocharlie Brain Engine

A Hermes-style (Nous Research) self-improving agent brain for the ellocharlie agent-driven company.

The brain provides persistent memory, autonomous skill creation, a closed learning loop, and a REST API consumed by the TypeScript dashboard and the `ecforge` CLI.

---

## What it does

| Capability | Description |
|---|---|
| **Persistent Memory** | FTS5 full-text search over SQLite. Every observation, decision, and insight is stored and instantly searchable. |
| **Autonomous Skill Creation** | After complex tasks, the brain evaluates whether a reusable skill should be created or an existing one improved. Skills are stored in SQLite *and* as auditable Markdown files. |
| **Periodic Nudges** | Self-prompts to review recent activity and surface knowledge worth persisting. |
| **User Models** | Profiles for all 7 team members (2 humans + 5 agents) with role, focus areas, and schedule. |
| **Cross-Session Recall** | Search past conversations, decisions, and outcomes across all sessions. |
| **REST API** | FastAPI server on port `7777` — consumed by the TypeScript dashboard and `ecforge` CLI. |

---

## Architecture

```
brain/
├── brain/                  # Python package
│   ├── __init__.py
│   ├── db.py               # SQLite + FTS5 layer (sqlite-utils)
│   ├── memory.py           # Memory, session, decision, nudge engine
│   ├── skills.py           # Autonomous skill creation engine (Hermes-style)
│   ├── team.py             # Team member profiles
│   ├── learning.py         # Closed learning loop
│   └── server.py           # FastAPI REST server (port 7777)
├── data/
│   └── brain.db            # SQLite database (auto-created)
├── skills/                 # Human-readable Markdown skill files
│   └── example-onboarding-flow.md
├── pyproject.toml
└── README.md
```

---

## Quick start

### 1. Install

```bash
cd brain
pip install -e ".[dev]"
```

### 2. Run the server

```bash
brain
# or
uvicorn brain.server:app --port 7777 --reload
```

The server starts at `http://localhost:7777`.

Interactive docs: `http://localhost:7777/docs`

### 3. Verify

```bash
curl http://localhost:7777/health
# {"status":"ok","version":"0.1.0"}
```

---

## API Reference

All endpoints return JSON. Errors follow standard HTTP status codes with a `detail` field.

### System

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |

### Team

| Method | Path | Description |
|---|---|---|
| GET | `/team` | List all team members |
| GET | `/team/{member}` | Get a single member's profile |

Valid member keys: `nicholas`, `kristine`, `ceo`, `cto`, `growth`, `cx-lead`, `ops`

### Memory

| Method | Path | Description |
|---|---|---|
| POST | `/memory` | Store a memory |
| GET | `/memory/search?q=...&member=...&limit=10` | FTS5 search |
| GET | `/memory/recent/{member}?limit=20` | Chronological recall |

**POST /memory body:**
```json
{
  "team_member": "nicholas",
  "content": "Customer Acme Corp prefers async comms over calls.",
  "category": "customer_insight"
}
```

**Valid categories:** `decision`, `preference`, `context`, `learning`, `customer_insight`, `product_feedback`, `metric`, `relationship`

### Skills

| Method | Path | Description |
|---|---|---|
| POST | `/skills` | Create a skill |
| GET | `/skills` | List all skills |
| GET | `/skills/{name}` | Get a skill |
| PUT | `/skills/{name}/improve` | Improve with feedback |
| GET | `/skills/match?context=...` | Find best matching skill |
| DELETE | `/skills/{name}` | Delete a skill |

**POST /skills body:**
```json
{
  "name": "customer-escalation",
  "description": "Handle tier-1 customer escalations",
  "trigger_pattern": "customer escalation angry churn",
  "content": "1. Acknowledge within 5 min\n2. ..."
}
```

Skills are simultaneously written to `brain/skills/{name}.md` for human review.

### Decisions

| Method | Path | Description |
|---|---|---|
| POST | `/decisions` | Log a decision |
| GET | `/decisions/search?q=...` | FTS5 search |
| GET | `/decisions/recent/{member}` | Recent decisions |

### Nudges

| Method | Path | Description |
|---|---|---|
| POST | `/nudges/check/{member}` | Trigger a nudge check |
| GET | `/nudges/pending/{member}` | Get pending nudges |
| PUT | `/nudges/{id}/act` | Mark acted on |

### Sessions

| Method | Path | Description |
|---|---|---|
| POST | `/sessions` | Start a session |
| PUT | `/sessions/{id}/end` | End a session |
| GET | `/sessions/{member}` | List sessions |
| POST | `/sessions/{id}/summarize` | Generate summary |

### Learning loop

| Method | Path | Description |
|---|---|---|
| POST | `/learning/after-task` | After-task hook |
| POST | `/learning/periodic-review/{member}` | Periodic review |

**POST /learning/after-task body:**
```json
{
  "team_member": "cto",
  "task_description": "Reviewed and merged PR for auth refactor",
  "outcome": "Decided to use JWT with refresh tokens. All tests passing.",
  "context": {"category": "decision", "reasoning": "Better security posture"}
}
```

The brain decides autonomously whether to create a skill, improve an existing one, log a decision, store a memory, or do nothing.

---

## Connecting an LLM provider

The brain currently ships with rule-based stubs for all LLM calls. To enable fully autonomous improvement, replace the `_llm_call` function in `brain/learning.py`:

```python
# brain/learning.py  — replace _llm_call

import anthropic

_client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env

def _llm_call(prompt: str, model: str = "claude-sonnet-4-5") -> str:
    message = _client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
```

Similarly, update `brain/memory.py :: summarize_session` for LLM-powered session summaries.

---

## TypeScript / ecforge integration

The brain exposes a standard HTTP API. From the TypeScript dashboard or `ecforge` CLI:

```typescript
// Store a memory
await fetch("http://localhost:7777/memory", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    team_member: "nicholas",
    content: "Onboarding call with Acme — they want Slack integration.",
    category: "customer_insight",
  }),
});

// Search all knowledge
const res = await fetch("http://localhost:7777/memory/search?q=Acme+Slack");
const results = await res.json();

// Trigger after-task learning
await fetch("http://localhost:7777/learning/after-task", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    team_member: "ceo",
    task_description: "Prepared investor update deck",
    outcome: "Decided to lead with ARR growth chart. Sent to 3 angels.",
  }),
});
```

---

## Skills: the Hermes principle

Skills are stored both in SQLite (for querying) **and** as Markdown files in `brain/skills/` (for human auditability). This dual-storage is a core Hermes principle from Nous Research: agent-generated knowledge must be inspectable, diffable, and exportable.

Every `brain/skills/*.md` file has a YAML front-matter header:

```yaml
---
name: skill-name
trigger: "natural language trigger phrase"
team_member: cx-lead
created: 2026-04-08
usage_count: 3
last_used: 2026-04-08T14:22:00Z
---
```

Skills can be seeded manually by dropping `.md` files into `brain/skills/` and calling `POST /skills` to register them in the database.

---

## Team members

| Key | Role | Type | Schedule |
|---|---|---|---|
| `nicholas` | Founder | Human | always |
| `kristine` | Founder | Human | always |
| `ceo` | Chief Executive Officer | Agent | weekdays-9am |
| `cto` | Chief Technology Officer | Agent | on-demand |
| `growth` | Growth Lead | Agent | mon-wed-fri |
| `cx-lead` | CX Lead | Agent | always-on |
| `ops` | Operations Engineer | Agent | always-on |

---

## Development

```bash
# Run tests
pytest

# Lint
ruff check brain/

# Auto-fix lint
ruff check --fix brain/
```

The SQLite database is created automatically at `brain/data/brain.db` on first run.
The `brain/data/` and `brain/skills/` directories are git-tracked via `.gitkeep` files.
Add `brain/data/brain.db` to `.gitignore` to avoid committing the live database.
