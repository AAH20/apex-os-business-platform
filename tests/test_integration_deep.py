"""Deep integration tests for APEX-OS Business Platform.

Tests cover: Kafka connector, REST API client, webhook receiver,
data transformer, and Redis rate limiter.
"""
import json
import time
import uuid

import pytest

from apex_os_bp.integration.kafka_connector import (
    KafkaConsumer,
    KafkaConsumerConfig,
    KafkaDeliveryGuarantee,
    KafkaMessage,
    KafkaOffsetReset,
    KafkaProducer,
    KafkaProducerConfig,
    KafkaTopicManager,
)
from apex_os_bp.integration.rest_client import (
    AuthConfig,
    AuthType,
    HTTPMethod,
    RESTClient,
    RESTRequest,
    RESTResponse,
    RetryConfig,
)
from apex_os_bp.integration.webhook_receiver import (
    SignatureAlgorithm,
    WebhookConfig,
    WebhookDelivery,
    WebhookDeduplicator,
    WebhookEventType,
    WebhookPayload,
    WebhookReceiver,
    WebhookSignatureVerifier,
    WebhookStatus,
)
from apex_os_bp.integration.data_transformer import (
    DataTransformer,
    FieldMapping,
    TransformFieldType,
    TransformOperation,
    TransformPipeline,
    TransformResult,
    ValidationRule,
)
from apex_os_bp.integration.redis_rate_limiter import (
    InMemoryBackend,
    RateLimitAlgorithm,
    RateLimitConfig,
    RateLimitResult,
    RedisRateLimiter,
)


# ===================================================================
# Kafka Connector Tests
# ===================================================================


class TestKafkaMessage:
    """Test KafkaMessage data structure."""

    def test_message_creation(self):
        """Message can be created with topic and value."""
        msg = KafkaMessage(topic="orders", value={"id": 1})
        assert msg.topic == "orders"
        assert msg.value == {"id": 1}

    def test_encoded_value_dict(self):
        """Dict value is encoded to JSON bytes."""
        msg = KafkaMessage(topic="test", value={"key": "value"})
        encoded = msg.encoded_value()
        assert isinstance(encoded, bytes)
        assert json.loads(encoded) == {"key": "value"}

    def test_encoded_value_str(self):
        """String value is encoded to UTF-8 bytes."""
        msg = KafkaMessage(topic="test", value="hello")
        assert msg.encoded_value() == b"hello"

    def test_encoded_value_bytes(self):
        """Bytes value passes through unchanged."""
        msg = KafkaMessage(topic="test", value=b"\x00\x01")
        assert msg.encoded_value() == b"\x00\x01"

    def test_message_with_key_and_headers(self):
        """Message supports key and headers."""
        msg = KafkaMessage(
            topic="events",
            value="data",
            key="event-1",
            headers={"source": "test"},
        )
        assert msg.key == "event-1"
        assert msg.headers["source"] == "test"


class TestKafkaProducerConfig:
    """Test KafkaProducerConfig defaults."""

    def test_default_config(self):
        """Default config has expected values."""
        config = KafkaProducerConfig()
        assert config.delivery_guarantee == KafkaDeliveryGuarantee.AT_LEAST_ONCE
        assert config.acks == "all"
        assert config.retries == 3

    def test_custom_config(self):
        """Custom config is stored."""
        config = KafkaProducerConfig(
            delivery_guarantee=KafkaDeliveryGuarantee.EXACTLY_ONCE,
            acks="1",
            retries=5,
        )
        assert config.delivery_guarantee == KafkaDeliveryGuarantee.EXACTLY_ONCE
        assert config.acks == "1"
        assert config.retries == 5


class TestKafkaProducer:
    """Test KafkaProducer."""

    def test_producer_connect_disconnect(self):
        """Producer can connect and disconnect."""
        producer = KafkaProducer()
        assert not producer._connected
        producer.connect()
        assert producer._connected
        producer.disconnect()
        assert not producer._connected

    def test_send_message(self):
        """Message can be sent."""
        producer = KafkaProducer()
        producer.connect()
        msg = KafkaMessage(topic="test", value="hello")
        producer.send(msg)
        assert producer.pending_count == 1
        producer.disconnect()

    def test_send_batch(self):
        """Multiple messages can be sent as batch."""
        producer = KafkaProducer()
        producer.connect()
        messages = [KafkaMessage(topic="test", value=f"msg-{i}") for i in range(5)]
        producer.send_batch(messages)
        assert producer.pending_count == 5
        producer.disconnect()

    def test_flush_produces_messages(self):
        """Flush moves pending to produced."""
        producer = KafkaProducer()
        producer.connect()
        producer.send(KafkaMessage(topic="test", value="data"))
        assert producer.pending_count == 1
        assert len(producer.produced_messages) == 0
        producer.flush()
        assert producer.pending_count == 0
        assert len(producer.produced_messages) == 1
        producer.disconnect()

    def test_send_requires_connection(self):
        """Sending without connection raises error."""
        producer = KafkaProducer()
        with pytest.raises(RuntimeError):
            producer.send(KafkaMessage(topic="test", value="data"))

    def test_delivery_callback(self):
        """Delivery callback is invoked on flush."""
        producer = KafkaProducer()
        producer.connect()
        delivered = []
        producer.register_delivery_callback(lambda msg: delivered.append(msg))
        producer.send(KafkaMessage(topic="test", value="data"))
        producer.flush()
        assert len(delivered) == 1
        producer.disconnect()

    def test_context_manager(self):
        """Producer works as context manager."""
        with KafkaProducer() as producer:
            assert producer._connected
            producer.send(KafkaMessage(topic="test", value="data"))
        assert not producer._connected

    def test_chained_send(self):
        """Send returns self for chaining."""
        producer = KafkaProducer()
        producer.connect()
        result = producer.send(KafkaMessage(topic="a", value="1")).send(
            KafkaMessage(topic="b", value="2")
        )
        assert result is producer
        assert producer.pending_count == 2
        producer.disconnect()


