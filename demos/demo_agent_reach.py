#!/usr/bin/env python3
"""AgentReach Demo — showcases agent creation, routing, load balancing, health, and metrics."""

import time
import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Agent:
    id: str
    name: str
    role: str
    status: str = "idle"
    load: int = 0
    messages_processed: int = 0
    avg_response_ms: float = 0.0
    health: str = "healthy"
    last_heartbeat: float = 0.0


@dataclass
class Message:
    id: str
    sender: str
    recipient: Optional[str]
    content: str
    priority: int = 1
    timestamp: float = 0.0


# ─── Demo 1: Agent Creation ──────────────────────────────────────────────────

def demo_agent_creation():
    print("=" * 60)
    print("DEMO 1: Agent Creation")
    print("=" * 60)

    agents: List[Agent] = []
    roles = ["router", "worker", "monitor", "analyzer", "executor"]

    for i, role in enumerate(roles):
        agent = Agent(
            id=str(uuid.uuid4())[:8],
            name=f"agent-{role}-{i}",
            role=role,
            last_heartbeat=time.time(),
        )
        agents.append(agent)
        print(f"  Created: {agent.name} (id={agent.id}, role={agent.role})")

    print(f"\n  Total agents created: {len(agents)}")
    print(f"  Roles: {[a.role for a in agents]}")
    print()


# ─── Demo 2: Message Routing ─────────────────────────────────────────────────

def demo_message_routing():
    print("=" * 60)
    print("DEMO 2: Message Routing")
    print("=" * 60)

    agents: Dict[str, Agent] = {
        "router": Agent(id="r1", name="router", role="router"),
        "worker": Agent(id="w1", name="worker", role="worker"),
        "monitor": Agent(id="m1", name="monitor", role="monitor"),
    }

    messages = [
        Message(id="msg-1", sender="user", recipient="router", content="Process this task", priority=2),
        Message(id="msg-2", sender="router", recipient="worker", content="Execute job #42", priority=1),
        Message(id="msg-3", sender="worker", recipient="monitor", content="Report status", priority=3),
        Message(id="msg-4", sender="monitor", recipient="router", content="Health check OK", priority=1),
    ]

    for msg in messages:
        recipient = agents.get(msg.recipient)
        if recipient:
            recipient.messages_processed += 1
            recipient.load += 1
            print(f"  Routed {msg.id}: {msg.sender} -> {recipient.name} | "
                  f"priority={msg.priority} | '{msg.content}'")
        else:
            print(f"  Dropped {msg.id}: no agent '{msg.recipient}'")

    print(f"\n  Routing table:")
    for name, agent in agents.items():
        print(f"    {name}: {agent.messages_processed} msgs, load={agent.load}")
    print()


# ─── Demo 3: Load Balancing ──────────────────────────────────────────────────

def demo_load_balancing():
    print("=" * 60)
    print("DEMO 3: Load Balancing")
    print("=" * 60)

    workers = [
        Agent(id=f"w{i}", name=f"worker-{i}", role="worker", load=random.randint(0, 10))
        for i in range(5)
    ]

    print("  Initial loads:")
    for w in workers:
        print(f"    {w.name}: load={w.load}")

    incoming_tasks = 20
    print(f"\n  Distributing {incoming_tasks} tasks (least-loaded strategy):")

    for task_id in range(incoming_tasks):
        least_loaded = min(workers, key=lambda w: w.load)
        least_loaded.load += 1
        if task_id < 5 or task_id >= incoming_tasks - 3:
            print(f"    Task-{task_id} -> {least_loaded.name} (load now {least_loaded.load})")
        elif task_id == 5:
            print("    ...")

    print(f"\n  Final loads:")
    for w in workers:
        bar = "█" * w.load + "░" * (25 - w.load)
        print(f"    {w.name}: [{bar}] load={w.load}")

    avg_load = sum(w.load for w in workers) / len(workers)
    print(f"\n  Average load: {avg_load:.1f}")
    print()


# ─── Demo 4: Health Monitoring ───────────────────────────────────────────────

def demo_health_monitoring():
    print("=" * 60)
    print("DEMO 4: Health Monitoring")
    print("=" * 60)

    agents = [
        Agent(id=f"a{i}", name=f"agent-{i}", role="worker",
              last_heartbeat=time.time() - random.uniform(0, 120))
        for i in range(6)
    ]

    now = time.time()
    print(f"  {'Agent':<12} {'Last HB (s)':<14} {'Status':<10} {'Health'}")
    print(f"  {'-'*12} {'-'*14} {'-'*10} {'-'*10}")

    for agent in agents:
        elapsed = now - agent.last_heartbeat
        if elapsed < 5:
            agent.health = "healthy"
        elif elapsed < 30:
            agent.health = "degraded"
        else:
            agent.health = "unhealthy"
        print(f"  {agent.name:<12} {elapsed:<14.1f} {agent.status:<10} {agent.health}")

    healthy = sum(1 for a in agents if a.health == "healthy")
    degraded = sum(1 for a in agents if a.health == "degraded")
    unhealthy = sum(1 for a in agents if a.health == "unhealthy")

    print(f"\n  Summary: {healthy} healthy, {degraded} degraded, {unhealthy} unhealthy")
    print()


# ─── Demo 5: Performance Metrics ─────────────────────────────────────────────

def demo_performance_metrics():
    print("=" * 60)
    print("DEMO 5: Performance Metrics")
    print("=" * 60)

    agents = [
        Agent(id=f"a{i}", name=f"agent-{i}", role="worker",
              messages_processed=random.randint(50, 500),
              avg_response_ms=random.uniform(5, 200))
        for i in range(5)
    ]

    print(f"  {'Agent':<12} {'Msgs':<8} {'Avg (ms)':<12} {'Throughput':<12}")
    print(f"  {'-'*12} {'-'*8} {'-'*12} {'-'*12}")

    total_msgs = 0
    for agent in agents:
        throughput = agent.messages_processed / max(agent.avg_response_ms, 1) * 1000
        total_msgs += agent.messages_processed
        print(f"  {agent.name:<12} {agent.messages_processed:<8} "
              f"{agent.avg_response_ms:<12.1f} {throughput:<12.1f} msg/s")

    avg_response = sum(a.avg_response_ms for a in agents) / len(agents)
    print(f"\n  Total messages processed: {total_msgs}")
    print(f"  Average response time: {avg_response:.1f} ms")
    print(f"  Fleet size: {len(agents)} agents")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 60)
    print("  APEX-OS AgentReach Demo Suite")
    print("█" * 60 + "\n")

    demo_agent_creation()
    demo_message_routing()
    demo_load_balancing()
    demo_health_monitoring()
    demo_performance_metrics()

    print("█" * 60)
    print("  All AgentReach demos completed successfully!")
    print("█" * 60 + "\n")


if __name__ == "__main__":
    main()
