"""
Devil's Advocate — Lightweight Relevance Agent
Performs a low-cost metadata analysis to determine if a page should be scraped.
"""

import json
import logging
from agents.base_agent import BaseAgent

logger = logging.getLogger("relevance_agent")

SYSTEM_PROMPT = """You are the Lightweight Relevance Agent.
Your job is to determine if a webpage is relevant to the user's active research session using ONLY its metadata (Title, URL, Description, Headings).

Be LIBERAL in your assessment. When in doubt, default to "scrape" — it is better to do an extra full analysis than to incorrectly exclude a valid research page.

Only return "exclude" if you are HIGHLY CONFIDENT the page is completely unrelated to the topic — for example, an online store, a weather forecast, a sports score, a social media profile, or something with zero semantic overlap with the topic.

Instructions:
1. Compare the page metadata against the "Session Topic".
2. Assign a confidence score from 0.0 to 1.0 of how related it is to the topic.
3. Only set decision to "exclude" if confidence < 0.12 (very low bar — near-zero overlap).
4. If the page is ambiguous, uncertain, or even loosely related, set decision to "scrape".
5. Provide a brief 1-sentence reason.

Respond in strict JSON:
{
  "confidence": 0.0,
  "decision": "exclude" | "scrape",
  "reason": "..."
}
Do NOT add commentary outside the JSON."""


class LightweightRelevanceAgent(BaseAgent):
    """
    Skill: progressive_analysis & relevance_scoring.
    Performs low-cost relevance check before triggering a full webscrape.
    """
    def __init__(self):
        super().__init__(name="LightweightRelevanceAgent", system_prompt=SYSTEM_PROMPT)

    def run(self, metadata: dict, session_topic: str) -> dict:
        prompt = (
            f"=== SESSION TOPIC ===\n{session_topic}\n\n"
            f"=== PAGE METADATA ===\n"
            f"Title: {metadata.get('title', 'Unknown')}\n"
            f"URL: {metadata.get('url', 'Unknown')}\n"
            f"Description: {metadata.get('metaDescription', 'None')}\n"
            f"Headings: {', '.join(metadata.get('headings', []))}\n\n"
            "Evaluate relevance and return JSON decision."
        )

        raw = self._call_llm(prompt, temperature=0.1)
        cleaned = self._clean_json_response(raw)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Relevance LLM response: %s", cleaned[:200])
            data = {
                "confidence": 0.5,
                "decision": "scrape",
                "reason": "Failed to parse LLM response; defaulting to scrape."
            }

        # Validate format
        decision = data.get("decision", "scrape").lower()
        if decision not in ["exclude", "scrape"]:
            decision = "scrape"
            
        confidence = float(data.get("confidence", 0.5))

        return {
            "confidence": confidence,
            "decision": decision,
            "reason": data.get("reason", "No reason provided.")
        }
