/**
 * workflows/daily-standup.ts
 *
 * Reads all agent configs, scans their last output files, and generates a
 * daily standup summary markdown file at standup/YYYY-MM-DD.md.
 *
 * Usage: bun run standup
 */

import { readdir, stat, mkdir } from "node:fs/promises";
import { join, resolve, basename, extname } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AgentConfig {
  name: string;
  codename: string;
  model: string;
  schedule: string;
  trigger?: string;
  skills: string[];
  responsibilities: string[];
  outputs: string[];
  escalation: string;
}

interface AgentStatus {
  codename: string;
  name: string;
  schedule: string;
  lastOutputFile: string | null;
  lastOutputTime: Date | null;
  recentOutputs: string[];
  outputCount: number;
}

interface StandupData {
  date: string;
  agents: AgentStatus[];
  totalOutputs: number;
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const ROOT = resolve(import.meta.dir, "..");
const AGENTS_DIR = join(ROOT, "agents");
const STANDUP_DIR = join(ROOT, "standup");

// ---------------------------------------------------------------------------
// YAML parser (reused minimal implementation)
// ---------------------------------------------------------------------------

type YamlValue = string | string[] | unknown;
type YamlDoc = Record<string, YamlValue>;

function parseSimpleYaml(content: string): YamlDoc {
  const result: YamlDoc = {};
  const lines = content.split("\n");
  let currentKey: string | null = null;
  let currentList: string[] | null = null;

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("#") || line.trim() === "") continue;

    const commentStripped = line.includes("  #")
      ? line.slice(0, line.indexOf("  #")).trimEnd()
      : line;

    if (/^ {2,}- /.test(line)) {
      const value = line.replace(/^ {2,}- /, "").trim();
      if (currentList !== null) currentList.push(value);
      continue;
    }

    if (/^ {2,}\w/.test(line) && currentList === null) continue;

    const match = commentStripped.match(/^(\w[\w-]*):\s*(.*)?$/);
    if (match) {
      const [, key, rawValue] = match;
      const value = rawValue?.trim() ?? "";
      if (currentKey !== null && currentList !== null) result[currentKey] = currentList;
      currentList = null;
      currentKey = key;
      if (value === "" || value === undefined) {
        currentList = [];
      } else {
        result[key] = value;
        currentKey = null;
      }
    }
  }

  if (currentKey !== null && currentList !== null && currentList.length > 0) {
    result[currentKey] = currentList;
  }

  return result;
}

