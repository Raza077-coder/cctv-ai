"""CCTV AI — FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.alerts.engine import manager
from app.api import alerts, analytics, cameras, events, health, misc
from app.core.config import get_settings
from app.database.session import init_db
from app.services.camera_pipeline import set_event_loop, stop_all_pipelines

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("cctv_ai")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_storage()
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as exc:
        logger.error("Database init failed: %s", exc)
    set_event_loop(asyncio.get_running_loop())
    yield
    stop_all_pipelines()
    logger.info("Shutdown complete")


app = FastAPI(
    title="CCTV AI",
    description="AI-Powered Video Surveillance & Analytics System — "
                "YOLO object detection, multi-object tracking, motion detection, "
                "behavior analytics, crowd density, ANPR, face recognition, smart alerts.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(cameras.router, prefix=settings.api_prefix)
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(alerts.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(misc.router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Live updates: frame_stats, events, alerts broadcast to connected dashboards."""
    await manager.connect(ws)
    try:
        while True:
            # keepalive ping from client; we respond with pong
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({"kind": "pong", "ts": __import__("datetime").datetime.utcnow().isoformat() + "Z"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
