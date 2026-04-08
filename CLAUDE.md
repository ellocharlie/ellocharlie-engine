# CLAUDE.md — ellocharlie-engine

> Read this file before touching anything in this repo.
> Then read `MEMO.md` and `GROWTH.md` — they are the founding documents and encode the values behind every decision.

---

## What This Repo Is

`ellocharlie-engine` is the **brain and orchestrator for the entire ellocharlie org**. It does not contain product code. It contains everything that governs how the org thinks, plans, and operates:

- The **brain** (Python service on port 7777) — memory, skills, and the learning loop
- The **dashboard** (HTML/JS on port 3333) — cross-repo issue tracking and org-wide metrics
- **Agent configs** (`agents/*.yml`) — canonical definitions for all 5 AI agents
- **Workflow scripts** (`workflows/*.ts`) — Bun scripts driving recurring operations
- **Index scripts** (`index/*.ts`) — build and publish the org-wide manifest
- **Submodule pointers** (`modules/`) — live links to the product repos

This repo is the source of truth. When anything conflicts with what's here, this repo wins — except the `workspace.yaml`, which overrides everything.

---

## The Single Source of Truth

**`workspace.yaml`** governs:
- Org identity, mission, domain
- Team members (human and agent)
- All repo URLs, types, and owners
- KPIs and OKRs
- Infrastructure topology
- Brain and dashboard config

Before editing any agent behavior, workflow schedule, or infrastructure reference — check `workspace.yaml`. If the change needs to persist, it goes in `workspace.yaml` first.

---

## Founding Documents

Read these before doing anything substantive:

| File | Purpose |
|------|---------|
| `MEMO.md` | The founding memo. Explains why ellocharlie exists, the five beliefs, and how Nicholas and Cristine think about customers and systems. This is the voice of the company. |
| `GROWTH.md` | The growth playbook. 7% WoW from 2 customers, full compound model, phase-by-phase acquisition strategy. Every growth-related decision is made against this document. |

If you're writing content, making product decisions, or adjusting agent behavior — MEMO.md and GROWTH.md are the calibration baseline.

---

## Submodule Architecture

This repo is a **superrepo**. The actual product repos are submodules in `modules/`:

| Module | Repo | Owner |
|--------|------|-------|
| `modules/site` | `https://github.com/ellocharlie/ellocharlie.com` | Growth |
| `modules/agents` | `https://github.com/ellocharlie/ellocharlie-agents` | CTO |
| `modules/content` | `https://github.com/ellocharlie/ellocharlie-content` | Growth |

### Initialize submodules (first time)

```bash
git submodule update --init --recursive
```

### Update a submodule to its latest remote commit

```bash
git submodule update --remote modules/<name>
git add modules/<name>
git commit -m "chore: bump <name> to latest"
```

### Check submodule state

```bash
git submodule status
```

### Work inside a submodule

```bash
cd modules/agents
git checkout main
# make changes, commit, push to the submodule's own remote
cd ../..
git add modules/agents
git commit -m "chore: bump agents submodule"
```

**Never commit changes to submodule files from this repo's working tree.** Changes to `modules/*` content must go through each submodule's own commit/push flow.

---

## Running the Brain

The brain is a Python service that provides memory, skills, and the learning loop for the agent system.

```bash
cd brain
pip install -e .
brain
```

Starts on **port 7777**. The brain reads and writes to `brain/data/brain.db` (SQLite). The `brain/skills/` directory contains the skill implementations loaded at runtime.

Configuration is in `workspace.yaml` under the `brain:` key:
```yaml
brain:
  engine: python
  port: 7777
  database: brain/data/brain.db
  skills_dir: brain/skills/
  learning_loop: enabled
  nudge_interval: 4h
```

The brain does not auto-restart. If it's down, agents that depend on memory or learning-loop skills will degrade gracefully but will not persist state across sessions.

---

## Serving the Dashboard

The dashboard is a static HTML/JS app that pulls live data from the GitHub API and the brain.

```bash
cd dashboard
python -m http.server 3333
```

