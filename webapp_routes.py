"""
Devil's Advocate — Webapp Routes
FastAPI routes for the web interface to view session history.
"""

import logging
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Query, Depends, Header, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from database import db
from auth import (
    User, UserCreate, UserLogin, Token,
    create_access_token, get_current_user, decode_token
)

logger = logging.getLogger("webapp_routes")

router = APIRouter(prefix="/webapp", tags=["Webapp"])

# ── WebSocket Manager ────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        # Maps session_id to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket connected for session: {session_id}")

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected for session: {session_id}")

    async def broadcast_nebula(self, session_id: str, nebula_data: dict):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(nebula_data)
                except Exception as e:
                    logger.error(f"WebSocket broadcast error: {e}")

manager = ConnectionManager()



# ── Auth Routes ──────────────────────────────────────────────────────

@router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    try:
        user = User.create(user_data.email, user_data.password, user_data.name)
        token = create_access_token({"sub": user["email"]})
        return Token(access_token=token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user = User.verify(credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user["email"]})
    return Token(access_token=token)


@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


# ── Request Models ───────────────────────────────────────────────────

class SyncSessionRequest(BaseModel):
    session_id: str
    topic: str = ""
    user_topic: str = ""
    started_at: int
    bias_score: float = 5.0
    opinions_summary: str = ""
    guardrail_triggered: bool = False
    stats: dict = {}
    pages: list = []
    counter_perspectives: list = []
    sources: list = []


class MarkCitationRequest(BaseModel):
    page_id: int
    note: str = ""


# ── Helper: resolve user from optional Bearer token ──────────────────
def get_user_email_from_header(authorization: Optional[str] = Header(default=None)) -> str:
    """Extract user email from Authorization header. Returns empty string if not authenticated."""
    if not authorization or not authorization.startswith("Bearer "):
        return ""
    try:
        token = authorization.split(" ", 1)[1]
        payload = decode_token(token)
        return payload.get("sub", "")
    except Exception:
        return ""


# ── Session Sync (called by extension) ──────────────────────────────

@router.post("/sync-session")
async def sync_session(
    request: SyncSessionRequest,
    user_email: str = Depends(get_user_email_from_header)
):
    """Sync a session from the extension. Auth optional — links to user if token provided."""
    try:
        existing = db.get_session(request.session_id)

        if existing:
            db.update_session(request.session_id, {
                "topic": request.topic,
                "user_topic": request.user_topic,
                "bias_score": request.bias_score,
                "opinions_summary": request.opinions_summary,
                "guardrail_triggered": request.guardrail_triggered,
                "stats_analyzed": request.stats.get("analyzed", 0),
                "stats_approved": request.stats.get("approved", 0),
                "stats_skipped": request.stats.get("skipped", 0)
            })
            # Update user_email if we now have one and didn't before
            if user_email and not existing.get("user_email"):
                db.update_session(request.session_id, {"user_email": user_email})
        else:
            db.create_session({
                "session_id": request.session_id,
                "user_email": user_email,
                "topic": request.topic,
                "user_topic": request.user_topic,
                "started_at": request.started_at,
                "bias_score": request.bias_score,
                "opinions_summary": request.opinions_summary,
                "guardrail_triggered": request.guardrail_triggered
            })
            db.update_session(request.session_id, {
                "stats_analyzed": request.stats.get("analyzed", 0),
                "stats_approved": request.stats.get("approved", 0),
                "stats_skipped": request.stats.get("skipped", 0)
            })

        # Pages — deduplicate by URL
        existing_pages = db.get_session_pages(request.session_id)
        existing_urls = {p["url"] for p in existing_pages}
        for page in request.pages:
            if page.get("url") not in existing_urls:
                db.add_page(request.session_id, {
                    "url": page.get("url"),
                    "title": page.get("title"),
                    "topic": page.get("topic"),
                    "bias_score": page.get("biasScore", page.get("bias_score")),
                    "analyzed_at": page.get("timestamp", page.get("analyzed_at"))
                })

        # Counter perspectives — clear and re-add
        with db.get_connection() as conn:
            conn.cursor().execute(
                "DELETE FROM counter_perspectives WHERE session_id = ?", (request.session_id,)
            )
        for cp in request.counter_perspectives:
            cp_id = db.add_counter_perspective(request.session_id, {
                "topic": cp.get("topic"),
                "viewpoint": cp.get("viewpoint")
            })
            for source in cp.get("sources", []):
                db.add_source(request.session_id, source, cp_id)

        # Standalone sources — clear and re-add
        with db.get_connection() as conn:
            conn.cursor().execute(
                "DELETE FROM sources WHERE session_id = ? AND counter_perspective_id IS NULL",
                (request.session_id,)
            )
        for source in request.sources:
            db.add_source(request.session_id, source)

        # Broadcast the updated nebula graph via WebSocket
        try:
            from nebula_engine import compute_nebula
            updated_pages = db.get_session_pages(request.session_id)
            updated_cps = db.get_session_counter_perspectives(request.session_id)
            nebula = compute_nebula(updated_pages, updated_cps, request.bias_score)
            # Use asyncio.create_task or await if safe
            import asyncio
            asyncio.create_task(manager.broadcast_nebula(request.session_id, nebula))
        except Exception as e:
            logger.error(f"Failed to broadcast nebula update: {e}")

        logger.info("Session %s synced (user: %s)", request.session_id, user_email or "anonymous")
        return {"success": True, "session_id": request.session_id}

    except Exception as e:
        logger.error("Failed to sync session: %s", e)
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


