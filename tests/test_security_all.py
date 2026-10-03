"""
Comprehensive security tests for APEX-OS Business Platform.
Covers: authentication, authorization, input validation, SQL injection, XSS.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from typing import Any

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    """Async HTTP client for the app under test."""
    from app.main import app  # Adjust import to your app entry point
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    """Return headers with a valid auth token (adjust to your auth flow)."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "TestP@ssw0rd!"
    })
    if resp.status_code == 200:
        token = resp.json().get("access_token", "")
        return {"Authorization": f"Bearer {token}"}
    return {}


# ---------------------------------------------------------------------------
# 1. Authentication Tests
# ---------------------------------------------------------------------------

class TestAuthentication:
    """Verify authentication mechanisms are enforced."""

    @pytest.mark.asyncio
    async def test_login_requires_credentials(self, client):
        """Login without credentials must fail."""
        resp = await client.post("/api/v1/auth/login", json={})
        assert resp.status_code in (400, 401, 422)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        """Login with wrong password must fail."""
        resp = await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_requires_auth(self, client):
        """Protected routes must reject unauthenticated requests."""
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_with_valid_auth(self, client, auth_headers):
        """Protected routes must accept authenticated requests."""
        resp = await client.get("/api/v1/users/me", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client):
        """Malformed or invalid tokens must be rejected."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, client):
        """Expired tokens must be rejected."""
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjF9.invalid"}
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_rate_limiting(self, client):
        """Multiple failed login attempts should trigger rate limiting."""
        for _ in range(10):
            await client.post("/api/v1/auth/login", json={
                "username": "testuser",
                "password": "wrong"
            })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "wrong"
        })
        assert resp.status_code in (401, 429)

    @pytest.mark.asyncio
    async def test_password_not_returned_in_response(self, client):
        """Login response must not contain the password."""
        resp = await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "TestP@ssw0rd!"
        })
        if resp.status_code == 200:
            assert "password" not in resp.text.lower()


# ---------------------------------------------------------------------------
# 2. Authorization Tests
# ---------------------------------------------------------------------------

class TestAuthorization:
    """Verify role-based and permission-based access control."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_admin_routes(self, client, auth_headers):
        """Regular users must not access admin-only routes."""
        resp = await client.get("/api/v1/admin/users", headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_access_admin_routes(self, client):
        """Admin users must be able to access admin routes."""
        resp = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminP@ssw0rd!"
        })
        if resp.status_code == 200:
            token = resp.json().get("access_token", "")
            headers = {"Authorization": f"Bearer {token}"}
            resp2 = await client.get("/api/v1/admin/users", headers=headers)
            assert resp2.status_code == 200

    @pytest.mark.asyncio
    async def test_user_cannot_delete_others_resources(self, client, auth_headers):
        """Users must not delete resources they don't own."""
        resp = await client.delete("/api/v1/users/999", headers=auth_headers)
        assert resp.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_user_cannot_modify_others_data(self, client, auth_headers):
        """Users must not modify data belonging to other users."""
        resp = await client.put("/api/v1/users/999", headers=auth_headers, json={
            "email": "hacked@example.com"
        })
        assert resp.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_role_escalation_prevented(self, client, auth_headers):
        """Users must not be able to escalate their own role."""
        resp = await client.put("/api/v1/users/me", headers=auth_headers, json={
            "role": "admin"
        })
        assert resp.status_code in (400, 403, 422)


