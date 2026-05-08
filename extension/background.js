import { getSession, updateSession, addActivity, addPageResult, getAuthToken } from "./storage.js";

const API_BASE = "http://localhost:8000";

// ── Sync session to backend ──────────────────────────────────────────
async function syncSessionToBackend(session) {
  try {
    const token = await getAuthToken();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const payload = {
      session_id: session.sessionId,
      topic: session.latestTopic || session.topic || "",
      user_topic: session.userTopic || "",
      started_at: session.startedAt,
      bias_score: session.latestBiasScore || 5.0,
      opinions_summary: session.latestOpinionsSummary || "",
      guardrail_triggered: session.guardrailTriggered || false,
      stats: session.stats || {},
      pages: (session.history || []).map(h => ({
        url: h.url, title: h.title, topic: h.topic,
        biasScore: h.biasScore, timestamp: h.timestamp
      })),
      counter_perspectives: (session.allCounterPerspectives || []).map(cp => ({
        topic: cp.topic, viewpoint: cp.viewpoint,
        sources: (cp.sources || []).map(s => ({
          url: s.url, title: s.title, summary: s.summary,
          perspective: s.perspective, credibility: s.credibility
        }))
      })),
      sources: (session.allSources || []).map(s => ({
        url: s.url, title: s.title, summary: s.summary,
        perspective: s.perspective, credibility: s.credibility
      }))
    };

    const res = await fetch(`${API_BASE}/webapp/sync-session`, {
      method: "POST", headers, body: JSON.stringify(payload)
    });

    if (res.ok) {
      console.log("[DA] Session synced to webapp backend");
    } else {
      console.error("[DA] Sync failed:", res.status);
    }
  } catch (e) {
    console.error("[DA] Sync to backend failed:", e);
  }
}

async function endSessionOnBackend(sessionId) {
  try {
    const token = await getAuthToken();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    await fetch(`${API_BASE}/webapp/end-session/${sessionId}`, { method: "POST", headers });
  } catch (e) {
    console.error("[DA] End session on backend failed:", e);
  }
}

