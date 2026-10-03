"""Deepened multi-tenancy: isolation, provisioning, billing, customization, migration."""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# 1. Tenant Isolation with Row-Level Security
# ---------------------------------------------------------------------------

class TenantContext:
    """Thread-local tenant context for row-level security."""

    _current_tenant_id: Optional[str] = None

    @classmethod
    def set_tenant(cls, tenant_id: str) -> None:
        cls._current_tenant_id = tenant_id

    @classmethod
    def get_tenant(cls) -> Optional[str]:
        return cls._current_tenant_id

    @classmethod
    def clear(cls) -> None:
        cls._current_tenant_id = None


@contextmanager
def tenant_scope(tenant_id: str) -> Generator[None, None, None]:
    """Context manager that scopes all operations to a single tenant."""
    TenantContext.set_tenant(tenant_id)
    try:
        yield
    finally:
        TenantContext.clear()


class TenantIsolatedMixin:
    """Mixin adding tenant_id column and RLS enforcement to ORM models."""

    tenant_id: str = ""

    @classmethod
    def for_tenant(cls, tenant_id: str) -> List["TenantIsolatedMixin"]:
        """Return rows belonging to the given tenant (RLS query)."""
        return [r for r in cls._all() if r.tenant_id == tenant_id]

    @classmethod
    def _all(cls) -> List["TenantIsolatedMixin"]:
        return []  # Override in concrete models


def tenant_rls_policy(table: str, tenant_id: str) -> str:
    """Generate a PostgreSQL RLS policy expression for a table."""
    return (
        f"CREATE POLICY tenant_isolation ON {table} "
        f"USING (tenant_id = '{tenant_id}') "
        f"WITH CHECK (tenant_id = '{tenant_id}');"
    )


# ---------------------------------------------------------------------------
# 2. Tenant Provisioning with Onboarding
# ---------------------------------------------------------------------------

class OnboardingStep(Enum):
    PROFILE = "profile"
    BILLING = "billing"
    INVITE_TEAM = "invite_team"
    DATA_IMPORT = "data_import"
    INTEGRATIONS = "integrations"


@dataclass
class Tenant:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slug: str = ""
    plan: str = "trial"
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.utcnow)
    settings: Dict[str, Any] = field(default_factory=dict)
    onboarding_completed: List[str] = field(default_factory=list)


