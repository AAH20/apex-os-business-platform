"""Agent Orchestration Module.

Manages multiple agents, routes tasks to appropriate agents,
coordinates parallel and sequential execution, and aggregates results.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional


class AgentStatus(str, Enum):
    """Status of an agent execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentResult:
    """Result returned by an agent after task execution."""

    agent_id: str
    task_id: str
    status: AgentStatus
    output: Any = None
    error: Optional[str] = None
    started_at: float = 0.0
    completed_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Execution duration in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return 0.0

    @property
    def success(self) -> bool:
        """Whether the agent completed successfully."""
        return self.status == AgentStatus.COMPLETED and self.error is None


@dataclass
class Agent:
    """An AI agent with a specific role and capabilities."""

    name: str
    role: str
    capabilities: list[str] = field(default_factory=list)
    handler: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
    max_concurrency: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    async def execute(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """Execute a task and return the result."""
        task_id = str(uuid.uuid4())
        started = time.time()
        ctx = context or {}

        if self.handler is None:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status=AgentStatus.FAILED,
                error=f"Agent '{self.name}' has no handler",
                started_at=started,
                completed_at=time.time(),
            )

        try:
            self._status = AgentStatus.RUNNING
            output = await self.handler(task, ctx)
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status=AgentStatus.COMPLETED,
                output=output,
                started_at=started,
                completed_at=time.time(),
            )
        except Exception as exc:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status=AgentStatus.FAILED,
                error=str(exc),
                started_at=started,
                completed_at=time.time(),
            )

    _status: AgentStatus = AgentStatus.PENDING

    @property
    def status(self) -> AgentStatus:
        return self._status


class AgentOrchestrator:
    """Orchestrates multiple agents for task execution.

    Supports sequential and parallel execution, task routing
    based on agent capabilities, and result aggregation.
    """

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}
        self._history: list[AgentResult] = []

    def register_agent(self, agent: Agent) -> None:
        """Register an agent with the orchestrator."""
        self._agents[agent.agent_id] = agent

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the orchestrator."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Retrieve an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[Agent]:
        """List all registered agents."""
        return list(self._agents.values())

    def find_agent_by_capability(self, capability: str) -> Optional[Agent]:
        """Find the first agent that has the given capability."""
        for agent in self._agents.values():
            if capability in agent.capabilities:
                return agent
        return None

    def find_agents_by_role(self, role: str) -> list[Agent]:
        """Find all agents with a specific role."""
        return [a for a in self._agents.values() if a.role == role]

    async def execute_single(
        self, agent_id: str, task: str, context: dict[str, Any] | None = None
    ) -> AgentResult:
        """Execute a single task on a specific agent."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return AgentResult(
                agent_id=agent_id,
                task_id=str(uuid.uuid4()),
                status=AgentStatus.FAILED,
                error=f"Agent '{agent_id}' not found",
            )
        result = await agent.execute(task, context)
        self._history.append(result)
        return result

    async def execute_parallel(
        self,
        tasks: list[tuple[str, str, dict[str, Any] | None]],
    ) -> list[AgentResult]:
        """Execute multiple tasks in parallel.

        Each task is a tuple of (agent_id, task_description, context).
        """
        coros = [
            self.execute_single(agent_id, task, ctx)
            for agent_id, task, ctx in tasks
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)
        processed: list[AgentResult] = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                agent_id = tasks[i][0]
                processed.append(
                    AgentResult(
                        agent_id=agent_id,
                        task_id=str(uuid.uuid4()),
                        status=AgentStatus.FAILED,
                        error=str(res),
                    )
                )
            else:
                processed.append(res)
        return processed

    async def execute_sequential(
        self,
        tasks: list[tuple[str, str, dict[str, Any] | None]],
    ) -> list[AgentResult]:
        """Execute tasks sequentially, passing context forward."""
        results: list[AgentResult] = []
        shared_context: dict[str, Any] = {}

        for agent_id, task, ctx in tasks:
            merged_ctx = {**shared_context, **(ctx or {})}
            result = await self.execute_single(agent_id, task, merged_ctx)
            results.append(result)
            if result.success and result.output is not None:
                shared_context[f"result_{len(results)}"] = result.output
            if not result.success:
                break

        return results

    async def route_and_execute(
        self, task: str, capability: str, context: dict[str, Any] | None = None
    ) -> AgentResult:
        """Route a task to the best agent based on capability."""
        agent = self.find_agent_by_capability(capability)
        if agent is None:
            return AgentResult(
                agent_id="",
                task_id=str(uuid.uuid4()),
                status=AgentStatus.FAILED,
                error=f"No agent found with capability '{capability}'",
            )
        return await self.execute_single(agent.agent_id, task, context)

    def get_history(self) -> list[AgentResult]:
        """Get execution history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear execution history."""
        self._history.clear()

    def get_success_rate(self) -> float:
        """Calculate the success rate of all executions."""
        if not self._history:
            return 0.0
        successes = sum(1 for r in self._history if r.success)
        return successes / len(self._history)
