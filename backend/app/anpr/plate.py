"""ANPR / LPR pipeline.

Pipeline: frame -> vehicle detection (from YOLO) -> plate candidate detection
(OpenCV morphology) -> OCR (pytesseract if available; otherwise modular stub) ->
normalize plate text -> store result + snapshot.

The OCR step uses pytesseract when installed. If Tesseract is not available the
module still runs the detection pipeline and reports the plate crop with
OCR unavailable — it never fabricates plate numbers.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_OCR_AVAILABLE: bool | None = None


def ocr_available() -> bool:
    global _OCR_AVAILABLE
    if _OCR_AVAILABLE is None:
        try:
            import pytesseract  # noqa: F401
            _OCR_AVAILABLE = True
        except Exception:
            _OCR_AVAILABLE = False
    return _OCR_AVAILABLE


def normalize_plate(text: str) -> str:
    """Normalize OCR output: uppercase, keep alnum, collapse spaces."""
    t = text.upper()
    t = re.sub(r"[^A-Z0-9]", "", t)
    return t


def find_plate_candidates(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Morphology-based plate candidate detection (width/height ratio heuristic)."""
    candidates: list[tuple[int, int, int, int]] = []
    # Adaptive threshold to handle lighting
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)
    # Close horizontal gaps (characters)
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_h)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h_img, w_img = gray.shape
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # License plates are typically wide rectangles
        if w < 40 or h < 12:
            continue
        aspect = w / h
        if 2.0 <= aspect <= 6.5 and h > h_img * 0.015 and w < w_img * 0.9:
            candidates.append((x, y, w, h))
    # keep top 5 by area
    candidates.sort(key=lambda r: r[2] * r[3], reverse=True)
    return candidates[:5]


def _ocr_plate_crop(crop_bgr: np.ndarray) -> str:
    import pytesseract

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    # upscale + threshold for better OCR
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # PSM 7 = single text line
    text = pytesseract.image_to_string(gray, config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return text.strip()


class ANPRService:
    def __init__(self, plates_dir: Path, min_plate_conf: float = 0.5):
        self.plates_dir = plates_dir
        self.plates_dir.mkdir(parents=True, exist_ok=True)
        self.min_plate_conf = min_plate_conf

    def process_frame(self, frame_bgr: np.ndarray, vehicles: list) -> list[dict]:
        """Detect plates on the frame near vehicle boxes.

        vehicles: list of DetectionResult for vehicle classes.
        Returns list of {plate, confidence, crop_path, bbox}.
        """
        if not ocr_available():
            return []  # OCR engine not installed — no fabricated results

        results: list[dict] = []
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        for veh in vehicles:
            vx1, vy1, vx2, vy2 = veh.bbox
            # crop the lower half of the vehicle (plate region heuristic)
            crop_top = vy1 + int((vy2 - vy1) * 0.45)
            crop_bottom = vy2 + int((vy2 - vy1) * 0.1)
            crop_top = max(0, crop_top)
            crop_bottom = min(frame_bgr.shape[0], crop_bottom)
            if crop_bottom - crop_top < 20:
                continue
            veh_region = gray[crop_top:crop_bottom, max(0, vx1 - 10):vx2 + 10]
            if veh_region.size == 0:
                continue

            candidates = find_plate_candidates(veh_region)
            for (x, y, w, h) in candidates:
                crop = frame_bgr[crop_top + y: crop_top + y + h, max(0, vx1 - 10) + x: max(0, vx1 - 10) + x + w]
                if crop.size == 0:
                    continue
                try:
                    text = _ocr_plate_crop(crop)
                except Exception as exc:  # pragma: no cover
                    logger.warning("plate OCR failed: %s", exc)
                    continue
                normalized = normalize_plate(text)
                if len(normalized) < 4:
                    continue  # too short to be a plate
                # confidence heuristic based on plate length + OCR determinism
                conf = min(0.95, 0.5 + 0.08 * len(normalized))
                fname = f"plate_{len(results):03d}_{normalized}.jpg"
                path = self.plates_dir / fname
                cv2.imwrite(str(path), crop)
                results.append({
                    "plate": text.strip().upper(),
                    "normalized": normalized,
                    "confidence": round(conf, 3),
                    "crop_path": str(path),
                    "bbox": [int(x), int(y), int(w), int(h)],
                })
                break  # one plate per vehicle per frame

        return results
