"""Advanced Agent-Reach Module for APEX-OS Business Platform.

Provides multi-agent orchestration, health monitoring, priority message
routing, consistent-hashing load balancing, and performance analytics.
"""

from __future__ import annotations

import hashlib
import heapq
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set, Tuple


class Priority(IntEnum):
    """Message priority levels (lower value = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(order=True)
class RoutedMessage:
    """A message enqueued for delivery to an agent."""
    priority: Priority
    timestamp: float = field(compare=True)
    payload: Any = field(compare=False)
    recipient: str = field(compare=False, default="")


class PriorityMessageRouter:
    """Routes messages to agents using a priority queue."""

    def __init__(self) -> None:
        self._queue: List[RoutedMessage] = []
        self._lock = threading.Lock()

    def send(self, recipient: str, payload: Any, priority: Priority = Priority.NORMAL) -> None:
        """Enqueue a message for *recipient*."""
        with self._lock:
            heapq.heappush(self._queue, RoutedMessage(priority, time.monotonic(), payload, recipient))

    def receive(self, agent_id: str) -> Optional[Any]:
        """Dequeue the highest-priority message for *agent_id*."""
        with self._lock:
            for i, msg in enumerate(self._queue):
                if msg.recipient == agent_id:
                    return self._queue.pop(i).payload
        return None

    def size(self) -> int:
        """Return the number of queued messages."""
        return len(self._queue)


class ConsistentHashRing:
    """Consistent hashing ring for agent load balancing."""

    def __init__(self, replicas: int = 150) -> None:
        self.replicas = replicas
        self._ring: Dict[int, str] = {}
        self._sorted_keys: List[int] = []
        self._nodes: Set[str] = set()

    def add_node(self, node: str) -> None:
        """Add a node to the ring."""
        if node in self._nodes:
            return
        self._nodes.add(node)
        for i in range(self.replicas):
            key = self._hash(f"{node}:{i}")
            self._ring[key] = node
        self._sorted_keys = sorted(self._ring)

    def remove_node(self, node: str) -> None:
        """Remove a node from the ring."""
        if node not in self._nodes:
            return
        self._nodes.discard(node)
        for i in range(self.replicas):
            key = self._hash(f"{node}:{i}")
            del self._ring[key]
        self._sorted_keys = sorted(self._ring)

    def get_node(self, key: str) -> Optional[str]:
        """Return the node responsible for *key*."""
        if not self._ring:
            return None
        h = self._hash(key)
        idx = self._bisect_right(h)
        return self._ring[self._sorted_keys[idx]]

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def _bisect_right(self, h: int) -> int:
        lo, hi = 0, len(self._sorted_keys)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._sorted_keys[mid] < h:
                lo = mid + 1
            else:
                hi = mid
        return lo % len(self._sorted_keys)


class AgentHealthMonitor:
    """Monitors agent liveness via periodic heartbeats."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._heartbeats: Dict[str, float] = {}
        self._lock = threading.Lock()

    def beat(self, agent_id: str) -> None:
        """Record a heartbeat from *agent_id*."""
        with self._lock:
            self._heartbeats[agent_id] = time.monotonic()

    def is_healthy(self, agent_id: str) -> bool:
        """Return True if the agent's last heartbeat is within timeout."""
        with self._lock:
            last = self._heartbeats.get(agent_id)
        return last is not None and (time.monotonic() - last) < self.timeout

    def prune(self) -> List[str]:
        """Remove and return agents whose heartbeat has expired."""
        expired: List[str] = []
        with self._lock:
            now = time.monotonic()
            expired = [a for a, t in self._heartbeats.items() if now - t >= self.timeout]
            for a in expired:
                del self._heartbeats[a]
        return expired


@dataclass
class AgentStats:
    """Performance metrics for a single agent."""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_latency: float = 0.0
    last_heartbeat: float = 0.0

    @property
    def avg_latency(self) -> float:
        done = self.tasks_completed + self.tasks_failed
        return self.total_latency / done if done else 0.0

    @property
    def success_rate(self) -> float:
        done = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / done if done else 0.0


class AgentPerformanceAnalytics:
    """Collects and reports per-agent performance metrics."""

    def __init__(self) -> None:
        self._stats: Dict[str, AgentStats] = defaultdict(AgentStats)
        self._lock = threading.Lock()

    def record(self, agent_id: str, latency: float, success: bool) -> None:
        """Record a task outcome for *agent_id*."""
        with self._lock:
            s = self._stats[agent_id]
            s.total_latency += latency
            if success:
                s.tasks_completed += 1
            else:
                s.tasks_failed += 1

    def heartbeat(self, agent_id: str) -> None:
        with self._lock:
            self._stats[agent_id].last_heartbeat = time.monotonic()

    def report(self, agent_id: str) -> Dict[str, float]:
        with self._lock:
            s = self._stats[agent_id]
        return {
            "tasks_completed": s.tasks_completed,
            "tasks_failed": s.tasks_failed,
            "avg_latency": s.avg_latency,
            "success_rate": s.success_rate,
        }

    def leaderboard(self, top_n: int = 5) -> List[Tuple[str, float]]:
        with self._lock:
            ranked = sorted(self._stats.items(), key=lambda kv: kv[1].success_rate, reverse=True)
        return [(a, s.success_rate) for a, s in ranked[:top_n]]


class AgentOrchestrator:
    """Coordinates agents: dispatch, health, routing, and analytics."""

    def __init__(self, replicas: int = 150, heartbeat_timeout: float = 30.0) -> None:
        self.ring = ConsistentHashRing(replicas)
        self.monitor = AgentHealthMonitor(heartbeat_timeout)
        self.router = PriorityMessageRouter()
        self.analytics = AgentPerformanceAnalytics()
        self._agents: Set[str] = set()
        self._lock = threading.Lock()

    def register(self, agent_id: str) -> None:
        """Register a new agent."""
        with self._lock:
            self._agents.add(agent_id)
        self.ring.add_node(agent_id)
        self.monitor.beat(agent_id)

    def deregister(self, agent_id: str) -> None:
        """Remove an agent from the orchestrator."""
        with self._lock:
            self._agents.discard(agent_id)
        self.ring.remove_node(agent_id)

    def dispatch(self, task_key: str, payload: Any, priority: Priority = Priority.NORMAL) -> Optional[str]:
        """Dispatch a task to the agent responsible for *task_key*."""
        agent = self.ring.get_node(task_key)
        if agent is None:
            return None
        self.router.send(agent, payload, priority)
        return agent

    def heartbeat(self, agent_id: str) -> None:
        """Forward a heartbeat to the health monitor and analytics."""
        self.monitor.beat(agent_id)
        self.analytics.heartbeat(agent_id)

    def poll(self, agent_id: str) -> Optional[Any]:
        """Poll for the next message destined for *agent_id*."""
        return self.router.receive(agent_id)

    def record_result(self, agent_id: str, latency: float, success: bool) -> None:
        """Record a task result for analytics."""
        self.analytics.record(agent_id, latency, success)

    def health_check(self) -> List[str]:
        """Prune unhealthy agents and return their IDs."""
        expired = self.monitor.prune()
        for agent_id in expired:
            self.deregister(agent_id)
        return expired

    def stats(self, agent_id: str) -> Dict[str, float]:
        """Return analytics for *agent_id*."""
        return self.analytics.report(agent_id)

    def top_agents(self, n: int = 5) -> List[Tuple[str, float]]:
        """Return the top-N agents by success rate."""
        return self.analytics.leaderboard(n)
