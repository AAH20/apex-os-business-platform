"""Tests for billing module."""
import pytest
from datetime import datetime, timedelta

from apex_os_bp.billing.models import (
    BillingCycle,
    DunningAction,
    DunningRecord,
    DunningStatus,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    UsageRecord,
)
from apex_os_bp.billing.subscription import SubscriptionBilling
from apex_os_bp.billing.usage import UsageBilling
from apex_os_bp.billing.invoice import InvoiceGenerator
from apex_os_bp.billing.payment import PaymentProcessor
from apex_os_bp.billing.dunning import DunningManager


# ============================================================================
# Model Tests
# ============================================================================

class TestSubscriptionPlan:
    """Test subscription plan model."""

    def test_plan_creation(self):
        """Plan can be created with required fields."""
        plan = SubscriptionPlan.create(
            name="Pro Plan",
            price=99.99,
            currency="USD",
            billing_cycle=BillingCycle.MONTHLY,
        )
        assert plan.name == "Pro Plan"
        assert plan.price == 99.99
        assert plan.currency == "USD"
        assert plan.billing_cycle == BillingCycle.MONTHLY
        assert plan.id is not None

    def test_plan_with_features(self):
        """Plan supports feature list."""
        plan = SubscriptionPlan.create(
            name="Enterprise",
            price=499.99,
            features=["unlimited_users", "api_access", "priority_support"],
        )
        assert len(plan.features) == 3
        assert "api_access" in plan.features

    def test_plan_with_usage_limits(self):
        """Plan supports usage limits and overage rates."""
        plan = SubscriptionPlan.create(
            name="Metered",
            price=49.99,
            usage_limits={"api_calls": 10000, "storage_gb": 100},
            overage_rates={"api_calls": 0.001, "storage_gb": 0.10},
        )
        assert plan.usage_limits["api_calls"] == 10000
        assert plan.overage_rates["storage_gb"] == 0.10


class TestSubscription:
    """Test subscription model."""

    def test_subscription_creation(self):
        """Subscription can be created."""
        plan = SubscriptionPlan.create(name="Basic", price=29.99)
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        assert sub.customer_id == "cust-1"
        assert sub.plan.name == "Basic"
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.auto_renew is True

    def test_subscription_with_trial(self):
        """Subscription with trial period."""
        plan = SubscriptionPlan.create(name="Pro", price=99.99)
        sub = Subscription.create(customer_id="cust-1", plan=plan, trial_days=14)
        assert sub.status == SubscriptionStatus.TRIALING
        assert sub.trial_end is not None
        assert sub.trial_end > datetime.now()

    def test_subscription_cancel(self):
        """Subscription can be canceled."""
        plan = SubscriptionPlan.create(name="Basic", price=29.99)
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        sub.cancel()
        assert sub.status == SubscriptionStatus.CANCELED
        assert sub.auto_renew is False

    def test_subscription_renew(self):
        """Subscription can be renewed."""
        plan = SubscriptionPlan.create(name="Basic", price=29.99)
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        sub.renew()
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.end_date is not None

    def test_canceled_subscription_cannot_renew(self):
        """Canceled subscription cannot be renewed."""
        plan = SubscriptionPlan.create(name="Basic", price=29.99)
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        sub.cancel()
        with pytest.raises(ValueError, match="Cannot renew a canceled subscription"):
            sub.renew()

    def test_is_active(self):
        """Active check works correctly."""
        plan = SubscriptionPlan.create(name="Basic", price=29.99)
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        assert sub.is_active() is True
        sub.cancel()
        assert sub.is_active() is False


