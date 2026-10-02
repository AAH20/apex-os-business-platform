"""Core data models for the multi-tenancy system."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional


class TenantStatus(enum.Enum):
    """Lifecycle status of a tenant."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class TenantPlan(enum.Enum):
    """Subscription plans available to tenants."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantRole(enum.Enum):
    """Roles assignable to users within a tenant."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class TenantPermission(enum.Enum):
    """Granular permissions for tenant-scoped resources."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_USERS = "manage_users"
    MANAGE_BILLING = "manage_billing"
    MANAGE_SETTINGS = "manage_settings"
    VIEW_AUDIT_LOG = "view_audit_log"
    MANAGE_API_KEYS = "manage_api_keys"


class HealthStatus(enum.Enum):
    """Health status of a tenant's services."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Tenant:
    """Represents a tenant (organisation) in the system."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slug: str = ""
    tenant_id: str = ""
    plan: TenantPlan = TenantPlan.FREE
    status: TenantStatus = TenantStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    max_users: int = 5
    max_storage_bytes: int = 1_073_741_824  # 1 GB
    max_api_calls_per_month: int = 10_000
    encryption_key_id: Optional[str] = None
    billing_email: Optional[str] = None
    suspended_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    def is_suspended(self) -> bool:
        return self.status == TenantStatus.SUSPENDED

    def can_provision(self) -> bool:
        return self.status in (TenantStatus.PENDING, TenantStatus.ACTIVE)


@dataclass
class TenantUser:
    """A user belonging to a specific tenant."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    email: str = ""
    role: TenantRole = TenantRole.MEMBER
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    permissions: set[TenantPermission] = field(default_factory=set)

    def has_permission(self, permission: TenantPermission) -> bool:
        return permission in self.permissions


@dataclass
class UsageRecord:
    """Tracks resource consumption for billing and monitoring."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    metric: str = ""  # e.g. "api_calls", "storage", "compute_seconds"
    quantity: float = 0.0
    unit: str = ""  # e.g. "count", "bytes", "seconds"
    recorded_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice:
    """A billing invoice for a tenant."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    amount_cents: int = 0
    currency: str = "USD"
    status: str = "draft"  # draft, open, paid, void, uncollectible
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    line_items: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = None


@dataclass
class Alert:
    """A monitoring alert for a tenant."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    name: str = ""
    severity: str = "info"  # info, warning, critical
    message: str = ""
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    is_resolved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditLog:
    """An audit log entry for tenant-scoped actions."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    user_id: Optional[str] = None
    action: str = ""
    resource_type: str = ""
    resource_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)
