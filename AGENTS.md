# AGENTS.md

> This file is the standing order for every AI agent that touches this repository.
> Read it completely before writing a single line of code, opening a PR, or making any commit.

---

## If You Are an AI Agent — Stop. Read This First.

You are operating inside the **ellocharlie** GitHub organization. This is an agent-driven company built with a high quality bar and tight org discipline. Before you do anything:

1. **Read this file completely.** Every section applies to you.
2. **Read the repo's `CLAUDE.md`.** It contains repo-specific rules, patterns, and context that override general guidance.
3. **Read `workspace.yaml` in `ellocharlie-engine`.** It is the single source of truth for org identity, KPIs, OKRs, team structure, infrastructure, and repo ownership.
4. **Understand your scope.** You are working in one repo inside a multi-repo org. Changes with cross-repo implications require escalation to the appropriate agent or human.

If you are not willing to read those files before acting, stop here. Open a draft PR explaining what you were asked to do and why you could not proceed safely. Do not guess. Do not approximate. Do not "just try something and see."

This is not a warning. It is the quality standard.

---

## The Org Structure

ellocharlie is a five-agent, two-human company. Every repository is a node in a deliberate system.

### The Superrepo: `ellocharlie-engine`

The superrepo is [`ellocharlie-engine`](https://github.com/ellocharlie/ellocharlie-engine). It is the brain and orchestrator for the entire org:

- **Agent configs** live in `agents/*.yml` — these are canonical definitions for all five AI agents.
- **`workspace.yaml`** is the single source of truth for everything: org identity, team members (human and agent), repo URLs, KPIs, OKRs, and infrastructure topology.
- **Submodule pointers** in `modules/` link to all product repos.
- **Workflow scripts** in `workflows/` drive recurring operations (standup, content pipeline, weekly review).

Changes to agent behavior, schedules, or infrastructure topology go through the engine repo.

### The Repositories

| Repo | Type | Owner | Purpose |
|------|------|-------|---------|
| `ellocharlie-engine` | Controller | Nicholas | Superrepo — brain, dashboard, orchestrator, index |
| `ellocharlie.com` | Site | Growth agent | Static marketing landing page (HTML/CSS/JS) |
| `ellocharlie-agents` | Skills | CTO agent | Multi-agent runtime, 18 skills, ecforge CLI |
| `ellocharlie-content` | Content | Growth agent | Blog, case studies, changelog, docs (MDX pipeline) |

### The Five Agents

| Codename | Role | Schedule | Authority |
|----------|------|----------|-----------|
| `ceo` | Chief Executive Officer | Weekdays 9am UTC | Strategy, OKRs, positioning approval |
| `cto` | Chief Technology Officer | On PR trigger | Code review, architecture, tech accuracy |
| `growth` | Growth Lead | Mon/Wed/Fri 10am UTC | Content drafts, SEO, landing page copy |
| `cx-lead` | CX Lead | Always-on | Ticket triage, SLA enforcement, health scoring |
| `ops` | Operations Engineer | Always-on | Deploys, canary, infra, incident response |

Escalation chains: agents escalate to the codename listed in their `escalation:` field in the agent config, or to `"human"` for matters requiring judgment that no agent has authority to make.

---

## Before Making Changes

Work through this checklist in order. Do not skip steps.

- [ ] **Read `CLAUDE.md` for this repo.** It exists for a reason. Every line is intentional.
- [ ] **Read `workspace.yaml` in `ellocharlie-engine`.** Confirm the KPIs and OKRs relevant to your change. Reference them in your commit message if applicable.
- [ ] **Understand where this repo sits in the org.** Is it a submodule of the engine? Does it have downstream dependencies? Are you working in the right place?
- [ ] **Search open issues and PRs.** Is this already being worked on? Is there an existing issue tracking this problem?
- [ ] **Confirm the scope of your change.** A change in `ellocharlie-content` that affects frontmatter schema might require updates to the validation script and the build script in the same repo. A change in `ellocharlie-engine` agent configs always requires running `bun run index:build`.
- [ ] **Verify the author is configured.** Every commit must have a real, identifiable author — not `agent@example.com`, not blank, not a GitHub Actions bot email unless that bot is an authorized agent.
- [ ] **Confirm tests exist or write them.** If the repo has a test suite and your change affects logic, tests must pass before you open a PR.
- [ ] **Confirm the change is complete.** Do not open a PR with known broken behavior, TODOs in critical paths, or "I'll fix this later" comments in shipped code.

---

## Commit Standards

ellocharlie uses **Conventional Commits**. Every commit must follow this format:

```
<type>(<optional scope>): <description>

[optional body]

[optional footer — e.g., Closes #42, [kpi.cx.nps_target]]
```

### Types

| Type | Use |
|------|-----|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `docs` | Documentation only — no code changes |
| `chore` | Maintenance, dependency bumps, config changes |
| `ci` | Changes to GitHub Actions, cron jobs, workflow files |
| `refactor` | Code restructuring with no behavior change |
| `test` | Adding or updating tests |
| `perf` | Performance improvement |
| `content` | New or updated content (ellocharlie-content only) |
| `review` | Content review approval (ellocharlie-content only) |

### Scopes (repo-specific)

**ellocharlie-engine:** `agents`, `index`, `workflows`, `ci`, `modules`, `brain`, `dashboard`

**ellocharlie.com:** `layout`, `copy`, `style`, `seo`, `a11y`, `dark-mode`

**ellocharlie-agents:** `skills`, `cli`, `runtime`, `config`, `tests`

**ellocharlie-content:** `blog`, `docs`, `case-studies`, `changelog`, `calendar`, `scripts`

### Rules

- **One logical change per commit.** Do not bundle unrelated changes. If you need to fix a typo and add a feature, that is two commits.
- **Present tense, imperative mood.** `add ceo agent config`, not `added ceo agent config` or `adds ceo agent config`.
- **No period at the end** of the subject line.
- **Subject line ≤ 72 characters.** Body lines ≤ 100 characters.
- **Reference KPIs/OKRs when applicable.** If a commit implements work against a measurable target in `workspace.yaml`, call it out in the footer: `[cx.nps_target]`, `[content.blog_cadence]`, etc.
- **Author must be configured** with a real name and email. Commits without identifiable authors will be rejected.

### Examples

```
feat(agents): add cx escalation skill for NPS < 7 trigger [cx.nps_target]

Implements the escalation path when a customer survey response falls
below 7. Fires a webhook to the cx-lead agent and creates an Attio
task with the customer context.

Closes #34
```

```
fix(skills): correct ops canary rollback threshold

Canary was rolling back at 3% error rate instead of the configured 5%.
Updated the threshold check in canary.ts and added a test for
edge case at exactly 5%.
```

```
content: draft why-your-crm-goes-dark-after-the-sale [content.blog_cadence]
```

```
chore: bump content submodule to latest — 3 posts published [content.blog_cadence]
```

---

## What We Will Not Accept

These patterns result in immediate PR rejection, no exceptions:

### Slop PRs
A PR that is clearly the product of an AI agent running without genuine understanding of the problem. Indicators: vague description ("updated some files"), no issue reference when one clearly exists, changes that don't cohere into a single logical unit, copy-pasted boilerplate that doesn't fit the context.

### Speculative Fixes
Changing code "just in case" or "for good measure" without a specific, verifiable reason. Every line changed must have a documented purpose. If you can't explain in one sentence why a specific line needed to change, it should not be in the PR.

### Bulk Changes Without Context
PRs that touch many files across many subsystems without a clear throughline. Refactors that weren't discussed. Dependency upgrades without upgrade notes and test confirmation.

### Domain-Specific Additions to Core Repos
Adding `ellocharlie-content`-specific logic to `ellocharlie-engine`. Adding product-specific code to the site repo that belongs in the app. Adding site copy to the agents runtime. Every file has a home — put it there.

### Changes Without Tests (Where Tests Are Expected)
If the repo has a test suite and your change is testable, tests are required. "I couldn't figure out how to write the test" is not a reason to skip tests — it is a reason to open a discussion issue first.

### Hardcoded Secrets or Credentials
Any file containing an API key, token, password, or credential in plaintext, regardless of whether the credential appears valid. This includes `.env` files committed to the repo.

### Fabricated Content
Invented customer names, fabricated metrics, hallucinated product features, or any claim that could mislead a reader or a downstream agent. Content must be factual. Cite sources.

### Broken Canonical State
Leaving `index/manifest.json` stale after changing agent configs, leaving `content-manifest.json` stale after adding content, leaving submodule pointers uncommitted after bumping a submodule.

---

## Quality Bar

Every change merged to `main` must clear all of these:

### 1. Clear Purpose
What is this change for? The answer must fit in one sentence and must be verifiable. "Improve code quality" is not a purpose. "Fix the canary rollback threshold that was triggering at the wrong error rate" is a purpose.

### 2. Tested Where Applicable
If the repo has tests: they pass. If the change affects logic that could break: there is a test that would catch it. If no tests exist yet and this is new logic: you added them.

### 3. Follows Existing Patterns
Read five existing files in the same subsystem before writing a new one. The code you write should be indistinguishable in style from the code already there. Do not introduce a new pattern without documenting why the existing one was insufficient.

### 4. References the Relevant KPI/OKR (When Applicable)
If a commit or PR implements work against a KPI or OKR in `workspace.yaml`, reference it. This is how the org tracks whether autonomous agent work is advancing the company's real goals.

### 5. Single Logical Change
One PR, one purpose. If you discover a related fix while working on something else, that fix gets its own branch and its own PR.

### 6. Human-Reviewable
The diff must be readable by a human in a reasonable amount of time. A 47-file PR that rewrites the entire index system is not reviewable — it needs to be broken down.

### 7. Complete
No half-finished features. No `TODO: fix this later` in shipped code paths. No known failing tests with a comment saying "will fix in follow-up." If it's not done, it doesn't merge.

---

## Author Configuration

Every commit must be authored by an identifiable entity. Configure git correctly before committing:

### For human contributors
```bash
git config user.name "Your Name"
git config user.email "your@email.com"
```

### For agent commits (cr_oot)
Agent commits in the ellocharlie org are made by `cr_oot`. The author block will be configured by the orchestration layer. Do not override it.

### For other AI agents
If you are an AI agent committing on behalf of a human, the commit must clearly indicate this. The recommended pattern is to set the author as the human and add a `Co-authored-by:` trailer for the agent:

```
Co-authored-by: Claude (Anthropic) <claude@anthropic.com>
```

---

## Cross-Repo Changes

Some changes have effects that span multiple repos. These require extra care:

- **Agent config changes** in `ellocharlie-engine` → run `bun run index:build` → commit the updated manifest.
- **Submodule bumps** in `ellocharlie-engine` → verify the submodule's own tests pass before bumping.
- **Frontmatter schema changes** in `ellocharlie-content` → update `scripts/validate.ts` and `scripts/build.ts` in the same PR.
- **API endpoint changes** in `ellocharlie-agents` → check if `ellocharlie-engine` workflows reference the affected endpoints.
- **Pricing or messaging changes** in `ellocharlie.com` → must align with `workspace.yaml` and require CEO agent approval on positioning.

When in doubt: open an issue describing the cross-repo impact and wait for a human or the CEO agent to confirm scope before proceeding.

---

## Escalation

If you encounter a situation where you cannot proceed safely — ambiguous requirements, conflicting instructions, missing context, or a change that exceeds your authorized scope — escalate. Do not guess.

The escalation chain:
1. Check the agent config's `escalation:` field for the appropriate agent to contact.
2. If the escalation agent cannot resolve it either, the chain terminates at `human`.
3. Open a GitHub Issue tagged with `needs-human-review` and describe exactly what you encountered, what you tried, and what decision needs to be made.

**Never proceed with a change you are not confident is correct.** A partial, honest escalation is better than a confident, wrong commit.

---

*This file is part of the ellocharlie org foundation. It applies to every repository in the org. Repo-specific rules in `CLAUDE.md` extend and override this file where they conflict. If you find guidance in this file that conflicts with `CLAUDE.md`, `CLAUDE.md` wins.*
