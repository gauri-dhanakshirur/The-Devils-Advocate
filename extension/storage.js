export async function getSession() {
  const data = await chrome.storage.local.get("session");
  return data.session || null;
}

export async function startSession(topic) {
  const session = {
    active: true,
    topic,
    sessionId: crypto.randomUUID(),
    startedAt: Date.now(),
    stats: {
      analyzed: 0,
      approved: 0,
      skipped: 0
    },
    processedUrls: [],
    activity: []
  };

  await chrome.storage.local.set({ session });
  return session;
}

export async function stopSession() {
  await chrome.storage.local.remove("session");
}

export async function updateSession(session) {
  await chrome.storage.local.set({ session });
}

export async function addActivity(entry) {
  const session = await getSession();
  if (!session) return;

  session.activity.unshift({
    timestamp: Date.now(),
    ...entry
  });

  session.activity = session.activity.slice(0, 20);
  await updateSession(session);
}