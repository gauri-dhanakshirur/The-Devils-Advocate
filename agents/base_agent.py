"""
Devil's Advocate — Agent Base Class
Every sub-agent inherits from this to gain LLM access via Groq.
"""

from groq import Groq
from config import settings


class BaseAgent:
    """Abstract base for all Devil's Advocate sub-agents."""

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self._client = Groq(api_key=settings.GROQ_API_KEY)

    def _call_llm(self, user_message: str, temperature: float | None = None) -> str:
        """Send a prompt to the Groq-hosted Llama-3 model and return the text."""
        response = self._client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature or settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
        return response.choices[0].message.content

    def run(self, text: str) -> dict:
        """Override in subclasses to return structured output."""
        raise NotImplementedError
