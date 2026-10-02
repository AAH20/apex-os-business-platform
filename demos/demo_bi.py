#!/usr/bin/env python3
"""APEX-OS BI Demo: dashboard, widget, query, report, share."""
import json
import random
import statistics
from datetime import datetime, timedelta

random.seed(42)


def create_dashboard():
    dash = {
        "id": "dash_001",
        "name": "Executive Overview",
        "created": datetime.now().isoformat(timespec="seconds"),
        "widgets": [],
    }
    print("CREATE DASHBOARD")
    print(f"  id:       {dash['id']}")
    print(f"  name:     {dash['name']}")
    print(f"  created:  {dash['created']}")
    print(f"  widgets:  {len(dash['widgets'])}\n")
    return dash


def add_widget(dash):
    widgets = [
        {"type": "line_chart", "title": "Revenue Trend", "metric": "revenue"},
        {"type": "bar_chart", "title": "Orders by Region", "metric": "orders"},
        {"type": "kpi_card", "title": "Active Users", "metric": "users"},
    ]
    for w in widgets:
        dash["widgets"].append(w)
    print("ADD WIDGETS")
    for w in dash["widgets"]:
        print(f"  [{w['type']:12s}] {w['title']} (metric: {w['metric']})")
    print(f"  total widgets: {len(dash['widgets'])}\n")
    return dash


def query_data():
    regions = ["NA", "EU", "APAC", "LATAM"]
    data = {r: random.randint(200, 800) for r in regions}
    total = sum(data.values())
    print("QUERY DATA")
    print(f"  SELECT region, COUNT(*) FROM orders GROUP BY region")
    for r, c in data.items():
        pct = c / total * 100
        print(f"    {r:6s} {c:5d}  {pct:5.1f}%  {'#' * int(pct / 3)}")
    print(f"  total rows: {total}\n")
    return data


def generate_report(data):
    revenue = round(sum(random.uniform(500, 1200) for _ in range(30)), 2)
    orders = sum(data.values())
    aov = round(revenue / orders, 2) if orders else 0
    top_region = max(data, key=data.get)
    report = {
        "title": "Weekly Business Report",
        "period": "2026-09-25 to 2026-10-01",
        "revenue": revenue,
        "orders": orders,
        "aov": aov,
        "top_region": top_region,
        "generated": datetime.now().isoformat(timespec="seconds"),
    }
    print("GENERATE REPORT")
    print(f"  title:     {report['title']}")
    print(f"  period:    {report['period']}")
    print(f"  revenue:   ${revenue:,.2f}")
    print(f"  orders:    {orders}")
    print(f"  AOV:       ${aov}")
    print(f"  top region:{report['top_region']}")
    print(f"  generated: {report['generated']}\n")
    return report


def share_dashboard(dash, report):
    share = {
        "dashboard_id": dash["id"],
        "dashboard_name": dash["name"],
        "shared_with": ["team@apex-os.com", "exec@apex-os.com"],
        "report_title": report["title"],
        "link": f"https://bi.apex-os.com/d/{dash['id']}",
        "expires": (datetime.now() + timedelta(days=7)).isoformat(timespec="seconds"),
    }
    print("SHARE DASHBOARD")
    print(f"  dashboard: {share['dashboard_name']} ({share['dashboard_id']})")
    print(f"  link:      {share['link']}")
    print(f"  shared:    {', '.join(share['shared_with'])}")
    print(f"  expires:   {share['expires']}")
    print(f"  status:    SHARED\n")
    return share


if __name__ == "__main__":
    dash = create_dashboard()
    dash = add_widget(dash)
    data = query_data()
    report = generate_report(data)
    share_dashboard(dash, report)
