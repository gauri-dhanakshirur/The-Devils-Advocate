"""
Devil's Advocate — Configuration Module
Loads environment variables and exposes validated settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration sourced from environment variables."""

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Groq model settings
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    @classmethod
    def validate(cls) -> list[str]:
        """Return a list of missing critical keys."""
        missing = []
        if not cls.GROQ_API_KEY or cls.GROQ_API_KEY == "your_groq_key_here":
            missing.append("GROQ_API_KEY")
        if not cls.SERPAPI_API_KEY or cls.SERPAPI_API_KEY == "your_serpapi_key_here":
            missing.append("SERPAPI_API_KEY")
        return missing


settings = Settings()
