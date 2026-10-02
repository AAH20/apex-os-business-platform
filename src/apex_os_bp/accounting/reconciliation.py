"""Payment reconciliation: match payments to invoices, detect discrepancies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from apex_os_bp.accounting.models import Invoice


class PaymentMethod(str, Enum):
    """Supported payment methods."""

    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    CHECK = "check"
    DIGITAL_WALLET = "digital_wallet"
    CRYPTO = "crypto"
    OTHER = "other"


class ReconciliationStatus(str, Enum):
    """Outcome of reconciling a payment against an invoice."""

    MATCHED = "matched"
    PARTIAL = "partial"
    OVERPAYMENT = "overpayment"
    UNMATCHED = "unmatched"
    DISCREPANCY = "discrepancy"


@dataclass
class Payment:
    """A received or made payment."""

    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    payment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = field(default_factory=date.today)
    reference: Optional[str] = None
    payer_id: Optional[str] = None
    payee_id: Optional[str] = None
    invoice_id: Optional[str] = None
    notes: str = ""
    is_reconciled: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.amount, (int, float)):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if self.amount <= 0:
            raise ValueError("Payment amount must be positive")


@dataclass
class ReconciliationResult:
    """The outcome of matching a payment to an invoice."""

    payment: Payment
    invoice: Optional[Invoice]
    status: ReconciliationStatus
    matched_amount: Decimal
    difference: Decimal
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notes: str = ""

    @property
    def is_fully_reconciled(self) -> bool:
        """True if the payment exactly covers the invoice."""
        return self.status == ReconciliationStatus.MATCHED


@dataclass
class ReconciliationReport:
    """Summary of a reconciliation run."""

    results: list[ReconciliationResult]
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: date = field(default_factory=date.today)

    @property
    def total_payments(self) -> int:
        """Number of payments processed."""
        return len(self.results)

    @property
    def matched_count(self) -> int:
        """Number of fully matched payments."""
        return sum(1 for r in self.results if r.status == ReconciliationStatus.MATCHED)

    @property
    def partial_count(self) -> int:
        """Number of partially matched payments."""
        return sum(1 for r in self.results if r.status == ReconciliationStatus.PARTIAL)

    @property
    def overpayment_count(self) -> int:
        """Number of overpayments."""
        return sum(1 for r in self.results if r.status == ReconciliationStatus.OVERPAYMENT)

    @property
    def unmatched_count(self) -> int:
        """Number of unmatched payments."""
        return sum(1 for r in self.results if r.status == ReconciliationStatus.UNMATCHED)

    @property
    def discrepancy_count(self) -> int:
        """Number of payments with discrepancies."""
        return sum(1 for r in self.results if r.status == ReconciliationStatus.DISCREPANCY)

    @property
    def total_matched_amount(self) -> Decimal:
        """Sum of all matched amounts."""
        return sum(r.matched_amount for r in self.results)

    @property
    def total_difference(self) -> Decimal:
        """Sum of all differences (over/under payments)."""
        return sum(abs(r.difference) for r in self.results)

    @property
    def reconciliation_rate(self) -> float:
        """Fraction of payments that were fully matched."""
        if not self.results:
            return 0.0
        return self.matched_count / len(self.results)

    def unmatched_payments(self) -> list[Payment]:
        """Return all payments that could not be matched."""
        return [
            r.payment for r in self.results
            if r.status == ReconciliationStatus.UNMATCHED
        ]

    def discrepancies(self) -> list[ReconciliationResult]:
        """Return all results flagged as discrepancies."""
        return [
            r for r in self.results
            if r.status == ReconciliationStatus.DISCREPANCY
        ]


class ReconciliationEngine:
    """Match payments to invoices and produce reconciliation reports."""

    def __init__(self, tolerance: Decimal = Decimal("0.01")) -> None:
        self.tolerance = tolerance
        self._payments: dict[str, Payment] = {}
        self._invoices: dict[str, Invoice] = {}

    # -- registration -------------------------------------------------------

    def register_payment(self, payment: Payment) -> None:
        """Add a payment to the engine."""
        self._payments[payment.payment_id] = payment

    def register_invoice(self, invoice: Invoice) -> None:
        """Add an invoice to the engine."""
        self._invoices[invoice.invoice_id] = invoice

    def register_payments(self, payments: list[Payment]) -> None:
        """Bulk-register payments."""
        for p in payments:
            self.register_payment(p)

    def register_invoices(self, invoices: list[Invoice]) -> None:
        """Bulk-register invoices."""
        for inv in invoices:
            self.register_invoice(inv)

    # -- matching -----------------------------------------------------------

    def match_by_invoice_id(self, payment: Payment) -> ReconciliationResult:
        """Match a payment to an invoice using ``payment.invoice_id``."""
        if not payment.invoice_id:
            return ReconciliationResult(
                payment=payment,
                invoice=None,
                status=ReconciliationStatus.UNMATCHED,
                matched_amount=Decimal("0"),
                difference=payment.amount,
                notes="No invoice_id on payment",
            )

        invoice = self._invoices.get(payment.invoice_id)
        if invoice is None:
            return ReconciliationResult(
                payment=payment,
                invoice=None,
                status=ReconciliationStatus.UNMATCHED,
                matched_amount=Decimal("0"),
                difference=payment.amount,
                notes=f"Invoice '{payment.invoice_id}' not found",
            )

        return self._reconcile(payment, invoice)

    def match_by_reference(self, payment: Payment) -> ReconciliationResult:
        """Match a payment to an invoice by reference string."""
        if not payment.reference:
            return ReconciliationResult(
                payment=payment,
                invoice=None,
                status=ReconciliationStatus.UNMATCHED,
                matched_amount=Decimal("0"),
                difference=payment.amount,
                notes="No reference on payment",
            )

        for invoice in self._invoices.values():
            # Match against invoice ID or any reference stored on the invoice
            if payment.reference == invoice.invoice_id:
                return self._reconcile(payment, invoice)

        return ReconciliationResult(
            payment=payment,
            invoice=None,
            status=ReconciliationStatus.UNMATCHED,
            matched_amount=Decimal("0"),
            difference=payment.amount,
            notes=f"No invoice matching reference '{payment.reference}'",
        )

    def match_by_amount(self, payment: Payment) -> ReconciliationResult:
        """Match a payment to an open invoice with the same amount."""
        candidates = [
            inv for inv in self._invoices.values()
            if inv.status != "paid"
            and inv.currency == payment.currency
            and abs(inv.amount_due - payment.amount) <= self.tolerance
        ]
        if not candidates:
            return ReconciliationResult(
                payment=payment,
                invoice=None,
                status=ReconciliationStatus.UNMATCHED,
                matched_amount=Decimal("0"),
                difference=payment.amount,
                notes="No open invoice with matching amount",
            )
        # Prefer the oldest invoice (FIFO)
        candidates.sort(key=lambda i: i.issue_date)
        return self._reconcile(payment, candidates[0])

    def auto_match(self, payment: Payment) -> ReconciliationResult:
        """Try all matching strategies in order."""
        # 1. Direct invoice ID
        result = self.match_by_invoice_id(payment)
        if result.status != ReconciliationStatus.UNMATCHED:
            return result

        # 2. Reference
        result = self.match_by_reference(payment)
        if result.status != ReconciliationStatus.UNMATCHED:
            return result

        # 3. Amount
        result = self.match_by_amount(payment)
        if result.status != ReconciliationStatus.UNMATCHED:
            return result

        return ReconciliationResult(
            payment=payment,
            invoice=None,
            status=ReconciliationStatus.UNMATCHED,
            matched_amount=Decimal("0"),
            difference=payment.amount,
            notes="No matching strategy succeeded",
        )

    def _reconcile(
        self,
        payment: Payment,
        invoice: Invoice,
    ) -> ReconciliationResult:
        """Compare a payment against an invoice and classify the result."""
        if payment.currency != invoice.currency:
            return ReconciliationResult(
                payment=payment,
                invoice=invoice,
                status=ReconciliationStatus.DISCREPANCY,
                matched_amount=Decimal("0"),
                difference=payment.amount,
                notes=f"Currency mismatch: {payment.currency} vs {invoice.currency}",
            )

        diff = payment.amount - invoice.amount_due

        if abs(diff) <= self.tolerance:
            status = ReconciliationStatus.MATCHED
            matched = invoice.amount_due
        elif diff < 0:
            status = ReconciliationStatus.PARTIAL
            matched = payment.amount
        else:
            status = ReconciliationStatus.OVERPAYMENT
            matched = invoice.amount_due

        return ReconciliationResult(
            payment=payment,
            invoice=invoice,
            status=status,
            matched_amount=matched,
            difference=diff,
        )

    # -- batch processing ---------------------------------------------------

    def reconcile_all(self) -> ReconciliationReport:
        """Reconcile all registered payments and return a report."""
        results: list[ReconciliationResult] = []
        for payment in self._payments.values():
            result = self.auto_match(payment)
            results.append(result)
            if result.status in (
                ReconciliationStatus.MATCHED,
                ReconciliationStatus.PARTIAL,
                ReconciliationStatus.OVERPAYMENT,
            ):
                payment.is_reconciled = True
        return ReconciliationReport(results=results)

    def reconcile_payment(self, payment_id: str) -> ReconciliationResult:
        """Reconcile a single payment by ID."""
        if payment_id not in self._payments:
            raise KeyError(f"Payment '{payment_id}' not found")
        payment = self._payments[payment_id]
        result = self.auto_match(payment)
        if result.status in (
            ReconciliationStatus.MATCHED,
            ReconciliationStatus.PARTIAL,
            ReconciliationStatus.OVERPAYMENT,
        ):
            payment.is_reconciled = True
        return result

    # -- queries ------------------------------------------------------------

    @property
    def unreconciled_payments(self) -> list[Payment]:
        """All payments not yet reconciled."""
        return [p for p in self._payments.values() if not p.is_reconciled]

    @property
    def reconciled_payments(self) -> list[Payment]:
        """All payments that have been reconciled."""
        return [p for p in self._payments.values() if p.is_reconciled]
