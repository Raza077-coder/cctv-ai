"""Analytics endpoint: summary stats, per-camera stats, detections, plates."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Alert, Camera, Detection, Event, LicensePlate
from app.schemas import AnalyticsSummary, CameraStats, DetectionOut

router = APIRouter(prefix="/analytics", tags=["analytics"])

VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle"}


@router.get("/summary", response_model=AnalyticsSummary)
def summary(db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=24)

    cameras = db.query(Camera).all()
    active = sum(1 for c in cameras if c.status == "running")
    events_24h = db.query(func.count(Event.id)).filter(Event.created_at >= since).scalar() or 0
    alerts_active = db.query(func.count(Alert.id)).filter(Alert.status == "active").scalar() or 0
    people = (
        db.query(func.count(Detection.id))
        .filter(Detection.object_class == "person", Detection.created_at >= since)
        .scalar() or 0
    )
    vehicles = (
        db.query(func.count(Detection.id))
        .filter(Detection.object_class.in_(VEHICLE_CLASSES), Detection.created_at >= since)
        .scalar() or 0
    )
    plates = (
        db.query(func.count(LicensePlate.id)).filter(LicensePlate.created_at >= since).scalar() or 0
    )

    per_camera: list[CameraStats] = []
    for cam in cameras:
        cam_events = (
            db.query(func.count(Event.id))
            .filter(Event.camera_id == cam.id, Event.created_at >= since)
            .scalar() or 0
        )
        cam_alerts = (
            db.query(func.count(Alert.id))
            .filter(Alert.camera_id == cam.id, Alert.created_at >= since)
            .scalar() or 0
        )
        cam_people = (
            db.query(func.count(Detection.id))
            .filter(Detection.camera_id == cam.id, Detection.object_class == "person",
                    Detection.created_at >= since)
            .scalar() or 0
        )
        cam_vehicles = (
            db.query(func.count(Detection.id))
            .filter(Detection.camera_id == cam.id,
                    Detection.object_class.in_(VEHICLE_CLASSES),
                    Detection.created_at >= since)
            .scalar() or 0
        )
        cam_dets = (
            db.query(func.count(Detection.id))
            .filter(Detection.camera_id == cam.id, Detection.created_at >= since)
            .scalar() or 0
        )
        per_camera.append(CameraStats(
            camera_id=cam.id, camera_name=cam.name,
            events_24h=cam_events, alerts_24h=cam_alerts,
            people_count=cam_people, vehicle_count=cam_vehicles,
            detections_24h=cam_dets,
        ))

    return AnalyticsSummary(
        total_cameras=len(cameras),
        active_cameras=active,
        events_24h=events_24h,
        alerts_active=alerts_active,
        people_detected_24h=people,
        vehicles_detected_24h=vehicles,
        plates_detected_24h=plates,
        per_camera=per_camera,
    )


@router.get("/detections", response_model=dict)
def detections(
    camera_id: int | None = None,
    object_class: str | None = None,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(hours=hours)
    q = db.query(Detection).filter(Detection.created_at >= since)
    if camera_id:
        q = q.filter(Detection.camera_id == camera_id)
    if object_class:
        q = q.filter(Detection.object_class == object_class)
    total = q.count()
    items = q.order_by(Detection.created_at.desc()).limit(limit).all()
    return {"total": total, "items": [DetectionOut.model_validate(d).model_dump() for d in items]}


@router.get("/plates", response_model=dict)
def plates(
    camera_id: int | None = None,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(hours=hours)
    q = db.query(LicensePlate).filter(LicensePlate.created_at >= since)
    if camera_id:
        q = q.filter(LicensePlate.camera_id == camera_id)
    total = q.count()
    items = q.order_by(LicensePlate.created_at.desc()).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": p.id, "plate_number": p.plate_number, "normalized_plate": p.normalized_plate,
                "confidence": p.confidence, "camera_id": p.camera_id,
                "snapshot_path": p.snapshot_path, "created_at": p.created_at.isoformat(),
            }
            for p in items
        ],
    }


@router.get("/classes", response_model=dict)
def class_breakdown(hours: int = Query(default=24, ge=1, le=168), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = (
        db.query(Detection.object_class, func.count(Detection.id))
        .filter(Detection.created_at >= since)
        .group_by(Detection.object_class)
        .all()
    )
    return {"items": [{"class": c, "count": n} for c, n in rows]}


@router.get("/camera/{camera_id}/stats", response_model=CameraStats)
def camera_stats(camera_id: int, hours: int = Query(default=24, ge=1, le=168), db: Session = Depends(get_db)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    since = datetime.utcnow() - timedelta(hours=hours)
    counts = {
        "events": db.query(func.count(Event.id)).filter(Event.camera_id == camera_id, Event.created_at >= since).scalar() or 0,
        "alerts": db.query(func.count(Alert.id)).filter(Alert.camera_id == camera_id, Alert.created_at >= since).scalar() or 0,
        "people": db.query(func.count(Detection.id)).filter(Detection.camera_id == camera_id, Detection.object_class == "person", Detection.created_at >= since).scalar() or 0,
        "vehicles": db.query(func.count(Detection.id)).filter(Detection.camera_id == camera_id, Detection.object_class.in_(VEHICLE_CLASSES), Detection.created_at >= since).scalar() or 0,
        "detections": db.query(func.count(Detection.id)).filter(Detection.camera_id == camera_id, Detection.created_at >= since).scalar() or 0,
    }
    return CameraStats(
        camera_id=cam.id, camera_name=cam.name,
        events_24h=counts["events"], alerts_24h=counts["alerts"],
        people_count=counts["people"], vehicle_count=counts["vehicles"],
        detections_24h=counts["detections"],
    )
