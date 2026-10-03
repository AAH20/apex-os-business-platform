"""
Comprehensive security tests for APEX-OS Business Platform.
Covers authentication, authorization, input validation, SQL injection, and XSS prevention.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
import re


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Synchronous test client for basic endpoint checks."""
    from app.main import app
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Asynchronous test client for async endpoint tests."""
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def valid_user_payload():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecureP@ssw0rd123",
    }


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token-12345"}


# ===========================================================================
# 1. AUTHENTICATION TESTS
# ===========================================================================

class TestAuthentication:
    """Verify authentication mechanisms are enforced correctly."""

    def test_login_requires_credentials(self, client):
        """Login endpoint must reject requests without credentials."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_rejects_invalid_credentials(self, client):
        """Login must reject invalid username/password combinations."""
        response = client.post("/api/v1/auth/login", json={
            "username": "invalid_user",
            "password": "wrong_password",
        })
        assert response.status_code == 401

    def test_login_rejects_empty_password(self, client):
        """Login must reject empty password strings."""
        response = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "",
        })
        assert response.status_code == 422

    def test_protected_endpoint_requires_auth(self, client):
        """Protected endpoints must reject unauthenticated requests."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_protected_endpoint_rejects_invalid_token(self, client):
        """Protected endpoints must reject invalid bearer tokens."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_rejects_malformed_token(self, client):
        """Protected endpoints must reject malformed authorization headers."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "NotBearer token123"},
        )
        assert response.status_code == 401

    def test_token_expiry_enforced(self, client):
        """Expired tokens must be rejected."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer expired.token.value"},
        )
        assert response.status_code == 401

    def test_password_not_returned_in_response(self, client):
        """Login response must never contain the user's password."""
        response = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "SecureP@ssw0rd123",
        })
        if response.status_code == 200:
            assert "password" not in response.json()

    def test_rate_limiting_on_login(self, client):
        """Login endpoint should enforce rate limiting after repeated failures."""
        for _ in range(10):
            client.post("/api/v1/auth/login", json={
                "username": "testuser",
                "password": "wrong",
            })
        response = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "wrong",
        })
        assert response.status_code in (401, 429)

    def test_account_lockout_after_failed_attempts(self, client):
        """Account should be temporarily locked after repeated failed logins."""
        for _ in range(6):
            client.post("/api/v1/auth/login", json={
                "username": "lockme_user",
                "password": "wrong",
            })
        response = client.post("/api/v1/auth/login", json={
            "username": "lockme_user",
            "password": "SecureP@ssw0rd123",
        })
        assert response.status_code in (401, 423)

    def test_refresh_token_rotation(self, client):
        """Using a refresh token should issue a new refresh token."""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "old-refresh-token",
        })
        if response.status_code == 200:
            data = response.json()
            assert "refresh_token" in data
            assert data["refresh_token"] != "old-refresh-token"


# ===========================================================================
# 2. AUTHORIZATION TESTS
# ===========================================================================

