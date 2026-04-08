/* ────────────────────────────────────────────────────────────
   ellocharlie command center — dashboard logic
   GitHub API + Brain API (port 7777) integration
──────────────────────────────────────────────────────────── */

'use strict';

// ── Config ──────────────────────────────────────────────────
const CONFIG = {
  GITHUB_ORG: 'ellocharlie',
  GITHUB_API: 'https://api.github.com',
  BRAIN_API: 'http://localhost:7777',
  REPOS: ['ellocharlie.com', 'ellocharlie-agents', 'ellocharlie-engine', 'ellocharlie-content'],
  AGENTS: ['ceo', 'cto', 'growth', 'cx-lead', 'ops'],
  REFRESH_INTERVAL: 60, // seconds
  LAUNCH_DATE: '2026-04-08',
  GROWTH_TARGETS: [
    { week: 0, customers: 2, mrr: 275 },
    { week: 4, customers: 2.6, mrr: 360 },
    { week: 8, customers: 3.4, mrr: 473 },
    { week: 12, customers: 4.5, mrr: 619 },
    { week: 16, customers: 5.9, mrr: 812 },
    { week: 20, customers: 7.7, mrr: 1064 },
    { week: 26, customers: 11.6, mrr: 1597 },
    { week: 52, customers: 59.0, mrr: 8099 },
  ],
};

// Repo display config
const REPO_META = {
  'ellocharlie.com':      { color: '--color-primary',   class: 'repo-site',    label: 'site',    icon: '🌐' },
  'ellocharlie-agents':   { color: '--color-blue',       class: 'repo-agents',  label: 'agents',  icon: '🤖' },
  'ellocharlie-engine':   { color: '--color-gold',       class: 'repo-engine',  label: 'engine',  icon: '⚙️' },
  'ellocharlie-content':  { color: '--color-purple',     class: 'repo-content', label: 'content', icon: '✍️' },
};

const AGENT_META = {
  ceo:      { name: 'CEO',      role: 'Chief Executive Officer',    color: '--color-gold',    icon: '🏛️', schedule: 'Weekdays 9am UTC' },
  cto:      { name: 'CTO',      role: 'Chief Technology Officer',   color: '--color-blue',    icon: '⚙️', schedule: 'On-demand / PR' },
  growth:   { name: 'Growth',   role: 'Growth Lead',                color: '--color-success', icon: '📈', schedule: 'Mon/Wed/Fri 10am' },
  'cx-lead':{ name: 'CX Lead',  role: 'Customer Experience Lead',   color: '--color-primary', icon: '💬', schedule: 'Always on' },
  ops:      { name: 'Ops',      role: 'Operations Engineer',         color: '--color-purple',  icon: '🔧', schedule: 'Always on' },
};

// ── State ───────────────────────────────────────────────────
let state = {
  token: null,
  issues: [],
  filteredIssues: [],
  repos: [],
  team: {},
  memories: {},
  filters: { repo: 'all', label: 'all', assignee: 'all', state: 'open', search: '' },
  sort: 'newest',
  refreshTimer: null,
  countdown: CONFIG.REFRESH_INTERVAL,
  loading: { issues: false, agents: false, metrics: false },
  metrics: { customers: 2, mrr: 275, wow: 0 },
};

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  checkToken();
});

function checkToken() {
  const stored = sessionStorage.getItem('gh_token');
  if (stored) {
    state.token = stored;
    bootDashboard();
  } else {
    showTokenGate();
  }
}

function showTokenGate() {
  const gate = document.getElementById('token-gate');
  if (gate) gate.classList.remove('hidden');
}

function hideTokenGate() {
  const gate = document.getElementById('token-gate');
  if (gate) gate.classList.add('hidden');
}

window.submitToken = function () {
  const input = document.getElementById('token-input');
  const val = input ? input.value.trim() : '';
  if (!val) return showToast('Please enter a GitHub token', 'error');
  if (!val.startsWith('gh')) return showToast('Token should start with "gh"', 'error');
  state.token = val;
  sessionStorage.setItem('gh_token', val);
  hideTokenGate();
  bootDashboard();
};

