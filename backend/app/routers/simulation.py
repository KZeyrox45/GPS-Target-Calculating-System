"""
simulation.py - Simulation REST + WebSocket router
===================================================

Two separate APIRouter objects are exported:
  - router   - REST endpoints mounted at /api  (POST /api/simulation/start, etc.)
  - ws_router - WebSocket endpoint mounted at / (WS  /ws/tracking/{id})

This separation is required because FastAPI's CORS middleware does NOT apply to
WebSocket upgrade requests, which means the browser's Origin header is rejected
when connecting directly to ws://localhost:8000.  Instead, the frontend proxies
through Vite's dev-server (/ws -> ws://localhost:8000), so the WS path must be
at /ws/tracking/{id} on the backend - i.e. mounted at root, not under /api.
"""

import csv
import io
import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from ..models.schemas import SimulationStartRequest, SimulationStartResponse
from ..simulation.target_simulator import SimulationConfig, SimulationEngine

log = logging.getLogger(__name__)

# --- REST router (prefix /api added in main.py) ---
router = APIRouter()

# --- WebSocket router (no prefix - mounted at root in main.py) ---
ws_router = APIRouter()

# In-memory session registry  { session_id: SimulationEngine }
_sessions: dict[str, SimulationEngine] = {}


# --- REST endpoints ---

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
        use_realistic_sim=request.use_realistic_sim,
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


@router.get("/simulation/stats/{session_id}")
async def get_session_stats(session_id: str):
    """
    Return live RMSE statistics for an active simulation session.

    Response fields:
    - steps: number of time steps processed so far
    - kalman_rmse_m: running horizontal RMSE of Kalman filter (metres)
    - alpha_beta_rmse_m: running horizontal RMSE of alpha-beta filter (metres)
    - raw_rmse_m: running horizontal RMSE of raw sensor measurement (metres)
    - duration_s: elapsed simulation time (seconds)
    - target_type: pedestrian | motorcycle | drone
    """
    engine = _sessions.get(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return engine.get_stats()


@router.get("/simulation/export/{session_id}")
async def export_session_csv(session_id: str):
    """
    Export trajectory and error metrics as a CSV file.

    The CSV contains one row per simulation time step with columns:
    step, timestamp, gt_east, gt_north, gt_alt, raw_east, raw_north,
    kalman_east, kalman_north, kalman_alt, kalman_rmse,
    ab_east, ab_north, ab_rmse, uncertainty_m.

    Available while the session is active.
    """
    engine = _sessions.get(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="Session not found")

    frames = engine._frames
    if not frames:
        raise HTTPException(status_code=204, detail="No data yet - session has not started or no frames recorded.")

    output = io.StringIO()
    fieldnames = [
        "step", "timestamp",
        "gt_east", "gt_north", "gt_alt",
        "raw_east", "raw_north", "azimuth", "elevation", "range_m",
        "kalman_east", "kalman_north", "kalman_alt", "kalman_error_m", "kalman_rmse_m",
        "ab_east", "ab_north", "ab_error_m", "ab_rmse_m",
        "uncertainty_m",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for f in frames:
        gt = f.get("ground_truth", {})
        raw = f.get("raw_measurement", {})
        kf  = f.get("kalman", {})
        ab  = f.get("alpha_beta", {})
        met = f.get("metrics", {})
        writer.writerow({
            "step":           f.get("step"),
            "timestamp":      f.get("timestamp"),
            "gt_east":        round(gt.get("east",  0.0), 4),
            "gt_north":       round(gt.get("north", 0.0), 4),
            "gt_alt":         round(gt.get("alt",   0.0), 4),
            "raw_east":       round(raw.get("east",  0.0), 4),
            "raw_north":      round(raw.get("north", 0.0), 4),
            "azimuth":        round(raw.get("azimuth",   0.0), 4),
            "elevation":      round(raw.get("elevation", 0.0), 4),
            "range_m":        round(raw.get("range",     0.0), 4),
            "kalman_east":    round(kf.get("east",  0.0), 4),
            "kalman_north":   round(kf.get("north", 0.0), 4),
            "kalman_alt":     round(kf.get("alt",   0.0), 4),
            "kalman_error_m": round(met.get("kalman_error",  0.0), 4),
            "kalman_rmse_m":  round(met.get("kalman_rmse",   0.0), 4),
            "ab_east":        round(ab.get("east",  0.0), 4),
            "ab_north":       round(ab.get("north", 0.0), 4),
            "ab_error_m":     round(met.get("alpha_beta_error", 0.0), 4),
            "ab_rmse_m":      round(met.get("alpha_beta_rmse", 0.0), 4),
            "uncertainty_m":  round(kf.get("uncertainty_m",   0.0), 4),
        })

    csv_bytes = output.getvalue().encode("utf-8")
    target_type = engine.config.target_type
    filename = f"tracking_{target_type}_{session_id[:8]}.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@ws_router.websocket("/ws/tracking/{session_id}")
async def ws_tracking(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint - streams live TrackingFrame JSON at 10 Hz.

    Path: /ws/tracking/{session_id}
    Proxied by Vite dev-server: /ws -> ws://localhost:8000

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

        # Simulation finished naturally - notify client then close cleanly
        await websocket.send_text(json.dumps({"type": "simulation_end"}))
        await websocket.close()

    except WebSocketDisconnect:
        log.info("WS disconnected by client: session=%s", session_id)
        engine.stop()

    except Exception:
        log.exception("WS error for session=%s", session_id)
        engine.stop()
        try:
            await websocket.close(code=1011)
        except OSError:
            pass

    finally:
        _sessions.pop(session_id, None)
        log.info("WS session cleaned up: session=%s", session_id)
