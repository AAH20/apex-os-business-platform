"""Usage-based billing engine."""
from __future__ import annotations

from typing import Dict, List, Optional

from apex_os_bp.billing.models import (
    Invoice,
    InvoiceLine,
    Subscription,
    UsageRecord,
)


class UsageBilling:
    """Manages metered/usage-based billing."""

    def __init__(self):
        self._usage_records: Dict[str, List[UsageRecord]] = {}

    def record_usage(
        self,
        customer_id: str,
        subscription_id: str,
        metric: str,
        quantity: float,
    ) -> UsageRecord:
        """Record usage for a metered billing metric."""
        record = UsageRecord.record(
            customer_id=customer_id,
            subscription_id=subscription_id,
            metric=metric,
            quantity=quantity,
        )
        if subscription_id not in self._usage_records:
            self._usage_records[subscription_id] = []
        self._usage_records[subscription_id].append(record)
        return record

    def get_usage(
        self,
        subscription_id: str,
        metric: Optional[str] = None,
    ) -> List[UsageRecord]:
        """Get usage records for a subscription, optionally filtered by metric."""
        records = self._usage_records.get(subscription_id, [])
        if metric:
            return [r for r in records if r.metric == metric]
        return list(records)

    def get_total_usage(self, subscription_id: str, metric: str) -> float:
        """Get total usage quantity for a specific metric."""
        records = self.get_usage(subscription_id, metric)
        return sum(r.quantity for r in records)

    def calculate_overage(
        self,
        subscription: Subscription,
    ) -> Dict[str, float]:
        """Calculate overage charges for a subscription."""
        overages: Dict[str, float] = {}
        for metric, limit in subscription.plan.usage_limits.items():
            total = self.get_total_usage(subscription.id, metric)
            if total > limit:
                overage_qty = total - limit
                rate = subscription.plan.overage_rates.get(metric, 0.0)
                overages[metric] = overage_qty * rate
        return overages

    def generate_usage_invoice(
        self,
        subscription: Subscription,
    ) -> Invoice:
        """Generate an invoice for usage-based charges."""
        invoice = Invoice.create(
            customer_id=subscription.customer_id,
            subscription_id=subscription.id,
            currency=subscription.plan.currency,
        )

        overages = self.calculate_overage(subscription)
        for metric, charge in overages.items():
            if charge > 0:
                rate = subscription.plan.overage_rates.get(metric, 0.0)
                limit = subscription.plan.usage_limits.get(metric, 0)
                total = self.get_total_usage(subscription.id, metric)
                overage_qty = total - limit
                invoice.add_line(InvoiceLine(
                    description=f"Overage: {metric}",
                    quantity=overage_qty,
                    unit_price=rate,
                ))

        return invoice

    def reset_usage(self, subscription_id: str) -> None:
        """Reset usage records for a subscription (e.g., after billing cycle)."""
        if subscription_id in self._usage_records:
            self._usage_records[subscription_id] = []