class TestInvoice:
    """Test invoice model."""

    def test_invoice_creation(self):
        """Invoice can be created."""
        invoice = Invoice.create(customer_id="cust-1")
        assert invoice.customer_id == "cust-1"
        assert invoice.status == InvoiceStatus.DRAFT
        assert invoice.total == 0.0

    def test_add_line_item(self):
        """Line items can be added to invoice."""
        invoice = Invoice.create(customer_id="cust-1")
        invoice.add_line(InvoiceLine(description="Service", quantity=2, unit_price=50.0))
        assert len(invoice.lines) == 1
        assert invoice.subtotal == 100.0
        assert invoice.total == 100.0

    def test_apply_tax(self):
        """Tax can be applied to invoice."""
        invoice = Invoice.create(customer_id="cust-1")
        invoice.add_line(InvoiceLine(description="Service", quantity=1, unit_price=100.0))
        invoice.apply_tax(0.1)
        assert invoice.tax == 10.0
        assert invoice.total == 110.0

    def test_mark_paid(self):
        """Invoice can be marked as paid."""
        invoice = Invoice.create(customer_id="cust-1")
        invoice.mark_paid()
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.paid_at is not None

    def test_mark_void(self):
        """Invoice can be voided."""
        invoice = Invoice.create(customer_id="cust-1")
        invoice.mark_void()
        assert invoice.status == InvoiceStatus.VOID

    def test_is_overdue(self):
        """Overdue check works correctly."""
        invoice = Invoice.create(customer_id="cust-1")
        invoice.status = InvoiceStatus.OPEN
        invoice.due_date = datetime.now() - timedelta(days=1)
        assert invoice.is_overdue() is True

    def test_is_not_overdue(self):
        """Non-overdue invoice check."""
        invoice = Invoice.create(customer_id="cust-1")
        invoice.status = InvoiceStatus.OPEN
        invoice.due_date = datetime.now() + timedelta(days=7)
        assert invoice.is_overdue() is False

    def test_paid_invoice_not_overdue(self):
        """Paid invoice is never overdue."""
        invoice = Invoice.create(customer_id="cust-1")
        invoice.status = InvoiceStatus.PAID
        invoice.due_date = datetime.now() - timedelta(days=1)
        assert invoice.is_overdue() is False


class TestPayment:
    """Test payment model."""

    def test_payment_creation(self):
        """Payment can be created."""
        payment = Payment.create(
            invoice_id="inv-1",
            customer_id="cust-1",
            amount=100.0,
        )
        assert payment.invoice_id == "inv-1"
        assert payment.customer_id == "cust-1"
        assert payment.amount == 100.0
        assert payment.status == PaymentStatus.PENDING

    def test_mark_succeeded(self):
        """Payment can be marked as succeeded."""
        payment = Payment.create(invoice_id="inv-1", customer_id="cust-1", amount=100.0)
        payment.mark_succeeded("txn-123")
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.transaction_id == "txn-123"

    def test_mark_failed(self):
        """Payment can be marked as failed."""
        payment = Payment.create(invoice_id="inv-1", customer_id="cust-1", amount=100.0)
        payment.mark_failed("Insufficient funds")
        assert payment.status == PaymentStatus.FAILED
        assert payment.failure_reason == "Insufficient funds"

    def test_mark_refunded(self):
        """Payment can be marked as refunded."""
        payment = Payment.create(invoice_id="inv-1", customer_id="cust-1", amount=100.0)
        payment.mark_succeeded("txn-123")
        payment.mark_refunded()
        assert payment.status == PaymentStatus.REFUNDED


class TestDunningRecord:
    """Test dunning record model."""

    def test_dunning_record_creation(self):
        """Dunning record can be created."""
        record = DunningRecord.create(
            customer_id="cust-1",
            invoice_id="inv-1",
        )
        assert record.customer_id == "cust-1"
        assert record.invoice_id == "inv-1"
        assert record.status == DunningStatus.PENDING
        assert record.attempt == 0

    def test_add_action(self):
        """Actions can be added to dunning record."""
        record = DunningRecord.create(customer_id="cust-1", invoice_id="inv-1")
        record.add_action(DunningAction.EMAIL_REMINDER)
        assert len(record.actions) == 1
        assert record.attempt == 1

    def test_mark_resolved(self):
        """Dunning record can be resolved."""
        record = DunningRecord.create(customer_id="cust-1", invoice_id="inv-1")
        record.mark_resolved()
        assert record.status == DunningStatus.RESOLVED
        assert record.resolved_at is not None

    def test_mark_escalated(self):
        """Dunning record can be escalated."""
        record = DunningRecord.create(customer_id="cust-1", invoice_id="inv-1")
        record.mark_escalated()
        assert record.status == DunningStatus.ESCALATED

    def test_can_retry(self):
        """Retry check works correctly."""
        record = DunningRecord.create(customer_id="cust-1", invoice_id="inv-1", max_attempts=3)
        assert record.can_retry() is True
        record.add_action(DunningAction.EMAIL_REMINDER)
        record.add_action(DunningAction.FINAL_NOTICE)
        record.add_action(DunningAction.ACCOUNT_SUSPENSION)
        assert record.can_retry() is False

    def test_is_resolved(self):
        """Resolved check works correctly."""
        record = DunningRecord.create(customer_id="cust-1", invoice_id="inv-1")
        assert record.is_resolved() is False
        record.mark_resolved()
        assert record.is_resolved() is True


