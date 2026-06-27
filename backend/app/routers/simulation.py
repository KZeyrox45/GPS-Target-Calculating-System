"""
simulation.py — Simulation REST + WebSocket router
===================================================

Two separate APIRouter objects are exported:
  • router   — REST endpoints mounted at /api  (POST /api/simulation/start, etc.)
  • ws_router — WebSocket endpoint mounted at / (WS  /ws/tracking/{id})

This separation is required because FastAPI's CORS middleware does NOT apply to
WebSocket upgrade requests, which means the browser's Origin header is rejected
when connecting directly to ws://localhost:8000.  Instead, the frontend proxies
through Vite's dev-server (/ws → ws://localhost:8000), so the WS path must be
at /ws/tracking/{id} on the backend — i.e. mounted at root, not under /api.
"""

import uuid
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from ..models.schemas import SimulationStartRequest, SimulationStartResponse
from ..simulation.target_simulator import SimulationEngine, SimulationConfig

log = logging.getLogger(__name__)

# ── REST router (prefix /api added in main.py) ────────────────────────────────
router = APIRouter()

# ── WebSocket router (no prefix — mounted at root in main.py) ─────────────────
ws_router = APIRouter()

# In-memory session registry  { session_id: SimulationEngine }
_sessions: dict[str, SimulationEngine] = {}


# ── REST endpoints ─────────────────────────────────────────────────────────────

@router.post("/simulation/start", response_model=SimulationStartResponse)
async def start_simulation(request: SimulationStartRequest):
    """
    Create a new simulation session.
    Returns a session_id and the WebSocket URL to connect to.
    """
    session_id = str(uuid.uuid4())

    config = SimulationConfig(
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_alt=request.observer_alt,
        target_type=request.target_type,
        algorithm=request.algorithm,
        duration_s=request.duration_s,
        update_rate_hz=request.update_rate_hz,
        alpha=request.alpha,
        seed=request.seed,
    )
    _sessions[session_id] = SimulationEngine(config)

    return SimulationStartResponse(
        session_id=session_id,
        ws_url=f"/ws/tracking/{session_id}",
        message="Session created. Connect to ws_url to begin.",
    )


@router.post("/simulation/stop/{session_id}")
async def stop_simulation(session_id: str):
    """Stop an active simulation and remove the session."""
    engine = _sessions.get(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="Session not found")
    engine.stop()
    _sessions.pop(session_id, None)
    return {"message": f"Session {session_id} stopped."}


@router.get("/simulation/sessions")
async def list_sessions():
    """List all active session IDs (debug / monitoring endpoint)."""
    return {"active_sessions": list(_sessions.keys())}


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@ws_router.websocket("/ws/tracking/{session_id}")
async def ws_tracking(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint — streams live TrackingFrame JSON at 10 Hz.

    Path: /ws/tracking/{session_id}
    Proxied by Vite dev-server: /ws → ws://localhost:8000

    Message format: JSON dict (see TrackingFrame.to_dict())
    Terminal message: {"type": "simulation_end"}
    """
    engine = _sessions.get(session_id)
    if engine is None:
        # Send a close frame before closing so the client gets a clean rejection
        await websocket.close(code=4404, reason="Session not found")
        return

    await websocket.accept()
    log.info("WS connected: session=%s", session_id)

    try:
        async for frame in engine.run():
            await websocket.send_text(json.dumps(frame.to_dict()))

        # Simulation finished naturally — notify client then close cleanly
        await websocket.send_text(json.dumps({"type": "simulation_end"}))
        await websocket.close()

    except WebSocketDisconnect:
        log.info("WS disconnected by client: session=%s", session_id)
        engine.stop()

    except Exception as exc:
        log.exception("WS error for session=%s: %s", session_id, exc)
        engine.stop()
        try:
            await websocket.close(code=1011)
        except Exception:
            pass

    finally:
        _sessions.pop(session_id, None)
        log.info("WS session cleaned up: session=%s", session_id)
