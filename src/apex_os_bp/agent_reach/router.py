"""Message router with load-balanced agent selection."""

from __future__ import annotations

import fnmatch
from typing import Dict, List, Optional

from .load_balancer import RoundRobin
from .models import Agent, Message, Route


class MessageRouter:
    """Routes messages to agents using configurable load balancing and route rules."""

    def __init__(self, load_balancer=None):
        self._agents: Dict[str, Agent] = {}
        self._routes: List[Route] = []
        self._load_balancer = load_balancer or RoundRobin()

    def register_agent(self, agent: Agent) -> None:
        self._agents[agent.id] = agent
        self._load_balancer.add_agent(agent)

    def unregister_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return self._load_balancer.remove_agent(agent_id)
        return False

    def add_route(self, route: Route) -> None:
        self._routes.append(route)
        self._routes.sort(key=lambda r: r.priority, reverse=True)

    def remove_route(self, route_id: str) -> bool:
        for i, r in enumerate(self._routes):
            if r.id == route_id:
                self._routes.pop(i)
                return True
        return False

    def _match_route(self, message: Message) -> Optional[Route]:
        for route in self._routes:
            if fnmatch.fnmatch(message.sender_id or "", route.source_pattern):
                return route
        return None

    def route(self, message: Message) -> Optional[Agent]:
        """Route a message to the best available agent."""
        route = self._match_route(message)
        if route and route.target_agent_ids:
            for agent_id in route.target_agent_ids:
                agent = self._agents.get(agent_id)
                if agent and agent.is_available:
                    agent.assign()
                    return agent
        agent = self._load_balancer.select()
        if agent:
            agent.assign()
        return agent

    def release(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.release()

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def route_count(self) -> int:
        return len(self._routes)
