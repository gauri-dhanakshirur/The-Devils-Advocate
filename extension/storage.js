export async function getSession() {
  try {
    const data = await chrome.storage.local.get("session");
    return data.session || null;
  } catch (e) {
    console.error("[DA Storage] Failed to get session:", e);
    return null;
  }
}

export async function startSession(topic) {
  const session = {
    active: true,
    topic: topic || "",
    sessionId: crypto.randomUUID(),
    startedAt: Date.now(),
    stats: {
      analyzed: 0,
      approved: 0,
      skipped: 0
    },
    processedUrls: [],
    activity: [],
    // Accumulated results across all pages in this session
    history: [],
    // Merged data from all analyses in session
    allCounterPerspectives: [],
    allSources: [],
    latestBiasScore: 5.0,
    latestTopic: "",
    latestOpinionsSummary: "",
    guardrailTriggered: false
  };

  await chrome.storage.local.set({ session });
  return session;
}

export async function stopSession() {
  try {
    await chrome.storage.local.remove("session");
  } catch (e) {
    console.error("[DA Storage] Failed to stop session:", e);
  }
}

export async function updateSession(session) {
  try {
    // Trim large fields to prevent storage quota issues
    if (session.processedUrls && session.processedUrls.length > 100) {
      session.processedUrls = session.processedUrls.slice(-100);
    }
    if (session.activity && session.activity.length > 50) {
      session.activity = session.activity.slice(0, 50);
    }
    // Keep only last 20 full history entries (they can be large)
    if (session.history && session.history.length > 20) {
      session.history = session.history.slice(-20);
    }
    // Cap accumulated perspectives and sources
    if (session.allCounterPerspectives && session.allCounterPerspectives.length > 30) {
      session.allCounterPerspectives = session.allCounterPerspectives.slice(-30);
    }
    if (session.allSources && session.allSources.length > 30) {
      session.allSources = session.allSources.slice(-30);
    }
    await chrome.storage.local.set({ session });
  } catch (e) {
    console.error("[DA Storage] Failed to update session:", e);
  }
}

export async function addPageResult(data, pageTitle, pageUrl) {
  try {
    const session = await getSession();
    if (!session) return;

    // Add to history
    if (!session.history) session.history = [];
    session.history.push({
      timestamp: Date.now(),
      title: pageTitle,
      url: pageUrl,
      topic: data.gatekeeper?.overarching_topic || "",
      biasScore: data.mirror?.cumulative_bias_score ?? 5.0,
    });

    // Accumulate counter-perspectives (with sources)
    const newPerspectives = data.counter_perspectives || [];
    if (!session.allCounterPerspectives) session.allCounterPerspectives = [];
    for (const cp of newPerspectives) {
      // Avoid exact duplicates by topic name
      const exists = session.allCounterPerspectives.some(
        e => e.topic.toLowerCase() === cp.topic.toLowerCase()
      );
      if (!exists) {
        session.allCounterPerspectives.push(cp);
      }
    }

    // Accumulate all curated sources
    const newLinks = data.librarian?.curated_links || [];
    if (!session.allSources) session.allSources = [];
    for (const link of newLinks) {
      const exists = session.allSources.some(e => e.url === link.url);
      if (!exists) {
        session.allSources.push(link);
      }
    }

    // Update latest session-wide fields
    session.latestBiasScore = data.mirror?.cumulative_bias_score ?? session.latestBiasScore;
    session.latestTopic = data.gatekeeper?.overarching_topic || session.latestTopic;
    session.latestOpinionsSummary = data.mirror?.opinions_summary || session.latestOpinionsSummary;
    session.guardrailTriggered = data.guardrail_triggered || false;
    session.topic = session.latestTopic;

    await updateSession(session);
  } catch (e) {
    console.error("[DA Storage] Failed to add page result:", e);
  }
}

export async function addActivity(entry) {
  try {
    const session = await getSession();
    if (!session) return;

    if (!session.activity) session.activity = [];
    session.activity.unshift({
      timestamp: Date.now(),
      ...entry
    });

    session.activity = session.activity.slice(0, 50);
    await updateSession(session);
  } catch (e) {
    console.error("[DA Storage] Failed to add activity:", e);
  }
}