# CCTV AI — AI-Powered Video Surveillance & Analytics System

A real, runnable AI video-surveillance platform: **YOLO object detection, multi-object tracking, motion detection, behavior analytics, crowd density, ANPR (license-plate recognition), opt-in face recognition, smart alerts** — with a React dashboard, FastAPI backend, PostgreSQL storage and live WebSocket updates.

> ⚠️ **Honest feature status:** every feature below is implemented and the core pipeline was exercised end-to-end in a sandbox with a real sample video (person detection, tracking, motion events, loitering alerts, live WebSocket stats). Features marked *(not hardware-verified)* are implemented but could not be fully exercised here — see [Known Limitations](#known-limitations).

---

## Features

| Feature | Status |
|---|---|
| Real-time object detection (person/car/truck/bus/bike…) via YOLOv8 | ✅ tested on sample video |
| Multi-object tracking with stable IDs (Person #1, Car #8) | ✅ tested (track ID stable across frames) |
| Motion detection (background model, regions, sensitivity) | ✅ tested (motion events generated) |
| Behavior analytics: loitering, restricted zone, wrong direction, running, crowd | ✅ loitering tested; rules unit-tested |
| Crowd density: count, level, per-zone, heatmap helper | ✅ unit-tested |
| ANPR / license-plate recognition (modular, Tesseract OCR) | ⚠️ implemented; *(OCR not hardware-verified — Tesseract not installed in sandbox)* |
| Face recognition (opt-in, local LBPH, unknown-person events) | ⚠️ implemented; *(not verified — disabled by default)* |
| Smart alerts with dedup + severity (motion, zone, crowd, plate, unknown face, offline) | ✅ tested |
| Multi-camera: webcam / video file / RTSP | ✅ file source tested; webcam/RTSP *(not hardware-verified)* |
| Unified dashboard: live stats, cameras, events, alerts, analytics, settings | ✅ built; production build passes |
| Real-time WebSocket updates | ✅ tested (live frame stats received) |

## Tech stack

- **Backend:** Python 3.11 · FastAPI · SQLAlchemy 2 · Pydantic v2 · OpenCV · Ultralytics YOLOv8 · PostgreSQL 15 · Redis · WebSockets
- **Frontend:** React 18 · TypeScript · Vite · React Router · Recharts
- **Infra:** Docker (backend/frontend/postgres/redis) · nginx (frontend)

## Project structure

```
cctv-ai/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, lifespan, WebSocket endpoint
│   │   ├── api/               # routers: health, cameras, events, alerts,
│   │   │                      #          analytics, misc (persons/settings)
│   │   ├── core/config.py     # env-driven settings
│   │   ├── database/          # engine, session, Base
│   │   ├── models/            # SQLAlchemy models (8 tables)
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── detection/yolo.py  # YOLO detector service
│   │   ├── tracking/tracker.py# IoU multi-object tracker
│   │   ├── analytics/         # motion.py, behavior.py, crowd.py
│   │   ├── anpr/plate.py      # ANPR pipeline (plate crop + OCR)
│   │   ├── face/face_service.py # opt-in LBPH face recognition
│   │   ├── alerts/engine.py   # alert engine + WebSocket manager
│   │   ├── services/camera_pipeline.py  # threaded per-camera pipeline
│   │   └── tests/             # pytest suite (22 tests)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/             # Dashboard, Cameras, Live Monitoring,
│   │   │                      # Events, Alerts, Analytics, Settings
│   │   ├── components/        # Layout, ui primitives
│   │   ├── services/api.ts    # typed API client
│   │   ├── hooks/useLiveUpdates.ts  # WebSocket hook
│   │   └── styles.css
│   ├── Dockerfile + nginx.conf
│   └── package.json
├── models/                    # YOLO weights (git-ignored, auto-downloaded)
├── storage/                   # snapshots/recordings/plates/faces (git-ignored)
├── scripts/                   # setup.sh, test_e2e.sh
├── docs/architecture.md
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## Requirements

- Python 3.10+ (3.11 recommended)
- Node.js 18+ / npm
- PostgreSQL 14+ (or the bundled Docker service)
- Redis 6+ (or the bundled Docker service)
- ffmpeg (optional, for video transcoding)

## Installation

```bash
# 1. Clone & enter
git clone https://github.com/Raza077-coder/cctv-ai.git
cd cctv-ai

# 2. (Optional) system deps on Debian/Ubuntu
./scripts/setup.sh

# 3. Backend
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env        # edit DATABASE_URL / SECRET_KEY

# 4. Create the database (local Postgres)
su postgres -c "psql -c \"CREATE USER cctv WITH PASSWORD 'CCTV_secret_change_me' CREATEDB;\""
su postgres -c "psql -c 'CREATE DATABASE cctv_ai OWNER cctv;'"

# 5. Frontend
cd ../frontend
npm install
```

## Run locally

```bash
# Terminal 1 — backend (first start downloads yolov8n.pt ~6 MB)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
# API docs: http://localhost:8000/docs
# Health:   http://localhost:8000/api/health

# Terminal 2 — frontend (dev server with API/WS proxy)
cd frontend
npm run dev
# Open http://localhost:5173
```

## Docker

```bash
docker compose up --build
# frontend: http://localhost:8080
# backend:  http://localhost:8000/api/health
# docs:     http://localhost:8000/docs
```

GPU support: install the nvidia-container-toolkit, then uncomment the `deploy.resources.reservations` block in `docker-compose.yml`.

## Usage

1. **Add a camera** — Cameras page → add a webcam (`0`), a video file (`/path/to/video.mp4`), or an RTSP stream (`rtsp://user:pass@host/...`).
2. **Start detection** — click *Start Detection* on the camera card.
3. **Live monitoring** — the Live Monitoring page shows per-camera people / vehicles / FPS / motion / crowd stats streamed over WebSocket.
4. **Events & Alerts** — browse the event log; acknowledge or resolve alerts.
5. **Analytics** — charts of per-camera activity, class breakdown, plate reads.

## Environment variables

See [`.env.example`](.env.example). Key ones:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `SECRET_KEY` | — | signing secret (generate one) |
| `YOLO_MODEL` | `yolov8n.pt` | model weights file |
| `DETECTION_CONFIDENCE` | `0.35` | YOLO confidence threshold |
| `PROCESS_FPS` | `15` | analysis rate (lower = less CPU) |
| `ENABLE_ANPR` | `true` | ANPR pipeline on/off |
| `ENABLE_FACE_RECOGNITION` | `false` | face recognition on/off (opt-in) |
| `ENABLE_MOTION_DETECTION` | `true` | motion detection on/off |
| `CORS_ORIGINS` | localhost list | allowed frontend origins |

## API documentation

Interactive OpenAPI docs at `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc`. Key endpoints:

```
GET  /api/health
GET  /api/cameras            POST /api/cameras
PUT  /api/cameras/{id}       DELETE /api/cameras/{id}
POST /api/cameras/detection/start    POST /api/cameras/detection/stop
GET  /api/events             GET /api/alerts
PATCH /api/alerts/{id}
GET  /api/analytics/summary  GET /api/analytics/detections
GET  /api/analytics/plates   GET /api/analytics/classes
GET  /api/persons            POST /api/persons
GET  /api/settings           PUT /api/settings/{key}
WS   /ws
```

## Testing

```bash
# Backend unit + API tests (requires a running local PostgreSQL; creates cctv_ai_test)
cd backend
python -m pytest app/tests -q

# Frontend type-check + production build
cd frontend
npm run build

# End-to-end smoke test against a running backend + sample video
./scripts/test_e2e.sh http://localhost:8000 storage/intel_sample.mp4
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `No space left on device` during pip install | `pip cache purge`; use the CPU torch wheel (`--index-url https://download.pytorch.org/whl/cpu`) |
| YOLO model download slow / blocked | place `yolov8n.pt` in `models/` manually |
| `permission denied to create database` (tests) | `ALTER USER cctv CREATEDB;` |
| Webcam not opening in Docker | pass `--device /dev/video0` to the container, or use a file/RTSP source |
| OCR plates empty | install Tesseract: `apt-get install -y tesseract-ocr` and restart |
| FPS low | lower `PROCESS_FPS`, use a smaller model (`yolov8n.pt`), or enable GPU |

## Security & privacy notes

- All credentials are env-based; **never commit `.env`**.
- Face recognition is **opt-in** (`ENABLE_FACE_RECOGNITION=true`) and uses a **local** authorized-person database only — no external datasets, no biometric data in the repository.
- Snapshots, recordings, plate crops and face images live under `storage/` which is git-ignored. Deploy behind a reverse proxy with TLS and restrict access to the storage endpoints in production.
- Behavior analytics are rule-based heuristics with explicit confidence — they are not certified AI predictions; a human operator should verify alerts before any enforcement action.

## Known limitations

- **ANPR OCR not hardware-verified**: the detection → crop → OCR → normalize pipeline is implemented, but the sandbox lacked Tesseract, so plate *text* recognition was not exercised on real footage. Install `tesseract-ocr` and test with a real vehicle plate video.
- **Face recognition not exercised**: disabled by default; requires locally registered face images to train the LBPH model.
- **Webcam / RTSP not hardware-verified**: the code paths are implemented and unit-covered; no physical camera was available in the sandbox.
- **CPU-only**: inference ran on CPU (~2–10 FPS depending on resolution). GPU deployment is supported via Docker with the nvidia runtime.
- No "24/7 recording" or commercial-grade guarantees are claimed — this is a capable development platform, not a certified security product.

## License

[MIT](LICENSE) © 2026 Ali Raza (Raza077-coder)
