"""Deepened security module: JWT refresh, OAuth2, SAML SSO, ABAC, security headers."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import jwt

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = 900          # 15 minutes
REFRESH_TOKEN_TTL = 604800     # 7 days
MAX_REFRESH_ROTATIONS = 3
NONCE_TTL = 300

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class User:
    id: str
    roles: Set[str] = field(default_factory=set)
    attributes: Dict[str, Any] = field(default_factory=dict)
    mfa_enabled: bool = False


@dataclass
class SecurityContext:
    user: User
    permissions: Set[Permission] = field(default_factory=set)
    claims: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""

# ---------------------------------------------------------------------------
# 1. JWT Token Refresh with Rotation
# ---------------------------------------------------------------------------


class TokenManager:
    def __init__(self, secret: str, algorithm: str = DEFAULT_ALGORITHM):
        self._secret = secret
        self._algorithm = algorithm
        self._refresh_store: Dict[str, Dict[str, Any]] = {}
        self._rotation_count: Dict[str, int] = {}

    def issue_tokens(self, user: User, claims: Optional[Dict] = None) -> Dict[str, str]:
        now = int(time.time())
        base_claims = {"sub": user.id, "roles": list(user.roles), **(claims or {})}
        access = jwt.encode(
            {**base_claims, "iat": now, "exp": now + ACCESS_TOKEN_TTL, "type": "access"},
            self._secret, algorithm=self._algorithm,
        )
        refresh_id = secrets.token_urlsafe(32)
        refresh = jwt.encode(
            {**base_claims, "iat": now, "exp": now + REFRESH_TOKEN_TTL,
             "type": "refresh", "jti": refresh_id},
            self._secret, algorithm=self._algorithm,
        )
        self._refresh_store[refresh_id] = {
            "user_id": user.id, "issued_at": now, "rotated": False,
        }
        self._rotation_count[refresh_id] = 0
        return {"access_token": access, "refresh_token": refresh, "token_type": "Bearer"}

    def refresh(self, refresh_token: str) -> Dict[str, str]:
        try:
            payload = jwt.decode(refresh_token, self._secret,
                                 algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError:
            raise SecurityError("Refresh token expired")
        except jwt.InvalidTokenError as exc:
            raise SecurityError(f"Invalid refresh token: {exc}")
        if payload.get("type") != "refresh":
            raise SecurityError("Not a refresh token")
        jti = payload.get("jti", "")
        record = self._refresh_store.get(jti)
        if record is None:
            raise SecurityError("Refresh token revoked")
        if record.get("rotated"):
            self._revoke_family(jti)
            raise SecurityError("Refresh token reuse detected — family revoked")
        count = self._rotation_count.get(jti, 0)
        if count >= MAX_REFRESH_ROTATIONS:
            self._revoke_family(jti)
            raise SecurityError("Max rotations exceeded")
        record["rotated"] = True
        self._rotation_count[jti] = count + 1
        user = User(id=payload["sub"], roles=set(payload.get("roles", [])))
        return self.issue_tokens(user, {k: v for k, v in payload.items()
                                        if k not in {"iat", "exp", "type", "jti"}})

    def revoke(self, refresh_token: str) -> None:
        try:
            payload = jwt.decode(refresh_token, self._secret,
                                 algorithms=[self._algorithm])
            jti = payload.get("jti", "")
            self._revoke_family(jti)
        except jwt.InvalidTokenError:
            pass

    def _revoke_family(self, jti: str) -> None:
        self._refresh_store.pop(jti, None)
        self._rotation_count.pop(jti, None)

# ---------------------------------------------------------------------------
# 2. OAuth2 Authorization Code Flow
# ---------------------------------------------------------------------------


class OAuth2Provider:
    def __init__(self, token_manager: TokenManager):
        self._tm = token_manager
        self._codes: Dict[str, Dict[str, Any]] = {}
        self._clients: Dict[str, Dict[str, str]] = {}

    def register_client(self, client_id: str, redirect_uris: List[str],
                        secret: str = "") -> None:
        self._clients[client_id] = {
            "redirect_uris": redirect_uris, "secret": secret,
        }

    def create_authorization_url(self, client_id: str, redirect_uri: str,
                                 scope: str = "openid", state: Optional[str] = None,
                                 code_challenge: Optional[str] = None) -> str:
        client = self._clients.get(client_id)
        if not client or redirect_uri not in client["redirect_uris"]:
            raise SecurityError("Invalid client or redirect URI")
        code = secrets.token_urlsafe(32)
        self._codes[code] = {
            "client_id": client_id, "redirect_uri": redirect_uri,
            "scope": scope, "state": state, "code_challenge": code_challenge,
            "expires_at": time.time() + NONCE_TTL,
        }
        params = [f"code={code}", f"state={state or ''}"]
        if code_challenge:
            params.append(f"code_challenge={code_challenge}")
            params.append("code_challenge_method=S256")
        return f"{redirect_uri}?{'&'.join(params)}"

    def exchange_code(self, code: str, client_id: str,
                      code_verifier: Optional[str] = None) -> Dict[str, str]:
        record = self._codes.pop(code, None)
        if not record or record["expires_at"] < time.time():
            raise SecurityError("Invalid or expired authorization code")
        if record["client_id"] != client_id:
            raise SecurityError("Client mismatch")
        challenge = record.get("code_challenge")
        if challenge:
            if not code_verifier:
                raise SecurityError("PKCE verifier required")
            computed = hashlib.sha256(code_verifier.encode()).digest()
            import base64
            expected = base64.urlsafe_b64encode(computed).rstrip(b"=").decode()
            if not hmac.compare_digest(challenge, expected):
                raise SecurityError("PKCE verification failed")
        user = User(id=f"oauth:{client_id}")
        return self._tm.issue_tokens(user, {"scope": record["scope"]})

# ---------------------------------------------------------------------------
# 3. SAML SSO Integration
# ---------------------------------------------------------------------------


class SAMLProvider:
    def __init__(self, idp_metadata_url: str, sp_entity_id: str,
                 acs_url: str):
        self._idp_url = idp_metadata_url
        self._sp_entity_id = sp_entity_id
        self._acs_url = acs_url
        self._idp_cert: Optional[str] = None

    def create_authn_request(self, request_id: Optional[str] = None) -> str:
        rid = request_id or f"_id-{uuid.uuid4().hex}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return (
            f'<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
            f'ID="{rid}" Version="2.0" IssueInstant="{timestamp}" '
            f'Destination="{self._idp_url}" '
            f'AssertionConsumerServiceURL="{self._acs_url}">'
            f'<saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">'
            f'{self._sp_entity_id}</saml:Issuer></samlp:AuthnRequest>'
        )

    def parse_saml_response(self, saml_response_b64: str,
                            username_attr: str = "uid") -> User:
        import base64
        import xml.etree.ElementTree as ET
        try:
            decoded = base64.b64decode(saml_response_b64).decode()
            root = ET.fromstring(decoded)
        except Exception as exc:
            raise SecurityError(f"Invalid SAML response: {exc}")
        ns = {"saml": "urn:oasis:names:tc:SAML:2.0:assertion",
              "samlp": "urn:oasis:names:tc:SAML:2.0:protocol"}
        name_id = root.find(".//saml:NameID", ns)
        if name_id is None:
            raise SecurityError("SAML response missing NameID")
        user_id = name_id.text or ""
        roles: Set[str] = set()
        for attr in root.findall(".//saml:Attribute", ns):
            if attr.get("Name") == "roles":
                for val in attr.findall("saml:AttributeValue", ns):
                    if val.text:
                        roles.add(val.text)
        return User(id=user_id, roles=roles,
                    attributes={"saml_assertion_id": root.get("ID", "")})

# ---------------------------------------------------------------------------
# 4. RBAC + ABAC
# ---------------------------------------------------------------------------


class AccessControl:
    def __init__(self):
        self._role_permissions: Dict[str, Set[Permission]] = {}
        self._policies: List[Callable[[User, str, str], bool]] = []

    def assign_role(self, role: str, permissions: Set[Permission]) -> None:
        self._role_permissions[role] = permissions

    def add_abac_policy(self, policy: Callable[[User, str, str], bool]) -> None:
        self._policies.append(policy)

    def check(self, user: User, resource: str, action: str) -> bool:
        role_perms: Set[Permission] = set()
        for role in user.roles:
            role_perms |= self._role_permissions.get(role, set())
        action_perm = Permission(action)
        if action_perm in role_perms:
            return True
        return any(policy(user, resource, action) for policy in self._policies)

    def require(self, user: User, resource: str, action: str) -> None:
        if not self.check(user, resource, action):
            raise SecurityError(
                f"Access denied: {user.id} cannot {action} {resource}"
            )

# ---------------------------------------------------------------------------
# 5. Security Headers Middleware
# ---------------------------------------------------------------------------
DEFAULT_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


class SecurityHeadersMiddleware:
    def __init__(self, app: Callable, csp: str = DEFAULT_CSP,
                 hsts_max_age: int = 31536000,
                 include_subdomains: bool = True):
        self._app = app
        self._csp = csp
        self._hsts = f"max-age={hsts_max_age}"
        if include_subdomains:
            self._hsts += "; includeSubDomains"

    def __call__(self, environ: Dict, start_response: Callable) -> Any:
        def wrapped_start_response(status: str, headers: List[Tuple[str, str]],
                                     exc_info=None):
            headers.extend([
                ("Content-Security-Policy", self._csp),
                ("Strict-Transport-Security", self._hsts),
                ("X-Frame-Options", "DENY"),
                ("X-Content-Type-Options", "nosniff"),
                ("Referrer-Policy", "strict-origin-when-cross-origin"),
                ("Permissions-Policy", "geolocation=(), microphone=(), camera=()"),
                ("Cross-Origin-Opener-Policy", "same-origin"),
            ])
            return start_response(status, headers, exc_info)
        return self._app(environ, wrapped_start_response)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SecurityError(Exception):
    pass
