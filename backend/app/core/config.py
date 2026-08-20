"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_ROOT = BACKEND_DIR.parent  # cctv-ai/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "CCTV AI"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api"

    # --- Database / Redis ---
    database_url: str = (
        "postgresql+psycopg2://cctv:CCTV_secret_change_me@localhost:5432/cctv_ai"
    )
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change_me_generate_a_random_hex_string"

    # --- AI models ---
    yolo_model: str = "yolov8n.pt"
    detection_confidence: float = 0.35
    process_fps: int = 15

    # --- Feature toggles ---
    enable_face_recognition: bool = False
    enable_anpr: bool = True
    enable_motion_detection: bool = True

    # --- Storage ---
    storage_root: str = str(PROJECT_ROOT / "storage")

    # --- Security ---
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_paths(self) -> dict[str, Path]:
        root = Path(self.storage_root)
        return {
            "snapshots": root / "snapshots",
            "recordings": root / "recordings",
            "plates": root / "plates",
            "faces": root / "faces",
        }

    def ensure_storage(self) -> None:
        for p in self.storage_paths.values():
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