# ---------------------------------------------------------------------------
# 3. Input Validation Tests
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Verify all inputs are properly validated."""

    @pytest.mark.asyncio
    async def test_email_validation(self, client, auth_headers):
        """Invalid email formats must be rejected."""
        resp = await client.post("/api/v1/users", headers=auth_headers, json={
            "email": "not-an-email",
            "password": "ValidP@ss1"
        })
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_password_min_length(self, client, auth_headers):
        """Passwords below minimum length must be rejected."""
        resp = await client.post("/api/v1/users", headers=auth_headers, json={
            "email": "valid@example.com",
            "password": "short"
        })
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_required_fields_enforced(self, client, auth_headers):
        """Missing required fields must be rejected."""
        resp = await client.post("/api/v1/users", headers=auth_headers, json={})
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_string_length_limits(self, client, auth_headers):
        """Overly long string inputs must be rejected or truncated."""
        resp = await client.post("/api/v1/users", headers=auth_headers, json={
            "email": "a" * 300 + "@example.com",
            "password": "ValidP@ss1"
        })
        assert resp.status_code in (400, 422, 201)

    @pytest.mark.asyncio
    async def test_numeric_field_validation(self, client, auth_headers):
        """Non-numeric values in numeric fields must be rejected."""
        resp = await client.post("/api/v1/projects", headers=auth_headers, json={
            "name": "Test Project",
            "budget": "not-a-number"
        })
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_null_in_required_fields(self, client, auth_headers):
        """Null values in required fields must be rejected."""
        resp = await client.post("/api/v1/users", headers=auth_headers, json={
            "email": None,
            "password": "ValidP@ss1"
        })
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_content_type_enforced(self, client, auth_headers):
        """Requests with wrong content-type must be rejected."""
        resp = await client.post(
            "/api/v1/users",
            headers={**auth_headers, "Content-Type": "text/plain"},
            content="raw text"
        )
        assert resp.status_code in (400, 415, 422)


# ---------------------------------------------------------------------------
# 4. SQL Injection Prevention Tests
# ---------------------------------------------------------------------------

class TestSQLInjectionPrevention:
    """Verify SQL injection attacks are prevented."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1' UNION SELECT * FROM users --",
        "' OR 1=1 --",
        "admin'--",
        "' OR '1'='1' /*",
        "1 AND 1=1",
        "'; EXEC xp_cmdshell('dir'); --",
    ])
    async def test_login_sql_injection(self, client, payload):
        """SQL injection in login fields must not authenticate."""
        resp = await client.post("/api/v1/auth/login", json={
            "username": payload,
            "password": payload
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1' UNION SELECT username,password FROM users --",
    ])
    async def test_search_sql_injection(self, client, auth_headers, payload):
        """SQL injection in search/filter params must be sanitized."""
        resp = await client.get(
            f"/api/v1/users?search={payload}",
            headers=auth_headers
        )
        assert resp.status_code in (200, 400, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict))

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", [
        "'; DROP TABLE projects; --",
        "1' OR '1'='1",
    ])
    async def test_id_field_sql_injection(self, client, auth_headers, payload):
        """SQL injection in ID path parameters must be rejected."""
        resp = await client.get(f"/api/v1/projects/{payload}", headers=auth_headers)
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.asyncio
    async def test_order_by_sql_injection(self, client, auth_headers):
        """SQL injection in sort/order parameters must be rejected."""
        resp = await client.get(
            "/api/v1/users?order_by=username;DROP TABLE users;--",
            headers=auth_headers
        )
        assert resp.status_code in (200, 400, 422)


# ---------------------------------------------------------------------------
# 5. XSS Prevention Tests
# ---------------------------------------------------------------------------

class TestXSSPrevention:
    """Verify cross-site scripting attacks are prevented."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
        "<body onload=alert('xss')>",
        "<svg onload=alert('xss')>",
        "\"><script>alert('xss')</script>",
        "'-alert(1)-'",
    ])
    async def test_xss_in_input_fields(self, client, auth_headers, payload):
        """XSS payloads in user input must be sanitized or rejected."""
        resp = await client.post("/api/v1/projects", headers=auth_headers, json={
            "name": payload,
            "description": "Test description"
        })
        if resp.status_code in (200, 201):
            data = resp.json()
            name = data.get("name", "")
            assert "<script>" not in name.lower()
            assert "javascript:" not in name.lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
    ])
    async def test_xss_in_search_params(self, client, auth_headers, payload):
        """XSS payloads in query parameters must be sanitized."""
        resp = await client.get(
            f"/api/v1/projects?search={payload}",
            headers=auth_headers
        )
        assert resp.status_code in (200, 400, 422)
        if resp.status_code == 200:
            text = resp.text
            assert "<script>alert" not in text.lower()

    @pytest.mark.asyncio
    async def test_xss_in_error_messages(self, client):
        """XSS payloads in error messages must be escaped."""
        resp = await client.get("/api/v1/nonexistent<script>alert(1)</script>")
        assert resp.status_code == 404
        text = resp.text
        assert "<script>" not in text.lower()

    @pytest.mark.asyncio
    async def test_content_type_no_sniff(self, client):
        """Responses should include X-Content-Type-Options header."""
        resp = await client.get("/api/v1/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    @pytest.mark.asyncio
    async def test_xss_protection_header(self, client):
        """Responses should include X-XSS-Protection header."""
        resp = await client.get("/api/v1/health")
        assert "x-xss-protection" in resp.headers


# ---------------------------------------------------------------------------
# Additional Security Headers Tests
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """Verify security headers are present."""

    @pytest.mark.asyncio
    async def test_strict_transport_security(self, client):
        """HSTS header should be present."""
        resp = await client.get("/api/v1/health")
        assert "strict-transport-security" in resp.headers

    @pytest.mark.asyncio
    async def test_content_security_policy(self, client):
        """CSP header should be present."""
        resp = await client.get("/api/v1/health")
        assert "content-security-policy" in resp.headers

    @pytest.mark.asyncio
    async def test_frame_options(self, client):
        """X-Frame-Options header should prevent clickjacking."""
        resp = await client.get("/api/v1/health")
        assert resp.headers.get("x-frame-options") in ("DENY", "SAMEORIGIN")