window.skipToken = function () {
  state.token = null;
  hideTokenGate();
  bootDashboard();
};

function bootDashboard() {
  loadAllData();
  startAutoRefresh();
  bindFilterEvents();
  bindSortEvents();
  bindModalEvents();
  bindSidebarNav();
  loadMetricsFromStorage();
}

// ── Theme ───────────────────────────────────────────────────
function initTheme() {
  const stored = sessionStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = stored || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  updateThemeToggle(theme);
}

window.toggleTheme = function () {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  sessionStorage.setItem('theme', next);
  updateThemeToggle(next);
};

function updateThemeToggle(theme) {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;
  btn.innerHTML = theme === 'dark'
    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>`
    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
  btn.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
}

// ── Data Loading ────────────────────────────────────────────
async function loadAllData() {
  await Promise.allSettled([
    loadIssues(),
    loadAgentData(),
    loadBrainData(),
  ]);
  renderGrowthMetrics();
  renderStandup();
}

// ── GitHub Issues ───────────────────────────────────────────
async function loadIssues() {
  state.loading.issues = true;
  showIssuesSkeleton();

  const allIssues = [];
  const headers = { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;

  await Promise.allSettled(
    CONFIG.REPOS.map(async (repo) => {
      try {
        let page = 1;
        while (true) {
          const url = `${CONFIG.GITHUB_API}/repos/${CONFIG.GITHUB_ORG}/${repo}/issues?state=all&per_page=50&page=${page}`;
          const res = await fetch(url, { headers });
          if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`);
          const data = await res.json();
          if (!data.length) break;
          data.forEach(issue => {
            if (!issue.pull_request) { // exclude PRs
              allIssues.push({ ...issue, _repo: repo });
            }
          });
          if (data.length < 50) break;
          page++;
        }
      } catch (e) {
        console.warn(`Failed to load issues from ${repo}:`, e.message);
      }
    })
  );

  state.issues = allIssues;
  state.loading.issues = false;
  applyFiltersAndSort();
  populateFilterOptions();
  updateIssueBadge();
}

function populateFilterOptions() {
  const repoSel = document.getElementById('filter-repo');
  const labelSel = document.getElementById('filter-label');
  const assigneeSel = document.getElementById('filter-assignee');
  if (!repoSel) return;

  // Repos
  const repos = [...new Set(state.issues.map(i => i._repo))];
  repoSel.innerHTML = `<option value="all">All repos</option>` +
    repos.map(r => `<option value="${r}">${r}</option>`).join('');

  // Labels
  const labels = [...new Set(state.issues.flatMap(i => i.labels.map(l => l.name)))];
  labelSel.innerHTML = `<option value="all">All labels</option>` +
    labels.map(l => `<option value="${l}">${l}</option>`).join('');

  // Assignees
  const assignees = [...new Set(state.issues.filter(i => i.assignee).map(i => i.assignee.login))];
  assigneeSel.innerHTML = `<option value="all">All assignees</option>` +
    assignees.map(a => `<option value="${a}">${a}</option>`).join('');
}

function applyFiltersAndSort() {
  let filtered = [...state.issues];
  const { repo, label, assignee, state: issueState, search } = state.filters;

  if (repo !== 'all') filtered = filtered.filter(i => i._repo === repo);
  if (label !== 'all') filtered = filtered.filter(i => i.labels.some(l => l.name === label));
  if (assignee !== 'all') filtered = filtered.filter(i => i.assignee?.login === assignee);
  if (issueState !== 'all') filtered = filtered.filter(i => i.state === issueState);
  if (search) {
    const q = search.toLowerCase();
    filtered = filtered.filter(i => i.title.toLowerCase().includes(q) || i._repo.toLowerCase().includes(q));
  }

  // Sort
  if (state.sort === 'newest') filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  else if (state.sort === 'oldest') filtered.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  else if (state.sort === 'comments') filtered.sort((a, b) => b.comments - a.comments);

  state.filteredIssues = filtered;
  renderIssues();
}