@router.post("/end-session/{session_id}")
async def end_session(session_id: str):
    try:
        db.end_session(session_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Session Reads (require auth, user-scoped) ────────────────────────

@router.get("/sessions")
async def get_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get sessions for the logged-in user only."""
    try:
        user_email = current_user["email"]
        sessions = db.get_sessions_for_user(user_email, limit, offset)
        stats    = db.get_global_stats_for_user(user_email)
        return {
            "sessions": sessions,
            "global_stats": stats,
            "pagination": {"limit": limit, "offset": offset, "has_more": len(sessions) == limit}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session_detail(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Allow access if session belongs to user OR has no owner (legacy)
        if session.get("user_email") and session["user_email"] != current_user["email"]:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "session": session,
            "pages": db.get_session_pages(session_id),
            "counter_perspectives": db.get_session_counter_perspectives(session_id),
            "sources": db.get_session_sources(session_id),
            "citations": db.get_citations(session_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        session = db.get_session(session_id)
        if session and session.get("user_email") and session["user_email"] != current_user["email"]:
            raise HTTPException(status_code=403, detail="Access denied")
        db.delete_session(session_id)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/citation")
async def mark_citation(
    request: MarkCitationRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        db.mark_as_citation(request.page_id, request.note)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/source/{source_id}/visited")
async def mark_source_visited(source_id: int):
    try:
        db.mark_source_visited(source_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_global_stats(current_user: dict = Depends(get_current_user)):
    try:
        return db.get_global_stats_for_user(current_user["email"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nebula/{session_id}")
async def get_nebula(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Knowledge Nebula — Interactive graph visualization of session bias.
    Computes nodes, edges, centrality, ghost nodes, and graph metrics
    from the session's page vectors and counter-perspectives.
    """
    from nebula_engine import compute_nebula

    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.get("user_email") and session["user_email"] != current_user["email"]:
            raise HTTPException(status_code=403, detail="Access denied")

        pages = db.get_session_pages(session_id)
        counter_perspectives = db.get_session_counter_perspectives(session_id)
        bias_score = session.get("bias_score", 5.0)

        nebula = compute_nebula(pages, counter_perspectives, bias_score)
        return nebula

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Nebula computation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Nebula engine error: {e}")

@router.websocket("/ws/nebula/{session_id}")
async def websocket_nebula_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time Knowledge Nebula updates."""
    await manager.connect(websocket, session_id)
    try:
        # Send initial state
        from nebula_engine import compute_nebula
        session = db.get_session(session_id)
        if session:
            pages = db.get_session_pages(session_id)
            counter_perspectives = db.get_session_counter_perspectives(session_id)
            bias_score = session.get("bias_score", 5.0)
            nebula = compute_nebula(pages, counter_perspectives, bias_score)
            await websocket.send_json(nebula)
        
        while True:
            # Keep connection alive and wait for client messages if any
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, session_id)

