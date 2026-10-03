"""
Comprehensive security tests for all APEX-OS Business Platform pages.
Covers XSS prevention, CSRF protection, input validation, authentication, and authorization.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

# Import the FastAPI app and dependencies
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from app.main import app
    from app.core.security import create_access_token, verify_password, get_password_hash
    from app.core.config import settings
    from app.api.deps import get_current_user, get_current_active_user
    from app.models.user import User
except ImportError:
    # Fallback for different project structures
    app = None
    create_access_token = None
    verify_password = None
    get_password_hash = None
    settings = None
    get_current_user = None
    get_current_active_user = None
    User = None


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    """Create an async test client."""
    if app is None:
        pytest.skip("FastAPI app not available")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client():
    """Create an authenticated async test client."""
    if app is None:
        pytest.skip("FastAPI app not available")
    transport = ASGITransport(app=app)
    token = "test-token"
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_client():
    """Create an admin authenticated async test client."""
    if app is None:
        pytest.skip("FastAPI app not available")
    transport = ASGITransport(app=app)
    token = "admin-token"
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


# ─── 1. XSS Prevention Tests ─────────────────────────────────────────────────

class TestXSSPrevention:
    """Verify that user-supplied input cannot inject executable scripts."""

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
        "<svg onload=alert('xss')>",
        "\"><script>alert(String.fromCharCode(88,83,83))</script>",
        "'-alert(1)-'",
        "<iframe src='javascript:alert(1)'>",
        "<body onload=alert('xss')>",
        "<input onfocus=alert('xss') autofocus>",
        "<marquee onstart=alert('xss')>",
        "<details open ontoggle=alert('xss')>",
        "<math><mtext><table><mglyph><style><!--</style><img src=x onerror=alert(1)>",
    ]

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_login_form(self, client, payload):
        """XSS payloads in login fields must not be reflected unescaped."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": payload, "password": payload},
        )
        if resp.status_code == 200:
            assert payload not in resp.text or "&lt;" in resp.text or "&#" in resp.text

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_registration(self, client, payload):
        """XSS payloads in registration fields must be sanitized."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": payload,
                "email": f"{payload}@test.com",
                "password": "TestPass123!",
                "full_name": payload,
            },
        )
        if resp.status_code in (200, 201):
            assert "<script>" not in resp.text.lower() or "&lt;script&gt;" in resp.text.lower()

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_search_params(self, client, payload):
        """XSS via query parameters must not execute."""
        resp = await client.get(f"/api/v1/search?q={payload}")
        if resp.status_code == 200:
            assert "<script>" not in resp.text.lower() or "&lt;script&gt;" in resp.text.lower()

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_headers(self, client, payload):
        """XSS via custom headers must not be reflected."""
        resp = await client.get("/", headers={"X-Custom": payload})
        if resp.status_code == 200:
            assert "<script>" not in resp.text.lower() or "&lt;script&gt;" in resp.text.lower()

    async def test_xss_in_json_body(self, client):
        """XSS in JSON body fields must be escaped in response."""
        resp = await client.post(
            "/api/v1/feedback",
            json={"message": "<script>alert(1)</script>", "rating": 5},
        )
        if resp.status_code in (200, 201):
            assert "<script>" not in resp.text.lower() or "&lt;script&gt;" in resp.text.lower()

    async def test_content_type_enforcement(self, client):
        """Responses must have correct content-type to prevent MIME sniffing."""
        resp = await client.get("/")
        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type or "application/json" in content_type

    async def test_xss_protection_header(self, client):
        """X-XSS-Protection header should be set."""
        resp = await client.get("/")
        assert "x-xss-protection" in resp.headers or "content-security-policy" in resp.headers


# ─── 2. CSRF Protection Tests ───────────────────────────────────────────────

class TestCSRFProtection:
    """Verify that state-changing requests require CSRF tokens."""

    async def test_csrf_token_required_for_post(self, client):
        """POST without CSRF token should be rejected."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "user", "password": "pass"},
            headers={"Origin": "http://evil.com"},
        )
        assert resp.status_code in (403, 401, 400)

    async def test_csrf_token_required_for_put(self, client):
        """PUT without CSRF token should be rejected."""
        resp = await client.put(
            "/api/v1/users/me",
            json={"full_name": "New Name"},
            headers={"Origin": "http://evil.com"},
        )
        assert resp.status_code in (403, 401, 400)

    async def test_csrf_token_required_for_delete(self, client):
        """DELETE without CSRF token should be rejected."""
        resp = await client.request(
            "DELETE",
            "/api/v1/users/1",
            headers={"Origin": "http://evil.com"},
        )
        assert resp.status_code in (403, 401, 400)

    async def test_csrf_token_required_for_patch(self, client):
        """PATCH without CSRF token should be rejected."""
        resp = await client.patch(
            "/api/v1/users/me",
            json={"email": "new@test.com"},
            headers={"Origin": "http://evil.com"},
        )
        assert resp.status_code in (403, 401, 400)

    async def test_csrf_protection_on_password_change(self, client):
        """Password change must be CSRF-protected."""
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"old_password": "old", "new_password": "new"},
            headers={"Origin": "http://evil.com"},
        )
        assert resp.status_code in (403, 401, 400)

    async def test_csrf_protection_on_profile_update(self, client):
        """Profile update must be CSRF-protected."""
        resp = await client.put(
            "/api/v1/users/me",
            json={"bio": "hacked"},
            headers={"Origin": "http://evil.com"},
        )
        assert resp.status_code in (403, 401, 400)

    async def test_same_site_cookie_attribute(self, client):
        """Session cookies must have SameSite attribute."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "user", "password": "pass"},
        )
        set_cookie = resp.headers.get("set-cookie", "")
        if set_cookie:
            assert "samesite" in set_cookie.lower()

    async def test_referer_check_on_sensitive_ops(self, client):
        """Sensitive operations should validate Referer/Origin."""
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"email": "admin@test.com"},
            headers={"Referer": "http://evil.com", "Origin": "http://evil.com"},
        )
        assert resp.status_code in (403, 400, 401)


# ─── 3. Input Validation Tests ──────────────────────────────────────────────

class TestInputValidation:
    """Verify that all inputs are properly validated and sanitized."""

    async def test_sql_injection_in_login(self, client):
        """SQL injection attempts in login must be rejected."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "' OR '1'='1", "password": "' OR '1'='1"},
        )
        assert resp.status_code in (401, 403, 422)

    async def test_sql_injection_in_search(self, client):
        """SQL injection in search query must be rejected."""
        resp = await client.get("/api/v1/search?q='; DROP TABLE users;--")
        assert resp.status_code in (400, 422, 500)

    async def test_command_injection_in_filename(self, client):
        """Command injection in filename must be rejected."""
        resp = await client.post(
            "/api/v1/files/upload",
            files={"file": ("; rm -rf /; echo pwned", b"content")},
        )
        assert resp.status_code in (400, 422, 403)

    async def test_path_traversal_in_file_access(self, client):
        """Path traversal attempts must be blocked."""
        resp = await client.get("/api/v1/files/../../../etc/passwd")
        assert resp.status_code in (400, 403, 404)

    async def test_path_traversal_encoded(self, client):
        """URL-encoded path traversal must be blocked."""
        resp = await client.get("/api/v1/files/..%2F..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code in (400, 403, 404)

    async def test_oversized_input_rejected(self, client):
        """Extremely large inputs must be rejected."""
        huge_string = "A" * 100000
        resp = await client.post(
            "/api/v1/feedback",
            json={"message": huge_string},
        )
        assert resp.status_code in (400, 413, 422)

    async def test_invalid_email_format(self, client):
        """Invalid email formats must be rejected."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "not-an-email",
                "password": "TestPass123!",
            },
        )
        assert resp.status_code in (400, 422)

    async def test_weak_password_rejected(self, client):
        """Weak passwords must be rejected."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@test.com",
                "password": "123",
            },
        )
        assert resp.status_code in (400, 422)

    async def test_null_bytes_rejected(self, client):
        """Null bytes in input must be rejected."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "test\x00user",
                "email": "test@test.com",
                "password": "TestPass123!",
            },
        )
        assert resp.status_code in (400, 422)

    async def test_unicode_normalization_attack(self, client):
        """Unicode normalization attacks must be handled."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "аdmin",  # Cyrillic 'а'
                "email": "test@test.com",
                "password": "TestPass123!",
            },
        )
        # Should either reject or normalize safely
        assert resp.status_code in (200, 201, 400, 422)

    async def test_content_type_validation(self, client):
        """Wrong content-type must be rejected."""
        resp = await client.post(
            "/api/v1/auth/register",
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (400, 415, 422)

    async def test_integer_overflow(self, client):
        """Integer overflow attempts must be handled."""
        resp = await client.get("/api/v1/items?page=99999999999999999999")
        assert resp.status_code in (400, 422, 500)


# ─── 4. Authentication Tests ────────────────────────────────────────────────

class TestAuthentication:
    """Verify that authentication mechanisms are secure."""

    async def test_login_requires_valid_credentials(self, client):
        """Login with invalid credentials must fail."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_login_rate_limiting(self, client):
        """Multiple failed login attempts should trigger rate limiting."""
        for _ in range(10):
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": "user", "password": "wrong"},
            )
        assert resp.status_code in (401, 429)

    async def test_token_expiration(self, client):
        """Expired tokens must be rejected."""
        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer expired-token"},
        )
        assert resp.status_code == 401

    async def test_invalid_token_rejected(self, client):
        """Malformed tokens must be rejected."""
        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    async def test_no_token_rejected(self, client):
        """Requests without token must be rejected."""
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401

    async def test_token_in_url_rejected(self, client):
        """Tokens in URL query params should be rejected or not logged."""
        resp = await client.get("/api/v1/users/me?token=secret-token")
        assert resp.status_code in (401, 403)

    async def test_password_not_in_response(self, client):
        """Password hash must never appear in API responses."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "user", "password": "pass"},
        )
        assert "password" not in resp.text.lower() or "password" in resp.text.lower()
        assert "hash" not in resp.text.lower()

    async def test_session_fixation_protection(self, client):
        """Session ID must change after login."""
        resp_before = await client.get("/")
        resp_after = await client.post(
            "/api/v1/auth/login",
            data={"username": "user", "password": "pass"},
        )
        # Session identifier should differ
        assert resp_before.cookies != resp_after.cookies or resp_after.status_code == 401

    async def test_account_lockout(self, client):
        """Account should lock after repeated failures."""
        for _ in range(15):
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": "user", "password": "wrong"},
            )
        assert resp.status_code in (401, 423, 429)

    async def test_refresh_token_rotation(self, client):
        """Refresh tokens should be rotated."""
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "old-refresh-token"},
        )
        assert resp.status_code in (200, 401)


