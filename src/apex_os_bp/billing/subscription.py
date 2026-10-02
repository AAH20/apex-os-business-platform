"""Subscription billing engine."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.billing.models import (
    BillingCycle,
    Invoice,
    InvoiceLine,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)


class SubscriptionBilling:
    """Manages subscription lifecycle and recurring billing."""

    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}
        self._plans: Dict[str, SubscriptionPlan] = {}

    def create_plan(
        self,
        name: str,
        price: float,
        currency: str = "USD",
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        features: Optional[List[str]] = None,
        usage_limits: Optional[Dict[str, float]] = None,
        overage_rates: Optional[Dict[str, float]] = None,
    ) -> SubscriptionPlan:
        """Create a new subscription plan."""
        plan = SubscriptionPlan.create(
            name=name,
            price=price,
            currency=currency,
            billing_cycle=billing_cycle,
            features=features,
            usage_limits=usage_limits,
            overage_rates=overage_rates,
        )
        self._plans[plan.id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """Get plan by ID."""
        return self._plans.get(plan_id)

    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        trial_days: int = 0,
        auto_renew: bool = True,
    ) -> Subscription:
        """Create a new subscription for a customer."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        sub = Subscription.create(
            customer_id=customer_id,
            plan=plan,
            trial_days=trial_days,
            auto_renew=auto_renew,
        )
        self._subscriptions[sub.id] = sub
        return sub

    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        return self._subscriptions.get(subscription_id)

    def cancel_subscription(self, subscription_id: str) -> Subscription:
        """Cancel a subscription."""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            raise ValueError(f"Subscription not found: {subscription_id}")
        sub.cancel()
        return sub

    def renew_subscription(self, subscription_id: str) -> Subscription:
        """Renew a subscription."""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            raise ValueError(f"Subscription not found: {subscription_id}")
        sub.renew()
        return sub

    def generate_invoice(self, subscription_id: str) -> Invoice:
        """Generate an invoice for a subscription's current period."""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            raise ValueError(f"Subscription not found: {subscription_id}")

        invoice = Invoice.create(
            customer_id=sub.customer_id,
            subscription_id=sub.id,
            currency=sub.plan.currency,
        )
        invoice.add_line(InvoiceLine(
            description=f"{sub.plan.name} subscription",
            quantity=1,
            unit_price=sub.plan.price,
        ))
        return invoice

    def get_customer_subscriptions(self, customer_id: str) -> List[Subscription]:
        """Get all subscriptions for a customer."""
        return [s for s in self._subscriptions.values() if s.customer_id == customer_id]

    def get_active_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions."""
        return [s for s in self._subscriptions.values() if s.is_active()]

    def process_renewals(self) -> List[Subscription]:
        """Process renewals for subscriptions past their end date."""
        renewed = []
        now = datetime.now()
        for sub in self._subscriptions.values():
            if sub.status == SubscriptionStatus.CANCELED:
                continue
            if not sub.auto_renew:
                continue
            if sub.end_date and now >= sub.end_date:
                sub.renew()
                renewed.append(sub)
        return renewed