Opens at **http://localhost:3333**. The dashboard shows:
- Cross-repo open issues and PR status
- KPI tracking against `workspace.yaml` targets
- Agent activity log
- Content pipeline status

The dashboard reads `workspace.yaml` for config and queries the GitHub org (`ellocharlie`) for live data. No build step required — it's vanilla HTML/JS.

---

## Index: Build and Sync

### Build the org manifest

```bash
bun run index:build
```

Reads submodule `package.json` and `README.md` files, agent configs, and `workspace.yaml`. Outputs `index/manifest.json`. Run this after bumping any submodule or editing agent configs.

### Sync to GitHub Gist

```bash
GITHUB_TOKEN=... bun run index:sync
```

Pushes `index/manifest.json` to a public GitHub Gist as a JSON endpoint. Requires `GITHUB_TOKEN` with `gist` scope. The Gist ID is stored in `index/.gist-id` after the first run — subsequent runs update the same Gist.

---

## Workflows

### Daily standup

```bash
bun run standup
```

Triggered automatically by `.github/workflows/daily-standup.yml` at 9am UTC on weekdays, or run manually. Reads agent configs and output directories, produces `standup/YYYY-MM-DD.md`. Commit the output file after generation.

### Weekly review

Triggered manually or on Fridays. Run via `.github/workflows/weekly-review.yml`. Produces `reviews/YYYY-Www.md` aggregating the week's activity across all repos and agents.

### Content pipeline

Triggered by `.github/workflows/content-pipeline.yml` Mon/Wed/Fri at 10am UTC. Reads `modules/content/content/calendar/backlog.yml`, picks the next topic, scaffolds a draft in `modules/content/content/blog/`, and updates the backlog status.

---

## Agent Configs (`agents/*.yml`)

Each agent has a canonical config file:

| File | Agent | Role | Schedule |
|------|-------|------|----------|
| `agents/ceo.yml` | CEO | Strategy, metrics, drift detection | Weekdays 9am UTC |
| `agents/cto.yml` | CTO | Code review, architecture, tech debt | On PR trigger |
| `agents/growth.yml` | Growth | Content, SEO, acquisition analytics | Mon/Wed/Fri 10am UTC |
| `agents/cx-lead.yml` | CX Lead | Ticket triage, health scoring, SLA | Always-on, on new ticket |
| `agents/ops.yml` | Ops | Deploy, infra, incident response | Always-on, on deploy request |

These configs are the single source of truth for agent behavior. They are read by:
1. `index/build-index.ts` — to build the manifest
2. `modules/agents` runtime — to configure Claude sessions

### Schema rules

- `codename` — lowercase, hyphens only
- `model` — valid Anthropic model ID
- `schedule` — cron expression, `on-demand`, or `always-on`
- `trigger` — GitHub event name: `pull_request`, `deploy_request`, `alert`, `new_ticket`
- `skills` — array of skill IDs implemented in `modules/agents/skills/`
- `escalation` — must be a valid agent codename or `"human"`

### When editing agent configs

- **Add a skill**: Add the skill ID to the `skills` array. Ensure the skill exists in `modules/agents/skills/`.
- **Change schedule**: Edit the cron expression AND update the corresponding GitHub Actions workflow in `.github/workflows/`.
- **Change escalation**: Must resolve to a valid agent codename or `"human"`.
- **After any change**: Run `bun run index:build` to regenerate the manifest.

---

## KPIs and OKRs (from workspace.yaml)

All commits that implement work against a KPI or OKR should reference it. The current targets:

**KPIs:**
- Growth: 7% WoW customer growth
- Revenue: Track toward GROWTH.md milestones; blended ARPU $137.50/customer
- CX: 15m first-response SLA, 4h resolution SLA, NPS target 70, churn < 2%/month
- Engineering: Daily deploys, mandatory canary, 100% review coverage
- Content: 3 posts/week, 100 articles by month 12

**OKRs (Q2 2026):**
1. Land first 10 customers (owner: Nicholas)
2. Ship Phase 1 CX platform (owner: CTO)
3. Build content engine and SEO foundation (owner: Growth)