function bindFilterEvents() {
  const ids = ['filter-repo', 'filter-label', 'filter-assignee', 'filter-state'];
  const keys = ['repo', 'label', 'assignee', 'state'];
  ids.forEach((id, i) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', e => { state.filters[keys[i]] = e.target.value; applyFiltersAndSort(); });
  });
  const search = document.getElementById('issue-search');
  if (search) {
    let debounce;
    search.addEventListener('input', e => {
      clearTimeout(debounce);
      debounce = setTimeout(() => { state.filters.search = e.target.value; applyFiltersAndSort(); }, 200);
    });
  }
}

function bindSortEvents() {
  document.querySelectorAll('[data-sort]').forEach(btn => {
    btn.addEventListener('click', () => {
      state.sort = btn.dataset.sort;
      document.querySelectorAll('[data-sort]').forEach(b => b.classList.remove('sorted'));
      btn.classList.add('sorted');
      applyFiltersAndSort();
    });
  });
}

function renderIssues() {
  const tbody = document.getElementById('issues-tbody');
  const count = document.getElementById('issues-count');
  if (!tbody) return;

  if (count) count.textContent = `${state.filteredIssues.length} issue${state.filteredIssues.length !== 1 ? 's' : ''}`;

  if (!state.filteredIssues.length) {
    tbody.innerHTML = `
      <tr><td colspan="6">
        <div class="empty-state">
          <div class="empty-state-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/></svg></div>
          <h3>No issues found</h3>
          <p>Try adjusting your filters or create a new issue.</p>
        </div>
      </td></tr>`;
    return;
  }

  tbody.innerHTML = state.filteredIssues.map(issue => {
    const meta = REPO_META[issue._repo] || {};
    const labels = issue.labels.map(l => {
      const bg = l.color ? `#${l.color}` : 'var(--color-surface-offset)';
      const fg = l.color ? contrastColor(l.color) : 'var(--color-text-muted)';
      return `<span class="label-badge" style="background:${bg};color:${fg};border-color:${bg}">${escHtml(l.name)}</span>`;
    }).join('');

    const assignee = issue.assignee
      ? `<span class="issue-assignee"><img class="assignee-avatar" src="${escHtml(issue.assignee.avatar_url)}" alt="${escHtml(issue.assignee.login)}" loading="lazy">${escHtml(issue.assignee.login)}</span>`
      : `<span class="issue-date" style="font-style:italic">Unassigned</span>`;

    return `
      <tr class="issue-row ${meta.class || ''}" data-repo="${escHtml(issue._repo)}">
        <td>
          <span class="issue-repo-badge">${escHtml(meta.label || issue._repo)}</span>
        </td>
        <td>
          <a class="issue-title-link" href="${escHtml(issue.html_url)}" target="_blank" rel="noopener">
            <span class="issue-number">#${issue.number}</span>
            ${escHtml(issue.title)}
          </a>
        </td>
        <td><div class="issue-labels">${labels}</div></td>
        <td>${assignee}</td>
        <td class="issue-date">${relativeDate(issue.created_at)}</td>
        <td>
          <span class="issue-state-badge ${issue.state === 'open' ? 'state-open' : 'state-closed'}">
            ${issue.state === 'open'
              ? '<svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="6"/></svg>'
              : '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>'
            }
            ${issue.state}
          </span>
          ${issue.comments > 0 ? `<span class="comment-count" style="margin-top:4px"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>${issue.comments}</span>` : ''}
        </td>
      </tr>`;
  }).join('');
}

function showIssuesSkeleton() {
  const tbody = document.getElementById('issues-tbody');
  if (!tbody) return;
  tbody.innerHTML = Array(6).fill(0).map(() =>
    `<tr><td colspan="6"><div class="skeleton skeleton-row"></div></td></tr>`
  ).join('');
}

function updateIssueBadge() {
  const badge = document.getElementById('issues-badge');
  const openCount = state.issues.filter(i => i.state === 'open').length;
  if (badge) badge.textContent = openCount;
}

// ── Agent Activity ──────────────────────────────────────────
async function loadAgentData() {
  state.loading.agents = true;

  // Try brain API for team status
  const teamData = await brainGet('/team');
  const team = {};

  if (teamData) {
    state.team = teamData;
  }

  // Load recent memories for each agent
  await Promise.allSettled(
    CONFIG.AGENTS.map(async (agent) => {
      const mem = await brainGet(`/memory/recent/${agent}`);
      if (mem) state.memories[agent] = mem;
    })
  );

  state.loading.agents = false;
  renderAgentCards();
}

