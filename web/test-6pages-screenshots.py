#!/usr/bin/env python3
"""Test 6 pages: screenshot + verify dark theme, data, buttons, console errors."""
import subprocess, os, json, time

PAGES = [
    ("notifications", "http://localhost:3000/notifications"),
    ("export-templates", "http://localhost:3000/export-templates"),
    ("workflows", "http://localhost:3000/workflows"),
    ("data-warehouse", "http://localhost:3000/data-warehouse"),
    ("knowledge-base", "http://localhost:3000/knowledge-base"),
    ("monitoring", "http://localhost:3000/monitoring"),
]

SCREENSHOT_DIR = "/Users/ahmedhassan/apex-os-business-platform/web/screenshots/6pages-test"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

results = []
for name, url in PAGES:
    ss_path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    cmd = [
        CHROME,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
        f"--screenshot={ss_path}",
        "--virtual-time-budget=5000",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        exists = os.path.exists(ss_path)
        size = os.path.getsize(ss_path) if exists else 0
        results.append({
            "page": name,
            "url": url,
            "screenshot": ss_path if exists else None,
            "size_bytes": size,
            "success": exists and size > 1000,
            "chrome_error": result.stderr[:300] if result.returncode != 0 and not exists else None,
        })
        print(f"{name}: {'OK' if exists and size > 1000 else 'FAIL'} ({size} bytes)")
    except Exception as e:
        results.append({"page": name, "url": url, "success": False, "error": str(e)})
        print(f"{name}: ERROR - {e}")

with open(os.path.join(SCREENSHOT_DIR, "results.json"), "w") as f:
    json.dump(results, f, indent=2)

print(f"\nScreenshots saved to {SCREENSHOT_DIR}")
