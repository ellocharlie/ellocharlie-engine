# Technical Specifications

Versioned technical specifications for ellocharlie platform features.

Specs are written before implementation begins and updated as decisions evolve. Each spec defines the architecture, schema, API contracts, and implementation roadmap for a discrete platform feature or system.

---

| Date | Spec | Status |
|------|------|--------|
| 2026-04-08 | [Phase 1: CX Platform](../PHASE1-CX-PLATFORM.md) | In Progress |

---

## Adding a Spec

1. Write the spec as a Markdown file in `docs/specs/` with the naming convention `YYYY-MM-DD-slug.md`.
2. Add a row to the table above with the date, a linked title, and status (`Draft` / `In Progress` / `Complete` / `Superseded`).
3. Link to the spec from the relevant `AGENTS.md` or `CLAUDE.md` so agents have context when acting in scope.

## Spec Template

```markdown
# [Feature Name] Technical Specification

**Version:** 1.0
**Date:** YYYY-MM-DD
**Author:** [name or agent codename]
**Status:** Draft | In Progress | Complete

---

## 1. Overview
## 2. Architecture
## 3. Schema / API Contracts
## 4. Implementation Roadmap
## 5. Open Questions
```
