#!/usr/bin/env python3
"""Test 6 pages using Chrome headless with CDP for console errors."""
import subprocess
import json
import time
import os
import urllib.request
import websocket
from pathlib import Path

PAGES = [
    ("capacity-planning", "http://localhost:3000/capacity-planning"),
    ("cost-management", "http://localhost:3000/cost-management"),
    ("disaster-recovery", "http://localhost:3000/disaster-recovery"),
    ("integrations", "http://localhost:3000/integrations"),
    ("roles-crud", "http://localhost:3000/roles-crud"),
    ("permissions-crud", "http://localhost:3000/permissions-crud"),
]

SCREENSHOT_DIR = Path("/Users/ahmedhassan/apex-os-business-platform/web/screenshots/final-6pages-chrome")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Launch Chrome with remote debugging
proc = subprocess.Popen([
    CHROME,
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--remote-debugging-port=9222",
    "--window-size=1920,1080",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(3)

try:
    # Get WebSocket URL
    tabs = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
    ws_url = tabs[0]["webSocketDebuggerUrl"]
    ws = websocket.create_connection(ws_url)
    msg_id = 1

    def send_cdp(method, params=None):
        nonlocal msg_id
        msg = {"id": msg_id, "method": method}
        if params:
            msg["params"] = params
        ws.send(json.dumps(msg))
        result = json.loads(ws.recv())
        msg_id += 1
        return result

    send_cdp("Page.enable")
    send_cdp("Runtime.enable")

    results = []

    for name, url in PAGES:
        print(f"\n=== Testing {name} ===")
        
        # Navigate
        send_cdp("Page.navigate", {"url": url})
        time.sleep(4)

        # Get console errors via Runtime
        console_result = send_cdp("Runtime.evaluate", {
            "expression": """
            (function() {
                const errors = [];
                // Check if page has content
                const body = document.body;
                const text = body ? body.innerText : '';
                const buttons = document.querySelectorAll('button');
                const bgColor = window.getComputedStyle(body).backgroundColor;
                return {
                    textLength: text.length,
                    buttonCount: buttons.length,
                    bgColor: bgColor,
                    title: document.title,
                    url: window.location.href
                };
            })()
            """,
            "returnByValue": True
        })
        
        page_info = console_result.get("result", {}).get("result", {}).get("value", {})
        print(f"  URL: {page_info.get('url', 'N/A')}")
        print(f"  Title: {page_info.get('title', 'N/A')}")
        print(f"  Text length: {page_info.get('textLength', 0)}")
        print(f"  Buttons: {page_info.get('buttonCount', 0)}")
        print(f"  BG color: {page_info.get('bgColor', 'N/A')}")

        # Screenshot
        ss_result = send_cdp("Page.captureScreenshot", {
            "format": "png",
            "captureBeyondViewport": True
        })
        
        if "result" in ss_result and "data" in ss_result["result"]:
            import base64
            img_data = base64.b64decode(ss_result["result"]["data"])
            ss_path = SCREENSHOT_DIR / f"{name}.png"
            with open(ss_path, "wb") as f:
                f.write(img_data)
            ss_size = len(img_data)
            print(f"  Screenshot: {ss_path} ({ss_size} bytes)")
        else:
            ss_size = 0
            print(f"  Screenshot: FAILED")

        # Check dark theme
        bg = page_info.get("bgColor", "")
        is_dark = False
        if bg and bg != "rgba(0, 0, 0, 0)":
            import re
            m = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', bg)
            if m:
                r, g, b_val = int(m.group(1)), int(m.group(2)), int(m.group(3))
                is_dark = r < 100 and g < 100 and b_val < 100

        results.append({
            "page": name,
            "url": url,
            "screenshot_size": ss_size,
            "dark_theme": is_dark,
            "bg_color": bg,
            "data_loaded": page_info.get("textLength", 0) > 200,
            "content_length": page_info.get("textLength", 0),
            "buttons": page_info.get("buttonCount", 0),
            "title": page_info.get("title", ""),
        })

    ws.close()

    # Write results
    with open(SCREENSHOT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n=== Results saved to {SCREENSHOT_DIR / 'results.json'} ===")
    for r in results:
        print(f"\n{r['page']}:")
        print(f"  Screenshot: {r['screenshot_size']} bytes")
        print(f"  Dark theme: {r['dark_theme']}")
        print(f"  Data loaded: {r['data_loaded']} ({r['content_length']} chars)")
        print(f"  Buttons: {r['buttons']}")

finally:
    proc.terminate()
    proc.wait()
