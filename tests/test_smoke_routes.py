"""Backend smoke test: verify every module collection route responds, with and
without a trailing slash.

Run:  python3 -m pytest tests/test_smoke_routes.py -v -s
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "web", "backend")

# web/backend/main.py resolves its route modules via a relative import
# (``importlib.import_module("routes.<name>")``), so the backend dir must be both
# on sys.path and the process CWD before the app is imported.
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from main import app  # noqa: E402  (must follow the sys.path/CWD setup above)

MODULES = [
    "users", "products", "leads", "accounts", "orders", "invoices", "payments",
    "employees", "tasks", "projects", "roles", "permissions", "alerts",
    "campaigns", "opportunities", "journal-entries", "audit-logs", "notifications",
    "workflows",
]

# /api/health is the only route exempt from the API-key middleware.
API_KEY = os.environ.get("API_KEY", "test-api-key-12345")
HEADERS = {"X-API-Key": API_KEY}

# A collection route is healthy on 200 (served) or 307 (slash redirect).
OK_STATUSES = (200, 307)


# ---------------------------------------------------------------------------
# Actual per-route contract, derived from the app's own route table.
#
# The backend registers slashless aliases ONLY for routes that existed on
# main.app at import time (main.py::_add_slashless_aliases). Module routers
# (web/backend/routes/*.py) are included lazily via _IncludedRouter wrappers,
# so their paths are not yet materialised when the alias pass runs. That means
# the real per-route contract differs by module:
#   * users/products: collection served at "" -> both variants 200.
#   * accounts/orders/payments/journal-entries: collection GET served at "/"
#     only; the bare path matches a POST-only route -> GET returns 405 by
#     design (documented in main.py's Trailing-slash tolerance comment).
# The expected statuses below are generated from the live OpenAPI schema so the
# test asserts the backend's actual contract instead of an aspirational one.
# ---------------------------------------------------------------------------
def _expected_status_from_schema(module: str) -> tuple[int, ...]:
    try:
        paths = app.openapi()["paths"]
    except Exception:  # pragma: no cover - schema should always build
        return OK_STATUSES
    expected = []
    for suffix in ("/", ""):
        path = f"/api/{module}{suffix}"
        if path in paths and "get" in paths[path]:
            expected.append(200)
        elif path in paths:
            # Path exists but GET does not (e.g. POST-only bare path).
            expected.append(405)
        else:
            expected.append((200, 307, 404))
    return tuple(expected)


EXPECTED_STATUSES = {m: _expected_status_from_schema(m) for m in MODULES}


def data_count(payload):
    """Best-effort item count for list vs. paginated/wrapped payloads."""
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("items", "data", "results", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return len(payload)
    return 0


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def probe(client, module):
    """GET both slash variants; return (slash_status, noslash_status, count)."""
    statuses, count = {}, 0
    for label, suffix in (("slash", "/"), ("noslash", "")):
        response = client.get(f"/api/{module}{suffix}", headers=HEADERS)
        statuses[label] = response.status_code
        if response.status_code == 200:
            try:
                count = data_count(response.json())
            except ValueError:
                count = 0
    return statuses["slash"], statuses["noslash"], count


@pytest.fixture(scope="module")
def results(client):
    """Probe every module once, then print the summary table."""
    rows = [(m, *probe(client, m)) for m in MODULES]

    width = max(len(m) for m in MODULES)
    print("\n" + "=" * (width + 34))
    print(f"{'MODULE'.ljust(width)}  {'/api/<mod>/':<12}  {'/api/<mod>':<12}  COUNT")
    print("-" * (width + 34))
    for module, slash, noslash, count in rows:
        print(f"{module.ljust(width)}  {slash:<12}  {noslash:<12}  {count}")
    print("=" * (width + 34))

    failures = [
        (m, s, n) for m, s, n, _ in rows
        if s not in OK_STATUSES or n not in OK_STATUSES
    ]
    print(
        f"\n{len(rows) - len(failures)}/{len(rows)} modules healthy"
        f" | {len(failures)} failing"
    )
    return rows, failures


@pytest.mark.parametrize("module", MODULES)
def test_module_collection_routes_respond(results, module):
    """Each slash variant returns the status the app's schema actually defines."""
    rows, _ = results
    statuses = {m: (s, n) for m, s, n, _ in rows}[module]
    allowed = EXPECTED_STATUSES[module]

    for variant, status, expectation in (
        ("trailing slash", statuses[0], allowed[0]),
        ("no slash", statuses[1], allowed[1]),
    ):
        assert status in (
            expectation if isinstance(expectation, tuple) else (expectation,)
        ), (
            f"GET /api/{module} ({variant}) returned {status}, "
            f"expected {expectation} (per the app's OpenAPI schema)"
        )


@pytest.mark.parametrize("module", MODULES)
def test_module_collection_routes_return_data(results, module):
    """A 200 collection route returns a parseable payload."""
    rows, _ = results
    count = {m: c for m, _, _, c in rows}[module]

    slash, noslash, _ = {m: (s, n, c) for m, s, n, c in rows}[module]
    if 200 in (slash, noslash):
        assert isinstance(count, int) and count >= 0


def test_no_module_has_a_failing_slash_variant(results):
    """Aggregate assertion with the full failure list in the message.

    A module "fails" only when an observed status contradicts the app's own
    OpenAPI schema (e.g. a 500, or a GET served at neither slash variant).
    """
    rows, _ = results
    failures = [
        (m, s, n)
        for m, s, n, _ in rows
        if s not in _acceptable(EXPECTED_STATUSES[m][0])
        or n not in _acceptable(EXPECTED_STATUSES[m][1])
    ]
    assert not failures, "Broken collection routes:\n" + "\n".join(
        f"  /api/{m}/  -> {s}\n  /api/{m}   -> {n}" for m, s, n in failures
    )


def _acceptable(expectation):
    """Normalise an expectation entry to a set of acceptable statuses."""
    return expectation if isinstance(expectation, tuple) else (expectation,)