class TestUsageRecord:
    """Test usage record model."""

    def test_usage_record_creation(self):
        """Usage record can be created."""
        record = UsageRecord.record(
            customer_id="cust-1",
            subscription_id="sub-1",
            metric="api_calls",
            quantity=150.0,
        )
        assert record.customer_id == "cust-1"
        assert record.subscription_id == "sub-1"
        assert record.metric == "api_calls"
        assert record.quantity == 150.0


# ============================================================================
# Subscription Billing Tests
# ============================================================================

class TestSubscriptionBilling:
    """Test subscription billing engine."""

    def test_create_plan(self):
        """Plan can be created via billing engine."""
        billing = SubscriptionBilling()
        plan = billing.create_plan(name="Starter", price=19.99)
        assert plan.name == "Starter"
        assert plan.price == 19.99
        assert billing.get_plan(plan.id) == plan

    def test_create_subscription(self):
        """Subscription can be created via billing engine."""
        billing = SubscriptionBilling()
        plan = billing.create_plan(name="Pro", price=99.99)
        sub = billing.create_subscription(customer_id="cust-1", plan_id=plan.id)
        assert sub.customer_id == "cust-1"
        assert sub.plan.id == plan.id
        assert sub.status == SubscriptionStatus.ACTIVE

    def test_create_subscription_invalid_plan(self):
        """Creating subscription with invalid plan raises error."""
        billing = SubscriptionBilling()
        with pytest.raises(ValueError, match="Plan not found"):
            billing.create_subscription(customer_id="cust-1", plan_id="nonexistent")

    def test_get_subscription(self):
        """Subscription can be retrieved."""
        billing = SubscriptionBilling()
        plan = billing.create_plan(name="Basic", price=29.99)
        sub = billing.create_subscription(customer_id="cust-1", plan_id=plan.id)
        assert billing.get_subscription(sub.id) == sub

    def test_cancel_subscription(self):
        """Subscription can be canceled via billing engine."""
        billing = SubscriptionBilling()
        plan = billing.create_plan(name="Basic", price=29.99)
        sub = billing.create_subscription(customer_id="cust-1", plan_id=plan.id)
        canceled = billing.cancel_subscription(sub.id)
        assert canceled.status == SubscriptionStatus.CANCELED

    def test_renew_subscription(self):
        """Subscription can be renewed via billing engine."""
        billing = SubscriptionBilling()
        plan = billing.create_plan(name="Basic", price=29.99)
        sub = billing.create_subscription(customer_id="cust-1", plan_id=plan.id)
        renewed = billing.renew_subscription(sub.id)
        assert renewed.status == SubscriptionStatus.ACTIVE
        assert renewed.end_date is not None

    def test_generate_invoice(self):
        """Invoice can be generated for subscription."""
        billing = SubscriptionBilling()
        plan = billing.create_plan(name="Pro", price=99.99)
        sub = billing.create_subscription(customer_id="cust-1", plan_id=plan.id)
        invoice = billing.generate_invoice(sub.id)
        assert invoice.customer_id == "cust-1"
        assert invoice.subscription_id == sub.id
        assert invoice.total == 99.99
        assert len(invoice.lines) == 1

    def test_get_customer_subscriptions(self):
        """Customer subscriptions can be retrieved."""
        billing = SubscriptionBilling()
        plan = billing.create_plan(name="Basic", price=29.99)
        sub1 = billing.create_subscription(customer_id="cust-1", plan_id=plan.id)
        sub2 = billing.create_subscription(customer_id="cust-1", plan_id=plan.id)
        billing.create_subscription(customer_id="cust-2", plan_id=plan.id)
        subs = billing.get_customer_subscriptions("cust-1")
        assert len(subs) == 2

    def test_get_active_subscriptions(self):
        """Active subscriptions can be retrieved."""
        billing = SubscriptionBilling()
        plan = billing.create_plan(name="Basic", price=29.99)
        sub1 = billing.create_subscription(customer_id="cust-1", plan_id=plan.id)
        sub2 = billing.create_subscription(customer_id="cust-2", plan_id=plan.id)
        billing.cancel_subscription(sub2.id)
        active = billing.get_active_subscriptions()
        assert len(active) == 1
        assert active[0].id == sub1.id

    def test_process_renewals(self):
        """Renewals can be processed for expired subscriptions."""
        billing = SubscriptionBilling()
        plan = billing.create_plan(name="Basic", price=29.99)
        sub = billing.create_subscription(customer_id="cust-1", plan_id=plan.id)
        # Manually set end date to past
        sub.end_date = datetime.now() - timedelta(days=1)
        renewed = billing.process_renewals()
        assert len(renewed) == 1
        assert renewed[0].status == SubscriptionStatus.ACTIVE


