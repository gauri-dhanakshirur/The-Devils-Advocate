"""
Devil's Advocate — Configuration Module
Loads environment variables and exposes validated settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration sourced from environment variables."""

    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # ── OpenClaw Gateway ────────────────────────────────────────────
    # OpenClaw is the sole agentic runtime. It manages the LLM provider
    # (Groq, OpenAI, Anthropic, etc.) via its own config at ~/.openclaw/
    OPENCLAW_BASE_URL: str = os.getenv(
        "OPENCLAW_BASE_URL", "http://127.0.0.1:18789/v1"
    )
    OPENCLAW_TOKEN: str = os.getenv(
        "OPENCLAW_TOKEN", "devils-advocate-token"
    )
    OPENCLAW_MODEL: str = os.getenv(
        "OPENCLAW_MODEL", "openclaw/main"
    )

    # Model parameters (passed through OpenClaw to the underlying LLM)
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1024

    @classmethod
    def validate(cls) -> list[str]:
        """Return a list of missing critical keys."""
        missing = []
        if not cls.OPENCLAW_BASE_URL:
            missing.append("OPENCLAW_BASE_URL")
        if not cls.OPENCLAW_TOKEN:
            missing.append("OPENCLAW_TOKEN")
        if not cls.SERPAPI_API_KEY or cls.SERPAPI_API_KEY == "your_serpapi_key_here":
            missing.append("SERPAPI_API_KEY")
        return missing


settings = Settings()
