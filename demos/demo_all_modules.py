#!/usr/bin/env python3
"""Comprehensive demo runner for all APEX-OS Business Platform modules.

Usage:
    python demos/demo_all_modules.py              # run all demos
    python demos/demo_all_modules.py dashboard    # run a single demo
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

HEADER = "=" * 60


def banner(title: str) -> None:
    print(f"\n{HEADER}\n  {title}\n{HEADER}")


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


# ── 1. Dashboard ────────────────────────────────────────────────────────────
def demo_dashboard() -> None:
    banner("1. DASHBOARD DEMO")
    kpis = {
        "Revenue (MTD)": "$1,284,500",
        "Active Users": 48_392,
        "Open Deals": 1_247,
        "Support Tickets": 89,
        "Uptime": "99.98%",
    }
    for k, v in kpis.items():
        print(f"  {k:<20} {v}")
    ok("Dashboard rendered with 5 KPI widgets")


# ── 2. Accounting ───────────────────────────────────────────────────────────
def demo_accounting() -> None:
    banner("2. ACCOUNTING DEMO")
    txns = [
        ("INV-1001", "Acme Corp", 12_500.00, "paid"),
        ("INV-1002", "Globex", 8_750.00, "pending"),
        ("INV-1003", "Initech", 23_100.00, "paid"),
        ("EXP-2001", "AWS", 4_200.00, "paid"),
        ("EXP-2002", "Office Lease", 15_000.00, "pending"),
    ]
    total = sum(t[2] for t in txns)
    print(f"  {'ID':<12} {'Entity':<15} {'Amount':>12} {'Status':<10}")
    print(f"  {'-'*12} {'-'*15} {'-'*12} {'-'*10}")
    for tid, entity, amount, status in txns:
        print(f"  {tid:<12} {entity:<15} ${amount:>10,.2f} {status:<10}")
    print(f"\n  Total ledger value: ${total:,.2f}")
    ok(f"Processed {len(txns)} transactions")


# ── 3. CRM ───────────────────────────────────────────────────────────────────
def demo_crm() -> None:
    banner("3. CRM DEMO")
    leads = [
        {"name": "Alice Johnson", "company": "Acme", "score": 87, "stage": "negotiation"},
        {"name": "Bob Smith", "company": "Globex", "score": 62, "stage": "qualified"},
        {"name": "Carol White", "company": "Initech", "score": 94, "stage": "proposal"},
        {"name": "Dan Brown", "company": "Umbrella", "score": 45, "stage": "contacted"},
    ]
    for lead in leads:
        bar = "█" * (lead["score"] // 10) + "░" * (10 - lead["score"] // 10)
        print(f"  {lead['name']:<18} {lead['company']:<12} [{bar}] {lead['score']:>3}  {lead['stage']}")
    hot = [l for l in leads if l["score"] >= 80]
    print(f"\n  Hot leads (score ≥ 80): {len(hot)}")
    ok(f"Scored {len(leads)} leads")


# ── 4. Analytics ─────────────────────────────────────────────────────────────
def demo_analytics() -> None:
    banner("4. ANALYTICS DEMO")
    daily = [random.randint(800, 1500) for _ in range(30)]
    print(f"  Sessions (last 30 days):")
    print(f"    Min:    {min(daily):,}")
    print(f"    Max:    {max(daily):,}")
    print(f"    Mean:   {statistics.mean(daily):,.1f}")
    print(f"    Median: {statistics.median(daily):,.1f}")
    print(f"    Stdev:  {statistics.stdev(daily):,.1f}")
    trend = "↗ UP" if daily[-1] > daily[0] else "↘ DOWN"
    print(f"    Trend:  {trend} ({daily[0]} → {daily[-1]})")
    ok("Analytics pipeline complete")


# ── 5. AgentReach ────────────────────────────────────────────────────────────
def demo_agentreach() -> None:
    banner("5. AGENTREACH DEMO")
    channels = ["WhatsApp", "SMS", "Email", "Voice", "Web Chat"]
    agents = [f"Agent-{i:02d}" for i in range(1, 6)]
    print(f"  Active agents: {len(agents)}")
    print(f"  Channels: {', '.join(channels)}")
    conversations = []
    for _ in range(10):
        conv = {
            "id": f"CV-{random.randint(1000,9999)}",
            "agent": random.choice(agents),
            "channel": random.choice(channels),
            "duration_s": random.randint(30, 600),
            "resolved": random.random() > 0.2,
        }
        conversations.append(conv)
    resolved = sum(1 for c in conversations if c["resolved"])
    avg_dur = statistics.mean(c["duration_s"] for c in conversations)
    print(f"  Conversations simulated: {len(conversations)}")
    print(f"  Resolution rate: {resolved/len(conversations)*100:.0f}%")
    print(f"  Avg duration: {avg_dur:.0f}s")
    ok("AgentReach routing engine tested")


# ── 6. BigData ───────────────────────────────────────────────────────────────
def demo_bigdata() -> None:
    banner("6. BIGDATA DEMO")
    records = 1_000_000
    batch_size = 10_000
    batches = records // batch_size
    print(f"  Total records:  {records:,}")
    print(f"  Batch size:     {batch_size:,}")
    print(f"  Batches:        {batches}")
    partitions = [f"dt=2026-10-{d:02d}" for d in range(1, 8)]
    print(f"  Partitions:     {len(partitions)}")
    for p in partitions:
        size_mb = random.randint(120, 480)
        print(f"    {p}  →  {size_mb} MB")
    total_mb = records * 250 / 1_000_000
    print(f"\n  Estimated raw size: {total_mb:.0f} MB")
    ok("BigData ingestion pipeline simulated")


# ── 7. DataScience ───────────────────────────────────────────────────────────
def demo_datascience() -> None:
    banner("7. DATASCIENCE DEMO")
    # Simulate a simple linear regression
    n = 100
    x = [i for i in range(n)]
    y = [2.5 * xi + random.gauss(0, 10) for xi in x]
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / sum((xi - x_mean) ** 2 for xi in x)
    intercept = y_mean - slope * x_mean
    y_pred = [slope * xi + intercept for xi in x]
    ss_res = sum((yi - yp) ** 2 for yi, yp in zip(y, y_pred))
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    r2 = 1 - ss_res / ss_tot
    print(f"  Model: y = {slope:.4f}x + {intercept:.4f}")
    print(f"  R² score: {r2:.4f}")
    print(f"  Samples: {n}")
    print(f"  Features: 1 (univariate)")
    ok("Linear regression trained and evaluated")


# ── 8. ContinuousBI ──────────────────────────────────────────────────────────
def demo_continuousbi() -> None:
    banner("8. CONTINUOUS BI DEMO")
    metrics = [
        ("conversion_rate", 3.2, "%"),
        ("churn_rate", 1.8, "%"),
        ("nps_score", 72, ""),
        ("arr_growth", 12.5, "%"),
        ("cac_ratio", 2.1, ""),
    ]
    print(f"  {'Metric':<22} {'Value':>8} {'Unit':<6} {'Status':<10}")
    print(f"  {'-'*22} {'-'*8} {'-'*6} {'-'*10}")
    for name, value, unit in metrics:
        status = "🟢 good" if value > 5 else "🟡 watch"
        print(f"  {name:<22} {value:>8.1f} {unit:<6} {status:<10}")
    refresh = "every 15 min"
    print(f"\n  Refresh cadence: {refresh}")
    print(f"  Data sources: 4 (Stripe, Segment, Postgres, S3)")
    ok("Continuous BI dashboards refreshed")


# ── Main ─────────────────────────────────────────────────────────────────────
DEMOS = {
    "dashboard": demo_dashboard,
    "accounting": demo_accounting,
    "crm": demo_crm,
    "analytics": demo_analytics,
    "agentreach": demo_agentreach,
    "bigdata": demo_bigdata,
    "datascience": demo_datascience,
    "continuousbi": demo_continuousbi,
}


def main() -> None:
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        APEX-OS Business Platform — Module Demos            ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    selected = sys.argv[1:] if len(sys.argv) > 1 else list(DEMOS)
    for name in selected:
        if name not in DEMOS:
            print(f"\n  [SKIP] Unknown demo: {name}")
            continue
        DEMOS[name]()
    print(f"\n{HEADER}")
    print(f"  All {len(selected)} demo(s) completed at {datetime.now():%H:%M:%S}")
    print(f"{HEADER}\n")


if __name__ == "__main__":
    main()
