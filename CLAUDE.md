# CLAUDE.md — ellocharlie-engine

Instructions for Claude Code agents working in this repository.

---

## What This Repo Is

`ellocharlie-engine` is the controller/orchestrator monorepo for the ellocharlie GitHub org. It does not contain application code — it contains:

- **Agent configs** (`agents/*.yml`) — source of truth for all 5 AI agents
- **Workflow scripts** (`workflows/*.ts`) — Bun scripts that drive recurring operations
- **Index scripts** (`index/*.ts`) — build and publish the org-wide manifest
- **Submodule pointers** (`modules/`) — links to the actual product repos

Do not put product code here. If you're adding a feature to the site or agents runtime, work in the appropriate submodule.

---

## Working With This Repo

### Runtime

All scripts use **Bun**. Do not use Node.js APIs when Bun equivalents exist:

| Node | Bun preferred |
|------|---------------|
| `fs.readFileSync` | `await Bun.file(path).text()` |
| `fs.writeFileSync` | `await Bun.write(path, content)` |
| `JSON.parse(...)` | `await Bun.file(path).json()` |
| `process.env.X` | `Bun.env.X` |

### TypeScript

- Strict mode is assumed. Every function must have typed parameters and return types.
- Use `interface` for object shapes, `type` for unions/aliases.
- No `any`. Use `unknown` and narrow it.
- All async functions must be awaited — no floating promises.

### Imports

- Use ESM (`import`/`export`), never `require`.
- Prefer Bun built-ins and stdlib over npm packages for file I/O, HTTP, and path ops.
- The `type: "module"` flag is set in `package.json`.

---

## Agent Config Files (`agents/*.yml`)

These are the canonical definitions for each agent. They are read by:
1. `index/build-index.ts` (to build the manifest)
2. `modules/agents` runtime (to configure Claude sessions)

### When to edit agent configs

- **Add a skill**: Add the skill ID to the `skills` array. Ensure the skill is implemented in `modules/agents/skills/`.
- **Change schedule**: Edit the cron expression. Also update the corresponding GitHub Actions workflow in `.github/workflows/` if the agent is cron-triggered.
- **Add context sources**: Add a path relative to the repo root. The path must exist in one of the submodules or this repo.
- **Change escalation**: Must be a valid agent `codename` or `"human"`.

### Schema rules

- `codename` must be lowercase, no spaces (use hyphens).
- `model` must be a valid Anthropic model ID.
- `schedule` is either a cron expression string or one of: `on-demand`, `always-on`.
- `trigger` is a GitHub event name or a named trigger: `pull_request`, `deploy_request`, `alert`, `new_ticket`.

---

## Submodules

Submodules live in `modules/`. They are **separate repos** — do not commit changes to submodule files from this repo.

### Updating a submodule to latest

```bash
git submodule update --remote modules/<name>
git add modules/<name>
git commit -m "chore: bump <name> to latest"
```

### Checking submodule status

```bash
git submodule status
```

### Working inside a submodule

```bash
cd modules/agents
git checkout main
# make changes, commit, push
cd ../..
git add modules/agents
git commit -m "chore: bump agents submodule"
```

---

## Index Scripts

### `index/build-index.ts`

Reads submodule `package.json` and `README.md` files to build `index/manifest.json`.

- Run with: `bun run index:build`
- Output: `index/manifest.json` (committed to this repo)
- Should be run after bumping any submodule

### `index/gist-sync.ts`

Pushes `index/manifest.json` to a GitHub Gist as a public JSON endpoint.

- Run with: `GITHUB_TOKEN=... bun run index:sync`
- Requires `GITHUB_TOKEN` with `gist` scope
- Stores the Gist ID in `index/.gist-id` on first run
- Subsequent runs update the same Gist

---

## Workflows

### `workflows/daily-standup.ts`

Triggered by: `.github/workflows/daily-standup.yml` at 9am UTC weekdays.

Reads agent configs + output directories and produces `standup/YYYY-MM-DD.md`. Commit the output file after generation.

### `workflows/weekly-review.ts`

Triggered manually or on Fridays. Produces `reviews/YYYY-Www.md` aggregating the week's activity.

### `workflows/content-pipeline.ts`

Triggered by: `.github/workflows/content-pipeline.yml` Mon/Wed/Fri at 10am UTC.

Reads `modules/content/calendar/backlog.md`, picks the next topic, creates a draft file in `modules/content/blog-drafts/`, and updates the backlog status.

---

## GitHub Actions Workflows

Located in `.github/workflows/`. They use two secrets:

- `GITHUB_TOKEN` — auto-provided by GitHub Actions
- `ANTHROPIC_API_KEY` — must be set in repo Settings → Secrets

Do not hardcode secrets. Always read from environment variables.

---

## Commit Conventions

Follow Conventional Commits:

```
feat: add new agent skill config
fix: correct ops escalation target
chore: bump agents submodule
docs: update architecture diagram
ci: add weekly-review cron trigger
```

Scopes (optional): `agents`, `index`, `workflows`, `ci`, `modules`

---

## What Not to Do

- Do not add `npm install` steps — Bun handles dependencies.
- Do not put application secrets in agent YAML files — use env vars.
- Do not commit `index/manifest.json` with stale timestamps — always regenerate before committing.
- Do not add `node_modules/` — Bun manages its own cache.
- Do not create new agent configs without a corresponding entry in the README agent table.
- Do not modify submodule files directly from this repo's working tree.

---

## Adding a New Agent

1. Create `agents/<codename>.yml` following the schema in README.md.
2. Add the agent to the README agent table.
3. If cron-triggered, add a GitHub Actions workflow in `.github/workflows/`.
4. Run `bun run index:build` to regenerate the manifest.
5. Commit with `feat(agents): add <codename> agent`.

---

## Debugging

### Build index fails

Check that submodules are initialized:
```bash
git submodule update --init --recursive
```

### Gist sync fails

Check that `GITHUB_TOKEN` has `gist` scope:
```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/gists
```

### TypeScript errors

Run the type checker:
```bash
bun x tsc --noEmit
```

---

## Key File Paths

| Path | Purpose |
|------|---------|
| `agents/*.yml` | Agent definitions |
| `index/manifest.json` | Generated org state snapshot |
| `index/.gist-id` | Gist ID persisted after first sync |
| `modules/agents/docs/STACK-CONTEXT.md` | Stack context injected into most agents |
| `modules/agents/ARCHITECTURE.md` | Architecture doc injected into CTO |
| `modules/content/calendar/backlog.md` | Content topic backlog |
| `standup/` | Daily standup outputs |
| `reviews/` | Weekly review outputs |