// ── Auto-analyze on tab update (only if session is active) ──────────
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete" || !tab.url) return;

  const session = await getSession();
  if (!session?.active) return;

  // Skip internal Chrome pages
  if (
    tab.url.startsWith("chrome://") ||
    tab.url.startsWith("chrome-extension://") ||
    tab.url.startsWith("about:") ||
    tab.url.startsWith("edge://") ||
    tab.url.startsWith("devtools://")
  ) return;

  // Step 1: High-confidence exclusion (Hostname Blacklist only — not full URL)
  const blockedHostnames = [
    "paypal.com", "amazon.com", "amazon.in", "facebook.com", "instagram.com",
    "twitter.com", "x.com", "netflix.com", "gmail.com", "mail.google.com",
    "accounts.google.com", "login.microsoftonline.com", "reddit.com"
  ];
  const blockedPathPrefixes = ["/login", "/signin", "/checkout", "/cart", "/account", "/pay"];
  try {
    const parsed = new URL(tab.url);
    const hostname = parsed.hostname.toLowerCase();
    const path = parsed.pathname.toLowerCase();
    if (blockedHostnames.some(h => hostname === h || hostname.endsWith("." + h))) {
      console.log("[DA] Skipped (Blocked hostname):", hostname);
      return;
    }
    if (blockedPathPrefixes.some(p => path.startsWith(p))) {
      console.log("[DA] Skipped (Login/checkout path):", tab.url);
      return;
    }
  } catch (e) { return; } // Invalid URL
  // Step 1b: Skip search engine results pages (SERPs) — no useful article content
  const searchPatterns = [
    /google\.[a-z.]+\/search/i,
    /bing\.com\/(search|images|videos)/i,
    /duckduckgo\.com\/\?/i,
    /yahoo\.com\/search/i,
    /search\.yahoo\.com/i,
    /yandex\.[a-z]+\/search/i,
    /baidu\.com\/s/i,
    /ecosia\.org\/search/i,
  ];
  if (searchPatterns.some(p => p.test(tab.url))) {
    console.log("[DA] Skipped (Search results page):", tab.url);
    return;
  }

  if (session.processedUrls && session.processedUrls.includes(tab.url)) {
    console.log("[DA] Duplicate skipped:", tab.url);
    return;
  }

  try {
    // Delay for content script readiness (it is already auto-injected via manifest)
    await new Promise(r => setTimeout(r, 800));

    // Step 2 & 3: Lightweight Relevance Analysis
    let meta;
    try {
      meta = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_METADATA" });
    } catch (e) {
      console.log("[DA] Cannot communicate with page for metadata:", tab.url);
      return;
    }

    if (!meta || (!meta.title && !meta.metaDescription)) {
      console.log("[DA] No metadata from:", tab.url);
      return;
    }

    // Re-read session
    const freshSession = await getSession();
    if (!freshSession?.active) return;
    
    let shouldScrape = true; // Default to scrape if it's the very first page
    const sessionTopic = freshSession.userTopic || freshSession.topic || "";

    // If we have a topic established (not the first page), do a relevance check
    if (freshSession.history && freshSession.history.length > 0 && sessionTopic) {
      try {
        const relController = new AbortController();
        const relTimeout = setTimeout(() => relController.abort(), 10000);
        
        const relRes = await fetch(`${API_BASE}/relevance-check`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...meta, session_topic: sessionTopic }),
          signal: relController.signal
        });
        clearTimeout(relTimeout);
        
        if (relRes.ok) {
          const relData = await relRes.json();
          console.log(`[DA] Relevance Check [${relData.confidence.toFixed(2)}] (${relData.decision}): ${relData.reason}`);
          if (relData.decision === "exclude") {
            shouldScrape = false;
            // Mark as skipped silently without adding history
            freshSession.stats.skipped++;
            if (!freshSession.processedUrls) freshSession.processedUrls = [];
            freshSession.processedUrls.push(tab.url);
            await updateSession(freshSession);
            return;
          }
        }
      } catch (err) {
        console.error("[DA] Relevance check failed, defaulting to scrape:", err.message);
      }
    }

    if (!shouldScrape) return;

    // Step 4: Webscrape Trigger (Extract full text)
    let page;
    try {
      page = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_PAGE" });
    } catch (e) {
      console.log("[DA] Cannot extract full page:", tab.url);
      return;
    }

    if (!page || !page.articleText || page.articleText.length < 20) {
      console.log("[DA] Not enough full text from:", tab.url);
      freshSession.stats.skipped++;
      await updateSession(freshSession);
      return;
    }

    // Mark URL as processed NOW to prevent duplicate analysis
    if (!freshSession.processedUrls) freshSession.processedUrls = [];
    freshSession.processedUrls.push(tab.url);
    await updateSession(freshSession);

    const text = page.articleText;
    console.log("[DA] Analyzing full page:", page.title?.slice(0, 60));

    // Call backend
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    const analysisTopic = freshSession.userTopic || "";

    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        text: text.slice(0, 12000), 
        url: tab.url,
        session_topic: analysisTopic
      }),
      signal: controller.signal
    });

    clearTimeout(timeout);

    if (!res.ok) {
      console.error("[DA] API error:", res.status);
      const s = await getSession();
      if (s) { s.stats.analyzed++; s.stats.skipped++; await updateSession(s); }
      await addActivity({ type: "error", title: page.title || tab.url, reason: `API error: ${res.status}` });
      return;
    }

    const data = await res.json();

    if (data.error) {
      // Gatekeeper rejected — log but don't store in history
      const s = await getSession();
      if (s) { s.stats.analyzed++; s.stats.skipped++; await updateSession(s); }
      await addActivity({
        type: "skipped",
        title: page.title || tab.url,
        reason: data.synthesis || "Rejected by Gatekeeper"
      });
    } else {
      // Success — write history FIRST (this triggers the popup update), then update stats
      await addPageResult(data, page.title || tab.url, tab.url);

      // Update stats on the freshest copy of session (after addPageResult wrote)
      const s = await getSession();
      if (s) { s.stats.analyzed++; s.stats.approved++; await updateSession(s); }

      await addActivity({
        type: "approved",
        title: page.title || tab.url,
        reason: `Bias: ${data.mirror?.cumulative_bias_score ?? "N/A"}/10 | ${(data.counter_perspectives || []).length} counter-perspectives`
      });

      // Live-sync to webapp after every successful analysis
      const latestSession = await getSession();
      if (latestSession) await syncSessionToBackend(latestSession);
    }

    console.log("[DA] Analysis complete for:", tab.url);

  } catch (err) {
    if (err.name === "AbortError") {
      console.error("[DA] Analysis timed out for:", tab.url);
    } else {
      console.error("[DA] Background analysis failed:", err);
    }
  }
});

