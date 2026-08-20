"""SQLAlchemy ORM models for CCTV AI."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Camera(Base):
    """A video source: webcam (0), local file, or RTSP stream."""

    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="rtsp")  # webcam|file|rtsp
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Detection / alert settings (JSON blobs)
    detection_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    alert_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="stopped")  # stopped|running|error|offline
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    events: Mapped[list[Event]] = relationship(back_populates="camera", cascade="all, delete-orphan")
    alerts: Mapped[list[Alert]] = relationship(back_populates="camera", cascade="all, delete-orphan")
    detections: Mapped[list[Detection]] = relationship(back_populates="camera", cascade="all, delete-orphan")


class Event(Base):
    """A timestamped event (motion, zone entry, crowd, plate, face, ...)."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)  # motion|zone_entry|loitering|wrong_direction|crowd|running|plate_detected|face_unknown|face_recognized|camera_offline
    message: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info|low|medium|high|critical
    extra_data: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    camera: Mapped[Camera | None] = relationship(back_populates="events")


class Alert(Base):
    """A notification-level alert raised by the alert engine."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # info|low|medium|high|critical
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|acknowledged|resolved
    snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extra_data: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    camera: Mapped[Camera | None] = relationship(back_populates="alerts")


class Detection(Base):
    """An individual object detection (person / car / ...) at a point in time."""

    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    object_class: Mapped[str] = mapped_column(String(50), index=True)  # person|car|truck|...
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox: Mapped[dict] = mapped_column(JSON, default=dict)  # {x1,y1,x2,y2}
    frame_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_data: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    camera: Mapped[Camera | None] = relationship(back_populates="detections")


class Person(Base):
    """Local authorized-person database (opt-in face recognition)."""

    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    embedding: Mapped[list] = mapped_column(JSON, default=list)  # face embedding vector
    face_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LicensePlate(Base):
    """Recognized license plate records (ANPR)."""

    __tablename__ = "license_plates"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    plate_number: Mapped[str] = mapped_column(String(30), index=True)
    normalized_plate: Mapped[str] = mapped_column(String(30), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SystemSetting(Base):
    """Key/value system settings (motion sensitivity, thresholds, ...)."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