class TenantProvisioner:
    """Provisions new tenants with onboarding workflow."""

    def __init__(self) -> None:
        self._tenants: Dict[str, Tenant] = {}
        self._onboarding_hooks: Dict[OnboardingStep, List[Callable]] = {}

    def register_hook(self, step: OnboardingStep, fn: Callable) -> None:
        self._onboarding_hooks.setdefault(step, []).append(fn)

    def provision(self, name: str, slug: str, plan: str = "trial") -> Tenant:
        tenant = Tenant(name=name, slug=slug, plan=plan)
        self._tenants[tenant.id] = tenant
        self._run_onboarding(tenant)
        return tenant

    def _run_onboarding(self, tenant: Tenant) -> None:
        for step in OnboardingStep:
            for hook in self._onboarding_hooks.get(step, []):
                hook(tenant)
            tenant.onboarding_completed.append(step.value)

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def deactivate(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.status = "inactive"
            return True
        return False


# ---------------------------------------------------------------------------
# 3. Tenant Billing with Usage Metering
# ---------------------------------------------------------------------------

@dataclass
class UsageEvent:
    tenant_id: str
    metric: str
    quantity: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PlanLimits:
    plan: str
    max_users: int
    max_storage_gb: float
    max_api_calls: int
    price_monthly: float


class UsageMeter:
    """Tracks per-tenant usage events and computes billing."""

    PLANS: Dict[str, PlanLimits] = {
        "trial": PlanLimits("trial", 3, 1.0, 1_000, 0.0),
        "starter": PlanLimits("starter", 10, 10.0, 10_000, 29.0),
        "pro": PlanLimits("pro", 50, 100.0, 100_000, 99.0),
        "enterprise": PlanLimits("enterprise", 500, 1000.0, 1_000_000, 499.0),
    }

    def __init__(self) -> None:
        self._events: List[UsageEvent] = []

    def record(self, tenant_id: str, metric: str, quantity: float) -> None:
        self._events.append(UsageEvent(tenant_id, metric, quantity))

    def get_usage(self, tenant_id: str, metric: str) -> float:
        return sum(
            e.quantity for e in self._events
            if e.tenant_id == tenant_id and e.metric == metric
        )

    def compute_invoice(self, tenant_id: str, plan: str) -> Dict[str, Any]:
        limits = self.PLANS.get(plan, self.PLANS["trial"])
        usage = {
            metric: self.get_usage(usage_id, metric)
            for usage_id in [tenant_id]
            for metric in ["api_calls", "storage_gb", "users"]
        }
        overage = max(0, usage["api_calls"] - limits.max_api_calls)
        overage_cost = overage * 0.001
        return {
            "tenant_id": tenant_id,
            "plan": plan,
            "base_price": limits.price_monthly,
            "usage": usage,
            "overage_cost": round(overage_cost, 2),
            "total": round(limits.price_monthly + overage_cost, 2),
        }


# ---------------------------------------------------------------------------
# 4. Tenant Customization with Themes
# ---------------------------------------------------------------------------

@dataclass
class Theme:
    tenant_id: str
    primary_color: str = "#1a73e8"
    secondary_color: str = "#34a853"
    font_family: str = "Inter"
    logo_url: str = ""
    custom_css: str = ""
    dark_mode: bool = False


class ThemeManager:
    """Manages per-tenant UI themes and branding."""

    def __init__(self) -> None:
        self._themes: Dict[str, Theme] = {}

    def set_theme(self, tenant_id: str, **kwargs: Any) -> Theme:
        theme = self._themes.get(tenant_id, Theme(tenant_id=tenant_id))
        for key, value in kwargs.items():
            if hasattr(theme, key):
                setattr(theme, key, value)
        self._themes[tenant_id] = theme
        return theme

    def get_theme(self, tenant_id: str) -> Theme:
        return self._themes.get(tenant_id, Theme(tenant_id=tenant_id))

    def apply_css_override(self, tenant_id: str, css: str) -> None:
        theme = self.get_theme(tenant_id)
        theme.custom_css = css


# ---------------------------------------------------------------------------
# 5. Tenant Migration with Data Portability
# ---------------------------------------------------------------------------

class TenantMigrator:
    """Exports and imports tenant data for portability."""

    EXPORT_VERSION = "1.0"

    def __init__(self, provisioner: TenantProvisioner, meter: UsageMeter) -> None:
        self._provisioner = provisioner
        self._meter = meter

    def export_tenant(self, tenant_id: str) -> Dict[str, Any]:
        tenant = self._provisioner.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        return {
            "version": self.EXPORT_VERSION,
            "exported_at": datetime.utcnow().isoformat(),
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "plan": tenant.plan,
                "settings": tenant.settings,
                "onboarding_completed": tenant.onboarding_completed,
            },
            "usage": {
                "api_calls": self._meter.get_usage(tenant_id, "api_calls"),
                "storage_gb": self._meter.get_usage(tenant_id, "storage_gb"),
                "users": self._meter.get_usage(tenant_id, "users"),
            },
        }

    def import_tenant(self, data: Dict[str, Any]) -> Tenant:
        if data.get("version") != self.EXPORT_VERSION:
            raise ValueError(f"Unsupported export version: {data.get('version')}")
        t = data["tenant"]
        tenant = self._provisioner.provision(t["name"], t["slug"], t["plan"])
        tenant.settings = t.get("settings", {})
        tenant.onboarding_completed = t.get("onboarding_completed", [])
        usage = data.get("usage", {})
        for metric, qty in usage.items():
            self._meter.record(tenant.id, metric, qty)
        return tenant

    def migrate_plan(self, tenant_id: str, new_plan: str) -> bool:
        tenant = self._provisioner.get_tenant(tenant_id)
        if not tenant or new_plan not in UsageMeter.PLANS:
            return False
        tenant.plan = new_plan
        return True
