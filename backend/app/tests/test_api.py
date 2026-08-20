"""Backend test suite: startup, health, DB, cameras, events, alerts, analytics."""
import time

from app.tests.conftest import TEST_DB  # noqa: F401


def test_app_startup_and_root(client):
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["app"] == "CCTV AI"
    assert "/docs" in body["docs"]


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in ("ok", "degraded")
    assert body["database"] in ("ok", "error")
    assert "features" in body


def test_openapi_docs_available(client):
    res = client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]
    for p in ["/api/health", "/api/cameras", "/api/events", "/api/alerts", "/api/analytics/summary"]:
        assert p in paths, f"missing route {p}"


def test_database_connection(client):
    from sqlalchemy import text
    from app.database.session import engine
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_camera_crud(client):
    # create
    res = client.post("/api/cameras", json={
        "name": "CRUD Cam",
        "source_type": "rtsp",
        "source_url": "rtsp://example.com/stream",
    })
    assert res.status_code == 201
    cam = res.json()
    assert cam["name"] == "CRUD Cam"
    cid = cam["id"]

    # list
    res = client.get("/api/cameras")
    assert res.status_code == 200
    ids = [c["id"] for c in res.json()]
    assert cid in ids

    # get
    res = client.get(f"/api/cameras/{cid}")
    assert res.status_code == 200
    assert res.json()["source_type"] == "rtsp"

    # update
    res = client.put(f"/api/cameras/{cid}", json={"name": "CRUD Cam v2", "location": "gate"})
    assert res.status_code == 200
    assert res.json()["name"] == "CRUD Cam v2"
    assert res.json()["location"] == "gate"

    # delete
    res = client.delete(f"/api/cameras/{cid}")
    assert res.status_code == 204
    res = client.get(f"/api/cameras/{cid}")
    assert res.status_code == 404


def test_camera_validation(client):
    res = client.post("/api/cameras", json={"name": "", "source_url": ""})
    assert res.status_code == 422
    res = client.post("/api/cameras", json={
        "name": "Bad", "source_type": "drone", "source_url": "x",
    })
    assert res.status_code == 422


def test_events_flow(client, sample_camera):
    cid = sample_camera["id"]

    # create events directly via DB to simulate pipeline
    from app.database.session import SessionLocal
    from app.models import Event
    db = SessionLocal()
    before = db.query(Event).filter(Event.camera_id == cid).count()
    db.add(Event(camera_id=cid, event_type="motion", message="Motion detected", severity="low"))
    db.add(Event(camera_id=cid, event_type="crowd", message="Crowd: 6 people", severity="high"))
    db.commit()
    db.close()

    res = client.get("/api/events", params={"camera_id": cid})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= before + 2
    types = {e["event_type"] for e in body["items"]}
    assert "motion" in types and "crowd" in types

    # filter by type
    res = client.get("/api/events", params={"event_type": "motion"})
    assert all(e["event_type"] == "motion" for e in res.json()["items"])


def test_alerts_flow(client, sample_camera):
    cid = sample_camera["id"]
    from app.database.session import SessionLocal
    from app.models import Alert
    db = SessionLocal()
    alert = Alert(camera_id=cid, alert_type="restricted_zone", title="Zone Breach",
                  message="Person entered restricted zone", severity="high")
    db.add(alert)
    db.commit()
    db.refresh(alert)
    db.close()

    res = client.get("/api/alerts", params={"status": "active"})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    match = next(a for a in body["items"] if a["id"] == alert.id)
    assert match["status"] == "active"

    # acknowledge
    res = client.patch(f"/api/alerts/{alert.id}", json={"status": "acknowledged"})
    assert res.status_code == 200
    assert res.json()["status"] == "acknowledged"


def test_analytics_summary(client, sample_camera):
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["total_cameras"] >= 1
    assert body["active_cameras"] >= 0
    assert "per_camera" in body
    assert all(c["camera_id"] > 0 for c in body["per_camera"])


def test_analytics_detections(client, sample_camera):
    from app.database.session import SessionLocal
    from app.models import Detection
    db = SessionLocal()
    db.add(Detection(camera_id=sample_camera["id"], object_class="person", confidence=0.9,
                     track_id=3, bbox={"x1": 1, "y1": 2, "x2": 10, "y2": 20}))
    db.commit()
    db.close()

    res = client.get("/api/analytics/detections", params={"object_class": "person"})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert all(d["object_class"] == "person" for d in body["items"])


def test_settings_endpoint(client):
    res = client.put("/api/settings/motion_sensitivity", json={"value": "30"})
    assert res.status_code == 200
    res = client.get("/api/settings")
    keys = [s["key"] for s in res.json()]
    assert "motion_sensitivity" in keys


def test_detection_start_stop_validation(client):
    res = client.post("/api/cameras/detection/start", json={"camera_id": 999999})
    assert res.status_code == 404
