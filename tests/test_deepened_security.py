"""Tests for deepened security module."""
import pytest
import time
import jwt
from datetime import datetime, timedelta


class TestJWTRefresh:
    @pytest.fixture
    def jwt_mgr(self):
        from apex_os_bp.security.deepened import TokenManager
        return TokenManager(secret="test-secret", access_ttl=60, refresh_ttl=3600)

    def test_create_access_token(self, jwt_mgr):
        token = jwt_mgr.create_access_token("user1")
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "user1"
        assert payload["type"] == "access"

    def test_create_refresh_token(self, jwt_mgr):
        token = jwt_mgr.create_refresh_token("user1")
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["type"] == "refresh"

    def test_refresh_flow(self, jwt_mgr):
        refresh = jwt_mgr.create_refresh_token("user1")
        new_access = jwt_mgr.refresh(refresh)
        payload = jwt.decode(new_access, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "user1"
        assert payload["type"] == "access"

    def test_expired_access_token_rejected(self, jwt_mgr):
        token = jwt.encode(
            {"sub": "user1", "type": "access", "exp": datetime.utcnow() - timedelta(seconds=1)},
            "test-secret", algorithm="HS256"
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt_mgr.verify(token)

    def test_invalid_token_rejected(self, jwt_mgr):
        with pytest.raises(jwt.InvalidTokenError):
            jwt_mgr.verify("not-a-token")


class TestOAuth2:
    @pytest.fixture
    def oauth(self):
        from apex_os_bp.security.deepened import OAuth2Provider
        return OAuth2Provider()

    def test_authorization_url(self, oauth):
        url = oauth.get_auth_url("client123", "https://app.com/callback")
        assert "client_id=client123" in url
        assert "redirect_uri=" in url

    def test_code_exchange(self, oauth):
        code = oauth.generate_code("client123", "user1")
        token = oauth.exchange_code(code, "client123")
        assert token["access_token"]
        assert token["token_type"] == "Bearer"

    def test_invalid_code_rejected(self, oauth):
        with pytest.raises(ValueError):
            oauth.exchange_code("bad-code", "client123")


class TestSAML:
    @pytest.fixture
    def saml(self):
        from apex_os_bp.security.deepened import SAMLProvider
        return SAMLProvider()

    def test_generate_authn_request(self, saml):
        req = saml.create_authn_request("https://idp.com/sso")
        assert "AuthnRequest" in req
        assert "https://idp.com/sso" in req

    def test_parse_response(self, saml):
        response = saml.create_response("user1", "test@example.com")
        parsed = saml.parse_response(response)
        assert parsed["name_id"] == "user1"
        assert parsed["email"] == "test@example.com"


class TestABAC:
    @pytest.fixture
    def abac(self):
        from apex_os_bp.security.deepened import AccessControl
        return AccessControl()

    def test_allow_owner(self, abac):
        assert abac.check("user1", "read", "doc1", {"owner": "user1"}) is True

    def test_deny_non_owner(self, abac):
        assert abac.check("user2", "read", "doc1", {"owner": "user1"}) is False

    def test_role_based_access(self, abac):
        abac.grant_role("user1", "admin")
        assert abac.check("user1", "delete", "doc1", {}) is True

    def test_permission_denied(self, abac):
        assert abac.check("user1", "delete", "doc1", {}) is False


class TestSecurityHeadersMiddleware:
    @pytest.fixture
    def headers(self):
        from apex_os_bp.security.deepened import SecurityHeadersMiddleware
        return SecurityHeadersMiddleware()

    def test_default_headers(self, headers):
        h = headers.get()
        assert h["X-Content-Type-Options"] == "nosniff"
        assert h["X-Frame-Options"] == "DENY"

    def test_csp_header(self, headers):
        h = headers.get()
        assert "Content-Security-Policy" in h
        assert "default-src" in h["Content-Security-Policy"]

    def test_hsts_header(self, headers):
        h = headers.get()
        assert "Strict-Transport-Security" in h
        assert "max-age" in h["Strict-Transport-Security"]

    def test_custom_csp(self, headers):
        headers.set_csp({"default-src": "'self'"})
        h = headers.get()
        assert h["Content-Security-Policy"] == "default-src 'self'"
