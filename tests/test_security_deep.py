"""Tests for the deepened security module."""

import base64
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.security import (
    JWTManager, TokenExpiredError, TokenInvalidError,
    RBACManager, Permission, Role, PermissionDeniedError,
    AuditLogger, AuditAction, AuditSeverity,
    EncryptionManager, DecryptionError,
    RateLimiter, RateLimitConfig, RateLimitExceeded,
)


class TestJWTManager(unittest.TestCase):
    """Tests for JWT token management."""

    def setUp(self):
        self.jwt = JWTManager(secret_key="test-secret-key-12345")

    def test_create_token(self):
        token = self.jwt.create_token("user1", roles=["admin"])
        self.assertIsInstance(token, str)
        parts = token.split(".")
        self.assertEqual(len(parts), 3)

    def test_verify_valid_token(self):
        token = self.jwt.create_token("user1", roles=["admin"], permissions=["read"])
        payload = self.jwt.verify_token(token)
        self.assertEqual(payload["sub"], "user1")
        self.assertIn("admin", payload["roles"])
        self.assertIn("read", payload["permissions"])
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)

    def test_verify_invalid_signature(self):
        token = self.jwt.create_token("user1")
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalidsignature"
        with self.assertRaises(TokenInvalidError):
            self.jwt.verify_token(tampered)

    def test_verify_expired_token(self):
        token = self.jwt.create_token("user1", expires_in=-1)
        with self.assertRaises(TokenExpiredError):
            self.jwt.verify_token(token)

    def test_verify_malformed_token(self):
        with self.assertRaises(TokenInvalidError):
            self.jwt.verify_token("not.a.valid.token")
        with self.assertRaises(TokenInvalidError):
            self.jwt.verify_token("invalid")

    def test_refresh_token(self):
        token = self.jwt.create_token("user1", roles=["user"])
        new_token = self.jwt.refresh_token(token)
        payload = self.jwt.verify_token(new_token)
        self.assertEqual(payload["sub"], "user1")
        self.assertIn("user", payload["roles"])

    def test_token_with_additional_claims(self):
        token = self.jwt.create_token(
            "user1", additional_claims={"email": "test@example.com"}
        )
        payload = self.jwt.verify_token(token)
        self.assertEqual(payload["email"], "test@example.com")

    def test_different_secret_keys(self):
        jwt1 = JWTManager(secret_key="key1")
        jwt2 = JWTManager(secret_key="key2")
        token = jwt1.create_token("user1")
        with self.assertRaises(TokenInvalidError):
            jwt2.verify_token(token)

    def test_decode_without_verification(self):
        token = self.jwt.create_token("user1", roles=["admin"])
        payload = self.jwt.decode_without_verification(token)
        self.assertEqual(payload["sub"], "user1")

    def test_unsupported_algorithm(self):
        with self.assertRaises(ValueError):
            JWTManager(secret_key="key", algorithm="RS256")


class TestRBAC(unittest.TestCase):
    """Tests for role-based access control."""

    def setUp(self):
        self.rbac = RBACManager()

    def test_admin_has_all_permissions(self):
        for perm in Permission:
            self.assertTrue(self.rbac.has_permission(["admin"], perm))

    def test_viewer_limited_permissions(self):
        self.assertTrue(self.rbac.has_permission(["viewer"], Permission.READ))
        self.assertFalse(self.rbac.has_permission(["viewer"], Permission.WRITE))
        self.assertFalse(self.rbac.has_permission(["viewer"], Permission.DELETE))

    def test_user_permissions(self):
        self.assertTrue(self.rbac.has_permission(["user"], Permission.READ))
        self.assertTrue(self.rbac.has_permission(["user"], Permission.WRITE))
        self.assertFalse(self.rbac.has_permission(["user"], Permission.DELETE))
        self.assertFalse(self.rbac.has_permission(["user"], Permission.ADMIN))

    def test_multiple_roles(self):
        roles = ["viewer", "user"]
        self.assertTrue(self.rbac.has_permission(roles, Permission.READ))
        self.assertTrue(self.rbac.has_permission(roles, Permission.WRITE))
        self.assertFalse(self.rbac.has_permission(roles, Permission.ADMIN))

    def test_has_any_permission(self):
        self.assertTrue(
            self.rbac.has_any_permission(["user"], [Permission.WRITE, Permission.DELETE])
        )
        self.assertFalse(
            self.rbac.has_any_permission(["viewer"], [Permission.WRITE, Permission.DELETE])
        )

    def test_has_all_permissions(self):
        self.assertTrue(
            self.rbac.has_all_permissions(["admin"], [Permission.READ, Permission.WRITE])
        )
        self.assertFalse(
            self.rbac.has_all_permissions(["user"], [Permission.READ, Permission.ADMIN])
        )

    def test_custom_role(self):
        self.rbac.add_custom_role("auditor", [Permission.READ, Permission.AUDIT_READ])
        self.assertTrue(self.rbac.has_permission(["auditor"], Permission.READ))
        self.assertTrue(self.rbac.has_permission(["auditor"], Permission.AUDIT_READ))
        self.assertFalse(self.rbac.has_permission(["auditor"], Permission.WRITE))

    def test_remove_custom_role(self):
        self.rbac.add_custom_role("temp", [Permission.READ])
        self.assertTrue(self.rbac.has_permission(["temp"], Permission.READ))
        self.rbac.remove_custom_role("temp")
        self.assertFalse(self.rbac.has_permission(["temp"], Permission.READ))

    def test_get_permissions(self):
        perms = self.rbac.get_permissions(["admin"])
        self.assertIn(Permission.ADMIN, perms)
        self.assertIn(Permission.READ, perms)

    def test_require_permission_decorator(self):
        @self.rbac.require_permission(Permission.ADMIN)
        def admin_only(roles):
            return "success"

        self.assertEqual(admin_only(roles=["admin"]), "success")
        with self.assertRaises(PermissionDeniedError):
            admin_only(roles=["user"])

    def test_require_permission_decorator_with_dict(self):
        @self.rbac.require_permission(Permission.READ)
        def read_data(user):
            return "data"

        self.assertEqual(read_data({"roles": ["viewer"]}), "data")
        with self.assertRaises(PermissionDeniedError):
            read_data({"roles": []})