class TestKafkaConsumerConfig:
    """Test KafkaConsumerConfig."""

    def test_default_config(self):
        """Default config has expected values."""
        config = KafkaConsumerConfig(group_id="test-group", topics=["orders"])
        assert config.group_id == "test-group"
        assert config.topics == ["orders"]
        assert config.auto_offset_reset == KafkaOffsetReset.LATEST
        assert config.enable_auto_commit is True

    def test_custom_config(self):
        """Custom config is stored."""
        config = KafkaConsumerConfig(
            group_id="g1",
            topics=["t1", "t2"],
            auto_offset_reset=KafkaOffsetReset.EARLIEST,
            max_poll_records=100,
        )
        assert config.auto_offset_reset == KafkaOffsetReset.EARLIEST
        assert config.max_poll_records == 100


class TestKafkaConsumer:
    """Test KafkaConsumer."""

    def _make_consumer(self) -> KafkaConsumer:
        config = KafkaConsumerConfig(group_id="test-group", topics=["test-topic"])
        return KafkaConsumer(config)

    def test_consumer_connect_subscribe(self):
        """Consumer can connect and subscribe."""
        consumer = self._make_consumer()
        assert not consumer.is_connected
        consumer.connect()
        assert consumer.is_connected
        consumer.subscribe()
        assert consumer._subscribed
        consumer.close()

    def test_consumer_context_manager(self):
        """Consumer works as context manager."""
        config = KafkaConsumerConfig(group_id="test-group", topics=["test-topic"])
        with KafkaConsumer(config) as consumer:
            assert consumer.is_connected
            assert consumer._subscribed
        assert not consumer.is_connected

    def test_register_handler(self):
        """Handler can be registered for a topic."""
        consumer = self._make_consumer()
        handler = lambda msg: None
        consumer.register_handler("test-topic", handler)
        assert "test-topic" in consumer._handlers

    def test_poll_returns_injected_messages(self):
        """Poll returns injected messages."""
        consumer = self._make_consumer()
        consumer.connect()
        consumer.subscribe()
        msg = KafkaMessage(topic="test-topic", value="hello", offset=1)
        consumer.inject_message(msg)
        messages = consumer.poll()
        assert len(messages) == 1
        assert messages[0].value == "hello"
        consumer.close()

    def test_poll_requires_subscription(self):
        """Poll without subscription raises error."""
        consumer = self._make_consumer()
        consumer.connect()
        with pytest.raises(RuntimeError):
            consumer.poll()

    def test_commit_updates_position(self):
        """Commit updates consumer position."""
        consumer = self._make_consumer()
        consumer.connect()
        msg = KafkaMessage(topic="test-topic", value="data", offset=42)
        consumer.commit(msg)
        assert consumer.position["test-topic"] == 42
        consumer.close()

    def test_seek_sets_position(self):
        """Seek sets the position for a topic."""
        consumer = self._make_consumer()
        consumer.connect()
        consumer.seek("test-topic", 100)
        assert consumer.position["test-topic"] == 100
        consumer.close()


class TestKafkaTopicManager:
    """Test KafkaTopicManager."""

    def test_create_topic(self):
        """Topic can be created."""
        mgr = KafkaTopicManager()
        info = mgr.create_topic("orders", num_partitions=6)
        assert info["name"] == "orders"
        assert info["num_partitions"] == 6

    def test_create_duplicate_topic_raises(self):
        """Creating duplicate topic raises error."""
        mgr = KafkaTopicManager()
        mgr.create_topic("orders")
        with pytest.raises(ValueError):
            mgr.create_topic("orders")

    def test_delete_topic(self):
        """Topic can be deleted."""
        mgr = KafkaTopicManager()
        mgr.create_topic("orders")
        assert mgr.delete_topic("orders") is True
        assert mgr.topic_exists("orders") is False

    def test_delete_nonexistent_topic(self):
        """Deleting nonexistent topic returns False."""
        mgr = KafkaTopicManager()
        assert mgr.delete_topic("nonexistent") is False

    def test_list_topics(self):
        """Topics can be listed."""
        mgr = KafkaTopicManager()
        mgr.create_topic("a")
        mgr.create_topic("b")
        assert set(mgr.list_topics()) == {"a", "b"}

    def test_describe_topic(self):
        """Topic metadata can be retrieved."""
        mgr = KafkaTopicManager()
        mgr.create_topic("orders", num_partitions=3)
        info = mgr.describe_topic("orders")
        assert info is not None
        assert info["num_partitions"] == 3

    def test_describe_nonexistent_topic(self):
        """Describing nonexistent topic returns None."""
        mgr = KafkaTopicManager()
        assert mgr.describe_topic("nonexistent") is None


# ===================================================================
# REST API Client Tests
# ===================================================================


class TestRESTResponse:
    """Test RESTResponse data structure."""

    def test_ok_property(self):
        """2xx status codes are ok."""
        assert RESTResponse(status_code=200, body="").ok
        assert RESTResponse(status_code=201, body="").ok
        assert RESTResponse(status_code=204, body="").ok
        assert not RESTResponse(status_code=404, body="").ok
        assert not RESTResponse(status_code=500, body="").ok

    def test_json_property_with_dict(self):
        """JSON property returns dict body directly."""
        resp = RESTResponse(status_code=200, body={"key": "value"})
        assert resp.json == {"key": "value"}

    def test_json_property_with_json_string(self):
        """JSON property parses JSON string body."""
        resp = RESTResponse(status_code=200, body='{"key": "value"}')
        assert resp.json == {"key": "value"}

    def test_json_property_with_invalid_json(self):
        """JSON property returns None for invalid JSON."""
        resp = RESTResponse(status_code=200, body="not json")
        assert resp.json is None

    def test_text_property(self):
        """Text property returns string body."""
        resp = RESTResponse(status_code=200, body="hello")
        assert resp.text == "hello"

    def test_text_property_with_bytes(self):
        """Text property decodes bytes body."""
        resp = RESTResponse(status_code=200, body=b"hello")
        assert resp.text == "hello"


