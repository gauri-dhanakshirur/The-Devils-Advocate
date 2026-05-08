"""
Devil's Advocate — Agent 3: Counter-Opinion Architect (The "Devil's Advocate")
Identifies the "missing mass" in the user's research to break the echo chamber.
"""

import json
import logging
from agents.base_agent import BaseAgent

logger = logging.getLogger("counter_opinion")

SYSTEM_PROMPT = """You are the Counter-Opinion Architect (The Devil's Advocate).
Your sole purpose is to broaden the user's knowledge by introducing diverse perspectives.

Instructions:
1. Review the overarching research theme and opinions identified by the Bias Auditor.
2. Generate 3-5 logical, high-quality counter-topics and concise summaries of alternative viewpoints.
3. Ensure these arguments are grounded in alternative narratives, conflicting theories, or historical contexts.
4. Avoid being contrarian for its own sake; focus on legitimate alternative viewpoints.

🚫 TRUTH-GATING GUARDRAIL:
You must prioritize accuracy over variety. If the research topic is an objective fact (e.g., 'What is the boiling point of water?') or if no credible, documented counter-perspectives exist, you MUST return the string "RESULT_NULL: NO_CREDIBLE_DISSENT_FOUND" inside the "null_guardrail" JSON field. Do not synthesize artificial conflict.

Respond in strict JSON:
{
  "null_guardrail": "None" | "RESULT_NULL: NO_CREDIBLE_DISSENT_FOUND",
  "counter_topics": [
    {
      "topic": "...",
      "alternative_viewpoint": "..."
    }
  ]
}
Do NOT add commentary outside the JSON."""


class CounterOpinionAgent(BaseAgent):
    """
    Skill: argument_generation.
    Identifies logical counter-arguments and strictly guards against hallucination
    on objective facts.
    """
    def __init__(self):
        super().__init__(name="CounterOpinionAgent", system_prompt=SYSTEM_PROMPT)

    def run(self, auditor_output: dict) -> dict:
        prompt = (
            f"=== RESEARCH THEME ===\n{auditor_output.get('research_theme', 'Unknown')}\n\n"
            f"=== OPINIONS SO FAR ===\n{auditor_output.get('opinions_summary', 'None provided')}\n\n"
            "Generate counter-topics or apply the Truth-Gating Guardrail if it's objective fact."
        )

        raw = self._call_llm(prompt, temperature=0.2)
        cleaned = self._clean_json_response(raw)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse CounterOpinion LLM response: %s", cleaned[:200])
            data = {
                "null_guardrail": "None",
                "counter_topics": []
            }

        # Validate counter_topics is a list
        if not isinstance(data.get("counter_topics"), list):
            data["counter_topics"] = []

        # Ensure each counter_topic has required fields
        validated = []
        for ct in data["counter_topics"]:
            if isinstance(ct, dict) and "topic" in ct:
                validated.append({
                    "topic": ct.get("topic", "Unknown"),
                    "alternative_viewpoint": ct.get("alternative_viewpoint", "No details provided.")
                })
        data["counter_topics"] = validated

        return data
