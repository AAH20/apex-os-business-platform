"""Core data models for Agent-Reach."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentStatus(str, Enum):
    """Operational status of an agent."""

    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class Agent:
    """Represents an agent that can receive and process messages."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: AgentStatus = AgentStatus.IDLE
    capacity: int = 10
    active_connections: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)

    @property
    def is_available(self) -> bool:
        return self.status != AgentStatus.OFFLINE and self.active_connections < self.capacity

    def assign(self) -> None:
        self.active_connections += 1
        if self.active_connections >= self.capacity:
            self.status = AgentStatus.BUSY

    def release(self) -> None:
        self.active_connections = max(0, self.active_connections - 1)
        if self.active_connections < self.capacity:
            self.status = AgentStatus.IDLE


@dataclass
class Message:
    """A message sent between agents or to a channel."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: Optional[str] = None
    recipient_id: Optional[str] = None
    channel_id: Optional[str] = None
    payload: Any = None
    priority: int = 0
    timestamp: float = field(default_factory=time.time)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class Channel:
    """A named communication channel for pub/sub messaging."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    subscribers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def subscribe(self, agent_id: str) -> bool:
        if agent_id not in self.subscribers:
            self.subscribers.append(agent_id)
            return True
        return False

    def unsubscribe(self, agent_id: str) -> bool:
        if agent_id in self.subscribers:
            self.subscribers.remove(agent_id)
            return True
        return False


@dataclass
class Route:
    """A routing rule mapping a source to target agents."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_pattern: str = "*"
    target_agent_ids: List[str] = field(default_factory=list)
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
