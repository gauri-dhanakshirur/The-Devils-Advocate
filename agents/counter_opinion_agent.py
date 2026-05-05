"""
Devil's Advocate — Agent 3: Counter-Opinion Architect (The "Devil's Advocate")
Identifies the "missing mass" in the user's research to break the echo chamber.
"""

import json
from agents.base_agent import BaseAgent

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
            f"=== RESEARCH THEME ===\n{auditor_output.get('research_theme')}\n\n"
            f"=== OPINIONS SO FAR ===\n{auditor_output.get('opinions_summary')}\n\n"
            "Generate counter-topics or apply the Truth-Gating Guardrail if it's objective fact."
        )

        raw = self._call_llm(prompt, temperature=0.2)
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
                "null_guardrail": "Error parsing JSON.",
                "counter_topics": []
            }

        return data
