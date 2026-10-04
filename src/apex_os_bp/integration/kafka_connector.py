"""Kafka connector for APEX-OS Business Platform.

Provides a high-level interface for producing and consuming messages
from Kafka topics with support for batching, partitioning, and
consumer groups.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class KafkaDeliveryGuarantee(str, Enum):
    """Delivery guarantee levels for Kafka producers."""

    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


class KafkaOffsetReset(str, Enum):
    """Offset reset policy for consumer groups."""

    EARLIEST = "earliest"
    LATEST = "latest"
    NONE = "none"


@dataclass
class KafkaMessage:
    """Represents a Kafka message."""

    topic: str
    value: Union[str, bytes, Dict[str, Any]]
    key: Optional[str] = None
    partition: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    offset: Optional[int] = None
    timestamp: Optional[float] = None

    def encoded_value(self) -> bytes:
        """Encode message value to bytes."""
        if isinstance(self.value, bytes):
            return self.value
        if isinstance(self.value, str):
            return self.value.encode("utf-8")
        return json.dumps(self.value).encode("utf-8")


@dataclass
class KafkaConsumerConfig:
    """Configuration for a Kafka consumer."""

    group_id: str
    topics: List[str]
    auto_offset_reset: KafkaOffsetReset = KafkaOffsetReset.LATEST
    enable_auto_commit: bool = True
    max_poll_records: int = 500
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000


@dataclass
class KafkaProducerConfig:
    """Configuration for a Kafka producer."""

    delivery_guarantee: KafkaDeliveryGuarantee = KafkaDeliveryGuarantee.AT_LEAST_ONCE
    acks: str = "all"
    retries: int = 3
    batch_size: int = 16384
    linger_ms: int = 5
    compression_type: Optional[str] = "snappy"
    max_in_flight_requests: int = 5


class KafkaProducer:
    """Kafka message producer.

    In production this wraps confluent-kafka or kafka-python. Here we
    provide a clean interface with an in-memory transport for testing
    and development.
    """

    def __init__(self, config: Optional[KafkaProducerConfig] = None):
        self.config = config or KafkaProducerConfig()
        self._connected = False
        self._pending: List[KafkaMessage] = []
        self._produced: List[KafkaMessage] = []
        self._delivery_callbacks: List[Callable] = []

    def connect(self) -> None:
        """Establish connection to Kafka cluster."""
        self._connected = True
        logger.info("Kafka producer connected")

    def disconnect(self) -> None:
        """Disconnect from Kafka cluster."""
        self._flush()
        self._connected = False
        logger.info("Kafka producer disconnected")

    def send(self, message: KafkaMessage) -> "KafkaProducer":
        """Send a message to Kafka.

        Returns self for method chaining.
        """
        if not self._connected:
            raise RuntimeError("Producer not connected")
        self._pending.append(message)
        return self

    def send_batch(self, messages: List[KafkaMessage]) -> "KafkaProducer":
        """Send multiple messages."""
        for msg in messages:
            self.send(msg)
        return self

    def _flush(self) -> None:
        """Flush pending messages to Kafka."""
        for msg in self._pending:
            self._produced.append(msg)
            for cb in self._delivery_callbacks:
                try:
                    cb(msg)
                except Exception:
                    logger.exception("Delivery callback failed")
        self._pending.clear()

    def flush(self) -> None:
        """Public flush method."""
        self._flush()

    @property
    def produced_messages(self) -> List[KafkaMessage]:
        """Get all produced messages (for testing/verification)."""
        return list(self._produced)

    @property
    def pending_count(self) -> int:
        """Get count of pending (unsent) messages."""
        return len(self._pending)

    def register_delivery_callback(self, callback: Callable) -> None:
        """Register a callback invoked after each message is flushed."""
        self._delivery_callbacks.append(callback)

    def __enter__(self) -> "KafkaProducer":
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()


class KafkaConsumer:
    """Kafka message consumer with consumer group support."""

    def __init__(self, config: KafkaConsumerConfig):
        self.config = config
        self._connected = False
        self._subscribed = False
        self._messages: List[KafkaMessage] = []
        self._position: Dict[str, int] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running = False

    def connect(self) -> None:
        """Establish connection to Kafka cluster."""
        self._connected = True
        logger.info("Kafka consumer connected (group=%s)", self.config.group_id)

    def subscribe(self) -> None:
        """Subscribe to configured topics."""
        if not self._connected:
            raise RuntimeError("Consumer not connected")
        self._subscribed = True
        logger.info("Subscribed to topics: %s", self.config.topics)

    def register_handler(self, topic: str, handler: Callable) -> None:
        """Register a message handler for a topic."""
        self._handlers[topic] = handler

    def poll(self, timeout_ms: int = 1000) -> List[KafkaMessage]:
        """Poll for new messages.

        In production this fetches from Kafka. Here we return from
        the internal buffer (useful for testing).
        """
        if not self._subscribed:
            raise RuntimeError("Consumer not subscribed")
        messages = self._messages[: self.config.max_poll_records]
        self._messages = self._messages[self.config.max_poll_records :]
        return messages

    def commit(self, message: KafkaMessage) -> None:
        """Commit offset for a message."""
        if message.topic and message.offset is not None:
            self._position[message.topic] = message.offset

    def commit_all(self) -> None:
        """Commit all pending offsets."""
        logger.info("Committed offsets: %s", self._position)

    def seek(self, topic: str, offset: int) -> None:
        """Seek to a specific offset for a topic."""
        self._position[topic] = offset

    def close(self) -> None:
        """Close the consumer."""
        self._running = False
        self._subscribed = False
        self._connected = False
        logger.info("Kafka consumer closed")

    def inject_message(self, message: KafkaMessage) -> None:
        """Inject a message into the consumer buffer (for testing)."""
        self._messages.append(message)

    @property
    def position(self) -> Dict[str, int]:
        """Get current consumer positions."""
        return dict(self._position)

    @property
    def is_connected(self) -> bool:
        """Check if consumer is connected."""
        return self._connected

    def __enter__(self) -> "KafkaConsumer":
        self.connect()
        self.subscribe()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class KafkaTopicManager:
    """Manage Kafka topics: creation, deletion, and metadata."""

    def __init__(self):
        self._topics: Dict[str, Dict[str, Any]] = {}

    def create_topic(
        self,
        name: str,
        num_partitions: int = 3,
        replication_factor: int = 1,
        config: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a new topic."""
        if name in self._topics:
            raise ValueError(f"Topic already exists: {name}")
        topic_info = {
            "name": name,
            "num_partitions": num_partitions,
            "replication_factor": replication_factor,
            "config": config or {},
            "created_at": time.time(),
        }
        self._topics[name] = topic_info
        return topic_info

    def delete_topic(self, name: str) -> bool:
        """Delete a topic. Returns True if deleted, False if not found."""
        if name in self._topics:
            del self._topics[name]
            return True
        return False

    def list_topics(self) -> List[str]:
        """List all topic names."""
        return list(self._topics.keys())

    def describe_topic(self, name: str) -> Optional[Dict[str, Any]]:
        """Get topic metadata."""
        return self._topics.get(name)

    def topic_exists(self, name: str) -> bool:
        """Check if a topic exists."""
        return name in self._topics
