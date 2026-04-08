# Changelog — ellocharlie-engine

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] - 2026-04-08

### Added

- **`workspace.yaml`** — Single source of truth for the entire org: identity, team, repos, KPIs, OKRs, brain config, dashboard config, and infrastructure topology.
- **Five agent configs** in `agents/`:
  - `ceo.yml` — Strategy, OKR tracking, investor updates. Runs weekdays 9am UTC with `autoplan`, `benchmark`, and `plan-ceo-review` skills.
  - `cto.yml` — Code review, architecture decisions, tech debt. Triggered on pull request events.
  - `growth.yml` — Content drafting, SEO analytics, acquisition. Runs Mon/Wed/Fri 10am UTC.
  - `cx-lead.yml` — Ticket triage, customer health scoring, SLA enforcement. Always-on, triggered on new ticket.
  - `ops.yml` — CI/CD, canary deploys, incident response, infrastructure. Always-on, triggered on deploy request.
- **`brain/`** — Python service (port 7777) providing memory, skill dispatch, and learning loop for the agent system. Reads/writes to SQLite at `brain/data/brain.db`. Skills directory at `brain/skills/`.
- **`dashboard/`** — Static HTML/JS org dashboard (port 3333) showing cross-repo issue tracking, KPI progress, agent activity, and content pipeline status. No build step required.
- **`index/build-index.ts`** — Scans all submodules, reads their `package.json` and `README.md`, and outputs `index/manifest.json` as a structured org state snapshot.
- **`index/gist-sync.ts`** — Pushes `index/manifest.json` to a public GitHub Gist, serving as a live org-state API endpoint.
- **`workflows/daily-standup.ts`** — Generates `standup/YYYY-MM-DD.md` from agent configs and outputs. Triggered by GitHub Actions at 9am UTC weekdays.
- **`workflows/weekly-review.ts`** — Generates `reviews/YYYY-Www.md` aggregating the week's activity. Triggered on Fridays.
- **`workflows/content-pipeline.ts`** — Reads `backlog.yml` from the content submodule, picks the next queued topic, and scaffolds a draft. Triggered Mon/Wed/Fri 10am UTC.
- **`.gitmodules`** — Submodule declarations for `modules/site` (ellocharlie.com), `modules/agents` (ellocharlie-agents), and `modules/content` (ellocharlie-content).
- **`CLAUDE.md`** — Comprehensive instructions for AI agents and humans: superrepo architecture, submodule workflow, brain/dashboard startup, agent config schema, Bun/TypeScript standards, commit conventions, and full key file reference.
- **`MEMO.md`** — Founding memo encoding the company voice, values, and beliefs. Source of truth for all strategic decisions.
- **`GROWTH.md`** — Growth playbook: 7% WoW compound model, phase-by-phase acquisition strategy, ARPU targets, and content/SEO roadmap.
- **`docs/GAP-ANALYSIS.md`** — Gap analysis against target state.
- **`docs/PHASE1-CX-PLATFORM.md`** — Phase 1 CX platform specification.
- **`package.json`** — Bun project config with scripts: `index:build`, `index:sync`, `standup`, `review`, `content`.

### Org Context

This release establishes the controller layer of the ellocharlie agent-driven company. The engine is the source of gravity for the org — all other repositories are submodules, all agent behavior is defined here, and `workspace.yaml` is the single point of configuration for the entire system.

Current OKRs (Q2 2026):
- Land first 10 customers through personal network (owner: Nicholas)
- Ship Phase 1 CX platform (owner: CTO agent)
- Build content engine and SEO foundation (owner: Growth agent)

---

[Unreleased]: https://github.com/ellocharlie/ellocharlie-engine/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ellocharlie/ellocharlie-engine/releases/tag/v0.1.0
