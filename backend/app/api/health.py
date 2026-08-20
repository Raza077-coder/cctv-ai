"""Health endpoint: app, database, redis, models, features."""
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.database.session import engine
from app.detection.yolo import get_detector
from app.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    settings = get_settings()

    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    redis_status = "not_configured"
    try:
        import redis
        r = redis.Redis.from_url(settings.redis_url, socket_timeout=2)
        redis_status = "ok" if r.ping() else "error"
    except Exception:
        redis_status = "unavailable"

    detector = get_detector()
    models_loaded = [settings.yolo_model] if detector.loaded else []
    if detector.load_error:
        models_loaded = []

    return HealthOut(
        status="ok" if db_status == "ok" else "degraded",
        app=settings.app_name,
        version=settings.app_version,
        database=db_status,
        redis=redis_status,
        models_loaded=models_loaded,
        features={
            "face_recognition": settings.enable_face_recognition,
            "anpr": settings.enable_anpr,
            "motion_detection": settings.enable_motion_detection,
        },
    )