# ============================================================================
# Usage Billing Tests
# ============================================================================

class TestUsageBilling:
    """Test usage-based billing engine."""

    def test_record_usage(self):
        """Usage can be recorded."""
        usage = UsageBilling()
        record = usage.record_usage(
            customer_id="cust-1",
            subscription_id="sub-1",
            metric="api_calls",
            quantity=500.0,
        )
        assert record.metric == "api_calls"
        assert record.quantity == 500.0

    def test_get_usage(self):
        """Usage records can be retrieved."""
        usage = UsageBilling()
        usage.record_usage("cust-1", "sub-1", "api_calls", 100.0)
        usage.record_usage("cust-1", "sub-1", "api_calls", 200.0)
        usage.record_usage("cust-1", "sub-1", "storage_gb", 50.0)
        records = usage.get_usage("sub-1")
        assert len(records) == 3

    def test_get_usage_filtered_by_metric(self):
        """Usage records can be filtered by metric."""
        usage = UsageBilling()
        usage.record_usage("cust-1", "sub-1", "api_calls", 100.0)
        usage.record_usage("cust-1", "sub-1", "storage_gb", 50.0)
        records = usage.get_usage("sub-1", metric="api_calls")
        assert len(records) == 1
        assert records[0].metric == "api_calls"

    def test_get_total_usage(self):
        """Total usage can be calculated."""
        usage = UsageBilling()
        usage.record_usage("cust-1", "sub-1", "api_calls", 100.0)
        usage.record_usage("cust-1", "sub-1", "api_calls", 200.0)
        usage.record_usage("cust-1", "sub-1", "api_calls", 300.0)
        total = usage.get_total_usage("sub-1", "api_calls")
        assert total == 600.0

    def test_calculate_overage_no_excess(self):
        """No overage when usage is within limits."""
        usage = UsageBilling()
        plan = SubscriptionPlan.create(
            name="Metered",
            price=49.99,
            usage_limits={"api_calls": 10000},
            overage_rates={"api_calls": 0.001},
        )
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        usage.record_usage("cust-1", sub.id, "api_calls", 5000.0)
        overages = usage.calculate_overage(sub)
        assert len(overages) == 0

    def test_calculate_overage_with_excess(self):
        """Overage is calculated when usage exceeds limits."""
        usage = UsageBilling()
        plan = SubscriptionPlan.create(
            name="Metered",
            price=49.99,
            usage_limits={"api_calls": 1000},
            overage_rates={"api_calls": 0.01},
        )
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        usage.record_usage("cust-1", sub.id, "api_calls", 1500.0)
        overages = usage.calculate_overage(sub)
        assert "api_calls" in overages
        assert overages["api_calls"] == 500.0 * 0.01  # 5.0

    def test_generate_usage_invoice(self):
        """Usage invoice can be generated."""
        usage = UsageBilling()
        plan = SubscriptionPlan.create(
            name="Metered",
            price=49.99,
            usage_limits={"api_calls": 1000},
            overage_rates={"api_calls": 0.01},
        )
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        usage.record_usage("cust-1", sub.id, "api_calls", 1500.0)
        invoice = usage.generate_usage_invoice(sub)
        assert invoice.customer_id == "cust-1"
        assert invoice.subscription_id == sub.id
        assert len(invoice.lines) == 1
        assert invoice.lines[0].description == "Overage: api_calls"
        assert invoice.total == 5.0

    def test_generate_usage_invoice_no_overage(self):
        """Usage invoice with no overage has no line items."""
        usage = UsageBilling()
        plan = SubscriptionPlan.create(
            name="Metered",
            price=49.99,
            usage_limits={"api_calls": 10000},
            overage_rates={"api_calls": 0.01},
        )
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        usage.record_usage("cust-1", sub.id, "api_calls", 1000.0)
        invoice = usage.generate_usage_invoice(sub)
        assert len(invoice.lines) == 0
        assert invoice.total == 0.0

    def test_reset_usage(self):
        """Usage can be reset for a subscription."""
        usage = UsageBilling()
        usage.record_usage("cust-1", "sub-1", "api_calls", 5000.0)
        usage.reset_usage("sub-1")
        records = usage.get_usage("sub-1")
        assert len(records) == 0


# ============================================================================
# Invoice Generator Tests
# ============================================================================

