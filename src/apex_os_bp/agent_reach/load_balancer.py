"""Load balancing strategies for agent message distribution."""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional

from .models import Agent


class RoundRobin:
    """Distributes messages sequentially across available agents."""

    def __init__(self, agents: Optional[List[Agent]] = None):
        self._agents: List[Agent] = list(agents) if agents else []
        self._index: int = 0

    def add_agent(self, agent: Agent) -> None:
        self._agents.append(agent)

    def remove_agent(self, agent_id: str) -> bool:
        for i, a in enumerate(self._agents):
            if a.id == agent_id:
                self._agents.pop(i)
                self._index = self._index % max(1, len(self._agents))
                return True
        return False

    def select(self) -> Optional[Agent]:
        available = [a for a in self._agents if a.is_available]
        if not available:
            return None
        agent = available[self._index % len(available)]
        self._index = (self._index + 1) % len(available)
        return agent


class LeastConnections:
    """Selects the agent with the fewest active connections."""

    def __init__(self, agents: Optional[List[Agent]] = None):
        self._agents: List[Agent] = list(agents) if agents else []

    def add_agent(self, agent: Agent) -> None:
        self._agents.append(agent)

    def remove_agent(self, agent_id: str) -> bool:
        for i, a in enumerate(self._agents):
            if a.id == agent_id:
                self._agents.pop(i)
                return True
        return False

    def select(self) -> Optional[Agent]:
        available = [a for a in self._agents if a.is_available]
        if not available:
            return None
        return min(available, key=lambda a: a.active_connections)


class ConsistentHashing:
    """Maps messages to agents using consistent hashing with virtual nodes."""

    VIRTUAL_NODES = 150

    def __init__(self, agents: Optional[List[Agent]] = None, virtual_nodes: int = VIRTUAL_NODES):
        self._virtual_nodes = virtual_nodes
        self._ring: Dict[int, Agent] = {}
        self._agents: Dict[str, Agent] = {}
        if agents:
            for agent in agents:
                self.add_agent(agent)

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_agent(self, agent: Agent) -> None:
        self._agents[agent.id] = agent
        for i in range(self._virtual_nodes):
            h = self._hash(f"{agent.id}:{i}")
            self._ring[h] = agent

    def remove_agent(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        self._ring = {h: a for h, a in self._ring.items() if a.id != agent_id}
        return True

    def select(self, key: Optional[str] = None) -> Optional[Agent]:
        if not self._ring:
            return None
        if key is None:
            key = str(id(object()))
        h = self._hash(key)
        sorted_hashes = sorted(self._ring.keys())
        for ring_hash in sorted_hashes:
            if ring_hash >= h:
                agent = self._ring[ring_hash]
                if agent.is_available:
                    return agent
        agent = self._ring[sorted_hashes[0]]
        return agent if agent.is_available else None
