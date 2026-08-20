"""Alert engine: raises alerts for events, deduplicates, persists to DB."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models import Alert, Event
from app.schemas import AlertOut

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    "motion": "low",
    "restricted_zone": "high",
    "loitering": "medium",
    "wrong_direction": "medium",
    "crowd": "high",
    "running": "medium",
    "plate_detected": "info",
    "face_unknown": "high",
    "face_recognized": "info",
    "camera_offline": "critical",
    "camera_online": "info",
    "system": "info",
}


@dataclass
class LiveUpdate:
    kind: str  # event | alert | detection | status | frame_stats
    payload: dict = field(default_factory=dict)


class ConnectionManager:
    """WebSocket connection manager (broadcast live updates to dashboard)."""

    def __init__(self):
        self._connections: list = []

    async def connect(self, ws) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("WS client connected (%d total)", len(self._connections))

    def disconnect(self, ws) -> None:
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, kind: str, payload: dict) -> None:
        message = {"kind": kind, "data": payload, "ts": datetime.utcnow().isoformat() + "Z"}
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


def _db() -> Session:
    return SessionLocal()


def record_event(camera_id: int | None, event_type: str, message: str,
                 severity: str | None = None, confidence: float | None = None,
                 extra_data: dict | None = None, snapshot_path: str | None = None,
                 raise_alert: bool = True, db: Session | None = None) -> Event:
    """Persist an event (+ optionally alert) and broadcast over WS."""
    own_session = db is None
    session = db or _db()
    try:
        severity = severity or SEVERITY_MAP.get(event_type, "info")
        ev = Event(
            camera_id=camera_id,
            event_type=event_type,
            message=message,
            severity=severity,
            confidence=confidence,
            extra_data=extra_data or {},
            snapshot_path=snapshot_path,
        )
        session.add(ev)
        session.commit()
        session.refresh(ev)

        if raise_alert:
            # Deduplicate: skip if an active alert of this type exists within the window
            window_s = 30.0 if event_type in ("motion", "loitering", "running", "wrong_direction") else 60.0
            if not _recent_active_alert(session, camera_id, event_type, window_s):
                alert = Alert(
                    camera_id=camera_id,
                    alert_type=event_type,
                    title=event_type.replace("_", " ").title(),
                    message=message,
                    severity=severity,
                    snapshot_path=snapshot_path,
                    extra_data=extra_data or {},
                )
                session.add(alert)
                session.commit()
                session.refresh(alert)
            else:
                alert = None
        else:
            alert = None
        return ev
    finally:
        if own_session:
            session.close()


def _recent_active_alert(session: Session, camera_id: int | None, alert_type: str,
                         window_s: float) -> bool:
    """True if an active alert of this type exists within the window."""
    cutoff = datetime.utcnow() - timedelta(seconds=window_s)
    existing = (
        session.query(Alert)
        .filter(Alert.camera_id == camera_id, Alert.alert_type == alert_type,
                Alert.created_at >= cutoff, Alert.status == "active")
        .first()
    )
    return existing is not None


def dedup_alert(camera_id: int | None, alert_type: str, window_s: float = 15.0,
                db: Session | None = None) -> bool:
    """True if an active alert of this type was created within the window."""
    session = db or _db()
    try:
        cutoff = datetime.utcnow() - timedelta(seconds=window_s)
        existing = (
            session.query(Alert)
            .filter(Alert.camera_id == camera_id, Alert.alert_type == alert_type,
                    Alert.created_at >= cutoff)
            .first()
        )
        return existing is not None
    finally:
        if session is not None and db is None:
            session.close()
