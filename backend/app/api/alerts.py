"""Alerts endpoint with filtering, pagination, acknowledgment."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Alert
from app.schemas import AlertAck, AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=dict)
def list_alerts(
    camera_id: int | None = None,
    alert_type: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Alert)
    if camera_id:
        q = q.filter(Alert.camera_id == camera_id)
    if alert_type:
        q = q.filter(Alert.alert_type == alert_type)
    if status:
        q = q.filter(Alert.status == status)
    if severity:
        q = q.filter(Alert.severity == severity)
    total = q.count()
    items = q.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [AlertOut.model_validate(a).model_dump() for a in items]}


@router.patch("/{alert_id}", response_model=AlertOut)
def ack_alert(alert_id: int, payload: AlertAck, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = payload.status
    db.commit()
    db.refresh(alert)
    return alert
