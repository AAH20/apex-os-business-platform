"""Dunning management engine."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.billing.models import (
    DunningAction,
    DunningRecord,
    DunningStatus,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
)


class DunningManager:
    """Manages dunning process for failed payments."""

    DEFAULT_SEQUENCE = [
        DunningAction.EMAIL_REMINDER,
        DunningAction.FINAL_NOTICE,
        DunningAction.ACCOUNT_SUSPENSION,
    ]

    def __init__(self):
        self._records: Dict[str, DunningRecord] = {}
        self._sequence: List[DunningAction] = list(self.DEFAULT_SEQUENCE)

    def start_dunning(
        self,
        customer_id: str,
        invoice_id: str,
        subscription_id: Optional[str] = None,
        max_attempts: int = 3,
    ) -> DunningRecord:
        """Start dunning process for a failed payment."""
        record = DunningRecord.create(
            customer_id=customer_id,
            invoice_id=invoice_id,
            subscription_id=subscription_id,
            max_attempts=max_attempts,
        )
        self._records[record.id] = record
        return record

    def get_record(self, record_id: str) -> Optional[DunningRecord]:
        """Get dunning record by ID."""
        return self._records.get(record_id)

    def get_customer_records(self, customer_id: str) -> List[DunningRecord]:
        """Get all dunning records for a customer."""
        return [r for r in self._records.values() if r.customer_id == customer_id]

    def get_pending_records(self) -> List[DunningRecord]:
        """Get all pending dunning records."""
        return [r for r in self._records.values() if r.status == DunningStatus.PENDING]

    def get_active_records(self) -> List[DunningRecord]:
        """Get all active (non-resolved) dunning records."""
        return [r for r in self._records.values() if not r.is_resolved()]

    def execute_next_action(self, record_id: str) -> DunningRecord:
        """Execute the next dunning action in sequence."""
        record = self._records.get(record_id)
        if not record:
            raise ValueError(f"Dunning record not found: {record_id}")
        if not record.can_retry():
            raise ValueError(f"Dunning record cannot be retried: {record_id}")

        action_index = min(record.attempt, len(self._sequence) - 1)
        action = self._sequence[action_index]
        record.add_action(action)
        record.status = DunningStatus.SENT

        if record.attempt >= record.max_attempts:
            record.mark_escalated()

        return record

    def resolve(self, record_id: str) -> DunningRecord:
        """Mark a dunning record as resolved."""
        record = self._records.get(record_id)
        if not record:
            raise ValueError(f"Dunning record not found: {record_id}")
        record.mark_resolved()
        return record

    def process_dunning(
        self,
        invoice: Invoice,
        payment: Optional[Payment] = None,
        subscription: Optional[Subscription] = None,
    ) -> Optional[DunningRecord]:
        """Process dunning for an invoice, creating or advancing a record."""
        # Find existing active record for this invoice
        existing = None
        for record in self._records.values():
            if record.invoice_id == invoice.id and not record.is_resolved():
                existing = record
                break

        if existing:
            if payment and payment.status == PaymentStatus.SUCCEEDED:
                self.resolve(existing.id)
                return existing
            return self.execute_next_action(existing.id)

        # Create new dunning record
        record = self.start_dunning(
            customer_id=invoice.customer_id,
            invoice_id=invoice.id,
            subscription_id=invoice.subscription_id,
        )
        return self.execute_next_action(record.id)

    def handle_payment_success(
        self,
        invoice: Invoice,
        payment: Payment,
    ) -> Optional[DunningRecord]:
        """Handle successful payment during dunning."""
        for record in self._records.values():
            if record.invoice_id == invoice.id and not record.is_resolved():
                self.resolve(record.id)
                return record
        return None

    def handle_payment_failure(
        self,
        invoice: Invoice,
        payment: Payment,
        subscription: Optional[Subscription] = None,
    ) -> DunningRecord:
        """Handle failed payment, advancing dunning process."""
        return self.process_dunning(invoice, payment, subscription)

    def get_escalated_records(self) -> List[DunningRecord]:
        """Get all escalated dunning records."""
        return [r for r in self._records.values() if r.status == DunningStatus.ESCALATED]

    def get_resolved_records(self) -> List[DunningRecord]:
        """Get all resolved dunning records."""
        return [r for r in self._records.values() if r.is_resolved()]

    def set_sequence(self, sequence: List[DunningAction]) -> None:
        """Set a custom dunning action sequence."""
        if not sequence:
            raise ValueError("Dunning sequence cannot be empty")
        self._sequence = list(sequence)

    def get_sequence(self) -> List[DunningAction]:
        """Get the current dunning action sequence."""
        return list(self._sequence)
