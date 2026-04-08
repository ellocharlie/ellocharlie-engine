/**
 * index/build-index.ts
 *
 * Scans all submodules in modules/, reads their package.json and README.md,
 * then reads all agent YAML configs from agents/ and builds index/manifest.json.
 *
 * Usage: bun run index:build
 */

import { readdir, stat } from "node:fs/promises";
import { join, resolve } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RepoEntry {
  name: string;
  module: string;
  description: string;
  version: string;
  readme_excerpt: string;
  exists: boolean;
}

interface AgentEntry {
  name: string;
  codename: string;
  model: string;
  schedule: string;
  trigger?: string;
  skills: string[];
  responsibilities: string[];
  escalation: string;
}

interface Manifest {
  org: string;
  updated: string;
  repos: Record<string, RepoEntry>;
  agents: Record<string, AgentEntry>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ROOT = resolve(import.meta.dir, "..");
const MODULES_DIR = join(ROOT, "modules");
const AGENTS_DIR = join(ROOT, "agents");

/** Safely read a file, returning null if it doesn't exist. */
async function readFileSafe(path: string): Promise<string | null> {
  try {
    return await Bun.file(path).text();
  } catch {
    return null;
  }
}

/** Extract the first non-heading paragraph from a README for use as an excerpt. */
function extractReadmeExcerpt(readme: string, maxLength = 200): string {
  const lines = readme.split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith("#") && !trimmed.startsWith("!")) {
      return trimmed.length > maxLength
        ? trimmed.slice(0, maxLength) + "…"
        : trimmed;
    }
  }
  return "";
}