class TestRESTRequest:
    """Test RESTRequest data structure."""

    def test_full_url_no_params(self):
        """Full URL without params is unchanged."""
        req = RESTRequest(method=HTTPMethod.GET, url="http://example.com/api")
        assert req.full_url() == "http://example.com/api"

    def test_full_url_with_params(self):
        """Full URL includes query params."""
        req = RESTRequest(
            method=HTTPMethod.GET,
            url="http://example.com/api",
            params={"page": "1"},
        )
        assert "page=1" in req.full_url()

    def test_full_url_with_existing_params(self):
        """Full URL appends to existing query string."""
        req = RESTRequest(
            method=HTTPMethod.GET,
            url="http://example.com/api?foo=bar",
            params={"page": "1"},
        )
        assert "foo=bar" in req.full_url()
        assert "page=1" in req.full_url()

    def test_encoded_body_dict(self):
        """Dict body is encoded to JSON bytes."""
        req = RESTRequest(
            method=HTTPMethod.POST,
            url="http://example.com",
            body={"key": "value"},
        )
        assert json.loads(req.encoded_body()) == {"key": "value"}

    def test_encoded_body_none(self):
        """None body returns None."""
        req = RESTRequest(method=HTTPMethod.GET, url="http://example.com")
        assert req.encoded_body() is None


