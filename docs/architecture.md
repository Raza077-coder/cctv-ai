# CCTV AI — Architecture

## Overview

CCTV AI is an AI-powered video surveillance & analytics platform. Video sources
(webcam / file / RTSP) are processed by a per-camera threaded pipeline that
runs YOLO object detection, IoU-based multi-object tracking, motion detection,
rule-based behavior analytics, crowd density, optional ANPR and optional face
recognition. Results are persisted to PostgreSQL and streamed live to the
dashboard over WebSocket.

```
┌───────────┐     ┌──────────────────────────────────────────────────────────┐
│   React   │────▶│  FastAPI  (REST /api + WebSocket /ws)                    │
│  Frontend │◀────│                                                          │
│ (Vite/TS) │  WS │  ├─ api/        routers (health, cameras, events,        │
└───────────┘     │  │              alerts, analytics, settings, persons)   │
                  │  ├─ services/   CameraPipeline (thread per camera)       │
                  │  ├─ detection/  YOLO (Ultralytics)                       │
                  │  ├─ tracking/   IoU tracker (stable IDs)                 │
                  │  ├─ analytics/  motion, behavior rules, crowd            │
                  │  ├─ anpr/       plate detection + OCR (Tesseract)        │
                  │  ├─ face/       opt-in LBPH face recognition             │
                  │  ├─ alerts/     alert engine + WS manager                │
                  │  ├─ models/     SQLAlchemy ORM (7 tables)                │
                  │  ├─ schemas/    Pydantic request/response models         │
                  │  └─ database/   engine/session                           │
                  └───────────────┬──────────────────────────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  PostgreSQL (events, alerts,│
                    │  detections, cameras,       │
                    │  persons, plates, settings) │
                    └────────────────────────────┘
```

## Processing pipeline (per camera, daemon thread)

1. **Capture** — OpenCV `VideoCapture` (webcam index, file path, or RTSP URL).
2. **Motion detection** — running-average background model; frame differencing
   + threshold; contour regions with `motion` ratio.
3. **Object detection** — YOLOv8-nano (CPU-friendly, auto-downloaded weights);
   focuses on surveillance classes: person, car, motorcycle, bus, truck, bicycle.
4. **Multi-object tracking** — greedy IoU association with class consistency;
   every track keeps a stable `track_id` (e.g. `Person #1`) until lost for N
   frames. No external re-ID weights required.
5. **Behavior analytics** (rule-based, auditable, not perfect AI):
   - loitering (track stays > `loiter_seconds`),
   - restricted-zone entry (point-in-polygon),
   - wrong-direction movement (velocity vs. expected flow),
   - running (person speed in px/s),
   - crowd (people count ≥ threshold).
   Each result carries the rule name + confidence so operators can audit.
6. **Crowd density** — people count, crowd level, heat overlay helper.
7. **ANPR** (opt-in) — vehicle boxes → plate candidate morphology → Tesseract
   OCR → normalize → store (plate, confidence, snapshot crop). If Tesseract is
   unavailable the module reports nothing — it never fabricates plates.
8. **Face recognition** (opt-in, local DB only) — Haar cascade + LBPH trained
   on locally registered person images; unknown-person events. No external
   datasets, no private biometric data committed.
9. **Persistence + alerts** — events always recorded; alerts deduplicated per
   type in a time window; both written to PostgreSQL and broadcast over WS.

## Data model

| Table             | Purpose                                             |
|-------------------|-----------------------------------------------------|
| `cameras`         | video sources + detection/alert settings            |
| `events`          | timestamped event log (motion, zone, crowd, plate…) |
| `alerts`          | notification-level alerts (active/ack/resolved)     |
| `detections`      | per-object detections (class, conf, track_id, bbox) |
| `persons`         | local authorized-person face DB                     |
| `license_plates`  | ANPR results                                        |
| `system_settings` | key/value system configuration                      |

## API surface (`/api`)

- `GET /health` — app/db/redis/models status
- `GET|POST /cameras`, `PUT|DELETE /cameras/{id}` — CRUD
- `POST /cameras/detection/start|stop` — pipeline control
- `GET /events` — filtered, paginated event log
- `GET /alerts`, `PATCH /alerts/{id}` — alerts + acknowledgment
- `GET /analytics/summary|detections|plates|classes|camera/{id}/stats`
- `GET|POST /persons`, `POST /persons/{id}/face`, `DELETE /persons/{id}`
- `GET|PUT /settings/{key}`
- `WS /ws` — live `frame_stats` / event / alert broadcasts

## Security model

- All secrets via environment variables (`.env`, never committed).
- CORS restricted to configured origins.
- Input validation via Pydantic schemas on every endpoint.
- Storage dirs (`snapshots/`, `recordings/`, `plates/`, `faces/`) are
  git-ignored; biometric data stays local and opt-in.
- No hardcoded passwords; default credentials in `.env.example` are
  placeholders that must be changed.

## Scalability notes

- Each camera runs its own thread; for many cameras or GPU inference, run
  multiple backend replicas behind a load balancer (pipeline state is
  in-memory per process; PostgreSQL is the shared store).
- Redis is used for the health/status layer and is available for pub/sub or
  queue-based scaling (e.g. Celery) if needed.