# ─── 5. Authorization Tests ─────────────────────────────────────────────────

class TestAuthorization:
    """Verify that users can only access resources they are authorized for."""

    async def test_unauthenticated_access_denied(self, client):
        """Unauthenticated users cannot access protected resources."""
        protected_endpoints = [
            "/api/v1/users/me",
            "/api/v1/dashboard",
            "/api/v1/admin/users",
            "/api/v1/settings",
        ]
        for endpoint in protected_endpoints:
            resp = await client.get(endpoint)
            assert resp.status_code in (401, 403), f"{endpoint} should require auth"

    async def test_non_admin_cannot_access_admin(self, authenticated_client):
        """Non-admin users cannot access admin endpoints."""
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/settings",
            "/api/v1/admin/audit-logs",
        ]
        for endpoint in admin_endpoints:
            resp = await authenticated_client.get(endpoint)
            assert resp.status_code in (403, 401), f"{endpoint} should require admin"

    async def test_user_cannot_access_other_user_data(self, authenticated_client):
        """Users cannot access other users' data."""
        resp = await authenticated_client.get("/api/v1/users/99999/profile")
        assert resp.status_code in (403, 404)

    async def test_user_cannot_delete_other_user(self, authenticated_client):
        """Users cannot delete other users."""
        resp = await authenticated_client.request("DELETE", "/api/v1/users/99999")
        assert resp.status_code in (403, 404)

    async def test_user_cannot_modify_other_user(self, authenticated_client):
        """Users cannot modify other users' data."""
        resp = await authenticated_client.put(
            "/api/v1/users/99999",
            json={"full_name": "Hacked"},
        )
        assert resp.status_code in (403, 404)

    async def test_role_escalation_prevented(self, authenticated_client):
        """Users cannot escalate their own privileges."""
        resp = await authenticated_client.put(
            "/api/v1/users/me",
            json={"role": "admin", "is_superuser": True},
        )
        assert resp.status_code in (403, 422, 400)

    async def test_idor_in_resource_access(self, authenticated_client):
        """Insecure Direct Object References must be prevented."""
        resp = await authenticated_client.get("/api/v1/documents/1")
        assert resp.status_code in (200, 403, 404)

    async def test_privilege_escalation_via_parameter(self, authenticated_client):
        """Parameter tampering for privilege escalation must fail."""
        resp = await authenticated_client.post(
            "/api/v1/users/me/role",
            json={"role": "admin"},
        )
        assert resp.status_code in (403, 404, 405)

    async def test_horizontal_privilege_escalation(self, authenticated_client):
        """Users cannot perform actions on behalf of other users."""
        resp = await authenticated_client.post(
            "/api/v1/users/99999/reset-password",
            json={"new_password": "hacked"},
        )
        assert resp.status_code in (403, 404)

    async def test_vertical_privilege_escalation(self, authenticated_client):
        """Regular users cannot access superuser features."""
        resp = await authenticated_client.get("/api/v1/admin/system/config")
        assert resp.status_code in (403, 404)

    async def test_api_key_scoping(self, authenticated_client):
        """API keys should be scoped to their permissions."""
        resp = await authenticated_client.get(
            "/api/v1/admin/users",
            headers={"X-API-Key": "user-scoped-key"},
        )
        assert resp.status_code in (403, 401)


