#!/usr/bin/env python3
"""Demo: Continuous BI — real-time dashboards and KPI monitoring."""

import random
import time
from datetime import datetime, timedelta

KPIS = [
    "revenue", "active_users", "conversion_rate",
    "churn_rate", "nps_score", "avg_order_value",
]
THRESHOLDS = {
    "revenue": (50000, 100000),
    "active_users": (1000, 5000),
    "conversion_rate": (0.02, 0.05),
    "churn_rate": (0.01, 0.03),
    "nps_score": (30, 60),
    "avg_order_value": (50, 150),
}


def read_kpi(name: str) -> float:
    """Simulate reading a KPI value."""
    low, high = THRESHOLDS[name]
    return round(random.uniform(low * 0.7, high * 1.3), 2)


def evaluate_kpi(name: str, value: float) -> str:
    """Evaluate KPI against thresholds."""
    low, high = THRESHOLDS[name]
    if value < low:
        return "🔴 BELOW"
    if value > high:
        return "🟢 ABOVE"
    return "🟡 WITHIN"


def format_value(name: str, value: float) -> str:
    """Format KPI value for display."""
    if name in ("conversion_rate", "churn_rate"):
        return f"{value * 100:.2f}%"
    if name in ("revenue", "avg_order_value"):
        return f"${value:,.2f}"
    if name == "nps_score":
        return f"{value:.1f}"
    return f"{value:,.0f}"


def run_demo():
    print("=" * 60)
    print("  CONTINUOUS BI DEMO — Real-Time KPI Monitoring")
    print("=" * 60)

    # Simulate 3 refresh cycles
    for cycle in range(1, 4):
        print(f"\n  ── Refresh Cycle {cycle} "
              f"({datetime.now().strftime('%H:%M:%S')}) ──")
        alerts = []
        for kpi in KPIS:
            value = read_kpi(kpi)
            status = evaluate_kpi(kpi, value)
            formatted = format_value(kpi, value)
            print(f"    {status}  {kpi:20s} : {formatted}")
            if "BELOW" in status or "ABOVE" in status:
                alerts.append((kpi, status, formatted))
        if alerts:
            print(f"\n    ⚠ {len(alerts)} alert(s) triggered:")
            for kpi, status, val in alerts:
                print(f"      • {kpi}: {status} ({val})")
        else:
            print("\n    ✓ All KPIs within normal range")
        if cycle < 3:
            time.sleep(0.1)

    # Trend summary
    print("\n" + "-" * 60)
    print("  7-DAY TREND SUMMARY (simulated)")
    print("-" * 60)
    base_date = datetime.now() - timedelta(days=7)
    for kpi in KPIS:
        trend = random.choice(["↑ increasing", "↓ decreasing",
                               "→ stable", "↔ volatile"])
        change = round(random.uniform(-15, 15), 1)
        sign = "+" if change >= 0 else ""
        print(
            f"    {kpi:20s}  {trend:15s}  {sign}{change}%"
        )

    # Anomaly detection
    print("\n" + "-" * 60)
    print("  ANOMALY DETECTION (simulated)")
    print("-" * 60)
    anomalies = random.randint(0, 3)
    if anomalies == 0:
        print("    ✓ No anomalies detected in the last 24h")
    else:
        for _ in range(anomalies):
            kpi = random.choice(KPIS)
            severity = random.choice(["low", "medium", "high"])
            print(
                f"    ⚠ Anomaly in '{kpi}' "
                f"(severity: {severity})"
            )

    print("\n" + "=" * 60)
    print("  Continuous BI demo complete.\n")


if __name__ == "__main__":
    run_demo()
