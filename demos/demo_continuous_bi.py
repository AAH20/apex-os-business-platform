#!/usr/bin/env python3
"""ContinuousBI Demo — Dashboards, reports, alerts, data freshness, performance metrics."""

import json
import random
import time
from datetime import datetime, timedelta

random.seed(42)


def banner(title):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def demo_dashboard_creation():
    banner("1. DASHBOARD CREATION DEMO")
    print("Creating executive KPI dashboard...")
    dashboard = {
        "name": "Executive Overview",
        "refresh_interval_sec": 30,
        "widgets": [
            {"type": "kpi", "title": "Daily Revenue", "value": "$128,450", "delta": "+12.3%"},
            {"type": "kpi", "title": "Active Users", "value": "8,234", "delta": "+5.1%"},
            {"type": "chart", "title": "Revenue Trend (30d)", "chart_type": "line"},
            {"type": "chart", "title": "Top Products", "chart_type": "bar"},
            {"type": "table", "title": "Recent Orders", "rows": 10},
        ],
    }
    print(f"  ✓ Dashboard: {dashboard['name']}")
    print(f"  ✓ Refresh interval: {dashboard['refresh_interval_sec']}s")
    for w in dashboard["widgets"]:
        print(f"    • [{w['type']}] {w['title']}")


def demo_report_generation():
    banner("2. REPORT GENERATION DEMO")
    print("Generating weekly business report...")
    report = {
        "title": "Weekly Business Report",
        "period": f"{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} → {datetime.now().strftime('%Y-%m-%d')}",
        "sections": [],
    }
    sections = [
        ("Executive Summary", "Revenue up 12% week-over-week driven by new product launch."),
        ("Sales Performance", "Top region: EMEA ($45K). Best seller: Enterprise Plan (340 units)."),
        ("Customer Metrics", "NPS: 72 (+3). Churn: 2.1% (-0.4pp). New signups: 1,240."),
        ("Operational", "Avg response time: 1.2s. Uptime: 99.97%. Support tickets: 89 (-15%)."),
    ]
    for heading, body in sections:
        report["sections"].append({"heading": heading, "body": body})
        print(f"  ✓ Section: {heading}")
    print(f"\n  📄 Report: {report['title']}")
    print(f"  📅 Period: {report['period']}")
    print(f"  📊 Sections: {len(report['sections'])}")


def demo_alert_rules():
    banner("3. ALERT RULES DEMO")
    print("Configuring alert rules...")
    rules = [
        {"name": "High Churn Rate", "condition": "churn_rate > 5%", "severity": "critical", "channel": "pagerduty"},
        {"name": "Revenue Drop", "condition": "daily_revenue < $80000", "severity": "warning", "channel": "slack"},
        {"name": "API Latency", "condition": "p99_latency > 500ms", "severity": "warning", "channel": "slack"},
        {"name": "Disk Usage", "condition": "disk_usage > 85%", "severity": "info", "channel": "email"},
    ]
    print(f"  {'Rule':<20}{'Condition':<28}{'Severity':<12}{'Channel'}")
    print(f"  {'-' * 70}")
    for r in rules:
        print(f"  {r['name']:<20}{r['condition']:<28}{r['severity']:<12}{r['channel']}")
    metrics = {"churn_rate": 6.2, "daily_revenue": 92000, "p99_latency": 320, "disk_usage": 88}
    print(f"\n  Evaluating against current metrics: {json.dumps(metrics)}")
    triggered = [r for r in rules if _evaluate(r["condition"], metrics)]
    for t in triggered:
        print(f"  🚨 TRIGGERED: {t['name']} → notify via {t['channel']}")


def _evaluate(condition, metrics):
    for key, val in metrics.items():
        if key in condition and ">" in condition:
            threshold = float(condition.split(">")[1].strip().rstrip("%"))
            if val > threshold:
                return True
    return False


def demo_data_freshness():
    banner("4. DATA FRESHNESS DEMO")
    print("Checking data pipeline freshness...")
    tables = [
        {"name": "orders", "last_update": datetime.now() - timedelta(minutes=2), "expected_lag_min": 5},
        {"name": "users", "last_update": datetime.now() - timedelta(minutes=15), "expected_lag_min": 30},
        {"name": "transactions", "last_update": datetime.now() - timedelta(hours=2), "expected_lag_min": 60},
        {"name": "inventory", "last_update": datetime.now() - timedelta(days=1), "expected_lag_min": 120},
    ]
    print(f"  {'Table':<16}{'Last Update':<24}{'Lag':<10}{'Expected':<10}{'Status'}")
    print(f"  {'-' * 70}")
    for t in tables:
        lag = datetime.now() - t["last_update"]
        lag_min = lag.total_seconds() / 60
        status = "✅ fresh" if lag_min <= t["expected_lag_min"] else "⚠️ stale"
        print(f"  {t['name']:<16}{t['last_update'].strftime('%Y-%m-%d %H:%M'):<24}"
              f"{lag_min:>6.0f}m{t['expected_lag_min']:>8}m   {status}")


def demo_performance_metrics():
    banner("5. PERFORMANCE METRICS DEMO")
    print("Collecting system performance metrics...")
    metrics = {
        "api": {
            "requests_per_sec": random.randint(800, 1200),
            "p50_latency_ms": random.randint(20, 50),
            "p99_latency_ms": random.randint(100, 300),
            "error_rate": round(random.uniform(0.001, 0.01), 4),
        },
        "database": {
            "active_connections": random.randint(10, 50),
            "query_time_p95_ms": random.randint(5, 20),
            "cache_hit_rate": round(random.uniform(0.85, 0.98), 4),
        },
        "queue": {
            "messages_pending": random.randint(0, 500),
            "consumers_active": random.randint(2, 8),
            "oldest_message_age_sec": random.randint(0, 30),
        },
    }
    for category, data in metrics.items():
        print(f"\n  📊 {category.upper()}")
        for key, val in data.items():
            unit = "ms" if "ms" in key else ("%" if "rate" in key else "")
            if unit == "%" and isinstance(val, float) and val < 1:
                val = f"{val:.2%}"
            elif unit:
                val = f"{val}{unit}"
            print(f"    {key:<28} {val}")


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         APEX-OS ContinuousBI Demo Suite                     ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    demo_dashboard_creation()
    demo_report_generation()
    demo_alert_rules()
    demo_data_freshness()
    demo_performance_metrics()
    print(f"\n{'─' * 60}")
    print("  All ContinuousBI demos completed successfully!")
    print(f"{'─' * 60}\n")
