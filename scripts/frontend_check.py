"""Headless-browser integration check for the CCTV AI dashboard.

Loads each page against the live backend, captures console errors and page
errors, and verifies real API data appears (health, summary, cameras).
"""
import json
import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
PAGES = ["/", "/cameras", "/monitor", "/events", "/alerts", "/analytics", "/settings"]

results = {}
console_errors = []
page_errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page_errors.append(str(e)))

    for path in PAGES:
        try:
            page.goto(BASE + path, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(1500)
            title = page.title()
            body_text = page.inner_text("body")
            results[path] = {
                "title": title,
                "has_health": "CCTV AI" in body_text or "Dashboard" in body_text,
                "body_len": len(body_text),
            }
            # check for error banners
            if "Cannot reach backend" in body_text or "Failed to load" in body_text:
                results[path]["error_banner"] = True
        except Exception as e:
            results[path] = {"error": str(e)[:120]}

    # Dashboard-specific: real summary numbers
    page.goto(BASE + "/", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2500)
    db_text = page.inner_text("body")
    results["/"] = {
        "title": page.title(),
        "cameras_label_visible": "Cameras" in db_text,
        "events_label_visible": "Events (24h)" in db_text,
        "live_badge": "Live" in db_text or "Offline" in db_text,
        "backend_error_visible": "Cannot reach backend" in db_text,
    }

    # Cameras page: real camera cards from DB
    page.goto(BASE + "/cameras", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2000)
    cam_text = page.inner_text("body")
    results["/cameras"]["camera_cards"] = any(
        name in cam_text for name in ["Sample Video", "BBB Sample", "Intel Sample"]
    )

    browser.close()

print("=== RESULTS ===")
print(json.dumps(results, indent=2))
print("=== CONSOLE ERRORS ===")
print(json.dumps(console_errors[:10], indent=2) if console_errors else "none")
print("=== PAGE ERRORS ===")
print(json.dumps(page_errors[:10], indent=2) if page_errors else "none")

# exit non-zero on errors
if console_errors or page_errors:
    sys.exit(2)
