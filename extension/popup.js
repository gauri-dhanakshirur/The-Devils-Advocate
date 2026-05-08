import { getSession, startSession, stopSession, updateSession, addPageResult } from "./storage.js";

// ── Constants ────────────────────────────────────────────────────────
const API_BASE = "http://localhost:8000";

// ── DOM References ───────────────────────────────────────────────────
const analyzeBtn = document.getElementById("analyzeBtn");
const sessionToggle = document.getElementById("sessionToggle");
const serverStatus = document.getElementById("serverStatus");
const connectionBanner = document.getElementById("connectionBanner");
const loadingState = document.getElementById("loadingState");
const errorState = document.getElementById("errorState");
const errorMessage = document.getElementById("errorMessage");
const retryBtn = document.getElementById("retryBtn");
const resultsContainer = document.getElementById("resultsContainer");
const emptyState = document.getElementById("emptyState");
const sessionBar = document.getElementById("sessionBar");
const sessionDuration = document.getElementById("sessionDuration");

// ── State ────────────────────────────────────────────────────────────
let isServerOnline = false;
let isAnalyzing = false;
let durationTimer = null;

// ── Server Health Check ──────────────────────────────────────────────
async function checkServer() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(`${API_BASE}/`, { signal: controller.signal });
    clearTimeout(timeout);
    if (res.ok) {
      isServerOnline = true;
      serverStatus.className = "status-dot online";
      serverStatus.title = "Backend connected";
      connectionBanner.classList.add("hidden");
      sessionToggle.disabled = false;
      const session = await getSession();
      if (session?.active) analyzeBtn.disabled = false;
      return true;
    }
  } catch (e) { /* not reachable */ }

  isServerOnline = false;
  serverStatus.className = "status-dot offline";
  serverStatus.title = "Backend offline";
  connectionBanner.classList.remove("hidden");
  sessionToggle.disabled = true;
  analyzeBtn.disabled = true;
  return false;
}

// ── Pipeline Animation ───────────────────────────────────────────────
function updatePipelineStep(stepNum, status) {
  const step = document.getElementById(`step${stepNum}`);
  if (!step) return;
  const statusEl = step.querySelector(".step-status");
  step.className = `pipeline-step ${status}`;
  switch (status) {
    case "active": statusEl.textContent = "processing..."; break;
    case "done": statusEl.textContent = "done"; break;
    default: statusEl.textContent = "waiting";
  }
}

function resetPipeline() {
  for (let i = 1; i <= 4; i++) updatePipelineStep(i, "");
}

// ── Extract Page Text ────────────────────────────────────────────────
async function extractCurrentPageText() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) throw new Error("No active tab found");
  if (tab.url.startsWith("chrome://") || tab.url.startsWith("chrome-extension://") || tab.url.startsWith("about:")) {
    throw new Error("Cannot analyze browser internal pages");
  }
  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
  } catch (e) { /* already injected */ }
  await new Promise(r => setTimeout(r, 200));
  const response = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_PAGE" });
  if (!response || !response.articleText) throw new Error("Could not extract page content — try refreshing");
  return { ...response, url: tab.url };
}

// ── Analyze Current Page (manual trigger) ────────────────────────────
async function analyzePage() {
  if (isAnalyzing || !isServerOnline) return;
  isAnalyzing = true;

  resultsContainer.classList.add("hidden");
  emptyState.classList.add("hidden");
  errorState.classList.add("hidden");
  loadingState.classList.remove("hidden");
  analyzeBtn.disabled = true;
  analyzeBtn.querySelector(".btn-text").textContent = "Analyzing...";
  resetPipeline();

  try {
    updatePipelineStep(1, "active");
    const page = await extractCurrentPageText();
    const text = `${page.title || ""} ${page.metaDescription || ""} ${page.articleText || ""}`.trim();
    if (text.length < 20) throw new Error("Not enough text on this page to analyze");

    updatePipelineStep(1, "done");

    // Animate pipeline steps progressively
    let currentStep = 2;
    const pipelineTimer = setInterval(() => {
      if (currentStep <= 4) {
        updatePipelineStep(currentStep, "active");
        if (currentStep > 2) updatePipelineStep(currentStep - 1, "done");
        currentStep++;
      }
    }, 2000);

    updatePipelineStep(2, "active");

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.slice(0, 12000), url: page.url || "" }),
      signal: controller.signal
    });
    clearTimeout(timeout);
    clearInterval(pipelineTimer);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: `Server error (${res.status})` }));
      throw new Error(errData.detail || `Analysis failed (${res.status})`);
    }

    const data = await res.json();
    for (let i = 1; i <= 4; i++) updatePipelineStep(i, "done");
    await new Promise(r => setTimeout(r, 400));

    // Update session
    const session = await getSession();
    if (session) {
      session.stats.analyzed++;
      if (!data.error) {
        session.stats.approved++;
        if (!session.processedUrls) session.processedUrls = [];
        session.processedUrls.push(page.url);
        await updateSession(session);
        // Accumulate into session history
        await addPageResult(data, page.title || page.url, page.url);
      } else {
        session.stats.skipped++;
        await updateSession(session);
      }
    }

    // Render full session view
    await renderSessionView();

  } catch (e) {
    loadingState.classList.add("hidden");
    errorState.classList.remove("hidden");
    errorMessage.textContent = e.name === "AbortError"
      ? "Analysis timed out — try again."
      : e.message || "Something went wrong";
  } finally {
    isAnalyzing = false;
    analyzeBtn.disabled = false;
    analyzeBtn.querySelector(".btn-text").textContent = "Analyze This Page";
  }
}

