#!/usr/bin/env python3
"""Analytics Demo: Cohort analysis, funnel, forecasting, anomaly detection, correlation."""

import random
import math
import datetime
from typing import List, Dict, Tuple

random.seed(42)


# ─── Demo 1: Cohort Analysis ────────────────────────────────────────────────

def demo_cohort_analysis():
    print("=" * 60)
    print("DEMO 1: Cohort Analysis")
    print("=" * 60)
    cohorts = {
        "2024-Q1": [100, 85, 72, 65, 60],
        "2024-Q2": [120, 95, 80, 70],
        "2024-Q3": [90, 78, 68],
        "2024-Q4": [110, 88],
    }
    months = ["M0", "M1", "M2", "M3", "M4"]
    print(f"  {'Cohort':10s} | {' | '.join(months)}")
    print(f"  {'-'*10}-+-{'-'*35}")
    for cohort, retention in cohorts.items():
        vals = [f"{r}%" for r in retention]
        print(f"  {cohort:10s} | {' | '.join(vals)}")
    m1_avg = sum(r[1] for r in cohorts.values() if len(r) > 1) / sum(1 for r in cohorts.values() if len(r) > 1)
    print(f"  Avg M1 retention: {m1_avg:.1f}%\n")
    return cohorts


# ─── Demo 2: Funnel Analysis ────────────────────────────────────────────────

def demo_funnel_analysis():
    print("=" * 60)
    print("DEMO 2: Funnel Analysis")
    print("=" * 60)
    stages = [
        ("Visited", 10000),
        ("Signed Up", 3500),
        ("Activated", 2100),
        ("Subscribed", 840),
        ("Retained (M1)", 588),
    ]
    prev = None
    for stage, count in stages:
        if prev:
            conv = count / prev * 100
            print(f"  {stage:16s}: {count:6d}  (conversion: {conv:.1f}%)")
        else:
            print(f"  {stage:16s}: {count:6d}")
        prev = count
    overall = stages[-1][1] / stages[0][1] * 100
    print(f"  Overall conversion: {overall:.1f}%\n")
    return stages


# ─── Demo 3: Forecasting ─────────────────────────────────────────────────────

def demo_forecasting():
    print("=" * 60)
    print("DEMO 3: Forecasting")
    print("=" * 60)
    revenue = [120, 135, 148, 160, 175, 190, 205, 220, 238, 255, 270, 290]
    n = len(revenue)
    x_mean = (n - 1) / 2
    y_mean = sum(revenue) / n
    num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(revenue))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den
    intercept = y_mean - slope * x_mean
    print(f"  Historical (last 12 months): {revenue}")
    print(f"  Trend: slope={slope:.2f}/month, intercept={intercept:.2f}")
    forecasts = []
    for m in range(1, 4):
        pred = intercept + slope * (n - 1 + m)
        forecasts.append(round(pred, 1))
        print(f"  Forecast M+{m}: ${pred:.1f}k")
    print(f"  Next quarter projection: ${sum(forecasts):.1f}k\n")
    return forecasts


# ─── Demo 4: Anomaly Detection ──────────────────────────────────────────────

def demo_anomaly_detection():
    print("=" * 60)
    print("DEMO 4: Anomaly Detection")
    print("=" * 60)
    data = [100, 102, 98, 105, 103, 101, 99, 104, 102, 100, 250, 103, 98, 101, 97, 102]
    mean = sum(data) / len(data)
    variance = sum((x - mean) ** 2 for x in data) / len(data)
    std = math.sqrt(variance)
    threshold = 2.5 * std
    print(f"  Data points: {len(data)}")
    print(f"  Mean: {mean:.2f}, Std: {std:.2f}, Threshold (±2.5σ): {threshold:.2f}")
    anomalies = []
    for i, val in enumerate(data):
        if abs(val - mean) > threshold:
            anomalies.append((i, val))
            print(f"  ⚠ ANOMALY at index {i}: value={val} (deviation: {val - mean:+.2f})")
    if not anomalies:
        print("  No anomalies detected.")
    print(f"  Anomalies found: {len(anomalies)}\n")
    return anomalies


# ─── Demo 5: Correlation ────────────────────────────────────────────────────

def demo_correlation():
    print("=" * 60)
    print("DEMO 5: Correlation Analysis")
    print("=" * 60)
    spend = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
    revenue = [105, 120, 140, 155, 170, 185, 200, 215, 230, 245]
    n = len(spend)
    x_mean = sum(spend) / n
    y_mean = sum(revenue) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(spend, revenue))
    den_x = math.sqrt(sum((x - x_mean) ** 2 for x in spend))
    den_y = math.sqrt(sum((y - y_mean) ** 2 for y in revenue))
    r = num / (den_x * den_y)
    print(f"  Marketing Spend vs Revenue")
    print(f"  Pearson r = {r:.4f}")
    if r > 0.7:
        strength = "Strong positive"
    elif r > 0.3:
        strength = "Moderate positive"
    elif r > -0.3:
        strength = "Weak/No"
    elif r > -0.7:
        strength = "Moderate negative"
    else:
        strength = "Strong negative"
    print(f"  Interpretation: {strength} correlation")
    print(f"  {'Spend':>8s} | {'Revenue':>8s}")
    for x, y in zip(spend, revenue):
        print(f"  {x:8.1f} | {y:8.1f}")
    print()
    return r


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 60)
    print("  APEX-OS Analytics Demo Suite")
    print("█" * 60 + "\n")
    demo_cohort_analysis()
    demo_funnel_analysis()
    demo_forecasting()
    demo_anomaly_detection()
    demo_correlation()
    print("=" * 60)
    print("Analytics Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
