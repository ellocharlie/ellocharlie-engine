# ellocharlie-engine

The controller and orchestrator for the [ellocharlie](https://github.com/ellocharlie) GitHub org. This repo is the **brain** of a 5-person agent-driven company — it holds agent configurations, shared workflows, the org-wide index, and the glue code that makes everything run autonomously.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ellocharlie-engine                           │
│                    (this repo — the controller)                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
          ┌─────────────────┼──────────────────────┐
          │                 │                       │
    ┌─────▼──────┐   ┌──────▼──────┐   ┌───────────▼────────┐
    │  modules/  │   │   agents/   │   │    workflows/       │
    │   site     │   │  (5 agents) │   │  daily-standup.ts   │
    │   agents   │   │  ceo.yml    │   │  weekly-review.ts   │
    │   content  │   │  cto.yml    │   │  content-pipeline.ts│
    └─────┬──────┘   │  growth.yml │   └────────────────────-┘
          │          │  cx-lead.yml│
          │          │  ops.yml    │         ┌────────────────┐
          │          └──────┬──────┘         │    index/      │
          │                 │                │ build-index.ts │
          │                 │                │  gist-sync.ts  │
          │                 │                └───────┬────────┘
          │                 │                        │
          └─────────────────┴────────────────────────┘
                            │
                     ┌──────▼──────┐
                     │  manifest   │
                     │  .json      │  ←── Synced to GitHub Gist
                     └─────────────┘
```

### Agent Org Chart

```
                    ┌──────────────────┐
                    │   CEO (autoplan) │
                    │  OKRs · Strategy │
                    │   Investor Upd.  │
                    └────────┬─────────┘
                             │ escalation
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │     CTO     │   │   Growth    │   │   CX Lead   │
    │  PR Review  │   │  3x/wk blog │   │  Always-on  │
    │  Arch Decis.│   │  SEO · Social│   │  Tickets    │
    └──────┬──────┘   └──────┬──────┘   └─────────────┘
           │ escalation      │ content approval
    ┌──────▼──────┐   ┌──────▼──────┐
    │     OPS     │   │  CEO review │
    │  CI/CD      │   │  (positioning)│
    │  Deploys    │   └─────────────┘
    │  Incidents  │
    └─────────────┘
```

### Data Flow

```
  GitHub Events ──────────────────────────────────────────────────────┐
  (PR opened, deploy req, new ticket)                                 │
                                                                      ▼
  Cron Jobs ──────────────────────────────────────────────────► Agent Runner
  (daily standup, content pipeline)                           (claude-sonnet-4-5)
                                                                      │
                                                        ┌─────────────┴────────────┐
                                                        ▼                          ▼
                                                   Tool Skills              Outputs written
                                                 (autoplan, ship,          to submodule repos
                                                  review, cx-triage)      (PRs, reports, posts)
```

---

## Submodule Repos

| Module | Repo | Purpose |
|--------|------|---------|
| `modules/site` | [ellocharlie/ellocharlie.com](https://github.com/ellocharlie/ellocharlie.com) | Astro marketing site |
| `modules/agents` | [ellocharlie/ellocharlie-agents](https://github.com/ellocharlie/ellocharlie-agents) | Agent runtimes, skills, stack context |
| `modules/content` | [ellocharlie/ellocharlie-content](https://github.com/ellocharlie/ellocharlie-content) | Blog drafts, social posts, SEO reports |

---

## The 5 Agents

| Codename | Role | Schedule | Key Skills |
|----------|------|----------|------------|
| `ceo` | Chief Executive Officer | Weekdays 9am UTC | autoplan, benchmark, plan-ceo-review |
| `cto` | Chief Technology Officer | On PR trigger | review, ship, design-review, drizzle-migrate |
| `growth` | Growth Lead | Mon/Wed/Fri 10am UTC | autoplan, benchmark, mirofish, paperclip |
| `cx-lead` | CX Lead | Always-on (ticket trigger) | cx-triage, cx-respond, cx-escalate, attio-sync |
| `ops` | Operations Engineer | Always-on (deploy/alert trigger) | ship, canary, gcr-deploy, neon-ops |

---

## Quickstart

### Prerequisites

- [Bun](https://bun.sh) >= 1.0
- `GITHUB_TOKEN` env var with `gist` and `repo` scopes

### Clone with submodules

```bash
git clone --recurse-submodules https://github.com/ellocharlie/ellocharlie-engine.git
cd ellocharlie-engine
```

### Update submodules

```bash
git submodule update --remote --merge
```

### Build the org index

Scans all submodules, reads their `package.json` and `README.md`, and outputs `index/manifest.json`:

```bash
bun run index:build
```

### Sync manifest to GitHub Gist

Reads `index/manifest.json` and creates or updates a GitHub Gist (acts as a public API endpoint for the org state):

```bash
GITHUB_TOKEN=ghp_... bun run index:sync
```

### Run daily standup

```bash
bun run standup
# → outputs standup/YYYY-MM-DD.md
```

### Run weekly review

```bash
bun run review
# → outputs reviews/YYYY-Www.md
```

### Trigger content pipeline

```bash
bun run content
# → picks topics from backlog, kicks off growth agent drafts
```

---

## How Agents Work

Each agent is defined by a YAML config in `agents/`. The configs are consumed by the agent runner in `modules/agents`.

### Agent Lifecycle

1. **Trigger** — Either a cron schedule, a GitHub event (PR, deploy request, new ticket), or on-demand.
2. **Context loading** — The runner reads `context_sources` paths from the agent config and injects them into the Claude prompt as context.
3. **Skill dispatch** — The agent's `skills` list maps to pre-built tool implementations in `modules/agents/skills/`.
4. **Output writing** — Outputs are written back to the repo (PRs, markdown reports, structured JSON) at the paths defined in `outputs`.
5. **Escalation** — If the agent encounters something beyond its authority, it escalates to the `escalation` target (either another agent codename or `human`).

### Agent Config Schema

```yaml
name: string           # Human-readable name
codename: string       # Used as identifier across the system
model: string          # LLM model (e.g., claude-sonnet-4-5)
schedule: cron|string  # Cron expression or named schedule
trigger: string        # GitHub event or named trigger (optional)
skills: string[]       # Skill IDs available to this agent
responsibilities: string[]  # Plain-language capability descriptions
context_sources: string[]   # Paths injected as context (relative to repo root)
outputs: string[]           # Where this agent writes its work
escalation: string          # Codename or "human"
```

### Skills

Skills are reusable tool wrappers that give agents specific capabilities:

| Skill | Description |
|-------|-------------|
| `autoplan` | Generate structured plans from goals or briefs |
| `benchmark` | Run performance comparisons against baselines |
| `review` | Code review with structured feedback |
| `ship` | Stage and deploy changes through CI/CD |
| `canary` | Deploy to canary percentage with automatic rollback |
| `cx-triage` | Classify and prioritize support tickets |
| `cx-respond` | Draft customer responses |
| `cx-escalate` | Package escalations with full context |
| `attio-sync` | Sync data to/from Attio CRM |
| `gcr-deploy` | Deploy container images to Google Cloud Run |
| `neon-ops` | Database operations on Neon Postgres |
| `drizzle-migrate` | Run Drizzle ORM migrations |
| `investigate` | Root cause analysis for incidents |

---

## Index & Gist API

The `index/` scripts maintain a live snapshot of the org state.

`index/manifest.json` structure:

```json
{
  "org": "ellocharlie",
  "updated": "2026-04-08T09:00:00.000Z",
  "repos": {
    "site": { "name": "ellocharlie.com", "description": "...", "version": "..." },
    "agents": { "name": "ellocharlie-agents", "description": "...", "version": "..." },
    "content": { "name": "ellocharlie-content", "description": "...", "version": "..." }
  },
  "agents": {
    "ceo": { "model": "claude-sonnet-4-5", "schedule": "0 9 * * 1-5", "skills": [...] },
    "cto": { "model": "claude-sonnet-4-5", "schedule": "on-demand", "skills": [...] },
    ...
  }
}
```

The Gist URL is stored in `index/.gist-id` after the first sync. Subsequent runs update the same Gist.

---

## Content Pipeline

The content pipeline is an automated 3-step review chain:

```
growth (draft) → cto (technical review) → ceo (positioning review) → ops (publish)
```

Topics come from `modules/content/calendar/backlog.md`. Each topic is promoted through pipeline stages by updating frontmatter in the draft file.

---

## CI/CD

Two GitHub Actions workflows run automatically:

- **daily-standup.yml** — Runs every weekday at 9am UTC, commits standup summary to `standup/`
- **content-pipeline.yml** — Runs Mon/Wed/Fri at 10am UTC, kicks off the content generation cycle

Both workflows use `GITHUB_TOKEN` (auto-provided) and `ANTHROPIC_API_KEY` (repo secret).

---

## Repository Layout

```
ellocharlie-engine/
├── README.md                    # This file
├── CLAUDE.md                    # Instructions for Claude Code agents
├── package.json                 # Bun scripts
├── .gitmodules                  # Submodule definitions
│
├── index/
│   ├── build-index.ts           # Scans submodules → manifest.json
│   ├── gist-sync.ts             # Pushes manifest.json → GitHub Gist
│   └── manifest.json            # Generated — do not edit manually
│
├── agents/
│   ├── ceo.yml
│   ├── cto.yml
│   ├── growth.yml
│   ├── cx-lead.yml
│   └── ops.yml
│
├── workflows/
│   ├── daily-standup.ts
│   ├── weekly-review.ts
│   └── content-pipeline.ts
│
├── modules/                     # Git submodules
│   ├── site/                    # ellocharlie/ellocharlie.com
│   ├── agents/                  # ellocharlie/ellocharlie-agents
│   └── content/                 # ellocharlie/ellocharlie-content
│
├── standup/                     # Generated standup summaries
├── reviews/                     # Generated weekly reviews
│
└── .github/
    └── workflows/
        ├── daily-standup.yml
        └── content-pipeline.yml
```