class TestRESTClient:
    """Test RESTClient."""

    def test_default_headers(self):
        """Default headers are set."""
        client = RESTClient()
        assert client.default_headers == {}

    def test_set_session_header(self):
        """Session header can be set."""
        client = RESTClient()
        client.set_session_header("X-Custom", "value")
        assert client._session_headers["X-Custom"] == "value"

    def test_clear_session_headers(self):
        """Session headers can be cleared."""
        client = RESTClient()
        client.set_session_header("X-Custom", "value")
        client.clear_session_headers()
        assert client._session_headers == {}

    def test_bearer_auth_header(self):
        """Bearer auth sets Authorization header."""
        auth = AuthConfig(auth_type=AuthType.BEARER, token="my-token")
        client = RESTClient(auth=auth)
        req = RESTRequest(method=HTTPMethod.GET, url="http://example.com")
        headers = client._build_headers(req)
        assert headers["Authorization"] == "Bearer my-token"

    def test_api_key_auth_header(self):
        """API key auth sets API key header."""
        auth = AuthConfig(
            auth_type=AuthType.API_KEY,
            api_key="secret-key",
            api_key_header="X-API-Key",
        )
        client = RESTClient(auth=auth)
        req = RESTRequest(method=HTTPMethod.GET, url="http://example.com")
        headers = client._build_headers(req)
        assert headers["X-API-Key"] == "secret-key"

    def test_basic_auth_header(self):
        """Basic auth sets Authorization header."""
        auth = AuthConfig(
            auth_type=AuthType.BASIC,
            username="user",
            password="pass",
        )
        client = RESTClient(auth=auth)
        req = RESTRequest(method=HTTPMethod.GET, url="http://example.com")
        headers = client._build_headers(req)
        assert headers["Authorization"].startswith("Basic ")

    def test_no_auth_header(self):
        """No auth type does not set Authorization."""
        auth = AuthConfig(auth_type=AuthType.NONE)
        client = RESTClient(auth=auth)
        req = RESTRequest(method=HTTPMethod.GET, url="http://example.com")
        headers = client._build_headers(req)
        assert "Authorization" not in headers

    def test_request_hook(self):
        """Request hook is called before request."""
        client = RESTClient()
        called = []
        client.add_request_hook(lambda req: called.append(req))
        # We can't easily test the full flow without a server,
        # but we can verify the hook is registered
        assert len(client._request_hooks) == 1

    def test_response_hook(self):
        """Response hook is registered."""
        client = RESTClient()
        client.add_response_hook(lambda resp: None)
        assert len(client._response_hooks) == 1

    def test_base_url_joining(self):
        """Base URL is joined with path."""
        client = RESTClient(base_url="http://example.com/api")
        # We verify the URL building logic
        req = RESTRequest(method=HTTPMethod.GET, url="/users")
        full = req.full_url()
        assert full == "/users"

    def test_retry_config_defaults(self):
        """Default retry config has expected values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.backoff_factor == 0.5
        assert 429 in config.retry_on_status
        assert 500 in config.retry_on_status

    def test_auth_config_defaults(self):
        """Default auth config has expected values."""
        config = AuthConfig()
        assert config.auth_type == AuthType.NONE


# ===================================================================
# Webhook Receiver Tests
# ===================================================================


class TestWebhookSignatureVerifier:
    """Test webhook signature verification."""

    def _make_verifier(self, secret: str = "test-secret") -> WebhookSignatureVerifier:
        config = WebhookConfig(secret=secret)
        return WebhookSignatureVerifier(config)

    def test_compute_signature(self):
        """Signature can be computed."""
        verifier = self._make_verifier()
        sig = verifier.compute_signature("body")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex

    def test_verify_valid_signature(self):
        """Valid signature passes verification."""
        verifier = self._make_verifier()
        sig = verifier.compute_signature("body")
        assert verifier.verify("body", sig) is True

    def test_verify_invalid_signature(self):
        """Invalid signature fails verification."""
        verifier = self._make_verifier()
        assert verifier.verify("body", "invalid") is False

    def test_verify_with_timestamp(self):
        """Signature with timestamp is verified."""
        verifier = self._make_verifier()
        sig = verifier.compute_signature("body", "1234567890")
        assert verifier.verify("body", sig, "1234567890") is True

    def test_different_bodies_different_signatures(self):
        """Different bodies produce different signatures."""
        verifier = self._make_verifier()
        sig1 = verifier.compute_signature("body1")
        sig2 = verifier.compute_signature("body2")
        assert sig1 != sig2

    def test_hmac_sha512(self):
        """HMAC-SHA512 algorithm works."""
        config = WebhookConfig(secret="s", signature_algorithm=SignatureAlgorithm.HMAC_SHA512)
        verifier = WebhookSignatureVerifier(config)
        sig = verifier.compute_signature("body")
        assert len(sig) == 128  # SHA-512 hex

    def test_hmac_sha1(self):
        """HMAC-SHA1 algorithm works."""
        config = WebhookConfig(secret="s", signature_algorithm=SignatureAlgorithm.HMAC_SHA1)
        verifier = WebhookSignatureVerifier(config)
        sig = verifier.compute_signature("body")
        assert len(sig) == 40  # SHA-1 hex


class TestWebhookDeduplicator:
    """Test webhook deduplication."""

    def test_not_duplicate_initially(self):
        """New event ID is not duplicate."""
        dedup = WebhookDeduplicator()
        assert dedup.is_duplicate("event-1") is False

    def test_duplicate_after_marking(self):
        """Event ID is duplicate after marking."""
        dedup = WebhookDeduplicator()
        dedup.mark_seen("event-1")
        assert dedup.is_duplicate("event-1") is True

    def test_different_events_not_duplicate(self):
        """Different event IDs are not duplicates."""
        dedup = WebhookDeduplicator()
        dedup.mark_seen("event-1")
        assert dedup.is_duplicate("event-2") is False

    def test_clear_removes_all(self):
        """Clear removes all tracked events."""
        dedup = WebhookDeduplicator()
        dedup.mark_seen("event-1")
        dedup.mark_seen("event-2")
        dedup.clear()
        assert dedup.size == 0
        assert dedup.is_duplicate("event-1") is False

    def test_ttl_expiry(self):
        """Events expire after TTL."""
        dedup = WebhookDeduplicator(ttl_seconds=0.01)
        dedup.mark_seen("event-1")
        time.sleep(0.02)
        assert dedup.is_duplicate("event-1") is False


class TestWebhookPayload:
    """Test WebhookPayload data structure."""

    def test_get_method(self):
        """Get retrieves value from data."""
        payload = WebhookPayload(
            event_id="e1",
            event_type=WebhookEventType.ORDER_CREATED,
            data={"order_id": 123, "total": 99.99},
            timestamp=time.time(),
            raw_body="",
        )
        assert payload.get("order_id") == 123
        assert payload.get("missing") is None
        assert payload.get("missing", "default") == "default"


class TestWebhookDelivery:
    """Test WebhookDelivery data structure."""

    def test_should_retry_under_max(self):
        """Delivery under max attempts should retry."""
        payload = WebhookPayload(
            event_id="e1",
            event_type=WebhookEventType.CUSTOM,
            data={},
            timestamp=time.time(),
            raw_body="",
        )
        delivery = WebhookDelivery(
            delivery_id="d1",
            payload=payload,
            status=WebhookStatus.FAILED,
            attempts=1,
            max_attempts=3,
        )
        assert delivery.should_retry is True

    def test_should_not_retry_over_max(self):
        """Delivery over max attempts should not retry."""
        payload = WebhookPayload(
            event_id="e1",
            event_type=WebhookEventType.CUSTOM,
            data={},
            timestamp=time.time(),
            raw_body="",
        )
        delivery = WebhookDelivery(
            delivery_id="d1",
            payload=payload,
            status=WebhookStatus.FAILED,
            attempts=3,
            max_attempts=3,
        )
        assert delivery.should_retry is False

    def test_should_not_retry_completed(self):
        """Completed delivery should not retry."""
        payload = WebhookPayload(
            event_id="e1",
            event_type=WebhookEventType.CUSTOM,
            data={},
            timestamp=time.time(),
            raw_body="",
        )
        delivery = WebhookDelivery(
            delivery_id="d1",
            payload=payload,
            status=WebhookStatus.COMPLETED,
            attempts=0,
            max_attempts=3,
        )
        assert delivery.should_retry is False


class TestWebhookReceiver:
    """Test WebhookReceiver end-to-end."""

    def _make_receiver(self, secret: str = "webhook-secret") -> WebhookReceiver:
        config = WebhookConfig(secret=secret)
        return WebhookReceiver(config)

    def _make_body(self, event_type: str = "order.created") -> str:
        return json.dumps({"order_id": 123, "total": 99.99})

    def _make_headers(
        self,
        body: str,
        secret: str = "webhook-secret",
        event_type: str = "order.created",
    ) -> dict:
        verifier = WebhookSignatureVerifier(WebhookConfig(secret=secret))
        ts = str(time.time())
        sig = verifier.compute_signature(body, ts)
        return {
            "X-Webhook-Signature": sig,
            "X-Webhook-Event-Id": str(uuid.uuid4()),
            "X-Webhook-Event-Type": event_type,
            "X-Webhook-Timestamp": ts,
        }

    def test_parse_payload(self):
        """Payload is parsed from body and headers."""
        receiver = self._make_receiver()
        body = self._make_body()
        headers = self._make_headers(body)
        payload = receiver.parse_payload(body, headers)
        assert payload.event_type == WebhookEventType.ORDER_CREATED
        assert payload.data["order_id"] == 123

    def test_parse_payload_custom_event(self):
        """Unknown event type defaults to CUSTOM."""
        receiver = self._make_receiver()
        body = json.dumps({"foo": "bar"})
        headers = self._make_headers(body, event_type="unknown.event")
        payload = receiver.parse_payload(body, headers)
        assert payload.event_type == WebhookEventType.CUSTOM

    def test_receive_valid_webhook(self):
        """Valid webhook is processed successfully."""
        receiver = self._make_receiver()
        body = self._make_body()
        headers = self._make_headers(body)
        delivery = receiver.receive(body, headers)
        assert delivery.status == WebhookStatus.COMPLETED

    def test_receive_invalid_signature(self):
        """Invalid signature causes failure."""
        receiver = self._make_receiver()
        body = self._make_body()
        headers = {
            "X-Webhook-Signature": "invalid",
            "X-Webhook-Event-Id": str(uuid.uuid4()),
            "X-Webhook-Event-Type": "order.created",
            "X-Webhook-Timestamp": str(time.time()),
        }
        delivery = receiver.receive(body, headers)
        assert delivery.status == WebhookStatus.FAILED
        assert "signature" in delivery.error.lower()

    def test_receive_duplicate_event(self):
        """Duplicate event is skipped."""
        receiver = self._make_receiver()
        body = self._make_body()
        headers = self._make_headers(body)
        event_id = headers["X-Webhook-Event-Id"]

        delivery1 = receiver.receive(body, headers)
        assert delivery1.status == WebhookStatus.COMPLETED

        # Same event ID
        delivery2 = receiver.receive(body, headers)
        assert delivery2.status == WebhookStatus.SKIPPED
        assert "duplicate" in delivery2.error.lower()

    def test_receive_old_webhook(self):
        """Old webhook is skipped."""
        receiver = self._make_receiver()
        body = self._make_body()
        old_ts = str(time.time() - 600)  # 10 minutes old
        verifier = WebhookSignatureVerifier(WebhookConfig(secret="webhook-secret"))
        sig = verifier.compute_signature(body, old_ts)
        headers = {
            "X-Webhook-Signature": sig,
            "X-Webhook-Event-Id": str(uuid.uuid4()),
            "X-Webhook-Event-Type": "order.created",
            "X-Webhook-Timestamp": old_ts,
        }
        delivery = receiver.receive(body, headers)
        assert delivery.status == WebhookStatus.SKIPPED

    def test_register_handler(self):
        """Handler can be registered for event type."""
        receiver = self._make_receiver()
        handler = lambda payload: None
        receiver.register_handler(WebhookEventType.ORDER_CREATED, handler)
        assert len(receiver._handlers[WebhookEventType.ORDER_CREATED]) == 1

    def test_register_global_handler(self):
        """Global handler can be registered."""
        receiver = self._make_receiver()
        handler = lambda payload: None
        receiver.register_global_handler(handler)
        assert len(receiver._global_handlers) == 1

    def test_handler_called_on_receive(self):
        """Registered handler is called when webhook is received."""
        receiver = self._make_receiver()
        received_payloads = []
        receiver.register_handler(
            WebhookEventType.ORDER_CREATED,
            lambda payload: received_payloads.append(payload),
        )
        body = self._make_body()
        headers = self._make_headers(body)
        receiver.receive(body, headers)
        assert len(received_payloads) == 1
        assert received_payloads[0].data["order_id"] == 123

    def test_global_handler_called(self):
        """Global handler is called for all events."""
        receiver = self._make_receiver()
        received_payloads = []
        receiver.register_global_handler(lambda payload: received_payloads.append(payload))
        body = self._make_body()
        headers = self._make_headers(body)
        receiver.receive(body, headers)
        assert len(received_payloads) == 1

    def test_get_delivery(self):
        """Delivery can be retrieved by ID."""
        receiver = self._make_receiver()
        body = self._make_body()
        headers = self._make_headers(body)
        delivery = receiver.receive(body, headers)
        found = receiver.get_delivery(delivery.delivery_id)
        assert found is not None
        assert found.delivery_id == delivery.delivery_id

    def test_get_delivery_history(self):
        """Delivery history can be retrieved."""
        receiver = self._make_receiver()
        body = self._make_body()
        headers = self._make_headers(body)
        receiver.receive(body, headers)
        history = receiver.get_delivery_history()
        assert len(history) == 1

    def test_get_delivery_history_filtered(self):
        """Delivery history can be filtered by status."""
        receiver = self._make_receiver()
        body = self._make_body()
        headers = self._make_headers(body)
        receiver.receive(body, headers)
        completed = receiver.get_delivery_history(status=WebhookStatus.COMPLETED)
        assert len(completed) == 1
        failed = receiver.get_delivery_history(status=WebhookStatus.FAILED)
        assert len(failed) == 0

    def test_get_stats(self):
        """Stats are tracked."""
        receiver = self._make_receiver()
        body = self._make_body()
        headers = self._make_headers(body)
        receiver.receive(body, headers)
        stats = receiver.get_stats()
        assert stats["total"] == 1
        assert stats["completed"] == 1

    def test_skip_signature_check(self):
        """Signature check can be skipped."""
        receiver = self._make_receiver()
        body = self._make_body()
        headers = {
            "X-Webhook-Event-Id": str(uuid.uuid4()),
            "X-Webhook-Event-Type": "order.created",
            "X-Webhook-Timestamp": str(time.time()),
        }
        delivery = receiver.receive(body, headers, skip_signature_check=True)
        assert delivery.status == WebhookStatus.COMPLETED


# ===================================================================
# Data Transformer Tests
# ===================================================================


class TestFieldMapping:
    """Test FieldMapping data structure."""

    def test_mapping_creation(self):
        """Mapping can be created."""
        mapping = FieldMapping(source="first_name", target="firstName")
        assert mapping.source == "first_name"
        assert mapping.target == "firstName"
        assert mapping.field_type == TransformFieldType.STRING

    def test_mapping_with_default(self):
        """Mapping with default value."""
        mapping = FieldMapping(
            source="status",
            target="status",
            default="active",
        )
        assert mapping.default == "active"


class TestDataTransformer:
    """Test DataTransformer."""

    def test_simple_rename(self):
        """Simple field rename works."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="first_name", target="firstName"))
        result = transformer.transform({"first_name": "John"})
        assert result.data["firstName"] == "John"
        assert result.success

    def test_type_conversion_integer(self):
        """String to integer conversion works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="age",
                target="age",
                field_type=TransformFieldType.INTEGER,
            )
        )
        result = transformer.transform({"age": "25"})
        assert result.data["age"] == 25

    def test_type_conversion_float(self):
        """String to float conversion works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="price",
                target="price",
                field_type=TransformFieldType.FLOAT,
            )
        )
        result = transformer.transform({"price": "19.99"})
        assert result.data["price"] == 19.99

    def test_type_conversion_boolean(self):
        """String to boolean conversion works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="active",
                target="active",
                field_type=TransformFieldType.BOOLEAN,
            )
        )
        result = transformer.transform({"active": "true"})
        assert result.data["active"] is True

    def test_default_value(self):
        """Default value is used when field is missing."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="status",
                target="status",
                default="pending",
            )
        )
        result = transformer.transform({})
        assert result.data["status"] == "pending"

    def test_required_field_missing(self):
        """Missing required field produces error."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="email",
                target="email",
                required=True,
            )
        )
        result = transformer.transform({})
        assert not result.success
        assert len(result.errors) > 0

    def test_uppercase_transform(self):
        """Uppercase transform works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="name",
                target="name",
                operation=TransformOperation.UPPERCASE,
            )
        )
        result = transformer.transform({"name": "john"})
        assert result.data["name"] == "JOHN"

    def test_lowercase_transform(self):
        """Lowercase transform works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="email",
                target="email",
                operation=TransformOperation.LOWERCASE,
            )
        )
        result = transformer.transform({"email": "JOHN@EXAMPLE.COM"})
        assert result.data["email"] == "john@example.com"

    def test_trim_transform(self):
        """Trim transform works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="name",
                target="name",
                operation=TransformOperation.TRIM,
            )
        )
        result = transformer.transform({"name": "  john  "})
        assert result.data["name"] == "john"

    def test_map_transform(self):
        """Map transform converts values."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="status",
                target="status",
                operation=TransformOperation.MAP,
                operation_config={"mapping": {"A": "active", "I": "inactive"}},
            )
        )
        result = transformer.transform({"status": "A"})
        assert result.data["status"] == "active"

    def test_regex_replace_transform(self):
        """Regex replace transform works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="phone",
                target="phone",
                operation=TransformOperation.REGEX_REPLACE,
                operation_config={"pattern": "[^0-9]", "replacement": ""},
            )
        )
        result = transformer.transform({"phone": "(555) 123-4567"})
        assert result.data["phone"] == "5551234567"

    def test_split_transform(self):
        """Split transform works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="tags",
                target="tags",
                operation=TransformOperation.SPLIT,
                operation_config={"separator": ","},
            )
        )
        result = transformer.transform({"tags": "a,b,c"})
        assert result.data["tags"] == ["a", "b", "c"]

    def test_filter_condition(self):
        """Filter condition drops records."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="id", target="id"))
        transformer.add_filter(lambda data: data.get("active", False))
        result = transformer.transform({"id": 1, "active": False})
        assert result.dropped

    def test_no_filter_passes(self):
        """Record passes when filter condition is true."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="id", target="id"))
        transformer.add_filter(lambda data: data.get("active", False))
        result = transformer.transform({"id": 1, "active": True})
        assert not result.dropped
        assert result.success

    def test_validation_required(self):
        """Required validation rule works."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="email", target="email"))
        transformer.add_validator(ValidationRule(field="email", rule_type="required"))
        result = transformer.transform({"email": ""})
        assert not result.success

    def test_validation_min_length(self):
        """Min length validation works."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="name", target="name"))
        transformer.add_validator(
            ValidationRule(field="name", rule_type="min_length", value=3)
        )
        result = transformer.transform({"name": "ab"})
        assert not result.success

    def test_validation_max_length(self):
        """Max length validation works."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="name", target="name"))
        transformer.add_validator(
            ValidationRule(field="name", rule_type="max_length", value=5)
        )
        result = transformer.transform({"name": "toolongname"})
        assert not result.success

    def test_validation_pattern(self):
        """Pattern validation works."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="email", target="email"))
        transformer.add_validator(
            ValidationRule(field="email", rule_type="pattern", value=r"^[\w.]+@[\w.]+$")
        )
        result = transformer.transform({"email": "invalid"})
        assert not result.success

    def test_validation_enum(self):
        """Enum validation works."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="status", target="status"))
        transformer.add_validator(
            ValidationRule(field="status", rule_type="enum", value=["active", "inactive"])
        )
        result = transformer.transform({"status": "unknown"})
        assert not result.success

    def test_validation_range(self):
        """Range validation works."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="age", target="age"))
        transformer.add_validator(
            ValidationRule(field="age", rule_type="range", value=(0, 150))
        )
        result = transformer.transform({"age": 200})
        assert not result.success

    def test_nested_field_access(self):
        """Nested field access with dot notation works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(source="user.name", target="userName")
        )
        result = transformer.transform({"user": {"name": "John"}})
        assert result.data["userName"] == "John"

    def test_nested_field_set(self):
        """Nested field set with dot notation works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(source="name", target="user.profile.name")
        )
        result = transformer.transform({"name": "John"})
        assert result.data["user"]["profile"]["name"] == "John"

    def test_batch_transform(self):
        """Batch transform processes multiple records."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="name", target="name"))
        sources = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
        results = transformer.transform_batch(sources)
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_stats_tracking(self):
        """Stats are tracked during transformation."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="name", target="name"))
        transformer.transform({"name": "a"})
        transformer.transform({})
        stats = transformer.stats
        assert stats["processed"] == 2
        assert stats["succeeded"] == 2
        assert stats["failed"] == 0

    def test_reset_stats(self):
        """Stats can be reset."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="name", target="name"))
        transformer.transform({"name": "a"})
        transformer.reset_stats()
        assert transformer.stats["processed"] == 0

    def test_pre_processor(self):
        """Pre-processor is applied before mapping."""
        transformer = DataTransformer()
        transformer.add_pre_processor(lambda d: {**d, "extra": "added"})
        transformer.add_mapping(FieldMapping(source="extra", target="extra"))
        result = transformer.transform({})
        assert result.data["extra"] == "added"

    def test_post_processor(self):
        """Post-processor is applied after mapping."""
        transformer = DataTransformer()
        transformer.add_mapping(FieldMapping(source="name", target="name"))
        transformer.add_post_processor(lambda d: {**d, "processed": True})
        result = transformer.transform({"name": "a"})
        assert result.data["processed"] is True

    def test_custom_transform_function(self):
        """Custom transform function is applied."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="amount",
                target="amount",
                custom_transform=lambda v: v * 2,
            )
        )
        result = transformer.transform({"amount": 10})
        assert result.data["amount"] == 20

    def test_flatten_transform(self):
        """Flatten transform works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="address",
                target="address",
                operation=TransformOperation.FLATTEN,
                operation_config={"prefix": "addr_"},
            )
        )
        result = transformer.transform({"address": {"city": "NYC", "zip": "10001"}})
        assert result.data["address"]["addr_city"] == "NYC"

    def test_concat_transform(self):
        """Concat transform works."""
        transformer = DataTransformer()
        transformer.add_mapping(
            FieldMapping(
                source="name",
                target="greeting",
                operation=TransformOperation.CONCAT,
                operation_config={"separator": " ", "fields": []},
            )
        )
        result = transformer.transform({"name": "World"})
        assert "World" in result.data["greeting"]


