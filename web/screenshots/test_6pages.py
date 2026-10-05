#!/usr/bin/env python3
"""Test 6 pages with Chrome headless screenshots."""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PAGES = [
    "opportunities-crud",
    "campaigns-crud",
    "alerts-crud",
    "user-management",
    "lead-management",
    "report-management",
]

BASE_URL = "http://localhost:3000"
SCREENSHOT_DIR = Path("/Users/ahmedhassan/apex-os-business-platform/web/screenshots/test-6pages-final")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

results = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: console_errors.append(str(err)))

    for page_name in PAGES:
        print(f"\n--- Testing: {page_name} ---")
        console_errors.clear()
        result = {
            "page": page_name,
            "url": f"{BASE_URL}/{page_name}",
            "screenshot": str(SCREENSHOT_DIR / f"{page_name}.png"),
            "dark_theme": False,
            "data_loaded": False,
            "buttons": {},
            "console_errors": [],
            "issues": [],
        }

        try:
            page.goto(f"{BASE_URL}/{page_name}", wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # Screenshot
            page.screenshot(path=str(SCREENSHOT_DIR / f"{page_name}.png"), full_page=True)
            print(f"  Screenshot saved")

            # Check dark theme
            bg_color = page.evaluate("getComputedStyle(document.body).backgroundColor")
            is_dark = "rgb(17, 24, 39)" in bg_color or "rgb(31, 41, 55)" in bg_color or "rgb(0, 0, 0)" in bg_color or int(bg_color.split(",")[0].strip("rgb(")) < 50
            result["dark_theme"] = is_dark
            print(f"  Dark theme: {is_dark} (bg: {bg_color})")

            # Check data loaded - look for table rows or content
            rows = page.locator("tbody tr").count()
            has_content = page.locator("table, .grid, .list, [role='table']").count() > 0
            result["data_loaded"] = rows > 0 or has_content
            print(f"  Data loaded: {result['data_loaded']} (rows: {rows})")

            # Check buttons
            buttons = page.locator("button, [role='button']")
            btn_count = buttons.count()
            btn_texts = []
            for i in range(min(btn_count, 20)):
                try:
                    txt = buttons.nth(i).inner_text().strip()
                    if txt:
                        btn_texts.append(txt)
                except:
                    pass
            result["buttons"] = {
                "count": btn_count,
                "texts": btn_texts[:10],
            }
            print(f"  Buttons: {btn_count} found")

            # Check for specific action buttons
            for action in ["Create", "Add", "New", "Edit", "Delete", "Search", "Export"]:
                found = page.locator(f"button:has-text('{action}'), [role='button']:has-text('{action}')").count()
                result["buttons"][action.lower()] = found > 0

            # Console errors
            result["console_errors"] = console_errors[:10]
            if console_errors:
                print(f"  Console errors: {len(console_errors)}")

            # Check for error messages on page
            error_msgs = page.locator(".error, .alert-error, [role='alert']").count()
            if error_msgs > 0:
                result["issues"].append(f"Found {error_msgs} error elements on page")

        except Exception as e:
            result["issues"].append(str(e))
            print(f"  ERROR: {e}")

        results.append(result)

    browser.close()

# Save results
results_file = SCREENSHOT_DIR / "results.json"
with open(results_file, "w") as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*60}")
print(f"Results saved to: {results_file}")
print(f"{'='*60}")
for r in results:
    status = "PASS" if not r["issues"] and r["dark_theme"] else "ISSUES"
    print(f"  {r['page']}: {status} | dark={r['dark_theme']} data={r['data_loaded']} buttons={r['buttons']['count']} errors={len(r['console_errors'])}")
