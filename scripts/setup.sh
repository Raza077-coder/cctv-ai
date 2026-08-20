#!/usr/bin/env bash
# Setup script: installs system + python deps and prepares local services.
set -euo pipefail

echo "==> [1/4] System packages (OpenCV runtime, ffmpeg)"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    libgl1 libglib2.0-0 ffmpeg postgresql postgresql-contrib redis-server
fi

echo "==> [2/4] Python dependencies"
pip install --no-cache-dir -r backend/requirements.txt

echo "==> [3/4] PostgreSQL database + user"
if command -v pg_isready >/dev/null 2>&1; then
  service postgresql start || true
  su postgres -c "psql -c \"CREATE USER cctv WITH PASSWORD 'CCTV_secret_change_me' CREATEDB;\"" 2>/dev/null || true
  su postgres -c "psql -c 'CREATE DATABASE cctv_ai OWNER cctv;'" 2>/dev/null || true
fi

echo "==> [4/4] Frontend dependencies"
(cd frontend && npm install --no-audit --no-fund)

echo "Setup complete. Copy .env.example to .env and adjust values."
