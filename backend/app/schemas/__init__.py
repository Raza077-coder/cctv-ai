"""Pydantic schemas for API request/response bodies."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------- Camera ----------
class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_type: str = Field(default="rtsp", pattern="^(webcam|file|rtsp)$")
    source_url: str = Field(min_length=1, max_length=500)
    location: str | None = None
    enabled: bool = True
    detection_settings: dict[str, Any] = Field(default_factory=dict)
    alert_settings: dict[str, Any] = Field(default_factory=dict)


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    location: str | None = None
    enabled: bool | None = None
    detection_settings: dict[str, Any] | None = None
    alert_settings: dict[str, Any] | None = None


class CameraOut(CameraBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    last_seen: datetime | None = None
    created_at: datetime


# ---------- Events ----------
class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int
    camera_id: int | None
    event_type: str
    message: str
    confidence: float | None
    severity: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="extra_data")
    snapshot_path: str | None
    created_at: datetime


# ---------- Alerts ----------
class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int
    camera_id: int | None
    alert_type: str
    title: str
    message: str
    severity: str
    status: str
    snapshot_path: str | None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="extra_data")
    created_at: datetime


class AlertAck(BaseModel):
    status: str = Field(pattern="^(active|acknowledged|resolved)$")


# ---------- Detections ----------
class DetectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    camera_id: int | None
    object_class: str
    confidence: float
    track_id: int | None
    bbox: dict[str, Any]
    frame_number: int | None
    created_at: datetime


# ---------- Detection control ----------
class DetectionStart(BaseModel):
    camera_id: int
    process_fps: int | None = Field(default=None, ge=1, le=30)


class DetectionStop(BaseModel):
    camera_id: int


# ---------- Persons (face DB) ----------
class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str | None = None


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    role: str | None
    created_at: datetime


# ---------- Settings ----------
class SettingUpdate(BaseModel):
    value: str


class SettingOut(BaseModel):
    key: str
    value: str


# ---------- Analytics ----------
class CameraStats(BaseModel):
    camera_id: int
    camera_name: str
    events_24h: int
    alerts_24h: int
    people_count: int
    vehicle_count: int
    detections_24h: int


class AnalyticsSummary(BaseModel):
    total_cameras: int
    active_cameras: int
    events_24h: int
    alerts_active: int
    people_detected_24h: int
    vehicles_detected_24h: int
    plates_detected_24h: int
    per_camera: list[CameraStats]


class HealthOut(BaseModel):
    status: str
    app: str
    version: str
    database: str
    redis: str
    models_loaded: list[str]
    features: dict[str, bool]