async function readFileSafe(path: string): Promise<string | null> {
  try {
    return await Bun.file(path).text();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Agent config loading
// ---------------------------------------------------------------------------

async function loadAgentConfigs(): Promise<AgentConfig[]> {
  let files: string[];
  try {
    const entries = await readdir(AGENTS_DIR);
    files = entries.filter((f) => f.endsWith(".yml"));
  } catch {
    return [];
  }

  const configs: AgentConfig[] = [];
  for (const file of files) {
    const raw = await readFileSafe(join(AGENTS_DIR, file));
    if (!raw) continue;

    const doc = parseSimpleYaml(raw);
    configs.push({
      name: (doc["name"] as string) ?? file.replace(".yml", ""),
      codename: (doc["codename"] as string) ?? file.replace(".yml", ""),
      model: (doc["model"] as string) ?? "unknown",
      schedule: (doc["schedule"] as string) ?? "unknown",
      trigger: doc["trigger"] as string | undefined,
      skills: (doc["skills"] as string[]) ?? [],
      responsibilities: (doc["responsibilities"] as string[]) ?? [],
      outputs: (doc["outputs"] as string[]) ?? [],
      escalation: (doc["escalation"] as string) ?? "human",
    });
  }

  return configs;
}

// ---------------------------------------------------------------------------
// Output scanning
// ---------------------------------------------------------------------------

/** Find the most recently modified file in a directory (non-recursive). */
async function findLatestFile(
  dir: string
): Promise<{ path: string; mtime: Date } | null> {
  try {
    const entries = await readdir(dir);
    const files = entries.filter((e) => extname(e) !== "");

    if (files.length === 0) return null;

    const withStats = await Promise.all(
      files.map(async (f) => {
        const full = join(dir, f);
        const s = await stat(full).catch(() => null);
        return s ? { path: full, mtime: s.mtime } : null;
      })
    );

    const valid = withStats.filter(Boolean) as { path: string; mtime: Date }[];
    valid.sort((a, b) => b.mtime.getTime() - a.mtime.getTime());
    return valid[0] ?? null;
  } catch {
    return null;
  }
}

async function getAgentStatus(
  config: AgentConfig
): Promise<AgentStatus> {
  const recentOutputs: string[] = [];
  let lastOutputFile: string | null = null;
  let lastOutputTime: Date | null = null;
  let outputCount = 0;

  for (const outputPath of config.outputs) {
    const fullPath = join(ROOT, outputPath);

    // Check if it's a directory or file
    const s = await stat(fullPath).catch(() => null);
    if (!s) {
      recentOutputs.push(`${outputPath} (not found)`);
      continue;
    }

    if (s.isDirectory()) {
      // List up to 5 recent files
      try {
        const entries = await readdir(fullPath);
        const mdFiles = entries.filter((e) => e.endsWith(".md") || e.endsWith(".json"));
        outputCount += mdFiles.length;

        const latest = await findLatestFile(fullPath);
        if (latest && (!lastOutputTime || latest.mtime > lastOutputTime)) {
          lastOutputTime = latest.mtime;
          lastOutputFile = latest.path.replace(ROOT + "/", "");
        }

        const recent = mdFiles.slice(-3).map((f) => join(outputPath, f));
        recentOutputs.push(...recent);
      } catch {
        recentOutputs.push(`${outputPath} (empty)`);
      }
    } else {
      // Single file
      outputCount += 1;
      recentOutputs.push(outputPath);
      if (!lastOutputTime || s.mtime > lastOutputTime) {
        lastOutputTime = s.mtime;
        lastOutputFile = outputPath;
      }
    }
  }

  return {
    codename: config.codename,
    name: config.name,
    schedule: config.schedule,
    lastOutputFile,
    lastOutputTime,
    recentOutputs: recentOutputs.slice(0, 5),
    outputCount,
  };
}

// ---------------------------------------------------------------------------
// Standup generation
// ---------------------------------------------------------------------------

function formatSchedule(schedule: string): string {
  if (schedule === "always-on") return "Always-on";
  if (schedule === "on-demand") return "On-demand";
  if (schedule.startsWith("0 9 * * 1-5")) return "Weekdays 9am UTC";
  if (schedule.startsWith("0 10 * * 1,3,5")) return "Mon/Wed/Fri 10am UTC";
  return schedule;
}

function formatTimeAgo(date: Date | null): string {
  if (!date) return "never";
  const diffMs = Date.now() - date.getTime();
  const diffH = Math.floor(diffMs / (1000 * 60 * 60));
  const diffM = Math.floor(diffMs / (1000 * 60));
  if (diffH > 48) return `${Math.floor(diffH / 24)}d ago`;
  if (diffH > 0) return `${diffH}h ago`;
  if (diffM > 0) return `${diffM}m ago`;
  return "just now";
}

function renderStandup(data: StandupData): string {
  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });

  const lines: string[] = [
    `# Daily Standup — ${data.date}`,
    ``,
    `_Generated at ${now.toISOString()}_`,
    ``,
    `---`,
    ``,
    `## Agent Status`,
    ``,
    `| Agent | Schedule | Last Output | Output Count |`,
    `|-------|----------|-------------|--------------|`,
  ];

  for (const agent of data.agents) {
    const lastOut = agent.lastOutputFile
      ? `\`${basename(agent.lastOutputFile)}\` (${formatTimeAgo(agent.lastOutputTime)})`
      : "_none yet_";
    lines.push(
      `| **${agent.name}** (\`${agent.codename}\`) | ${formatSchedule(agent.schedule)} | ${lastOut} | ${agent.outputCount} |`
    );
  }

  lines.push(``);
  lines.push(`---`);
  lines.push(``);
  lines.push(`## Recent Outputs`);
  lines.push(``);

  for (const agent of data.agents) {
    if (agent.recentOutputs.length === 0) continue;
    lines.push(`### ${agent.name}`);
    lines.push(``);
    for (const output of agent.recentOutputs) {
      lines.push(`- \`${output}\``);
    }
    lines.push(``);
  }

  lines.push(`---`);
  lines.push(``);
  lines.push(`## Summary`);
  lines.push(``);
  lines.push(`- **Total agents**: ${data.agents.length}`);
  lines.push(`- **Total outputs tracked**: ${data.totalOutputs}`);
  lines.push(`- **Agents active today**: ${data.agents.filter(a => a.outputCount > 0).length}`);
  lines.push(``);
  lines.push(`_Next standup: tomorrow at 9am UTC_`);

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const today = new Date().toISOString().split("T")[0]!;

  console.log(`📋 Generating daily standup for ${today}...`);

  // Load agent configs
  const configs = await loadAgentConfigs();
  if (configs.length === 0) {
    throw new Error("No agent configs found in agents/ directory");
  }
  console.log(`  Loaded ${configs.length} agent configs`);

  // Get status for each agent
  const agentStatuses = await Promise.all(configs.map(getAgentStatus));

  const totalOutputs = agentStatuses.reduce((sum, a) => sum + a.outputCount, 0);

  const standupData: StandupData = {
    date: today,
    agents: agentStatuses,
    totalOutputs,
  };

  // Render markdown
  const markdown = renderStandup(standupData);

  // Write output
  await mkdir(STANDUP_DIR, { recursive: true });
  const outputPath = join(STANDUP_DIR, `${today}.md`);
  await Bun.write(outputPath, markdown + "\n");

  console.log(`\n✅ Standup written to standup/${today}.md`);
  console.log(`   Agents   : ${configs.length}`);
  console.log(`   Outputs  : ${totalOutputs}`);
}

await main();
