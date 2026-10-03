#!/usr/bin/env python3
"""APEX-OS Dashboard Demo — showcases metrics, charts, activity, actions, health."""

import random
import time
from datetime import datetime, timedelta

random.seed(42)


def header(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def section(title):
    print(f"\n--- {title} ---")


# ── 1. Dashboard Metrics ──────────────────────────────────────────────
def demo_metrics():
    header("1. DASHBOARD METRICS")
    metrics = {
        "Total Revenue": ("$1,284,500", "+12.4%", "up"),
        "Active Users": ("8,421", "+5.2%", "up"),
        "Pending Orders": ("342", "-3.1%", "down"),
        "System Uptime": ("99.97%", "+0.02%", "up"),
        "Avg Response Time": ("142ms", "-8ms", "up"),
        "Error Rate": ("0.12%", "-0.03%", "up"),
    }
    for name, (value, change, trend) in metrics.items():
        arrow = "▲" if trend == "up" else "▼"
        print(f"  {name:<22} {value:>12}  {arrow} {change}")
    print(f"\n  Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ── 2. Chart Rendering ───────────────────────────────────────────────
def demo_charts():
    header("2. CHART RENDERING")
    section("Revenue Trend (last 14 days)")
    base = 35000
    for i in range(14):
        day = datetime.now() - timedelta(days=13 - i)
        val = base + random.randint(-5000, 8000)
        bar = "█" * int(val / 2000)
        print(f"  {day.strftime('%m-%d')}  ${val:>7,}  {bar}")

    section("Department Distribution")
    depts = [("Engineering", 38), ("Sales", 24), ("Marketing", 16),
             ("Support", 12), ("HR", 6), ("Finance", 4)]
    for name, pct in depts:
        bar = "▓" * (pct // 2)
        print(f"  {name:<14} {pct:>3}%  {bar}")

    section("Monthly Recurring Revenue")
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    mrr = [82, 89, 95, 103, 112, 121]
    for m, v in zip(months, mrr):
        bar = "░" * (v // 5)
        print(f"  {m}  ${v}K  {bar}")


# ── 3. Activity Feed ─────────────────────────────────────────────────
def demo_activity():
    header("3. ACTIVITY FEED")
    activities = [
        ("09:42", "user", "Sarah Chen created invoice #INV-2041 for $4,200"),
        ("09:38", "system", "Nightly backup completed successfully (2.3 GB)"),
        ("09:15", "user", "Marcus Webb approved purchase order #PO-882"),
        ("08:57", "alert", "CPU usage exceeded 85% on node prod-03"),
        ("08:30", "user", "Aisha Patel updated Q4 budget allocation"),
        ("08:12", "system", "SSL certificate renewed for api.apex-os.io"),
        ("07:55", "user", "David Kim closed ticket #TKT-1042"),
        ("07:30", "alert", "Unusual login detected from IP 203.0.113.42"),
        ("07:00", "system", "Scheduled maintenance window started"),
        ("06:45", "user", "Elena Rodriguez added 3 new team members"),
    ]
    for ts, kind, msg in activities:
        icon = {"user": "👤", "system": "⚙", "alert": "⚠"}.get(kind, "•")
        print(f"  [{ts}] {icon} {msg}")
    print(f"\n  Showing 10 of 1,247 activities")


# ── 4. Quick Actions ─────────────────────────────────────────────────
def demo_quick_actions():
    header("4. QUICK ACTIONS")
    actions = [
        ("Create Invoice", "Generate a new invoice for a client"),
        ("Add Expense", "Log a business expense with receipt"),
        ("Run Report", "Generate a financial or operational report"),
        ("Invite User", "Send an invitation to a new team member"),
        ("Export Data", "Download data in CSV or PDF format"),
        ("Schedule Meeting", "Book a meeting and send calendar invites"),
    ]
    for i, (name, desc) in enumerate(actions, 1):
        print(f"  [{i}] {name:<18} — {desc}")
    print("\n  Simulating action selection...")
    time.sleep(0.3)
    selected = random.randint(1, len(actions))
    name = actions[selected - 1][0]
    print(f"  ✓ Action '{name}' executed successfully")
    print(f"  ✓ Confirmation notification sent to admin")


# ── 5. System Health ─────────────────────────────────────────────────
def demo_health():
    header("5. SYSTEM HEALTH")
    services = [
        ("API Gateway", "healthy", 99.99, "12ms"),
        ("Auth Service", "healthy", 99.95, "8ms"),
        ("Database (Primary)", "healthy", 99.99, "3ms"),
        ("Database (Replica)", "healthy", 99.97, "5ms"),
        ("Cache Layer", "degraded", 98.12, "45ms"),
        ("Queue Worker", "healthy", 99.88, "22ms"),
        ("Storage Service", "healthy", 99.99, "18ms"),
        ("Notification Service", "healthy", 99.91, "35ms"),
    ]
    print(f"  {'Service':<26} {'Status':<12} {'Uptime':>8} {'Latency':>8}")
    print(f"  {'-' * 56}")
    for svc, status, uptime, latency in services:
        icon = "🟢" if status == "healthy" else "🟡"
        print(f"  {icon} {svc:<24} {status:<12} {uptime:>7.2f}% {latency:>8}")

    section("Resource Usage")
    resources = [("CPU", 42, 100), ("Memory", 67, 100),
                 ("Disk", 54, 100), ("Network I/O", 23, 100)]
    for name, used, total in resources:
        pct = int(used / total * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  {name:<14} [{bar}] {pct}%")

    section("Recent Alerts")
    alerts = [
        ("2h ago", "WARNING", "Cache hit rate dropped below 80%"),
        ("5h ago", "INFO", "Auto-scaling added 1 new instance"),
        ("1d ago", "INFO", "Database vacuum completed"),
    ]
    for ts, level, msg in alerts:
        print(f"  [{ts:>6}] {level:<8} {msg}")
    print(f"\n  Overall Status: OPERATIONAL ✓")


# ── Main ─────────────────────────────────────────────────────────────
def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║        APEX-OS Business Platform — Dashboard Demo       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    demo_metrics()
    demo_charts()
    demo_activity()
    demo_quick_actions()
    demo_health()
    print(f"\n{'=' * 60}")
    print("  Dashboard demo complete.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
