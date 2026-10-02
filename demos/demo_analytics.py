#!/usr/bin/env python3
"""
APEX-OS Business Platform — Analytics Demo
===========================================
Demonstrates a BI dashboard with sample data.

Shows:
  • KPI cards (revenue, orders, customers, growth)
  • Time-series revenue chart (ASCII)
  • Sales by category breakdown
  • Top customers table
  • Regional performance heatmap
  • Trend analysis with period-over-period comparison

Usage:
    python demo_analytics.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SalesRecord:
    """A single sales transaction."""
    date: date
    region: str
    category: str
    customer: str
    product: str
    quantity: int
    unit_price: Decimal
    cost: Decimal

    @property
    def revenue(self) -> Decimal:
        return Decimal(self.quantity) * self.unit_price

    @property
    def profit(self) -> Decimal:
        return self.revenue - (Decimal(self.quantity) * self.cost)


@dataclass
class Dashboard:
    """BI dashboard — aggregates and visualizes sales data."""
    records: List[SalesRecord] = field(default_factory=list)

    def add_record(self, record: SalesRecord) -> None:
        self.records.append(record)

    # --- KPIs ---
    def total_revenue(self) -> Decimal:
        return sum(r.revenue for r in self.records)

    def total_profit(self) -> Decimal:
        return sum(r.profit for r in self.records)

    def total_orders(self) -> int:
        return len(self.records)

    def unique_customers(self) -> int:
        return len(set(r.customer for r in self.records))

    def avg_order_value(self) -> Decimal:
        if not self.records:
            return Decimal("0")
        return self.total_revenue() / len(self.records)

    def profit_margin(self) -> float:
        rev = self.total_revenue()
        if rev == 0:
            return 0.0
        return float(self.total_profit() / rev * 100)

    # --- Aggregations ---
    def revenue_by_date(self) -> Dict[date, Decimal]:
        result: Dict[date, Decimal] = {}
        for r in self.records:
            result[r.date] = result.get(r.date, Decimal("0")) + r.revenue
        return dict(sorted(result.items()))

    def revenue_by_category(self) -> Dict[str, Decimal]:
        result: Dict[str, Decimal] = {}
        for r in self.records:
            result[r.category] = result.get(r.category, Decimal("0")) + r.revenue
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def revenue_by_region(self) -> Dict[str, Decimal]:
        result: Dict[str, Decimal] = {}
        for r in self.records:
            result[r.region] = result.get(r.region, Decimal("0")) + r.revenue
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def top_customers(self, n: int = 5) -> List[Tuple[str, Decimal]]:
        customer_rev: Dict[str, Decimal] = {}
        for r in self.records:
            customer_rev[r.customer] = customer_rev.get(r.customer, Decimal("0")) + r.revenue
        sorted_customers = sorted(customer_rev.items(), key=lambda x: x[1], reverse=True)
        return sorted_customers[:n]

    def revenue_by_region_category(self) -> Dict[str, Dict[str, Decimal]]:
        result: Dict[str, Dict[str, Decimal]] = {}
        for r in self.records:
            if r.region not in result:
                result[r.region] = {}
            result[r.region][r.category] = result[r.region].get(r.category, Decimal("0")) + r.revenue
        return result

    def period_comparison(self, days: int = 30) -> Dict[str, Decimal]:
        """Compare last N days vs the N days before that."""
        if not self.records:
            return {"current": Decimal("0"), "previous": Decimal("0"), "growth_pct": Decimal("0")}
        max_date = max(r.date for r in self.records)
        cutoff = max_date - timedelta(days=days)
        prev_cutoff = cutoff - timedelta(days=days)
        current = sum(r.revenue for r in self.records if r.date > cutoff)
        previous = sum(r.revenue for r in self.records if prev_cutoff < r.date <= cutoff)
        growth = ((current - previous) / previous * 100) if previous else Decimal("0")
        return {"current": current, "previous": previous, "growth_pct": growth}


# ---------------------------------------------------------------------------
# ASCII chart helpers
# ---------------------------------------------------------------------------

def bar_chart(data: Dict[str, Decimal], title: str, width: int = 50) -> str:
    """Generate a simple ASCII horizontal bar chart."""
    if not data:
        return f"  {title}\n  (no data)"
    max_val = max(data.values())
    lines = [f"  {title}"]
    lines.append(f"  {'─' * (width + 20)}")
    for label, value in data.items():
        bar_len = int(float(value / max_val) * width) if max_val else 0
        bar = "█" * bar_len
        lines.append(f"  {label:<15} │{bar:<{width}}│ ${value:>10,.0f}")
    lines.append(f"  {'─' * (width + 20)}")
    return "\n".join(lines)


def line_chart(data: Dict[date, Decimal], title: str, width: int = 60, height: int = 10) -> str:
    """Generate a simple ASCII line chart for time-series data."""
    if not data:
        return f"  {title}\n  (no data)"
    dates = list(data.keys())
    values = list(data.values())
    max_val = max(values)
    min_val = min(values)
    val_range = max_val - min_val if max_val != min_val else Decimal("1")

    # Sample points to fit width
    n = len(dates)
    step = max(1, n // width)
    sampled = [(dates[i], values[i]) for i in range(0, n, step)]
    if sampled[-1][0] != dates[-1]:
        sampled.append((dates[-1], values[-1]))

    # Build grid
    grid = [[" " for _ in range(len(sampled))] for _ in range(height)]

    for col, (_, val) in enumerate(sampled):
        row = int(float((val - min_val) / val_range) * (height - 1))
        row = max(0, min(height - 1, row))
        grid[height - 1 - row][col] = "●"

    lines = [f"  {title}"]
    lines.append(f"  ${max_val:>10,.0f} ┤")
    for row in grid:
        lines.append(f"  {'':>12} │{''.join(row)}")
    lines.append(f"  ${min_val:>10,.0f} ┤")
    lines.append(f"  {'':>12} └{'─' * len(sampled)}")
    lines.append(f"  {'':>14}{dates[0]}  →  {dates[-1]}")
    return "\n".join(lines)


def heatmap(data: Dict[str, Dict[str, Decimal]], title: str) -> str:
    """Generate a simple ASCII heatmap for region × category."""
    all_categories = sorted(set(cat for cats in data.values() for cat in cats))
    lines = [f"  {title}"]
    # Header
    header = f"  {'Region':<12}" + "".join(f"{cat:>12}" for cat in all_categories) + f"{'Total':>12}"
    lines.append(header)
    lines.append(f"  {'─' * (len(header) - 2)}")
    # Find max for scaling
    all_values = [v for cats in data.values() for v in cats.values()]
    max_val = max(all_values) if all_values else Decimal("1")
    # Rows
    for region, cats in sorted(data.items()):
        row_total = sum(cats.values())
        row = f"  {region:<12}"
        for cat in all_categories:
            val = cats.get(cat, Decimal("0"))
            # Use block intensity: ░▒▓█
            intensity = float(val / max_val) if max_val else 0
            if intensity > 0.75:
                cell = "███"
            elif intensity > 0.5:
                cell = "▓▓▓"
            elif intensity > 0.25:
                cell = "▒▒▒"
            elif intensity > 0:
                cell = "░░░"
            else:
                cell = "   "
            row += f"{cell:>12}"
        row += f"${row_total:>10,.0f}"
        lines.append(row)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def generate_sample_data() -> Dashboard:
    """Generate 90 days of sample sales data."""
    dash = Dashboard()
    regions = ["North", "South", "East", "West"]
    categories = ["Software", "Services", "Hardware", "Support"]
    customers = [
        "Acme Corp", "Globex Inc", "Initech", "Umbrella Corp",
        "Stark Industries", "Wayne Enterprises", "Cyberdyne Systems",
        "Soylent Corp", "Hooli", "Pied Piper",
    ]
    products = {
        "Software": [("Enterprise License", 5000, 500), ("SaaS Subscription", 500, 50), ("Add-on Module", 1000, 100)],
        "Services": [("Consulting Day", 1500, 600), ("Implementation", 8000, 3000), ("Training Day", 800, 300)],
        "Hardware": [("Server Appliance", 12000, 7000), ("Workstation", 2500, 1500), ("Network Gear", 3000, 1800)],
        "Support": [("Premium Support (mo)", 1000, 200), ("Basic Support (mo)", 300, 60)],
    }

    base_date = date(2026, 7, 1)
    # Deterministic pseudo-random for reproducibility
    seed = 42
    def next_rand() -> float:
        nonlocal seed
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        return seed / 0x7FFFFFFF

    for day_offset in range(90):
        d = base_date + timedelta(days=day_offset)
        # More sales on weekdays
        if d.weekday() >= 5:
            continue
        # 3-8 transactions per day
        num_txn = 3 + int(next_rand() * 6)
        for _ in range(num_txn):
            region = regions[int(next_rand() * len(regions))]
            category = categories[int(next_rand() * len(categories))]
            customer = customers[int(next_rand() * len(customers))]
            product_info = products[category][int(next_rand() * len(products[category]))]
            product_name, unit_price, cost = product_info
            quantity = 1 + int(next_rand() * 5)
            # Add some seasonality (higher at end of quarter)
            if d.month in (3, 6, 9, 12) and d.day > 20:
                quantity = int(quantity * 1.5)
            dash.add_record(SalesRecord(
                date=d, region=region, category=category,
                customer=customer, product=product_name,
                quantity=quantity, unit_price=Decimal(str(unit_price)),
                cost=Decimal(str(cost)),
            ))
    return dash


def run_demo() -> None:
    """Run the analytics demonstration."""
    print("=" * 70)
    print("  APEX-OS Business Platform — Analytics Demo")
    print("  BI Dashboard with Sample Data")
    print("=" * 70)

    dash = generate_sample_data()
    print(f"\n  Loaded {dash.total_orders()} sales records (Jul–Sep 2026)")

    # 1. KPI Cards
    print("\n" + "─" * 70)
    print("  📊 KEY PERFORMANCE INDICATORS")
    print("─" * 70)
    kpis = [
        ("Total Revenue", f"${dash.total_revenue():>12,.2f}"),
        ("Total Profit", f"${dash.total_profit():>12,.2f}"),
        ("Total Orders", f"{dash.total_orders():>12,}"),
        ("Unique Customers", f"{dash.unique_customers():>12,}"),
        ("Avg Order Value", f"${dash.avg_order_value():>12,.2f}"),
        ("Profit Margin", f"{dash.profit_margin():>11.1f}%"),
    ]
    for label, value in kpis:
        print(f"  {label:<20} {value:>20}")

    # 2. Period-over-period comparison
    print("\n" + "─" * 70)
    print("  📈 PERIOD-OVER-PERIOD COMPARISON (30-day)")
    print("─" * 70)
    comp = dash.period_comparison(30)
    growth_icon = "📈" if comp["growth_pct"] > 0 else "📉"
    print(f"  Current 30 days:  ${comp['current']:>12,.2f}")
    print(f"  Previous 30 days: ${comp['previous']:>12,.2f}")
    print(f"  Growth:           {growth_icon} {comp['growth_pct']:>+.1f}%")

    # 3. Revenue trend (daily)
    print("\n" + "─" * 70)
    print(line_chart(dash.revenue_by_date(), "  Daily Revenue Trend"))

    # 4. Revenue by category
    print("\n" + "─" * 70)
    print(bar_chart(dash.revenue_by_category(), "  Revenue by Category"))

    # 5. Revenue by region
    print("\n" + "─" * 70)
    print(bar_chart(dash.revenue_by_region(), "  Revenue by Region"))

    # 6. Region × Category heatmap
    print("\n" + "─" * 70)
    print(heatmap(dash.revenue_by_region_category(), "  Region × Category Heatmap"))

    # 7. Top customers
    print("\n" + "─" * 70)
    print("  🏆 TOP 5 CUSTOMERS BY REVENUE")
    print("─" * 70)
    print(f"  {'Rank':<6} {'Customer':<25} {'Revenue':>15} {'% of Total':>12}")
    print(f"  {'─'*6} {'─'*25} {'─'*15} {'─'*12}")
    total_rev = dash.total_revenue()
    for i, (customer, rev) in enumerate(dash.top_customers(5), 1):
        pct = float(rev / total_rev * 100) if total_rev else 0
        print(f"  {i:<6} {customer:<25} ${rev:>13,.2f} {pct:>10.1f}%")

    # 8. Category performance detail
    print("\n" + "─" * 70)
    print("  📋 CATEGORY PERFORMANCE DETAIL")
    print("─" * 70)
    cat_rev = dash.revenue_by_category()
    for cat, rev in cat_rev.items():
        pct = float(rev / total_rev * 100) if total_rev else 0
        bar = "█" * int(pct / 2)
        print(f"  {cat:<12} ${rev:>12,.2f}  ({pct:>5.1f}%)  {bar}")

    print("\n" + "=" * 70)
    print("  Analytics demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
