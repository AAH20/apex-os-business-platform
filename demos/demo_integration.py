"""
APEX-OS Business Platform - Integration Demos
Demonstrates: API routes, webhooks, data transformation, rate limiting, workflow execution.
Run: python demos/demo_integration.py
"""
import json, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request


def demo_api_route():
    print("\n=== Demo 1: Create API Route ===")
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api/v1/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "service": "apex-os"}).encode())
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, *a, **k): pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r = urlopen(f"http://127.0.0.1:{port}/api/v1/health")
        print(f"  GET /api/v1/health -> {r.status}: {json.loads(r.read())}")
    finally:
        srv.shutdown()
    print("  ✓ API route created and served response")


def demo_webhook():
    print("\n=== Demo 2: Send Webhook ===")
    received = {}
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            received["payload"] = json.loads(self.rfile.read(n))
            received["event"] = self.headers.get("X-Event-Type", "unknown")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"received": true}')
        def log_message(self, *a, **k): pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        body = json.dumps({"event": "order.created", "order_id": "ORD-123", "total": 99.99}).encode()
        req = Request(f"http://127.0.0.1:{port}/webhook", data=body,
                      headers={"Content-Type": "application/json", "X-Event-Type": "order.created"})
        r = urlopen(req)
        print(f"  Webhook sent -> {r.status}: {r.read().decode()}")
        print(f"  Server received: event={received['event']}, payload={received['payload']}")
    finally:
        srv.shutdown()
    print("  ✓ Webhook delivered and acknowledged")


def demo_transform():
    print("\n=== Demo 3: Transform Data ===")
    raw = [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "role": "admin"},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "role": "user"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "role": "user"},
    ]
    result = [
        {"user_id": r["id"], "display_name": r["name"].upper(),
         "contact": r["email"].lower(), "is_admin": r["role"] == "admin",
         "metadata": {"source": "demo", "version": 1}}
        for r in raw
    ]
    print(f"  Input: {len(raw)} records")
    print(f"  Output: {json.dumps(result, indent=4)}")
    print("  ✓ Data transformed successfully")


def demo_rate_limit():
    print("\n=== Demo 4: Rate Limit Check ===")
    class RateLimiter:
        def __init__(self, max_requests=3, window_sec=10):
            self.max_requests, self.window_sec, self.requests = max_requests, window_sec, []
        def is_allowed(self):
            now = time.time()
            self.requests = [t for t in self.requests if now - t < self.window_sec]
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False
    limiter = RateLimiter(max_requests=3, window_sec=5)
    for i in range(5):
        ok = limiter.is_allowed()
        print(f"  req{i+1}: {'ALLOWED' if ok else 'BLOCKED'}")
        time.sleep(0.05)
    print("  ✓ Rate limiter blocked excess requests")


def demo_workflow():
    print("\n=== Demo 5: Workflow Execution ===")
    class Workflow:
        def __init__(self, name):
            self.name, self.steps = name, []
        def add_step(self, name, action):
            self.steps.append((name, action))
            return self
        def run(self, context=None):
            ctx = context or {}
            print(f"  Starting workflow: {self.name}")
            for name, action in self.steps:
                ctx[name] = action(ctx)
                print(f"    Step '{name}' -> {ctx[name]}")
            print(f"  Workflow '{self.name}' completed with {len(self.steps)} steps")
            return ctx
    wf = (Workflow("order-processing")
          .add_step("validate", lambda c: {"valid": True, "order_id": "ORD-456"})
          .add_step("payment", lambda c: {"payment_id": "PAY-789", "status": "captured", "amount": 149.99})
          .add_step("notify", lambda c: {"email_sent": True, "to": "customer@example.com"}))
    ctx = wf.run()
    print(f"  Final context keys: {list(ctx.keys())}")
    print("  ✓ Workflow executed all steps")


if __name__ == "__main__":
    print("=" * 60)
    print("  APEX-OS Business Platform - Integration Demos")
    print("=" * 60)
    demo_api_route()
    demo_webhook()
    demo_transform()
    demo_rate_limit()
    demo_workflow()
    print("\n" + "=" * 60)
    print("  All 5 demos completed successfully ✓")
    print("=" * 60)
