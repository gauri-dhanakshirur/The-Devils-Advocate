// Devil's Advocate — Content Script
// Extracts meaningful text from the current page for analysis

function extractMetadata() {
  const title = document.title || "";
  const url = window.location.href || "";
  const domain = window.location.hostname || "";

  const metaDescription =
    document.querySelector('meta[name="description"]')?.content || "";

  // Extract headings for context
  const headings = [...document.querySelectorAll("h1, h2, h3")]
    .slice(0, 15)
    .map(el => el.innerText.trim())
    .filter(Boolean);

  return { title, url, domain, metaDescription, headings };
}

function extractPageData() {
  const meta = extractMetadata();

  // Try to find the main article content first
  let articleText = "";
  
  // Priority 1: <article> tag
  const article = document.querySelector("article");
  if (article) {
    articleText = article.innerText;
  }
  
  // Priority 2: main content area
  if (!articleText) {
    const main = document.querySelector("main, [role='main'], .post-content, .article-body, .entry-content, #content");
    if (main) {
      articleText = main.innerText;
    }
  }
  
  // Priority 3: Largest text block
  if (!articleText) {
    const paragraphs = [...document.querySelectorAll("p")];
    if (paragraphs.length > 0) {
      articleText = paragraphs.map(p => p.innerText.trim()).filter(t => t.length > 30).join("\n\n");
    }
  }
  
  // Fallback: body text
  if (!articleText) {
    articleText = document.body?.innerText || "";
  }

  // Clean and truncate
  articleText = articleText
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 10000);

  return {
    ...meta,
    articleText
  };
}

// Listen for extraction requests
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "EXTRACT_PAGE") {
    try {
      const data = extractPageData();
      sendResponse(data);
    } catch (e) {
      console.error("[DA Content] Extraction error:", e);
      sendResponse({ title: document.title, url: location.href, domain: location.hostname, metaDescription: "", headings: [], articleText: "" });
    }
  } else if (message.type === "EXTRACT_METADATA") {
    try {
      const data = extractMetadata();
      sendResponse(data);
    } catch (e) {
      console.error("[DA Content] Metadata extraction error:", e);
      sendResponse({ title: document.title, url: location.href, domain: location.hostname, metaDescription: "", headings: [] });
    }
  }
  return true; // Keep the message channel open for async response
});