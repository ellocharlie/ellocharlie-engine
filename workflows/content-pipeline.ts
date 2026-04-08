/**
 * workflows/content-pipeline.ts
 *
 * Orchestrates the 4-stage content generation pipeline:
 *   1. growth  → draft
 *   2. cto     → technical review
 *   3. ceo     → positioning review
 *   4. ops     → publish
 *
 * Reads the content topic backlog from:
 *   modules/content/calendar/backlog.md
 *
 * Picks the next pending topic and advances it through pipeline stages
 * by writing/updating draft files with YAML frontmatter stage markers.
 *
 * Usage: bun run content
 */

import { readdir, mkdir } from "node:fs/promises";
import { join, resolve, basename } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type PipelineStage =
  | "backlog"
  | "draft"
  | "technical-review"
  | "positioning-review"
  | "ready-to-publish"
  | "published";

interface BacklogTopic {
  title: string;
  slug: string;
  stage: PipelineStage;
  assignedAgent: string;
  priority: number;
  tags: string[];
  raw: string;
}

interface DraftFrontmatter {
  title: string;
  slug: string;
  stage: PipelineStage;
  assignedAgent: string;
  tags: string[];
  created: string;
  updated: string;
  reviewedBy: string[];
}

interface PipelineResult {
  topic: string;
  slug: string;
  previousStage: PipelineStage;
  nextStage: PipelineStage;
  assignedTo: string;
  draftPath: string;
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const ROOT = resolve(import.meta.dir, "..");
const CONTENT_DIR = join(ROOT, "modules", "content");
const BACKLOG_PATH = join(CONTENT_DIR, "calendar", "backlog.md");
const DRAFTS_DIR = join(CONTENT_DIR, "blog-drafts");
const SOCIAL_DIR = join(CONTENT_DIR, "social-posts");

/** Pipeline stage order and agent assignments. */
const PIPELINE_STAGES: { stage: PipelineStage; agent: string; label: string }[] = [
  { stage: "backlog", agent: "growth", label: "Backlog" },
  { stage: "draft", agent: "cto", label: "Draft (growth → awaiting CTO review)" },
  { stage: "technical-review", agent: "ceo", label: "Technical Review (CTO → awaiting CEO review)" },
  { stage: "positioning-review", agent: "ops", label: "Positioning Review (CEO → awaiting publish)" },
  { stage: "ready-to-publish", agent: "ops", label: "Ready to Publish" },
  { stage: "published", agent: "ops", label: "Published" },
];

function getNextStage(current: PipelineStage): PipelineStage {
  const idx = PIPELINE_STAGES.findIndex((s) => s.stage === current);
  if (idx === -1 || idx >= PIPELINE_STAGES.length - 1) return "published";
  return PIPELINE_STAGES[idx + 1]!.stage;
}

function getStageAgent(stage: PipelineStage): string {
  return PIPELINE_STAGES.find((s) => s.stage === stage)?.agent ?? "ops";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function readFileSafe(path: string): Promise<string | null> {
  try {
    return await Bun.file(path).text();
  } catch {
    return null;
  }
}

function toSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60);
}

function serializeFrontmatter(fm: DraftFrontmatter): string {
  const lines = [
    "---",
    `title: "${fm.title}"`,
    `slug: ${fm.slug}`,
    `stage: ${fm.stage}`,
    `assignedAgent: ${fm.assignedAgent}`,
    `tags: [${fm.tags.map((t) => `"${t}"`).join(", ")}]`,
    `created: ${fm.created}`,
    `updated: ${fm.updated}`,
    `reviewedBy: [${fm.reviewedBy.map((r) => `"${r}"`).join(", ")}]`,
    "---",
  ];
  return lines.join("\n");
}

function parseFrontmatter(content: string): { fm: Partial<DraftFrontmatter>; body: string } {
  if (!content.startsWith("---")) return { fm: {}, body: content };

  const endIdx = content.indexOf("\n---\n", 4);
  if (endIdx === -1) return { fm: {}, body: content };

  const fmBlock = content.slice(4, endIdx);
  const body = content.slice(endIdx + 5);
  const fm: Partial<DraftFrontmatter> = {};

  for (const line of fmBlock.split("\n")) {
    const match = line.match(/^(\w+):\s*(.*)$/);
    if (!match) continue;
    const [, key, value] = match;
    const trimmed = value?.trim() ?? "";

    if (key === "stage") fm.stage = trimmed as PipelineStage;
    else if (key === "title") fm.title = trimmed.replace(/^"|"$/g, "");
    else if (key === "slug") fm.slug = trimmed;
    else if (key === "assignedAgent") fm.assignedAgent = trimmed;
    else if (key === "created") fm.created = trimmed;
    else if (key === "updated") fm.updated = trimmed;
    else if (key === "tags") {
      fm.tags = trimmed
        .replace(/^\[|\]$/g, "")
        .split(",")
        .map((t) => t.trim().replace(/^"|"$/g, ""))
        .filter(Boolean);
    } else if (key === "reviewedBy") {
      fm.reviewedBy = trimmed
        .replace(/^\[|\]$/g, "")
        .split(",")
        .map((t) => t.trim().replace(/^"|"$/g, ""))
        .filter(Boolean);
    }
  }

  return { fm, body };
}