class TestAuditLogger(unittest.TestCase):
    """Tests for audit logging."""

    def setUp(self):
        self.logger = AuditLogger()

    def test_log_event(self):
        event = self.logger.log("user1", AuditAction.LOGIN, "auth")
        self.assertEqual(event.user_id, "user1")
        self.assertEqual(event.action, "login")
        self.assertEqual(event.resource, "auth")
        self.assertTrue(event.success)

    def test_get_events_by_user(self):
        self.logger.log("user1", AuditAction.LOGIN, "auth")
        self.logger.log("user2", AuditAction.LOGOUT, "auth")
        self.logger.log("user1", AuditAction.DATA_READ, "data")

        events = self.logger.get_events(user_id="user1")
        self.assertEqual(len(events), 2)

    def test_get_events_by_action(self):
        self.logger.log("user1", AuditAction.LOGIN, "auth")
        self.logger.log("user2", AuditAction.LOGOUT, "auth")

        events = self.logger.get_events(action="login")
        self.assertEqual(len(events), 1)

    def test_get_events_with_limit(self):
        for i in range(10):
            self.logger.log(f"user{i}", AuditAction.LOGIN, "auth")
        events = self.logger.get_events(limit=5)
        self.assertEqual(len(events), 5)

    def test_clear(self):
        self.logger.log("user1", AuditAction.LOGIN, "auth")
        self.assertEqual(self.logger.count(), 1)
        self.logger.clear()
        self.assertEqual(self.logger.count(), 0)

    def test_max_events_eviction(self):
        logger = AuditLogger(max_events=5)
        for i in range(10):
            logger.log(f"user{i}", AuditAction.LOGIN, "auth")
        self.assertEqual(logger.count(), 5)

    def test_to_dict(self):
        self.logger.log(
            "user1", AuditAction.LOGIN, "auth", details={"ip": "127.0.0.1"}
        )
        dicts = self.logger.to_dict()
        self.assertEqual(len(dicts), 1)
        self.assertEqual(dicts[0]["user_id"], "user1")
        self.assertEqual(dicts[0]["details"]["ip"], "127.0.0.1")

    def test_severity_filter(self):
        self.logger.log(
            "user1", AuditAction.ACCESS_DENIED, "resource",
            severity=AuditSeverity.WARNING,
        )
        events = self.logger.get_events(severity="warning")
        self.assertEqual(len(events), 1)

    def test_to_json(self):
        self.logger.log("user1", AuditAction.LOGIN, "auth")
        json_str = self.logger.to_json()
        self.assertIn("user1", json_str)
        self.assertIn("login", json_str)


