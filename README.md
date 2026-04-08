<div align="center">

# ellocharlie

**Stop losing customers to broken processes.**

[![CI](https://img.shields.io/github/actions/workflow/status/ellocharlie/ellocharlie-engine/ci.yml?branch=main&label=CI)](https://github.com/ellocharlie/ellocharlie-engine/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://python.org)
[![Bun](https://img.shields.io/badge/Bun-1.x-f9f1e1.svg)](https://bun.sh)

</div>

---

## What is ellocharlie?

Every company has the same problem, and most don't notice it until a customer is already gone. The deal closes. The handoff from sales happens — or doesn't. The customer lands in a support queue that knows nothing about the sales conversation. Three weeks later they churn and everyone is surprised.

Nicholas Daniel-Richards and Kristine built ellocharlie because they've watched this happen too many times, at companies of every size. Nicholas spent eight years building ShipHero and Packiyo, watching warehouse operations collapse not from bad engineering but from tools that refused to talk to each other. Kristine spent years at IBM and inside Amazon's early infrastructure, learning that the gap between what enterprise technology promises and what a real human actually experiences at 2pm on a Tuesday is where companies live or die.

ellocharlie is the unified CX platform for companies with 2 to 500 employees — CRM, helpdesk, knowledge base, onboarding, and health monitoring in one system. Not duct-taped together. Actually unified. Five AI agents run the operations so the humans can focus on the work that machines genuinely cannot do. Read [MEMO.md](MEMO.md) for the full founding story.

---

## The Org at a Glance

| Repo | What it is | Owner |
|------|------------|-------|
| [ellocharlie-engine](https://github.com/ellocharlie/ellocharlie-engine) | You are here. The brain, dashboard, and orchestrator. | Nicholas |
| [ellocharlie.com](https://github.com/ellocharlie/ellocharlie.com) | Marketing landing page | Growth Agent |
| [ellocharlie-agents](https://github.com/ellocharlie/ellocharlie-agents) | 18 skills + ecforge CLI | CTO Agent |
| [ellocharlie-content](https://github.com/ellocharlie/ellocharlie-content) | Blog posts and content engine | Growth Agent |
| [.github](https://github.com/ellocharlie/.github) | Org profile, issue templates, community health | — |

---

## The Team

**Nicholas Daniel-Richards** — Founder. 20+ years building digital platforms: ShipHero (warehouse management at scale), the National Basketball Players Association, Code and Theory, Packiyo. Handles product, strategy, and every customer conversation for the first 10. The one who answers the phone.

**Kristine** — Founder. Enterprise tech veteran with time at IBM and inside Jeff Bezos's Amazon before it became what it is today. Bridges the gap between what technology promises and what customers actually experience. The last-mile obsession is baked into every CX decision we make.

**CEO Agent** — Tracks whether we're doing what we said we'd do. Runs weekday mornings at 9am. Reviews the growth numbers, flags drift between strategy and execution, and drafts investor updates when the time comes.

**CTO Agent** — Reviews every pull request and architecture decision. Catches multi-tenant data leaks, migration risks, and technical debt before it compounds. Triggers on every PR; doesn't clock out.

**Growth Agent** — Writes 3 blog posts a week, manages SEO strategy, and runs the build-in-public pipeline. Works Monday, Wednesday, and Friday. By Month 6, it will have published more content than most marketing teams produce in a year.

**CX Lead Agent** — Always on. Monitors every customer interaction, maintains the 15-minute first-response SLA, tracks account health scores, and surfaces at-risk accounts before customers know they're unhappy.

**Ops Agent** — Always on. Handles deploys with mandatory 5% canary testing, monitors infrastructure, and manages incident response. The reason we sleep through the night.

---

## For Founders: How to Run Your Company

This section is for Nicholas and Kristine.

### Check on the company

```bash
# Open the dashboard (shows issues, agents, metrics, standup)
cd dashboard && python -m http.server 3333
# Open http://localhost:3333
```

Or run the daily standup from the terminal:

```bash
bun run standup
```

### Store a memory or decision

The brain remembers everything important. Talk to it directly:

```bash
# Store a memory
curl -X POST http://localhost:7777/memory \
  -H 'Content-Type: application/json' \
  -d '{"team_member": "nicholas", "content": "Customer X loved the onboarding flow but wants Slack integration", "category": "customer_insight"}'

# Log a decision
curl -X POST http://localhost:7777/decisions \
  -H 'Content-Type: application/json' \
  -d '{"team_member": "nicholas", "context": "Phase 1 prioritization", "decision": "Ship email channel before Slack", "reasoning": "Lower complexity, faster time to value"}'
```

### Onboard a new customer

1. Customer signs up at [app.ellocharlie.com/register](https://app.ellocharlie.com/register)
2. CX Lead agent sends a welcome message within 15 minutes
3. Nicholas schedules the onboarding call — for the first 10 customers, always
4. Onboarding project created with default checklist
5. Health monitoring starts with a 48-hour first check
6. Weekly check-in rotation for the first 90 days

See the full flow in `brain/skills/example-onboarding-flow.md`.

### Publish a blog post

```bash
# The pipeline:
# 1. Growth agent drafts → content/blog/
# 2. CTO reviews technical accuracy
# 3. CEO approves positioning
# 4. Ops deploys (triggers site rebuild)

# Or manually scaffold a new post:
cd ../ellocharlie-content
bun run scripts/new-post.ts
```

### See the growth numbers

Open [GROWTH.md](GROWTH.md) for the full model — week-by-week from 2 customers to $10M ARR at 7% WoW. The dashboard shows current vs. target at a glance. The number that matters: are we at or above 7%?

### Key documents

Read these before anything else:

| Document | What it is |
|----------|------------|
| [MEMO.md](MEMO.md) | Why we built this. Our beliefs. How we work. |
| [GROWTH.md](GROWTH.md) | 7% WoW growth strategy from 2 customers to $10M ARR |
| [workspace.yaml](workspace.yaml) | Single source of truth — team, repos, KPIs, OKRs |
| [docs/PHASE1-CX-PLATFORM.md](docs/PHASE1-CX-PLATFORM.md) | Phase 1 technical spec (4,260 lines) |
| [docs/GAP-ANALYSIS.md](docs/GAP-ANALYSIS.md) | Platform quality gaps and $30M roadmap |

---

## For Engineers: Getting Started

### Clone the entire org

```bash
git clone --recurse-submodules https://github.com/ellocharlie/ellocharlie-engine.git
cd ellocharlie-engine
```

### Start the brain

```bash
cd brain
pip install -e ".[dev]"
brain  # Starts FastAPI on port 7777
```

### Run the tests

```bash
cd brain
pytest -v  # 176 tests
```

### Serve the dashboard

```bash
cd dashboard
python -m http.server 3333
# Open http://localhost:3333 — enter a GitHub token when prompted
```

### Architecture

```
ellocharlie-engine/          ← You are here (superrepo)
├── brain/                   ← Python: memory, skills, learning loop (port 7777)
├── dashboard/               ← HTML/JS: issues, agents, metrics (port 3333)
├── agents/                  ← YAML: 5 agent configs
├── workflows/               ← TypeScript: standup, review, content pipeline
├── index/                   ← TypeScript: gist-based org index
├── modules/
│   ├── site/       → github.com/ellocharlie/ellocharlie.com
│   ├── agents/     → github.com/ellocharlie/ellocharlie-agents
│   └── content/    → github.com/ellocharlie/ellocharlie-content
├── workspace.yaml           ← Single source of truth
├── MEMO.md                  ← Founding story
└── GROWTH.md                ← Growth strategy
```

The brain (port 7777) is the memory and skills layer. The dashboard (port 3333) reads GitHub and the brain to give you a real-time view of the org. The agents run on their own schedules and communicate through the brain. Nothing is stateful except the brain's SQLite database at `brain/data/brain.db`.

### Commit conventions

We use [Conventional Commits](https://conventionalcommits.org):

```
feat(brain): add skill auto-improvement after 10 uses
fix(dashboard): correct issue count badge for closed filter
docs(engine): update onboarding flow in README
ci(content): add MDX validation to PR checks
test(brain): add FTS5 edge case coverage
```

One logical change per commit. Author: `cr_oot`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

### Where to add things

| I want to... | Go to... |
|--------------|----------|
| Add a new agent skill | `ellocharlie-agents/skills/<name>/SKILL.md` |
| Add a new workflow | `workflows/<name>.ts` |
| Add a new agent config | `agents/<name>.yml` |
| Write a blog post | `ellocharlie-content/content/blog/` |
| Add a brain endpoint | `brain/brain/server.py` |
| Create a new brain skill | `brain/skills/<name>.md` |
| Update the dashboard | `dashboard/app.js` + `dashboard/style.css` |

### Key files for context

Read these before making changes:

- [CLAUDE.md](CLAUDE.md) — Instructions for AI agents working in this repo
- [AGENTS.md](AGENTS.md) — Contribution guidelines for AI agents
- [CONTRIBUTING.md](CONTRIBUTING.md) — Human contributor guidelines
- [workspace.yaml](workspace.yaml) — Org manifest with KPIs and OKRs

---

## For Content Contributors

You don't need to touch any code to contribute. Here's how content moves from idea to published:

1. **Ideas go in the backlog** — `ellocharlie-content/content/calendar/backlog.yml`
2. **Growth agent picks topics** and writes first drafts (3 per week)
3. **CTO agent reviews** for technical accuracy
4. **CEO (Nicholas) approves** for positioning and voice
5. **Ops agent deploys** — the article goes live on ellocharlie.com

To suggest a topic: [open an issue](https://github.com/ellocharlie/ellocharlie-content/issues/new?template=feature_request.md) on the content repo.

To write a post directly, follow the guide in the [content repo README](https://github.com/ellocharlie/ellocharlie-content#readme).

Our voice is professional, empathetic, and data-driven. Not corporate. Not buzzwordy. The bar is: would a smart founder find this genuinely useful, or are we just making noise? Read [MEMO.md](MEMO.md) for the full philosophy.

---

## Community

- [Code of Conduct](https://github.com/ellocharlie/.github/blob/main/CODE_OF_CONDUCT.md)
- [Security Policy](https://github.com/ellocharlie/.github/blob/main/SECURITY.md)
- [Contributing Guide](CONTRIBUTING.md)
- [MIT License](LICENSE)

---

<div align="center">

Built by Nicholas Daniel-Richards & Kristine.<br>
New York, 2026.

*"Stop losing customers to broken processes."*

</div>