// ── Render Full Session View ─────────────────────────────────────────
async function renderSessionView() {
  const session = await getSession();
  if (!session) return;

  loadingState.classList.add("hidden");
  errorState.classList.add("hidden");

  // If no pages analyzed yet, show empty state
  if (!session.history || session.history.length === 0) {
    emptyState.classList.remove("hidden");
    resultsContainer.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  resultsContainer.classList.remove("hidden");

  // ── Research Trajectory ──
  document.getElementById("topicName").textContent = session.latestTopic || "Unknown Topic";

  const biasScore = session.latestBiasScore ?? 5.0;
  const biasPercent = (biasScore / 10) * 100;
  document.getElementById("biasValue").textContent = `${biasScore}/10`;
  const biasFill = document.getElementById("biasFill");
  biasFill.style.width = `${biasPercent}%`;
  biasFill.className = "bias-fill";
  if (biasScore >= 7) biasFill.classList.add("high");
  else if (biasScore >= 4) biasFill.classList.add("moderate");

  document.getElementById("opinionsSummary").textContent = session.latestOpinionsSummary || "";

  // ── Pages Analyzed (History) ──
  const historyList = document.getElementById("historyList");
  historyList.innerHTML = "";
  document.getElementById("historyCount").textContent = session.history.length;

  session.history.forEach((entry, i) => {
    const div = document.createElement("div");
    div.className = "history-item";
    div.onclick = () => chrome.tabs.create({ url: entry.url });
    div.innerHTML = `
      <span class="history-num">${i + 1}</span>
      <span class="history-title">${escapeHtml(entry.title || entry.url)}</span>
      <span class="history-bias">${entry.biasScore}/10</span>
    `;
    historyList.appendChild(div);
  });

  // ── Guardrail ──
  const guardrailCard = document.getElementById("guardrailCard");
  const counterCard = document.getElementById("counterCard");

  if (session.guardrailTriggered) {
    guardrailCard.classList.remove("hidden");
    counterCard.classList.add("hidden");
  } else {
    guardrailCard.classList.add("hidden");
    counterCard.classList.remove("hidden");
  }

  // ── Counter-Perspectives (as clickable links) ──
  const perspectives = session.allCounterPerspectives || [];
  document.getElementById("counterCount").textContent = perspectives.length;
  const counterList = document.getElementById("counterList");
  counterList.innerHTML = "";

  if (perspectives.length === 0) {
    counterList.innerHTML = '<p style="font-size: 11px; color: var(--text-muted); padding: 6px 0;">No counter-perspectives yet. Keep researching.</p>';
  } else {
    perspectives.forEach(cp => {
      const div = document.createElement("div");
      div.className = "counter-item";

      let sourcesHtml = "";
      const sources = cp.sources || [];
      if (sources.length > 0) {
        sourcesHtml = '<div class="counter-sources">';
        sources.forEach(s => {
          sourcesHtml += `
            <div class="counter-link" data-url="${escapeAttr(s.url || '#')}">
              <span class="counter-link-arrow">→</span>
              <span class="counter-link-title">${escapeHtml(s.title || 'Read more')}</span>
              <span class="counter-link-cred">${escapeHtml(s.credibility || '')}</span>
            </div>`;
        });
        sourcesHtml += '</div>';
      } else {
        sourcesHtml = '<p class="counter-no-sources">No source link found for this perspective</p>';
      }

      div.innerHTML = `
        <div class="counter-topic">${escapeHtml(cp.topic || "Untitled")}</div>
        <div class="counter-viewpoint">${escapeHtml(cp.viewpoint || "")}</div>
        ${sourcesHtml}
      `;
      counterList.appendChild(div);
    });

    // Attach click handlers to counter-links
    counterList.querySelectorAll(".counter-link").forEach(el => {
      el.addEventListener("click", () => {
        const url = el.getAttribute("data-url");
        if (url && url !== "#") chrome.tabs.create({ url });
      });
    });
  }

  // ── Curated Sources (all accumulated) ──
  const allSources = session.allSources || [];
  document.getElementById("sourcesCount").textContent = allSources.length;
  const sourcesList = document.getElementById("sourcesList");
  sourcesList.innerHTML = "";

  if (allSources.length === 0) {
    sourcesList.innerHTML = '<p style="font-size: 11px; color: var(--text-muted); padding: 6px 0;">No curated sources yet.</p>';
  } else {
    allSources.forEach((link, i) => {
      const div = document.createElement("div");
      div.className = "source-item";
      div.onclick = () => chrome.tabs.create({ url: link.url });

      const perspectiveClass = getPerspectiveClass(link.perspective);
      const credClass = (link.credibility || "medium").toLowerCase();

      div.innerHTML = `
        <div class="source-rank">${i + 1}</div>
        <div class="source-content">
          <div class="source-title">${escapeHtml(link.title || "Source")}</div>
          <div class="source-summary">${escapeHtml(link.summary || "")}</div>
          <div class="source-meta">
            <span class="source-tag ${perspectiveClass}">${escapeHtml(link.perspective || "Neutral")}</span>
            <span class="source-tag ${credClass}">${escapeHtml(link.credibility || "Medium")}</span>
          </div>
        </div>
      `;
      sourcesList.appendChild(div);
    });
  }

  // ── Session Stats ──
  document.getElementById("statAnalyzed").textContent = session.stats?.analyzed || 0;
  document.getElementById("statApproved").textContent = session.stats?.approved || 0;
  document.getElementById("statSkipped").textContent = session.stats?.skipped || 0;

  // Duration
  if (session.startedAt) {
    const elapsed = Math.floor((Date.now() - session.startedAt) / 1000);
    document.getElementById("statDuration").textContent = formatDuration(elapsed);
  }
}

// ── Session Toggle ───────────────────────────────────────────────────
async function toggleSession() {
  const session = await getSession();

  if (session?.active) {
    // End session
    await stopSession();
    sessionToggle.classList.remove("active");
    sessionToggle.querySelector(".btn-text").textContent = "Start Research Session";
    analyzeBtn.disabled = true;
    sessionBar.classList.add("hidden");
    resultsContainer.classList.add("hidden");
    emptyState.classList.remove("hidden");
    if (durationTimer) clearInterval(durationTimer);
  } else {
    // Start session
    await startSession("");
    sessionToggle.classList.add("active");
    sessionToggle.querySelector(".btn-text").textContent = "End Session";
    analyzeBtn.disabled = !isServerOnline;
    sessionBar.classList.remove("hidden");
    startDurationTimer();
  }
}

// ── Duration Timer ───────────────────────────────────────────────────
function startDurationTimer() {
  if (durationTimer) clearInterval(durationTimer);
  durationTimer = setInterval(async () => {
    const session = await getSession();
    if (!session?.startedAt) return;
    const elapsed = Math.floor((Date.now() - session.startedAt) / 1000);
    sessionDuration.textContent = formatDuration(elapsed);
  }, 1000);
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

// ── Restore State on Popup Open ──────────────────────────────────────
async function restoreState() {
  const session = await getSession();

  if (session?.active) {
    sessionToggle.classList.add("active");
    sessionToggle.querySelector(".btn-text").textContent = "End Session";
    analyzeBtn.disabled = !isServerOnline;
    sessionBar.classList.remove("hidden");
    startDurationTimer();

    // Render accumulated session data
    await renderSessionView();
  } else {
    emptyState.classList.remove("hidden");
  }
}

// ── Auto-refresh: poll session data for background updates ──────────
let refreshTimer = null;
function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(async () => {
    const session = await getSession();
    if (session?.active && session.history && session.history.length > 0) {
      // Only re-render if there's new data
      const counterCount = document.getElementById("counterCount");
      const currentCount = parseInt(counterCount?.textContent || "0");
      const sessionCount = (session.allCounterPerspectives || []).length;
      if (sessionCount !== currentCount) {
        await renderSessionView();
      }
      // Always update stats
      document.getElementById("statAnalyzed").textContent = session.stats?.analyzed || 0;
      document.getElementById("statApproved").textContent = session.stats?.approved || 0;
      document.getElementById("statSkipped").textContent = session.stats?.skipped || 0;
    }
  }, 3000);
}

// ── Helpers ──────────────────────────────────────────────────────────
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

function escapeAttr(str) {
  return (str || "").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function getPerspectiveClass(perspective) {
  if (!perspective) return "neutral";
  const p = perspective.toLowerCase();
  if (p.includes("counter") || p.includes("opposing")) return "counter";
  if (p.includes("inline")) return "inline";
  return "neutral";
}

// ── Event Listeners ──────────────────────────────────────────────────
analyzeBtn.addEventListener("click", analyzePage);
sessionToggle.addEventListener("click", toggleSession);
retryBtn.addEventListener("click", analyzePage);

// ── Initialize ───────────────────────────────────────────────────────
async function init() {
  await checkServer();
  await restoreState();
  startAutoRefresh();
  setInterval(checkServer, 10000);
}

init();