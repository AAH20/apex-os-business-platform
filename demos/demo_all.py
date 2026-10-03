#!/usr/bin/env python3
"""
APEX-OS Business Platform — Comprehensive Demo Suite
Covers: Dashboard, Accounting, CRM, Analytics, AgentReach, BigData, DataScience, ContinuousBI
Run: python demos/demo_all.py [--module MODULE]
"""

import argparse
import json
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ── Helpers ──────────────────────────────────────────────────────────────────

def banner(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")

def sub(title: str) -> None:
    print(f"\n── {title} {'─' * (52 - len(title))}")

def ok(msg: str) -> None:
    print(f"  ✓ {msg}")

def info(msg: str) -> None:
    print(f"    {msg}")

def table(headers: list[str], rows: list[list]) -> None:
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    fmt = "  " + " │ ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  " + "─┼─".join("─" * w for w in widths))
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))

def simulate_work(label: str, steps: int = 3, delay: float = 0.1) -> None:
    for i in range(1, steps + 1):
        print(f"    [{i}/{steps}] {label}…")
        time.sleep(delay)

# ── 1. Dashboard Demo ────────────────────────────────────────────────────────

def demo_dashboard() -> None:
    banner("1. DASHBOARD DEMO")
    sub("KPI Cards")
    kpis = [
        ("Total Revenue", "$1,284,500", "+12.4%"),
        ("Active Users", "8,421", "+5.2%"),
        ("Conversion Rate", "3.42%", "+0.8%"),
        ("Avg Order Value", "$152.30", "-1.1%"),
        ("Churn Rate", "1.8%", "-0.3%"),
        ("NPS Score", "72", "+4"),
    ]
    table(["Metric", "Value", "Trend"], kpis)

    sub("Revenue by Channel")
    channels = [("Organic", 420000), ("Paid", 310000), ("Social", 280000),
                ("Email", 175000), ("Referral", 99500)]
    total = sum(v for _, v in channels)
    for name, val in channels:
        pct = val / total * 100
        bar = "█" * int(pct / 2)
        info(f"{name:<12} ${val:>10,}  {bar} {pct:.1f}%")

    sub("Recent Activity Feed")
    events = [
        "New enterprise client signed — Acme Corp ($48K ARR)",
        "Invoice #1042 paid — $12,300",
        "Churn risk alert: 3 accounts flagged",
        "Campaign 'Q4 Launch' hit 120% of target",
        "New team member: Sarah Chen (Sales)",
    ]
    for e in events:
        info(f"• {e}")
    ok("Dashboard rendered successfully")

# ── 2. Accounting Demo ───────────────────────────────────────────────────────

def demo_accounting() -> None:
    banner("2. ACCOUNTING DEMO")
    sub("Chart of Accounts")
    accounts = [
        ("1000", "Cash", "Asset", 245000),
        ("1100", "Accounts Receivable", "Asset", 189000),
        ("1200", "Inventory", "Asset", 67000),
        ("2000", "Accounts Payable", "Liability", 98000),
        ("2100", "Credit Card Payable", "Liability", 12500),
        ("3000", "Owner's Equity", "Equity", 300500),
        ("4000", "Revenue", "Income", 1284500),
        ("5000", "COGS", "Expense", -514000),
        ("6000", "Salaries", "Expense", -385000),
        ("6100", "Marketing", "Expense", -142000),
    ]
    table(["Code", "Account", "Type", "Balance"], accounts)

    sub("Trial Balance Check")
    assets = sum(b for _, n, t, b in accounts if t == "Asset")
    liab_eq = sum(b for _, n, t, b in accounts if t in ("Liability", "Equity"))
    income_exp = sum(b for _, n, t, b in accounts if t in ("Income", "Expense"))
    info(f"Total Assets:        ${assets:>12,}")
    info(f"Total Liab + Equity: ${liab_eq:>12,}")
    info(f"Net Income:          ${income_exp:>12,}")
    balanced = assets == liab_eq
    ok(f"Trial balance {'BALANCED' if balanced else 'OUT OF BALANCE'}")

    sub("Aging Report (AR)")
    aging = [("Current", 120000), ("1-30 days", 45000),
             ("31-60 days", 18000), ("61-90 days", 4500), (">90 days", 2000)]
    for bucket, amt in aging:
        info(f"{bucket:<12} ${amt:>10,}")
    ok("Accounting module demo complete")

# ── 3. CRM Demo ──────────────────────────────────────────────────────────────