class TestInvoiceGenerator:
    """Test invoice generation engine."""

    def test_create_invoice(self):
        """Invoice can be created."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        assert invoice.customer_id == "cust-1"
        assert invoice.status == InvoiceStatus.DRAFT

    def test_add_line_item(self):
        """Line item can be added to invoice."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        gen.add_line_item(invoice.id, "Consulting", 10, 150.0)
        assert len(invoice.lines) == 1
        assert invoice.subtotal == 1500.0

    def test_add_line_item_to_nonexistent_invoice(self):
        """Adding line to nonexistent invoice raises error."""
        gen = InvoiceGenerator()
        with pytest.raises(ValueError, match="Invoice not found"):
            gen.add_line_item("nonexistent", "Test", 1, 100.0)

    def test_add_line_item_to_non_draft(self):
        """Adding line to non-draft invoice raises error."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        gen.add_line_item(invoice.id, "Service", 1, 100.0)
        gen.finalize_invoice(invoice.id)
        with pytest.raises(ValueError, match="Cannot modify invoice"):
            gen.add_line_item(invoice.id, "Test", 1, 100.0)

    def test_apply_tax(self):
        """Tax can be applied to invoice."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        gen.add_line_item(invoice.id, "Service", 1, 100.0)
        gen.apply_tax(invoice.id, 0.2)
        assert invoice.tax == 20.0
        assert invoice.total == 120.0

    def test_finalize_invoice(self):
        """Invoice can be finalized."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        gen.add_line_item(invoice.id, "Service", 1, 100.0)
        gen.finalize_invoice(invoice.id)
        assert invoice.status == InvoiceStatus.OPEN

    def test_finalize_empty_invoice_raises(self):
        """Finalizing empty invoice raises error."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        with pytest.raises(ValueError, match="no line items"):
            gen.finalize_invoice(invoice.id)

    def test_finalize_non_draft_raises(self):
        """Finalizing non-draft invoice raises error."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        gen.add_line_item(invoice.id, "Service", 1, 100.0)
        gen.finalize_invoice(invoice.id)
        with pytest.raises(ValueError, match="Cannot finalize"):
            gen.finalize_invoice(invoice.id)

    def test_get_invoice(self):
        """Invoice can be retrieved."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        assert gen.get_invoice(invoice.id) == invoice

    def test_get_customer_invoices(self):
        """Customer invoices can be retrieved."""
        gen = InvoiceGenerator()
        gen.create_invoice(customer_id="cust-1")
        gen.create_invoice(customer_id="cust-1")
        gen.create_invoice(customer_id="cust-2")
        invoices = gen.get_customer_invoices("cust-1")
        assert len(invoices) == 2

    def test_get_open_invoices(self):
        """Open invoices can be retrieved."""
        gen = InvoiceGenerator()
        inv1 = gen.create_invoice(customer_id="cust-1")
        gen.add_line_item(inv1.id, "Service", 1, 100.0)
        gen.finalize_invoice(inv1.id)
        gen.create_invoice(customer_id="cust-2")  # draft
        open_invoices = gen.get_open_invoices()
        assert len(open_invoices) == 1

    def test_get_overdue_invoices(self):
        """Overdue invoices can be retrieved."""
        gen = InvoiceGenerator()
        inv1 = gen.create_invoice(customer_id="cust-1")
        gen.add_line_item(inv1.id, "Service", 1, 100.0)
        gen.finalize_invoice(inv1.id)
        inv1.due_date = datetime.now() - timedelta(days=1)
        gen.create_invoice(customer_id="cust-2")  # draft, not overdue
        overdue = gen.get_overdue_invoices()
        assert len(overdue) == 1

    def test_void_invoice(self):
        """Invoice can be voided."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        gen.void_invoice(invoice.id)
        assert invoice.status == InvoiceStatus.VOID

    def test_void_paid_invoice_raises(self):
        """Voiding paid invoice raises error."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        invoice.mark_paid()
        with pytest.raises(ValueError, match="Cannot void a paid invoice"):
            gen.void_invoice(invoice.id)

    def test_mark_paid(self):
        """Invoice can be marked as paid."""
        gen = InvoiceGenerator()
        invoice = gen.create_invoice(customer_id="cust-1")
        gen.mark_paid(invoice.id)
        assert invoice.status == InvoiceStatus.PAID

    def test_generate_subscription_invoice(self):
        """Complete subscription invoice can be generated."""
        gen = InvoiceGenerator()
        plan = SubscriptionPlan.create(name="Pro", price=99.99)
        sub = Subscription.create(customer_id="cust-1", plan=plan)
        invoice = gen.generate_subscription_invoice(sub, tax_rate=0.1)
        assert invoice.customer_id == "cust-1"
        assert invoice.subscription_id == sub.id
        assert invoice.status == InvoiceStatus.OPEN
        assert invoice.subtotal == 99.99
        assert invoice.tax == 9.999
        assert abs(invoice.total - 109.989) < 0.01


