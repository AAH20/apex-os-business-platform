#!/usr/bin/env python3
"""Demo: Agent Reach — multi-channel agent dispatch and monitoring."""

import json
import random
import time
from datetime import datetime, timedelta

CHANNELS = ["email", "slack", "sms", "webhook", "api"]
AGENTS = ["support-bot", "sales-assist", "ops-monitor", "data-fetch"]


def simulate_dispatch(agent: str, channel: str) -> dict:
    """Simulate dispatching an agent to a channel."""
    latency = round(random.uniform(0.1, 2.5), 2)
    success = random.random() > 0.1
    return {
        "agent": agent,
        "channel": channel,
        "latency_s": latency,
        "status": "delivered" if success else "failed",
        "timestamp": datetime.now().isoformat(),
    }


def run_demo():
    print("=" * 60)
    print("  AGENT REACH DEMO — Multi-Channel Agent Dispatch")
    print("=" * 60)

    results = []
    for agent in AGENTS:
        channel = random.choice(CHANNELS)
        result = simulate_dispatch(agent, channel)
        results.append(result)
        status_icon = "✓" if result["status"] == "delivered" else "✗"
        print(
            f"  {status_icon} {agent:15s} → {channel:10s} "
            f"({result['latency_s']}s) [{result['status']}]"
        )
        time.sleep(0.05)

    delivered = sum(1 for r in results if r["status"] == "delivered")
    avg_latency = sum(r["latency_s"] for r in results) / len(results)

    print("-" * 60)
    print(f"  Total dispatches : {len(results)}")
    print(f"  Delivered        : {delivered}")
    print(f"  Failed           : {len(results) - delivered}")
    print(f"  Avg latency      : {avg_latency:.2f}s")
    print(f"  Success rate     : {delivered / len(results) * 100:.1f}%")
    print("=" * 60)

    # Channel breakdown
    print("\n  Channel Breakdown:")
    for ch in CHANNELS:
        ch_results = [r for r in results if r["channel"] == ch]
        if ch_results:
            ch_ok = sum(1 for r in ch_results if r["status"] == "delivered")
            print(f"    {ch:10s}: {ch_ok}/{len(ch_results)} delivered")

    print("\n  Agent Reach demo complete.\n")


if __name__ == "__main__":
    run_demo()
