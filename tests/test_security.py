"""Tests for security module."""
import pytest
from apex_os_bp.security.auth import Authenticator, User, Permission, Role
from apex_os_bp.security.vault import SecretVault


class TestUser:
    """Test user data structure."""

    def test_user_creation(self):
        """User can be created."""
        user = User(id="u-1", username="testuser", email="test@example.com")
        assert user.id == "u-1"
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_user_with_roles(self):
        """User supports roles."""
        user = User(id="u-1", username="testuser", email="test@example.com", roles=["admin"])
        assert "admin" in user.roles


class TestPermission:
    """Test permission data structure."""

    def test_permission_creation(self):
        """Permission can be created."""
        perm = Permission(resource="invoice", action="read")
        assert perm.resource == "invoice"
        assert perm.action == "read"


class TestRole:
    """Test role data structure."""

    def test_role_creation(self):
        """Role can be created."""
        role = Role(name="admin", permissions=[Permission(resource="*", action="*")])
        assert role.name == "admin"
        assert len(role.permissions) == 1


class TestAuthenticator:
    """Test authenticator."""

    def test_register_user(self):
        """User can be registered."""
        auth = Authenticator()
        user = auth.register("testuser", "test@example.com", "password123")
        assert user.username == "testuser"

    def test_authenticate_success(self):
        """User can authenticate with correct password."""
        auth = Authenticator()
        auth.register("testuser", "test@example.com", "password123")
        result = auth.authenticate("testuser", "password123")
        assert result is not None
        assert result.username == "testuser"

    def test_authenticate_failure(self):
        """Authentication fails with wrong password."""
        auth = Authenticator()
        auth.register("testuser", "test@example.com", "password123")
        result = auth.authenticate("testuser", "wrongpassword")
        assert result is None

    def test_authorize_success(self):
        """User with permission is authorized."""
        auth = Authenticator()
        user = auth.register("admin", "admin@example.com", "password123")
        auth.assign_role(user.id, "admin")
        assert auth.authorize(user.id, "invoice", "read")

    def test_authorize_failure(self):
        """User without permission is not authorized."""
        auth = Authenticator()
        user = auth.register("user", "user@example.com", "password123")
        assert not auth.authorize(user.id, "invoice", "read")


class TestSecretVault:
    """Test secret vault."""

    def test_store_secret(self):
        """Secret can be stored."""
        vault = SecretVault()
        vault.store("db_password", "secret123")
        assert vault.get("db_password") == "secret123"

    def test_get_missing_secret(self):
        """Missing secret returns None."""
        vault = SecretVault()
        assert vault.get("nonexistent") is None

    def test_delete_secret(self):
        """Secret can be deleted."""
        vault = SecretVault()
        vault.store("db_password", "secret123")
        vault.delete("db_password")
        assert vault.get("db_password") is None

    def test_list_secrets(self):
        """Secrets can be listed."""
        vault = SecretVault()
        vault.store("key1", "value1")
        vault.store("key2", "value2")
        keys = vault.list_keys()
        assert "key1" in keys
        assert "key2" in keys
