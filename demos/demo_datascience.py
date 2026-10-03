#!/usr/bin/env python3
"""Demo: Data Science — statistical analysis and model simulation."""

import math
import random
import statistics
from datetime import datetime, timedelta


def generate_dataset(n: int, noise: float = 0.1) -> list:
    """Generate synthetic dataset with linear relationship + noise."""
    data = []
    for i in range(n):
        x = i / n
        y = 2.5 * x + 1.0 + random.gauss(0, noise)
        data.append((x, round(y, 4)))
    return data


def compute_stats(data: list) -> dict:
    """Compute descriptive statistics."""
    ys = [d[1] for d in data]
    return {
        "count": len(ys),
        "mean": round(statistics.mean(ys), 4),
        "median": round(statistics.median(ys), 4),
        "stdev": round(statistics.stdev(ys), 4) if len(ys) > 1 else 0,
        "min": round(min(ys), 4),
        "max": round(max(ys), 4),
    }


def simple_linear_regression(data: list) -> dict:
    """Fit y = slope * x + intercept using least squares."""
    n = len(data)
    xs = [d[0] for d in data]
    ys = [d[1] for d in data]
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in data)
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den else 0
    intercept = mean_y - slope * mean_x
    # R-squared
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in data)
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    return {
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r_squared": round(r2, 4),
    }


def run_demo():
    print("=" * 60)
    print("  DATA SCIENCE DEMO — Statistical Analysis & Modeling")
    print("=" * 60)

    # Generate datasets of varying sizes
    datasets = {
        "small": generate_dataset(50),
        "medium": generate_dataset(200),
        "large": generate_dataset(1000),
    }

    for name, data in datasets.items():
        stats = compute_stats(data)
        model = simple_linear_regression(data)
        print(f"\n  Dataset: {name} ({stats['count']} points)")
        print(f"    Mean={stats['mean']}  Median={stats['median']}  "
              f"Stdev={stats['stdev']}")
        print(f"    Range=[{stats['min']}, {stats['max']}]")
        print(
            f"    Model: y = {model['slope']}x + {model['intercept']}  "
            f"(R²={model['r_squared']})"
        )

    # Feature importance simulation
    print("\n" + "-" * 60)
    print("  FEATURE IMPORTANCE (simulated)")
    print("-" * 60)
    features = ["tenure", "usage_freq", "support_tickets", "plan_type",
                "region", "acquisition_channel"]
    importances = sorted(
        [(f, round(random.uniform(0.05, 0.95), 3)) for f in features],
        key=lambda x: -x[1],
    )
    for feat, imp in importances:
        bar = "█" * int(imp * 20)
        print(f"    {feat:20s} {bar} {imp:.3f}")

    # Model performance over time
    print("\n" + "-" * 60)
    print("  MODEL DRIFT MONITORING (simulated)")
    print("-" * 60)
    base_date = datetime.now() - timedelta(days=30)
    for day in range(0, 31, 5):
        date = base_date + timedelta(days=day)
        accuracy = 0.92 - day * 0.001 + random.gauss(0, 0.005)
        drift = "⚠ DRIFT" if accuracy < 0.88 else "✓ OK"
        print(
            f"    {date.strftime('%Y-%m-%d')}  "
            f"accuracy={accuracy:.4f}  {drift}"
        )

    print("\n" + "=" * 60)
    print("  Data Science demo complete.\n")


if __name__ == "__main__":
    run_demo()