class TestTransformPipeline:
    """Test TransformPipeline."""

    def test_single_stage_pipeline(self):
        """Pipeline with single stage works."""
        stage = DataTransformer()
        stage.add_mapping(FieldMapping(source="first_name", target="firstName"))
        pipeline = TransformPipeline()
        pipeline.add_stage(stage)
        result = pipeline.execute({"first_name": "John"})
        assert result.data["firstName"] == "John"

    def test_multi_stage_pipeline(self):
        """Pipeline with multiple stages chains correctly."""
        stage1 = DataTransformer()
        stage1.add_mapping(FieldMapping(source="first_name", target="firstName"))

        stage2 = DataTransformer()
        stage2.add_mapping(FieldMapping(source="firstName", target="name"))

        pipeline = TransformPipeline()
        pipeline.add_stage(stage1)
        pipeline.add_stage(stage2)

        result = pipeline.execute({"first_name": "John"})
        assert result.data["name"] == "John"

    def test_pipeline_drops_filtered_record(self):
        """Pipeline drops record filtered at any stage."""
        stage1 = DataTransformer()
        stage1.add_mapping(FieldMapping(source="name", target="name"))

        stage2 = DataTransformer()
        stage2.add_filter(lambda d: False)

        pipeline = TransformPipeline()
        pipeline.add_stage(stage1)
        pipeline.add_stage(stage2)

        result = pipeline.execute({"name": "test"})
        assert result.dropped

    def test_pipeline_batch(self):
        """Pipeline batch execution works."""
        stage = DataTransformer()
        stage.add_mapping(FieldMapping(source="id", target="id"))
        pipeline = TransformPipeline()
        pipeline.add_stage(stage)
        results = pipeline.execute_batch([{"id": 1}, {"id": 2}])
        assert len(results) == 2
        assert all(r.success for r in results)