// ---------------------------------------------------------------------------
// Backlog parsing
// ---------------------------------------------------------------------------

/**
 * Parse the backlog.md file.
 * Expected format: markdown list items with stage badges, e.g.:
 *
 *   - [backlog] How to build an agent-driven company #startup #agents
 *   - [draft] Using Neon Postgres for serverless apps #postgres #neon
 */
function parseBacklog(content: string): BacklogTopic[] {
  const topics: BacklogTopic[] = [];
  const lines = content.split("\n");
  let priority = 0;

  for (const line of lines) {
    const match = line.match(/^[-*]\s+\[(\w[\w-]*)\]\s+(.+)$/);
    if (!match) continue;

    const [, stageRaw, rest] = match;
    const stage = (stageRaw as PipelineStage) ?? "backlog";

    // Extract tags (#tag)
    const tags = [...rest.matchAll(/#(\w+)/g)].map((m) => m[1]!);
    const title = rest.replace(/#\w+/g, "").trim();
    const slug = toSlug(title);

    topics.push({
      title,
      slug,
      stage,
      assignedAgent: getStageAgent(stage),
      priority: priority++,
      tags,
      raw: line,
    });
  }

  return topics;
}

/** Create a minimal default backlog if one doesn't exist. */
function defaultBacklog(): string {
  return `# Content Backlog

Topics are listed in priority order. Format:
  - [stage] Topic title #tag1 #tag2

Stages: backlog → draft → technical-review → positioning-review → ready-to-publish → published

---

- [backlog] How we built a 5-person company powered by AI agents #agents #startup
- [backlog] Why we chose Neon Postgres for serverless database ops #postgres #neon #infrastructure
- [backlog] Astro 5 for marketing sites: what we learned #astro #webdev
- [backlog] CX automation without losing the human touch #cx #agents #support
- [backlog] Canary deployments on Google Cloud Run #deployment #gcr #devops
`;
}

// ---------------------------------------------------------------------------
// Draft management
// ---------------------------------------------------------------------------

async function findExistingDraft(slug: string): Promise<string | null> {
  try {
    const entries = await readdir(DRAFTS_DIR);
    const match = entries.find((f) => f.includes(slug));
    return match ? join(DRAFTS_DIR, match) : null;
  } catch {
    return null;
  }
}

async function createDraft(topic: BacklogTopic): Promise<string> {
  const now = new Date().toISOString();
  const filename = `${now.split("T")[0]}-${topic.slug}.md`;
  const path = join(DRAFTS_DIR, filename);

  const fm: DraftFrontmatter = {
    title: topic.title,
    slug: topic.slug,
    stage: "draft",
    assignedAgent: "growth",
    tags: topic.tags,
    created: now,
    updated: now,
    reviewedBy: [],
  };

  const body = `
## Brief

_[Growth agent: expand this into a full blog post. Target 1,200–1,800 words. SEO-optimized for the primary keyword derived from the title. Include an intro, 3–5 H2 sections, and a CTA.]_

## Outline

- Introduction
- Section 1
- Section 2
- Section 3
- Conclusion & CTA

## Draft

_[Content goes here]_
`;

  const content = serializeFrontmatter(fm) + "\n" + body;
  await mkdir(DRAFTS_DIR, { recursive: true });
  await Bun.write(path, content);
  return path;
}

async function advanceDraft(draftPath: string): Promise<{ previousStage: PipelineStage; nextStage: PipelineStage; assignedTo: string }> {
  const raw = await Bun.file(draftPath).text();
  const { fm, body } = parseFrontmatter(raw);

  const previousStage = fm.stage ?? "draft";
  const nextStage = getNextStage(previousStage);
  const assignedTo = getStageAgent(nextStage);
  const now = new Date().toISOString();

  const reviewedBy = fm.reviewedBy ?? [];
  if (previousStage !== "backlog" && !reviewedBy.includes(fm.assignedAgent ?? "")) {
    reviewedBy.push(fm.assignedAgent ?? "unknown");
  }

  const updatedFm: DraftFrontmatter = {
    title: fm.title ?? "Untitled",
    slug: fm.slug ?? toSlug(fm.title ?? "untitled"),
    stage: nextStage,
    assignedAgent: assignedTo,
    tags: fm.tags ?? [],
    created: fm.created ?? now,
    updated: now,
    reviewedBy,
  };

  const updatedContent = serializeFrontmatter(updatedFm) + "\n" + body;
  await Bun.write(draftPath, updatedContent);

  return { previousStage, nextStage, assignedTo };
}

// ---------------------------------------------------------------------------
// Backlog update
// ---------------------------------------------------------------------------

function updateBacklogLine(content: string, oldLine: string, newStage: PipelineStage): string {
  const updatedLine = oldLine.replace(/\[\w[\w-]*\]/, `[${newStage}]`);
  return content.replace(oldLine, updatedLine);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  console.log("📝 Running content pipeline...");

  // Ensure directories exist
  await mkdir(join(CONTENT_DIR, "calendar"), { recursive: true });
  await mkdir(DRAFTS_DIR, { recursive: true });
  await mkdir(SOCIAL_DIR, { recursive: true });

  // Load backlog
  let backlogContent = await readFileSafe(BACKLOG_PATH);
  if (!backlogContent) {
    console.log("  Backlog not found — creating default backlog");
    backlogContent = defaultBacklog();
    await Bun.write(BACKLOG_PATH, backlogContent);
  }

  const topics = parseBacklog(backlogContent);
  console.log(`  Found ${topics.length} topics in backlog`);

  if (topics.length === 0) {
    console.log("  No topics found. Add items to modules/content/calendar/backlog.md");
    return;
  }

  // Print pipeline summary
  const stageCounts = topics.reduce(
    (acc, t) => ({ ...acc, [t.stage]: (acc[t.stage] ?? 0) + 1 }),
    {} as Record<string, number>
  );
  console.log("\n  Pipeline state:");
  for (const [stage, count] of Object.entries(stageCounts)) {
    console.log(`    ${stage.padEnd(22)} ${count}`);
  }

  const results: PipelineResult[] = [];

  // Process each in-flight topic (not backlog, not published)
  const inFlight = topics.filter(
    (t) => t.stage !== "backlog" && t.stage !== "published"
  );

  for (const topic of inFlight) {
    console.log(`\n  Advancing "${topic.title}" [${topic.stage}]...`);
    const existingDraft = await findExistingDraft(topic.slug);

    if (!existingDraft) {
      console.log(`    ⚠️  No draft file found for "${topic.slug}" — skipping`);
      continue;
    }

    const { previousStage, nextStage, assignedTo } = await advanceDraft(existingDraft);

    // Update backlog file
    backlogContent = updateBacklogLine(backlogContent, topic.raw, nextStage);

    results.push({
      topic: topic.title,
      slug: topic.slug,
      previousStage,
      nextStage,
      assignedTo,
      draftPath: existingDraft,
    });

    console.log(`    ${previousStage} → ${nextStage} (assigned: ${assignedTo})`);
  }

  // Pick the next backlog topic to start drafting
  const nextBacklogTopic = topics.find((t) => t.stage === "backlog");
  if (nextBacklogTopic) {
    console.log(`\n  Starting new draft: "${nextBacklogTopic.title}"`);
    const draftPath = await createDraft(nextBacklogTopic);
    const draftFilename = basename(draftPath);

    // Update backlog
    backlogContent = updateBacklogLine(backlogContent, nextBacklogTopic.raw, "draft");

    results.push({
      topic: nextBacklogTopic.title,
      slug: nextBacklogTopic.slug,
      previousStage: "backlog",
      nextStage: "draft",
      assignedTo: "growth",
      draftPath,
    });

    console.log(`    Created: ${draftFilename}`);
    console.log(`    Assigned to: growth`);
  }

  // Write updated backlog
  await Bun.write(BACKLOG_PATH, backlogContent);

  // Summary
  console.log(`\n✅ Content pipeline complete`);
  console.log(`   Topics advanced : ${results.filter((r) => r.previousStage !== "backlog").length}`);
  console.log(`   New drafts      : ${results.filter((r) => r.previousStage === "backlog").length}`);

  if (results.length > 0) {
    console.log(`\n   Changes:`);
    for (const r of results) {
      console.log(`   - "${r.topic}" :: ${r.previousStage} → ${r.nextStage} (${r.assignedTo})`);
    }
  }
}

await main();
