#!/usr/bin/env bash
# Quick end-to-end test: starts backend, registers a sample video camera,
# runs detection for a few seconds, prints results, then stops.
set -euo pipefail

BASE="${1:-http://localhost:8000}"
VIDEO="${2:-storage/intel_sample.mp4}"

echo "==> Health check"
curl -sf "$BASE/api/health" | python3 -m json.tool

echo "==> Registering sample video camera"
CAM_ID=$(curl -sf -X POST "$BASE/api/cameras" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"E2E Test\",\"source_type\":\"file\",\"source_url\":\"$VIDEO\"}" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "    camera id: $CAM_ID"

echo "==> Starting detection"
curl -sf -X POST "$BASE/api/cameras/detection/start" \
  -H "Content-Type: application/json" \
  -d "{\"camera_id\":$CAM_ID,\"process_fps\":10}" | python3 -m json.tool

echo "==> Waiting 30s for processing..."
sleep 30

echo "==> Events"
curl -sf "$BASE/api/events?camera_id=$CAM_ID&limit=5" | python3 -m json.tool
echo "==> Detections"
curl -sf "$BASE/api/analytics/detections?camera_id=$CAM_ID&limit=5" | python3 -m json.tool
echo "==> Summary"
curl -sf "$BASE/api/analytics/summary" | python3 -m json.tool

echo "==> Stopping detection"
curl -sf -X POST "$BASE/api/cameras/detection/stop" \
  -H "Content-Type: application/json" \
  -d "{\"camera_id\":$CAM_ID}" | python3 -m json.tool

echo "E2E test complete."
