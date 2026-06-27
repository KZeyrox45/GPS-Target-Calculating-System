"""
main.py — FastAPI Application Entry Point
==========================================
Real-Time Moving Target Tracking System — Backend
Thesis: "Real-Time Moving Target Tracking and Geolocation Using Laser-IMU-GNSS Fusion"

Routing layout
──────────────
  /api/simulation/start   POST   — create session
  /api/simulation/stop/*  POST   — stop session
  /api/simulation/sessions GET   — list sessions
  /api/calculate          POST   — Phase-1 static calculator
  /ws/tracking/{id}       WS     — live tracking stream (proxied by Vite /ws)
  /health                 GET    — health check
  /docs                   GET    — Swagger UI
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.simulation import router as simulation_router, ws_router
from .routers.calculator  import router as calculator_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Target Tracking System backend starting up")
    yield
    log.info("🛑 Backend shutting down")


app = FastAPI(
    title="Real-Time Target Tracking System",
    description=(
        "Backend API for the GPS+IMU+Laser fusion target tracking system. "
        "Provides Kalman and α-β filter implementations, target simulation, "
        "and real-time WebSocket streaming."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — applies to HTTP requests only (not WS upgrades)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST endpoints under /api ──────────────────────────────────────────────────
app.include_router(simulation_router, prefix="/api", tags=["Simulation"])
app.include_router(calculator_router,  prefix="/api", tags=["Calculator"])

# ── WebSocket endpoint at root (Vite proxies /ws → ws://localhost:8000) ────────
app.include_router(ws_router, prefix="", tags=["WebSocket"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Target Tracking System API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
