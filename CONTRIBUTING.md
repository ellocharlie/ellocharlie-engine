# Contributing to ellocharlie

Thank you for your interest in contributing. This guide explains how to report bugs, suggest features, and submit changes across the ellocharlie org.

All repositories in the ellocharlie GitHub organization are governed by the same standards. Read this guide once — it applies everywhere.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Report a Bug](#how-to-report-a-bug)
- [How to Suggest a Feature](#how-to-suggest-a-feature)
- [How to Submit Changes](#how-to-submit-changes)
- [Commit Message Format](#commit-message-format)
- [Code Review Process](#code-review-process)
- [Testing Requirements](#testing-requirements)
- [License](#license)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold it. Report unacceptable behavior to [hello@ellocharlie.com](mailto:hello@ellocharlie.com).

---

## How to Report a Bug

**Before opening a bug report:**

1. Check the [open issues](../../issues) to see if the bug has already been reported.
2. Check the [CHANGELOG](CHANGELOG.md) to see if it was recently fixed.
3. If you believe you've found a **security vulnerability**, do not open a public issue — see [SECURITY.md](SECURITY.md) instead.

**To report a bug:**

1. Go to the **Issues** tab in the relevant repository.
2. Click **New issue** and select the **Bug Report** template.
3. Fill in all sections of the template as completely as you can. Incomplete reports are harder to act on.
4. Include:
   - A clear description of what happened versus what you expected
   - Steps to reproduce (the more specific, the faster we can fix it)
   - Your environment (OS, browser if applicable, relevant version numbers)
   - Any error logs or screenshots that help explain the problem

We triage new issues within one business day. Bugs with clear reproduction steps are prioritized.

---

## How to Suggest a Feature

**Before opening a feature request:**

1. Search [open issues](../../issues) to see if the feature has already been requested.
2. Check the [project roadmap](https://github.com/ellocharlie/ellocharlie-engine/blob/main/workspace.yaml) to see if it aligns with current OKRs.

**To suggest a feature:**

1. Go to the **Issues** tab in the relevant repository.
2. Click **New issue** and select the **Feature Request** template.
3. Describe the problem the feature would solve (not just the solution you envision). The clearer the problem statement, the more useful the discussion.
4. Include:
   - What problem this solves and who it affects
   - Your proposed solution
   - Any alternatives you've considered
   - Mockups, diagrams, or references if you have them

Features are evaluated against the org's current OKRs and KPIs in `workspace.yaml`. A technically excellent feature request that doesn't advance current priorities will be labeled `backlog` and revisited later — that's not a rejection, it's prioritization.

---

## How to Submit Changes

### Prerequisites

- A GitHub account
- Familiarity with [Git](https://git-scm.com/) and [GitHub pull requests](https://docs.github.com/en/pull-requests)
- Bun installed (`>=1.0`) if contributing to TypeScript repos
- Python (`>=3.11`) if contributing to the brain service in `ellocharlie-engine`

### Step-by-step

**1. Fork the repository**

Click **Fork** at the top-right of the repository page. This creates your own copy under your GitHub account.

**2. Clone your fork**

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

**3. Create a branch**

Branch names should be descriptive and follow this convention:

```
<type>/<short-description>
```

Examples:
```bash
git checkout -b feat/add-cx-escalation-webhook
git checkout -b fix/canary-rollback-threshold
git checkout -b docs/update-agent-config-schema
```

Branch types mirror commit types: `feat`, `fix`, `docs`, `chore`, `ci`, `refactor`, `test`, `content`.

**4. Read the repo's `CLAUDE.md`**

Every repository has a `CLAUDE.md` with repo-specific conventions, architecture decisions, and patterns. Read it before writing code. The patterns documented there are intentional.

**5. Make your changes**

- Follow the existing code style — read five nearby files before writing your own.
- Add or update tests for any logic changes (see [Testing Requirements](#testing-requirements)).
- Update documentation if your change affects how something works.
- Keep each commit focused on one logical change.

**6. Run the test suite**

```bash
# TypeScript repos
bun test

# Python (brain service)
cd brain && pytest

# Content repo
bun run validate
```

All tests must pass before you open a PR. A CI failure on an open PR blocks review.

**7. Push and open a pull request**

```bash
git push origin feat/your-branch-name
```

Then open a pull request from your fork to the `main` branch of the original repo. Use the pull request template — it exists to make reviews faster.

**8. Respond to review feedback**

Reviewers may request changes. Address feedback by pushing new commits to the same branch. Do not force-push or rebase after a review has started — it makes the diff harder to follow. Squash at merge, not before.

---

## Commit Message Format

All commits in the ellocharlie org follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<optional scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `chore` | Maintenance, deps, config |
| `ci` | GitHub Actions, workflow changes |
| `refactor` | Code restructure, no behavior change |
| `test` | Adding or updating tests |
| `perf` | Performance improvement |
| `content` | New or updated content (content repo) |

### Rules

- **Subject line:** present tense, imperative mood, ≤ 72 characters, no trailing period
- **One commit per logical change:** don't bundle unrelated changes
- **Reference issues:** use `Closes #42` in the footer to auto-close issues on merge
- **Reference KPIs where relevant:** use `[kpi.metric_name]` footer notation to tie work to `workspace.yaml` targets

### Examples

```
feat(agents): add cx escalation webhook for NPS < 7 [cx.nps_target]

Closes #34
```

```
fix: correct canary rollback threshold in ops skill

Was rolling back at 3% error rate instead of the configured 5%.
Updated the check and added a boundary condition test.
```

```
docs: add submodule workflow to CLAUDE.md
```

---

## Code Review Process

Every PR requires at least one approving review before merge. The responsible reviewer depends on what changed:

| Changed area | Reviewer |
|-------------|----------|
| Agent configs, `workspace.yaml`, brain service | Nicholas (human) or CEO agent |
| TypeScript scripts, workflows, index | CTO agent |
| Marketing copy, landing page | Growth agent + Nicholas |
| Content (blog, docs, case studies) | CTO (technical accuracy) or CEO (positioning) |
| CI/CD, GitHub Actions | CTO agent or Ops agent |
| Cross-repo changes | Nicholas (human) |

**Review SLA:** PRs are reviewed within one business day. If your PR has been open for more than 48 hours without any response, ping in the issue or add the `needs-review` label.

**What reviewers look for:**

- Does the change do what the PR description says it does?
- Does the code follow existing patterns?
- Are tests present and passing?
- Is the commit history clean and readable?
- Does the PR template checklist reflect the actual state of the PR?

**Reviewers will not:**
- Accept PRs that mix multiple unrelated changes
- Accept PRs without a description
- Approve code they haven't actually read
- Skip testing for "trivial" changes — every change can break something

---

## Testing Requirements

### TypeScript repos (`ellocharlie-engine`, `ellocharlie-agents`)

- Use Bun's built-in test runner: `bun test`
- Test files live in `__tests__/` or alongside the file as `*.test.ts`
- All new logic must have at least one test
- Edge cases must be tested — especially boundary conditions and error paths

### Content repo (`ellocharlie-content`)

- Run `bun run validate` to check all MDX frontmatter before opening a PR
- The 11-point validation check must pass with zero errors

### Site repo (`ellocharlie.com`)

- Manual visual review across light mode, dark mode, and mobile viewport
- Run the browser's accessibility checker (Lighthouse or axe) — no new accessibility violations
- Verify all links are valid

### General rules

- Do not submit a PR with known failing tests, even if "it's just a flaky test"
- Do not comment out tests to make CI pass
- If you discover a pre-existing broken test, open a separate issue rather than including a fix in an unrelated PR

---

## License

By submitting a contribution, you agree that your contribution is licensed under the [MIT License](LICENSE) that covers this repository. You confirm that you have the right to submit it under that license.

---

*Questions? Open an issue or email [hello@ellocharlie.com](mailto:hello@ellocharlie.com).*
