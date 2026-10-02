#!/usr/bin/env python3
"""Deep analytics demos: forecasting, anomaly detection, cohorts, funnels, reports."""
import random
import statistics
from collections import defaultdict
from datetime import datetime, timedelta

random.seed(42)


def time_series_forecasting():
    print("\n=== TIME SERIES FORECASTING ===")
    base = 100
    series = [base + i * 2 + random.gauss(0, 5) for i in range(30)]
    window = 7
    ma = [statistics.mean(series[i:i + window]) for i in range(len(series) - window + 1)]
    trend = (ma[-1] - ma[0]) / len(ma)
    forecast = [ma[-1] + trend * (i + 1) for i in range(7)]
    print(f"Last 7 actual: {[round(x, 1) for x in series[-7:]]}")
    print(f"7-day MA trend: {trend:.2f}/day")
    print(f"7-day forecast: {[round(x, 1) for x in forecast]}")


def anomaly_detection():
    print("\n=== ANOMALY DETECTION ===")
    data = [random.gauss(50, 5) for _ in range(100)]
    data[42] = 95
    data[77] = 5
    mean = statistics.mean(data)
    stdev = statistics.stdev(data)
    anomalies = [(i, round(v, 1)) for i, v in enumerate(data) if abs(v - mean) > 3 * stdev]
    print(f"Mean={mean:.1f}, StdDev={stdev:.1f}, threshold=±{3 * stdev:.1f}")
    print(f"Anomalies detected: {anomalies}")


def cohort_analysis():
    print("\n=== COHORT ANALYSIS ===")
    cohorts = defaultdict(list)
    for week in range(6):
        signups = random.randint(20, 50)
        for w in range(week, 6):
            retained = int(signups * (0.85 ** (w - week)) * random.uniform(0.9, 1.1))
            cohorts[f"W{week}"].append(retained)
    print("Cohort retention (signups per week):")
    for c, vals in cohorts.items():
        print(f"  {c}: {vals}")


def funnel_analysis():
    print("\n=== FUNNEL ANALYSIS ===")
    stages = ["Visit", "Signup", "Activate", "Subscribe", "Renew"]
    counts = [10000, 3500, 2100, 800, 640]
    for i, (stage, count) in enumerate(zip(stages, counts)):
        pct = count / counts[0] * 100
        step = f" ({count / counts[i - 1] * 100:.1f}%)" if i > 0 else ""
        print(f"  {stage:12s}: {count:6d}  {pct:5.1f}%{step}")


def report_builder():
    print("\n=== REPORT BUILDER ===")
    sections = {
        "Summary": "Revenue up 12% QoQ, churn down 2%.",
        "Top Products": "A ($45k), B ($32k), C ($28k).",
        "Risks": "Churn spike in segment X, supply delay in SKU-42.",
        "Next Steps": ["Launch retention campaign", "Diversify suppliers"],
    }
    for title, body in sections.items():
        print(f"\n## {title}")
        if isinstance(body, list):
            for item in body:
                print(f"  - {item}")
        else:
            print(f"  {body}")


if __name__ == "__main__":
    print("APEX-OS Deep Analytics Demos")
    time_series_forecasting()
    anomaly_detection()
    cohort_analysis()
    funnel_analysis()
    report_builder()
    print("\nAll demos complete.")