class TestEncryptionManager(unittest.TestCase):
    """Tests for encryption at rest."""

    def setUp(self):
        self.enc = EncryptionManager(master_key="super-secret-master-key")

    def test_encrypt_decrypt(self):
        plaintext = "Hello, World!"
        ciphertext = self.enc.encrypt(plaintext)
        self.assertNotEqual(ciphertext, plaintext)
        decrypted = self.enc.decrypt(ciphertext)
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_bytes(self):
        plaintext = b"binary data \x00\x01\x02"
        ciphertext = self.enc.encrypt(plaintext)
        decrypted = self.enc.decrypt(ciphertext)
        self.assertEqual(decrypted, plaintext.decode("utf-8"))

    def test_different_keys_produce_different_ciphertexts(self):
        enc1 = EncryptionManager(master_key="key1")
        enc2 = EncryptionManager(master_key="key2")
        plaintext = "secret"
        ct1 = enc1.encrypt(plaintext)
        ct2 = enc2.encrypt(plaintext)
        self.assertNotEqual(ct1, ct2)

    def test_same_plaintext_different_ciphertext(self):
        plaintext = "same text"
        ct1 = self.enc.encrypt(plaintext)
        ct2 = self.enc.encrypt(plaintext)
        self.assertNotEqual(ct1, ct2)

    def test_decrypt_with_wrong_key(self):
        enc1 = EncryptionManager(master_key="key1")
        enc2 = EncryptionManager(master_key="key2")
        ciphertext = enc1.encrypt("secret")
        with self.assertRaises(DecryptionError):
            enc2.decrypt(ciphertext)

    def test_decrypt_tampered_ciphertext(self):
        ciphertext = self.enc.encrypt("secret")
        data = bytearray(base64.b64decode(ciphertext))
        data[-1] ^= 0xFF
        tampered = base64.b64encode(bytes(data)).decode("ascii")
        with self.assertRaises(DecryptionError):
            self.enc.decrypt(tampered)

    def test_decrypt_invalid_base64(self):
        with self.assertRaises(DecryptionError):
            self.enc.decrypt("not-valid-base64!!!")

    def test_encrypt_decrypt_dict(self):
        data = {"username": "admin", "password": "secret123"}
        ciphertext = self.enc.encrypt_dict(data)
        decrypted = self.enc.decrypt_dict(ciphertext)
        self.assertEqual(decrypted, data)

    def test_unicode(self):
        plaintext = "Hello 世界 🌍"
        ciphertext = self.enc.encrypt(plaintext)
        decrypted = self.enc.decrypt(ciphertext)
        self.assertEqual(decrypted, plaintext)

    def test_empty_string(self):
        plaintext = ""
        ciphertext = self.enc.encrypt(plaintext)
        decrypted = self.enc.decrypt(ciphertext)
        self.assertEqual(decrypted, plaintext)

    def test_long_text(self):
        plaintext = "A" * 10000
        ciphertext = self.enc.encrypt(plaintext)
        decrypted = self.enc.decrypt(ciphertext)
        self.assertEqual(decrypted, plaintext)


class TestRateLimiter(unittest.TestCase):
    """Tests for per-user rate limiting."""

    def setUp(self):
        self.config = RateLimitConfig(max_requests=5, window_seconds=1.0)
        self.limiter = RateLimiter(self.config)

    def test_allow_within_limit(self):
        for _ in range(5):
            allowed, _ = self.limiter.allow_request("user1")
            self.assertTrue(allowed)

    def test_deny_over_limit(self):
        for _ in range(5):
            self.limiter.allow_request("user1")
        allowed, retry_after = self.limiter.allow_request("user1")
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_check_rate_limit_raises(self):
        for _ in range(5):
            self.limiter.check_rate_limit("user1")
        with self.assertRaises(RateLimitExceeded):
            self.limiter.check_rate_limit("user1")

    def test_per_user_isolation(self):
        for _ in range(5):
            self.limiter.allow_request("user1")
        allowed, _ = self.limiter.allow_request("user2")
        self.assertTrue(allowed)

    def test_window_expires(self):
        for _ in range(5):
            self.limiter.allow_request("user1")
        allowed, _ = self.limiter.allow_request("user1")
        self.assertFalse(allowed)
        time.sleep(1.1)
        allowed, _ = self.limiter.allow_request("user1")
        self.assertTrue(allowed)

    def test_get_remaining(self):
        self.assertEqual(self.limiter.get_remaining("user1"), 5)
        self.limiter.allow_request("user1")
        self.assertEqual(self.limiter.get_remaining("user1"), 4)

    def test_reset_user(self):
        for _ in range(5):
            self.limiter.allow_request("user1")
        self.limiter.reset("user1")
        allowed, _ = self.limiter.allow_request("user1")
        self.assertTrue(allowed)

    def test_reset_all(self):
        for _ in range(5):
            self.limiter.allow_request("user1")
            self.limiter.allow_request("user2")
        self.limiter.reset_all()
        self.assertEqual(self.limiter.get_remaining("user1"), 5)
        self.assertEqual(self.limiter.get_remaining("user2"), 5)

    def test_get_reset_time(self):
        now = time.time()
        self.limiter.allow_request("user1")
        reset_time = self.limiter.get_reset_time("user1")
        self.assertGreaterEqual(reset_time, now)

    def test_rate_limit_exceeded_has_retry_after(self):
        for _ in range(5):
            self.limiter.allow_request("user1")
        with self.assertRaises(RateLimitExceeded) as ctx:
            self.limiter.check_rate_limit("user1")
        self.assertGreater(ctx.exception.retry_after, 0)


if __name__ == "__main__":
    unittest.main()
