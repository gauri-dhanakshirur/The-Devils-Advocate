"""
Devil's Advocate — Gateway Server
FastAPI backend that exposes the multi-agent orchestrator via REST API.

Run with:  python main.py
Or:        uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from agents.orchestrator import Orchestrator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("gateway")

# ---------------------------------------------------------------------------
# Lifespan — validate keys on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = settings.validate()
    if missing:
        logger.warning(
            "⚠️  Missing API keys: %s — some features will be unavailable.",
            ", ".join(missing),
        )
    else:
        logger.info("✅ All API keys loaded successfully.")
    logger.info("🚀 Devil's Advocate Gateway running on http://%s:%s", settings.HOST, settings.PORT)
    yield

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Devil's Advocate Gateway",
    description=(
        "A multi-agent AI system that dismantles confirmation bias. "
        "Submit research text and receive a structured counter-narrative "
        "backed by real-world sources."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow browser extension and local dev to talk to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    """Payload sent by the Devil's Advocate extension or any client."""
    text: str = Field(
        ...,
        min_length=20,
        description="The research text to analyze. Must be at least 20 characters.",
    )
    url: str = Field(
        default="",
        description="The URL of the current page for Gatekeeper filtering."
    )


from typing import Optional

class AnalyzeResponse(BaseModel):
    """Full Devil's Advocate analysis result."""
    error: bool
    gatekeeper: Optional[dict] = None
    mirror: Optional[dict] = None
    devils_advocate: Optional[dict] = None
    librarian: Optional[dict] = None
    synthesis: str
    elapsed_seconds: float


class HealthResponse(BaseModel):
    status: str
    version: str
    keys_configured: dict


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Quick health check — shows which API keys are configured."""
    missing = settings.validate()
    return HealthResponse(
        status="operational" if not missing else "degraded",
        version="1.0.0",
        keys_configured={
            "groq": "GROQ_API_KEY" not in missing,
            "serpapi": "SERPAPI_API_KEY" not in missing,
            "pinecone": bool(settings.PINECONE_API_KEY),
        },
    )


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze(request: AnalyzeRequest):
    """
    🎯 Core endpoint — Run the full Devil's Advocate sequential pipeline.

    1. **Gatekeeper** — filters URL, keywords, and checks vector similarity
    2. **Mirror** — bias score and topic tracking
    3. **Devil's Advocate** — counter-opinions & Truth-Gating Guardrail
    4. **Librarian** — SerpAPI search and ranking
    5. **Orchestrator** — final synthesis
    """
    missing = settings.validate()
    if "GROQ_API_KEY" in missing:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Cannot run analysis.",
        )

    logger.info("📥 Received analysis request (%d chars) for URL: %s", len(request.text), request.url)
    start = time.time()

    try:
        orchestrator = Orchestrator()
        result = orchestrator.run(request.text, request.url)
    except Exception as e:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {e}")

    elapsed = round(time.time() - start, 2)
    logger.info("✅ Analysis complete in %.2fs", elapsed)

    return AnalyzeResponse(
        error=result.get("error", False),
        gatekeeper=result.get("gatekeeper"),
        mirror=result.get("mirror"),
        devils_advocate=result.get("devils_advocate"),
        librarian=result.get("librarian"),
        synthesis=result.get("synthesis", ""),
        elapsed_seconds=elapsed,
    )


@app.post("/quick-bias", tags=["Analysis"])
async def quick_bias(request: AnalyzeRequest):
    """Lightweight endpoint — only runs the Gatekeeper and Mirror."""
    from agents.session_integrity_agent import SessionIntegrityAgent
    from agents.bias_auditor_agent import BiasAuditorAgent

    gatekeeper = SessionIntegrityAgent()
    g_out = gatekeeper.run(request.text, request.url)
    
    if g_out.get("status") != "ACCEPTED":
        return g_out
        
    mirror = BiasAuditorAgent()
    return mirror.run(request.text, g_out.get("overarching_topic", ""))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
