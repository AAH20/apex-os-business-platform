"""Tenant security — RBAC, encryption, API keys, and security policies."""

from __future__ import annotations

import enum
import hashlib
import hmac
import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from apex_os_bp.multitenancy.models import (
    AuditLog,
    TenantPermission,
    TenantRole,
    TenantUser,
)

logger = logging.getLogger(__name__)


class TenantRBAC:
    """Role-Based Access Control scoped to tenants."""

    # Role-to-permissions mapping
    ROLE_PERMISSIONS: dict[TenantRole, set[TenantPermission]] = {
        TenantRole.OWNER: set(TenantPermission),
        TenantRole.ADMIN: {
            TenantPermission.READ,
            TenantPermission.WRITE,
            TenantPermission.DELETE,
            TenantPermission.MANAGE_USERS,
            TenantPermission.MANAGE_SETTINGS,
            TenantPermission.VIEW_AUDIT_LOG,
            TenantPermission.MANAGE_API_KEYS,
        },
        TenantRole.MEMBER: {
            TenantPermission.READ,
            TenantPermission.WRITE,
        },
        TenantRole.VIEWER: {
            TenantPermission.READ,
        },
    }

    def __init__(self) -> None:
        self._user_roles: dict[str, dict[str, TenantRole]] = {}  # tenant_id -> {user_id -> role}
        self._custom_permissions: dict[str, dict[str, set[TenantPermission]]] = {}

    def assign_role(
        self, tenant_id: str, user_id: str, role: TenantRole
    ) -> bool:
        """Assign a role to a user within a tenant."""
        if tenant_id not in self._user_roles:
            self._user_roles[tenant_id] = {}
        self._user_roles[tenant_id][user_id] = role
        logger.info(
            "Assigned role %s to user %s in tenant %s",
            role.value,
            user_id,
            tenant_id,
        )
        return True

    def get_role(self, tenant_id: str, user_id: str) -> Optional[TenantRole]:
        """Get the role of a user in a tenant."""
        return self._user_roles.get(tenant_id, {}).get(user_id)

    def get_permissions(self, tenant_id: str, user_id: str) -> set[TenantPermission]:
        """Get all permissions for a user in a tenant."""
        role = self.get_role(tenant_id, user_id)
        if role is None:
            return set()

        permissions = set(self.ROLE_PERMISSIONS.get(role, set()))

        # Add custom permissions
        custom = self._custom_permissions.get(tenant_id, {}).get(user_id, set())
        permissions.update(custom)

        return permissions

    def has_permission(
        self, tenant_id: str, user_id: str, permission: TenantPermission
    ) -> bool:
        """Check if a user has a specific permission in a tenant."""
        return permission in self.get_permissions(tenant_id, user_id)

    def has_any_permission(
        self, tenant_id: str, user_id: str, permissions: set[TenantPermission]
    ) -> bool:
        """Check if a user has any of the specified permissions."""
        user_perms = self.get_permissions(tenant_id, user_id)
        return bool(user_perms & permissions)

    def has_all_permissions(
        self, tenant_id: str, user_id: str, permissions: set[TenantPermission]
    ) -> bool:
        """Check if a user has all of the specified permissions."""
        user_perms = self.get_permissions(tenant_id, user_id)
        return permissions.issubset(user_perms)

    def grant_permission(
        self, tenant_id: str, user_id: str, permission: TenantPermission
    ) -> bool:
        """Grant a custom permission to a user beyond their role."""
        if tenant_id not in self._custom_permissions:
            self._custom_permissions[tenant_id] = {}
        if user_id not in self._custom_permissions[tenant_id]:
            self._custom_permissions[tenant_id][user_id] = set()
        self._custom_permissions[tenant_id][user_id].add(permission)
        return True

    def revoke_permission(
        self, tenant_id: str, user_id: str, permission: TenantPermission
    ) -> bool:
        """Revoke a custom permission from a user."""
        custom = self._custom_permissions.get(tenant_id, {}).get(user_id, set())
        if permission in custom:
            custom.remove(permission)
            return True
        return False

    def remove_user(self, tenant_id: str, user_id: str) -> bool:
        """Remove a user from a tenant entirely."""
        roles = self._user_roles.get(tenant_id, {})
        if user_id in roles:
            del roles[user_id]
            self._custom_permissions.get(tenant_id, {}).pop(user_id, None)
            return True
        return False

    def list_users(self, tenant_id: str) -> dict[str, TenantRole]:
        """List all users and their roles in a tenant."""
        return dict(self._user_roles.get(tenant_id, {}))


