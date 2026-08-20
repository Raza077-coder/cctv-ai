"""Per-camera processing pipeline.

Threaded pipeline per camera:
  capture -> (optional motion) -> YOLO detect -> track -> behavior/crowd
          -> ANPR -> face -> persist events/alerts -> broadcast WS -> snapshot

Runs in a daemon thread per camera; safe to start/stop via the API.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2

from app.alerts.engine import manager, record_event
from app.analytics.behavior import BehaviorAnalyzer
from app.analytics.crowd import crowd_level
from app.analytics.motion import MotionDetector
from app.anpr.plate import ANPRService
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.detection.yolo import DetectorService, VEHICLE_CLASSES
from app.face.face_service import FaceService
from app.models import Camera, Detection
from app.tracking.tracker import IoUTracker

logger = logging.getLogger(__name__)

PERSON_CLASS = "person"
TRACK_CLASSES = VEHICLE_CLASSES | {PERSON_CLASS}

# The asyncio event loop the FastAPI server runs on (captured at startup so
# worker threads can schedule WebSocket broadcasts safely).
_EVENT_LOOP: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop) -> None:
    """Called from the FastAPI lifespan so pipeline threads can broadcast."""
    global _EVENT_LOOP
    _EVENT_LOOP = loop


def get_event_loop():
    return _EVENT_LOOP


class CameraPipeline:
    def __init__(self, camera_id: int, detector: DetectorService):
        self.camera_id = camera_id
        self.detector = detector
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._cap: cv2.VideoCapture | None = None
        self.tracker = IoUTracker()
        self.motion = MotionDetector()
        self.behavior = BehaviorAnalyzer()
        self.anpr: ANPRService | None = None
        self.face: FaceService | None = None
        self.status = "stopped"
        self.fps = 0.0
        self.last_frame_stats: dict = {}
        self.snapshot_dir = Path("storage/snapshots")

    # ------------------------------------------------------------------
    def start(self, process_fps: int | None = None) -> None:
        if self._thread and self._thread.is_alive():
            return
        settings = get_settings()
        self.snapshot_dir = settings.storage_paths["snapshots"]
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._process_fps = process_fps or settings.process_fps
        if settings.enable_anpr:
            self.anpr = ANPRService(settings.storage_paths["plates"])
        if settings.enable_face_recognition:
            self.face = FaceService(settings.storage_paths["faces"], enabled=True)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=f"cam-{self.camera_id}", daemon=True)
        self._thread.start()
        self.status = "running"
        logger.info("Pipeline started for camera %d @ %d fps", self.camera_id, self._process_fps)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=8)
        if self._cap is not None:
            self._cap.release()
        self._cap = None
        self.status = "stopped"
        logger.info("Pipeline stopped for camera %d", self.camera_id)

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ------------------------------------------------------------------
    def _open_source(self, camera: Camera):
        if camera.source_type == "webcam":
            try:
                idx = int(camera.source_url)
            except ValueError:
                idx = 0
            cap = cv2.VideoCapture(idx)
        else:
            cap = cv2.VideoCapture(camera.source_url)
        return cap

    def _run(self) -> None:
        session = SessionLocal()
        try:
            camera = session.get(Camera, self.camera_id)
            if camera is None:
                logger.error("Camera %d not found", self.camera_id)
                return
            self._cap = self._open_source(camera)
            if not self._cap or not self._cap.isOpened():
                self.status = "error"
                record_event(self.camera_id, "camera_offline", f"Camera '{camera.name}' failed to open source",
                             db=session)
                camera.status = "error"
                session.commit()
                return

            # Load model once (may download weights on first run)
            try:
                self.detector.load()
            except Exception:
                self.status = "error"
                record_event(self.camera_id, "system", "YOLO model failed to load", severity="critical", db=session)
                camera.status = "error"
                session.commit()
                return

            camera.status = "running"
            camera.last_seen = datetime.utcnow()
            session.commit()

            frame_interval = 1.0 / max(1, self._process_fps)
            last_process = 0.0
            det_batch: list[dict] = []
            last_db_write = time.time()
            last_snapshot = time.time()

            while not self._stop_event.is_set():
                ok, frame = self._cap.read()
                if not ok or frame is None:
                    # EOF on file sources — restart from 0 if looping
                    if camera.source_type == "file":
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    self.status = "offline"
                    record_event(self.camera_id, "camera_offline",
                                 f"Camera '{camera.name}' lost connection", db=session)
                    camera.status = "offline"
                    session.commit()
                    break

                now = time.time()
                if now - last_process < frame_interval:
                    continue
                last_process = now

                stats = self._process_frame(frame, camera, session, det_batch)
                self.last_frame_stats = stats

                # DB write throttle (every ~2s)
                if now - last_db_write >= 2.0 and det_batch:
                    try:
                        session.add_all(det_batch)
                        session.commit()
                    except Exception as exc:
                        logger.error("DB write failed: %s", exc)
                        session.rollback()
                    det_batch = []
                    last_db_write = now

                # snapshot every ~10s
                if now - last_snapshot >= 10.0 and stats.get("any_objects"):
                    last_snapshot = now
                    path = self._save_snapshot(frame, stats)
                    if path:
                        stats["snapshot"] = path

                self._push_live(stats)
                camera.last_seen = datetime.utcnow()
                session.commit()

        except Exception as exc:
            logger.exception("Camera pipeline %d crashed", self.camera_id)
            self.status = "error"
            try:
                record_event(self.camera_id, "system", f"Pipeline error: {exc}", severity="critical", db=session)
            except Exception:
                pass
        finally:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            try:
                camera = session.get(Camera, self.camera_id)
                if camera and self.status != "running":
                    camera.status = self.status
                    session.commit()
            except Exception:
                pass
            session.close()

    # ------------------------------------------------------------------
    def _process_frame(self, frame, camera: Camera, session, det_batch) -> dict:
        stats: dict = {
            "camera_id": self.camera_id,
            "people": 0, "vehicles": 0, "objects": [],
            "motion": False, "motion_regions": [],
            "alerts": [], "events": [],
            "fps": 0.0, "crowd_level": "empty",
        }
        t0 = time.time()

        # 1) Motion
        motion_info = self.motion.detect(frame)
        stats["motion"] = motion_info["motion"]
        stats["motion_regions"] = motion_info["regions"]
        if motion_info["motion"] and get_settings().enable_motion_detection:
            stats["events"].append(("motion", f"Motion detected ({len(motion_info['regions'])} region(s))",
                                    motion_info["ratio"]))

        # 2) Detection + tracking
        try:
            detections = self.detector.detect(frame)
        except Exception as exc:
            logger.error("detect failed: %s", exc)
            detections = []
        trackable = [d for d in detections if d.class_name in TRACK_CLASSES]
        tracked = self.tracker.update(trackable)

        people_centers: list[tuple[float, float]] = []
        for track_id, bbox, class_name in tracked:
            x1, y1, x2, y2 = bbox
            people_centers.append(((x1 + x2) / 2.0, (y1 + y2) / 2.0))
            stats["objects"].append({
                "class": class_name, "track_id": track_id, "bbox": bbox,
                "label": f"{class_name.title()} #{track_id}",
            })
            if class_name == PERSON_CLASS:
                stats["people"] += 1
            elif class_name in VEHICLE_CLASSES:
                stats["vehicles"] += 1
            # persist detection (throttled batch write in _run)
            det_batch.append(Detection(
                camera_id=self.camera_id,
                object_class=class_name,
                confidence=next((d.confidence for d in detections
                                 if d.class_name == class_name and tuple(d.bbox) == tuple(bbox)), 0.0),
                track_id=track_id,
                bbox={"x1": bbox[0], "y1": bbox[1], "x2": bbox[2], "y3": bbox[3]},
            ))

        # 3) Behavior analytics
        try:
            behaviors = self.behavior.analyze(tracked, stats["people"])
            for b in behaviors:
                stats["events"].append((b.rule, b.message, b.confidence))
        except Exception as exc:
            logger.error("behavior failed: %s", exc)

        # 4) Crowd
        stats["crowd_level"] = crowd_level(stats["people"])
        if stats["crowd_level"] in ("high", "critical"):
            stats["events"].append(("crowd", f"Crowd level: {stats['crowd_level']} ({stats['people']} people)", 0.8))

        # 5) ANPR
        if self.anpr is not None:
            try:
                vehicles = [d for d in detections if d.class_name in VEHICLE_CLASSES]
                plates = self.anpr.process_frame(frame, vehicles)
                for p in plates:
                    stats["events"].append(("plate_detected", f"Plate detected: {p['normalized']}", p["confidence"]))
                    stats.setdefault("plates", []).append(p)
            except Exception as exc:
                logger.error("anpr failed: %s", exc)

        # 6) Face recognition (opt-in)
        if self.face is not None:
            try:
                faces = self.face.recognize(frame)
                for f in faces:
                    kind = "face_unknown" if f["is_unknown"] else "face_recognized"
                    name = "unknown" if f["is_unknown"] else f["name"]
                    stats["events"].append((kind, f"Face: {name} (conf {f['confidence']})", 0.7))
            except Exception as exc:
                logger.error("face failed: %s", exc)

        # 7) Persist events + alerts (deduplicated)
        for (etype, msg, conf) in stats["events"]:
            record_event(self.camera_id, etype, msg, confidence=conf,
                         extra_data={"motion_ratio": motion_info["ratio"]}, db=session)
            stats["alerts"].append({"type": etype, "message": msg, "severity": msg})

        # 8) FPS
        stats["fps"] = round(1.0 / max(1e-6, time.time() - t0), 1)
        stats["any_objects"] = bool(stats["objects"]) or stats["motion"]
        return stats

    # ------------------------------------------------------------------
    def _save_snapshot(self, frame, stats: dict) -> str | None:
        try:
            fname = f"cam{self.camera_id}_{int(time.time() * 1000)}.jpg"
            path = self.snapshot_dir / fname
            cv2.imwrite(str(path), frame)
            return str(path)
        except Exception as exc:
            logger.error("snapshot failed: %s", exc)
            return None

    def _push_live(self, stats: dict) -> None:
        loop = get_event_loop()
        if loop is None or not loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                manager.broadcast("frame_stats", {
                    "camera_id": self.camera_id,
                    "people": stats["people"],
                    "vehicles": stats["vehicles"],
                    "fps": stats["fps"],
                    "motion": stats["motion"],
                    "crowd_level": stats["crowd_level"],
                    "alerts": stats["alerts"][-5:],
                }),
                loop,
            )
        except Exception as exc:
            logger.debug("WS broadcast skipped: %s", exc)

    # ------------------------------------------------------------------
    def annotated_frame(self) -> bytes | None:
        """Return JPEG of the latest processed frame (for snapshot endpoint)."""
        if self._cap is None:
            return None
        return None  # frame stored in pipeline state would require shared buffer


# Registry of running pipelines
_pipelines: dict[int, CameraPipeline] = {}
_pipelines_lock = threading.Lock()


def get_pipeline(camera_id: int) -> CameraPipeline | None:
    with _pipelines_lock:
        return _pipelines.get(camera_id)


def start_pipeline(camera_id: int, process_fps: int | None = None) -> CameraPipeline:
    from app.detection.yolo import get_detector
    with _pipelines_lock:
        if camera_id in _pipelines and _pipelines[camera_id].running:
            return _pipelines[camera_id]
        pipeline = CameraPipeline(camera_id, get_detector())
        _pipelines[camera_id] = pipeline
    pipeline.start(process_fps)
    return pipeline


def stop_pipeline(camera_id: int) -> bool:
    with _pipelines_lock:
        pipeline = _pipelines.get(camera_id)
        if pipeline is None:
            return False
    pipeline.stop()
    return True


def stop_all_pipelines() -> None:
    with _pipelines_lock:
        ids = list(_pipelines.keys())
    for cid in ids:
        stop_pipeline(cid)
