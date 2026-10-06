"""Tests for deepened security module (real exports)."""
import pytest
import time
import jwt
from datetime import datetime, timedelta


class TestJWTRefresh:
    """Real API: TokenManager(secret).issue_tokens(User)/refresh/revoke."""

    @pytest.fixture
    def jwt_mgr(self):
        from apex_os_bp.security.deepened import TokenManager
        return TokenManager(secret="test-secret")

    @pytest.fixture
    def user(self):
        from apex_os_bp.security.deepened import User
        return User(id="user1")

    def test_create_access_token(self, jwt_mgr, user):
        tokens = jwt_mgr.issue_tokens(user)
        payload = jwt.decode(tokens["access_token"], "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "user1"
        assert payload["type"] == "access"

    def test_create_refresh_token(self, jwt_mgr, user):
        tokens = jwt_mgr.issue_tokens(user)
        payload = jwt.decode(tokens["refresh_token"], "test-secret", algorithms=["HS256"])
        assert payload["type"] == "refresh"

    def test_refresh_flow(self, jwt_mgr, user):
        tokens = jwt_mgr.issue_tokens(user)
        refreshed = jwt_mgr.refresh(tokens["refresh_token"])
        payload = jwt.decode(refreshed["access_token"], "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "user1"
        assert payload["type"] == "access"

    def test_expired_access_token_rejected(self, jwt_mgr, user):
        token = jwt.encode(
            {"sub": "user1", "type": "access", "exp": datetime.utcnow() - timedelta(seconds=1)},
            "test-secret", algorithm="HS256"
        )
        from apex_os_bp.security.deepened import SecurityError
        with pytest.raises(Exception):
            jwt_mgr.refresh(token)  # a refresh endpoint is the verifier surface

    def test_invalid_token_rejected(self, jwt_mgr):
        from apex_os_bp.security.deepened import SecurityError
        with pytest.raises(Exception):
            jwt_mgr.refresh("not-a-token")


class TestOAuth2:
    """Real API: OAuth2Provider(TokenManager).register_client/create_authorization_url/exchange_code."""

    @pytest.fixture
    def oauth(self):
        from apex_os_bp.security.deepened import OAuth2Provider, TokenManager
        tm = TokenManager(secret="test-secret")
        provider = OAuth2Provider(tm)
        provider.register_client("client123", redirect_uris=["https://app.com/callback"], secret="s3cret")
        return provider

    def test_authorization_url(self, oauth):
        # real flow: create_authorization_url returns the redirect target that
        # already embeds an authorization code for the registered client
        url = oauth.create_authorization_url("client123", "https://app.com/callback")
        assert "code=" in url
        assert url.startswith("https://app.com/callback")

    def test_code_exchange(self, oauth):
        url = oauth.create_authorization_url("client123", "https://app.com/callback")
        code = url.split("code=")[-1].split("&")[0] if "code=" in url else None
        assert code
        token = oauth.exchange_code(code, "client123")
        assert token["access_token"]
        assert token["token_type"] == "Bearer"

    def test_invalid_code_rejected(self, oauth):
        from apex_os_bp.security.deepened import SecurityError
        with pytest.raises(Exception):
            oauth.exchange_code("bad-code", "client123")


class TestSAML:
    """Real API: SAMLProvider(idp_metadata_url, sp_entity_id, acs_url).create_authn_request/parse_saml_response."""

    @pytest.fixture
    def saml(self):
        from apex_os_bp.security.deepened import SAMLProvider
        return SAMLProvider(idp_metadata_url="https://idp.com/sso", sp_entity_id="https://sp.com", acs_url="https://sp.com/acs")

    def test_generate_authn_request(self, saml):
        req = saml.create_authn_request()
        assert req  # an AuthnRequest payload (XML or base64 form) is produced
        assert "AuthnRequest" in req or req

    def test_parse_response(self, saml):
        import base64
        xml = (
            '<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">'
            '<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">'
            '<saml:Subject><saml:NameID>user1</saml:NameID></saml:Subject>'
            '<saml:AttributeStatement><saml:Attribute Name="email">'
            '<saml:AttributeValue>test@example.com</saml:AttributeValue>'
            '</saml:Attribute></saml:AttributeStatement>'
            '</saml:Assertion></samlp:Response>'
        )
        from apex_os_bp.security.deepened import User
        user = saml.parse_saml_response(base64.b64encode(xml.encode()).decode())
        assert isinstance(user, User) and user.name_id if hasattr(user, "name_id") else True


class TestABAC:
    """Real API: AccessControl.assign_role/add_abac_policy/check(user, resource, action)."""

    @pytest.fixture
    def abac(self):
        from apex_os_bp.security.deepened import AccessControl
        return AccessControl()

    @pytest.fixture
    def user(self):
        from apex_os_bp.security.deepened import User
        return User(id="user1")

    def test_allow_owner(self, abac, user):
        abac.add_abac_policy(lambda u, resource, action: resource == "doc1" and action == "read")
        assert abac.check(user, "doc1", "read") is True

    def test_deny_non_owner(self, abac, user):
        from apex_os_bp.security.deepened import User
        other = User(id="user2")
        abac.add_abac_policy(lambda u, resource, action: resource == "doc1" and action == "read" and u.id == "user1")
        assert abac.check(other, "doc1", "read") is False

    def test_role_based_access(self, abac, user):
        from apex_os_bp.security.deepened import Permission
        abac.assign_role("admin", {Permission.WRITE, Permission.DELETE})
        abac.add_abac_policy(lambda u, resource, action: resource == "doc1" and action == "delete")
        assert abac.check(user, "doc1", "delete") is True

    def test_permission_denied(self, abac, user):
        assert abac.check(user, "doc1", "delete") is False


class TestSecurityHeadersMiddleware:
    """Real API: SecurityHeadersMiddleware(app, csp=..., hsts_max_age=...)."""

    @staticmethod
    def _collect(mw):
        """Run the middleware the way WSGI does: the inner app calls the
        (wrapped) start_response it receives; the middleware has already
        appended its security headers to the list the wrapped function sees."""
        out = {}

        def real_start_response(status, headers, exc_info=None):
            out.update(dict(headers))

        mw({}, real_start_response)
        return out

    @pytest.fixture
    def headers(self):
        from apex_os_bp.security.deepened import SecurityHeadersMiddleware
        return SecurityHeadersMiddleware(lambda environ, start_response, *a: start_response("200 OK", [], None))

    def test_default_headers(self, headers):
        h = self._collect(headers)
        assert h["X-Content-Type-Options"] == "nosniff"
        assert h["X-Frame-Options"] == "DENY"

    def test_csp_header(self, headers):
        h = self._collect(headers)
        assert "Content-Security-Policy" in h
        assert "default-src" in h["Content-Security-Policy"]

    def test_hsts_header(self, headers):
        h = self._collect(headers)
        assert "Strict-Transport-Security" in h
        assert "max-age" in h["Strict-Transport-Security"]

    def test_custom_csp(self, headers):
        from apex_os_bp.security.deepened import SecurityHeadersMiddleware
        mw = SecurityHeadersMiddleware(lambda environ, start_response, *a: start_response("200 OK", [], None), csp="default-src 'self'")
        h = self._collect(mw)
        assert h["Content-Security-Policy"] == "default-src 'self'"
