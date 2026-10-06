"""Mount the built React SPA (web/frontend/dist) onto the backend app.

Used by tests/test_crud_accessibility.py to serve the real SPA + API
in-process during CI so browser tests render actual DOM. Also runnable
standalone: ``python tests/_ci_spa_server.py`` serves on port 8000.
"""
import os
import socket

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "web", "backend")
DIST = os.path.join(ROOT, "web", "frontend", "dist")


def build_spa_asgi(backend_app):
    """Return an ASGI app that serves the built SPA and passes everything
    else through to ``backend_app`` UNMUTATED.

    Mutating the shared ``main.app`` singleton is not an option: adding a
    catch-all SPA fallback route there shadows API 404s (e.g. GET
    /api/nonexistent would return index.html with 200), breaking every other
    test file's expectations in the same pytest session. Instead the SPA is
    layered UNDER a dispatcher: /api/* (and anything SPA files don't claim)
    goes to the real backend untouched; only document requests hit dist/.
    """
    import mimetypes
    from pathlib import Path

    dist = Path(DIST)
    index_html = dist / "index.html"
    dist_root = str(dist.resolve())

    async def send_file(file_path, send, status=200):
        import mimetypes as _m
        content_type = _m.guess_type(str(file_path))[0] or "application/octet-stream"
        with open(file_path, "rb") as f:
            body = f.read()
        headers = [
            (b"content-type", content_type.encode()),
            (b"content-length", str(len(body)).encode()),
        ]
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def asgi(scope, receive, send):
        if scope["type"] != "http":
            await backend_app(scope, receive, send)
            return
        path = scope["path"].lstrip("/")
        # API and all documented backend endpoints go straight to the backend.
        if path == "api" or path.startswith("api/") or path in ("openapi.json", "docs", "redoc", "docs/oauth2-redirect"):
            await backend_app(scope, receive, send)
            return
        candidate = (dist / path).resolve() if path else None
        if (
            path
            and str(candidate).startswith(dist_root)
            and candidate.is_file()
        ):
            await send_file(candidate, send)
            return
        # Everything else (/, /accounting, ...) is a client-side SPA route
        # served from the built index.html. 404s by design only exist under
        # /api, which never reaches this branch.
        await send_file(index_html, send)

    return asgi


class SpaServer:
    """Wraps the uvicorn Server + its thread; enables orderly shutdown.

    Why this exists: the raw ``Server.run()`` call inside a daemon thread
    starts an event loop via ``asyncio.run()``. Setting ``should_exit`` alone
    stops serving but leaves the loop object in a 'running' state until the
    thread actually exits, which poisons pytest-asyncio 1.4 for every test
    file that runs afterwards ('' '' RuntimeError: Runner.run() cannot be
    called from a running event loop). Joining the thread at teardown closes
    the loop cleanly.
    """

    def __init__(self, server, thread):
        self._server = server
        self._thread = thread

    @property
    def started(self) -> bool:
        return self._server.started

    @property
    def should_exit(self) -> bool:
        return self._server.should_exit

    @should_exit.setter
    def should_exit(self, value: bool) -> None:
        self._server.should_exit = value
        if value:
            # Block until the loop is actually gone (small grace period; a
            # wedged server must not hang the whole suite forever).
            self._thread.join(timeout=10)

    def stop(self) -> None:
        self.should_exit = True


def serve_spa_with_backend(backend_app, host="127.0.0.1", port=None):
    """Start an in-process uvicorn server; return (base_url, SpaServer)."""
    import threading
    import time

    import uvicorn

    if port is None:
        with socket.socket() as s:
            s.bind((host, 0))
            port = s.getsockname()[1]
        # Small retry loop in case another process grabs the port in between:
        for attempt in range(5):
            asgi = build_spa_asgi(backend_app)
            config = uvicorn.Config(asgi, host=host, port=port, log_level="warning")
            server = uvicorn.Server(config)
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            deadline = time.time() + 15
            while not server.started and not server.should_exit and time.time() < deadline:
                time.sleep(0.05)
            if server.started:
                return f"http://{host}:{port}", SpaServer(server, thread)
            thread.join(timeout=5)
            if not server.should_exit:
                # Bind failed for another reason (unexpected) - stop retrying.
                break
            # Port was grabbed between probe and bind; pick another.
            with socket.socket() as s:
                s.bind((host, 0))
                port = s.getsockname()[1]
        raise RuntimeError("In-process uvicorn server did not start within 30s")

    asgi = build_spa_asgi(backend_app)
    config = uvicorn.Config(asgi, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 30
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("In-process uvicorn server did not start within 30s")
    return f"http://{host}:{port}", SpaServer(server, thread)


if __name__ == "__main__":
    import sys  # noqa: E402

    if BACKEND not in sys.path:
        sys.path.insert(0, BACKEND)
    os.chdir(BACKEND)
    from main import app  # noqa: E402

    base_url, server = serve_spa_with_backend(app, port=8000)
    print(f"SPA + API server on {base_url}", flush=True)
    try:
        import threading  # noqa: E402  (keeps non-daemon reference alive)

        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.should_exit = True
