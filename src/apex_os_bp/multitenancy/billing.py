"""Tenant billing — usage metering, invoicing, and subscription management."""

from __future__ import annotations

import enum
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from apex_os_bp.multitenancy.models import (
    Invoice,
    Tenant,
    TenantPlan,
    UsageRecord,
)

logger = logging.getLogger(__name__)


class BillingCycle(enum.Enum):
    """Billing cycle options."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


# Plan pricing in cents
PLAN_PRICING: dict[TenantPlan, dict[str, Any]] = {
    TenantPlan.FREE: {
        "monthly_cents": 0,
        "yearly_cents": 0,
        "overage_per_1k_api_calls_cents": 0,
        "overage_per_gb_storage_cents": 0,
    },
    TenantPlan.STARTER: {
        "monthly_cents": 2_900,
        "yearly_cents": 29_000,
        "overage_per_1k_api_calls_cents": 50,
        "overage_per_gb_storage_cents": 100,
    },
    TenantPlan.PROFESSIONAL: {
        "monthly_cents": 9_900,
        "yearly_cents": 99_000,
        "overage_per_1k_api_calls_cents": 30,
        "overage_per_gb_storage_cents": 50,
    },
    TenantPlan.ENTERPRISE: {
        "monthly_cents": 49_900,
        "yearly_cents": 499_000,
        "overage_per_1k_api_calls_cents": 10,
        "overage_per_gb_storage_cents": 20,
    },
}


@dataclass
class UsageMeter:
    """Tracks and aggregates usage metrics for a tenant."""

    tenant_id: str = ""
    records: list[UsageRecord] = field(default_factory=list)

    def record(
        self,
        metric: str,
        quantity: float,
        unit: str = "count",
        metadata: Optional[dict[str, Any]] = None,
    ) -> UsageRecord:
        """Record a usage data point."""
        record = UsageRecord(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            metric=metric,
            quantity=quantity,
            unit=unit,
            recorded_at=datetime.utcnow(),
            metadata=metadata or {},
        )
        self.records.append(record)
        return record

    def get_usage(
        self,
        metric: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> float:
        """Get total usage for a metric within a time range."""
        total = 0.0
        for record in self.records:
            if record.metric != metric:
                continue
            if start and record.recorded_at < start:
                continue
            if end and record.recorded_at > end:
                continue
            total += record.quantity
        return total

    def get_usage_by_metric(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> dict[str, float]:
        """Get usage totals grouped by metric name."""
        totals: dict[str, float] = defaultdict(float)
        for record in self.records:
            if start and record.recorded_at < start:
                continue
            if end and record.recorded_at > end:
                continue
            totals[record.metric] += record.quantity
        return dict(totals)

    def clear(self) -> None:
        """Clear all usage records."""
        self.records.clear()


class BillingEngine:
    """Generates invoices and manages billing for tenants."""

    def __init__(self) -> None:
        self._invoices: dict[str, list[Invoice]] = {}
        self._usage_meters: dict[str, UsageMeter] = {}

    def get_or_create_meter(self, tenant_id: str) -> UsageMeter:
        """Get or create a usage meter for a tenant."""
        if tenant_id not in self._usage_meters:
            self._usage_meters[tenant_id] = UsageMeter(tenant_id=tenant_id)
        return self._usage_meters[tenant_id]

    def record_usage(
        self,
        tenant_id: str,
        metric: str,
        quantity: float,
        unit: str = "count",
        metadata: Optional[dict[str, Any]] = None,
    ) -> UsageRecord:
        """Record usage for a tenant."""
        meter = self.get_or_create_meter(tenant_id)
        return meter.record(metric, quantity, unit, metadata)

    def generate_invoice(
        self,
        tenant: Tenant,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Invoice:
        """Generate an invoice for a tenant based on usage and plan."""
        now = datetime.utcnow()
        period_start = period_start or (now - timedelta(days=30))
        period_end = period_end or now

        plan_config = PLAN_PRICING[tenant.plan]
        line_items: list[dict[str, Any]] = []
        total_cents = 0

        # Base subscription fee
        base_cents = plan_config["monthly_cents"]
        if base_cents > 0:
            line_items.append({
                "description": f"{tenant.plan.value.title()} plan subscription",
                "quantity": 1,
                "unit_price_cents": base_cents,
                "amount_cents": base_cents,
            })
            total_cents += base_cents

        # Calculate overage
        meter = self._usage_meters.get(tenant.id)
        if meter:
            usage = meter.get_usage_by_metric(period_start, period_end)

            # API call overage
            api_calls = usage.get("api_calls", 0)
            included_api_calls = tenant.max_api_calls_per_month
            if api_calls > included_api_calls:
                overage_calls = api_calls - included_api_calls
                overage_units = overage_calls / 1000
                overage_cents = int(
                    overage_units * plan_config["overage_per_1k_api_calls_cents"]
                )
                if overage_cents > 0:
                    line_items.append({
                        "description": "API call overage",
                        "quantity": overage_calls,
                        "unit_price_cents": plan_config["overage_per_1k_api_calls_cents"],
                        "amount_cents": overage_cents,
                    })
                    total_cents += overage_cents

            # Storage overage
            storage_bytes = usage.get("storage_bytes", 0)
            included_storage = tenant.max_storage_bytes
            if storage_bytes > included_storage:
                overage_bytes = storage_bytes - included_storage
                overage_gb = overage_bytes / 1_073_741_824
                overage_cents = int(
                    overage_gb * plan_config["overage_per_gb_storage_cents"]
                )
                if overage_cents > 0:
                    line_items.append({
                        "description": "Storage overage",
                        "quantity": round(overage_gb, 2),
                        "unit_price_cents": plan_config["overage_per_gb_storage_cents"],
                        "amount_cents": overage_cents,
                    })
                    total_cents += overage_cents

        invoice = Invoice(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            amount_cents=total_cents,
            currency="USD",
            status="open",
            period_start=period_start,
            period_end=period_end,
            line_items=line_items,
            due_date=period_end + timedelta(days=14),
        )

        if tenant.id not in self._invoices:
            self._invoices[tenant.id] = []
        self._invoices[tenant.id].append(invoice)

        logger.info(
            "Generated invoice %s for tenant %s: %d cents",
            invoice.id,
            tenant.id,
            total_cents,
        )

        return invoice

    def get_invoices(
        self,
        tenant_id: str,
        status: Optional[str] = None,
    ) -> list[Invoice]:
        """Get invoices for a tenant, optionally filtered by status."""
        invoices = self._invoices.get(tenant_id, [])
        if status:
            invoices = [inv for inv in invoices if inv.status == status]
        return invoices

    def mark_paid(self, invoice_id: str, tenant_id: str) -> bool:
        """Mark an invoice as paid."""
        invoices = self._invoices.get(tenant_id, [])
        for invoice in invoices:
            if invoice.id == invoice_id:
                invoice.status = "paid"
                invoice.paid_at = datetime.utcnow()
                logger.info("Invoice %s marked as paid", invoice_id)
                return True
        return False

    def void_invoice(self, invoice_id: str, tenant_id: str) -> bool:
        """Void an invoice."""
        invoices = self._invoices.get(tenant_id, [])
        for invoice in invoices:
            if invoice.id == invoice_id:
                invoice.status = "void"
                logger.info("Invoice %s voided", invoice_id)
                return True
        return False

    def get_outstanding_balance_cents(self, tenant_id: str) -> int:
        """Get total outstanding balance for a tenant."""
        invoices = self._invoices.get(tenant_id, [])
        return sum(
            inv.amount_cents
            for inv in invoices
            if inv.status in ("open", "uncollectible")
        )

    def change_plan(
        self,
        tenant: Tenant,
        new_plan: TenantPlan,
        prorate: bool = True,
    ) -> Optional[Invoice]:
        """Change a tenant's plan, optionally generating a prorated invoice."""
        old_plan = tenant.plan
        if old_plan == new_plan:
            return None

        tenant.plan = new_plan

        # Update limits
        from apex_os_bp.multitenancy.provisioning import TenantProvisioner

        limits = TenantProvisioner.PLAN_LIMITS[new_plan]
        tenant.max_users = limits["max_users"]
        tenant.max_storage_bytes = limits["max_storage_bytes"]
        tenant.max_api_calls_per_month = limits["max_api_calls_per_month"]

        # Generate prorated invoice if applicable
        prorated_invoice = None
        if prorate and PLAN_PRICING[new_plan]["monthly_cents"] > PLAN_PRICING[old_plan]["monthly_cents"]:
            prorated_invoice = self.generate_invoice(tenant)

        logger.info(
            "Tenant %s plan changed from %s to %s",
            tenant.id,
            old_plan.value,
            new_plan.value,
        )

        return prorated_invoice
