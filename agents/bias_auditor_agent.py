"""
Devil's Advocate — Agent 2: Bias & Stance Auditor (The "Mirror")
Evaluates how the current page affects the overall session trajectory.
"""

import json
import logging
from agents.base_agent import BaseAgent
from vector_memory import vector_memory

logger = logging.getLogger("bias_auditor")

SYSTEM_PROMPT = """You are the Bias & Stance Auditor (The Mirror).
Your job is to summarize the diverse opinions encountered so far based on the current text and previous topics.

Instructions:
1. Summarize the variety of opinions encountered so far in this session.
2. Clearly define the core Research Theme (e.g., 'Impact of Nuclear Energy').

Respond in strict JSON:
{
  "opinions_summary": "...",
  "research_theme": "..."
}
Do NOT add commentary outside the JSON."""


class BiasAuditorAgent(BaseAgent):
    """
    Skill: stance_analysis & bias_quantification.
    Calculates Bias Score based on vector clustering and defines the research theme.
    """
    def __init__(self):
        super().__init__(name="BiasAuditorAgent", system_prompt=SYSTEM_PROMPT)

    def run(self, text: str, gatekeeper_topic: str) -> dict:
        # Calculate session-wide Bias Score (0-10) using mathematical vector clustering
        bias_score = vector_memory.calculate_bias_score()

        # Build context from previous memory
        past_topics = [item["metadata"]["topic"] for item in vector_memory.local_memory]
        
        prompt = (
            f"=== CURRENT TEXT ===\n{text[:4000]}\n\n"
            f"=== GATEKEEPER TOPIC ===\n{gatekeeper_topic}\n\n"
            f"=== PAST SESSION TOPICS ===\n{json.dumps(past_topics)}\n\n"
            "Generate the opinions summary and extract the overarching research theme."
        )

        raw = self._call_llm(prompt, temperature=0.3)
        cleaned = self._clean_json_response(raw)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse BiasAuditor LLM response: %s", cleaned[:200])
            data = {
                "opinions_summary": "Unable to summarize opinions.",
                "research_theme": gatekeeper_topic
            }

        return {
            "cumulative_bias_score": bias_score,
            "research_theme": data.get("research_theme", gatekeeper_topic),
            "opinions_summary": data.get("opinions_summary", "Unable to summarize."),
            "feedback_prompt": f"Is '{data.get('research_theme', gatekeeper_topic)}' your intended research focus? (Thumbs Up/Down)"
        }