/** Check if a directory exists and is non-empty (i.e., submodule is initialized). */
async function isSubmodulePopulated(dir: string): Promise<boolean> {
  try {
    const entries = await readdir(dir);
    return entries.length > 0;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// YAML parser (minimal — handles the flat key: value and list structures used
// in agent configs without pulling in a YAML library).
// ---------------------------------------------------------------------------

type YamlValue = string | string[] | Record<string, unknown> | unknown;
type YamlDoc = Record<string, YamlValue>;

function parseSimpleYaml(content: string): YamlDoc {
  const result: YamlDoc = {};
  const lines = content.split("\n");
  let currentKey: string | null = null;
  let currentList: string[] | null = null;

  for (const raw of lines) {
    const line = raw.trimEnd();

    // Skip comments and blank lines at top level
    if (line.startsWith("#") || line.trim() === "") {
      if (line.trim() === "" && currentList !== null && currentKey !== null) {
        // End of list block — but keep accumulating until a new key appears
      }
      continue;
    }

    // Detect inline comment on cron schedule lines
    const commentStripped = line.includes("  #")
      ? line.slice(0, line.indexOf("  #")).trimEnd()
      : line;

    // List item under current key
    if (/^ {2,}- /.test(line)) {
      const value = line.replace(/^ {2,}- /, "").trim();
      if (currentList !== null) {
        currentList.push(value);
      }
      continue;
    }

    // Nested key (indented, not a list item) — skip for our purposes
    if (/^ {2,}\w/.test(line) && currentList === null) {
      continue;
    }

    // Top-level key: value
    const match = commentStripped.match(/^(\w[\w-]*):\s*(.*)?$/);
    if (match) {
      const [, key, rawValue] = match;
      const value = rawValue?.trim() ?? "";

      // Flush previous list
      if (currentKey !== null && currentList !== null) {
        result[currentKey] = currentList;
      }
      currentList = null;
      currentKey = key;

      if (value === "" || value === undefined) {
        // Value will be a list or block — start collecting
        currentList = [];
      } else {
        result[key] = value;
        currentKey = null;
      }
    }
  }

  // Flush trailing list
  if (currentKey !== null && currentList !== null && currentList.length > 0) {
    result[currentKey] = currentList;
  }

  return result;
}

// ---------------------------------------------------------------------------
// Repo scanning
// ---------------------------------------------------------------------------

async function scanRepo(moduleName: string): Promise<RepoEntry> {
  const dir = join(MODULES_DIR, moduleName);
  const populated = await isSubmodulePopulated(dir);

  if (!populated) {
    return {
      name: moduleName,
      module: moduleName,
      description: "(submodule not initialized)",
      version: "unknown",
      readme_excerpt: "",
      exists: false,
    };
  }

  const pkgRaw = await readFileSafe(join(dir, "package.json"));
  const readmeRaw = await readFileSafe(join(dir, "README.md"));

  let name = moduleName;
  let description = "";
  let version = "0.0.0";

  if (pkgRaw) {
    try {
      const pkg = JSON.parse(pkgRaw) as {
        name?: string;
        description?: string;
        version?: string;
      };
      name = pkg.name ?? moduleName;
      description = pkg.description ?? "";
      version = pkg.version ?? "0.0.0";
    } catch {
      // Malformed package.json — use defaults
    }
  }

  const readme_excerpt = readmeRaw ? extractReadmeExcerpt(readmeRaw) : "";

  return {
    name,
    module: moduleName,
    description,
    version,
    readme_excerpt,
    exists: true,
  };
}

async function scanAllRepos(): Promise<Record<string, RepoEntry>> {
  let moduleNames: string[];
  try {
    const entries = await readdir(MODULES_DIR);
    // Filter to directories only
    const stats = await Promise.all(
      entries.map(async (e) => ({
        name: e,
        isDir: (await stat(join(MODULES_DIR, e))).isDirectory(),
      }))
    );
    moduleNames = stats.filter((s) => s.isDir).map((s) => s.name);
  } catch {
    moduleNames = [];
  }

  const results = await Promise.all(moduleNames.map((n) => scanRepo(n)));
  return Object.fromEntries(results.map((r) => [r.module, r]));
}

// ---------------------------------------------------------------------------
// Agent scanning
// ---------------------------------------------------------------------------

async function scanAgent(filename: string): Promise<AgentEntry | null> {
  const path = join(AGENTS_DIR, filename);
  const raw = await readFileSafe(path);
  if (!raw) return null;

  const doc = parseSimpleYaml(raw);

  const codename = (doc["codename"] as string) ?? filename.replace(".yml", "");
  const name = (doc["name"] as string) ?? codename;
  const model = (doc["model"] as string) ?? "unknown";
  const schedule = (doc["schedule"] as string) ?? "unknown";
  const trigger = doc["trigger"] as string | undefined;
  const skills = (doc["skills"] as string[]) ?? [];
  const responsibilities = (doc["responsibilities"] as string[]) ?? [];
  const escalation = (doc["escalation"] as string) ?? "human";

  return {
    name,
    codename,
    model,
    schedule,
    trigger,
    skills,
    responsibilities,
    escalation,
  };
}

async function scanAllAgents(): Promise<Record<string, AgentEntry>> {
  let files: string[];
  try {
    const entries = await readdir(AGENTS_DIR);
    files = entries.filter((f) => f.endsWith(".yml"));
  } catch {
    files = [];
  }

  const results = await Promise.all(files.map((f) => scanAgent(f)));
  const agents: Record<string, AgentEntry> = {};
  for (const agent of results) {
    if (agent) {
      agents[agent.codename] = agent;
    }
  }
  return agents;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  console.log("🔍 Scanning submodules...");
  const repos = await scanAllRepos();

  console.log("🤖 Scanning agent configs...");
  const agents = await scanAllAgents();

  const manifest: Manifest = {
    org: "ellocharlie",
    updated: new Date().toISOString(),
    repos,
    agents,
  };

  const outputPath = join(ROOT, "index", "manifest.json");
  await Bun.write(outputPath, JSON.stringify(manifest, null, 2) + "\n");

  const repoCount = Object.keys(repos).length;
  const agentCount = Object.keys(agents).length;
  const populatedCount = Object.values(repos).filter((r) => r.exists).length;

  console.log(`\n✅ Manifest written to index/manifest.json`);
  console.log(`   Repos  : ${populatedCount}/${repoCount} initialized`);
  console.log(`   Agents : ${agentCount}`);
  console.log(`   Updated: ${manifest.updated}`);
}

await main();