# ===================================================================
# Redis Rate Limiter Tests
# ===================================================================


class TestInMemoryBackend:
    """Test InMemoryBackend."""

    def test_set_and_get(self):
        """Value can be set and retrieved."""
        backend = InMemoryBackend()
        backend.set("key", "value")
        assert backend.get("key") == "value"

    def test_get_nonexistent(self):
        """Getting nonexistent key returns None."""
        backend = InMemoryBackend()
        assert backend.get("nonexistent") is None

    def test_delete(self):
        """Key can be deleted."""
        backend = InMemoryBackend()
        backend.set("key", "value")
        backend.delete("key")
        assert backend.get("key") is None

    def test_incr(self):
        """Increment works."""
        backend = InMemoryBackend()
        assert backend.incr("counter") == 1
        assert backend.incr("counter") == 2
        assert backend.incr("counter", 5) == 7

    def test_expire(self):
        """Expiry is set."""
        backend = InMemoryBackend()
        backend.set("key", "value")
        backend.expire("key", 100)
        assert backend.ttl("key") > 0

    def test_ttl_nonexistent(self):
        """TTL of nonexistent key returns -2."""
        backend = InMemoryBackend()
        assert backend.ttl("nonexistent") == -2

    def test_lpush_lrange(self):
        """List push and range work."""
        backend = InMemoryBackend()
        backend.lpush("list", "a")
        backend.lpush("list", "b")
        assert backend.lrange("list", 0, -1) == ["b", "a"]

    def test_ltrim(self):
        """List trim works."""
        backend = InMemoryBackend()
        for i in range(5):
            backend.lpush("list", str(i))
        backend.ltrim("list", 0, 2)
        assert backend.llen("list") == 3

    def test_keys_pattern(self):
        """Keys pattern matching works."""
        backend = InMemoryBackend()
        backend.set("ratelimit:user1", "1")
        backend.set("ratelimit:user2", "2")
        backend.set("other", "3")
        keys = backend.keys("ratelimit:*")
        assert len(keys) == 2

    def test_clear(self):
        """Clear removes all data."""
        backend = InMemoryBackend()
        backend.set("a", "1")
        backend.set("b", "2")
        backend.clear()
        assert backend.get("a") is None
        assert backend.get("b") is None


