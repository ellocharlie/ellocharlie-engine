/**
 * workflows/weekly-review.ts
 *
 * Aggregates weekly metrics across all agent output directories:
 *   - PRs merged (from CTO pr-reviews output)
 *   - Tickets resolved (from CX ticket-responses output)
 *   - Content published (from Growth blog-drafts output)
 *   - Deploys executed (from Ops deploy-logs output)
 *
 * Writes a weekly review to reviews/YYYY-Www.md
 *
 * Usage: bun run review
 */

import { readdir, stat, mkdir } from "node:fs/promises";
import { join, resolve, extname } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WeeklyMetrics {
  week: string;          // ISO week string, e.g. "2026-W15"
  weekStart: Date;
  weekEnd: Date;
  prsReviewed: FileEntry[];
  ticketsResolved: FileEntry[];
  contentDrafted: FileEntry[];
  deploysExecuted: FileEntry[];
  incidentsReported: FileEntry[];
  agentActivity: AgentActivityEntry[];
}

interface FileEntry {
  path: string;
  name: string;
  mtime: Date;
  agent: string;
}

interface AgentActivityEntry {
  codename: string;
  name: string;
  outputCount: number;
  files: string[];
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const ROOT = resolve(import.meta.dir, "..");
const REVIEWS_DIR = join(ROOT, "reviews");

/** Output directories to scan, keyed by category. */
const OUTPUT_DIRS: Record<string, { path: string; agent: string }[]> = {
  prsReviewed: [
    { path: "modules/agents/pr-reviews", agent: "cto" },
  ],
  ticketsResolved: [
    { path: "modules/content/ticket-responses", agent: "cx-lead" },
  ],
  contentDrafted: [
    { path: "modules/content/blog-drafts", agent: "growth" },
    { path: "modules/content/social-posts", agent: "growth" },
  ],
  deploysExecuted: [
    { path: "modules/agents/deploy-logs", agent: "ops" },
  ],
  incidentsReported: [
    { path: "modules/agents/incident-reports", agent: "ops" },
  ],
};

/** All agent output dirs for general activity tracking. */
const ALL_AGENT_OUTPUTS: { codename: string; name: string; dirs: string[] }[] = [
  { codename: "ceo", name: "Chief Executive Officer", dirs: ["standup"] },
  { codename: "cto", name: "Chief Technology Officer", dirs: ["modules/agents/pr-reviews", "modules/agents/architecture-decision-records"] },
  { codename: "growth", name: "Growth Lead", dirs: ["modules/content/blog-drafts", "modules/content/social-posts", "modules/content/seo-reports"] },
  { codename: "cx-lead", name: "Customer Experience Lead", dirs: ["modules/content/ticket-responses", "modules/content/escalation-packages"] },
  { codename: "ops", name: "Operations Engineer", dirs: ["modules/agents/deploy-logs", "modules/agents/incident-reports"] },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getISOWeek(date: Date): string {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(
    ((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7
  );
  return `${d.getUTCFullYear()}-W${weekNo.toString().padStart(2, "0")}`;
}

function getWeekBounds(date: Date): { start: Date; end: Date } {
  const d = new Date(date);
  const day = d.getUTCDay() || 7; // Mon=1, Sun=7
  const monday = new Date(d);
  monday.setUTCDate(d.getUTCDate() - day + 1);
  monday.setUTCHours(0, 0, 0, 0);
  const sunday = new Date(monday);
  sunday.setUTCDate(monday.getUTCDate() + 6);
  sunday.setUTCHours(23, 59, 59, 999);
  return { start: monday, end: sunday };
}

async function scanDirectory(
  dir: string,
  agent: string,
  since: Date,
  until: Date
): Promise<FileEntry[]> {
  const fullPath = join(ROOT, dir);
  try {
    const entries = await readdir(fullPath);
    const files = entries.filter(
      (e) => extname(e) !== "" && !e.startsWith(".")
    );

    const results: FileEntry[] = [];
    for (const file of files) {
      const filePath = join(fullPath, file);
      const s = await stat(filePath).catch(() => null);
      if (!s) continue;
      if (s.mtime >= since && s.mtime <= until) {
        results.push({
          path: join(dir, file),
          name: file,
          mtime: s.mtime,
          agent,
        });
      }
    }

    return results.sort((a, b) => b.mtime.getTime() - a.mtime.getTime());
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Metric collection
// ---------------------------------------------------------------------------

async function collectMetrics(weekStart: Date, weekEnd: Date): Promise<WeeklyMetrics> {
  const week = getISOWeek(weekStart);

  // Collect categorized outputs
  async function collectCategory(
    category: string
  ): Promise<FileEntry[]> {
    const dirs = OUTPUT_DIRS[category] ?? [];
    const results = await Promise.all(
      dirs.map(({ path, agent }) => scanDirectory(path, agent, weekStart, weekEnd))
    );
    return results.flat();
  }

  const [prsReviewed, ticketsResolved, contentDrafted, deploysExecuted, incidentsReported] =
    await Promise.all([
      collectCategory("prsReviewed"),
      collectCategory("ticketsResolved"),
      collectCategory("contentDrafted"),
      collectCategory("deploysExecuted"),
      collectCategory("incidentsReported"),
    ]);

  // Collect general agent activity
  const agentActivity = await Promise.all(
    ALL_AGENT_OUTPUTS.map(async ({ codename, name, dirs }) => {
      const allFiles = await Promise.all(
        dirs.map((d) => scanDirectory(d, codename, weekStart, weekEnd))
      );
      const files = allFiles.flat();
      return {
        codename,
        name,
        outputCount: files.length,
        files: files.map((f) => f.name).slice(0, 5),
      };
    })
  );

  return {
    week,
    weekStart,
    weekEnd,
    prsReviewed,
    ticketsResolved,
    contentDrafted,
    deploysExecuted,
    incidentsReported,
    agentActivity,
  };
}

// ---------------------------------------------------------------------------
// Report rendering
// ---------------------------------------------------------------------------

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0]!;
}

function renderFileList(files: FileEntry[], max = 10): string {
  if (files.length === 0) return "_None this week._\n";
  const shown = files.slice(0, max);
  const lines = shown.map(
    (f) =>
      `- \`${f.name}\` — ${f.mtime.toISOString().slice(0, 10)} (\`${f.agent}\`)`
  );
  if (files.length > max) {
    lines.push(`- _...and ${files.length - max} more_`);
  }
  return lines.join("\n") + "\n";
}

function renderWeeklyReview(metrics: WeeklyMetrics): string {
  const totalActivity = metrics.agentActivity.reduce(
    (sum, a) => sum + a.outputCount,
    0
  );

  const lines: string[] = [
    `# Weekly Review — ${metrics.week}`,
    ``,
    `_${formatDate(metrics.weekStart)} → ${formatDate(metrics.weekEnd)}_`,
    `_Generated at ${new Date().toISOString()}_`,
    ``,
    `---`,
    ``,
    `## At a Glance`,
    ``,
    `| Metric | Count |`,
    `|--------|-------|`,
    `| PRs reviewed | ${metrics.prsReviewed.length} |`,
    `| Tickets resolved | ${metrics.ticketsResolved.length} |`,
    `| Content drafted | ${metrics.contentDrafted.length} |`,
    `| Deploys executed | ${metrics.deploysExecuted.length} |`,
    `| Incidents reported | ${metrics.incidentsReported.length} |`,
    `| **Total agent outputs** | **${totalActivity}** |`,
    ``,
    `---`,
    ``,
    `## Engineering (CTO)`,
    ``,
    `### PRs Reviewed`,
    ``,
    renderFileList(metrics.prsReviewed),
    `---`,
    ``,
    `## Customer Experience (CX Lead)`,
    ``,
    `### Tickets Resolved`,
    ``,
    renderFileList(metrics.ticketsResolved),
    `---`,
    ``,
    `## Growth`,
    ``,
    `### Content Drafted`,
    ``,
    renderFileList(metrics.contentDrafted),
    `---`,
    ``,
    `## Operations (OPS)`,
    ``,
    `### Deploys`,
    ``,
    renderFileList(metrics.deploysExecuted),
    ``,
    `### Incidents`,
    ``,
    renderFileList(metrics.incidentsReported),
    `---`,
    ``,
    `## Agent Activity Summary`,
    ``,
    `| Agent | Outputs This Week | Recent Files |`,
    `|-------|-------------------|--------------|`,
  ];

  for (const agent of metrics.agentActivity) {
    const recent = agent.files.slice(0, 3).map((f) => `\`${f}\``).join(", ") || "_none_";
    lines.push(
      `| **${agent.name}** | ${agent.outputCount} | ${recent} |`
    );
  }

  lines.push(``);
  lines.push(`---`);
  lines.push(``);
  lines.push(`## Notes`);
  lines.push(``);
  lines.push(`_Add qualitative notes here after review._`);
  lines.push(``);
  lines.push(`---`);
  lines.push(``);
  lines.push(`_Next review: ${formatDate(new Date(metrics.weekEnd.getTime() + 7 * 24 * 60 * 60 * 1000))}_`);

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const now = new Date();
  const { start: weekStart, end: weekEnd } = getWeekBounds(now);
  const week = getISOWeek(weekStart);

  console.log(`📊 Generating weekly review for ${week}...`);
  console.log(`   Week: ${formatDate(weekStart)} → ${formatDate(weekEnd)}`);

  const metrics = await collectMetrics(weekStart, weekEnd);

  const markdown = renderWeeklyReview(metrics);

  await mkdir(REVIEWS_DIR, { recursive: true });
  const outputPath = join(REVIEWS_DIR, `${week}.md`);
  await Bun.write(outputPath, markdown + "\n");

  console.log(`\n✅ Weekly review written to reviews/${week}.md`);
  console.log(`   PRs reviewed     : ${metrics.prsReviewed.length}`);
  console.log(`   Tickets resolved : ${metrics.ticketsResolved.length}`);
  console.log(`   Content drafted  : ${metrics.contentDrafted.length}`);
  console.log(`   Deploys          : ${metrics.deploysExecuted.length}`);
  console.log(`   Incidents        : ${metrics.incidentsReported.length}`);
}

await main();
