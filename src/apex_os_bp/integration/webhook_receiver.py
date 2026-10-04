"""Webhook receiver for APEX-OS Business Platform.

Handles incoming webhook deliveries with signature verification,
event parsing, deduplication, and handler dispatch. Supports
multiple webhook providers with configurable secret-based HMAC
signature validation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Common webhook event types."""

    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_CANCELLED = "order.cancelled"
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    INVOICE_PAID = "invoice.paid"
    INVOICE_OVERDUE = "invoice.overdue"
    REFUND_ISSUED = "refund.issued"
    CUSTOM = "custom"


class WebhookStatus(str, Enum):
    """Processing status for webhook deliveries."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class SignatureAlgorithm(str, Enum):
    """Supported signature algorithms."""

    HMAC_SHA256 = "hmac_sha256"
    HMAC_SHA512 = "hmac_sha512"
    HMAC_SHA1 = "hmac_sha1"


@dataclass
class WebhookPayload:
    """Parsed webhook payload."""

    event_id: str
    event_type: WebhookEventType
    data: Dict[str, Any]
    timestamp: float
    raw_body: str
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the event data."""
        return self.data.get(key, default)


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""

    delivery_id: str
    payload: WebhookPayload
    status: WebhookStatus
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = 0.0
    processed_at: Optional[float] = None
    error: Optional[str] = None
    response_status: Optional[int] = None

    def __post_init__(self) -> None:
        if self.created_at == 0.0:
            self.created_at = time.time()

    @property
    def should_retry(self) -> bool:
        """Check if delivery should be retried."""
        return self.attempts < self.max_attempts and self.status not in (
            WebhookStatus.COMPLETED,
            WebhookStatus.SKIPPED,
        )


@dataclass
class WebhookConfig:
    """Configuration for webhook receiving."""

    secret: str
    signature_header: str = "X-Webhook-Signature"
    timestamp_header: str = "X-Webhook-Timestamp"
    event_id_header: str = "X-Webhook-Event-Id"
    event_type_header: str = "X-Webhook-Event-Type"
    signature_algorithm: SignatureAlgorithm = SignatureAlgorithm.HMAC_SHA256
    max_age_seconds: float = 300.0
    dedup_enabled: bool = True
    dedup_ttl_seconds: float = 86400.0


class WebhookSignatureVerifier:
    """Verifies webhook signatures using HMAC."""

    def __init__(self, config: WebhookConfig):
        self.config = config

    def compute_signature(self, body: str, timestamp: Optional[str] = None) -> str:
        """Compute the expected signature for a body."""
        parts = [body]
        if timestamp:
            parts.insert(0, timestamp)
        signed_payload = ".".join(parts)

        algo = self.config.signature_algorithm
        if algo == SignatureAlgorithm.HMAC_SHA256:
            digest = hmac.new(
                self.config.secret.encode(),
                signed_payload.encode(),
                hashlib.sha256,
            ).hexdigest()
        elif algo == SignatureAlgorithm.HMAC_SHA512:
            digest = hmac.new(
                self.config.secret.encode(),
                signed_payload.encode(),
                hashlib.sha512,
            ).hexdigest()
        elif algo == SignatureAlgorithm.HMAC_SHA1:
            digest = hmac.new(
                self.config.secret.encode(),
                signed_payload.encode(),
                hashlib.sha1,
            ).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algo}")
        return digest

    def verify(self, body: str, signature: str, timestamp: Optional[str] = None) -> bool:
        """Verify a webhook signature."""
        expected = self.compute_signature(body, timestamp)
        return hmac.compare_digest(expected, signature)


class WebhookDeduplicator:
    """Deduplicates webhook deliveries by event ID."""

    def __init__(self, ttl_seconds: float = 86400.0):
        self.ttl_seconds = ttl_seconds
        self._seen: Dict[str, float] = {}

    def is_duplicate(self, event_id: str) -> bool:
        """Check if an event has been seen before."""
        self._cleanup()
        return event_id in self._seen

    def mark_seen(self, event_id: str) -> None:
        """Mark an event as seen."""
        self._seen[event_id] = time.time()

    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [eid for eid, ts in self._seen.items() if now - ts > self.ttl_seconds]
        for eid in expired:
            del self._seen[eid]

    def clear(self) -> None:
        """Clear all dedup state."""
        self._seen.clear()

    @property
    def size(self) -> int:
        """Get number of tracked event IDs."""
        return len(self._seen)


