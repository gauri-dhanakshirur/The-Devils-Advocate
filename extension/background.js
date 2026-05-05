import { getSession, updateSession, addActivity } from "./storage.js";
import { evaluateResearchPage } from "./agent.js";

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete" || !tab.url) return;

  const session = await getSession();
  if (!session?.active) return;

  if (
    tab.url.startsWith("chrome://") ||
    tab.url.startsWith("chrome-extension://")
  ) return;

  if (session.processedUrls.includes(tab.url)) {
    console.log("Duplicate skipped:", tab.url);
    return;
  }

  try {
    const page = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_PAGE" });
    if (!page) return;

    session.processedUrls.push(tab.url);
    session.stats.analyzed++;

    const agentResponse = await evaluateResearchPage(page, session);

    const inferredTopic = agentResponse.session?.inferredTopic;
    const pageDecision = agentResponse.pageDecision;
    const recommendations = agentResponse.recommendations;
    const routing = agentResponse.routing;

    // Agent controls topic unless user overrides later
    if (!session.topic && inferredTopic) {
      session.topic = inferredTopic;
    }

    // Persist recommendation state for popup
    session.recommendations = recommendations || {
      aligned: [],
      alternate: []
    };

    if (pageDecision.scrape) {
      session.stats.approved++;

      const storedPage = {
        sessionId: session.sessionId,
        topic: session.topic,
        extractedAt: Date.now(),
        page,
        pageDecision,
        routing
      };

      await chrome.storage.local.set({
        [`page_${Date.now()}`]: storedPage
      });

      await addActivity({
        type: "approved",
        title: page.title,
        reason: pageDecision.reason,
        confidence: pageDecision.confidence
      });

      // Placeholder for downstream agent routing
      console.log("Send approved page to:", routing?.sendTo);
    } else {
      session.stats.skipped++;

      await addActivity({
        type: "skipped",
        title: page.title,
        reason: pageDecision.reason,
        confidence: pageDecision.confidence
      });
    }

    await updateSession(session);

    console.log("Agent Response:", agentResponse);
  } catch (err) {
    console.error("Extraction failed:", err);
  }
});