# ============================================================================
# Payment Processor Tests
# ============================================================================

class TestPaymentProcessor:
    """Test payment processing engine."""

    def test_process_payment(self):
        """Payment can be processed."""
        proc = PaymentProcessor()
        payment = proc.process_payment(
            invoice_id="inv-1",
            customer_id="cust-1",
            amount=100.0,
        )
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.transaction_id is not None

    def test_process_payment_with_method(self):
        """Payment with specific method can be processed."""
        proc = PaymentProcessor()
        payment = proc.process_payment(
            invoice_id="inv-1",
            customer_id="cust-1",
            amount=100.0,
            method=PaymentMethod.BANK_TRANSFER,
        )
        assert payment.method == PaymentMethod.BANK_TRANSFER
        assert payment.status == PaymentStatus.SUCCEEDED

    def test_process_payment_failure(self):
        """Payment failure can be simulated."""
        proc = PaymentProcessor()
        payment = proc.process_payment_with_result(
            invoice_id="inv-1",
            customer_id="cust-1",
            amount=100.0,
            simulate_failure=True,
            failure_reason="Card declined",
        )
        assert payment.status == PaymentStatus.FAILED
        assert payment.failure_reason == "Card declined"

    def test_refund_payment(self):
        """Payment can be refunded."""
        proc = PaymentProcessor()
        payment = proc.process_payment(
            invoice_id="inv-1",
            customer_id="cust-1",
            amount=100.0,
        )
        proc.refund_payment(payment.id)
        assert payment.status == PaymentStatus.REFUNDED

    def test_refund_non_succeeded_raises(self):
        """Refunding non-succeeded payment raises error."""
        proc = PaymentProcessor()
        payment = proc.process_payment_with_result(
            invoice_id="inv-1",
            customer_id="cust-1",
            amount=100.0,
            simulate_failure=True,
        )
        with pytest.raises(ValueError, match="Cannot refund"):
            proc.refund_payment(payment.id)

    def test_get_payment(self):
        """Payment can be retrieved."""
        proc = PaymentProcessor()
        payment = proc.process_payment(
            invoice_id="inv-1",
            customer_id="cust-1",
            amount=100.0,
        )
        assert proc.get_payment(payment.id) == payment

    def test_get_invoice_payments(self):
        """Invoice payments can be retrieved."""
        proc = PaymentProcessor()
        proc.process_payment(invoice_id="inv-1", customer_id="cust-1", amount=100.0)
        proc.process_payment(invoice_id="inv-1", customer_id="cust-1", amount=50.0)
        proc.process_payment(invoice_id="inv-2", customer_id="cust-1", amount=75.0)
        payments = proc.get_invoice_payments("inv-1")
        assert len(payments) == 2

    def test_get_customer_payments(self):
        """Customer payments can be retrieved."""
        proc = PaymentProcessor()
        proc.process_payment(invoice_id="inv-1", customer_id="cust-1", amount=100.0)
        proc.process_payment(invoice_id="inv-2", customer_id="cust-1", amount=50.0)
        proc.process_payment(invoice_id="inv-3", customer_id="cust-2", amount=75.0)
        payments = proc.get_customer_payments("cust-1")
        assert len(payments) == 2

    def test_get_successful_payments(self):
        """Successful payments can be retrieved."""
        proc = PaymentProcessor()
        proc.process_payment(invoice_id="inv-1", customer_id="cust-1", amount=100.0)
        proc.process_payment_with_result(
            invoice_id="inv-2", customer_id="cust-1", amount=50.0, simulate_failure=True
        )
        successful = proc.get_successful_payments()
        assert len(successful) == 1

    def test_get_failed_payments(self):
        """Failed payments can be retrieved."""
        proc = PaymentProcessor()
        proc.process_payment(invoice_id="inv-1", customer_id="cust-1", amount=100.0)
        proc.process_payment_with_result(
            invoice_id="inv-2", customer_id="cust-1", amount=50.0, simulate_failure=True
        )
        failed = proc.get_failed_payments()
        assert len(failed) == 1

    def test_reconcile_invoice_paid(self):
        """Invoice reconciliation detects fully paid invoice."""
        proc = PaymentProcessor()
        invoice = Invoice.create(customer_id="cust-1")
        invoice.add_line(InvoiceLine(description="Test", quantity=1, unit_price=100.0))
        proc.process_payment(invoice_id=invoice.id, customer_id="cust-1", amount=100.0)
        assert proc.reconcile_invoice(invoice) is True

    def test_reconcile_invoice_unpaid(self):
        """Invoice reconciliation detects unpaid invoice."""
        proc = PaymentProcessor()
        invoice = Invoice.create(customer_id="cust-1")
        invoice.add_line(InvoiceLine(description="Test", quantity=1, unit_price=100.0))
        assert proc.reconcile_invoice(invoice) is False

    def test_settle_invoice(self):
        """Invoice can be settled when fully paid."""
        proc = PaymentProcessor()
        invoice = Invoice.create(customer_id="cust-1")
        invoice.add_line(InvoiceLine(description="Test", quantity=1, unit_price=100.0))
        invoice.status = InvoiceStatus.OPEN
        proc.process_payment(invoice_id=invoice.id, customer_id="cust-1", amount=100.0)
        result = proc.settle_invoice(invoice)
        assert result is True
        assert invoice.status == InvoiceStatus.PAID

    def test_settle_invoice_not_fully_paid(self):
        """Invoice cannot be settled when not fully paid."""
        proc = PaymentProcessor()
        invoice = Invoice.create(customer_id="cust-1")
        invoice.add_line(InvoiceLine(description="Test", quantity=1, unit_price=100.0))
        invoice.status = InvoiceStatus.OPEN
        result = proc.settle_invoice(invoice)
        assert result is False
        assert invoice.status == InvoiceStatus.OPEN


