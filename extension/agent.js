export async function evaluateResearchPage(page, session) {
  const text = `${page.title} ${page.metaDescription} ${page.articleText}`.toLowerCase();
  
  if (text.length < 20) {
      return fallbackDecision(page, session, "Text too short to analyze");
  }

  try {
      const res = await fetch("http://localhost:8000/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, url: page.url })
      });
      
      if (!res.ok) throw new Error("API failed");
      const data = await res.json();
      
      if (data.error) {
          return fallbackDecision(page, session, "Gatekeeper rejected page");
      }
      
      const { gatekeeper, librarian } = data;
      const links = librarian?.curated_links || [];
      
      return {
          session: {
            inferredTopic: gatekeeper?.overarching_topic || session.topic || "Unknown Topic",
            userOverrideAllowed: true
          },
          pageDecision: {
            relevant: true,
            safe: true,
            scrape: true,
            reason: "Analyzed by Devil's Advocate Pipeline",
            confidence: 0.95
          },
          recommendations: {
            aligned: links.filter(l => l.perspective.toLowerCase().includes("inline") || l.perspective.toLowerCase().includes("neutral")),
            alternate: links.filter(l => l.perspective.toLowerCase().includes("counter") || l.perspective.toLowerCase().includes("opposing"))
          },
          routing: {
            sendTo: "done"
          }
      };

  } catch (e) {
      console.error("Backend error:", e);
      return fallbackDecision(page, session, "Error connecting to backend");
  }
}

function fallbackDecision(page, session, reasonText) {
  const fallback = `${page.title} ${page.metaDescription}`.trim() || "Untitled Research Topic";
  return {
    session: {
      inferredTopic: session.topic || fallback,
      userOverrideAllowed: true
    },
    pageDecision: {
      relevant: false,
      safe: true,
      scrape: false,
      reason: reasonText,
      confidence: 0.5
    },
    recommendations: {
      aligned: [],
      alternate: []
    },
    routing: { sendTo: null }
  };
}