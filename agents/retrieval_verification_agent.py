"""
Devil's Advocate — Agent 4: Retrieval & Verification Agent (The "Librarian")
Connects the theoretical counter-arguments to real-world evidence.
"""

import json
import logging
from serpapi import GoogleSearch
from agents.base_agent import BaseAgent
from config import settings

logger = logging.getLogger("librarian")

SYSTEM_PROMPT = """You are the Retrieval & Verification Agent (The Librarian).

Instructions:
1. Convert the provided counter-topics into precise Google search queries.
2. Find credible external links that support these alternative perspectives.
3. If applicable, also find 1-2 sources inline with the current research to provide a complete picture.

Respond in strict JSON:
{
  "queries": ["...", "...", "..."]
}
Do NOT add commentary outside the JSON."""

RANKING_PROMPT = """You are the Retrieval & Verification Agent.
Filter and rank the following raw search results based on credibility, relevance to the session, and diversity.

Provide summaries for both counter-topics and inline topics.
CRITICAL: Do NOT include titles or URLs in your output. Only provide the "result_id" (integer 1-12) of the best links, along with their perspective and summary.

Respond in strict JSON:
{
  "curated_links": [
    {
      "result_id": 1,
      "perspective": "Counter-Opinion | Inline",
      "summary": "...",
      "credibility": "High | Medium | Low"
    }
  ]
}
Do NOT add commentary outside the JSON."""


class RetrievalVerificationAgent(BaseAgent):
    """
    Skill: tools.webSearch (powered by SerpAPI).
    Search Logic & Ranking based on credibility and diversity.
    """
    def __init__(self):
        super().__init__(name="RetrievalVerificationAgent", system_prompt=SYSTEM_PROMPT)

    def _generate_queries(self, counter_topics: list[dict], original_topic: str) -> list[str]:
        args_text = "\n".join(f"- {ct.get('topic', 'N/A')}: {ct.get('alternative_viewpoint', 'N/A')}" for ct in counter_topics)
        prompt = f"=== ORIGINAL RESEARCH TOPIC ===\n{original_topic}\n\n=== COUNTER-TOPICS ===\n{args_text}\n\nGenerate 3 precise search queries."
        
        raw = self._call_llm(prompt, temperature=0.3)
        cleaned = self._clean_json_response(raw)

        try:
            data = json.loads(cleaned)
            queries = data.get("queries", [])
            if not isinstance(queries, list):
                queries = []
            return queries[:3]
        except json.JSONDecodeError:
            logger.warning("Failed to parse query generation: %s", cleaned[:200])
            return [ct.get("topic", "alternative perspective") for ct in counter_topics[:3]]

    def _search(self, query: str) -> list[dict]:
        if not settings.SERPAPI_API_KEY or settings.SERPAPI_API_KEY == "your_serpapi_key_here":
            logger.warning("SerpAPI key not configured, skipping search")
            return []
        
        params = {
            "engine": "google",
            "q": query,
            "num": 4,
            "api_key": settings.SERPAPI_API_KEY,
        }
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            organic = results.get("organic_results", [])
            return organic[:4]
        except Exception as e:
            logger.error("SerpAPI search failed for '%s': %s", query, e)
            return []

    def _rank_results(self, all_results: list[dict], counter_topics: list[dict], original_topic: str) -> dict:
        if not all_results:
            return {"curated_links": []}
        
        results_text = ""
        for i, r in enumerate(all_results, 1):
            results_text += f"\n--- Result ID: {i} ---\nTitle: {r.get('title', 'N/A')}\nSnippet: {r.get('snippet', 'N/A')}\n"

        # Temporarily swap system prompt for ranking
        original_prompt = self.system_prompt
        self.system_prompt = RANKING_PROMPT
        prompt = f"=== ORIGINAL RESEARCH TOPIC ===\n{original_topic}\n\n=== COUNTER-TOPICS ===\n{json.dumps(counter_topics)}\n\n=== RAW RESULTS ===\n{results_text}\n\nRank and curate the top 3-4 links."
        
        raw = self._call_llm(prompt, temperature=0.2)
        self.system_prompt = original_prompt

        cleaned = self._clean_json_response(raw)

        try:
            parsed = json.loads(cleaned)
            final_links = []
            for item in parsed.get("curated_links", []):
                idx = item.get("result_id")
                if isinstance(idx, int) and 1 <= idx <= len(all_results):
                    actual_result = all_results[idx - 1]
                    final_links.append({
                        "rank": len(final_links) + 1,
                        "title": actual_result.get("title", "Unknown"),
                        "url": actual_result.get("link", "#"),
                        "summary": item.get("summary", ""),
                        "perspective": item.get("perspective", "Neutral"),
                        "credibility": item.get("credibility", "Medium")
                    })
            return {"curated_links": final_links}
        except json.JSONDecodeError:
            logger.warning("Failed to parse ranking response: %s", cleaned[:200])
            # Fallback: return raw results without ranking
            fallback = []
            for r in all_results[:4]:
                fallback.append({
                    "rank": len(fallback) + 1,
                    "title": r.get("title", "Unknown"),
                    "url": r.get("link", "#"),
                    "summary": r.get("snippet", ""),
                    "perspective": "Neutral",
                    "credibility": "Medium"
                })
            return {"curated_links": fallback}

    def run(self, counter_opinion_output: dict, topic: str = "") -> dict:
        # Check Guardrail from Agent 3
        guardrail = counter_opinion_output.get("null_guardrail", "")
        if isinstance(guardrail, str) and "NO_CREDIBLE_DISSENT_FOUND" in guardrail:
            return {
                "curated_links": [],
                "note": "Guardrail triggered: Objective fact or no credible dissent exists. Web search skipped."
            }

        counter_topics = counter_opinion_output.get("counter_topics", [])
        if not counter_topics:
            return {"curated_links": [], "note": "No counter topics provided."}

        queries = self._generate_queries(counter_topics, topic)
        logger.info("Generated search queries: %s", queries)
        
        all_results = []
        for q in queries:
            results = self._search(q)
            all_results.extend(results)

        if not all_results:
            return {"curated_links": [], "note": "No search results found.", "search_queries_used": queries}

        ranked = self._rank_results(all_results, counter_topics, topic)
        ranked["search_queries_used"] = queries
        return ranked