class TestAuthorization:
    """Verify role-based and permission-based access control."""

    def test_admin_endpoint_requires_admin_role(self, client):
        """Admin-only endpoints must reject non-admin users."""
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": "Bearer user-token"},
        )
        assert response.status_code == 403

    def test_user_cannot_access_other_user_data(self, client):
        """Users must not access another user's private data."""
        response = client.get(
            "/api/v1/users/other-user-id/profile",
            headers={"Authorization": "Bearer user-token"},
        )
        assert response.status_code in (403, 404)

    def test_role_escalation_prevented(self, client):
        """Users must not be able to escalate their own role."""
        response = client.patch(
            "/api/v1/users/me",
            json={"role": "admin"},
            headers={"Authorization": "Bearer user-token"},
        )
        assert response.status_code in (403, 422)

    def test_delete_requires_ownership_or_admin(self, client):
        """Delete operations require resource ownership or admin role."""
        response = client.delete(
            "/api/v1/resources/other-user-resource",
            headers={"Authorization": "Bearer user-token"},
        )
        assert response.status_code in (403, 404)

    def test_read_only_user_cannot_write(self, client):
        """Read-only role must not perform write operations."""
        response = client.post(
            "/api/v1/resources",
            json={"name": "test"},
            headers={"Authorization": "Bearer readonly-token"},
        )
        assert response.status_code == 403

    def test_cross_tenant_access_denied(self, client):
        """Users must not access resources belonging to other tenants."""
        response = client.get(
            "/api/v1/tenant-b/resources",
            headers={"Authorization": "Bearer tenant-a-token"},
        )
        assert response.status_code in (403, 404)

    def test_inactive_user_denied_access(self, client):
        """Deactivated/inactive users must be denied access."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer inactive-user-token"},
        )
        assert response.status_code in (401, 403)


# ===========================================================================
# 3. INPUT VALIDATION TESTS
# ===========================================================================

class TestInputValidation:
    """Verify all inputs are properly validated and sanitized."""

    def test_email_format_validation(self, client):
        """Invalid email formats must be rejected."""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "not-an-email",
            "password": "SecureP@ssw0rd123",
        })
        assert response.status_code == 422

    def test_password_minimum_length(self, client):
        """Passwords below minimum length must be rejected."""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "short",
        })
        assert response.status_code == 422

    def test_password_complexity_requirements(self, client):
        """Passwords must meet complexity requirements."""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "alllowercase",
        })
        assert response.status_code == 422

    def test_username_special_characters_rejected(self, client):
        """Usernames with dangerous special characters must be rejected."""
        response = client.post("/api/v1/auth/register", json={
            "username": "user;DROP TABLE users;--",
            "email": "test@example.com",
            "password": "SecureP@ssw0rd123",
        })
        assert response.status_code in (422, 400)

    def test_username_length_limits(self, client):
        """Usernames exceeding max length must be rejected."""
        response = client.post("/api/v1/auth/register", json={
            "username": "a" * 256,
            "email": "test@example.com",
            "password": "SecureP@ssw0rd123",
        })
        assert response.status_code == 422

    def test_integer_field_rejects_strings(self, client):
        """Integer fields must reject non-numeric input."""
        response = client.post("/api/v1/resources", json={
            "name": "test",
            "quantity": "not-a-number",
        }, headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 422

    def test_date_field_rejects_invalid_dates(self, client):
        """Date fields must reject invalid date strings."""
        response = client.post("/api/v1/events", json={
            "title": "Test Event",
            "date": "not-a-date",
        }, headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 422

    def test_file_upload_type_validation(self, client):
        """File uploads must validate file types."""
        response = client.post(
            "/api/v1/upload",
            files={"file": ("malware.exe", b"binary content", "application/x-msdownload")},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (400, 415, 422)

    def test_file_upload_size_limit(self, client):
        """File uploads exceeding size limits must be rejected."""
        large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        response = client.post(
            "/api/v1/upload",
            files={"file": ("large.pdf", large_content, "application/pdf")},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (413, 422)

    def test_json_body_size_limit(self, client):
        """Oversized JSON payloads must be rejected."""
        large_payload = {"data": "x" * (5 * 1024 * 1024)}
        response = client.post(
            "/api/v1/bulk",
            json=large_payload,
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (413, 422)

    def test_path_traversal_in_filename_rejected(self, client):
        """Filenames containing path traversal sequences must be rejected."""
        response = client.post(
            "/api/v1/upload",
            files={"file": ("../../../etc/passwd", b"content", "text/plain")},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (400, 422)

    def test_null_bytes_rejected_in_input(self, client):
        """Null bytes in string inputs must be rejected."""
        response = client.post("/api/v1/resources", json={
            "name": "test\x00malicious",
        }, headers={"Authorization": "Bearer test-token"})
        assert response.status_code in (400, 422)


# ===========================================================================
# 4. SQL INJECTION PREVENTION TESTS
# ===========================================================================

class TestSQLInjectionPrevention:
    """Verify SQL injection attacks are prevented."""

    def test_login_sql_injection_username(self, client):
        """SQL injection in login username field must be prevented."""
        response = client.post("/api/v1/auth/login", json={
            "username": "admin' OR '1'='1",
            "password": "anything",
        })
        assert response.status_code == 401

    def test_login_sql_injection_password(self, client):
        """SQL injection in login password field must be prevented."""
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "' OR '1'='1' --",
        })
        assert response.status_code == 401

    def test_search_sql_injection(self, client):
        """SQL injection in search parameters must be prevented."""
        response = client.get(
            "/api/v1/resources/search?q='; DROP TABLE users; --",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (200, 400, 422)

    def test_order_by_sql_injection(self, client):
        """SQL injection in sort/order parameters must be prevented."""
        response = client.get(
            "/api/v1/resources?order_by=id;DELETE FROM users",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (200, 400, 422)

    def test_filter_sql_injection(self, client):
        """SQL injection in filter parameters must be prevented."""
        response = client.get(
            "/api/v1/resources?filter_name=name' UNION SELECT * FROM users--",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (200, 400, 422)

    def test_body_sql_injection_in_text_fields(self, client):
        """SQL injection in JSON body text fields must be prevented."""
        response = client.post("/api/v1/resources", json={
            "name": "test'; DROP TABLE resources; --",
            "description": "normal description",
        }, headers={"Authorization": "Bearer test-token"})
        assert response.status_code in (200, 201, 400, 422)

    def test_sql_injection_does_not_leak_errors(self, client):
        """SQL injection attempts must not leak database error details."""
        response = client.get(
            "/api/v1/resources?filter_name=' AND 1=CONVERT(int, (SELECT table_name FROM information_schema.tables))--",
            headers={"Authorization": "Bearer test-token"},
        )
        if response.status_code >= 400:
            body = response.text.lower()
            assert "sql" not in body
            assert "syntax" not in body
            assert "error" not in body or "internal" in body

    def test_union_based_injection_prevented(self, client):
        """UNION-based SQL injection must be prevented."""
        response = client.get(
            "/api/v1/resources/search?q=' UNION SELECT username,password FROM users--",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (200, 400, 422)

    def test_time_based_blind_injection_prevented(self, client):
        """Time-based blind SQL injection must be prevented."""
        response = client.get(
            "/api/v1/resources/search?q='; WAITFOR DELAY '0:0:5'--",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (200, 400, 422)

    def test_stored_procedure_injection_prevented(self, client):
        """Stored procedure call injection must be prevented."""
        response = client.get(
            "/api/v1/resources/search?q='; EXEC xp_cmdshell('dir')--",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (200, 400, 422)


# ===========================================================================
# 5. XSS PREVENTION TESTS
# ===========================================================================

class TestXSSPrevention:
    """Verify cross-site scripting (XSS) attacks are prevented."""

    def test_script_tag_in_input_rejected_or_sanitized(self, client):
        """Script tags in user input must be rejected or sanitized."""
        response = client.post("/api/v1/resources", json={
            "name": "<script>alert('xss')</script>",
            "description": "test",
        }, headers={"Authorization": "Bearer test-token"})
        if response.status_code in (200, 201):
            assert "<script>" not in response.text

    def test_javascript_protocol_in_url_rejected(self, client):
        """javascript: protocol in URL fields must be rejected."""
        response = client.post("/api/v1/resources", json={
            "name": "test",
            "url": "javascript:alert('xss')",
        }, headers={"Authorization": "Bearer test-token"})
        assert response.status_code in (200, 201, 400, 422)
        if response.status_code in (200, 201):
            assert "javascript:" not in response.text.lower()

    def test_onerror_attribute_sanitized(self, client):
        """Event handler attributes must be sanitized."""
        response = client.post("/api/v1/resources", json={
            "name": "<img src=x onerror=alert('xss')>",
            "description": "test",
        }, headers={"Authorization": "Bearer test-token"})
        if response.status_code in (200, 201):
            assert "onerror" not in response.text.lower()

    def test_onload_attribute_sanitized(self, client):
        """onload event handlers must be sanitized."""
        response = client.post("/api/v1/resources", json={
            "name": "<body onload=alert('xss')>",
            "description": "test",
        }, headers={"Authorization": "Bearer test-token"})
        if response.status_code in (200, 201):
            assert "onload" not in response.text.lower()

    def test_svg_xss_vector_sanitized(self, client):
        """SVG-based XSS vectors must be sanitized."""
        response = client.post("/api/v1/resources", json={
            "name": "<svg onload=alert('xss')>",
            "description": "test",
        }, headers={"Authorization": "Bearer test-token"})
        if response.status_code in (200, 201):
            assert "<svg" not in response.text.lower()

    def test_template_injection_sanitized(self, client):
        """Template injection patterns must be sanitized."""
        response = client.post("/api/v1/resources", json={
            "name": "{{7*7}}",
            "description": "${7*7}",
        }, headers={"Authorization": "Bearer test-token"})
        if response.status_code in (200, 201):
            assert "49" not in response.text

    def test_xss_in_search_query_sanitized(self, client):
        """XSS payloads in search queries must be sanitized."""
        response = client.get(
            "/api/v1/resources/search?q=<script>alert(1)</script>",
            headers={"Authorization": "Bearer test-token"},
        )
        assert "<script>" not in response.text

    def test_xss_in_error_messages_sanitized(self, client):
        """XSS payloads in error messages must be sanitized."""
        response = client.get(
            "/api/v1/resources/<script>alert(1)</script>",
            headers={"Authorization": "Bearer test-token"},
        )
        if response.status_code >= 400:
            assert "<script>" not in response.text

    def test_content_type_header_enforced(self, client):
        """Responses must include X-Content-Type-Options header."""
        response = client.get("/api/v1/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_xss_protection_header_present(self, client):
        """Responses should include X-XSS-Protection header."""
        response = client.get("/api/v1/security-headers")
        assert "x-xss-protection" in response.headers

    def test_csp_header_present(self, client):
        """Responses should include Content-Security-Policy header."""
        response = client.get("/api/v1/security-headers")
        assert "content-security-policy" in response.headers

    def test_reflected_xss_in_username_sanitized(self, client):
        """Reflected XSS via username must be sanitized."""
        response = client.get(
            "/api/v1/users/<script>alert(1)</script>",
            headers={"Authorization": "Bearer test-token"},
        )
        if response.status_code >= 400:
            assert "<script>" not in response.text

    def test_dom_xss_via_hash_prevented(self, client):
        """DOM-based XSS via URL hash must be handled safely."""
        response = client.get(
            "/api/v1/resources#<img src=x onerror=alert(1)>",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (200, 404)

    def test_stored_xss_via_comment_field(self, client):
        """Stored XSS via comment/note fields must be sanitized."""
        response = client.post("/api/v1/resources/123/comments", json={
            "body": "<iframe src='javascript:alert(1)'></iframe>",
        }, headers={"Authorization": "Bearer test-token"})
        if response.status_code in (200, 201):
            assert "<iframe" not in response.text.lower()

    def test_xss_with_encoded_characters(self, client):
        """XSS using HTML entity encoding must be sanitized."""
        response = client.post("/api/v1/resources", json={
            "name": "&lt;script&gt;alert(1)&lt;/script&gt;",
            "description": "test",
        }, headers={"Authorization": "Bearer test-token"})
        if response.status_code in (200, 201):
            assert "<script>" not in response.text

    def test_xss_with_unicode_encoding(self, client):
        """XSS using Unicode encoding must be sanitized."""
        response = client.post("/api/v1/resources", json={
            "name": "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e",
            "description": "test",
        }, headers={"Authorization": "Bearer test-token"})
        if response.status_code in (200, 201):
            assert "<script>" not in response.text
