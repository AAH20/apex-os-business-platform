"""Pytest configuration for APEX-OS Business Platform tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apex_os_bp.api.app import create_api_app
from apex_os_bp.core.config import Config


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
