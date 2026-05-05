"""
Devil's Advocate — Agent 1: Session Integrity Agent (The "Gatekeeper")
Manages the 4-Level Safety Gate to filter out noise and protect privacy.
"""

import json
from agents.base_agent import BaseAgent
from vector_memory import vector_memory

SYSTEM_PROMPT = """You are the Session Integrity Agent (The Gatekeeper).
Your job is to identify the overarching topic of the provided text and extract a stance vector.

Instructions:
1. Identify the overarching research topic.
2. Generate a 3-dimensional normalized stance vector [-1.0 to 1.0] representing the text's 
   perspective (e.g., [Sentiment, Objectivity, Lean]). 
3. Summarize the confirmed research text succinctly.

Respond in strict JSON:
{
  "topic": "...",
  "stance_vector": [0.0, 0.0, 0.0],
  "summary": "..."
}
Do NOT add commentary outside the JSON."""


class SessionIntegrityAgent(BaseAgent):
    """
    Skill: session_management & relevance_scoring.
    Level 1: URL Blacklist
    Level 2: Keyword Heuristic
    Level 3: Vector Similarity (Pinecone Golden Thread)
    Level 4: Uncertainty Prompt
    """
    def __init__(self):
        super().__init__(name="SessionIntegrityAgent", system_prompt=SYSTEM_PROMPT)
        self.url_blacklist = ["bank", "paypal", "checkout", "amazon", "facebook", "instagram", "twitter", "shop"]
        self.transaction_keywords = ["checkout", "cart", "login", "password", "credit card", "buy now"]

    def run(self, text: str, url: str = "") -> dict:
        # Level 1 (Hard Filter): URL Blacklist
        url_lower = url.lower()
        if any(domain in url_lower for domain in self.url_blacklist):
            return {"status": "REJECTED_LEVEL_1", "reason": "URL matches restricted domain (banking/social/shopping)."}

        # Level 2 (Keyword Heuristic): Scan first 100 words for transactional intent
        first_100 = " ".join(text.split()[:100]).lower()
        if any(kw in first_100 for kw in self.transaction_keywords):
            return {"status": "REJECTED_LEVEL_2", "reason": "Transactional keywords found in opening text."}

        # Use LLM to extract topic and vector
        raw = self._call_llm(text, temperature=0.1)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = {
                "topic": "Unknown",
                "stance_vector": [0.0, 0.0, 0.0],
                "summary": "Failed to parse text."
            }

        # Level 3 (Vector Similarity): Compare to Golden Thread
        similarity = vector_memory.get_golden_thread_similarity(data["stance_vector"])
        
        # Level 4 (User Prompt): If similarity is very low (< 0.2) after the first few pages
        prompt_user = False
        if len(vector_memory.local_memory) > 1 and similarity < 0.2:
            prompt_user = True

        # If confirmed, store the vector in memory
        vector_memory.store_vector(data["stance_vector"], {"url": url, "topic": data["topic"]})

        return {
            "status": "ACCEPTED",
            "requires_user_confirmation": prompt_user,
            "similarity_to_golden_thread": round(similarity, 2),
            "confirmed_text": data["summary"],
            "overarching_topic": data["topic"],
            "stance_vector": data["stance_vector"]
        }
