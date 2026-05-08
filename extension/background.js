import { getSession, updateSession, addActivity, addPageResult } from "./storage.js";

const API_BASE = "http://localhost:8000";

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

  // Skip already-processed URLs
  if (session.processedUrls && session.processedUrls.includes(tab.url)) {
    console.log("[DA] Duplicate skipped:", tab.url);
    return;
  }

  try {
    // Inject content script if needed
    try {
      await chrome.scripting.executeScript({
        target: { tabId },
        files: ["content.js"]
      });
    } catch (e) {
      // May already be injected, or restricted page
      console.log("[DA] Script injection skipped:", e.message);
    }

    // Delay for content script readiness
    await new Promise(r => setTimeout(r, 600));

    let page;
    try {
      page = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_PAGE" });
    } catch (e) {
      console.log("[DA] Cannot communicate with page:", tab.url);
      return;
    }

    if (!page || !page.articleText) {
      console.log("[DA] No extractable content from:", tab.url);
      return;
    }

    // Re-read session (may have been updated)
    const freshSession = await getSession();
    if (!freshSession?.active) return;

    // Mark as processed
    if (!freshSession.processedUrls) freshSession.processedUrls = [];
    freshSession.processedUrls.push(tab.url);
    freshSession.stats.analyzed++;
    await updateSession(freshSession);

    const text = `${page.title || ""} ${page.metaDescription || ""} ${page.articleText || ""}`.trim();

    if (text.length < 20) {
      const s = await getSession();
      if (s) { s.stats.skipped++; await updateSession(s); }
      return;
    }

    console.log("[DA] Analyzing page:", page.title?.slice(0, 60));

    // Call backend
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.slice(0, 12000), url: tab.url }),
      signal: controller.signal
    });

    clearTimeout(timeout);

    if (!res.ok) {
      console.error("[DA] API error:", res.status);
      const s = await getSession();
      if (s) {
        s.stats.skipped++;
        await updateSession(s);
      }
      await addActivity({
        type: "error",
        title: page.title || tab.url,
        reason: `API error: ${res.status}`
      });
      return;
    }

    const data = await res.json();

    if (data.error) {
      const s = await getSession();
      if (s) {
        s.stats.skipped++;
        await updateSession(s);
      }
      await addActivity({
        type: "skipped",
        title: page.title || tab.url,
        reason: data.synthesis || "Rejected by Gatekeeper"
      });
    } else {
      // Success — accumulate into session
      const s = await getSession();
      if (s) {
        s.stats.approved++;
        await updateSession(s);
      }

      // Store full result in session history
      await addPageResult(data, page.title || tab.url, tab.url);

      await addActivity({
        type: "approved",
        title: page.title || tab.url,
        reason: `Bias: ${data.mirror?.cumulative_bias_score ?? "N/A"}/10 | ${(data.counter_perspectives || []).length} counter-perspectives`
      });
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