class WebhookReceiver:
    """Main webhook receiver: verifies, parses, deduplicates, and dispatches."""

    def __init__(self, config: WebhookConfig):
        self.config = config
        self._verifier = WebhookSignatureVerifier(config)
        self._deduplicator = WebhookDeduplicator(config.dedup_ttl_seconds) if config.dedup_enabled else None
        self._handlers: Dict[WebhookEventType, List[Callable]] = {}
        self._global_handlers: List[Callable] = []
        self._deliveries: Dict[str, WebhookDelivery] = {}
        self._delivery_history: List[WebhookDelivery] = []

    def register_handler(self, event_type: WebhookEventType, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def register_global_handler(self, handler: Callable) -> None:
        """Register a handler for all events."""
        self._global_handlers.append(handler)

    def parse_payload(
        self,
        body: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> WebhookPayload:
        """Parse a raw webhook body into a WebhookPayload."""
        headers = headers or {}
        data = json.loads(body) if body else {}

        event_id = headers.get(self.config.event_id_header, str(uuid.uuid4()))
        event_type_str = headers.get(self.config.event_type_header, WebhookEventType.CUSTOM.value)
        try:
            event_type = WebhookEventType(event_type_str)
        except ValueError:
            event_type = WebhookEventType.CUSTOM

        timestamp_str = headers.get(self.config.timestamp_header)
        timestamp = float(timestamp_str) if timestamp_str else time.time()

        return WebhookPayload(
            event_id=event_id,
            event_type=event_type,
            data=data,
            timestamp=timestamp,
            raw_body=body,
            headers=headers,
        )

    def verify_signature(
        self,
        body: str,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """Verify the signature of an incoming webhook."""
        return self._verifier.verify(body, signature, timestamp)

    def receive(
        self,
        body: str,
        headers: Optional[Dict[str, str]] = None,
        skip_signature_check: bool = False,
    ) -> WebhookDelivery:
        """Process an incoming webhook delivery.

        This is the main entry point: verifies signature, parses payload,
        checks dedup, dispatches to handlers, and records the delivery.
        """
        headers = headers or {}
        delivery_id = str(uuid.uuid4())

        # Parse
        try:
            payload = self.parse_payload(body, headers)
        except (json.JSONDecodeError, ValueError) as e:
            delivery = WebhookDelivery(
                delivery_id=delivery_id,
                payload=WebhookPayload(
                    event_id=delivery_id,
                    event_type=WebhookEventType.CUSTOM,
                    data={},
                    timestamp=time.time(),
                    raw_body=body,
                    headers=headers,
                ),
                status=WebhookStatus.FAILED,
                error=f"Parse error: {e}",
            )
            self._record_delivery(delivery)
            return delivery

        # Signature verification
        if not skip_signature_check:
            sig = headers.get(self.config.signature_header, "")
            ts = headers.get(self.config.timestamp_header)
            if not sig or not self.verify_signature(body, sig, ts):
                delivery = WebhookDelivery(
                    delivery_id=delivery_id,
                    payload=payload,
                    status=WebhookStatus.FAILED,
                    error="Invalid signature",
                )
                self._record_delivery(delivery)
                return delivery

        # Timestamp freshness check
        if self.config.max_age_seconds > 0:
            age = time.time() - payload.timestamp
            if age > self.config.max_age_seconds:
                delivery = WebhookDelivery(
                    delivery_id=delivery_id,
                    payload=payload,
                    status=WebhookStatus.SKIPPED,
                    error=f"Webhook too old: {age:.0f}s",
                )
                self._record_delivery(delivery)
                return delivery

        # Deduplication
        if self._deduplicator and self._deduplicator.is_duplicate(payload.event_id):
            delivery = WebhookDelivery(
                delivery_id=delivery_id,
                payload=payload,
                status=WebhookStatus.SKIPPED,
                error="Duplicate event",
            )
            self._record_delivery(delivery)
            return delivery

        if self._deduplicator:
            self._deduplicator.mark_seen(payload.event_id)

        # Dispatch
        delivery = WebhookDelivery(
            delivery_id=delivery_id,
            payload=payload,
            status=WebhookStatus.PROCESSING,
        )

        try:
            self._dispatch(payload)
            delivery.status = WebhookStatus.COMPLETED
            delivery.processed_at = time.time()
        except Exception as e:
            logger.exception("Webhook handler failed for event %s", payload.event_id)
            delivery.status = WebhookStatus.FAILED
            delivery.error = str(e)

        self._record_delivery(delivery)
        return delivery

    def _dispatch(self, payload: WebhookPayload) -> None:
        """Dispatch payload to registered handlers."""
        # Global handlers
        for handler in self._global_handlers:
            handler(payload)

        # Event-specific handlers
        handlers = self._handlers.get(payload.event_type, [])
        for handler in handlers:
            handler(payload)

    def _record_delivery(self, delivery: WebhookDelivery) -> None:
        """Record a delivery attempt."""
        self._deliveries[delivery.delivery_id] = delivery
        self._delivery_history.append(delivery)

    def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get a delivery by ID."""
        return self._deliveries.get(delivery_id)

    def get_delivery_history(
        self,
        status: Optional[WebhookStatus] = None,
    ) -> List[WebhookDelivery]:
        """Get delivery history, optionally filtered by status."""
        if status is None:
            return list(self._delivery_history)
        return [d for d in self._delivery_history if d.status == status]

    def get_stats(self) -> Dict[str, int]:
        """Get delivery statistics."""
        stats: Dict[str, int] = {}
        for d in self._delivery_history:
            key = d.status.value
            stats[key] = stats.get(key, 0) + 1
        stats["total"] = len(self._delivery_history)
        return stats
