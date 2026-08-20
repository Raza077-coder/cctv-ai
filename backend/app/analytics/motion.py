"""OpenCV-based motion detection (frame differencing + threshold)."""
from __future__ import annotations

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class MotionDetector:
    def __init__(self, sensitivity: float = 25.0, min_area: int = 800,
                 blur_size: int = 21):
        self.sensitivity = sensitivity   # threshold on diff
        self.min_area = min_area         # min contour area to count as motion
        self.blur_size = blur_size
        self._background: np.ndarray | None = None
        self._bg_weight = 0.05

    def reset(self) -> None:
        self._background = None

    def detect(self, frame_bgr: np.ndarray) -> dict:
        """Return motion info for the frame.

        Returns: {motion: bool, ratio: float, regions: [[x,y,w,h],...], frame: annotated}
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (self.blur_size, self.blur_size), 0)

        if self._background is None:
            self._background = gray.astype(np.float32)
            return {"motion": False, "ratio": 0.0, "regions": [], "frame": frame_bgr}

        # Running average background model
        self._background = (
            (1 - self._bg_weight) * self._background + self._bg_weight * gray.astype(np.float32)
        )

        diff = cv2.absdiff(gray, self._background.astype(np.uint8))
        _, thresh = cv2.threshold(diff, self.sensitivity, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions: list[list[int]] = []
        total_area = 0.0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                regions.append([int(x), int(y), int(w), int(h)])
                total_area += area

        frame_h, frame_w = gray.shape
        ratio = total_area / (frame_w * frame_h)

        annotated = frame_bgr.copy()
        for (x, y, w, h) in regions:
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 165, 255), 2)

        return {
            "motion": ratio > 0.001,
            "ratio": round(float(ratio), 5),
            "regions": regions,
            "frame": annotated,
        }
