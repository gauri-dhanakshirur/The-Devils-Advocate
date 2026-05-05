export function extractPageData() {
  const title = document.title || "";
  const url = window.location.href || "";
  const domain = window.location.hostname || "";

  const metaDescription =
    document.querySelector('meta[name="description"]')?.content || "";

  const headings = [...document.querySelectorAll("h1, h2, h3")]
    .slice(0, 10)
    .map(el => el.innerText.trim())
    .filter(Boolean);

  const articleText = (document.body?.innerText || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 8000);

  return {
    title,
    url,
    domain,
    metaDescription,
    headings,
    articleText
  };
}