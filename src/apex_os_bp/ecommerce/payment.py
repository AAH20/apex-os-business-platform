"""Payment gateway: processes payments for orders."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Optional

from .models import (
    Order,
    Payment,
    PaymentMethod,
    PaymentStatus,
)


@dataclass
class PaymentResult:
    success: bool
    payment: Optional[Payment] = None
    transaction_id: Optional[str] = None
    error_message: str = ""


class PaymentGateway:
    """Simulated payment gateway with authorization and capture flow."""

    def __init__(self, api_key: str = "test_key", api_secret: str = "test_secret") -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self._payments: dict[str, Payment] = {}

    def _generate_transaction_id(self) -> str:
        return f"txn_{secrets.token_hex(16)}"

    def _sign(self, data: str) -> str:
        return hmac.new(
            self.api_secret.encode(),
            data.encode(),
            hashlib.sha256,
        ).hexdigest()

    def authorize(
        self,
        order: Order,
        method: PaymentMethod = PaymentMethod.CREDIT_CARD,
        currency: str = "USD",
    ) -> PaymentResult:
        if order.total <= 0:
            return PaymentResult(
                success=False,
                error_message="Order total must be positive",
            )

        txn_id = self._generate_transaction_id()
        payment = Payment(
            order_id=order.id,
            amount=order.total,
            method=method,
            status=PaymentStatus.AUTHORIZED,
            transaction_id=txn_id,
            currency=currency,
        )
        self._payments[payment.id] = payment
        return PaymentResult(
            success=True,
            payment=payment,
            transaction_id=txn_id,
        )

    def capture(self, payment_id: str) -> PaymentResult:
        payment = self._payments.get(payment_id)
        if payment is None:
            return PaymentResult(
                success=False,
                error_message=f"Payment {payment_id} not found",
            )
        if payment.status != PaymentStatus.AUTHORIZED:
            return PaymentResult(
                success=False,
                error_message=f"Cannot capture payment in {payment.status} status",
            )
        payment.update_status(PaymentStatus.CAPTURED)
        return PaymentResult(
            success=True,
            payment=payment,
            transaction_id=payment.transaction_id,
        )

    def refund(self, payment_id: str) -> PaymentResult:
        payment = self._payments.get(payment_id)
        if payment is None:
            return PaymentResult(
                success=False,
                error_message=f"Payment {payment_id} not found",
            )
        if payment.status != PaymentStatus.CAPTURED:
            return PaymentResult(
                success=False,
                error_message=f"Cannot refund payment in {payment.status} status",
            )
        payment.update_status(PaymentStatus.REFUNDED)
        return PaymentResult(
            success=True,
            payment=payment,
            transaction_id=payment.transaction_id,
        )

    def void(self, payment_id: str) -> PaymentResult:
        payment = self._payments.get(payment_id)
        if payment is None:
            return PaymentResult(
                success=False,
                error_message=f"Payment {payment_id} not found",
            )
        if payment.status != PaymentStatus.AUTHORIZED:
            return PaymentResult(
                success=False,
                error_message=f"Cannot void payment in {payment.status} status",
            )
        payment.update_status(PaymentStatus.CANCELLED)
        return PaymentResult(
            success=True,
            payment=payment,
            transaction_id=payment.transaction_id,
        )

    def process_payment(
        self,
        order: Order,
        method: PaymentMethod = PaymentMethod.CREDIT_CARD,
        currency: str = "USD",
    ) -> PaymentResult:
        """Convenience method: authorize + capture in one step."""
        auth_result = self.authorize(order, method, currency)
        if not auth_result.success:
            return auth_result
        return self.capture(auth_result.payment.id)

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        return self._payments.get(payment_id)

    def get_payment_by_order(self, order_id: str) -> Optional[Payment]:
        for payment in self._payments.values():
            if payment.order_id == order_id:
                return payment
        return None

    def list_payments(self) -> list[Payment]:
        return list(self._payments.values())

    def count(self) -> int:
        return len(self._payments)

    def clear(self) -> None:
        self._payments.clear()
