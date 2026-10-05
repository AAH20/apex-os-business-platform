#!/usr/bin/env python3
"""Capture screenshots of 6 pages using Chrome headless."""
import subprocess
import os
import json
import time

PAGES = [
    ("capacity-planning", "http://localhost:3000/capacity-planning"),
    ("cost-management", "http://localhost:3000/cost-management"),
    ("disaster-recovery", "http://localhost:3000/disaster-recovery"),
    ("integrations", "http://localhost:3000/integrations"),
    ("roles-crud", "http://localhost:3000/roles-crud"),
    ("permissions-crud", "http://localhost:3000/permissions-crud"),
]

SCREENSHOT_DIR = "/Users/ahmedhassan/apex-os-business-platform/web/screenshots/retest-authfix"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

results = []
for name, url in PAGES:
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    cmd = [
        CHROME,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
        f"--screenshot={screenshot_path}",
        "--virtual-time-budget=5000",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        exists = os.path.exists(screenshot_path)
        size = os.path.getsize(screenshot_path) if exists else 0
        results.append({
            "page": name,
            "url": url,
            "screenshot": screenshot_path if exists else None,
            "size_bytes": size,
            "success": exists and size > 1000,
            "error": result.stderr[:500] if result.returncode != 0 and not exists else None
        })
        print(f"{name}: {'OK' if exists and size > 1000 else 'FAIL'} ({size} bytes)")
    except Exception as e:
        results.append({"page": name, "url": url, "success": False, "error": str(e)})
        print(f"{name}: ERROR - {e}")

with open(os.path.join(SCREENSHOT_DIR, "screenshot-results.json"), "w") as f:
    json.dump(results, f, indent=2)

print(f"\nScreenshots saved to {SCREENSHOT_DIR}")