// ── On Install ───────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
  console.log("[DA] Devil's Advocate extension installed");
});
// ── Analyze Active Tab on Session Start ──────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "ANALYZE_ACTIVE_TAB") {
    (async () => {
      try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.url) return;
        if (
          tab.url.startsWith("chrome://") ||
          tab.url.startsWith("chrome-extension://") ||
          tab.url.startsWith("about:") ||
          tab.url.startsWith("edge://")
        ) return;

        const blockedHostnames = [
          "paypal.com", "amazon.com", "amazon.in", "facebook.com", "instagram.com",
          "twitter.com", "x.com", "netflix.com", "gmail.com", "mail.google.com",
          "accounts.google.com", "login.microsoftonline.com", "reddit.com"
        ];
        try {
          const parsed = new URL(tab.url);
          const hostname = parsed.hostname.toLowerCase();
          const path = parsed.pathname.toLowerCase();
          if (blockedHostnames.some(h => hostname === h || hostname.endsWith("." + h))) return;
          if (["/login", "/signin", "/checkout", "/cart"].some(p => path.startsWith(p))) return;
        } catch (e) { return; }

        const searchPatterns = [
          /google\.[a-z.]+\/search/i, /bing\.com\/(search|images|videos)/i,
          /duckduckgo\.com\/\?/i, /yahoo\.com\/search/i,
        ];
        if (searchPatterns.some(p => p.test(tab.url))) return;

        // Wait for startSession to finish writing to storage
        await new Promise(r => setTimeout(r, 800));

        const session = await getSession();
        if (!session?.active) return;
        if (session.processedUrls?.includes(tab.url)) return;

        let page;
        try {
          page = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_PAGE" });
        } catch (e) { return; }

        if (!page?.articleText || page.articleText.length < 20) return;

        // Mark URL as processed immediately
        const s1 = await getSession();
        if (!s1) return;
        if (!s1.processedUrls) s1.processedUrls = [];
        s1.processedUrls.push(tab.url);
        await updateSession(s1);

        const analysisTopic = session.userTopic || "";
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 120000);

        const res = await fetch(`${API_BASE}/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: page.articleText.slice(0, 12000), url: tab.url, session_topic: analysisTopic }),
          signal: controller.signal
        });
        clearTimeout(timeout);

        if (!res.ok) return;
        const data = await res.json();

        if (!data.error) {
          await addPageResult(data, page.title || tab.url, tab.url);
          const s2 = await getSession();
          if (s2) { s2.stats.analyzed++; s2.stats.approved++; await updateSession(s2); }
          // Live-sync to webapp after first page
          await syncSessionToBackend(s2);
          console.log("[DA] Active tab analyzed on session start:", tab.url);
        }
      } catch (err) {
        console.error("[DA] Active tab analysis failed:", err);
      }
    })();
    return true;
  }
});

// ── End Session + Final Sync (called from popup via message) ─────────
// The popup is a short-lived context — it gets killed before async fetches
// complete. So we handle the end-session sync here in the persistent
// service worker instead.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "END_SESSION") {
    (async () => {
      try {
        const session = message.session;
        if (!session) return;

        // Sync full data first, then mark as ended
        await syncSessionToBackend(session);
        await endSessionOnBackend(session.sessionId);

        // Now clear local storage
        await chrome.storage.local.remove("session");
        console.log("[DA] Session ended and synced to webapp");
        sendResponse({ success: true });
      } catch (err) {
        console.error("[DA] End session failed:", err);
        sendResponse({ success: false });
      }
    })();
    return true; // Keep message channel open for async response
  }

  if (message.type === "SYNC_SESSION") {
    (async () => {
      try {
        const session = await getSession();
        if (session) await syncSessionToBackend(session);
        sendResponse({ success: true });
      } catch (err) {
        console.error("[DA] Manual sync failed:", err);
        sendResponse({ success: false });
      }
    })();
    return true;
  }
});
