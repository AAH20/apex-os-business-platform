"""Live chat module for real-time customer support."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ChatStatus(str, Enum):
    """Lifecycle states for a chat session."""

    QUEUED = "queued"
    ACTIVE = "active"
    WAITING = "waiting"
    ENDED = "ended"
    ABANDONED = "abandoned"


@dataclass
class ChatMessage:
    """Represents a single message in a chat session."""

    sender_id: str
    content: str
    sender_type: str = "customer"  # "customer" or "agent"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Serialize message to dictionary."""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "content": self.content,
            "sender_type": self.sender_type,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ChatSession:
    """Represents a live chat session between customer and agent."""

    customer_id: str
    agent_id: Optional[str] = None
    status: ChatStatus = ChatStatus.QUEUED
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    messages: list[ChatMessage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize session to dictionary."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }


class LiveChatManager:
    """Manages live chat sessions, queues, and messaging."""

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._agent_sessions: dict[str, list[str]] = {}

    def start_session(
        self, customer_id: str, metadata: Optional[dict] = None
    ) -> ChatSession:
        """Start a new chat session for a customer."""
        session = ChatSession(
            customer_id=customer_id,
            metadata=metadata or {},
        )
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Retrieve a chat session by ID."""
        return self._sessions.get(session_id)

    def assign_agent(self, session_id: str, agent_id: str) -> Optional[ChatSession]:
        """Assign an agent to a chat session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.agent_id = agent_id
        session.status = ChatStatus.ACTIVE
        if agent_id not in self._agent_sessions:
            self._agent_sessions[agent_id] = []
        self._agent_sessions[agent_id].append(session_id)
        return session

    def send_message(
        self,
        session_id: str,
        sender_id: str,
        content: str,
        sender_type: str = "customer",
    ) -> Optional[ChatMessage]:
        """Send a message in a chat session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.status == ChatStatus.ENDED:
            raise ValueError("Cannot send messages to an ended session")
        message = ChatMessage(
            sender_id=sender_id,
            content=content,
            sender_type=sender_type,
        )
        session.messages.append(message)
        return message

    def end_session(self, session_id: str) -> Optional[ChatSession]:
        """End a chat session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.status = ChatStatus.ENDED
        session.ended_at = datetime.now(timezone.utc)
        return session

    def abandon_session(self, session_id: str) -> Optional[ChatSession]:
        """Mark a session as abandoned."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.status = ChatStatus.ABANDONED
        session.ended_at = datetime.now(timezone.utc)
        return session

    def get_queue(self) -> list[ChatSession]:
        """Return all queued sessions waiting for an agent."""
        return [
            s for s in self._sessions.values() if s.status == ChatStatus.QUEUED
        ]

    def get_active_sessions(self) -> list[ChatSession]:
        """Return all active chat sessions."""
        return [
            s for s in self._sessions.values() if s.status == ChatStatus.ACTIVE
        ]

    def get_agent_sessions(self, agent_id: str) -> list[ChatSession]:
        """Return all sessions assigned to an agent."""
        session_ids = self._agent_sessions.get(agent_id, [])
        return [
            self._sessions[sid]
            for sid in session_ids
            if sid in self._sessions
        ]

    def get_customer_sessions(self, customer_id: str) -> list[ChatSession]:
        """Return all sessions for a customer."""
        return [
            s for s in self._sessions.values() if s.customer_id == customer_id
        ]

    def get_session_count(self) -> int:
        """Return total number of chat sessions."""
        return len(self._sessions)

    def get_queue_length(self) -> int:
        """Return number of sessions waiting in queue."""
        return len(self.get_queue())

    def get_average_wait_time(self) -> float:
        """Return average wait time in seconds for queued sessions."""
        queued = self.get_queue()
        if not queued:
            return 0.0
        now = datetime.now(timezone.utc)
        total_wait = sum(
            (now - s.started_at).total_seconds() for s in queued
        )
        return total_wait / len(queued)