class TenantEncryption:
    """Per-tenant encryption key management."""

    def __init__(self) -> None:
        self._keys: dict[str, dict[str, Any]] = {}  # tenant_id -> key_data

    def generate_key(self, tenant_id: str) -> str:
        """Generate a new encryption key for a tenant."""
        key_id = str(uuid.uuid4())
        key_material = secrets.token_bytes(32)  # 256-bit key

        self._keys[tenant_id] = {
            "key_id": key_id,
            "key_material": key_material,
            "created_at": datetime.utcnow(),
            "algorithm": "AES-256-GCM",
            "rotation_due": datetime.utcnow() + timedelta(days=90),
        }

        logger.info("Generated encryption key %s for tenant %s", key_id, tenant_id)
        return key_id

    def get_key(self, tenant_id: str) -> Optional[dict[str, Any]]:
        """Get the encryption key for a tenant."""
        return self._keys.get(tenant_id)

    def get_key_material(self, tenant_id: str) -> Optional[bytes]:
        """Get the raw key material for a tenant."""
        key_data = self._keys.get(tenant_id)
        if key_data:
            return key_data["key_material"]  # type: ignore[return-value]
        return None

    def rotate_key(self, tenant_id: str) -> Optional[str]:
        """Rotate the encryption key for a tenant."""
        if tenant_id not in self._keys:
            return None

        old_key = self._keys[tenant_id]
        new_key_id = str(uuid.uuid4())
        new_key_material = secrets.token_bytes(32)

        self._keys[tenant_id] = {
            "key_id": new_key_id,
            "key_material": new_key_material,
            "created_at": datetime.utcnow(),
            "algorithm": "AES-256-GCM",
            "rotation_due": datetime.utcnow() + timedelta(days=90),
            "previous_key_id": old_key["key_id"],
        }

        logger.info(
            "Rotated encryption key for tenant %s: %s -> %s",
            tenant_id,
            old_key["key_id"],
            new_key_id,
        )
        return new_key_id

    def needs_rotation(self, tenant_id: str) -> bool:
        """Check if a tenant's key needs rotation."""
        key_data = self._keys.get(tenant_id)
        if not key_data:
            return True
        return datetime.utcnow() >= key_data.get(
            "rotation_due", datetime.utcnow()
        )

    def encrypt(self, tenant_id: str, plaintext: bytes) -> Optional[bytes]:
        """Encrypt data using the tenant's key.

        In production, this would use a proper encryption library.
        This is a simplified implementation for demonstration.
        """
        key_material = self.get_key_material(tenant_id)
        if key_material is None:
            return None

        # Simplified XOR-based encryption for demonstration
        # DO NOT use in production — use cryptography.fernet or similar
        key_hash = hashlib.sha256(key_material).digest()
        encrypted = bytes(
            b ^ key_hash[i % len(key_hash)] for i, b in enumerate(plaintext)
        )
        return encrypted

    def decrypt(self, tenant_id: str, ciphertext: bytes) -> Optional[bytes]:
        """Decrypt data using the tenant's key."""
        # XOR is symmetric, so encrypt == decrypt
        return self.encrypt(tenant_id, ciphertext)


