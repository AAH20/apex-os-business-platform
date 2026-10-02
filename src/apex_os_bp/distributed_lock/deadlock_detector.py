"""Deadlock detection for distributed locks.

Builds a wait-for graph from lock acquisition attempts and detects
cycles indicating potential deadlocks.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LockOperation(Enum):
    """Type of lock operation."""

    ACQUIRE = "acquire"
    RELEASE = "release"
    RENEW = "renew"


@dataclass
class WaitForEdge:
    """Represents an edge in the wait-for graph.

    An edge from A to B means "A is waiting for B to release a lock".
    """

    waiter: str  # The transaction/owner waiting
    holder: str  # # The transaction/owner holding the lock
    lock_name: str
    operation: LockOperation = LockOperation.ACQUIRE
    timestamp: float = field(default_factory=time.monotonic)

    def __hash__(self) -> int:
        return hash((self.waiter, self.holder, self.lock_name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WaitForEdge):
            return NotImplemented
        return (
            self.waiter == other.waiter
            and self.holder == other.holder
            and self.lock_name == other.lock_name
        )


@dataclass
class DeadlockCycle:
    """Represents a detected deadlock cycle."""

    cycle: list[str]  # List of transaction IDs forming the cycle
    edges: list[WaitForEdge]  # Edges forming the cycle
    detected_at: float = field(default_factory=time.monotonic)

    def __str__(self) -> str:
        return " -> ".join(self.cycle + [self.cycle[0]])


class WaitForGraph:
    """Wait-for graph for deadlock detection.

    Maintains a directed graph where edges represent "waiting for"
    relationships between transactions/owners.
    """

    def __init__(self) -> None:
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._edges: dict[tuple[str, str], WaitForEdge] = {}
        self._lock = threading.RLock()

    def add_edge(self, edge: WaitForEdge) -> None:
        """Add a wait-for edge to the graph.

        Args:
            edge: The edge to add.
        """
        with self._lock:
            self._adjacency[edge.waiter].add(edge.holder)
            self._edges[(edge.waiter, edge.holder)] = edge

    def remove_edge(self, waiter: str, holder: str) -> bool:
        """Remove a wait-for edge from the graph.

        Args:
            waiter: The waiting transaction.
            holder: The holding transaction.

        Returns:
            True if the edge was removed, False if it didn't exist.
        """
        with self._lock:
            key = (waiter, holder)
            if key not in self._edges:
                return False
            del self._edges[key]
            self._adjacency[waiter].discard(holder)
            if not self._adjacency[waiter]:
                del self._adjacency[waiter]
            return True

    def remove_all_edges_for(self, transaction_id: str) -> int:
        """Remove all edges involving a transaction (as waiter or holder).

        Args:
            transaction_id: The transaction to remove.

        Returns:
            Number of edges removed.
        """
        with self._lock:
            count = 0
            # Remove as waiter
            if transaction_id in self._adjacency:
                for holder in list(self._adjacency[transaction_id]):
                    if self.remove_edge(transaction_id, holder):
                        count += 1
            # Remove as holder
            for waiter in list(self._adjacency.keys()):
                if self.remove_edge(waiter, transaction_id):
                    count += 1
            return count

    def detect_cycle(self) -> Optional[DeadlockCycle]:
        """Detect a cycle in the wait-for graph using DFS.

        Returns:
            DeadlockCycle if a cycle is found, None otherwise.
        """
        with self._lock:
            visited: set[str] = set()
            rec_stack: set[str] = set()
            path: list[str] = []

            def dfs(node: str) -> Optional[list[str]]:
                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                for neighbor in self._adjacency.get(node, set()):
                    if neighbor not in visited:
                        result = dfs(neighbor)
                        if result is not None:
                            return result
                    elif neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(neighbor)
                        return path[cycle_start:]

                path.pop()
                rec_stack.discard(node)
                return None

            for node in list(self._adjacency.keys()):
                if node not in visited:
                    cycle = dfs(node)
                    if cycle is not None:
                        # Build edges for the cycle
                        edges = []
                        for i in range(len(cycle)):
                            waiter = cycle[i]
                            holder = cycle[(i + 1) % len(cycle)]
                            edge = self._edges.get((waiter, holder))
                            if edge:
                                edges.append(edge)
                        return DeadlockCycle(cycle=cycle, edges=edges)

            return None

    def detect_all_cycles(self) -> list[DeadlockCycle]:
        """Detect all cycles in the wait-for graph.

        Returns:
            List of all detected deadlock cycles.
        """
        cycles = []
        while True:
            cycle = self.detect_cycle()
            if cycle is None:
                break
            cycles.append(cycle)
            # Remove one edge from the cycle to find more
            if cycle.edges:
                edge = cycle.edges[0]
                self.remove_edge(edge.waiter, edge.holder)
        return cycles

    def get_graph_state(self) -> dict[str, list[str]]:
        """Get the current state of the wait-for graph.

        Returns:
            Dict mapping each waiter to the list of holders it waits for.
        """
        with self._lock:
            return {k: list(v) for k, v in self._adjacency.items()}

    def clear(self) -> None:
        """Clear the entire graph."""
        with self._lock:
            self._adjacency.clear()
            self._edges.clear()

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        with self._lock:
            nodes = set(self._adjacency.keys())
            for holders in self._adjacency.values():
                nodes.update(holders)
            return len(nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        with self._lock:
            return len(self._edges)


class DeadlockDetector:
    """Detects deadlocks in distributed lock acquisitions.

    Maintains a wait-for graph and periodically checks for cycles.
    Can be used as a context manager or with explicit start/stop.

    Example:
        >>> detector = DeadlockDetector(check_interval=5.0)
        >>> detector.start()
        >>> # ... application code ...
        >>> detector.stop()
    """

    def __init__(
        self,
        check_interval: float = 10.0,
        max_graph_age_seconds: float = 300.0,
        on_deadlock_detected: Optional[Callable[[DeadlockCycle], None]] = None,
    ) -> None:
        """Initialize deadlock detector.

        Args:
            check_interval: How often to check for deadlocks (seconds).
            max_graph_age_seconds: Maximum age of edges before cleanup.
            on_deadlock_detected: Callback when a deadlock is detected.
        """
        self._graph = WaitForGraph()
        self._check_interval = check_interval
        self._max_graph_age = max_graph_age_seconds
        self._on_deadlock = on_deadlock_detected
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._detected_cycles: list[DeadlockCycle] = []
        self._lock = threading.Lock()

    @property
    def graph(self) -> WaitForGraph:
        return self._graph

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def detected_cycles(self) -> list[DeadlockCycle]:
        with self._lock:
            return list(self._detected_cycles)

    def record_wait(
        self,
        waiter: str,
        holder: str,
        lock_name: str,
        operation: LockOperation = LockOperation.ACQUIRE,
    ) -> None:
        """Record that `waiter` is waiting for `holder` to release a lock.

        Args:
            waiter: The transaction/owner that is waiting.
            holder: The transaction/owner that holds the lock.
            lock_name: The name of the lock being waited on.
            operation: The type of operation.
        """
        edge = WaitForEdge(
            waiter=waiter,
            holder=holder,
            lock_name=lock_name,
            operation=operation,
        )
        self._graph.add_edge(edge)

    def record_acquired(self, waiter: str, lock_name: str) -> None:
        """Record that a waiter has acquired a lock (remove wait edges).

        Args:
            waiter: The transaction that acquired the lock.
            lock_name: The name of the lock.
        """
        # Remove all wait edges for this waiter on this lock
        self._graph.remove_all_edges_for(waiter)

    def record_released(self, holder: str, lock_name: str) -> None:
        """Record that a holder has released a lock.

        Args:
            holder: The transaction that released the lock.
            lock_name: The name of the lock.
        """
        # Remove all wait edges where this holder is involved
        self._graph.remove_all_edges_for(holder)

    def check_deadlock(self) -> Optional[DeadlockCycle]:
        """Check for deadlocks immediately.

        Returns:
            DeadlockCycle if found, None otherwise.
        """
        cycle = self._graph.detect_cycle()
        if cycle:
            with self._lock:
                self._detected_cycles.append(cycle)
            if self._on_deadlock:
                try:
                    self._on_deadlock(cycle)
                except Exception as e:
                    logger.exception("Error in deadlock callback: %s", e)
            logger.error("Deadlock detected: %s", cycle)
        return cycle

    def start(self) -> None:
        """Start the background deadlock detection thread."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._detection_loop,
            name="deadlock-detector",
            daemon=True,
        )
        self._thread.start()
        logger.info("Deadlock detector started (interval=%.1fs)", self._check_interval)

    def stop(self) -> None:
        """Stop the background deadlock detection thread."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        logger.info("Deadlock detector stopped")

    def _detection_loop(self) -> None:
        """Background loop for periodic deadlock detection."""
        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=self._check_interval):
                break

            # Clean up old edges
            self._cleanup_old_edges()

            # Check for deadlocks
            self.check_deadlock()

    def _cleanup_old_edges(self) -> None:
        """Remove edges older than max_graph_age."""
        now = time.monotonic()
        to_remove = []
        for (waiter, holder), edge in list(self._graph._edges.items()):
            if now - edge.timestamp > self._max_graph_age:
                to_remove.append((waiter, holder))
        for waiter, holder in to_remove:
            self._graph.remove_edge(waiter, holder)

    def reset(self) -> None:
        """Reset the detector state."""
        self._graph.clear()
        with self._lock:
            self._detected_cycles.clear()

    def __enter__(self) -> DeadlockDetector:
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()
