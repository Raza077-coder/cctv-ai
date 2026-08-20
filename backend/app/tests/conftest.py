"""Pytest fixtures: test database, FastAPI TestClient."""
import os

os.environ["DATABASE_URL"] = "postgresql+psycopg2://cctv:CCTV_secret_change_me@localhost:5432/cctv_ai_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["YOLO_MODEL"] = "yolov8n.pt"
os.environ["ENABLE_ANPR"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database.session import Base, engine as prod_engine
from app.main import app

TEST_DB = "postgresql+psycopg2://cctv:CCTV_secret_change_me@localhost:5432/cctv_ai_test"


def _create_test_db() -> None:
    admin = create_engine("postgresql+psycopg2://cctv:CCTV_secret_change_me@localhost:5432/postgres")
    with admin.connect() as conn:
        conn.execute(text("COMMIT"))
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'cctv_ai_test'")
        ).fetchone()
        if not exists:
            conn.execute(text("CREATE DATABASE cctv_ai_test"))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def test_db_setup():
    _create_test_db()
    # point prod engine at test DB by rebuilding tables there
    engine = create_engine(TEST_DB)
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


@pytest.fixture()
def client():
    from app.database import session as db_session
    test_engine = create_engine(TEST_DB)
    db_session.engine = test_engine
    # SessionLocal captured the original engine at import time — rebuild it bound to the test engine
    db_session.SessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    with TestClient(app) as c:
        yield c
    # restore prod engine + session factory
    db_session.engine = prod_engine
    db_session.SessionLocal = sessionmaker(bind=prod_engine, autocommit=False, autoflush=False)


@pytest.fixture()
def sample_camera(client) -> dict:
    res = client.post("/api/cameras", json={
        "name": "Test Cam",
        "source_type": "file",
        "source_url": "/tmp/nonexistent.mp4",
        "location": "lab",
    })
    assert res.status_code == 201, res.text
    return res.json()
