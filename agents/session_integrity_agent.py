"""
Devil's Advocate — Agent 1: Session Integrity Agent (The "Gatekeeper")
Manages the 4-Level Safety Gate to filter out noise and protect privacy.
"""

import json
import logging
from agents.base_agent import BaseAgent
from vector_memory import vector_memory

logger = logging.getLogger("gatekeeper")

SYSTEM_PROMPT_BASE = """You are the Session Integrity Agent (The Gatekeeper).
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
        super().__init__(name="SessionIntegrityAgent", system_prompt=SYSTEM_PROMPT_BASE)
        self.url_blacklist = [
            "bank", "paypal", "checkout", "amazon", "facebook", "instagram",
            "twitter", "shop", "captcha", "verify", "challenge", "checkpoint",
            "bot-check", "security-check", "recaptcha", "cf-chl", "interstitial"
        ]
        self.transaction_keywords = [
            "checkout", "cart", "login", "password", "credit card", "buy now",
            "verify you are human", "are you a robot", "security check",
            "checking your browser", "ddos protection", "please wait"
        ]

    def run(self, text: str, url: str = "", session_topic: str = "") -> dict:
        # Level 1 (Hard Filter): URL Blacklist
        url_lower = url.lower()
        if any(domain in url_lower for domain in self.url_blacklist):
            return {"status": "REJECTED_LEVEL_1", "reason": "URL matches restricted domain (banking/social/shopping/verification)."}

        # Level 2 (Keyword Heuristic): Scan first 100 words for transactional/verification intent
        first_100 = " ".join(text.split()[:100]).lower()
        if any(kw in first_100 for kw in self.transaction_keywords):
            return {"status": "REJECTED_LEVEL_2", "reason": "Transactional or bot-verification keywords found in opening text."}

        # Build system prompt — anchor to user topic if provided
        system_prompt = SYSTEM_PROMPT_BASE
        if session_topic:
            system_prompt = (
                f"IMPORTANT: The user has defined the session research topic as: '{session_topic}'. "
                f"Use this as the overarching topic anchor. If the current text is relevant to this topic, "
                f"confirm it and use '{session_topic}' as the topic in your JSON response.\n\n"
                + SYSTEM_PROMPT_BASE
            )
        self.system_prompt = system_prompt

        # Use LLM to extract topic and vector
        raw = self._call_llm(text[:6000], temperature=0.1)  # Cap input to avoid token overflow
        cleaned = self._clean_json_response(raw)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gatekeeper LLM response: %s", cleaned[:200])
            data = {
                "topic": session_topic or "Unknown",
                "stance_vector": [0.0, 0.0, 0.0],
                "summary": "Failed to parse text."
            }

        # If user defined a topic, use it as the canonical topic
        if session_topic:
            data["topic"] = session_topic

        # Validate stance_vector shape
        stance = data.get("stance_vector", [0.0, 0.0, 0.0])
        if not isinstance(stance, list) or len(stance) != 3:
            stance = [0.0, 0.0, 0.0]
        # Clamp values to [-1, 1]
        stance = [max(-1.0, min(1.0, float(v))) for v in stance]

        # Level 3 (Vector Similarity): Compare to Golden Thread
        similarity = vector_memory.get_golden_thread_similarity(stance)
        
        # Level 4 (User Prompt): If similarity is very low (< 0.2) after the first few pages
        prompt_user = False
        if len(vector_memory.local_memory) > 1 and similarity < 0.2:
            prompt_user = True

        # If confirmed, store the vector in memory
        vector_memory.store_vector(stance, {"url": url, "topic": data.get("topic", "Unknown")})

        return {
            "status": "ACCEPTED",
            "requires_user_confirmation": prompt_user,
            "similarity_to_golden_thread": round(similarity, 2),
            "confirmed_text": data.get("summary", ""),
            "overarching_topic": data.get("topic", session_topic or "Unknown"),
            "stance_vector": stance
        }
