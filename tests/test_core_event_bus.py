"""Tests for core event bus module."""
import pytest
from apex_os_bp.core.event_bus import Event, EventBus, EventHandler


class TestEvent:
    """Test event data structure."""

    def test_event_creation(self):
        """Event can be created with type and data."""
        event = Event(type="test.event", data={"key": "value"})
        assert event.type == "test.event"
        assert event.data == {"key": "value"}

    def test_event_with_metadata(self):
        """Event supports metadata."""
        event = Event(type="test.event", data={}, metadata={"source": "test"})
        assert event.metadata["source"] == "test"

    def test_event_timestamp(self):
        """Event has timestamp."""
        event = Event(type="test.event", data={})
        assert event.timestamp is not None


class TestEventBus:
    """Test event bus functionality."""

    def test_subscribe_and_publish(self):
        """Subscribed handler receives published event."""
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test.event", handler)
        bus.publish(Event(type="test.event", data={"key": "value"}))

        assert len(received) == 1
        assert received[0].data["key"] == "value"

    def test_unsubscribe(self):
        """Unsubscribed handler does not receive events."""
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test.event", handler)
        bus.unsubscribe("test.event", handler)
        bus.publish(Event(type="test.event", data={}))

        assert len(received) == 0

    def test_multiple_handlers(self):
        """Multiple handlers receive same event."""
        bus = EventBus()
        received_a = []
        received_b = []

        bus.subscribe("test.event", lambda e: received_a.append(e))
        bus.subscribe("test.event", lambda e: received_b.append(e))
        bus.publish(Event(type="test.event", data={}))

        assert len(received_a) == 1
        assert len(received_b) == 1

    def test_wildcard_subscription(self):
        """Wildcard subscription receives all events."""
        bus = EventBus()
        received = []

        bus.subscribe("*", lambda e: received.append(e))
        bus.publish(Event(type="test.event", data={}))
        bus.publish(Event(type="other.event", data={}))

        assert len(received) == 2

    def test_handler_exception_does_not_break_bus(self):
        """Handler exception does not break event bus."""
        bus = EventBus()
        received = []

        def bad_handler(event):
            raise ValueError("test error")

        def good_handler(event):
            received.append(event)

        bus.subscribe("test.event", bad_handler)
        bus.subscribe("test.event", good_handler)
        bus.publish(Event(type="test.event", data={}))

        assert len(received) == 1

    def test_event_history(self):
        """Event bus tracks event history."""
        bus = EventBus()
        bus.publish(Event(type="test.event", data={"n": 1}))
        bus.publish(Event(type="test.event", data={"n": 2}))

        history = bus.get_history()
        assert len(history) == 2

    def test_clear_history(self):
        """Event history can be cleared."""
        bus = EventBus()
        bus.publish(Event(type="test.event", data={}))
        bus.clear_history()
        assert len(bus.get_history()) == 0
