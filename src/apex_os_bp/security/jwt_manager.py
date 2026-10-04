"""JWT token management for APEX-OS Business Platform."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional


class JWTError(Exception):
    """Base exception for JWT errors."""


class TokenExpiredError(JWTError):
    """Raised when a token has expired."""


class TokenInvalidError(JWTError):
    """Raised when a token is invalid."""


class JWTManager:
    """Manages JWT token creation, verification, and refresh.

    Implements HS256 (HMAC-SHA256) signed tokens using only the Python
    standard library. Tokens carry standard claims (sub, iat, exp) plus
    custom claims for roles and permissions.
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256", default_expiry: int = 3600):
        """Initialize the JWT manager.

        Args:
            secret_key: Secret key used for signing tokens.
            algorithm: Signing algorithm (only HS256 supported).
            default_expiry: Default token lifetime in seconds.
        """
        if algorithm != "HS256":
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        self._secret_key = secret_key.encode("utf-8")
        self._algorithm = algorithm
        self._default_expiry = default_expiry

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        """Base64url encode without padding."""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        """Base64url decode, restoring padding if needed."""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data.encode("ascii"))

    def _sign(self, message: bytes) -> bytes:
        """Create HMAC-SHA256 signature."""
        return hmac.new(self._secret_key, message, hashlib.sha256).digest()

    def create_token(
        self,
        user_id: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        expires_in: Optional[int] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new JWT token.

        Args:
            user_id: Subject identifier (user ID).
            roles: List of role names for the user.
            permissions: List of permission strings.
            expires_in: Token lifetime in seconds (overrides default).
            additional_claims: Extra claims to include in the payload.

        Returns:
            Encoded JWT token string.
        """
        now = int(time.time())
        exp = now + (expires_in if expires_in is not None else self._default_expiry)

        header = {"alg": self._algorithm, "typ": "JWT"}
        payload: Dict[str, Any] = {
            "sub": user_id,
            "iat": now,
            "exp": exp,
            "roles": roles or [],
            "permissions": permissions or [],
        }
        if additional_claims:
            payload.update(additional_claims)

        header_b64 = self._base64url_encode(
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        payload_b64 = self._base64url_encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )

        message = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = self._sign(message)

        return f"{header_b64}.{payload_b64}.{self._base64url_encode(signature)}"

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token.

        Args:
            token: The JWT token string to verify.

        Returns:
            Decoded payload dictionary.

        Raises:
            TokenInvalidError: If the token is malformed or signature is invalid.
            TokenExpiredError: If the token has expired.
        """
        parts = token.split(".")
        if len(parts) != 3:
            raise TokenInvalidError("Invalid token format: expected 3 parts")

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        try:
            message = f"{header_b64}.{payload_b64}".encode("ascii")
            expected_sig = self._sign(message)
            actual_sig = self._base64url_decode(signature_b64)
        except Exception as e:
            raise TokenInvalidError(f"Invalid token encoding: {e}")

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise TokenInvalidError("Invalid token signature")

        # Decode payload
        try:
            payload = json.loads(self._base64url_decode(payload_b64))
        except Exception as e:
            raise TokenInvalidError(f"Invalid payload encoding: {e}")

        # Check expiration
        if "exp" in payload and payload["exp"] < time.time():
            raise TokenExpiredError("Token has expired")

        return payload

    def refresh_token(self, token: str, expires_in: Optional[int] = None) -> str:
        """Refresh a valid token, issuing a new one with updated expiry.

        Args:
            token: The current valid token.
            expires_in: New lifetime in seconds (overrides default).

        Returns:
            New JWT token string.
        """
        payload = self.verify_token(token)
        return self.create_token(
            user_id=payload["sub"],
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            expires_in=expires_in,
        )

    def decode_without_verification(self, token: str) -> Dict[str, Any]:
        """Decode token payload without verifying signature (for debugging only).

        Args:
            token: The JWT token string.

        Returns:
            Decoded payload dictionary.
        """
        parts = token.split(".")
        if len(parts) != 3:
            raise TokenInvalidError("Invalid token format")
        return json.loads(self._base64url_decode(parts[1]))