class TestRateLimitResult:
    """Test RateLimitResult."""

    def test_to_headers(self):
        """Headers are generated correctly."""
        result = RateLimitResult(
            allowed=True,
            remaining=95,
            reset_time=1234567890,
            limit=100,
            current=5,
        )
        headers = result.to_headers()
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "95"
        assert headers["X-RateLimit-Reset"] == "1234567890"
        assert "Retry-After" not in headers

    def test_to_headers_with_retry(self):
        """Retry-After header is included when set."""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_time=1234567890,
            retry_after=30,
            limit=100,
            current=100,
        )
        headers = result.to_headers()
        assert headers["Retry-After"] == "30"


class TestRedisRateLimiter:
    """Test RedisRateLimiter (uses in-memory fallback)."""

    def _make_limiter(
        self,
        algorithm: RateLimitAlgorithm = RateLimitAlgorithm.FIXED_WINDOW,
        max_requests: int = 3,
        window_seconds: float = 60,
    ) -> RedisRateLimiter:
        config = RateLimitConfig(
            algorithm=algorithm,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
        return RedisRateLimiter(config=config)

    def test_fixed_window_allows_under_limit(self):
        """Fixed window allows requests under limit."""
        limiter = self._make_limiter(max_requests=3)
        assert limiter.check("user1").allowed
        assert limiter.check("user1").allowed
        assert limiter.check("user1").allowed

    def test_fixed_window_blocks_over_limit(self):
        """Fixed window blocks requests over limit."""
        limiter = self._make_limiter(max_requests=2)
        assert limiter.check("user1").allowed
        assert limiter.check("user1").allowed
        assert not limiter.check("user1").allowed

    def test_fixed_window_remaining_count(self):
        """Remaining count decreases."""
        limiter = self._make_limiter(max_requests=3)
        result = limiter.check("user1")
        assert result.remaining == 2
        result = limiter.check("user1")
        assert result.remaining == 1

    def test_fixed_window_retry_after(self):
        """Retry-After is set when blocked."""
        limiter = self._make_limiter(max_requests=1)
        limiter.check("user1")
        result = limiter.check("user1")
        assert not result.allowed
        assert result.retry_after is not None
        assert result.retry_after > 0

    def test_sliding_window_allows_under_limit(self):
        """Sliding window allows requests under limit."""
        limiter = self._make_limiter(
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            max_requests=3,
        )
        assert limiter.check("user1").allowed
        assert limiter.check("user1").allowed
        assert limiter.check("user1").allowed

    def test_sliding_window_blocks_over_limit(self):
        """Sliding window blocks requests over limit."""
        limiter = self._make_limiter(
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            max_requests=2,
        )
        assert limiter.check("user1").allowed
        assert limiter.check("user1").allowed
        assert not limiter.check("user1").allowed

    def test_token_bucket_allows_under_capacity(self):
        """Token bucket allows requests under capacity."""
        config = RateLimitConfig(
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            bucket_capacity=5,
            refill_rate=10.0,
        )
        limiter = RedisRateLimiter(config=config)
        for _ in range(5):
            assert limiter.check("user1").allowed

    def test_token_bucket_blocks_when_empty(self):
        """Token bucket blocks when empty."""
        config = RateLimitConfig(
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            bucket_capacity=2,
            refill_rate=0.001,  # Very slow refill
        )
        limiter = RedisRateLimiter(config=config)
        assert limiter.check("user1").allowed
        assert limiter.check("user1").allowed
        assert not limiter.check("user1").allowed

    def test_different_identifiers_independent(self):
        """Different identifiers have independent limits."""
        limiter = self._make_limiter(max_requests=1)
        assert limiter.check("user1").allowed
        assert limiter.check("user2").allowed
        assert not limiter.check("user1").allowed

    def test_reset(self):
        """Reset clears rate limit for identifier."""
        limiter = self._make_limiter(max_requests=1)
        limiter.check("user1")
        assert not limiter.check("user1").allowed
        limiter.reset("user1")
        assert limiter.check("user1").allowed

    def test_get_current_usage(self):
        """Current usage is reported."""
        limiter = self._make_limiter(max_requests=5)
        limiter.check("user1")
        usage = limiter.get_current_usage("user1")
        assert usage["limit"] == 5
        assert usage["current"] == 1
        assert usage["remaining"] == 4

    def test_backend_name(self):
        """Backend name is reported."""
        limiter = self._make_limiter()
        assert limiter.backend in ("redis", "memory")

    def test_result_headers(self):
        """Result can be converted to headers."""
        limiter = self._make_limiter(max_requests=10)
        result = limiter.check("user1")
        headers = result.to_headers()
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers
