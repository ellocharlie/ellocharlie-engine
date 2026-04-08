# Gap Analysis & $30M Platform Plan
**ellocharlie GitHub Org — April 2026**
**Benchmark: obra/superpowers (141K ★, 421 commits, production-grade agentic skills framework)**

---

## 1. Executive Summary

The ellocharlie org is early-stage infrastructure built on a solid philosophical foundation — ETHOS.md, CLAUDE.md files in every repo, and a mirrored skills platform with real depth. `ellocharlie-agents` is already the best repo in the org: it has 18 skills, a working CLI (`ecforge`), CI workflows, architecture docs, and a license. The other four repos lag meaningfully behind. The `.github` org profile is a single-file stub.

Against the Superpowers benchmark — the current gold standard for an agentic skills platform — the gaps are structural, not conceptual. Superpowers earns its $30M valuation through uncompromising execution discipline: every skill has mandatory frontmatter and pressure tests, every PR requires a signed comprehensive template, agent instructions explicitly define rejection criteria, and multi-platform plugin distribution is first-class. The ellocharlie org has the right ideas; it needs the right execution.

**Current state by repo:**

| Repo | Commits | Files | Grade | Critical Gaps |
|---|---|---|---|---|
| ellocharlie.com | 3 | 6 | D | No LICENSE, CI, tests, package.json |
| ellocharlie-agents | 1 | 75 | B+ | No AGENTS.md, PR/issue templates, multi-platform |
| ellocharlie-engine | 4 | 36 | C | No LICENSE, CI, tests, AGENTS.md, README |
| ellocharlie-content | 2 | 13 | D+ | No LICENSE, CI, expanded README |
| .github (org) | 1 | 1 | F | No templates, CODE_OF_CONDUCT, SECURITY, FUNDING |

**Target state:** Every repo at B+ or above, org-level defaults in place, ellocharlie-agents at A (Superpowers-parity on skill quality, agent instructions, and multi-platform distribution) — achievable in 4 focused weeks.

---

## 2. Repo-by-Repo Gap Analysis

---

### 2.1 `ellocharlie.com` — Landing Page

#### Strengths
- CLAUDE.md exists (agent context established)
- Static HTML/CSS/JS — minimal dependency surface
- Functional marketing site

#### Gaps

| Gap | Priority | Effort | Notes |
|---|---|---|---|
| `LICENSE` (MIT) | **P0** | 5 min | Legal blocker for any contribution |
| `package.json` with version field | **P0** | 30 min | Enables automated version bumping, npm scripts |
| `README.md` — comprehensive with badges | **P0** | 2 hr | Current state unknown; must link to live URL, describe stack, local dev, deploy |
| `.github/workflows/ci.yml` — lint + lighthouse | **P0** | 2 hr | No quality gate on HTML/CSS/JS today |
| `.gitignore` (Node + OS artifacts) | **P1** | 10 min | Prevents accidental junk commits |
| `CONTRIBUTING.md` | **P1** | 1 hr | Required for any external or AI contributor |
| `AGENTS.md` | **P1** | 2 hr | Superpowers-style agent-specific contributor guidelines |
| `CHANGELOG.md` | **P1** | 30 min | Start at 0.1.0, document current state |
| `.github/ISSUE_TEMPLATE/` (bug + feature + config.yml) | **P1** | 1 hr | Issue quality control |
| `.github/PULL_REQUEST_TEMPLATE.md` | **P1** | 1 hr | PR quality control |
| `CODE_OF_CONDUCT.md` or reference org-level | **P2** | 15 min | Can point to `.github` repo |
| Accessibility audit + remediation | **P2** | 4 hr | Production-grade landing page requirement |
| `SECURITY.md` or reference org-level | **P2** | 15 min | Responsible disclosure path |

**Estimated total effort: ~14 hours**

---

### 2.2 `ellocharlie-agents` — Skills Platform

#### Strengths
- 18 skills implemented
- `ecforge` CLI with documented commands
- `ARCHITECTURE.md` — structural clarity
- `ETHOS.md` — philosophical grounding
- `CONTRIBUTING.md` — exists and has substance
- `LICENSE` — MIT, present
- CI workflows — present
- CLAUDE.md — exists

#### Gaps

| Gap | Priority | Effort | Notes |
|---|---|---|---|
| `AGENTS.md` (Superpowers-quality) | **P0** | 4 hr | This is the most critical gap — no agent-specific contributor guidelines with quality gates, rejection criteria, and instruction for AI coding agents |
| `.github/PULL_REQUEST_TEMPLATE.md` | **P0** | 2 hr | Every PR must be validated against skill quality standards; no template = no gate |
| `.github/ISSUE_TEMPLATE/` (bug + feature + platform support + config.yml) | **P0** | 2 hr | Superpowers has 3 issue templates including platform-specific support |
| Skill file quality audit — frontmatter, pressure tests | **P0** | 8 hr | Each of 18 skills must have: `name`, `description`, `triggers`, `flow` (dot notation), and at minimum 3 pressure tests |
| Multi-platform support: `.claude-plugin` | **P1** | 3 hr | Claude plugin manifest — Superpowers first-class distribution path |
| Multi-platform support: `.cursor-plugin` | **P1** | 3 hr | Cursor plugin manifest |
| Multi-platform support: `.codex` | **P1** | 2 hr | OpenAI Codex configuration |
| Multi-platform support: `.opencode` | **P1** | 2 hr | OpenCode configuration |
| Multi-platform support: `gemini-extension.json` | **P1** | 2 hr | Gemini extension manifest |
| Slash commands — `brainstorm.md`, `execute-plan.md`, `write-plan.md` | **P1** | 3 hr | Superpowers command pattern for structured agent workflows |
| Session hooks — session-start, cursor hooks | **P1** | 2 hr | Superpowers hooks system for context injection at session start |
| `CHANGELOG.md` with semantic versioning | **P1** | 1 hr | No version history today |
| `package.json` or `.version-bump.json` | **P1** | 30 min | Automated version management |
| Plugin marketplace registration | **P2** | 4 hr | Once manifests are in place |
| Documentation site (GitHub Pages or equivalent) | **P2** | 8 hr | Superpowers has browsable skill docs |
| `SECURITY.md` or reference org-level | **P2** | 15 min | |

**Estimated total effort: ~47 hours**

---

### 2.3 `ellocharlie-engine` — Superrepo / Brain

#### Strengths
- Brain (Python) — core logic exists
- Dashboard — visual layer present
- `workspace.yaml` — configuration-as-code
- Agent configs — structured AI orchestration
- CLAUDE.md — agent context established
- MEMO.md + GROWTH.md — strategic documentation

#### Gaps

| Gap | Priority | Effort | Notes |
|---|---|---|---|
| `LICENSE` (MIT) | **P0** | 5 min | Legal blocker |
| `README.md` — comprehensive, linking all docs | **P0** | 3 hr | Must serve as the superrepo entry point — describe the entire system, link brain, dashboard, workspace.yaml, MEMO, GROWTH, and every doc |
| `.github/workflows/ci.yml` — pytest + lint | **P0** | 3 hr | No quality gate on brain Python code |
| `AGENTS.md` | **P0** | 4 hr | Agent-specific contributor guidelines for the most complex repo in the org |
| `CONTRIBUTING.md` | **P0** | 1.5 hr | Required before any contribution |
| Test suite — brain (pytest) | **P0** | 8 hr | Brain logic is untested; blocks production confidence |
| `.github/PULL_REQUEST_TEMPLATE.md` | **P1** | 1 hr | |
| `.github/ISSUE_TEMPLATE/` | **P1** | 1 hr | |
| `CHANGELOG.md` | **P1** | 30 min | |
| `.gitignore` (Python, env, OS) | **P1** | 10 min | `__pycache__`, `.env`, `venv/` must be excluded |
| Test suite — dashboard (smoke tests) | **P1** | 4 hr | Basic render and route validation |
| `CODE_OF_CONDUCT.md` or reference org-level | **P2** | 15 min | |
| `SECURITY.md` or reference org-level | **P2** | 15 min | |
| `pyproject.toml` or `requirements.txt` pinned | **P1** | 1 hr | Reproducible environments; if `requirements.txt` exists, audit for pins |

**Estimated total effort: ~27 hours**

---

### 2.4 `ellocharlie-content` — Blog Engine

#### Strengths
- 3 blog posts — content exists
- Backlog — editorial pipeline has structure
- Scripts — some automation present
- CLAUDE.md — agent context established

#### Gaps

| Gap | Priority | Effort | Notes |
|---|---|---|---|
| `LICENSE` (MIT) | **P0** | 5 min | |
| `README.md` — expanded | **P0** | 2 hr | Must describe blog structure, how to add posts, content conventions, frontmatter schema |
| `.github/workflows/ci.yml` — validate frontmatter + links | **P0** | 2 hr | Content CI: validate that every post has required frontmatter, no broken internal links |
| `CONTRIBUTING.md` | **P1** | 1 hr | Content contribution standards: post length, tone, frontmatter requirements |
| `AGENTS.md` | **P1** | 2 hr | How AI agents should create or edit content in this repo |
| `CHANGELOG.md` | **P1** | 30 min | |
| `.github/PULL_REQUEST_TEMPLATE.md` | **P1** | 45 min | Content PRs need a different template than code PRs — title, description, tags, SEO fields |
| `.github/ISSUE_TEMPLATE/` (content request + bug) | **P1** | 45 min | |
| `CODE_OF_CONDUCT.md` or reference | **P2** | 15 min | |
| Content frontmatter schema — enforced | **P1** | 1 hr | Define required fields (`title`, `date`, `author`, `tags`, `slug`, `description`) and validate in CI |
| `SECURITY.md` or reference | **P2** | 15 min | |

**Estimated total effort: ~10.5 hours**

---

### 2.5 `.github` — Org Profile

#### Strengths
- `profile/README.md` exists — org identity established

#### Gaps

| Gap | Priority | Effort | Notes |
|---|---|---|---|
| Default issue templates (bug, feature, platform support) | **P0** | 2 hr | These become org-wide defaults for any repo without its own; central governance |
| Default `PULL_REQUEST_TEMPLATE.md` | **P0** | 2 hr | Org-wide PR standard |
| `CODE_OF_CONDUCT.md` | **P0** | 30 min | Community health file — GitHub surfaces this automatically |
| `SECURITY.md` | **P0** | 30 min | Responsible disclosure — GitHub security advisory integration |
| `FUNDING.yml` | **P1** | 30 min | Enables GitHub Sponsors button on all repos |
| `profile/README.md` — expanded | **P1** | 2 hr | Currently unknown state; should describe the full org mission, link all repos, show contribution entry points |
| `SUPPORT.md` | **P2** | 30 min | Where to get help — Discord, GitHub Discussions, email |
| `GOVERNANCE.md` | **P2** | 1 hr | Decision-making process as the platform scales |

**Estimated total effort: ~9 hours**

---

## 3. Org-Level Gaps

These are gaps that transcend any single repo and require org-wide decisions and consistent enforcement.

### 3.1 Community Health Files

The `.github` repo is the org-wide default for community health files. Any repo that doesn't have its own `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, or issue templates will inherit them from `.github`. Currently, `.github` has none of these. This means the entire org has no responsible disclosure path, no community standards, and no issue quality gates.

**Resolution:** Populate `.github` first (Phase 1, Week 1). All other repos can then reference org-level files instead of duplicating them.

### 3.2 Commit Conventions

No commit convention is enforced or even documented across the org. The Superpowers benchmark uses strict conventional commits with a defined author identity. Without this, commit history is unreliable as a changelog source, automated version bumping is impossible, and PR review is harder.

**Resolution:** See Section 6 (Commit Standards). Add `commitlint` to CI for any repo with `package.json`; document the convention in every `CONTRIBUTING.md` and `AGENTS.md`.

### 3.3 CI/CD Coverage

Only `ellocharlie-agents` has CI workflows. Three repos have zero automated quality gates. This means code, content, and configuration are being committed with no lint, test, or build validation.

**Resolution:** Phase 2 adds CI to every repo. Minimum viable CI per repo type:
- **Static site (ellocharlie.com):** HTML validation, CSS lint, Lighthouse CI
- **Python (ellocharlie-engine):** `ruff` lint + `pytest`
- **Skills platform (ellocharlie-agents):** skill schema validation + existing CI hardening
- **Content (ellocharlie-content):** frontmatter validation, link checking

### 3.4 Testing Strategy

No testing strategy exists at the org level. `ellocharlie-engine`'s brain is untested Python. `ellocharlie.com` has no visual regression tests. `ellocharlie-agents` has no skill pressure testing (despite Superpowers having a complete pressure test framework per skill).

**Resolution:** See Phase 3. Adopt TDD as org standard. Document testing expectations in each repo's `CONTRIBUTING.md` and enforce via CI.

### 3.5 Release Process

No repo has a documented release process. No `CHANGELOG.md` files exist across the org. No version management (`package.json`, `.version-bump.json`, `pyproject.toml` with version). This means there is no reliable way to track what changed between deployments.

**Resolution:** Phase 2 adds automated release tooling. Phase 1 seeds `CHANGELOG.md` in every repo at the current state.

### 3.6 Documentation Standards

Documentation quality is inconsistent across the org. `ellocharlie-agents` has `ARCHITECTURE.md` and `ETHOS.md`. `ellocharlie-engine` has `MEMO.md` and `GROWTH.md`. No repo has a complete `README.md` that serves as an unambiguous entry point for a new contributor.

**Resolution:** Define and enforce a README standard (see Section 7 checklist). Every README must include: what the repo does, how to run it locally, how to contribute, links to all key docs, and status badges.

### 3.7 Security Policy

No repo has a `SECURITY.md`. No org-level security policy exists. GitHub will not surface a "Report a vulnerability" button without this. For a platform that runs AI agents with tool access, this is a material risk.

**Resolution:** Add `SECURITY.md` to `.github` repo (org-level default) in Week 1.

### 3.8 Branch Protection

No branch protection rules are documented or enforced. Without required PR reviews and required CI passing, any contributor (including AI agents) can push directly to `main`.

**Resolution:** Add branch protection rules as part of Phase 2. Require: 1 approving review, all CI checks passing, signed commits (where possible).

---

## 4. Quality Gaps vs. Superpowers

### 4.1 Skill File Quality

**Superpowers standard per skill:**
```
SKILL.md:
  - name: (machine-readable slug)
  - description: (one sentence, imperative voice)
  - triggers: (explicit list of when to invoke this skill)
  - flow: (dot notation diagram of execution steps)
  - pressure_tests: (minimum 3 adversarial test cases)
  - anti_patterns: (what NOT to do)
  - dependencies: (other skills or tools required)
```

**Current ellocharlie-agents state:**
- 18 skills exist — this is real value
- Skill file structure is likely inconsistent (mirrored from ObliviousOdin without audit)
- No confirmed frontmatter schema enforcement
- No documented pressure test requirements per skill
- No anti-patterns section

**Gap:** Every skill file must be audited against the Superpowers schema. Estimate 8 hours for full audit and remediation across 18 skills (avg 25 min/skill).

### 4.2 Agent Instruction Quality (CLAUDE.md Depth)

**Superpowers standard:**
CLAUDE.md / AGENTS.md explicitly defines:
- What an agent is allowed to do (permissions)
- What an agent must never do (prohibitions — hard rejections)
- Quality gates that will trigger a PR rejection
- The expected output format for each type of change
- How to handle ambiguity (escalate vs. proceed)
- Specific commit message format required
- Anti-slop measures (no vague commit messages, no placeholder TODOs, no "improvements" without specifics)

**Current ellocharlie org state:**
- CLAUDE.md exists in every repo — excellent
- But depth is unknown and likely insufficient for multi-agent collaboration
- No documented rejection criteria
- No anti-slop measures
- `ellocharlie-agents` is missing AGENTS.md entirely

**Gap:** Every CLAUDE.md must be reviewed and upgraded. AGENTS.md must be added to every repo with the full Superpowers-quality content. This is the single highest-leverage improvement available — it determines the quality of every future AI-generated contribution.

### 4.3 PR Process Rigor

**Superpowers PR template requires:**
- Summary of change (not "misc fixes")
- Motivation (why, not what)
- Type of change (checkboxes: bug fix, feature, breaking change, docs, refactor)
- Testing done (what tests were run, what passed)
- Screenshots (for UI changes)
- Checklist: docs updated, tests added, CHANGELOG updated, no TODOs left
- Anti-slop declaration (contributor confirms no LLM-generated filler)

**Current ellocharlie state:**
- No PR template in any repo
- No quality gate on PR descriptions
- AI agents can (and will) write vague, low-information PRs without constraints

**Gap:** Add `PULL_REQUEST_TEMPLATE.md` to every repo and to `.github` as the org-wide default. Template must be comprehensive and include the anti-slop checklist.

### 4.4 Testing Coverage

**Superpowers approach:**
- TDD applied to everything, including documentation
- Skill pressure tests are part of the skill definition — not optional
- CI fails if pressure tests are missing from a new skill PR

**Current ellocharlie state:**
- No tests in any repo except possibly `ellocharlie-agents` (CI exists but test content unknown)
- Brain (Python) is untested
- Dashboard is untested
- No skill pressure testing framework
- Content has no frontmatter validation CI

**Gap:** Testing is the largest single structural gap. Full remediation is a Phase 3 effort. The immediate action is to add CI skeletons that will fail clearly when tests are missing, creating pressure to add them.

### 4.5 Documentation Completeness

**Superpowers docs structure:**
```
docs/
  specs/
    YYYY-MM-DD-feature-name.md
  plans/
    YYYY-MM-DD-initiative.md
CHANGELOG.md
.version-bump.json
```

**Current ellocharlie state:**
- `ellocharlie-engine` has `docs/` with MEMO.md and GROWTH.md — good start
- No versioned specs or plans
- No CHANGELOG.md anywhere in the org
- No version management files

**Gap:** Establish the `docs/specs/` and `docs/plans/` pattern in `ellocharlie-engine`. Seed CHANGELOG.md in every repo. Add `.version-bump.json` and version field to every applicable config file.

### 4.6 Multi-Platform Distribution

**Superpowers:** Ships as a plugin for Claude, Cursor, Codex, OpenCode, and Gemini from the same source. This is what makes it a platform rather than a project.

**Current ellocharlie-agents:** Ships as `ecforge` CLI only. No plugin manifests for any AI coding environment.

**Gap:** Multi-platform support is a Phase 1/Phase 4 priority for `ellocharlie-agents`. The manifests are low-effort (JSON configuration files); the payoff is that the skills platform becomes natively available in every AI coding environment users already have.

---

## 5. The $30M Platform Roadmap

---

### Phase 1: Foundation (Week 1)
**Goal:** Every repo meets the minimum community health and documentation standard. No legal, contribution, or agent-instruction gaps remain.

**Owner:** cr_oot
**Success criteria:** All P0 items resolved. Every repo has LICENSE, README, CONTRIBUTING.md, AGENTS.md, CHANGELOG.md, and the `.github` org repo has all community health files.

#### Tasks

**`.github` org repo (do this first — it unlocks org-wide defaults)**

```
[ ] Add CODE_OF_CONDUCT.md (Contributor Covenant 2.1)
[ ] Add SECURITY.md (responsible disclosure, security@ellocharlie.com or GitHub advisory)
[ ] Add FUNDING.yml (GitHub Sponsors configuration)
[ ] Add SUPPORT.md (Discord, GitHub Discussions, email)
[ ] Add .github/ISSUE_TEMPLATE/bug_report.yml
[ ] Add .github/ISSUE_TEMPLATE/feature_request.yml
[ ] Add .github/ISSUE_TEMPLATE/config.yml (disable blank issues)
[ ] Add .github/PULL_REQUEST_TEMPLATE.md (comprehensive, anti-slop)
[ ] Expand profile/README.md (org mission, repo index, contribution entry points)
```

**All repos (parallel execution)**

```
[ ] ellocharlie.com — Add LICENSE (MIT)
[ ] ellocharlie.com — Add CONTRIBUTING.md
[ ] ellocharlie.com — Add AGENTS.md
[ ] ellocharlie.com — Add CHANGELOG.md (seed at 0.1.0)
[ ] ellocharlie.com — Add package.json with version field and npm scripts
[ ] ellocharlie.com — Rewrite README.md (comprehensive)
[ ] ellocharlie.com — Add .gitignore (Node + OS)

[ ] ellocharlie-agents — Add AGENTS.md (Superpowers-quality)
[ ] ellocharlie-agents — Add .github/PULL_REQUEST_TEMPLATE.md
[ ] ellocharlie-agents — Add .github/ISSUE_TEMPLATE/ (bug, feature, platform support, config.yml)
[ ] ellocharlie-agents — Add CHANGELOG.md
[ ] ellocharlie-agents — Add .version-bump.json

[ ] ellocharlie-engine — Add LICENSE (MIT)
[ ] ellocharlie-engine — Add CONTRIBUTING.md
[ ] ellocharlie-engine — Add AGENTS.md
[ ] ellocharlie-engine — Add CHANGELOG.md
[ ] ellocharlie-engine — Rewrite README.md (superrepo entry point)
[ ] ellocharlie-engine — Add .gitignore (Python + OS)
[ ] ellocharlie-engine — Verify/add pyproject.toml or pin requirements.txt

[ ] ellocharlie-content — Add LICENSE (MIT)
[ ] ellocharlie-content — Add CONTRIBUTING.md
[ ] ellocharlie-content — Add AGENTS.md
[ ] ellocharlie-content — Add CHANGELOG.md
[ ] ellocharlie-content — Expand README.md (post structure, frontmatter schema, how to contribute)
[ ] ellocharlie-content — Define and document frontmatter schema
```

**Estimated Phase 1 effort: ~35 hours**

---

### Phase 2: CI/CD (Week 2)
**Goal:** Every repo has automated quality gates. No untested code can merge to main. Branch protection is enforced.

**Owner:** cr_oot
**Success criteria:** All repos have at least one passing CI workflow. Branch protection enabled on main for all repos. Release automation in place for ellocharlie-agents.

#### Tasks

```
[ ] ellocharlie.com — .github/workflows/ci.yml (HTML validate + CSS lint + Lighthouse CI)
[ ] ellocharlie.com — .github/workflows/release.yml (tag → deploy)
[ ] ellocharlie.com — Enable branch protection (require CI pass + 1 review)

[ ] ellocharlie-agents — Harden existing CI (add commitlint, skill schema validation)
[ ] ellocharlie-agents — .github/workflows/release.yml (semantic-release or release-please)
[ ] ellocharlie-agents — .version-bump.json → automate CHANGELOG updates on release
[ ] ellocharlie-agents — Enable branch protection

[ ] ellocharlie-engine — .github/workflows/ci.yml (ruff lint + pytest, fail if no tests)
[ ] ellocharlie-engine — .github/workflows/release.yml
[ ] ellocharlie-engine — Enable branch protection

[ ] ellocharlie-content — .github/workflows/ci.yml (frontmatter validation + link checker)
[ ] ellocharlie-content — Enable branch protection

[ ] .github org — Configure org-level branch protection defaults where possible
[ ] All repos — Add CI status badges to README.md
```

**CI workflow template (Python — ellocharlie-engine):**
```yaml
name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install ruff
      - run: ruff check .
  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt pytest
      - run: pytest --tb=short
```

**CI workflow template (content — ellocharlie-content):**
```yaml
name: Content CI
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npx ts-node scripts/validate.ts
      - run: npx markdown-link-check posts/**/*.md
```

**Estimated Phase 2 effort: ~20 hours**

---

### Phase 3: Testing (Week 3)
**Goal:** Core logic is tested. Skills have pressure tests. Content has validation. No untested production code.

**Owner:** cr_oot
**Success criteria:** brain test coverage ≥ 80%, all 18 skills have ≥ 3 pressure tests, content validation CI blocks malformed posts.

#### Tasks

```
[ ] ellocharlie-engine — Write pytest test suite for brain (unit tests for core functions)
[ ] ellocharlie-engine — Write pytest test suite for agent config loading/validation
[ ] ellocharlie-engine — Add smoke tests for dashboard (basic render, route 200s)
[ ] ellocharlie-engine — Configure pytest-cov, add coverage report to CI
[ ] ellocharlie-engine — Add coverage badge to README.md

[ ] ellocharlie-agents — Audit all 18 skills for frontmatter completeness
[ ] ellocharlie-agents — Add pressure_tests section to each skill (≥ 3 per skill)
[ ] ellocharlie-agents — Build skill schema validation script (validates frontmatter schema)
[ ] ellocharlie-agents — Add skill schema validation to CI (fail on missing required fields)
[ ] ellocharlie-agents — Document pressure test format in CONTRIBUTING.md and AGENTS.md

[ ] ellocharlie-content — Enforce frontmatter schema validation in CI (title, date, author, tags, slug, description required)
[ ] ellocharlie-content — Add link checker to CI (markdown-link-check)
[ ] ellocharlie-content — Add reading time estimator / word count validator (optional, P2)

[ ] ellocharlie.com — Add Lighthouse CI with performance budget (score ≥ 90 on all categories)
[ ] ellocharlie.com — Add HTML validation (W3C validator or html-validate)
```

**Pressure test format (per skill, Superpowers-style):**
```markdown
## Pressure Tests

### PT-001: [Test name]
**Input:** [adversarial or edge-case trigger]
**Expected:** [specific, verifiable output]
**Anti-pattern avoided:** [what a bad implementation would do instead]

### PT-002: [Test name]
...

### PT-003: [Test name]
...
```

**Estimated Phase 3 effort: ~30 hours**

---

### Phase 4: Platform Polish (Week 4)
**Goal:** ellocharlie-agents is a fully multi-platform skills distribution system. The org has a documentation site. Slash commands and session hooks are operational.

**Owner:** cr_oot
**Success criteria:** Skills installable in Claude, Cursor, Codex, OpenCode, and Gemini via manifest files. Documentation site live. Slash commands operational in ecforge.

#### Tasks

```
[ ] ellocharlie-agents — Add .claude-plugin manifest (Claude plugin registration)
[ ] ellocharlie-agents — Add .cursor-plugin manifest (Cursor plugin registration)
[ ] ellocharlie-agents — Add .codex configuration (OpenAI Codex)
[ ] ellocharlie-agents — Add .opencode configuration (OpenCode)
[ ] ellocharlie-agents — Add gemini-extension.json (Gemini extension manifest)
[ ] ellocharlie-agents — Submit to Claude plugin marketplace
[ ] ellocharlie-agents — Submit to Cursor plugin marketplace

[ ] ellocharlie-agents — Add slash commands: commands/brainstorm.md
[ ] ellocharlie-agents — Add slash commands: commands/execute-plan.md
[ ] ellocharlie-agents — Add slash commands: commands/write-plan.md
[ ] ellocharlie-agents — Add session hooks: hooks/session-start.md
[ ] ellocharlie-agents — Add session hooks: hooks/cursor.md

[ ] ellocharlie-engine — Set up GitHub Pages or Cloudflare Pages for documentation site
[ ] ellocharlie-engine — Build docs index (auto-generate from skills + docs/ directory)
[ ] ellocharlie-engine — Add GOVERNANCE.md (decision-making as platform scales)

[ ] All repos — Final README audit (badges current, links valid, local dev works end-to-end)
[ ] All repos — Final CHANGELOG audit (all changes documented since repo inception)
[ ] All repos — Verify signed commits configured for cr_oot
```

**Plugin manifest template (.claude-plugin):**
```json
{
  "name": "ellocharlie-agents",
  "version": "1.0.0",
  "description": "18 production-grade agentic skills for software engineering workflows",
  "author": "cr_oot",
  "homepage": "https://github.com/ellocharlie/ellocharlie-agents",
  "skills_dir": "skills/",
  "entry": "ecforge",
  "license": "MIT"
}
```

**Estimated Phase 4 effort: ~25 hours**

---

### Roadmap Summary

| Phase | Focus | Duration | Effort | Key Deliverables |
|---|---|---|---|---|
| 1 | Foundation | Week 1 | ~35 hr | LICENSE + CONTRIBUTING + AGENTS + CHANGELOG in every repo; .github org defaults |
| 2 | CI/CD | Week 2 | ~20 hr | Quality gates on every repo; branch protection; release automation |
| 3 | Testing | Week 3 | ~30 hr | Brain test suite; skill pressure tests; content validation |
| 4 | Platform Polish | Week 4 | ~25 hr | Multi-platform plugin distribution; slash commands; hooks; docs site |
| **Total** | | **4 weeks** | **~110 hr** | **Org at production-grade, ellocharlie-agents at Superpowers-parity** |

---

## 6. Commit Standards

All contributors (human and AI) must follow these commit conventions across all ellocharlie repos.

### Convention: Conventional Commits (v1.0.0)

Format:
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to use |
|---|---|
| `feat` | New feature or capability (MINOR version bump) |
| `fix` | Bug fix (PATCH version bump) |
| `docs` | Documentation only (no code change) |
| `chore` | Maintenance: dependencies, config, tooling |
| `ci` | CI/CD workflow changes |
| `test` | Adding or modifying tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `style` | Formatting, whitespace (no logic change) |
| `perf` | Performance improvement |
| `revert` | Reverting a previous commit |

### Rules

1. **Type and description are mandatory.** No bare `git commit -m "stuff"`.
2. **Scope is recommended** — use the repo or module name: `feat(ecforge): add brainstorm command`
3. **Description is imperative, lowercase, no period.** `add LICENSE` not `Added LICENSE.`
4. **Body explains why, not what.** The diff shows what. The body explains the motivation.
5. **Breaking changes** use `BREAKING CHANGE:` in the footer, or `!` after the type: `feat!: rename ecforge command interface`
6. **One logical change per commit.** Do not bundle unrelated changes.
7. **Author:** `cr_oot` — configure globally: `git config --global user.name "cr_oot"`
8. **Signed commits** where possible: `git config --global commit.gpgsign true`
9. **No vague messages:** `fix: update things`, `chore: improvements`, `docs: changes` are rejected.
10. **AI agents must follow the same convention.** AGENTS.md in every repo must explicitly state this.

### Examples

```
feat(ecforge): add brainstorm slash command

Implements the /brainstorm command pattern from Superpowers.
Accepts a topic and returns a structured ideation output.

Closes #42
```

```
docs(ellocharlie-agents): add AGENTS.md with P0 contributor guidelines

Required for AI agent contribution quality gates. Includes:
- Permitted operations
- Hard rejection criteria  
- Anti-slop checklist
- Commit message requirements
```

```
ci(ellocharlie-engine): add pytest workflow with ruff lint

Adds .github/workflows/ci.yml. Runs on push and PR to main.
Fails on any lint error or test failure.
Coverage threshold: 80%.
```

### Enforcement

- Add `commitlint` to CI for repos with `package.json`
- Document in every repo's `CONTRIBUTING.md` and `AGENTS.md`
- Reference in `.github` PR template

---

## 7. File Checklist

The following files must exist in every repo. Use this as the acceptance checklist for Phase 1 completion.

### Universal (all repos)

```
[ ] README.md
    - What the repo does (1–3 sentences)
    - Local development setup (step by step)
    - How to contribute (link to CONTRIBUTING.md)
    - Links to all key docs (AGENTS.md, ARCHITECTURE.md, CHANGELOG.md, etc.)
    - Status badges (CI, version, license)

[ ] CLAUDE.md
    - Repo context for Claude/Claude Code
    - Key files to be aware of
    - What NOT to do in this repo
    - Preferred patterns and conventions

[ ] AGENTS.md
    - Agent-specific contributor guidelines (Superpowers-quality)
    - Permitted operations (what agents can do autonomously)
    - Hard prohibitions (what agents must never do)
    - Quality gates (what will cause a PR to be rejected)
    - Required commit message format
    - Anti-slop measures
    - How to handle ambiguity

[ ] CONTRIBUTING.md
    - How to set up local development
    - How to submit a PR
    - Code standards and style guide
    - Commit message format (reference Section 6)
    - PR checklist
    - Issue reporting guidelines

[ ] LICENSE
    - MIT License
    - Year and copyright holder: "cr_oot / ellocharlie"

[ ] CHANGELOG.md
    - Semantic versioning (MAJOR.MINOR.PATCH)
    - Unreleased section at top
    - Seeded with initial state at 0.1.0
    - Format: https://keepachangelog.com/en/1.1.0/

[ ] .gitignore
    - Language-appropriate (Node, Python, OS artifacts)
    - At minimum: .DS_Store, Thumbs.db, .env, node_modules/, __pycache__/, *.pyc, dist/, .venv/

[ ] .github/workflows/ci.yml
    - At minimum: lint + test
    - Runs on push and pull_request to main
    - Fails clearly with actionable output

[ ] .github/ISSUE_TEMPLATE/bug_report.yml
    - Structured YAML issue form
    - Required fields: description, steps to reproduce, expected behavior, actual behavior, environment

[ ] .github/ISSUE_TEMPLATE/feature_request.yml
    - Structured YAML issue form
    - Required fields: problem statement, proposed solution, alternatives considered

[ ] .github/ISSUE_TEMPLATE/config.yml
    - Disables blank issues
    - Links to relevant resources (docs, discussions)

[ ] .github/PULL_REQUEST_TEMPLATE.md
    - Summary (mandatory, not "misc fixes")
    - Motivation (why this change)
    - Type of change (checkboxes)
    - Testing done
    - Screenshots (for UI changes)
    - Checklist: docs updated, tests added, CHANGELOG updated, no open TODOs, anti-slop declaration
```

### `.github` Org Repo (additional)

```
[ ] CODE_OF_CONDUCT.md
    - Contributor Covenant 2.1
    - Enforcement contact

[ ] SECURITY.md
    - Supported versions table
    - How to report a vulnerability (private disclosure)
    - Response timeline commitment

[ ] FUNDING.yml
    - GitHub Sponsors configuration
    - Patreon / Open Collective if applicable

[ ] SUPPORT.md
    - Where to ask questions (GitHub Discussions preferred)
    - Where NOT to ask (do not open issues for support questions)
    - Response time expectations
```

### `ellocharlie-agents` (additional)

```
[ ] ARCHITECTURE.md — already exists; keep current
[ ] ETHOS.md — already exists; keep current
[ ] .version-bump.json — version management for release automation
[ ] commands/brainstorm.md — slash command definition
[ ] commands/execute-plan.md — slash command definition
[ ] commands/write-plan.md — slash command definition
[ ] hooks/session-start.md — session initialization hook
[ ] hooks/cursor.md — Cursor-specific hook
[ ] .claude-plugin — Claude plugin manifest
[ ] .cursor-plugin — Cursor plugin manifest
[ ] .codex — OpenAI Codex configuration
[ ] .opencode — OpenCode configuration
[ ] gemini-extension.json — Gemini extension manifest
[ ] Each skill in skills/ must have:
    [ ] name (frontmatter)
    [ ] description (frontmatter, one sentence, imperative)
    [ ] triggers (when to invoke)
    [ ] flow (dot notation execution diagram)
    [ ] pressure_tests (minimum 3)
    [ ] anti_patterns (what not to do)
```

### `ellocharlie-engine` (additional)

```
[ ] pyproject.toml or requirements.txt (pinned versions)
[ ] docs/specs/ directory (versioned technical specs)
[ ] docs/plans/ directory (versioned initiative plans)
[ ] tests/ directory with pytest suite
[ ] workspace.yaml — already exists; keep current
```

### `ellocharlie-content` (additional)

```
[ ] Content frontmatter schema document
[ ] scripts/validate.ts (or equivalent) — frontmatter + link validation
[ ] posts/ directory with consistent slug-based naming
```

---

## Appendix A: AGENTS.md Template

Use this template for every `AGENTS.md` created in Phase 1. Customize the repo-specific sections.

```markdown
# AGENTS.md — [Repo Name]
**For AI coding agents (Claude, Cursor, Codex, Gemini, et al.)**

This file defines the rules for AI agent contributions to this repository.
Read this before making any change. These rules are not suggestions.

---

## Permitted Operations

You may:
- Add new files following the patterns documented in CONTRIBUTING.md
- Edit existing files to fix bugs, improve documentation, or add features
- Open PRs for any of the above
- Run CI locally to verify your changes before committing

---

## Hard Prohibitions

You must never:
- Modify LICENSE, CODE_OF_CONDUCT.md, or SECURITY.md without explicit human approval
- Commit directly to main (all changes via PR)
- Leave TODO comments, placeholder text, or unfinished sections
- Write vague commit messages ("fix stuff", "update things", "improvements")
- Generate content that violates the Code of Conduct
- Delete or rename files without a corresponding update to all references
- Introduce new dependencies without explicit approval in the PR description

---

## Quality Gates

Your PR will be rejected if:
- [ ] The commit message does not follow Conventional Commits (see CONTRIBUTING.md §Commit Standards)
- [ ] You added code without tests (for code changes)
- [ ] You added a new skill without the required frontmatter and ≥ 3 pressure tests (ellocharlie-agents only)
- [ ] The PR description says "misc", "various", "improvements", "updates", or any other vague summary
- [ ] You left any `// TODO`, `# TODO`, `FIXME`, or `[placeholder]` in the code
- [ ] CI fails for any reason
- [ ] CHANGELOG.md was not updated

---

## Commit Message Format

```
<type>(<scope>): <description>
```

Types: feat, fix, docs, chore, ci, test, refactor, style, perf, revert
Description: imperative, lowercase, no period, ≤ 72 characters

Examples:
- `feat(ecforge): add brainstorm slash command`
- `fix(brain): handle empty agent config gracefully`
- `docs(readme): add local dev setup instructions`

---

## Handling Ambiguity

If requirements are unclear:
1. Check existing files for established patterns first
2. If still unclear, open an issue with the `question` label before proceeding
3. Do not guess and implement — incomplete implementations are worse than no implementation

---

## Repo-Specific Notes

[Customize for each repo: key files, critical patterns, things specific to this codebase]
```

---

## Appendix B: PR Template

Use this as `.github/PULL_REQUEST_TEMPLATE.md` in every repo and in `.github` as the org-wide default.

```markdown
## Summary

<!-- 
What does this PR do? Be specific. "Misc fixes" and "improvements" will result in an immediate request for changes.
One sentence minimum. Link the issue this closes if applicable.
-->

Closes #

## Motivation

<!--
Why is this change necessary? What problem does it solve?
The diff shows WHAT changed. This section explains WHY.
-->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] CI/CD change
- [ ] Refactor (no functional change)
- [ ] New skill (ellocharlie-agents only)

## Testing

<!--
What testing was done? What passed?
For new skills: list the pressure tests added and their results.
For code changes: describe what was tested and how.
-->

## Screenshots (if applicable)

<!-- UI changes require before/after screenshots -->

## Checklist

- [ ] My commit message follows Conventional Commits format
- [ ] I have updated CHANGELOG.md with a description of this change
- [ ] I have added or updated tests for my changes
- [ ] I have updated documentation (README, CONTRIBUTING, etc.) if needed
- [ ] CI passes locally (I have run the relevant checks)
- [ ] No open TODOs or placeholder text remains in my changes
- [ ] I have not introduced new dependencies without discussion

## Anti-Slop Declaration

- [ ] This PR description is written by me, not copied from a template without customization
- [ ] The summary is specific to this change, not a generic description
- [ ] All checkboxes above are accurate, not rubber-stamped
```

---

*Document version: 1.0.0 — April 8, 2026*
*Author: cr_oot*
*Benchmark reference: [obra/superpowers](https://github.com/obra/superpowers) (141K ★)*
