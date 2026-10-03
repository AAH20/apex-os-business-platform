"""Message broker with pub/sub support for agent communication."""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Any, Callable, Deque, Dict, List, Optional

from .models import Channel, Message


class MessageBroker:
    """Pub/sub message broker with channel-based subscriptions and queuing."""

    def __init__(self, max_queue_size: int = 1000):
        self._channels: Dict[str, Channel] = {}
        self._subscribers: Dict[str, List[str]] = defaultdict(list)
        self._queues: Dict[str, Deque[Message]] = defaultdict(deque)
        self._max_queue_size = max_queue_size
        self._lock = threading.Lock()
        self._handlers: Dict[str, List[Callable[[Message], None]]] = defaultdict(list)

    def create_channel(self, name: str, channel_id: Optional[str] = None) -> Channel:
        channel = Channel(id=channel_id or name, name=name)
        with self._lock:
            self._channels[channel.id] = channel
        return channel

    def delete_channel(self, channel_id: str) -> bool:
        with self._lock:
            if channel_id in self._channels:
                del self._channels[channel_id]
                self._subscribers.pop(channel_id, None)
                return True
        return False

    def subscribe(self, channel_id: str, agent_id: str) -> bool:
        with self._lock:
            channel = self._channels.get(channel_id)
            if not channel:
                return False
            result = channel.subscribe(agent_id)
            if result:
                self._subscribers[channel_id].append(agent_id)
            return result

    def unsubscribe(self, channel_id: str, agent_id: str) -> bool:
        with self._lock:
            channel = self._channels.get(channel_id)
            if not channel:
                return False
            result = channel.unsubscribe(agent_id)
            if result and agent_id in self._subscribers.get(channel_id, []):
                self._subscribers[channel_id].remove(agent_id)
            return result

    def publish(self, message: Message) -> int:
        """Publish a message to a channel. Returns delivery count."""
        channel_id = message.channel_id
        if not channel_id:
            return 0
        with self._lock:
            channel = self._channels.get(channel_id)
            if not channel:
                return 0
            delivered = 0
            for agent_id in channel.subscribers:
                if len(self._queues[agent_id]) < self._max_queue_size:
                    self._queues[agent_id].append(message)
                    delivered += 1
            for handler in self._handlers.get(channel_id, []):
                handler(message)
            return delivered

    def register_handler(self, channel_id: str, handler: Callable[[Message], None]) -> None:
        self._handlers[channel_id].append(handler)

    def unregister_handler(self, channel_id: str, handler: Callable[[Message], None]) -> bool:
        if channel_id in self._handlers and handler in self._handlers[channel_id]:
            self._handlers[channel_id].remove(handler)
            return True
        return False

    def consume(self, agent_id: str) -> Optional[Message]:
        """Consume the next message from an agent's queue."""
        with self._lock:
            queue = self._queues.get(agent_id)
            if queue:
                return queue.popleft()
        return None

    def queue_size(self, agent_id: str) -> int:
        with self._lock:
            return len(self._queues.get(agent_id, []))

    @property
    def channel_count(self) -> int:
        return len(self._channels)
