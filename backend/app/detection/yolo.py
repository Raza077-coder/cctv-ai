"""YOLO-based object detection service.

Uses Ultralytics YOLOv8 (or newer). The model weights file is auto-downloaded on
first use (e.g. yolov8n.pt) and cached in the models/ directory. Detection is
CPU-friendly by default; GPU is used automatically if CUDA is available.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# COCO classes we focus on for surveillance analytics
VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle"}
PERSON_CLASS = "person"
TRACKABLE_CLASSES = VEHICLE_CLASSES | {PERSON_CLASS}

# Common classes that also appear in COCO (kept for completeness in detection)
ALLOWED_CLASSES = TRACKABLE_CLASSES | {"dog", "cat", "backpack", "umbrella", "handbag"}


class DetectionResult:
    """A single detection with normalized fields."""

    __slots__ = ("class_name", "confidence", "bbox", "track_id", "frame_number")

    def __init__(self, class_name: str, confidence: float, bbox: tuple[int, int, int, int],
                 track_id: int | None = None, frame_number: int | None = None):
        self.class_name = class_name
        self.confidence = confidence
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.track_id = track_id
        self.frame_number = frame_number

    def to_dict(self) -> dict:
        x1, y1, x2, y2 = self.bbox
        return {
            "class": self.class_name,
            "confidence": round(float(self.confidence), 3),
            "track_id": self.track_id,
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "frame": self.frame_number,
        }


class DetectorService:
    """Lazy-loads the YOLO model and runs inference."""

    def __init__(self, model_name: str = "yolov8n.pt", confidence: float = 0.35,
                 model_dir: Path | None = None):
        self.model_name = model_name
        self.confidence = confidence
        self.model_dir = model_dir or Path("models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._lock = threading.Lock()
        self._load_error: str | None = None

    def load(self):
        """Load the YOLO model (idempotent). Raises on failure."""
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from ultralytics import YOLO
                weights = str(self.model_dir / self.model_name)
                self._model = YOLO(weights)
                logger.info("YOLO model %s loaded (device=%s)", weights, self._model.device)
            except Exception as exc:  # pragma: no cover - environment dependent
                self._load_error = str(exc)
                logger.error("Failed to load YOLO model %s: %s", self.model_name, exc)
                raise
        return self._model

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def detect(self, frame, conf_threshold: float | None = None) -> list[DetectionResult]:
        """Run detection on a BGR frame; returns normalized DetectionResults."""
        if self._model is None:
            self.load()
        conf = conf_threshold or self.confidence
        results = self._model.predict(frame, conf=conf, verbose=False)
        detections: list[DetectionResult] = []
        if not results:
            return detections
        r = results[0]
        names = r.names
        if r.boxes is None or len(r.boxes) == 0:
            return detections
        for box in r.boxes:
            cls_id = int(box.cls[0])
            class_name = names.get(cls_id, "unknown")
            if class_name not in ALLOWED_CLASSES:
                continue
            conf_val = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            detections.append(
                DetectionResult(class_name, conf_val, (x1, y1, x2, y2))
            )
        return detections


# Singleton used by the pipeline
_detector: DetectorService | None = None


def get_detector() -> DetectorService:
    global _detector
    if _detector is None:
        from app.core.config import get_settings
        settings = get_settings()
        _detector = DetectorService(
            model_name=settings.yolo_model,
            confidence=settings.detection_confidence,
            model_dir=Path("models"),
        )
    return _detector


def reset_detector() -> None:
    global _detector
    _detector = None
