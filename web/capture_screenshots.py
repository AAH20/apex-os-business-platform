#!/usr/bin/env python3
"""Capture screenshots of all pages using Chrome DevTools Protocol."""
import json
import base64
import time
import urllib.request
import websocket
import sys
from pathlib import Path

SCREENSHOTS_DIR = Path("/Users/ahmedhassan/apex-os-business-platform/web/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("dashboard", "http://localhost:3000/"),
    ("accounting", "http://localhost:3000/accounting"),
    ("crm", "http://localhost:3000/crm"),
    ("analytics", "http://localhost:3000/analytics"),
    ("agent-reach", "http://localhost:3000/agent-reach"),
    ("bigdata", "http://localhost:3000/bigdata"),
    ("datascience", "http://localhost:3000/datascience"),
    ("continuous-bi", "http://localhost:3000/continuous-bi"),
]

def capture_all():
    # Get WebSocket URL
    response = urllib.request.urlopen("http://localhost:9222/json")
    tabs = json.loads(response.read())
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
    
    for name, url in PAGES:
        send_cdp("Page.navigate", {"url": url})
        time.sleep(4)  # Wait for page to fully render
        
        result = send_cdp("Page.captureScreenshot", {
            "format": "png",
            "quality": 90,
            "captureBeyondViewport": True
        })
        
        if "result" in result and "data" in result["result"]:
            img_data = base64.b64decode(result["result"]["data"])
            filepath = SCREENSHOTS_DIR / f"{name}.png"
            with open(filepath, "wb") as f:
                f.write(img_data)
            print(f"✅ {name}.png ({len(img_data)//1024}KB)")
        else:
            print(f"❌ {name} failed")
    
    ws.close()
    print(f"\n✅ All screenshots saved to {SCREENSHOTS_DIR}")

if __name__ == "__main__":
    capture_all()