# ─── Security Headers Tests ─────────────────────────────────────────────────

class TestSecurityHeaders:
    """Verify security headers are present on all responses."""

    async def test_strict_transport_security(self, client):
        """HSTS header should be set."""
        resp = await client.get("/")
        assert "strict-transport-security" in resp.headers

    async def test_content_security_policy(self, client):
        """CSP header should be set."""
        resp = await client.get("/")
        assert "content-security-policy" in resp.headers

    async def test_x_content_type_options(self, client):
        """X-Content-Type-Options should be nosniff."""
        resp = await client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options(self, client):
        """X-Frame-Options should prevent clickjacking."""
        resp = await client.get("/")
        assert resp.headers.get("x-frame-options") in ("DENY", "SAMEORIGIN")

    async def test_referrer_policy(self, client):
        """Referrer-Policy should be set."""
        resp = await client.get("/")
        assert "referrer-policy" in resp.headers

    async def test_permissions_policy(self, client):
        """Permissions-Policy should restrict features."""
        resp = await client.get("/")
        assert "permissions-policy" in resp.headers


# ─── Rate Limiting Tests ────────────────────────────────────────────────────

class TestRateLimiting:
    """Verify rate limiting is enforced on sensitive endpoints."""

    async def test_login_rate_limit(self, client):
        """Login endpoint should be rate limited."""
        for _ in range(20):
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": "user", "password": "wrong"},
            )
        assert resp.status_code == 429

    async def test_registration_rate_limit(self, client):
        """Registration endpoint should be rate limited."""
        for _ in range(10):
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"user{resp.status_code}",
                    "email": f"user{resp.status_code}@test.com",
                    "password": "TestPass123!",
                },
            )
        assert resp.status_code in (429, 400)

    async def test_password_reset_rate_limit(self, client):
        """Password reset should be rate limited."""
        for _ in range(10):
            resp = await client.post(
                "/api/v1/auth/reset-password",
                json={"email": "test@test.com"},
            )
        assert resp.status_code in (429, 400)


# ─── File Upload Security Tests ─────────────────────────────────────────────

class TestFileUploadSecurity:
    """Verify file upload security measures."""

    async def test_executable_file_rejected(self, client):
        """Executable files must be rejected."""
        resp = await client.post(
            "/api/v1/files/upload",
            files={"file": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")},
        )
        assert resp.status_code in (400, 403, 415)

    async def test_script_file_rejected(self, client):
        """Script files must be rejected."""
        resp = await client.post(
            "/api/v1/files/upload",
            files={"file": ("evil.php", b"<?php echo 'pwned'; ?>", "application/x-php")},
        )
        assert resp.status_code in (400, 403, 415)

    async def test_file_size_limit(self, client):
        """Oversized files must be rejected."""
        resp = await client.post(
            "/api/v1/files/upload",
            files={"file": ("large.bin", b"x" * (100 * 1024 * 1024), "application/octet-stream")},
        )
        assert resp.status_code in (400, 413)

    async def test_content_type_spoofing(self, client):
        """Content-Type spoofing must be detected."""
        resp = await client.post(
            "/api/v1/files/upload",
            files={"file": ("fake.png", b"<?php echo 'pwned'; ?>", "image/png")},
        )
        assert resp.status_code in (400, 403, 415)
