"""
Devil's Advocate — Agent 4: Retrieval & Verification Agent (The "Librarian")
Connects the theoretical counter-arguments to real-world evidence.
"""

import json
from serpapi import GoogleSearch
from agents.base_agent import BaseAgent
from config import settings

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

Respond in strict JSON:
{
  "curated_links": [
    {
      "rank": 1,
      "title": "...",
      "url": "...",
      "summary": "...",
      "perspective": "Counter-Opinion | Inline",
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

    def _generate_queries(self, counter_topics: list[dict]) -> list[str]:
        args_text = "\n".join(f"- {ct.get('topic')}: {ct.get('alternative_viewpoint')}" for ct in counter_topics)
        prompt = f"=== COUNTER-TOPICS ===\n{args_text}\n\nGenerate 3 precise search queries."
        
        raw = self._call_llm(prompt, temperature=0.3)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            return data.get("queries", [])[:3]
        except json.JSONDecodeError:
            return [ct.get("topic", "alternative perspective") for ct in counter_topics[:3]]

    def _search(self, query: str) -> list[dict]:
        params = {
            "engine": "google",
            "q": query,
            "num": 4,
            "api_key": settings.SERPAPI_API_KEY,
        }
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            return results.get("organic_results", [])[:4]
        except Exception as e:
            return [{"title": "Search error", "snippet": str(e), "link": ""}]

    def _rank_results(self, all_results: list[dict], counter_topics: list[dict]) -> dict:
        results_text = ""
        for i, r in enumerate(all_results, 1):
            results_text += f"\n--- Result {i} ---\nTitle: {r.get('title', 'N/A')}\nURL: {r.get('link', 'N/A')}\nSnippet: {r.get('snippet', 'N/A')}\n"

        self.system_prompt = RANKING_PROMPT
        prompt = f"=== COUNTER-TOPICS ===\n{json.dumps(counter_topics)}\n\n=== RAW RESULTS ===\n{results_text}\n\nRank and curate the top 3-4 links."
        
        raw = self._call_llm(prompt, temperature=0.2)
        self.system_prompt = SYSTEM_PROMPT

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"curated_links": []}

    def run(self, counter_opinion_output: dict) -> dict:
        # Check Guardrail from Agent 3
        if "NO_CREDIBLE_DISSENT_FOUND" in counter_opinion_output.get("null_guardrail", ""):
            return {
                "curated_links": [],
                "note": "Guardrail triggered: Objective fact or no credible dissent exists. Web search skipped."
            }

        counter_topics = counter_opinion_output.get("counter_topics", [])
        if not counter_topics:
            return {"curated_links": [], "note": "No counter topics provided."}

        queries = self._generate_queries(counter_topics)
        all_results = []
        for q in queries:
            all_results.extend(self._search(q))

        ranked = self._rank_results(all_results, counter_topics)
        ranked["search_queries_used"] = queries
        return ranked