function renderAgentCards() {
  const grid = document.getElementById('agents-grid');
  if (!grid) return;

  grid.innerHTML = CONFIG.AGENTS.map(agentKey => {
    const meta = AGENT_META[agentKey];
    const teamInfo = state.team[agentKey] || {};
    const memory = state.memories[agentKey];
    const status = teamInfo.status || deriveStatus(agentKey);
    const lastAction = memory?.summary || teamInfo.last_action || 'No recent activity logged';
    const nextAction = teamInfo.next_action || meta.schedule;

    const statusClass = status === 'active' ? 'status-active'
      : status === 'scheduled' ? 'status-scheduled'
      : 'status-idle';

    return `
      <div class="agent-card" style="--agent-color: var(${meta.color})">
        <div class="agent-header">
          <div class="agent-identity">
            <div class="agent-icon">${meta.icon}</div>
            <div>
              <div class="agent-name">${meta.name}</div>
              <div class="agent-role">${meta.role}</div>
            </div>
          </div>
          <div class="agent-status-pill ${statusClass}">
            <span class="agent-pulse"></span>
            ${status}
          </div>
        </div>
        <div class="agent-last-action">
          <div class="agent-field-label">Last action</div>
          <div class="agent-field-value">${escHtml(lastAction)}</div>
        </div>
        <div class="agent-next">
          <div>
            <div class="agent-field-label">Schedule</div>
            <div class="agent-field-value" style="font-size: var(--text-xs)">${escHtml(nextAction)}</div>
          </div>
          <button class="btn btn-ghost btn-sm" onclick="triggerNudge('${agentKey}')">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            Nudge
          </button>
        </div>
      </div>`;
  }).join('');
}

function deriveStatus(agentKey) {
  const now = new Date();
  const hour = now.getUTCHours();
  const day = now.getUTCDay(); // 0=Sun, 1=Mon...5=Fri, 6=Sat
  if (agentKey === 'cx-lead' || agentKey === 'ops') return 'active';
  if (agentKey === 'ceo' && day >= 1 && day <= 5 && hour === 9) return 'active';
  if (agentKey === 'growth' && [1,3,5].includes(day) && hour === 10) return 'active';
  return 'idle';
}

