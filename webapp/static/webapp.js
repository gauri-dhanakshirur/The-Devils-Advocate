// Devil's Advocate — Webapp JavaScript
"use strict";

const API_BASE = "http://localhost:8000";

// ── State ─────────────────────────────────────────────────────────────
let authToken  = localStorage.getItem("da_token") || null;
let currentUser = null;
let currentSessionId = null;
let currentPageIdForCitation = null;

// ── Helpers ───────────────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}

function formatDuration(seconds) {
  if (!seconds) return "0:00";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
  return `${m}:${String(s).padStart(2,"0")}`;
}

function authHeaders() {
  const h = { "Content-Type": "application/json" };
  if (authToken) h["Authorization"] = `Bearer ${authToken}`;
  return h;
}

function saveToken(t)  { authToken = t; localStorage.setItem("da_token", t); }
function clearToken()  { authToken = null; localStorage.removeItem("da_token"); }

// ── Screen switching ──────────────────────────────────────────────────
function showAuth() {
  $("authScreen").style.display = "flex";
  $("mainApp").style.display    = "none";
}

function showApp(user) {
  currentUser = user;
  $("authScreen").style.display = "none";
  $("mainApp").style.display    = "flex";
  $("userNameDisplay").textContent = user.name || user.email;
  loadSessions();
}

// ── Auth error display ────────────────────────────────────────────────
function showErr(id, msg) {
  const el = $(id);
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
}
function hideErr(id) { $(id)?.classList.add("hidden"); }

