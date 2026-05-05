import { getSession, startSession, stopSession, updateSession } from "./storage.js";

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const overrideBtn = document.getElementById("overrideBtn");
const topicOverride = document.getElementById("topicOverride");

async function render() {
  const session = await getSession();
  startBtn.classList.toggle("active", !!session?.active);
  
  document.getElementById("status").textContent = session?.active
    ? "Session Active"
    : "No active session";

  document.getElementById("topicDisplay").textContent =
    session?.topic || "Awaiting topic inference...";

  document.getElementById("analyzed").textContent = session?.stats?.analyzed || 0;
  document.getElementById("approved").textContent = session?.stats?.approved || 0;
  document.getElementById("skipped").textContent = session?.stats?.skipped || 0;

  const activity = document.getElementById("activity");
  activity.innerHTML = "";

  (session?.activity || []).forEach(item => {
    const li = document.createElement("li");
    li.innerHTML = `
      <strong>${item.type === "approved" ? "Approved" : "Skipped"}</strong>
      <span>${item.title || "Untitled Page"}</span>
      <small>${item.reason || "No reason available"}</small>
      <small>Confidence: ${Math.round((item.confidence || 0) * 100)}%</small>
    `;
    activity.appendChild(li);
  });

  const alignedList = document.getElementById("alignedList");
  alignedList.innerHTML = "";

  (session?.recommendations?.aligned || []).forEach(item => {
    const li = document.createElement("li");
    li.innerHTML = `<a href="${item.url}" target="_blank">${item.title}</a>`;
    alignedList.appendChild(li);
  });

  const alternateList = document.getElementById("alternateList");
  alternateList.innerHTML = "";

  (session?.recommendations?.alternate || []).forEach(item => {
    const li = document.createElement("li");
    li.innerHTML = `<a href="${item.url}" target="_blank">${item.title}</a>`;
    alternateList.appendChild(li);
  });
}

startBtn.addEventListener("click", async () => {
  await startSession("");
  render();
});

stopBtn.addEventListener("click", async () => {
  await stopSession();
  render();
});

overrideBtn.addEventListener("click", async () => {
  const session = await getSession();
  if (!session) return;

  const newTopic = topicOverride.value.trim();
  if (!newTopic) return;

  session.topic = newTopic;
  await updateSession(session);
  topicOverride.value = "";
  render();
});

// Handle link clicks inside popup safely
document.addEventListener('click', function(e) {
  if (e.target.tagName === 'A' && e.target.href) {
    e.preventDefault();
    chrome.tabs.create({ url: e.target.href });
  }
});

render();