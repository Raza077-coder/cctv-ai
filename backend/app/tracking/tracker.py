"""Multi-object tracking with persistent IDs.

Implements a lightweight IoU-based tracker (ByteTrack-style association) so that
every tracked person/vehicle keeps a stable ID across frames. This is a clean,
dependency-free implementation: no torchreid/deep sort weights are required.
"""
from __future__ import annotations

import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1, ix2, iy2 = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter / (area_a + area_b - inter + 1e-9)


class Track:
    __slots__ = ("track_id", "class_name", "bbox", "age", "hits", "last_bboxes")

    def __init__(self, track_id: int, class_name: str, bbox: tuple[int, int, int, int]):
        self.track_id = track_id
        self.class_name = class_name
        self.bbox = bbox
        self.age = 0          # frames since last update
        self.hits = 1
        self.last_bboxes: list[tuple[int, int, int, int]] = [bbox]

    @property
    def lost(self) -> bool:
        return self.age > 0

    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


class IoUTracker:
    """Simple greedy IoU tracker with class-consistent matching."""

    def __init__(self, iou_threshold: float = 0.3, max_lost: int = 15):
        self.iou_threshold = iou_threshold
        self.max_lost = max_lost
        self._tracks: OrderedDict[int, Track] = OrderedDict()
        self._next_id = 1

    def update(self, detections: list) -> list:
        """Match detections to existing tracks.

        Each detection: object with .class_name, .bbox, .confidence.
        Returns list of (track_id, class_name, bbox).
        """
        # 1) Age existing tracks
        for tid in list(self._tracks.keys()):
            self._tracks[tid].age += 1
            if self._tracks[tid].age > self.max_lost:
                del self._tracks[tid]

        matched_det_idx: set[int] = set()
        results: list[tuple[int, tuple[int, int, int, int], str]] = []

        # 2) Greedy association (same class only)
        for tid, track in list(self._tracks.items()):
            best_iou, best_idx = self.iou_threshold, -1
            for i, det in enumerate(detections):
                if i in matched_det_idx or det.class_name != track.class_name:
                    continue
                iou = _iou(track.bbox, det.bbox)
                if iou > best_iou:
                    best_iou, best_idx = iou, i
            if best_idx >= 0:
                det = detections[best_idx]
                track.bbox = det.bbox
                track.age = 0
                track.hits += 1
                track.last_bboxes.append(det.bbox)
                if len(track.last_bboxes) > 60:
                    track.last_bboxes.pop(0)
                matched_det_idx.add(best_idx)
                results.append((track.track_id, det.bbox, det.class_name))

        # 3) New tracks for unmatched detections
        for i, det in enumerate(detections):
            if i in matched_det_idx:
                continue
            track = Track(self._next_id, det.class_name, det.bbox)
            self._tracks[self._next_id] = track
            results.append((track.track_id, det.bbox, det.class_name))
            self._next_id += 1

        return results

    def get_track(self, track_id: int) -> Track | None:
        return self._tracks.get(track_id)

    def active_tracks(self) -> list[Track]:
        return [t for t in self._tracks.values() if not t.lost]

    def clear(self) -> None:
        self._tracks.clear()
        self._next_id = 1
