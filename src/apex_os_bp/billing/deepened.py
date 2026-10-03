"""Deepened billing module: subscriptions, invoices, payments, dunning, ASC 606."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Domain enums
# ---------------------------------------------------------------------------

class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    UNPAID = "unpaid"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    UNCOLLECTIBLE = "uncollectible"
    VOID = "void"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class DunningAction(str, Enum):
    EMAIL_REMINDER = "email_reminder"
    CARD_RETRY = "card_retry"
    ESCALATE = "escalate"
    CANCEL = "cancel"


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------

@dataclass
class Plan:
    id: str
    name: str
    amount: Decimal
    currency: str = "usd"
    interval: BillingInterval = BillingInterval.MONTHLY
    trial_days: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Subscription:
    id: str
    customer_id: str
    plan: Plan
    status: SubscriptionStatus = SubscriptionStatus.TRIALING
    current_period_start: Optional[date] = None
    current_period_end: Optional[date] = None
    cancel_at_period_end: bool = False
    stripe_subscription_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_active(self) -> bool:
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)

    def days_until_renewal(self) -> int:
        if not self.current_period_end:
            return 0
        return max(0, (self.current_period_end - date.today()).days)


@dataclass
class InvoiceLineItem:
    description: str
    quantity: int
    unit_amount: Decimal
    currency: str = "usd"

    @property
    def total(self) -> Decimal:
        return self.unit_amount * self.quantity


@dataclass
class Invoice:
    id: str
    customer_id: str
    subscription_id: Optional[str]
    line_items: list[InvoiceLineItem]
    status: InvoiceStatus = InvoiceStatus.DRAFT
    due_date: Optional[date] = None
    paid_at: Optional[datetime] = None
    stripe_invoice_id: Optional[str] = None
    pdf_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def subtotal(self) -> Decimal:
        return sum((li.total for li in self.line_items), Decimal("0"))

    @property
    def total(self) -> Decimal:
        return self.subtotal  # tax hook omitted for brevity

    def mark_paid(self) -> None:
        self.status = InvoiceStatus.PAID
        self.paid_at = datetime.utcnow()


@dataclass
class Payment:
    id: str
    invoice_id: str
    amount: Decimal
    currency: str = "usd"
    status: PaymentStatus = PaymentStatus.PENDING
    stripe_payment_intent_id: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DunningStep:
    day_offset: int
    action: DunningAction
    template: str


@dataclass
class DunningRecord:
    id: str
    invoice_id: str
    step_index: int = 0
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    resolved: bool = False


# ---------------------------------------------------------------------------
# Subscription manager
# ---------------------------------------------------------------------------

class SubscriptionManager:
    def __init__(self) -> None:
        self._subs: dict[str, Subscription] = {}
        self._plans: dict[str, Plan] = {}

    def create_plan(self, name: str, amount: Decimal,
                    interval: BillingInterval = BillingInterval.MONTHLY,
                    trial_days: int = 0, currency: str = "usd") -> Plan:
        plan = Plan(id=str(uuid.uuid4()), name=name, amount=amount,
                    currency=currency, interval=interval, trial_days=trial_days)
        self._plans[plan.id] = plan
        return plan

    def subscribe(self, customer_id: str, plan_id: str) -> Subscription:
        plan = self._plans[plan_id]
        start = date.today()
        end = self._compute_period_end(start, plan.interval, plan.trial_days)
        sub = Subscription(id=str(uuid.uuid4()), customer_id=customer_id,
                           plan=plan, status=SubscriptionStatus.TRIALING,
                           current_period_start=start, current_period_end=end)
        self._subs[sub.id] = sub
        return sub

    def cancel(self, sub_id: str, immediate: bool = False) -> Subscription:
        sub = self._subs[sub_id]
        if immediate:
            sub.status = SubscriptionStatus.CANCELED
        else:
            sub.cancel_at_period_end = True
        return sub

    def renew(self, sub_id: str) -> Subscription:
        sub = self._subs[sub_id]
        if sub.status == SubscriptionStatus.CANCELED:
            raise ValueError("Cannot renew canceled subscription")
        sub.current_period_start = date.today()
        sub.current_period_end = self._compute_period_end(
            sub.current_period_start, sub.plan.interval, 0)
        sub.status = SubscriptionStatus.ACTIVE
        sub.cancel_at_period_end = False
        return sub

    def get(self, sub_id: str) -> Optional[Subscription]:
        return self._subs.get(sub_id)

    @staticmethod
    def _compute_period_end(start: date, interval: BillingInterval,
                            trial_days: int) -> date:
        delta = {"monthly": 30, "quarterly": 90, "annual": 365}[interval.value]
        return start + timedelta(days=delta + trial_days)


# ---------------------------------------------------------------------------
# Invoice generator (PDF-ready)
# ---------------------------------------------------------------------------

class InvoiceGenerator:
    def __init__(self, output_dir: str = "/tmp/invoices") -> None:
        self._invoices: dict[str, Invoice] = {}
        self._output_dir = output_dir

    def create(self, customer_id: str, subscription_id: Optional[str],
               line_items: list[InvoiceLineItem],
               due_days: int = 30) -> Invoice:
        inv = Invoice(id=str(uuid.uuid4()), customer_id=customer_id,
                      subscription_id=subscription_id, line_items=line_items,
                      status=InvoiceStatus.OPEN,
                      due_date=date.today() + timedelta(days=due_days))
        self._invoices[inv.id] = inv
        return inv

    def generate_pdf(self, invoice_id: str) -> str:
        inv = self._invoices[invoice_id]
        path = f"{self._output_dir}/{inv.id}.pdf"
        # Minimal PDF stub — real impl would use reportlab/weasyprint
        content = _render_pdf_text(inv)
        with open(path, "w") as f:
            f.write(content)
        inv.pdf_path = path
        return path

    def get(self, invoice_id: str) -> Optional[Invoice]:
        return self._invoices.get(invoice_id)


def _render_pdf_text(inv: Invoice) -> str:
    lines = [f"INVOICE {inv.id}", f"Customer: {inv.customer_id}",
             f"Date: {inv.created_at:%Y-%m-%d}", f"Due: {inv.due_date}", ""]
    for li in inv.line_items:
        lines.append(f"  {li.description} x{li.quantity} @ {li.unit_amount} = {li.total}")
    lines.append(f"\nTotal: {inv.total} {inv.line_items[0].currency if inv.line_items else 'usd'}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Payment processor (Stripe)
# ---------------------------------------------------------------------------

class StripePaymentProcessor:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._payments: dict[str, Payment] = {}

    def charge(self, invoice: Invoice, payment_method_id: str) -> Payment:
        payment = Payment(id=str(uuid.uuid4()), invoice_id=invoice.id,
                          amount=invoice.total,
                          currency=invoice.line_items[0].currency if invoice.line_items else "usd")
        try:
            # Real impl: stripe.PaymentIntent.create(amount=..., currency=...)
            payment.status = PaymentStatus.SUCCEEDED
            payment.stripe_payment_intent_id = f"pi_{uuid.uuid4().hex[:24]}"
            invoice.mark_paid()
        except Exception as exc:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = str(exc)
        self._payments[payment.id] = payment
        return payment

    def refund(self, payment_id: str) -> Payment:
        payment = self._payments[payment_id]
        payment.status = PaymentStatus.REFUNDED
        return payment

    def get(self, payment_id: str) -> Optional[Payment]:
        return self._payments.get(payment_id)


# ---------------------------------------------------------------------------
# Dunning manager
# ---------------------------------------------------------------------------

DEFAULT_DUNNING_SCHEDULE: list[DunningStep] = [
    DunningStep(1, DunningAction.EMAIL_REMINDER, "friendly_reminder"),
    DunningStep(3, DunningAction.CARD_RETRY, "retry_payment"),
    DunningStep(7, DunningAction.EMAIL_REMINDER, "urgent_reminder"),
    DunningStep(14, DunningAction.CARD_RETRY, "final_retry"),
    DunningStep(21, DunningAction.ESCALATE, "collections_notice"),
    DunningStep(30, DunningAction.CANCEL, "service_suspension"),
]


class DunningManager:
    def __init__(self, schedule: Optional[list[DunningStep]] = None) -> None:
        self._schedule = schedule or DEFAULT_DUNNING_SCHEDULE
        self._records: dict[str, DunningRecord] = {}

    def start(self, invoice_id: str) -> DunningRecord:
        rec = DunningRecord(id=str(uuid.uuid4()), invoice_id=invoice_id)
        self._records[rec.id] = rec
        return rec

    def process(self, record_id: str, invoice: Invoice,
                processor: StripePaymentProcessor,
                payment_method_id: str) -> DunningRecord:
        rec = self._records[record_id]
        if rec.resolved or invoice.status == InvoiceStatus.PAID:
            rec.resolved = True
            return rec
        step = self._schedule[min(rec.step_index, len(self._schedule) - 1)]
        rec.attempts += 1
        rec.last_attempt_at = datetime.utcnow()
        if step.action == DunningAction.CARD_RETRY:
            payment = processor.charge(invoice, payment_method_id)
            if payment.status == PaymentStatus.SUCCEEDED:
                rec.resolved = True
                return rec
        if step.action == DunningAction.CANCEL:
            rec.resolved = True
            return rec
        rec.step_index = min(rec.step_index + 1, len(self._schedule) - 1)
        return rec

    def get(self, record_id: str) -> Optional[DunningRecord]:
        return self._records.get(record_id)


# ---------------------------------------------------------------------------
# Revenue recognition (ASC 606)
# ---------------------------------------------------------------------------

class ASC606Recognizer:
    """Straight-line revenue recognition over the service period."""

    def __init__(self) -> None:
        self._schedule: dict[str, list[dict[str, Any]]] = {}

    def build_schedule(self, invoice: Invoice) -> list[dict[str, Any]]:
        if not invoice.subscription_id or not invoice.paid_at:
            raise ValueError("Invoice must be paid and linked to a subscription")
        total = invoice.total
        start = invoice.paid_at.date()
        # Assume monthly recognition for simplicity; real impl uses sub period
        periods = 12
        daily = total / Decimal(periods * 30)
        schedule = []
        for i in range(periods):
            period_start = start + timedelta(days=30 * i)
            period_end = period_start + timedelta(days=30)
            schedule.append({
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "amount": str(daily * 30),
                "recognized": False,
            })
        self._schedule[invoice.id] = schedule
        return schedule

    def recognize_period(self, invoice_id: str, period_index: int) -> Decimal:
        entries = self._schedule[invoice_id]
        entry = entries[period_index]
        if entry["recognized"]:
            return Decimal("0")
        entry["recognized"] = True
        return Decimal(entry["amount"])

    def recognized_to_date(self, invoice_id: str) -> Decimal:
        return sum((Decimal(e["amount"]) for e in self._schedule[invoice_id]
                    if e["recognized"]), Decimal("0"))

    def remaining_balance(self, invoice_id: str) -> Decimal:
        total = sum((Decimal(e["amount"]) for e in self._schedule[invoice_id]),
                    Decimal("0"))
        return total - self.recognized_to_date(invoice_id)
