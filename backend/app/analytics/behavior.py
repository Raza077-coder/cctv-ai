"""Rule-based behavior analytics.

These are practical computer-vision heuristics, NOT perfect AI predictions.
Each rule outputs a confidence and the rule that triggered it so results can be
audited. Rules:

- loitering:       track stays inside a zone (or frame) for > loiter_seconds
- restricted_zone: a person/vehicle enters a user-defined polygon
- wrong_direction: track moves predominantly against the expected flow vector
- crowd:           > crowd_threshold people in one frame/zone
- running:         person speed > running_speed_threshold px/sec
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BehaviorResult:
    rule: str
    message: str
    confidence: float
    track_id: int | None = None
    metadata: dict = field(default_factory=dict)


class ZoneAnalyzer:
    """Point-in-polygon helper for restricted zones."""

    @staticmethod
    def point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
        if not polygon or len(polygon) < 3:
            return False
        inside = False
        n = len(polygon)
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            if ((y1 > y) != (y2 > y)) and (
                x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
            ):
                inside = not inside
        return inside


class BehaviorAnalyzer:
    def __init__(
        self,
        loiter_seconds: float = 10.0,
        running_speed: float = 220.0,          # px/sec
        crowd_threshold: int = 5,
        expected_flow: tuple[float, float] = (0.0, -1.0),  # moving "up" by default
    ):
        self.loiter_seconds = loiter_seconds
        self.running_speed = running_speed
        self.crowd_threshold = crowd_threshold
        self.expected_flow = expected_flow

        # per-track state: track_id -> {first_seen, last_seen, positions, in_zone}
        self._state: dict[int, dict] = {}
        self._zone_polygon: list[list[float]] = []
        self._zone_name: str = "restricted"
        self._last_frame_time: float = time.time()

    def set_zone(self, polygon: list[list[float]], name: str = "restricted") -> None:
        self._zone_polygon = polygon
        self._zone_name = name

    def clear_zone(self) -> None:
        self._zone_polygon = []

    def reset(self) -> None:
        self._state.clear()

    def _speed(self, track_id: int, x: float, y: float, dt: float) -> float:
        st = self._state.get(track_id)
        if not st or not st["positions"] or dt <= 0:
            return 0.0
        lx, ly = st["positions"][-1]
        return ((x - lx) ** 2 + (y - ly) ** 2) ** 0.5 / dt

    def analyze(
        self,
        tracks: list[tuple[int, tuple[int, int, int, int], str]],
        people_count: int,
        now: float | None = None,
    ) -> list[BehaviorResult]:
        """Analyze current tracked objects. Returns triggered behavior results."""
        if now is None:
            now = time.time()
        dt = max(0.001, now - self._last_frame_time)
        self._last_frame_time = now
        results: list[BehaviorResult] = []
        seen_ids: set[int] = set()

        for track_id, bbox, class_name in tracks:
            x1, y1, x2, y2 = bbox
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            seen_ids.add(track_id)

            st = self._state.setdefault(
                track_id, {"first_seen": now, "last_seen": now, "positions": [], "zone_alerted": False}
            )
            st["last_seen"] = now
            st["positions"].append((cx, cy))
            if len(st["positions"]) > 90:
                st["positions"].pop(0)

            # ---- Loitering (person) ----
            if class_name == "person" and (now - st["first_seen"]) >= self.loiter_seconds:
                if not st.get("loiter_alerted"):
                    st["loiter_alerted"] = True
                    results.append(BehaviorResult(
                        rule="loitering",
                        message=f"Person #{track_id} loitering for {now - st['first_seen']:.0f}s",
                        confidence=0.7,
                        track_id=track_id,
                        metadata={"duration_s": round(now - st["first_seen"], 1)},
                    ))

            # ---- Restricted zone entry ----
            if self._zone_polygon and ZoneAnalyzer.point_in_polygon(cx, cy, self._zone_polygon):
                if not st.get("zone_alerted"):
                    st["zone_alerted"] = True
                    results.append(BehaviorResult(
                        rule="restricted_zone",
                        message=f"{class_name.title()} #{track_id} entered {self._zone_name} zone",
                        confidence=0.85,
                        track_id=track_id,
                        metadata={"zone": self._zone_name},
                    ))
            else:
                st["zone_alerted"] = False

            # ---- Wrong direction ----
            if len(st["positions"]) >= 5:
                dx = cx - st["positions"][-5][0]
                dy = cy - st["positions"][-5][1]
                mag = (dx * dx + dy * dy) ** 0.5
                if mag > 30:
                    dot = dx * self.expected_flow[0] + dy * self.expected_flow[1]
                    if dot < -0.35 * mag:
                        results.append(BehaviorResult(
                            rule="wrong_direction",
                            message=f"{class_name.title()} #{track_id} moving against expected flow",
                            confidence=0.6,
                            track_id=track_id,
                        ))

            # ---- Running (person speed) ----
            if class_name == "person":
                speed = self._speed(track_id, cx, cy, dt)
                if speed > self.running_speed:
                    results.append(BehaviorResult(
                        rule="running",
                        message=f"Person #{track_id} running ({speed:.0f} px/s)",
                        confidence=0.65,
                        track_id=track_id,
                        metadata={"speed_px_s": round(speed, 1)},
                    ))

        # ---- Crowd ----
        if people_count >= self.crowd_threshold:
            results.append(BehaviorResult(
                rule="crowd",
                message=f"Crowd detected: {people_count} people",
                confidence=min(0.9, 0.4 + people_count * 0.05),
                metadata={"people": people_count, "threshold": self.crowd_threshold},
            ))

        # clean up lost tracks
        for tid in list(self._state.keys()):
            if tid not in seen_ids and (now - self._state[tid]["last_seen"]) > 30:
                del self._state[tid]

        return results
