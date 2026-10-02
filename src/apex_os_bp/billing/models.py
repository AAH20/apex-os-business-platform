"""Billing data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class BillingCycle(Enum):
    """Billing cycle options."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatus(Enum):
    """Subscription status."""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    TRIALING = "trialing"


class InvoiceStatus(Enum):
    """Invoice status."""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    UNCOLLECTIBLE = "uncollectible"
    VOID = "void"


class PaymentStatus(Enum):
    """Payment status."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(Enum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"


class DunningStatus(Enum):
    """Dunning record status."""
    PENDING = "pending"
    SENT = "sent"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class DunningAction(Enum):
    """Dunning action types."""
    EMAIL_REMINDER = "email_reminder"
    FINAL_NOTICE = "final_notice"
    ACCOUNT_SUSPENSION = "account_suspension"
    ESCALATION = "escalation"


@dataclass
class SubscriptionPlan:
    """Subscription plan definition."""
    id: str
    name: str
    price: float
    currency: str = "USD"
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    features: List[str] = field(default_factory=list)
    usage_limits: Dict[str, float] = field(default_factory=dict)
    overage_rates: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        name: str,
        price: float,
        currency: str = "USD",
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        features: Optional[List[str]] = None,
        usage_limits: Optional[Dict[str, float]] = None,
        overage_rates: Optional[Dict[str, float]] = None,
    ) -> SubscriptionPlan:
        """Create a new subscription plan."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            price=price,
            currency=currency,
            billing_cycle=billing_cycle,
            features=features or [],
            usage_limits=usage_limits or {},
            overage_rates=overage_rates or {},
        )


@dataclass
class Subscription:
    """Customer subscription."""
    id: str
    customer_id: str
    plan: SubscriptionPlan
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    start_date: datetime = field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    auto_renew: bool = True
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        customer_id: str,
        plan: SubscriptionPlan,
        trial_days: int = 0,
        auto_renew: bool = True,
    ) -> Subscription:
        """Create a new subscription."""
        trial_end = None
        if trial_days > 0:
            trial_end = datetime.now() + timedelta(days=trial_days)
        return cls(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            plan=plan,
            status=SubscriptionStatus.TRIALING if trial_days > 0 else SubscriptionStatus.ACTIVE,
            trial_end=trial_end,
            auto_renew=auto_renew,
        )

    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)

    def cancel(self) -> None:
        """Cancel the subscription."""
        self.status = SubscriptionStatus.CANCELED
        self.auto_renew = False

    def renew(self) -> None:
        """Renew the subscription for another billing cycle."""
        if self.status == SubscriptionStatus.CANCELED:
            raise ValueError("Cannot renew a canceled subscription")
        self.status = SubscriptionStatus.ACTIVE
        if self.plan.billing_cycle == BillingCycle.MONTHLY:
            self.end_date = datetime.now() + timedelta(days=30)
        elif self.plan.billing_cycle == BillingCycle.QUARTERLY:
            self.end_date = datetime.now() + timedelta(days=90)
        elif self.plan.billing_cycle == BillingCycle.YEARLY:
            self.end_date = datetime.now() + timedelta(days=365)


@dataclass
class UsageRecord:
    """Usage record for metered billing."""
    id: str
    customer_id: str
    subscription_id: str
    metric: str
    quantity: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def record(
        cls,
        customer_id: str,
        subscription_id: str,
        metric: str,
        quantity: float,
    ) -> UsageRecord:
        """Record usage."""
        return cls(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            subscription_id=subscription_id,
            metric=metric,
            quantity=quantity,
        )


@dataclass
class InvoiceLine:
    """Invoice line item."""
    description: str
    quantity: float
    unit_price: float
    amount: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if self.amount == 0.0:
            self.amount = self.quantity * self.unit_price


@dataclass
class Invoice:
    """Invoice data structure."""
    id: str
    customer_id: str
    subscription_id: Optional[str]
    lines: List[InvoiceLine] = field(default_factory=list)
    status: InvoiceStatus = InvoiceStatus.DRAFT
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        customer_id: str,
        subscription_id: Optional[str] = None,
        currency: str = "USD",
        due_days: int = 30,
    ) -> Invoice:
        """Create a new invoice."""
        return cls(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            subscription_id=subscription_id,
            currency=currency,
            due_date=datetime.now() + timedelta(days=due_days),
        )

    def add_line(self, line: InvoiceLine) -> None:
        """Add a line item to the invoice."""
        self.lines.append(line)
        self._recalculate()

    def _recalculate(self) -> None:
        """Recalculate totals."""
        self.subtotal = sum(line.amount for line in self.lines)
        self.total = self.subtotal + self.tax

    def apply_tax(self, tax_rate: float) -> None:
        """Apply tax rate to the invoice."""
        self.tax = self.subtotal * tax_rate
        self._recalculate()

    def mark_paid(self) -> None:
        """Mark invoice as paid."""
        self.status = InvoiceStatus.PAID
        self.paid_at = datetime.now()

    def mark_void(self) -> None:
        """Mark invoice as void."""
        self.status = InvoiceStatus.VOID

    def is_paid(self) -> bool:
        """Check if invoice is paid."""
        return self.status == InvoiceStatus.PAID

    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.status != InvoiceStatus.OPEN:
            return False
        if not self.due_date:
            return False
        return datetime.now() > self.due_date


@dataclass
class Payment:
    """Payment data structure."""
    id: str
    invoice_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    method: PaymentMethod = PaymentMethod.CREDIT_CARD
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        invoice_id: str,
        customer_id: str,
        amount: float,
        method: PaymentMethod = PaymentMethod.CREDIT_CARD,
        currency: str = "USD",
    ) -> Payment:
        """Create a new payment."""
        return cls(
            id=str(uuid.uuid4()),
            invoice_id=invoice_id,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            method=method,
        )

    def mark_succeeded(self, transaction_id: str) -> None:
        """Mark payment as succeeded."""
        self.status = PaymentStatus.SUCCEEDED
        self.transaction_id = transaction_id

    def mark_failed(self, reason: str) -> None:
        """Mark payment as failed."""
        self.status = PaymentStatus.FAILED
        self.failure_reason = reason

    def mark_refunded(self) -> None:
        """Mark payment as refunded."""
        self.status = PaymentStatus.REFUNDED


@dataclass
class DunningRecord:
    """Dunning record for failed payment recovery."""
    id: str
    customer_id: str
    invoice_id: str
    subscription_id: Optional[str]
    status: DunningStatus = DunningStatus.PENDING
    attempt: int = 0
    max_attempts: int = 3
    actions: List[DunningAction] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        customer_id: str,
        invoice_id: str,
        subscription_id: Optional[str] = None,
        max_attempts: int = 3,
    ) -> DunningRecord:
        """Create a new dunning record."""
        return cls(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            invoice_id=invoice_id,
            subscription_id=subscription_id,
            max_attempts=max_attempts,
        )

    def add_action(self, action: DunningAction) -> None:
        """Add a dunning action."""
        self.actions.append(action)
        self.attempt += 1

    def mark_resolved(self) -> None:
        """Mark dunning as resolved."""
        self.status = DunningStatus.RESOLVED
        self.resolved_at = datetime.now()

    def mark_escalated(self) -> None:
        """Mark dunning as escalated."""
        self.status = DunningStatus.ESCALATED

    def is_resolved(self) -> bool:
        """Check if dunning is resolved."""
        return self.status in (DunningStatus.RESOLVED, DunningStatus.CLOSED)

    def can_retry(self) -> bool:
        """Check if another dunning attempt can be made."""
        return self.attempt < self.max_attempts and not self.is_resolved()
