"""Persons (face DB) + settings endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.face.face_service import FaceService
from app.models import Person, SystemSetting
from app.schemas import PersonCreate, PersonOut, SettingOut, SettingUpdate

router = APIRouter(tags=["persons", "settings"])


# ---------- Persons (face database) ----------
@router.get("/persons", response_model=list[PersonOut])
def list_persons(db: Session = Depends(get_db)):
    return db.query(Person).order_by(Person.id).all()


@router.post("/persons", response_model=PersonOut, status_code=201)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)):
    person = Person(name=payload.name, role=payload.role)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.post("/persons/{person_id}/face", response_model=dict)
async def upload_person_face(person_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a face image for a registered person (requires ENABLE_FACE_RECOGNITION)."""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "Person not found")
    settings = get_settings()
    if not settings.enable_face_recognition:
        raise HTTPException(400, "Face recognition is disabled (ENABLE_FACE_RECOGNITION=false)")
    data = await file.read()
    import cv2
    import numpy as np
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Invalid image")
    svc = FaceService(settings.storage_paths["faces"], enabled=True)
    result = svc.register_person(person.name, img)
    person.face_image_path = result["image"]
    db.commit()
    return {"status": "registered", "name": person.name, "image": result["image"]}


@router.delete("/persons/{person_id}", status_code=204)
def delete_person(person_id: int, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "Person not found")
    db.delete(person)
    db.commit()
    return None


# ---------- System settings ----------
@router.get("/settings", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db)):
    return db.query(SystemSetting).order_by(SystemSetting.key).all()


@router.put("/settings/{key}", response_model=SettingOut)
def update_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db)):
    setting = db.get(SystemSetting, key)
    if setting is None:
        setting = SystemSetting(key=key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value
    db.commit()
    db.refresh(setting)
    return setting
