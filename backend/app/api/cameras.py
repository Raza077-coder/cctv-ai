"""Camera CRUD + start/stop detection endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Camera
from app.schemas import CameraCreate, CameraOut, CameraUpdate, DetectionStart, DetectionStop
from app.services.camera_pipeline import start_pipeline, stop_pipeline

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraOut])
def list_cameras(enabled: bool | None = None, db: Session = Depends(get_db)):
    q = db.query(Camera).order_by(Camera.id)
    if enabled is not None:
        q = q.filter(Camera.enabled == enabled)
    return q.all()


@router.post("", response_model=CameraOut, status_code=201)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    cam = Camera(**payload.model_dump())
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    return cam


@router.put("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cam, k, v)
    db.commit()
    db.refresh(cam)
    return cam


@router.delete("/{camera_id}", status_code=204)
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    stop_pipeline(camera_id)
    db.delete(cam)
    db.commit()
    return None


@router.post("/detection/start", response_model=dict)
def start_detection(payload: DetectionStart, db: Session = Depends(get_db)):
    cam = db.get(Camera, payload.camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    pipeline = start_pipeline(payload.camera_id, payload.process_fps)
    cam.status = "running"
    db.commit()
    return {"status": "started", "camera_id": payload.camera_id, "fps": pipeline._process_fps}


@router.post("/detection/stop", response_model=dict)
def stop_detection(payload: DetectionStop, db: Session = Depends(get_db)):
    cam = db.get(Camera, payload.camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    stopped = stop_pipeline(payload.camera_id)
    if cam:
        cam.status = "stopped"
        db.commit()
    return {"status": "stopped" if stopped else "not_running", "camera_id": payload.camera_id}