---

## Commit Conventions

Use Conventional Commits:

```
feat: add new agent skill config
fix: correct ops escalation target
chore: bump agents submodule
docs: update architecture diagram
ci: add weekly-review cron trigger
```

Optional scopes: `agents`, `index`, `workflows`, `ci`, `modules`, `brain`, `dashboard`

When a commit implements work against a KPI or OKR, reference it:

```
feat(agents): add cx escalation skill for NPS < 7 trigger [cx.nps_target]
chore: bump content submodule — 3 posts published [content.blog_cadence]
```

---

## TypeScript / Bun Standards

All scripts use **Bun**. Do not use Node.js APIs when Bun equivalents exist:

| Node | Bun preferred |
|------|---------------|
| `fs.readFileSync` | `await Bun.file(path).text()` |
| `fs.writeFileSync` | `await Bun.write(path, content)` |
| `JSON.parse(...)` | `await Bun.file(path).json()` |
| `process.env.X` | `Bun.env.X` |

- Strict TypeScript. Every function has typed parameters and return types.
- `interface` for object shapes, `type` for unions/aliases.
- No `any`. Use `unknown` and narrow it.
- All async functions must be awaited — no floating promises.
- ESM only (`import`/`export`). Never `require`.

---

## GitHub Actions

Located in `.github/workflows/`. Two secrets required:
- `GITHUB_TOKEN` — auto-provided by GitHub Actions
- `ANTHROPIC_API_KEY` — set in repo Settings → Secrets

Never hardcode secrets. Always read from environment variables.

---

## Key File Reference

| Path | Purpose |
|------|---------|
| `workspace.yaml` | Single source of truth for org state |
| `MEMO.md` | Founding memo — company voice and values |
| `GROWTH.md` | Growth playbook — acquisition and retention strategy |
| `agents/*.yml` | Agent definitions (ceo, cto, growth, cx-lead, ops) |
| `brain/` | Python brain service (memory, skills, learning loop) |
| `brain/data/brain.db` | SQLite memory store (gitignored) |
| `brain/skills/` | Skill implementations loaded by the brain |
| `dashboard/` | Static HTML/JS metrics dashboard |
| `index/build-index.ts` | Org manifest builder |
| `index/gist-sync.ts` | Pushes manifest to GitHub Gist |
| `index/manifest.json` | Generated org state snapshot |
| `index/.gist-id` | Gist ID persisted after first sync (gitignored) |
| `modules/agents/` | Submodule: agents runtime (18 skills, ecforge CLI) |
| `modules/site/` | Submodule: marketing site |
| `modules/content/` | Submodule: content engine |
| `workflows/daily-standup.ts` | Standup generator |
| `workflows/weekly-review.ts` | Weekly review generator |
| `workflows/content-pipeline.ts` | Content backlog → draft automation |
| `standup/` | Daily standup outputs (gitignored) |
| `reviews/` | Weekly review outputs (gitignored) |
| `docs/PHASE1-CX-PLATFORM.md` | Phase 1 product spec |

---

## What Not to Do

- Do not put product code in this repo. Product code lives in the submodules.
- Do not add `npm install` steps. Bun handles dependencies.
- Do not commit secrets or API keys to any file.
- Do not commit `index/manifest.json` with stale timestamps — regenerate before committing.
- Do not add `node_modules/` — Bun manages its own cache.
- Do not create a new agent config without adding the agent to `workspace.yaml` and the README.
- Do not modify submodule file content from this repo's working tree.
- Do not skip the submodule update step after bumping a submodule pointer.

---

## Debugging

**Submodules not initialized:**
```bash
git submodule update --init --recursive
```

**Build index fails:**
Check submodule state first, then:
```bash
bun x tsc --noEmit
```

**Brain won't start:**
Check `brain/data/` exists and `pip install -e .` completed without errors. The `brain.db` file is created on first run.

**Gist sync fails:**
```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/gists
```
Verify `gist` scope is present.

**Dashboard shows no data:**
Check that `GITHUB_TOKEN` is set in the environment and the `ellocharlie` org is accessible.
