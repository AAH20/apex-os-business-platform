"""Invoice generation engine."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.billing.models import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Subscription,
)


class InvoiceGenerator:
    """Generates and manages invoices."""

    def __init__(self):
        self._invoices: Dict[str, Invoice] = {}

    def create_invoice(
        self,
        customer_id: str,
        subscription_id: Optional[str] = None,
        currency: str = "USD",
        due_days: int = 30,
    ) -> Invoice:
        """Create a new draft invoice."""
        invoice = Invoice.create(
            customer_id=customer_id,
            subscription_id=subscription_id,
            currency=currency,
            due_days=due_days,
        )
        self._invoices[invoice.id] = invoice
        return invoice

    def add_line_item(
        self,
        invoice_id: str,
        description: str,
        quantity: float,
        unit_price: float,
    ) -> Invoice:
        """Add a line item to an invoice."""
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(f"Cannot modify invoice with status: {invoice.status.value}")
        invoice.add_line(InvoiceLine(
            description=description,
            quantity=quantity,
            unit_price=unit_price,
        ))
        return invoice

    def apply_tax(self, invoice_id: str, tax_rate: float) -> Invoice:
        """Apply tax rate to an invoice."""
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        invoice.apply_tax(tax_rate)
        return invoice

    def finalize_invoice(self, invoice_id: str) -> Invoice:
        """Finalize a draft invoice, making it open for payment."""
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(f"Cannot finalize invoice with status: {invoice.status.value}")
        if not invoice.lines:
            raise ValueError("Cannot finalize invoice with no line items")
        invoice.status = InvoiceStatus.OPEN
        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        return self._invoices.get(invoice_id)

    def get_customer_invoices(self, customer_id: str) -> List[Invoice]:
        """Get all invoices for a customer."""
        return [i for i in self._invoices.values() if i.customer_id == customer_id]

    def get_open_invoices(self) -> List[Invoice]:
        """Get all open invoices."""
        return [i for i in self._invoices.values() if i.status == InvoiceStatus.OPEN]

    def get_overdue_invoices(self) -> List[Invoice]:
        """Get all overdue invoices."""
        return [i for i in self._invoices.values() if i.is_overdue()]

    def void_invoice(self, invoice_id: str) -> Invoice:
        """Void an invoice."""
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("Cannot void a paid invoice")
        invoice.mark_void()
        return invoice

    def mark_paid(self, invoice_id: str) -> Invoice:
        """Mark an invoice as paid."""
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        invoice.mark_paid()
        return invoice

    def generate_subscription_invoice(
        self,
        subscription: Subscription,
        tax_rate: float = 0.0,
    ) -> Invoice:
        """Generate a complete invoice for a subscription."""
        invoice = self.create_invoice(
            customer_id=subscription.customer_id,
            subscription_id=subscription.id,
            currency=subscription.plan.currency,
        )
        self.add_line_item(
            invoice_id=invoice.id,
            description=f"{subscription.plan.name} subscription",
            quantity=1,
            unit_price=subscription.plan.price,
        )
        if tax_rate > 0:
            self.apply_tax(invoice.id, tax_rate)
        return self.finalize_invoice(invoice.id)