// ── Brain API ───────────────────────────────────────────────
async function brainGet(path) {
  try {
    const res = await fetch(`${CONFIG.BRAIN_API}${path}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function brainPost(path, body) {
  try {
    const res = await fetch(`${CONFIG.BRAIN_API}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function loadBrainData() {
  const metrics = await brainGet('/memory/metrics');
  if (metrics) {
    state.metrics = { ...state.metrics, ...metrics };
  }
}

// ── Growth Metrics ──────────────────────────────────────────
function loadMetricsFromStorage() {
  const saved = sessionStorage.getItem('ec_metrics');
  if (saved) {
    try { state.metrics = { ...state.metrics, ...JSON.parse(saved) }; } catch {}
  }
}

function renderGrowthMetrics() {
  const launchDate = new Date(CONFIG.LAUNCH_DATE);
  const now = new Date();
  const daysSinceLaunch = Math.floor((now - launchDate) / (1000 * 60 * 60 * 24));
  const weeksSinceLaunch = Math.floor(daysSinceLaunch / 7);

  // KPI cards
  setKPI('kpi-customers', state.metrics.customers, 'customers', '→ 10 by end of Q2');
  setKPI('kpi-mrr', `$${(state.metrics.mrr || 275).toLocaleString()}`, 'MRR', `$${(state.metrics.mrr * 12 || 3300).toLocaleString()} ARR`);
  setKPI('kpi-wow', `${state.metrics.wow || 0}%`, 'WoW growth', 'Target: 7%');
  setKPI('kpi-days', daysSinceLaunch, 'days since launch', `Week ${weeksSinceLaunch}`);

  // Progress bar for customer target (10 by Q2)
  const customerProgress = Math.min((state.metrics.customers / 10) * 100, 100);
  const progressFill = document.getElementById('customer-progress');
  if (progressFill) progressFill.style.width = customerProgress + '%';

  // Milestones
  renderMilestones(weeksSinceLaunch);
}

function setKPI(id, value, label, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const valEl = el.querySelector('.kpi-value');
  const targetEl = el.querySelector('.kpi-target');
  if (valEl) valEl.textContent = value;
  if (targetEl) targetEl.textContent = target;
}

function renderMilestones(currentWeek) {
  const list = document.getElementById('milestones-list');
  if (!list) return;

  const milestones = CONFIG.GROWTH_TARGETS;
  list.innerHTML = milestones.map(m => {
    const isPast = currentWeek > m.week;
    const isCurrent = Math.abs(currentWeek - m.week) <= 1;
    const statusClass = isPast ? 'milestone-past' : isCurrent ? 'milestone-current' : 'milestone-future';
    const statusText = isPast ? '✓ passed' : isCurrent ? '← now' : `wk ${m.week}`;

    return `
      <div class="milestone-row">
        <span class="milestone-week">Wk ${m.week}</span>
        <span class="milestone-target">${m.customers} customers · $${m.mrr.toLocaleString()} MRR</span>
        <span class="milestone-status ${statusClass}">${statusText}</span>
      </div>`;
  }).join('');
}

// Metrics editing
window.editMetric = function (metric) {
  const current = state.metrics[metric] || 0;
  const label = metric === 'mrr' ? 'MRR ($)' : metric === 'wow' ? 'WoW Growth (%)' : 'Customer Count';
  openInputModal(`Update ${label}`, current, (val) => {
    state.metrics[metric] = parseFloat(val) || 0;
    sessionStorage.setItem('ec_metrics', JSON.stringify(state.metrics));
    renderGrowthMetrics();
    showToast(`${label} updated`, 'success');
  });
};

// ── Standup ─────────────────────────────────────────────────
async function renderStandup() {
  const standup = await brainGet('/standup/today');

  const updatesEl = document.getElementById('standup-updates');
  const blockersEl = document.getElementById('standup-blockers');
  const prioritiesEl = document.getElementById('standup-priorities');
  const timestampEl = document.getElementById('standup-timestamp');

  if (standup) {
    // Render updates
    if (updatesEl && standup.updates) {
      updatesEl.innerHTML = standup.updates.map(u => `
        <div class="standup-agent-row">
          <div class="standup-agent-name">${escHtml(AGENT_META[u.agent]?.name || u.agent)}</div>
          <div class="standup-agent-update">${escHtml(u.summary)}</div>
        </div>`).join('');
    }

    // Blockers
    if (blockersEl && standup.blockers) {
      blockersEl.innerHTML = standup.blockers.length > 0
        ? standup.blockers.map(b => `
          <div class="blocker-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <span class="blocker-text">${escHtml(b)}</span>
          </div>`).join('')
        : `<div class="empty-state" style="padding: var(--space-6)">
            <p style="color: var(--color-success); font-weight: 500;">✓ No blockers today</p>
          </div>`;
    }

    // Priorities
    if (prioritiesEl && standup.priorities) {
      prioritiesEl.innerHTML = standup.priorities.map((p, i) => `
        <div class="priority-item">
          <div class="priority-num">${i + 1}</div>
          <div class="priority-text">${escHtml(p)}</div>
        </div>`).join('');
    }

    if (timestampEl) timestampEl.textContent = `Generated ${relativeDate(standup.generated_at || new Date())}`;
  } else {
    // Fallback standup from memory
    renderFallbackStandup(updatesEl, blockersEl, prioritiesEl, timestampEl);
  }
}

function renderFallbackStandup(updatesEl, blockersEl, prioritiesEl, timestampEl) {
  // Build from available memories
  const agentUpdates = CONFIG.AGENTS.map(agentKey => {
    const meta = AGENT_META[agentKey];
    const memory = state.memories[agentKey];
    return { agent: agentKey, summary: memory?.summary || `No activity logged in last 24h` };
  });

  if (updatesEl) {
    updatesEl.innerHTML = agentUpdates.map(u => `
      <div class="standup-agent-row">
        <div class="standup-agent-name">${escHtml(AGENT_META[u.agent]?.name || u.agent)}</div>
        <div class="standup-agent-update">${escHtml(u.summary)}</div>
      </div>`).join('');
  }

  if (blockersEl) {
    const openIssues = state.issues.filter(i => i.state === 'open');
    const blockerIssues = openIssues.filter(i =>
      i.labels.some(l => ['blocker', 'blocked', 'critical', 'bug'].includes(l.name.toLowerCase()))
    ).slice(0, 3);

    blockersEl.innerHTML = blockerIssues.length > 0
      ? blockerIssues.map(b => `
        <div class="blocker-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <span class="blocker-text">[${escHtml(b._repo)}] ${escHtml(b.title)}</span>
        </div>`).join('')
      : `<div class="empty-state" style="padding: var(--space-6)"><p style="color: var(--color-success); font-weight: 500;">✓ No blockers</p></div>`;
  }

  if (prioritiesEl) {
    const priorities = [
      'Review and respond to open GitHub issues',
      'Check CX queue for customer tickets',
      'Review agent logs in brain database',
    ];
    prioritiesEl.innerHTML = priorities.map((p, i) => `
      <div class="priority-item">
        <div class="priority-num">${i + 1}</div>
        <div class="priority-text">${escHtml(p)}</div>
      </div>`).join('');
  }

  if (timestampEl) timestampEl.textContent = `Compiled ${relativeDate(new Date())}`;
}

// ── Quick Actions ────────────────────────────────────────────
window.openCreateIssueModal = function () {
  document.getElementById('modal-create-issue').classList.add('open');
  document.getElementById('modal-create-issue').querySelector('.modal').focus?.();
};

window.closeModal = function (id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('open');
};

window.submitCreateIssue = async function () {
  const repo = document.getElementById('issue-repo').value;
  const title = document.getElementById('issue-title').value.trim();
  const body = document.getElementById('issue-body').value.trim();
  const labels = document.getElementById('issue-labels').value.trim();

  if (!title) return showToast('Title is required', 'error');
  if (!repo) return showToast('Select a repo', 'error');

  if (!state.token) {
    showToast('No GitHub token — cannot create issue', 'error');
    return;
  }

  const labelArr = labels ? labels.split(',').map(l => l.trim()).filter(Boolean) : [];

  try {
    const res = await fetch(`${CONFIG.GITHUB_API}/repos/${CONFIG.GITHUB_ORG}/${repo}/issues`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${state.token}`,
        Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      body: JSON.stringify({ title, body, labels: labelArr }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || `${res.status}`);
    }

    const issue = await res.json();
    closeModal('modal-create-issue');
    showToast(`Issue #${issue.number} created in ${repo}`, 'success');
    document.getElementById('issue-title').value = '';
    document.getElementById('issue-body').value = '';
    document.getElementById('issue-labels').value = '';
    await loadIssues();
  } catch (e) {
    showToast(`Failed to create issue: ${e.message}`, 'error');
  }
};

window.openStoreMemoryModal = function () {
  document.getElementById('modal-store-memory').classList.add('open');
};

window.submitStoreMemory = async function () {
  const key = document.getElementById('memory-key').value.trim();
  const value = document.getElementById('memory-value').value.trim();
  const agent = document.getElementById('memory-agent').value;
  if (!key || !value) return showToast('Key and value are required', 'error');

  const result = await brainPost('/memory', { key, value, agent, timestamp: new Date().toISOString() });
  if (result) {
    showToast('Memory stored', 'success');
    closeModal('modal-store-memory');
  } else {
    showToast('Brain API unavailable — memory not saved', 'error');
  }
};

window.openLogDecisionModal = function () {
  document.getElementById('modal-log-decision').classList.add('open');
};

window.submitLogDecision = async function () {
  const title = document.getElementById('decision-title').value.trim();
  const context = document.getElementById('decision-context').value.trim();
  const outcome = document.getElementById('decision-outcome').value.trim();
  if (!title || !outcome) return showToast('Title and outcome are required', 'error');

  const result = await brainPost('/decisions', {
    title,
    context,
    outcome,
    timestamp: new Date().toISOString(),
    logged_by: 'nicholas',
  });

  if (result) {
    showToast('Decision logged', 'success');
    closeModal('modal-log-decision');
  } else {
    showToast('Brain API unavailable — decision not saved', 'error');
  }
};

window.openTriggerNudgeModal = function () {
  document.getElementById('modal-trigger-nudge').classList.add('open');
};

window.triggerNudge = async function (agent) {
  const result = await brainPost('/nudge', { agent, triggered_by: 'human', timestamp: new Date().toISOString() });
  showToast(result ? `Nudged ${AGENT_META[agent]?.name || agent}` : 'Brain API unavailable', result ? 'success' : 'error');
};

window.submitTriggerNudge = async function () {
  const agent = document.getElementById('nudge-agent').value;
  const message = document.getElementById('nudge-message').value.trim();
  const result = await brainPost('/nudge', { agent, message, triggered_by: 'human', timestamp: new Date().toISOString() });
  if (result) {
    showToast(`Nudge sent to ${AGENT_META[agent]?.name || agent}`, 'success');
    closeModal('modal-trigger-nudge');
  } else {
    showToast('Brain API unavailable', 'error');
  }
};

function bindModalEvents() {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
    }
  });
}

// ── Auto Refresh ─────────────────────────────────────────────
function startAutoRefresh() {
  state.countdown = CONFIG.REFRESH_INTERVAL;

  const countdownEl = document.getElementById('countdown');
  const countdownInterval = setInterval(() => {
    state.countdown--;
    if (countdownEl) countdownEl.textContent = `${state.countdown}s`;
    if (state.countdown <= 0) {
      state.countdown = CONFIG.REFRESH_INTERVAL;
      refreshAll();
    }
  }, 1000);

  state.refreshTimer = countdownInterval;
}

window.refreshAll = async function () {
  const btn = document.getElementById('refresh-btn');
  if (btn) btn.classList.add('spinning');
  state.countdown = CONFIG.REFRESH_INTERVAL;
  await loadAllData();
  if (btn) {
    btn.classList.remove('spinning');
    showToast('Dashboard refreshed', 'success');
  }
};

// ── Sidebar Nav ──────────────────────────────────────────────
function bindSidebarNav() {
  document.querySelectorAll('.sidebar-nav a[data-section]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const sectionId = link.dataset.section;
      const section = document.getElementById(sectionId);
      if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        document.querySelectorAll('.sidebar-nav a').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
      }
    });
  });

  // Track scroll position to update active nav
  const sections = document.querySelectorAll('.dashboard-section[id]');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const link = document.querySelector(`.sidebar-nav a[data-section="${entry.target.id}"]`);
        if (link) {
          document.querySelectorAll('.sidebar-nav a').forEach(l => l.classList.remove('active'));
          link.classList.add('active');
        }
      }
    });
  }, { threshold: 0.3 });

  sections.forEach(s => observer.observe(s));
}

// ── Input Modal Helper ────────────────────────────────────────
function openInputModal(label, current, onSave) {
  const modal = document.getElementById('modal-edit-metric');
  const titleEl = document.getElementById('edit-metric-label');
  const inputEl = document.getElementById('edit-metric-value');
  if (!modal || !titleEl || !inputEl) return;
  titleEl.textContent = label;
  inputEl.value = current;
  modal.classList.add('open');

  const saveBtn = document.getElementById('edit-metric-save');
  const handler = () => {
    onSave(inputEl.value);
    modal.classList.remove('open');
    saveBtn.removeEventListener('click', handler);
  };
  saveBtn.addEventListener('click', handler);
}

// ── Utilities ────────────────────────────────────────────────
function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function relativeDate(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function contrastColor(hexColor) {
  const r = parseInt(hexColor.slice(0, 2), 16);
  const g = parseInt(hexColor.slice(2, 4), 16);
  const b = parseInt(hexColor.slice(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? '#000000' : '#ffffff';
}

function showToast(message, type = '') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type ? `toast-${type}` : ''}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}