// ── Login ─────────────────────────────────────────────────────────────
async function doLogin() {
  hideErr("loginError");
  const email    = $("loginEmail").value.trim();
  const password = $("loginPassword").value;
  if (!email || !password) { showErr("loginError", "Please fill in all fields."); return; }

  const btn = $("loginBtn");
  btn.textContent = "Signing in…"; btn.disabled = true;

  try {
    const res  = await fetch(`${API_BASE}/webapp/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) { showErr("loginError", data.detail || "Login failed."); return; }

    saveToken(data.access_token);
    const me = await fetch(`${API_BASE}/webapp/auth/me`, { headers: authHeaders() });
    showApp(await me.json());
  } catch {
    showErr("loginError", "Cannot reach server. Make sure python main.py is running.");
  } finally {
    btn.textContent = "Sign In"; btn.disabled = false;
  }
}

// ── Register ──────────────────────────────────────────────────────────
async function doRegister() {
  hideErr("registerError");
  const name     = $("registerName").value.trim();
  const email    = $("registerEmail").value.trim();
  const password = $("registerPassword").value;
  if (!email || !password) { showErr("registerError", "Email and password are required."); return; }
  if (password.length < 6) { showErr("registerError", "Password must be at least 6 characters."); return; }

  const btn = $("registerBtn");
  btn.textContent = "Creating…"; btn.disabled = true;

  try {
    const res  = await fetch(`${API_BASE}/webapp/auth/register`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name })
    });
    const data = await res.json();
    if (!res.ok) { showErr("registerError", data.detail || "Registration failed."); return; }

    saveToken(data.access_token);
    const me = await fetch(`${API_BASE}/webapp/auth/me`, { headers: authHeaders() });
    showApp(await me.json());
  } catch {
    showErr("registerError", "Cannot reach server. Make sure python main.py is running.");
  } finally {
    btn.textContent = "Create Account"; btn.disabled = false;
  }
}

// ── Navigation ────────────────────────────────────────────────────────
function switchView(view) {
  ["sessions","detail","analytics"].forEach(v => {
    const el = $(v + "View");
    if (el) el.classList.toggle("active", v === view);
  });
  document.querySelectorAll(".nav-link").forEach(l =>
    l.classList.toggle("active", l.getAttribute("data-view") === view)
  );
  if (view === "sessions") loadSessions();
  else if (view === "analytics") loadAnalytics();
}

// ── Load Sessions ─────────────────────────────────────────────────────
async function loadSessions() {
  const list = $("sessionsList");
  if (!list) return;
  list.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading sessions…</span></div>`;

  try {
    const res  = await fetch(`${API_BASE}/webapp/sessions`, { headers: authHeaders() });
    if (res.status === 401) { clearToken(); showAuth(); return; }
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();

    const s = data.global_stats;
    $("totalSessions").textContent = s.total_sessions;
    $("totalPages").textContent    = s.total_pages;
    $("totalTime").textContent     = formatDuration(s.total_time_seconds);
    $("avgBias").textContent       = `${s.avg_bias_score}/10`;

    if (!data.sessions.length) {
      list.innerHTML = `<div class="empty-state"><h3>No Sessions Yet</h3><p>Start a research session in the browser extension to see it here.</p></div>`;
      return;
    }

    list.innerHTML = data.sessions.map(renderSessionCard).join("");

    list.querySelectorAll(".session-card").forEach(card => {
      card.addEventListener("click", e => {
        if (e.target.classList.contains("btn-small")) return;
        viewSessionDetail(card.getAttribute("data-session-id"));
      });
    });

    list.querySelectorAll(".delete-session-btn").forEach(btn => {
      btn.addEventListener("click", async e => {
        e.stopPropagation();
        if (confirm("Delete this session? This cannot be undone."))
          await deleteSession(btn.getAttribute("data-session-id"));
      });
    });

  } catch (err) {
    list.innerHTML = `<div class="empty-state"><h3>Error Loading Sessions</h3><p>${escapeHtml(err.message)}</p></div>`;
  }
}

function renderSessionCard(session) {
  const date    = new Date(session.started_at);
  const dateStr = date.toLocaleDateString("en-US", { month:"short", day:"numeric", year:"numeric" });
  const timeStr = date.toLocaleTimeString("en-US", { hour:"2-digit", minute:"2-digit" });
  const dur     = session.duration_seconds ? formatDuration(session.duration_seconds) : "In progress";
  const bias    = session.bias_score || 5.0;
  const topic   = session.user_topic || session.topic || "Untitled Session";
  const color   = bias >= 7 ? "var(--accent)" : bias >= 4 ? "var(--warning)" : "var(--success)";

  return `
    <div class="session-card" data-session-id="${session.session_id}">
      <div class="session-header">
        <div>
          <div class="session-topic">${escapeHtml(topic)}</div>
          <div class="session-meta">
            <span>${dateStr} • ${timeStr}</span>
            <span>${dur}</span>
            <span>${session.stats_approved || 0} pages</span>
          </div>
        </div>
        <div class="session-bias" style="color:${color}">${bias}/10</div>
      </div>
      <div class="bias-bar"><div class="bias-fill" style="width:${(bias/10)*100}%"></div></div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);margin-top:4px">
        <span>Balanced</span><span>Echo Chamber</span>
      </div>
      <div class="session-actions" style="margin-top:12px">
        <button class="btn-small delete-session-btn danger" data-session-id="${session.session_id}">Delete</button>
      </div>
    </div>`;
}

// ── Session Detail ────────────────────────────────────────────────────
async function viewSessionDetail(sessionId) {
  currentSessionId = sessionId;
  switchView("detail");
  const dc = $("detailContent");
  dc.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;

  try {
    const res  = await fetch(`${API_BASE}/webapp/session/${sessionId}`, { headers: authHeaders() });
    if (res.status === 401) { clearToken(); showAuth(); return; }
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();
    dc.innerHTML = renderSessionDetail(data);
    attachDetailHandlers();
  } catch (err) {
    dc.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${escapeHtml(err.message)}</p></div>`;
  }
}

function renderSessionDetail(data) {
  const session  = data.session;
  const pages    = data.pages || [];
  const cps      = data.counter_perspectives || [];
  const sources  = data.sources || [];
  const citations = data.citations || [];

  const topic    = session.user_topic || session.topic || "Untitled Session";
  const bias     = session.bias_score || 5.0;
  const date     = new Date(session.started_at).toLocaleDateString("en-US", { month:"long", day:"numeric", year:"numeric" });
  const duration = session.duration_seconds ? formatDuration(session.duration_seconds) : "In progress";
  const color    = bias >= 7 ? "var(--accent)" : bias >= 4 ? "var(--warning)" : "var(--success)";

  const alignedPages  = pages.filter(p => (p.bias_score || 5) >= 5);
  const alternatPages = pages.filter(p => (p.bias_score || 5) < 5);

  return `
    <div class="detail-header">
      <div class="detail-topic">${escapeHtml(topic)}</div>
      ${session.opinions_summary ? `<div class="detail-summary">${escapeHtml(session.opinions_summary)}</div>` : ""}
      <div class="bias-bar" style="margin:16px 0 4px"><div class="bias-fill" style="width:${(bias/10)*100}%"></div></div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);margin-bottom:16px">
        <span>Balanced</span><span>Echo Chamber</span>
      </div>
      <div class="detail-grid">
        <div><div class="detail-stat-label">BIAS SCORE</div><div class="detail-stat-value" style="color:${color}">${bias}/10</div></div>
        <div><div class="detail-stat-label">DATE</div><div class="detail-stat-value" style="font-size:14px">${date}</div></div>
        <div><div class="detail-stat-label">DURATION</div><div class="detail-stat-value" style="font-size:15px">${duration}</div></div>
        <div><div class="detail-stat-label">PAGES</div><div class="detail-stat-value">${session.stats_analyzed || 0}</div></div>
        <div><div class="detail-stat-label">APPROVED</div><div class="detail-stat-value">${session.stats_approved || 0}</div></div>
        <div><div class="detail-stat-label">FILTERED</div><div class="detail-stat-value">${session.stats_skipped || 0}</div></div>
      </div>
    </div>

    <div class="tab-bar">
      <button class="tab-btn active" data-tab="pages">Pages <span class="badge">${pages.length}</span></button>
      <button class="tab-btn" data-tab="aligned">Aligned Research <span class="badge">${alignedPages.length}</span></button>
      <button class="tab-btn" data-tab="alternate">Alternate Research <span class="badge">${alternatPages.length}</span></button>
      <button class="tab-btn" data-tab="counter">Counter-Perspectives <span class="badge">${cps.length}</span></button>
      <button class="tab-btn" data-tab="sources">Sources <span class="badge">${sources.length}</span></button>
      ${citations.length ? `<button class="tab-btn" data-tab="citations">Citations <span class="badge">${citations.length}</span></button>` : ""}
    </div>

    <div class="tab-panel active" data-panel="pages">
      ${!pages.length ? '<p style="color:var(--text-muted);font-size:13px;padding:16px 0">No pages analyzed yet.</p>' : ""}
      ${pages.map(p => `
        <div class="page-item">
          <div class="page-info">
            <div class="page-title-text">${escapeHtml(p.title || "Untitled")}</div>
            <a href="${escapeHtml(p.url)}" target="_blank" class="page-url">${escapeHtml(p.url)}</a>
          </div>
          <div class="page-actions">
            <button class="btn-small cite-btn ${p.is_citation ? "active-cite" : ""}"
              data-page-id="${p.id}" data-page-title="${escapeHtml(p.title || p.url)}">
              ${p.is_citation ? "✓ Cited" : "Cite"}
            </button>
          </div>
        </div>`).join("")}
    </div>

    <div class="tab-panel" data-panel="aligned">
      <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px">Pages that align with your primary research direction.</p>
      ${!alignedPages.length ? '<p style="color:var(--text-muted);font-size:13px">None found.</p>' : ""}
      ${alignedPages.map(p => `
        <div class="research-item aligned">
          <span class="research-tag aligned">ALIGNED</span>
          <div class="research-info">
            <div class="research-title"><a href="${escapeHtml(p.url)}" target="_blank">${escapeHtml(p.title || "Untitled")}</a></div>
            <div class="research-meta">Bias score: ${p.bias_score || "—"}/10</div>
          </div>
        </div>`).join("")}
    </div>

    <div class="tab-panel" data-panel="alternate">
      <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px">Pages representing alternative or opposing perspectives.</p>
      ${!alternatPages.length ? '<p style="color:var(--text-muted);font-size:13px">None found. Try browsing more diverse sources.</p>' : ""}
      ${alternatPages.map(p => `
        <div class="research-item alternate">
          <span class="research-tag alternate">ALTERNATE</span>
          <div class="research-info">
            <div class="research-title"><a href="${escapeHtml(p.url)}" target="_blank">${escapeHtml(p.title || "Untitled")}</a></div>
            <div class="research-meta">Bias score: ${p.bias_score || "—"}/10</div>
          </div>
        </div>`).join("")}
    </div>

    <div class="tab-panel" data-panel="counter">
      ${session.guardrail_triggered ? `<div class="guardrail-notice">Truth Guardrail activated — this topic is largely objective fact. No artificial counter-arguments were generated.</div>` : ""}
      ${!cps.length ? '<p style="color:var(--text-muted);font-size:13px">No counter-perspectives generated yet.</p>' : ""}
      ${cps.map(cp => `
        <div class="counter-item">
          <div class="counter-topic">${escapeHtml(cp.topic)}</div>
          <div class="counter-viewpoint">${escapeHtml(cp.viewpoint || "")}</div>
          ${cp.sources && cp.sources.length ? `
            <div class="counter-sources">
              ${cp.sources.map(s => `
                <a href="${escapeHtml(s.url)}" target="_blank" class="source-link" data-source-id="${s.id}">
                  <span class="source-arrow">→</span>
                  <span style="flex:1">${escapeHtml(s.title || "Source")}</span>
                  <span class="source-cred">${escapeHtml(s.credibility || "")}</span>
                </a>`).join("")}
            </div>` : ""}
        </div>`).join("")}
    </div>

    <div class="tab-panel" data-panel="sources">
      ${!sources.length ? '<p style="color:var(--text-muted);font-size:13px">No curated sources yet.</p>' : ""}
      ${sources.map(s => `
        <div class="research-item counter-opinion">
          <span class="research-tag counter-opinion">${escapeHtml(s.perspective || "SOURCE")}</span>
          <div class="research-info">
            <div class="research-title">
              <a href="${escapeHtml(s.url)}" target="_blank" class="source-link" data-source-id="${s.id}">${escapeHtml(s.title || "Source")}</a>
            </div>
            <div class="research-summary">${escapeHtml(s.summary || "")}</div>
            <div class="research-meta">Credibility: ${escapeHtml(s.credibility || "Medium")}</div>
          </div>
        </div>`).join("")}
    </div>

    ${citations.length ? `
    <div class="tab-panel" data-panel="citations">
      ${citations.map(p => `
        <div class="page-item">
          <div class="page-info">
            <div class="page-title-text">${escapeHtml(p.title || "Untitled")}</div>
            <a href="${escapeHtml(p.url)}" target="_blank" class="page-url">${escapeHtml(p.url)}</a>
            ${p.citation_note ? `<p style="font-size:12px;color:var(--text-secondary);margin-top:4px">${escapeHtml(p.citation_note)}</p>` : ""}
          </div>
        </div>`).join("")}
    </div>` : ""}
  `;
}

function attachDetailHandlers() {
  // Tab switching
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-tab");
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      document.querySelector(`.tab-panel[data-panel="${tab}"]`)?.classList.add("active");
    });
  });

  // Citations
  document.querySelectorAll(".cite-btn").forEach(btn => {
    btn.addEventListener("click", () =>
      openCitationModal(parseInt(btn.getAttribute("data-page-id")), btn.getAttribute("data-page-title"))
    );
  });

  // Source visit tracking
  document.querySelectorAll(".source-link[data-source-id]").forEach(link => {
    link.addEventListener("click", async () => {
      const id = parseInt(link.getAttribute("data-source-id"));
      if (id) await fetch(`${API_BASE}/webapp/source/${id}/visited`, { method: "POST" }).catch(() => {});
    });
  });
}

// ── Delete Session ────────────────────────────────────────────────────
async function deleteSession(sessionId) {
  try {
    await fetch(`${API_BASE}/webapp/session/${sessionId}`, { method: "DELETE", headers: authHeaders() });
    loadSessions();
  } catch { alert("Failed to delete session"); }
}

// ── Citation Modal ────────────────────────────────────────────────────
function openCitationModal(pageId, pageTitle) {
  currentPageIdForCitation = pageId;
  $("citationPageTitle").textContent = pageTitle;
  $("citationNote").value = "";
  $("citationModal").classList.remove("hidden");
}
function closeCitationModal() {
  $("citationModal").classList.add("hidden");
  currentPageIdForCitation = null;
}

// ── Analytics ─────────────────────────────────────────────────────────
let nebulaGraph = null;
let nebulaWs = null;

async function loadAnalytics() {
  const el = $("analyticsContent");
  if (!el) return;
  el.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;
  try {
    const res   = await fetch(`${API_BASE}/webapp/stats`, { headers: authHeaders() });
    if (res.status === 401) { clearToken(); showAuth(); return; }
    const stats = await res.json();
    el.innerHTML = `
      <div class="section-card">
        <div class="section-card-title">Global Statistics</div>
        <div class="detail-grid">
          <div><div class="detail-stat-label">TOTAL SESSIONS</div><div class="detail-stat-value">${stats.total_sessions}</div></div>
          <div><div class="detail-stat-label">TOTAL PAGES</div><div class="detail-stat-value">${stats.total_pages}</div></div>
          <div><div class="detail-stat-label">TOTAL TIME</div><div class="detail-stat-value">${formatDuration(stats.total_time_seconds)}</div></div>
          <div><div class="detail-stat-label">AVG BIAS</div><div class="detail-stat-value bias-highlight">${stats.avg_bias_score}/10</div></div>
        </div>
      </div>`;
  } catch (err) {
    el.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${escapeHtml(err.message)}</p></div>`;
  }

  // Populate the nebula session selector
  await populateNebulaSessionSelect();
}

async function populateNebulaSessionSelect() {
  const sel = $("nebulaSessionSelect");
  if (!sel) return;
  try {
    const res = await fetch(`${API_BASE}/webapp/sessions?limit=50`, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    sel.innerHTML = '<option value="">— Choose a session —</option>';
    for (const s of data.sessions) {
      const topic = s.user_topic || s.topic || "Untitled";
      const date  = new Date(s.started_at).toLocaleDateString("en-US", { month:"short", day:"numeric" });
      sel.innerHTML += `<option value="${s.session_id}">${escapeHtml(topic)} (${date})</option>`;
    }
  } catch (e) {
    console.error("Failed to populate nebula sessions:", e);
  }
}

async function launchNebula() {
  const sessionId = $("nebulaSessionSelect")?.value;
  if (!sessionId) return;

  const container = $("nebulaContainer");
  const metricsEl = $("nebulaMetrics");
  const legendEl  = $("nebulaLegend");
  const emptyEl   = $("nebulaEmpty");
  const graphEl   = $("nebulaGraph");

  // Reset
  container.classList.add("hidden");
  metricsEl.classList.add("hidden");
  legendEl.classList.add("hidden");
  emptyEl.classList.add("hidden");
  graphEl.innerHTML = '';

  if (nebulaWs) {
    nebulaWs.close();
    nebulaWs = null;
  }

  try {
    const wsUrl = API_BASE.replace(/^http/, "ws") + `/webapp/ws/nebula/${sessionId}`;
    nebulaWs = new WebSocket(wsUrl);

    nebulaWs.onmessage = (event) => {
      try {
        const nebula = JSON.parse(event.data);
        if (!nebula.nodes || nebula.nodes.length === 0) {
          emptyEl.classList.remove("hidden");
          return;
        }

        // Render metrics
        const m = nebula.metrics;
        metricsEl.innerHTML = `
          <div class="nebula-metric">
            <div class="nebula-metric-label">NODES</div>
            <div class="nebula-metric-value">${m.total_nodes}</div>
          </div>
          <div class="nebula-metric">
            <div class="nebula-metric-label">EDGES</div>
            <div class="nebula-metric-value">${m.total_edges}</div>
          </div>
          <div class="nebula-metric">
            <div class="nebula-metric-label">DIAMETER</div>
            <div class="nebula-metric-value ${m.diameter >= 3 ? 'good' : m.diameter >= 1 ? 'warn' : 'bad'}">${m.diameter}</div>
          </div>
          <div class="nebula-metric">
            <div class="nebula-metric-label">BRIDGES</div>
            <div class="nebula-metric-value good">${m.bridge_nodes}</div>
          </div>
          <div class="nebula-metric">
            <div class="nebula-metric-label">GHOST NODES</div>
            <div class="nebula-metric-value bad">${m.ghost_nodes}</div>
          </div>
          <div class="nebula-metric">
            <div class="nebula-metric-label">EXPOSURE</div>
            <div class="nebula-metric-value ${m.exposure_score >= 50 ? 'good' : m.exposure_score >= 20 ? 'warn' : 'bad'}">${m.exposure_score}%</div>
          </div>
          <div class="nebula-metric">
            <div class="nebula-metric-label">ECHO RISK</div>
            <div class="nebula-metric-value ${m.echo_chamber_risk >= 60 ? 'bad' : m.echo_chamber_risk >= 30 ? 'warn' : 'good'}">${m.echo_chamber_risk}%</div>
          </div>
          <div class="nebula-metric">
            <div class="nebula-metric-label">BIAS SCORE</div>
            <div class="nebula-metric-value ${m.session_bias_score >= 7 ? 'bad' : m.session_bias_score >= 4 ? 'warn' : 'good'}">${m.session_bias_score}</div>
          </div>
        `;
        metricsEl.classList.remove("hidden");
        legendEl.classList.remove("hidden");
        container.classList.remove("hidden");

        // Render force graph
        renderNebulaGraph(nebula, graphEl);
      } catch (e) {
        console.error("Failed to parse Nebula update", e);
      }
    };

    nebulaWs.onerror = (err) => {
      console.error("WebSocket error", err);
      emptyEl.innerHTML = `<p>WebSocket Error. Check console.</p>`;
      emptyEl.classList.remove("hidden");
    };

  } catch (err) {
    emptyEl.innerHTML = `<p>Error: ${escapeHtml(err.message)}</p>`;
    emptyEl.classList.remove("hidden");
  }
}

function renderNebulaGraph(nebula, containerEl) {
  if (nebulaGraph) {
    nebulaGraph._destructor && nebulaGraph._destructor();
    nebulaGraph = null;
  }
  containerEl.innerHTML = '';

  const width  = containerEl.clientWidth || 800;
  const height = 550;

  const graphData = {
    nodes: nebula.nodes.map(n => ({ ...n })),
    links: nebula.links.map(l => ({ ...l }))
  };

  nebulaGraph = ForceGraph()
    (containerEl)
    .width(width)
    .height(height)
    .graphData(graphData)
    .backgroundColor('transparent')
    .nodeLabel(n => '')
    .nodeVal(n => n.val || 6)
    .nodeColor(n => n.color || '#f59e0b')
    .nodeCanvasObjectMode(() => 'after')
    .nodeCanvasObject((node, ctx, globalScale) => {
      // Draw label
      const label = node.label || '';
      const fontSize = Math.max(10 / globalScale, 3);
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.fillStyle = node.type === 'ghost' ? 'rgba(239,68,68,0.8)' : 'rgba(232,232,240,0.85)';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      const truncLabel = label.length > 25 ? label.slice(0, 22) + '…' : label;
      ctx.fillText(truncLabel, node.x, node.y + (node.val || 6) / globalScale + 2);

      // Draw bridge indicator
      if (node.is_bridge) {
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 2 / globalScale;
        ctx.beginPath();
        ctx.arc(node.x, node.y, (node.val || 6) / globalScale + 3, 0, 2 * Math.PI);
        ctx.stroke();
      }

      // Draw ghost dashed ring
      if (node.type === 'ghost') {
        ctx.strokeStyle = 'rgba(239,68,68,0.5)';
        ctx.lineWidth = 1.5 / globalScale;
        ctx.setLineDash([3 / globalScale, 3 / globalScale]);
        ctx.beginPath();
        ctx.arc(node.x, node.y, (node.val || 6) / globalScale + 4, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    })
    .linkWidth(l => l.width || 1)
    .linkColor(l => l.color || 'rgba(139,92,246,0.3)')
    .linkLineDash(l => l.dashed ? [4, 4] : null)
    .onNodeClick((node) => {
      if (node.type === 'ghost' && node.sources && node.sources.length > 0) {
        window.open(node.sources[0].url, '_blank');
      } else if (node.url) {
        window.open(node.url, '_blank');
      }
    })
    .onNodeHover((node) => {
      containerEl.style.cursor = node ? 'pointer' : 'default';
    })
    .d3Force('charge').strength(-120);

  // Warm up simulation
  nebulaGraph.d3Force('link').distance(l => {
    const sim = l.similarity || 0.5;
    return 150 * (1 - sim);
  });

  // Cooldown after settling
  setTimeout(() => {
    if (nebulaGraph) nebulaGraph.cooldownTicks(0);
  }, 5000);
}

// ── Boot ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {

  // Auth form toggles
  $("showRegister")?.addEventListener("click", e => {
    e.preventDefault();
    $("loginForm").classList.add("hidden");
    $("registerForm").classList.remove("hidden");
  });
  $("showLogin")?.addEventListener("click", e => {
    e.preventDefault();
    $("registerForm").classList.add("hidden");
    $("loginForm").classList.remove("hidden");
  });

  // Auth buttons
  $("loginBtn")?.addEventListener("click", doLogin);
  $("loginPassword")?.addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });
  $("registerBtn")?.addEventListener("click", doRegister);
  $("registerPassword")?.addEventListener("keydown", e => { if (e.key === "Enter") doRegister(); });

  // Logout
  $("logoutBtn")?.addEventListener("click", () => { clearToken(); showAuth(); });

  // Nav links
  document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      switchView(link.getAttribute("data-view"));
    });
  });

  // Back button
  $("backBtn")?.addEventListener("click", () => switchView("sessions"));

  // Citation modal
  $("modalBackdrop")?.addEventListener("click", closeCitationModal);
  $("modalClose")?.addEventListener("click", closeCitationModal);
  $("cancelCitation")?.addEventListener("click", closeCitationModal);
  $("saveCitation")?.addEventListener("click", async () => {
    if (!currentPageIdForCitation) return;
    try {
      await fetch(`${API_BASE}/webapp/citation`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ page_id: currentPageIdForCitation, note: $("citationNote").value.trim() })
      });
      closeCitationModal();
      viewSessionDetail(currentSessionId);
    } catch { alert("Failed to save citation"); }
  });

  // Bias explainer toggle
  $("explainerToggle")?.addEventListener("click", () => {
    $("explainerBody")?.classList.toggle("open");
    document.querySelector(".explainer-chevron")?.classList.toggle("open");
  });

  // Nebula controls
  $("loadNebulaBtn")?.addEventListener("click", launchNebula);
  $("nebulaSessionSelect")?.addEventListener("change", () => {
    // Reset nebula when session changes
    $("nebulaContainer")?.classList.add("hidden");
    $("nebulaMetrics")?.classList.add("hidden");
    $("nebulaLegend")?.classList.add("hidden");
    $("nebulaEmpty")?.classList.add("hidden");
  });

  // Check existing token
  if (authToken) {
    try {
      const res = await fetch(`${API_BASE}/webapp/auth/me`, { headers: authHeaders() });
      if (res.ok) { showApp(await res.json()); return; }
    } catch {}
    clearToken();
  }
  showAuth();
});
