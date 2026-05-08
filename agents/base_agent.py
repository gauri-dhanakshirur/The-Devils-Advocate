"""
Devil's Advocate — Agent Base Class
Every sub-agent inherits from this to gain LLM access via Groq.
"""

import logging
from groq import Groq
from config import settings

logger = logging.getLogger("base_agent")


class BaseAgent:
    """Abstract base for all Devil's Advocate sub-agents."""

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self._client = Groq(api_key=settings.GROQ_API_KEY)

    def _call_llm(self, user_message: str, temperature: float | None = None) -> str:
        """Send a prompt to the Groq-hosted Llama-3 model and return the text."""
        try:
            response = self._client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature or settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            if not content:
                logger.warning("[%s] LLM returned empty content", self.name)
                return "{}"
            return content
        except Exception as e:
            logger.error("[%s] LLM call failed: %s", self.name, e)
            raise

    def _clean_json_response(self, raw: str) -> str:
        """Strip markdown code fences from LLM JSON output."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        return cleaned.strip()

    def run(self, text: str) -> dict:
        """Override in subclasses to return structured output."""
        raise NotImplementedError
