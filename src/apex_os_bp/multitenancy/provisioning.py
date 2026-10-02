"""Tenant provisioning — create, initialise, and manage tenant lifecycles."""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from apex_os_bp.multitenancy.isolation import TenantContext, set_current_tenant
from apex_os_bp.multitenancy.models import (
    Tenant,
    TenantPlan,
    TenantStatus,
    TenantUser,
    TenantRole,
    TenantPermission,
    AuditLog,
)

logger = logging.getLogger(__name__)


@dataclass
class ProvisioningResult:
    """Result of a tenant provisioning operation."""

    success: bool
    tenant: Optional[Tenant] = None
    admin_user: Optional[TenantUser] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_resources: list[str] = field(default_factory=list)


class TenantProvisioner:
    """Handles the full lifecycle of tenant provisioning.

    Responsibilities:
    - Create tenant records
    - Allocate resources (storage, compute, API quota)
    - Create initial admin user
    - Set up encryption keys
    - Initialize default settings
    - Run post-provisioning hooks
    """

    # Plan limits
    PLAN_LIMITS: dict[TenantPlan, dict[str, int]] = {
        TenantPlan.FREE: {
            "max_users": 5,
            "max_storage_bytes": 1_073_741_824,  # 1 GB
            "max_api_calls_per_month": 10_000,
        },
        TenantPlan.STARTER: {
            "max_users": 20,
            "max_storage_bytes": 10_737_418_240,  # 10 GB
            "max_api_calls_per_month": 100_000,
        },
        TenantPlan.PROFESSIONAL: {
            "max_users": 100,
            "max_storage_bytes": 107_374_182_400,  # 100 GB
            "max_api_calls_per_month": 1_000_000,
        },
        TenantPlan.ENTERPRISE: {
            "max_users": 10_000,
            "max_storage_bytes": 1_099_511_627_776,  # 1 TB
            "max_api_calls_per_month": 100_000_000,
        },
    }

    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._users: dict[str, list[TenantUser]] = {}
        self._audit_logs: list[AuditLog] = []

    def provision(
        self,
        name: str,
        slug: str,
        plan: TenantPlan = TenantPlan.FREE,
        admin_email: str = "",
        admin_name: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> ProvisioningResult:
        """Provision a new tenant with all required resources.

        Args:
            name: Human-readable tenant name.
            slug: URL-safe unique identifier.
            plan: Subscription plan.
            admin_email: Email for the initial admin user.
            admin_name: Display name for the initial admin user.
            metadata: Additional tenant metadata.

        Returns:
            ProvisioningResult with details of what was created.
        """
        result = ProvisioningResult(success=False)

        # Validate inputs
        if not name or not name.strip():
            result.errors.append("Tenant name is required")
            return result

        if not slug or not slug.strip():
            result.errors.append("Tenant slug is required")
            return result

        slug = self._normalize_slug(slug)

        if self._slug_exists(slug):
            result.errors.append(f"Tenant slug '{slug}' is already taken")
            return result

        if not admin_email or "@" not in admin_email:
            result.errors.append("Valid admin email is required")
            return result

        # Create tenant
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=name.strip(),
            slug=slug,
            plan=plan,
            status=TenantStatus.ACTIVE,
            metadata=metadata or {},
            **self.PLAN_LIMITS[plan],
        )
        tenant.encryption_key_id = self._generate_encryption_key_id(tenant.id)

        # Store tenant
        self._tenants[tenant.id] = tenant
        self._users[tenant.id] = []

        # Create admin user
        admin_user = self._create_admin_user(tenant.id, admin_email, admin_name)
        self._users[tenant.id].append(admin_user)

        # Run provisioning hooks
        try:
            self._allocate_storage(tenant)
            result.created_resources.append("storage")
        except Exception as exc:
            result.warnings.append(f"Storage allocation failed: {exc}")

        try:
            self._allocate_compute(tenant)
            result.created_resources.append("compute")
        except Exception as exc:
            result.warnings.append(f"Compute allocation failed: {exc}")

        try:
            self._setup_encryption(tenant)
            result.created_resources.append("encryption")
        except Exception as exc:
            result.warnings.append(f"Encryption setup failed: {exc}")

        try:
            self._create_default_settings(tenant)
            result.created_resources.append("settings")
        except Exception as exc:
            result.warnings.append(f"Default settings creation failed: {exc}")

        # Audit log
        self._audit_logs.append(
            AuditLog(
                tenant_id=tenant.id,
                action="tenant.provisioned",
                resource_type="tenant",
                resource_id=tenant.id,
                details={"plan": plan.value, "admin_email": admin_email},
            )
        )

        result.success = True
        result.tenant = tenant
        result.admin_user = admin_user

        logger.info(
            "Tenant provisioned: %s (%s) with plan %s",
            tenant.name,
            tenant.id,
            plan.value,
        )

        return result

    def suspend(self, tenant_id: str, reason: str = "") -> bool:
        """Suspend a tenant, disabling access but preserving data."""
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return False

        tenant.status = TenantStatus.SUSPENDED
        tenant.suspended_at = datetime.utcnow()
        tenant.updated_at = datetime.utcnow()

        self._audit_logs.append(
            AuditLog(
                tenant_id=tenant_id,
                action="tenant.suspended",
                resource_type="tenant",
                resource_id=tenant_id,
                details={"reason": reason},
            )
        )

        logger.info("Tenant suspended: %s (reason: %s)", tenant_id, reason)
        return True

    def resume(self, tenant_id: str) -> bool:
        """Resume a suspended tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return False

        if tenant.status != TenantStatus.SUSPENDED:
            return False

        tenant.status = TenantStatus.ACTIVE
        tenant.suspended_at = None
        tenant.updated_at = datetime.utcnow()

        self._audit_logs.append(
            AuditLog(
                tenant_id=tenant_id,
                action="tenant.resumed",
                resource_type="tenant",
                resource_id=tenant_id,
            )
        )

        logger.info("Tenant resumed: %s", tenant_id)
        return True

    def delete(self, tenant_id: str, hard_delete: bool = False) -> bool:
        """Delete a tenant. Soft delete by default, hard delete optionally."""
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return False

        if hard_delete:
            del self._tenants[tenant_id]
            self._users.pop(tenant_id, None)
        else:
            tenant.status = TenantStatus.DELETED
            tenant.deleted_at = datetime.utcnow()
            tenant.updated_at = datetime.utcnow()

        self._audit_logs.append(
            AuditLog(
                tenant_id=tenant_id,
                action="tenant.deleted",
                resource_type="tenant",
                resource_id=tenant_id,
                details={"hard_delete": hard_delete},
            )
        )

        logger.info("Tenant deleted: %s (hard=%s)", tenant_id, hard_delete)
        return True

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Retrieve a tenant by ID."""
        return self._tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Retrieve a tenant by slug."""
        for tenant in self._tenants.values():
            if tenant.slug == slug:
                return tenant
        return None

    def list_tenants(self, status: Optional[TenantStatus] = None) -> list[Tenant]:
        """List all tenants, optionally filtered by status."""
        tenants = list(self._tenants.values())
        if status is not None:
            tenants = [t for t in tenants if t.status == status]
        return tenants

    def get_tenant_users(self, tenant_id: str) -> list[TenantUser]:
        """Get all users belonging to a tenant."""
        return list(self._users.get(tenant_id, []))

    def add_user(
        self,
        tenant_id: str,
        email: str,
        role: TenantRole = TenantRole.MEMBER,
        name: str = "",
    ) -> Optional[TenantUser]:
        """Add a user to a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return None

        users = self._users.get(tenant_id, [])
        if len(users) >= tenant.max_users:
            logger.warning(
                "Cannot add user: tenant %s at max users (%d)",
                tenant_id,
                tenant.max_users,
            )
            return None

        # Check for duplicate email
        for u in users:
            if u.email == email:
                return None

        user = TenantUser(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            email=email,
            role=role,
            permissions=self._default_permissions_for_role(role),
        )
        users.append(user)
        self._users[tenant_id] = users

        self._audit_logs.append(
            AuditLog(
                tenant_id=tenant_id,
                action="user.added",
                resource_type="user",
                resource_id=user.id,
                details={"email": email, "role": role.value},
            )
        )

        return user

    def remove_user(self, tenant_id: str, user_id: str) -> bool:
        """Remove a user from a tenant."""
        users = self._users.get(tenant_id, [])
        for i, user in enumerate(users):
            if user.id == user_id:
                users.pop(i)
                self._audit_logs.append(
                    AuditLog(
                        tenant_id=tenant_id,
                        action="user.removed",
                        resource_type="user",
                        resource_id=user_id,
                    )
                )
                return True
        return False

    def get_audit_logs(self, tenant_id: str) -> list[AuditLog]:
        """Get audit logs for a tenant."""
        return [log for log in self._audit_logs if log.tenant_id == tenant_id]

    def _normalize_slug(self, slug: str) -> str:
        """Normalize a slug to be URL-safe."""
        return slug.lower().strip().replace(" ", "-").replace("_", "-")

    def _slug_exists(self, slug: str) -> bool:
        """Check if a slug is already in use."""
        return any(t.slug == slug for t in self._tenants.values())

    def _generate_encryption_key_id(self, tenant_id: str) -> str:
        """Generate a unique encryption key ID for a tenant."""
        raw = f"{tenant_id}:{secrets.token_hex(16)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _create_admin_user(
        self, tenant_id: str, email: str, name: str
    ) -> TenantUser:
        """Create the initial admin user for a tenant."""
        return TenantUser(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            email=email,
            role=TenantRole.OWNER,
            permissions=self._default_permissions_for_role(TenantRole.OWNER),
        )

    def _default_permissions_for_role(self, role: TenantRole) -> set[TenantPermission]:
        """Get default permissions for a role."""
        if role == TenantRole.OWNER:
            return set(TenantPermission)
        elif role == TenantRole.ADMIN:
            return {
                TenantPermission.READ,
                TenantPermission.WRITE,
                TenantPermission.DELETE,
                TenantPermission.MANAGE_USERS,
                TenantPermission.MANAGE_SETTINGS,
                TenantPermission.VIEW_AUDIT_LOG,
                TenantPermission.MANAGE_API_KEYS,
            }
        elif role == TenantRole.MEMBER:
            return {TenantPermission.READ, TenantPermission.WRITE}
        else:  # VIEWER
            return {TenantPermission.READ}

    def _allocate_storage(self, tenant: Tenant) -> None:
        """Allocate storage resources for a tenant."""
        logger.debug(
            "Allocated %d bytes storage for tenant %s",
            tenant.max_storage_bytes,
            tenant.id,
        )

    def _allocate_compute(self, tenant: Tenant) -> None:
        """Allocate compute resources for a tenant."""
        logger.debug("Allocated compute resources for tenant %s", tenant.id)

    def _setup_encryption(self, tenant: Tenant) -> None:
        """Set up encryption for a tenant."""
        logger.debug(
            "Set up encryption with key %s for tenant %s",
            tenant.encryption_key_id,
            tenant.id,
        )

    def _create_default_settings(self, tenant: Tenant) -> None:
        """Create default settings for a tenant."""
        logger.debug("Created default settings for tenant %s", tenant.id)
