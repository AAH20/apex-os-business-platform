"""Payment processing engine."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from apex_os_bp.billing.models import (
    Invoice,
    Payment,
    PaymentMethod,
    PaymentStatus,
)


class PaymentProcessor:
    """Processes payments and manages payment lifecycle."""

    def __init__(self):
        self._payments: Dict[str, Payment] = {}

    def process_payment(
        self,
        invoice_id: str,
        customer_id: str,
        amount: float,
        method: PaymentMethod = PaymentMethod.CREDIT_CARD,
        currency: str = "USD",
    ) -> Payment:
        """Process a payment for an invoice."""
        payment = Payment.create(
            invoice_id=invoice_id,
            customer_id=customer_id,
            amount=amount,
            method=method,
            currency=currency,
        )
        # Simulate payment processing
        transaction_id = str(uuid.uuid4())
        payment.mark_succeeded(transaction_id)
        self._payments[payment.id] = payment
        return payment

    def process_payment_with_result(
        self,
        invoice_id: str,
        customer_id: str,
        amount: float,
        method: PaymentMethod = PaymentMethod.CREDIT_CARD,
        currency: str = "USD",
        simulate_failure: bool = False,
        failure_reason: str = "Card declined",
    ) -> Payment:
        """Process a payment with explicit success/failure control."""
        payment = Payment.create(
            invoice_id=invoice_id,
            customer_id=customer_id,
            amount=amount,
            method=method,
            currency=currency,
        )
        if simulate_failure:
            payment.mark_failed(failure_reason)
        else:
            transaction_id = str(uuid.uuid4())
            payment.mark_succeeded(transaction_id)
        self._payments[payment.id] = payment
        return payment

    def refund_payment(self, payment_id: str) -> Payment:
        """Refund a payment."""
        payment = self._payments.get(payment_id)
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")
        if payment.status != PaymentStatus.SUCCEEDED:
            raise ValueError(f"Cannot refund payment with status: {payment.status.value}")
        payment.mark_refunded()
        return payment

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        return self._payments.get(payment_id)

    def get_invoice_payments(self, invoice_id: str) -> List[Payment]:
        """Get all payments for an invoice."""
        return [p for p in self._payments.values() if p.invoice_id == invoice_id]

    def get_customer_payments(self, customer_id: str) -> List[Payment]:
        """Get all payments for a customer."""
        return [p for p in self._payments.values() if p.customer_id == customer_id]

    def get_successful_payments(self) -> List[Payment]:
        """Get all successful payments."""
        return [p for p in self._payments.values() if p.status == PaymentStatus.SUCCEEDED]

    def get_failed_payments(self) -> List[Payment]:
        """Get all failed payments."""
        return [p for p in self._payments.values() if p.status == PaymentStatus.FAILED]

    def reconcile_invoice(self, invoice: Invoice) -> bool:
        """Check if an invoice is fully paid."""
        payments = self.get_invoice_payments(invoice.id)
        total_paid = sum(p.amount for p in payments if p.status == PaymentStatus.SUCCEEDED)
        return total_paid >= invoice.total

    def settle_invoice(self, invoice: Invoice) -> bool:
        """Settle an invoice if fully paid."""
        if self.reconcile_invoice(invoice):
            invoice.mark_paid()
            return True
        return False
