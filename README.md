<div align="center">

# ellocharlie-engine

**The brain and orchestrator for the ellocharlie agent-driven company.**

[![CI](https://github.com/ellocharlie/ellocharlie-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/ellocharlie/ellocharlie-engine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Bun](https://img.shields.io/badge/Bun-1.1+-black.svg)](https://bun.sh)

</div>

---

## What is this?

`ellocharlie-engine` is the controller superrepo for the [ellocharlie](https://github.com/ellocharlie) GitHub org — a CRM built for startups, operated by a 5-person agent-driven company.

This repo contains:

- **`brain/`** — A Hermes-style Python memory and learning engine (FastAPI, SQLite/FTS5, port 7777)
- **`dashboard/`** — An HTML/JS operations dashboard showing issues, agents, metrics, and standup summaries
- **`agents/`** — YAML configs for all 5 AI agents (CEO, CTO, Growth, CX Lead, Ops)
- **`workflows/`** — TypeScript orchestration scripts (daily standup, weekly review, content pipeline)
- **`index/`** — Org index builder and GitHub Gist sync
- **`workspace.yaml`** — The single source of truth for the entire org

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ellocharlie-engine                              │
│                   (superrepo — the controller)                       │
│                                                                      │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────────────┐│
│  │    brain/    │  │   dashboard/    │  │       agents/           ││
│  │  Python 3.11 │  │   HTML/JS       │  │  ceo.yml  cto.yml       ││
│  │  FastAPI     │  │   port :3333    │  │  growth.yml             ││
│  │  port :7777  │  │                 │  │  cx-lead.yml  ops.yml   ││
│  └──────┬───────┘  └────────┬────────┘  └──────────┬──────────────┘│
│         │                   │                       │               │
│  ┌──────▼───────┐  ┌────────▼────────┐  ┌──────────▼──────────────┐│
│  │  SQLite/FTS5 │  │  GitHub API     │  │     workflows/          ││
│  │  brain.db    │  │  (live data)    │  │  daily-standup.ts       ││
│  └──────────────┘  └─────────────────┘  │  weekly-review.ts       ││
│                                         │  content-pipeline.ts    ││
│                                         └─────────────────────────┘│
└──────────────────────────────┬──────────────────────────────────────┘
                               │  git submodules
           ┌───────────────────┼────────────────────┐
           │                   │                    │
    ┌──────▼──────┐    ┌───────▼──────┐    ┌────────▼─────┐
    │ modules/site│    │modules/agents│    │modules/content│
    │ellocharlie  │    │ellocharlie   │    │ellocharlie   │
    │   .com      │    │  -agents     │    │  -content    │
    └─────────────┘    └──────────────┘    └──────────────┘
```

### Agent Org Chart

```
                    ┌──────────────────┐
                    │       CEO        │
                    │  OKRs · Strategy │
                    │  Investor Updates│
                    │  Weekdays 9am UTC│
                    └────────┬─────────┘
                             │ escalation → human
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │     CTO     │   │   Growth    │   │   CX Lead   │
    │  PR triggers│   │Mon/Wed/Fri  │   │  always-on  │
    │  Arch Decis.│   │  Blog · SEO │   │  new_ticket │
    │  Sec Review │   │  Social     │   │  trigger    │
    └──────┬──────┘   └─────────────┘   └─────────────┘
           │ escalation → human
    ┌──────▼──────┐
    │     OPS     │
    │  always-on  │
    │  deploy req │
    │  alert trig.│
    └─────────────┘
```

---

## Quick Start

### Prerequisites

- [Bun](https://bun.sh) >= 1.1
- Python 3.11+
- `GITHUB_TOKEN` with `gist` and `repo` scopes
- `ANTHROPIC_API_KEY` for agent runs

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/ellocharlie/ellocharlie-engine.git
cd ellocharlie-engine
```

### 2. Install the brain

```bash
cd brain
pip install -e ".[dev]"
cd ..
```

### 3. Start the brain server

```bash
brain
# Listening on http://localhost:7777
# Interactive docs: http://localhost:7777/docs
```

### 4. Serve the dashboard

```bash
cd dashboard
python -m http.server 3333
# Open http://localhost:3333
```

### 5. Run your first standup

```bash
bun run standup
# → outputs standup/YYYY-MM-DD.md
```

---

## The Brain

The brain is a Hermes-style (Nous Research) self-improving agent memory engine written in Python.

### What it does

| Capability | Description |
|---|---|
| **Persistent Memory** | FTS5 full-text search over SQLite. Every observation, decision, and insight is stored and instantly searchable across sessions. |
| **Autonomous Skill Creation** | After complex tasks, the brain evaluates whether a reusable skill should be created or an existing one improved. Skills live in SQLite and as auditable Markdown files in `brain/skills/`. |
| **Periodic Nudges** | Self-prompts every 4 hours to surface knowledge worth persisting. Configurable via `workspace.yaml`. |
| **User Models** | Profiles for all 7 team members (2 humans + 5 agents) with role, focus areas, and schedule. |
| **Cross-Session Recall** | Search past conversations, decisions, and outcomes across all agents and humans. |

### How to run it

```bash
cd brain
pip install -e ".[dev]"
brain                        # starts FastAPI server on :7777
# or
uvicorn brain.server:app --port 7777 --reload
```

### API endpoint summary

| Group | Endpoints |
|---|---|
| System | `GET /health` |
| Team | `GET /team`, `GET /team/{member}` |
| Memory | `POST /memory`, `GET /memory/search`, `GET /memory/recent/{member}` |
| Skills | `POST /skills`, `GET /skills`, `GET /skills/{name}`, `PUT /skills/{name}/improve`, `GET /skills/match`, `DELETE /skills/{name}` |
| Decisions | `POST /decisions`, `GET /decisions/search`, `GET /decisions/recent/{member}` |
| Nudges | `POST /nudges/check/{member}`, `GET /nudges/pending/{member}`, `PUT /nudges/{id}/act` |
| Sessions | `POST /sessions`, `PUT /sessions/{id}/end`, `GET /sessions/{member}`, `POST /sessions/{id}/summarize` |
| Learning | `POST /learning/after-task`, `POST /learning/periodic-review/{member}` |

Full API documentation at `http://localhost:7777/docs` when the server is running. See [`brain/README.md`](brain/README.md) for complete schema reference.

---

## The Dashboard

The dashboard is a zero-dependency HTML/JS app that gives a live view into the org.

### What it shows

- **Issues** — Open GitHub issues across all org repos, filtered by assignee/agent
- **Agents** — Current agent status, last run time, and schedule
- **Metrics** — KPI tracking pulled from `workspace.yaml` targets (WoW growth, MRR, NPS, SLA)
- **Standup** — Latest daily standup summary from `standup/`

### How to serve it

```bash
# Any static file server works
cd dashboard
python -m http.server 3333

# or with Bun
bun --bun run --cwd dashboard serve
```

No build step required. The dashboard reads from the GitHub API (public org data) and the brain API (`localhost:7777`).

---

## Agent Roster

| Codename | Role | Schedule / Trigger | Key Skills |
|----------|------|--------------------|------------|
| `ceo` | Chief Executive Officer | Weekdays 9am UTC | `autoplan`, `benchmark`, `plan-ceo-review` |
| `cto` | Chief Technology Officer | On `pull_request` trigger | `review`, `ship`, `design-review`, `plan-eng-review`, `drizzle-migrate`, `qa-only` |
| `growth` | Growth Lead | Mon/Wed/Fri 10am UTC | `autoplan`, `benchmark`, `mirofish`, `paperclip` |
| `cx-lead` | Customer Experience Lead | Always-on, `new_ticket` trigger | `cx-triage`, `cx-respond`, `cx-escalate`, `attio-sync`, `investigate` |
| `ops` | Operations Engineer | Always-on, `deploy_request` / `alert` trigger | `ship`, `canary`, `gcr-deploy`, `neon-ops`, `benchmark` |

Agent configs live in `agents/`. Each YAML defines the model, schedule, skills, context sources, outputs, and escalation path. Full schema documented in [`agents/`](agents/).

---

## Submodules

This repo uses three Git submodules:

| Path | Repo | Description |
|------|------|-------------|
| `modules/site` | [ellocharlie/ellocharlie.com](https://github.com/ellocharlie/ellocharlie.com) | Marketing landing page (static HTML/CSS/JS, GitHub Pages) |
| `modules/agents` | [ellocharlie/ellocharlie-agents](https://github.com/ellocharlie/ellocharlie-agents) | Agent runtimes, 18 skills, `ecforge` CLI |
| `modules/content` | [ellocharlie/ellocharlie-content](https://github.com/ellocharlie/ellocharlie-content) | Blog drafts, content calendar, analytics (MDX pipeline) |

### Update all submodules

```bash
git submodule update --remote --merge
```

---

## Key Documents

| Document | Description |
|---|---|
| [`MEMO.md`](MEMO.md) | The founding memo — why ellocharlie exists, what problem it solves |
| [`GROWTH.md`](GROWTH.md) | 7% WoW growth strategy from 2 customers to $10M ARR |
| [`docs/GAP-ANALYSIS.md`](docs/GAP-ANALYSIS.md) | Gap analysis vs. Superpowers benchmark + $30M platform plan |
| [`docs/PHASE1-CX-PLATFORM.md`](docs/PHASE1-CX-PLATFORM.md) | Phase 1 CX platform technical spec (Pylon-like layer) |
| [`docs/specs/README.md`](docs/specs/README.md) | Index of all versioned technical specifications |
| [`docs/plans/README.md`](docs/plans/README.md) | Index of all versioned implementation plans |
| [`AGENTS.md`](AGENTS.md) | Instructions for AI agents operating in this repo |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guide (applies org-wide) |

---

## workspace.yaml

`workspace.yaml` is the single source of truth for the ellocharlie org. It defines:

- **Team** — Human founders and all 5 agents with their roles, models, schedules, and skills
- **Repos** — Every repo in the org with type, path, owner, deploy target, and status
- **KPIs** — Growth targets (7% WoW), revenue (ARPU $137.50), CX SLAs (15m first response), engineering (daily deploys), content (3 posts/week)
- **OKRs** — Q2 2026 objectives and key results
- **Infrastructure** — App (Google Cloud Run, Neon, Clerk), site (GitHub Pages), status page

Agents read `workspace.yaml` before acting to ensure all decisions align with current targets.

---

## Development

### Run brain tests

```bash
cd brain
pytest
```

### Lint

```bash
cd brain
ruff check brain/
ruff check --fix brain/    # auto-fix
```

### Build the org index

```bash
bun run index:build     # → index/manifest.json
```

### Sync manifest to GitHub Gist

```bash
GITHUB_TOKEN=ghp_... bun run index:sync
```

### All Bun scripts

```bash
bun run index:build    # Scan submodules → manifest.json
bun run index:sync     # Push manifest.json → GitHub Gist
bun run standup        # → standup/YYYY-MM-DD.md
bun run review         # → reviews/YYYY-Www.md
bun run content        # Trigger content pipeline
```

### Commit conventions

All commits follow [Conventional Commits](https://conventionalcommits.org):

```
feat: add canary deployment skill
fix: handle missing API key gracefully
docs: update agent roster table
chore: bump bun to 1.1.x
```

---

## Repository Layout

```
ellocharlie-engine/
├── README.md                      # This file
├── MEMO.md                        # Founding memo
├── GROWTH.md                      # Growth strategy
├── AGENTS.md                      # Agent operating instructions
├── CLAUDE.md                      # Claude Code agent instructions
├── CONTRIBUTING.md                # Contribution guide
├── CHANGELOG.md                   # Release history
├── LICENSE                        # MIT
├── VERSION                        # Current version (semver)
├── workspace.yaml                 # Single source of truth
├── package.json                   # Bun scripts
├── .gitmodules                    # Submodule definitions
│
├── brain/                         # Python brain engine
│   ├── README.md
│   ├── pyproject.toml
│   └── brain/
│       ├── server.py              # FastAPI server (:7777)
│       ├── memory.py              # Memory + nudge engine
│       ├── skills.py              # Autonomous skill creation
│       ├── learning.py            # Closed learning loop
│       ├── team.py                # Team member profiles
│       └── db.py                  # SQLite + FTS5 layer
│
├── dashboard/                     # Ops dashboard (HTML/JS)
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── agents/                        # Agent YAML configs
│   ├── ceo.yml
│   ├── cto.yml
│   ├── growth.yml
│   ├── cx-lead.yml
│   └── ops.yml
│
├── workflows/                     # TypeScript orchestration
│   ├── daily-standup.ts
│   ├── weekly-review.ts
│   └── content-pipeline.ts
│
├── index/                         # Org index + Gist sync
│   ├── build-index.ts
│   └── gist-sync.ts
│
├── docs/                          # Strategic documents
│   ├── GAP-ANALYSIS.md
│   ├── PHASE1-CX-PLATFORM.md
│   ├── specs/                     # Versioned technical specs
│   │   └── README.md
│   └── plans/                     # Versioned implementation plans
│       └── README.md
│
├── modules/                       # Git submodules
│   ├── site/                      # → ellocharlie/ellocharlie.com
│   ├── agents/                    # → ellocharlie/ellocharlie-agents
│   └── content/                   # → ellocharlie/ellocharlie-content
│
├── standup/                       # Generated standup summaries
├── reviews/                       # Generated weekly reviews
│
└── .github/
    └── workflows/
        ├── ci.yml
        ├── daily-standup.yml
        └── content-pipeline.yml
```

---

## Related Repos

| Repo | Description |
|------|-------------|
| [ellocharlie/ellocharlie.com](https://github.com/ellocharlie/ellocharlie.com) | Marketing landing page — static HTML/CSS/JS, deployed to GitHub Pages |
| [ellocharlie/ellocharlie-agents](https://github.com/ellocharlie/ellocharlie-agents) | Multi-agent platform — 18 skills, `ecforge` CLI, agent runtimes |
| [ellocharlie/ellocharlie-content](https://github.com/ellocharlie/ellocharlie-content) | Content engine — MDX blog pipeline, content calendar, analytics |
| [ellocharlie/ellocharlie-engine](https://github.com/ellocharlie/ellocharlie-engine) | **This repo** — superrepo, brain, dashboard, orchestrator |

---

<div align="center">

Built with [Anthropic Claude](https://anthropic.com) · Deployed on [Google Cloud Run](https://cloud.google.com/run) · MIT License

</div>
