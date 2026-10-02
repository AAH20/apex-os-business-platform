#!/usr/bin/env python3
"""APEX-OS Analytics Demo: forecast, anomalies, cohorts, funnel, report."""
import random
import statistics
from collections import defaultdict

random.seed(42)


def forecast():
    history = [100 + i * 3 + random.randint(-8, 8) for i in range(12)]
    n = len(history)
    slope = (n * sum(i * v for i, v in enumerate(history))
             - sum(range(n)) * sum(history)) / (n * sum(i * i for i in range(n)) - sum(range(n)) ** 2)
    intercept = (sum(history) - slope * sum(range(n))) / n
    future = [round(intercept + slope * (n + i), 1) for i in range(1, 4)]
    print("FORECAST")
    print("  history:", history)
    print("  next 3 periods:", future)
    print(f"  trend: {'up' if slope > 0 else 'down'} ({slope:+.2f}/period)\n")


def anomalies():
    data = [random.gauss(50, 5) for _ in range(40)] + [95, 5]
    mean, sd = statistics.mean(data), statistics.stdev(data)
    flagged = [(i, round(v, 1)) for i, v in enumerate(data) if abs(v - mean) > 2.5 * sd]
    print("ANOMALY DETECTION")
    print(f"  mean={mean:.1f} sd={sd:.1f} threshold=±{2.5 * sd:.1f}")
    print("  anomalies (index, value):", flagged, "\n")


def cohorts():
    cohorts = defaultdict(list)
    for c in range(6):
        size = random.randint(80, 120)
        for m in range(1, 5):
            cohorts[f"2026-{c + 1:02d}"].append(round(size * (0.92 ** m) / size * 100))
    print("COHORT RETENTION (%)")
    for name, rates in cohorts.items():
        print(f"  {name}: {' '.join(f'{r:5.1f}' for r in rates)}")
    print()


def funnel():
    stages = ["visit", "signup", "activate", "purchase", "retain"]
    counts = [10000]
    for _ in stages[1:]:
        counts.append(int(counts[-1] * random.uniform(0.35, 0.7)))
    print("FUNNEL")
    for s, c in zip(stages, counts):
        pct = c / counts[0] * 100
        print(f"  {s:10s} {c:6d}  {pct:5.1f}%  {'#' * int(pct / 2)}")
    print(f"  overall conversion: {counts[-1] / counts[0] * 100:.1f}%\n")


def report():
    revenue = round(sum(random.uniform(800, 1500) for _ in range(30)), 2)
    orders = random.randint(150, 300)
    aov = round(revenue / orders, 2)
    print("REPORT")
    print(f"  Period: 2026-09-01 to 2026-09-30")
    print(f"  Revenue: ${revenue:,.2f}")
    print(f"  Orders:  {orders}")
    print(f"  AOV:     ${aov}")
    print(f"  Status:  {'ON TRACK' if revenue > 20000 else 'BELOW TARGET'}\n")


if __name__ == "__main__":
    forecast()
    anomalies()
    cohorts()
    funnel()
    report()