def demo_crm() -> None:
    banner("3. CRM DEMO")
    sub("Sales Pipeline")
    stages = [
        ("Lead", 45, 0.10),
        ("Qualified", 28, 0.25),
        ("Proposal", 15, 0.50),
        ("Negotiation", 8, 0.75),
        ("Closed Won", 5, 1.00),
    ]
    table(["Stage", "Count", "Win %", "Weighted Value"],
          [[s, c, f"{w*100:.0f}%", f"${c * 50000 * w:,.0f}"] for s, c, w in stages])

    sub("Top Opportunities")
    opps = [
        ("Acme Corp", "Enterprise Plan", 48000, "Negotiation", "2026-10-15"),
        ("Globex Inc", "Team Plan", 24000, "Proposal", "2026-10-20"),
        ("Initech", "Starter Plan", 8000, "Qualified", "2026-11-01"),
        ("Umbrella Co", "Enterprise Plan", 65000, "Lead", "2026-11-10"),
        ("Stark Ind", "Team Plan", 18000, "Closed Won", "2026-09-28"),
    ]
    table(["Company", "Plan", "Value", "Stage", "Expected Close"], opps)

    sub("Contact Health Score")
    contacts = [("Alice Johnson", 92), ("Bob Smith", 78), ("Carol White", 45),
                ("Dan Brown", 88), ("Eve Davis", 61)]
    for name, score in contacts:
        bar = "▓" * (score // 10) + "░" * (10 - score // 10)
        info(f"{name:<16} [{bar}] {score}/100")
    ok("CRM pipeline demo complete")

# ── 4. Analytics Demo ────────────────────────────────────────────────────────

def demo_analytics() -> None:
    banner("4. ANALYTICS DEMO")
    sub("Cohort Retention Analysis")
    cohorts = ["2026-07", "2026-08", "2026-09"]
    months = ["M0", "M1", "M2", "M3"]
    retention = {
        "2026-07": [100, 78, 65, 58],
        "2026-08": [100, 82, 71, None],
        "2026-09": [100, 85, None, None],
    }
    table(["Cohort"] + months,
          [[c] + [f"{v}%" if v else "—" for v in retention[c]] for c in cohorts])

    sub("Funnel Analysis")
    funnel = [
        ("Visited Site", 50000, 100),
        ("Signed Up", 12000, 24),
        ("Activated", 6000, 12),
        ("Started Trial", 3000, 6),
        ("Converted to Paid", 1500, 3),
    ]
    table(["Step", "Users", "Conversion"],
          [[s, f"{u:,}", f"{c}%"] for s, u, c in funnel])

    sub("Statistical Summary")
    data = [random.gauss(100, 15) for _ in range(1000)]
    info(f"Count:    {len(data)}")
    info(f"Mean:     {statistics.mean(data):.2f}")
    info(f"Median:   {statistics.median(data):.2f}")
    info(f"Std Dev:  {statistics.stdev(data):.2f}")
    info(f"Min:      {min(data):.2f}")
    info(f"Max:      {max(data):.2f}")
    ok("Analytics demo complete")

# ── 5. AgentReach Demo ───────────────────────────────────────────────────────

def demo_agentreach() -> None:
    banner("5. AGENTREACH DEMO")
    sub("Agent Network Status")
    agents = [
        ("agent-east-1", "US East", "online", 12, 99.2),
        ("agent-west-1", "US West", "online", 8, 98.7),
        ("agent-eu-1", "Europe", "online", 15, 99.5),
        ("agent-ap-1", "Asia Pacific", "degraded", 3, 94.1),
        ("agent-sa-1", "South America", "offline", 0, 0.0),
    ]
    table(["Agent ID", "Region", "Status", "Active Tasks", "Uptime %"], agents)

    sub("Message Routing")
    messages = [
        ("msg-001", "campaign-blast", "agent-east-1", "delivered", 120),
        ("msg-002", "lead-followup", "agent-eu-1", "delivered", 45),
        ("msg-003", "churn-save", "agent-west-1", "delivered", 8),
        ("msg-004", "onboarding", "agent-ap-1", "queued", 0),
        ("msg-005", "renewal", "agent-east-1", "delivered", 22),
    ]
    table(["Msg ID", "Type", "Routed To", "Status", "Recipients"], messages)

    sub("Performance Metrics")
    metrics = {
        "Messages Processed (24h)": "14,320",
        "Avg Delivery Time": "1.2s",
        "Success Rate": "99.1%",
        "Retry Rate": "0.7%",
        "Dead Letter Queue": "3",
    }
    for k, v in metrics.items():
        info(f"{k:<30} {v}")
    ok("AgentReach demo complete")

# ── 6. BigData Demo ──────────────────────────────────────────────────────────

def demo_bigdata() -> None:
    banner("6. BIGDATA DEMO")
    sub("Data Pipeline Stages")
    stages = [
        ("Ingest", "Kafka", "2.4M events/min", "healthy"),
        ("Validate", "Schema Registry", "99.8% pass", "healthy"),
        ("Transform", "Spark", "1.8M records/min", "healthy"),
        ("Enrich", "Flink", "1.2M records/min", "healthy"),
        ("Load", "S3 + Redshift", "840K rows/min", "healthy"),
    ]
    table(["Stage", "Engine", "Throughput", "Status"], stages)

    sub("Data Lake Storage")
    datasets = [
        ("events", "Parquet", "2.4 TB", "14.2B rows"),
        ("transactions", "Parquet", "890 GB", "3.1B rows"),
        ("user_profiles", "Delta Lake", "120 GB", "45M rows"),
        ("logs", "JSON", "5.1 TB", "89B rows"),
        ("ml_features", "Parquet", "340 GB", "1.2B rows"),
    ]
    table(["Dataset", "Format", "Size", "Rows"], datasets)

    sub("Sample Aggregation Query")
    simulate_work("Scanning events partition", steps=3, delay=0.05)
    simulate_work("Computing daily aggregates", steps=2, delay=0.05)
    result = {
        "date": "2026-10-02",
        "total_events": 2_412_890,
        "unique_users": 842_100,
        "top_page": "/pricing",
        "top_page_views": 142_300,
        "avg_session_duration_sec": 245,
    }
    for k, v in result.items():
        info(f"{k:<30} {v:,}" if isinstance(v, int) else f"{k:<30} {v}")
    ok("BigData demo complete")

# ── 7. DataScience Demo ──────────────────────────────────────────────────────

def demo_datascience() -> None:
    banner("7. DATASCIENCE DEMO")
    sub("Model Registry")
    models = [
        ("churn-predictor", "XGBoost", "v3.2", "production", 0.87),
        ("revenue-forecast", "Prophet", "v2.1", "production", 0.92),
        ("lead-scorer", "LightGBM", "v4.0", "staging", 0.84),
        ("anomaly-detector", "IsolationForest", "v1.5", "production", 0.91),
        ("recommender", "Two-Tower NN", "v2.8", "development", 0.78),
    ]
    table(["Model", "Algorithm", "Version", "Stage", "AUC / R²"], models)

    sub("Feature Importance (churn-predictor)")
    features = [
        ("days_since_login", 0.28),
        ("support_tickets_30d", 0.22),
        ("plan_tier", 0.18),
        ("monthly_spend", 0.15),
        ("team_size", 0.10),
        ("nps_score", 0.07),
    ]
    for name, importance in features:
        bar = "█" * int(importance * 40)
        info(f"{name:<24} {bar} {importance:.2f}")

    sub("A/B Test Results")
    ab = [
        ("Control (A)", 5000, 3.2, 0.32),
        ("Variant (B)", 5000, 3.8, 0.38),
    ]
    table(["Group", "Sample Size", "Conversion %", "Revenue/User"],
          [[g, f"{n:,}", f"{c}%", f"${r}"] for g, n, c, r in ab])
    lift = (0.38 - 0.32) / 0.32 * 100
    info(f"Relative lift: +{lift:.1f}%")
    info("Statistical significance: p < 0.01 ✓")
    ok("DataScience demo complete")

# ── 8. ContinuousBI Demo ────────────────────────────────────────────────────

def demo_continuousbi() -> None:
    banner("8. CONTINUOUS BI DEMO")
    sub("Real-Time Metrics")
    metrics = [
        ("Revenue Today", "$48,230", "+8.2% vs yesterday"),
        ("Orders Today", 312, "+5.1% vs yesterday"),
        ("Avg Order Value", "$154.60", "+2.9% vs yesterday"),
        ("Cart Abandonment", "68.5%", "-1.2% vs yesterday"),
        ("Top Product", "Enterprise Plan", "42 orders"),
    ]
    table(["Metric", "Value", "Comparison"], metrics)

    sub("Live Dashboard Widgets")
    widgets = [
        ("revenue-ticker", "streaming", "1s refresh"),
        ("geo-heatmap", "streaming", "5s refresh"),
        ("top-products", "micro-batch", "30s refresh"),
        ("funnel-realtime", "streaming", "2s refresh"),
        ("alert-feed", "event-driven", "instant"),
    ]
    table(["Widget", "Mode", "Refresh"], widgets)

    sub("Automated Insights")
    insights = [
        "⚡ Revenue spike detected: +23% in EU region (14:00-15:00)",
        "⚠️  Inventory alert: 'Team Plan' SKU below safety stock",
        "📈 Trend: Mobile conversions up 15% week-over-week",
        "🔔 SLA warning: Support response time exceeding 5min target",
    ]
    for insight in insights:
        info(insight)

    sub("Data Freshness")
    sources = [
        ("PostgreSQL CDC", "2s delay", "healthy"),
        ("Stripe Webhooks", "1s delay", "healthy"),
        ("Salesforce API", "15min delay", "healthy"),
        ("Google Analytics", "1hr delay", "healthy"),
    ]
    table(["Source", "Lag", "Status"], sources)
    ok("ContinuousBI demo complete")

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
    parser = argparse.ArgumentParser(description="APEX-OS Business Platform Demo Suite")
    parser.add_argument("--module", "-m", choices=list(DEMOS), help="Run a single module demo")
    parser.add_argument("--list", "-l", action="store_true", help="List available demos")
    args = parser.parse_args()

    if args.list:
        print("Available demos:")
        for name, fn in DEMOS.items():
            print(f"  {name:<16} — {fn.__doc__ or name}")
        return

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        APEX-OS BUSINESS PLATFORM — DEMO SUITE              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python:  {sys.version.split()[0]}")

    if args.module:
        DEMOS[args.module]()
    else:
        for name, fn in DEMOS.items():
            fn()

    print(f"\n{'=' * 60}")
    print(f"  All demos completed at {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 60}\n")

if __name__ == "__main__":
    main()