@dataclass
class TenantAPIKey:
    """An API key for a tenant."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    name: str = ""
    key_hash: str = ""
    prefix: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    scopes: list[str] = field(default_factory=list)


class TenantAPIKeyManager:
    """Manages API keys for tenants."""

    KEY_PREFIX = "apk_"
    KEY_LENGTH = 32

    def __init__(self) -> None:
        self._keys: dict[str, list[TenantAPIKey]] = {}  # tenant_id -> [keys]
        self._key_lookup: dict[str, str] = {}  # key_hash -> tenant_id

    def create_key(
        self,
        tenant_id: str,
        name: str = "",
        scopes: Optional[list[str]] = None,
        expires_in_days: Optional[int] = 365,
    ) -> tuple[str, TenantAPIKey]:
        """Create a new API key for a tenant.

        Returns:
            Tuple of (plain_text_key, TenantAPIKey).
            The plain text key is shown only once.
        """
        plain_key = self.KEY_PREFIX + secrets.token_urlsafe(self.KEY_LENGTH)
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        prefix = plain_key[:12]

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = TenantAPIKey(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name or "API Key",
            key_hash=key_hash,
            prefix=prefix,
            expires_at=expires_at,
            scopes=scopes or ["read"],
        )

        if tenant_id not in self._keys:
            self._keys[tenant_id] = []
        self._keys[tenant_id].append(api_key)
        self._key_lookup[key_hash] = tenant_id

        logger.info("Created API key %s for tenant %s", api_key.id, tenant_id)
        return plain_key, api_key

    def validate_key(self, plain_key: str) -> Optional[TenantAPIKey]:
        """Validate an API key and return it if valid."""
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        tenant_id = self._key_lookup.get(key_hash)
        if tenant_id is None:
            return None

        for api_key in self._keys.get(tenant_id, []):
            if api_key.key_hash == key_hash:
                if not api_key.is_active:
                    return None
                if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
                    return None
                api_key.last_used_at = datetime.utcnow()
                return api_key
        return None

    def revoke_key(self, tenant_id: str, key_id: str) -> bool:
        """Revoke an API key."""
        keys = self._keys.get(tenant_id, [])
        for key in keys:
            if key.id == key_id:
                key.is_active = False
                logger.info("Revoked API key %s for tenant %s", key_id, tenant_id)
                return True
        return False

    def list_keys(self, tenant_id: str) -> list[TenantAPIKey]:
        """List all API keys for a tenant."""
        return list(self._keys.get(tenant_id, []))

    def delete_key(self, tenant_id: str, key_id: str) -> bool:
        """Permanently delete an API key."""
        keys = self._keys.get(tenant_id, [])
        for i, key in enumerate(keys):
            if key.id == key_id:
                keys.pop(i)
                self._key_lookup.pop(key.key_hash, None)
                return True
        return False


@dataclass
class SecurityPolicy:
    """Security policies for a tenant."""

    tenant_id: str = ""
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_special: bool = True
    session_timeout_minutes: int = 60
    max_failed_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    require_mfa: bool = False
    allowed_ip_ranges: list[str] = field(default_factory=list)
    enforce_ip_whitelist: bool = False
    audit_log_retention_days: int = 365
    data_retention_days: int = 2555  # 7 years
    encryption_at_rest: bool = True
    encryption_in_transit: bool = True

    def validate_password(self, password: str) -> tuple[bool, list[str]]:
        """Validate a password against the policy."""
        errors: list[str] = []

        if len(password) < self.password_min_length:
            errors.append(
                f"Password must be at least {self.password_min_length} characters"
            )
        if self.password_require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        if self.password_require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        if self.password_require_numbers and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        if self.password_require_special and not any(
            c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password
        ):
            errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors

    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if an IP address is allowed by the policy."""
        if not self.enforce_ip_whitelist:
            return True
        # Simplified IP range check
        import ipaddress

        try:
            ip = ipaddress.ip_address(ip_address)
            for range_str in self.allowed_ip_ranges:
                if ip in ipaddress.ip_network(range_str, strict=False):
                    return True
        except ValueError:
            return False
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "password_min_length": self.password_min_length,
            "password_require_uppercase": self.password_require_uppercase,
            "password_require_lowercase": self.password_require_lowercase,
            "password_require_numbers": self.password_require_numbers,
            "password_require_special": self.password_require_special,
            "session_timeout_minutes": self.session_timeout_minutes,
            "max_failed_login_attempts": self.max_failed_login_attempts,
            "lockout_duration_minutes": self.lockout_duration_minutes,
            "require_mfa": self.require_mfa,
            "allowed_ip_ranges": self.allowed_ip_ranges,
            "enforce_ip_whitelist": self.enforce_ip_whitelist,
            "audit_log_retention_days": self.audit_log_retention_days,
            "data_retention_days": self.data_retention_days,
            "encryption_at_rest": self.encryption_at_rest,
            "encryption_in_transit": self.encryption_in_transit,
        }


class TenantAuditLogger:
    """Audit logging for tenant-scoped actions."""

    def __init__(self) -> None:
        self._logs: dict[str, list[AuditLog]] = {}

    def log(
        self,
        tenant_id: str,
        action: str,
        user_id: Optional[str] = None,
        resource_type: str = "",
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        entry = AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            timestamp=datetime.utcnow(),
        )

        if tenant_id not in self._logs:
            self._logs[tenant_id] = []
        self._logs[tenant_id].append(entry)

        logger.debug(
            "Audit log: %s by %s on %s/%s in tenant %s",
            action,
            user_id,
            resource_type,
            resource_id,
            tenant_id,
        )
        return entry

    def get_logs(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Query audit logs for a tenant."""
        logs = self._logs.get(tenant_id, [])

        if user_id:
            logs = [l for l in logs if l.user_id == user_id]
        if action:
            logs = [l for l in logs if l.action == action]
        if resource_type:
            logs = [l for l in logs if l.resource_type == resource_type]
        if since:
            logs = [l for l in logs if l.timestamp >= since]

        return sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]

    def clear(self, tenant_id: str) -> None:
        """Clear all audit logs for a tenant."""
        self._logs.pop(tenant_id, None)