# ============================================================================
# Dunning Manager Tests
# ============================================================================

class TestDunningManager:
    """Test dunning management engine."""

    def test_start_dunning(self):
        """Dunning process can be started."""
        dm = DunningManager()
        record = dm.start_dunning(customer_id="cust-1", invoice_id="inv-1")
        assert record.customer_id == "cust-1"
        assert record.invoice_id == "inv-1"
        assert record.status == DunningStatus.PENDING

    def test_get_record(self):
        """Dunning record can be retrieved."""
        dm = DunningManager()
        record = dm.start_dunning(customer_id="cust-1", invoice_id="inv-1")
        assert dm.get_record(record.id) == record

    def test_get_customer_records(self):
        """Customer dunning records can be retrieved."""
        dm = DunningManager()
        dm.start_dunning(customer_id="cust-1", invoice_id="inv-1")
        dm.start_dunning(customer_id="cust-1", invoice_id="inv-2")
        dm.start_dunning(customer_id="cust-2", invoice_id="inv-3")
        records = dm.get_customer_records("cust-1")
        assert len(records) == 2

    def test_get_pending_records(self):
        """Pending dunning records can be retrieved."""
        dm = DunningManager()
        dm.start_dunning(customer_id="cust-1", invoice_id="inv-1")
        record2 = dm.start_dunning(customer_id="cust-2", invoice_id="inv-2")
        dm.resolve(record2.id)
        pending = dm.get_pending_records()
        assert len(pending) == 1

    def test_get_active_records(self):
        """Active dunning records can be retrieved."""
        dm = DunningManager()
        dm.start_dunning(customer_id="cust-1", invoice_id="inv-1")
        record2 = dm.start_dunning(customer_id="cust-2", invoice_id="inv-2")
        dm.resolve(record2.id)
        active = dm.get_active_records()
        assert len(active) == 1

    def test_execute_next_action(self):
        """Next dunning action can be executed."""
        dm = DunningManager()
        record = dm.start_dunning(customer_id="cust-1", invoice_id="inv-1")
        dm.execute_next_action(record.id)
        assert record.attempt == 1
        assert record.actions[0] == DunningAction.EMAIL_REMINDER
        assert record.status == DunningStatus.SENT

    def test_execute_multiple_actions(self):
        """Multiple dunning actions can be executed."""
        dm = DunningManager()
        record = dm.start_dunning(customer_id="cust-1", invoice_id="inv-1", max_attempts=3)
        dm.execute_next_action(record.id)
        dm.execute_next_action(record.id)
        assert record.attempt == 2
        assert record.actions[0] == DunningAction.EMAIL_REMINDER
        assert record.actions[1] == DunningAction.FINAL_NOTICE

    def test_escalation_after_max_attempts(self):
        """Dunning escalates after max attempts reached."""
        dm = DunningManager()
        record = dm.start_dunning(customer_id="cust-1", invoice_id="inv-1", max_attempts=2)
        dm.execute_next_action(record.id)
        dm.execute_next_action(record.id)
        assert record.status == DunningStatus.ESCALATED

    def test_execute_action_on_resolved_raises(self):
        """Executing action on resolved record raises error."""
        dm = DunningManager()
        record = dm.start_dunning(customer_id="cust-1", invoice_id="inv-1")
        dm.resolve(record.id)
        with pytest.raises(ValueError, match="cannot be retried"):
            dm.execute_next_action(record.id)

    def test_resolve(self):
        """Dunning record can be resolved."""
        dm = DunningManager()
        record = dm.start_dunning(customer_id="cust-1", invoice_id="inv-1")
        dm.resolve(record.id)
        assert record.status == DunningStatus.RESOLVED
        assert record.resolved_at is not None

    def test_process_dunning_creates_new(self):
        """Processing dunning creates new record for new invoice."""
        dm = DunningManager()
        invoice = Invoice.create(customer_id="cust-1")
        record = dm.process_dunning(invoice)
        assert record.invoice_id == invoice.id
        assert record.attempt == 1

    def test_process_dunning_advances_existing(self):
        """Processing dunning advances existing record."""
        dm = DunningManager()
        invoice = Invoice.create(customer_id="cust-1")
        record1 = dm.process_dunning(invoice)
        record2 = dm.process_dunning(invoice)
        assert record1.id == record2.id
        assert record2.attempt == 2

    def test_process_dunning_with_successful_payment(self):
        """Processing dunning with successful payment resolves record."""
        dm = DunningManager()
        invoice = Invoice.create(customer_id="cust-1")
        record = dm.process_dunning(invoice)
        payment = Payment.create(invoice_id=invoice.id, customer_id="cust-1", amount=100.0)
        payment.mark_succeeded("txn-123")
        dm.process_dunning(invoice, payment=payment)
        assert record.status == DunningStatus.RESOLVED

    def test_handle_payment_success(self):
        """Successful payment during dunning resolves record."""
        dm = DunningManager()
        invoice = Invoice.create(customer_id="cust-1")
        record = dm.start_dunning(customer_id="cust-1", invoice_id=invoice.id)
        payment = Payment.create(invoice_id=invoice.id, customer_id="cust-1", amount=100.0)
        payment.mark_succeeded("txn-123")
        dm.handle_payment_success(invoice, payment)
        assert record.status == DunningStatus.RESOLVED

    def test_handle_payment_failure(self):
        """Failed payment advances dunning."""
        dm = DunningManager()
        invoice = Invoice.create(customer_id="cust-1")
        payment = Payment.create(invoice_id=invoice.id, customer_id="cust-1", amount=100.0)
        payment.mark_failed("Card declined")
        record = dm.handle_payment_failure(invoice, payment)
        assert record.invoice_id == invoice.id
        assert record.attempt >= 1

    def test_get_escalated_records(self):
        """Escalated records can be retrieved."""
        dm = DunningManager()
        record = dm.start_dunning(customer_id="cust-1", invoice_id="inv-1", max_attempts=1)
        dm.execute_next_action(record.id)
        escalated = dm.get_escalated_records()
        assert len(escalated) == 1

    def test_get_resolved_records(self):
        """Resolved records can be retrieved."""
        dm = DunningManager()
        record = dm.start_dunning(customer_id="cust-1", invoice_id="inv-1")
        dm.resolve(record.id)
        resolved = dm.get_resolved_records()
        assert len(resolved) == 1

    def test_set_sequence(self):
        """Custom dunning sequence can be set."""
        dm = DunningManager()
        custom_sequence = [DunningAction.EMAIL_REMINDER, DunningAction.ESCALATION]
        dm.set_sequence(custom_sequence)
        assert dm.get_sequence() == custom_sequence

    def test_set_empty_sequence_raises(self):
        """Setting empty sequence raises error."""
        dm = DunningManager()
        with pytest.raises(ValueError, match="cannot be empty"):
            dm.set_sequence([])

    def test_default_sequence(self):
        """Default dunning sequence is correct."""
        dm = DunningManager()
        seq = dm.get_sequence()
        assert DunningAction.EMAIL_REMINDER in seq
        assert DunningAction.FINAL_NOTICE in seq
        assert DunningAction.ACCOUNT_SUSPENSION in seq
