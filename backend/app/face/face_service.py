"""Opt-in local face recognition module.

Uses OpenCV Haar cascade for face detection + LBPH recognizer (or simple
embedding distance) trained on LOCAL authorized-person images only. No external
datasets, no private biometric data. Enabled via ENABLE_FACE_RECOGNITION.

Because LBPH requires training data, the module exposes:
- register_person(name, image_path): adds a person (creates embeddings)
- recognize(frame): returns matches / unknown-person result
- If not enabled or no model data, recognize() returns [] (module is inert).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FaceService:
    def __init__(self, faces_dir: Path, enabled: bool = False,
                 cascade_path: str | None = None):
        self.faces_dir = faces_dir
        self.faces_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = enabled
        self._cascade = None
        self._recognizer = None
        self._names: dict[int, str] = {}
        self._trained = False
        if cascade_path:
            self._cascade = cv2.CascadeClassifier(cascade_path)
        else:
            try:
                self._cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                )
            except Exception:
                self._cascade = None

    def _load_cascade(self):
        if self._cascade is None:
            self._cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        return self._cascade

    def _train(self):
        """Train LBPH from registered face images in the faces dir."""
        if self._trained:
            return
        images, labels = [], []
        label = 0
        self._names = {}
        for person_dir in sorted(self.faces_dir.iterdir()):
            if not person_dir.is_dir():
                continue
            self._names[label] = person_dir.name
            for img_path in person_dir.glob("*.jpg"):
                img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                img = cv2.resize(img, (120, 120))
                images.append(img)
                labels.append(label)
            label += 1
        if images:
            self._recognizer = cv2.face.LBPHFaceRecognizer_create()
            self._recognizer.train(images, np.array(labels))
            self._trained = True
            logger.info("Face recognizer trained with %d samples / %d persons",
                        len(images), len(self._names))

    def register_person(self, name: str, image_bgr: np.ndarray) -> dict:
        """Register a person from a face crop (must be enabled)."""
        person_dir = self.faces_dir / name
        person_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{int(time.time() * 1000)}.jpg"
        path = person_dir / fname
        cv2.imwrite(str(path), image_bgr)
        self._trained = False
        return {"name": name, "image": str(path)}

    def recognize(self, frame_bgr: np.ndarray, threshold: float = 70.0) -> list[dict]:
        """Detect faces and match against the local DB.

        Returns list of {name, confidence, bbox, is_unknown}.
        """
        if not self.enabled:
            return []
        cascade = self._load_cascade()
        if cascade is None:
            return []
        try:
            self._train()
        except Exception as exc:  # pragma: no cover - cv2.face may be missing
            logger.warning("Face training unavailable: %s", exc)
            return []
        if not self._trained:
            return []  # no registered persons — nothing to match

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                         minSize=(48, 48))
        out: list[dict] = []
        for (x, y, w, h) in faces:
            crop = gray[y:y + h, x:x + w]
            crop = cv2.resize(crop, (120, 120))
            label, conf = self._recognizer.predict(crop)
            name = self._names.get(label, "unknown")
            # LBPH: lower distance = better match
            is_unknown = conf > threshold or label not in self._names
            out.append({
                "name": "unknown" if is_unknown else name,
                "confidence": round(float(conf), 1),
                "bbox": [int(x), int(y), int(w), int(h)],
                "is_unknown": bool(is_unknown),
            })
        return out
