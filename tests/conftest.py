"""Pytest configuration for APEX-OS Business Platform tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-testing-only")

# Make the source tree importable regardless of how pytest was invoked, so the
# suite behaves identically locally and in CI.
#
# `src` is needed for `apex_os_bp.*` imports. A handful of tests also import
# apex_os_bp's subpackages under their bare names (`from bigdata.ingestion
# import DataIngester`), which only resolve if `src/apex_os_bp` is on the path
# too. That directory contains a `logging` package, so it is APPENDED rather
# than prepended - putting it first would shadow the stdlib `logging` module
# and break any import chain that touches it (observed as
# "cannot import name 'LogRecord' from 'logging'").
_ROOT = Path(__file__).resolve().parents[1]
for _path in (_ROOT, _ROOT / "src", _ROOT / "web" / "backend"):
    _entry = str(_path)
    if _path.is_dir() and _entry not in sys.path:
        sys.path.insert(0, _entry)
_SRC_PKG = _ROOT / "src" / "apex_os_bp"
if _SRC_PKG.is_dir() and str(_SRC_PKG) not in sys.path:
    sys.path.append(str(_SRC_PKG))

import pytest
from fastapi.testclient import TestClient

from apex_os_bp.api.app import create_api_app
from apex_os_bp.core.config import Config


# ---------------------------------------------------------------------------
# Global state baseline
# ---------------------------------------------------------------------------
# web/backend keeps its in-memory data in module-level dicts (main.stores +
# ~40 routes/*.py state dicts). Tests that DELETE seeded rows would otherwise
# poison every later suite in the same process. Capture the pristine state
# HERE, at conftest import time - guaranteed to precede every test - and let
# the autouse fixture below restore it around each test.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _route_state import snapshot as _route_state_snapshot  # noqa: E402

_route_state_snapshot()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create a test FastAPI app with relaxed rate limits."""
    config = Config()
    config.set("api.rate_limit.max_requests", 1000)
    config.set("api.rate_limit.window_seconds", 60)
    return create_api_app(config)


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers by logging in as admin."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    if response.status_code == 200:
        token = response.json().get("access_token", "")
        return {"Authorization": f"Bearer {token}"}
    return {}


# ---------------------------------------------------------------------------
# Skip tests that require a running server (e2e, performance, UI)
# ---------------------------------------------------------------------------

_SERVER_DEPENDENT_PATTERNS = ("test_ui_ux.py", "test_performance_all.py")


def pytest_collection_modifyitems(config, items):
    """Skip tests that need a running server."""
    skip_server = pytest.mark.skip(reason="requires running server")
    for item in items:
        if any(pat in str(item.fspath) for pat in _SERVER_DEPENDENT_PATTERNS):
            item.add_marker(skip_server)


@pytest.fixture(autouse=True)
def _reseed_web_backend_store(request):
    """Restore the web/backend synthetic data store around every test.

    web/backend state = main.stores + ~40 routes/*.py module-level dicts.
    delete-heavy suites (test_all_modules) permanently remove seeded rows for
    every later test in the process. _route_state.restore() writes the
    immutable baseline (captured at conftest import) back around each test,
    making every suite independent of execution order.
    """
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    try:
        from _route_state import ensure_bare_baseline, restore

        # First call: capture the bare-name route universe ('routes.*', the
        # instances main.py binds to) BEFORE any test has mutated it.
        ensure_bare_baseline()

        restore()
        yield
        restore()
    except ImportError:
        yield

