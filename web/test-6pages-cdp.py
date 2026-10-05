#!/usr/bin/env python3
"""Test 6 pages using Chrome headless with CDP for console errors."""
import json
import time
import urllib.request
import websocket
import subprocess
import base64
import re
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

proc = subprocess.Popen([
    CHROME,
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    "--window-size=1920,1080",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(3)
msg_id = 1

try:
    tabs = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
    ws_url = tabs[0]["webSocketDebuggerUrl"]
    ws = websocket.create_connection(ws_url)

    def send_cdp(method, params=None):
        global msg_id
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
        print(f"=== {name} ===")
        send_cdp("Page.navigate", {"url": url})
        time.sleep(4)

        r = send_cdp("Runtime.evaluate", {
            "expression": 'JSON.stringify({textLength: document.body.innerText.length, buttonCount: document.querySelectorAll("button").length, bgColor: window.getComputedStyle(document.body).backgroundColor, title: document.title, url: window.location.href})',
            "returnByValue": True
        })
        info = json.loads(r["result"]["result"]["value"])
        print(f"  text={info['textLength']}, buttons={info['buttonCount']}, bg={info['bgColor']}")

        ss = send_cdp("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
        img = None
        if "result" in ss and "data" in ss["result"]:
            img = base64.b64decode(ss["result"]["data"])
            (SCREENSHOT_DIR / f"{name}.png").write_bytes(img)
            print(f"  screenshot: {len(img)} bytes")

        bg = info["bgColor"]
        m = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", bg)
        is_dark = m and int(m.group(1)) < 100 and int(m.group(2)) < 100 and int(m.group(3)) < 100

        results.append({
            "page": name,
            "screenshot_size": len(img) if img else 0,
            "dark_theme": is_dark,
            "bg_color": bg,
            "data_loaded": info["textLength"] > 200,
            "content_length": info["textLength"],
            "buttons": info["buttonCount"],
        })

    ws.close()
    (SCREENSHOT_DIR / "results.json").write_text(json.dumps(results, indent=2))
    print("Done. Results saved.")
    for r in results:
        print(f"{r['page']}: size={r['screenshot_size']}, dark={r['dark_theme']}, data={r['data_loaded']}, buttons={r['buttons']}")

finally:
    proc.terminate()
    proc.wait()
