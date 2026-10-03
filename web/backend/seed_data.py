"""
Seed script to populate all API endpoints with test data.
Run: python3 seed_data.py
"""
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, List, Union

BASE = "http://localhost:8000"

def api(method: str, path: str, data: Optional[Dict] = None) -> Union[Dict, List, None]:
    """Make API call and return parsed JSON."""
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        print(f"  ✗ {method} {path} → {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  ✗ {method} {path} → {e}")
        return None

def seed_users():
    """Seed users table."""
    print("\n=== Seeding Users ===")
    users = [
        {"name": "Ahmed Hassan", "email": "aah@a2zsoc.com", "role": "admin", "status": "active"},
        {"name": "Sarah Chen", "email": "francis@example.com", "role": "manager", "status": "active"},
        {"name": "Sarah Kim", "email": "sarah@example.com", "role": "editor", "status": "active"},
        {"name": "Mike Johnson", "email": "mike@example.com", "role": "viewer", "status": "active"},
        {"name": "Emily Davis", "email": "emily@example.com", "role": "editor", "status": "inactive"},
    ]
    for u in users:
        result = api("POST", "/api/users", u)
        if result:
            print(f"  ✓ Created user: {u['name']} ({u['email']})")

def seed_leads():
    """Seed leads table."""
    print("\n=== Seeding Leads ===")
    leads = [
        {"name": "Acme Corp", "company": "Acme Corporation", "email": "contact@acme.com", "phone": "+1-555-0101", "value": 50000, "status": "Qualified"},
        {"name": "TechStart Inc", "company": "TechStart", "email": "info@techstart.io", "phone": "+1-555-0102", "value": 25000, "status": "Contacted"},
        {"name": "Global Systems", "company": "Global Systems Ltd", "email": "sales@globalsys.com", "phone": "+1-555-0103", "value": 100000, "status": "Proposal"},
        {"name": "DataFlow", "company": "DataFlow Analytics", "email": "hello@dataflow.ai", "phone": "+1-555-0104", "value": 75000, "status": "Negotiation"},
        {"name": "CloudNine", "company": "CloudNine Solutions", "email": "team@cloudnine.co", "phone": "+1-555-0105", "value": 30000, "status": "New"},
        {"name": "InnovateTech", "company": "InnovateTech", "email": "contact@innovatetech.com", "phone": "+1-555-0106", "value": 150000, "status": "Won"},
        {"name": "SmartSystems", "company": "SmartSystems Inc", "email": "info@smartsys.com", "phone": "+1-555-0107", "value": 45000, "status": "Lost"},
    ]
    for l in leads:
        result = api("POST", "/api/leads", l)
        if result:
            print(f"  ✓ Created lead: {l['name']} (${l['value']:,})")

def seed_reports():
    """Seed reports table."""
    print("\n=== Seeding Reports ===")
    reports = [
        {"name": "Revenue Dashboard", "report_type": "dashboard", "description": "Monthly revenue trends", "owner": "finance-team", "is_active": True},
        {"name": "User Growth", "report_type": "chart", "description": "Weekly active users", "owner": "growth-team", "is_active": True},
        {"name": "Churn Analysis", "report_type": "table", "description": "Customer churn breakdown", "owner": "retention-team", "is_active": True},
        {"name": "Sales Pipeline", "report_type": "funnel", "description": "Deal stage funnel", "owner": "sales-team", "is_active": True},
        {"name": "Support Tickets", "report_type": "chart", "description": "Ticket volume by category", "owner": "support-team", "is_active": False},
    ]
    for r in reports:
        result = api("POST", "/api/reports", r)
        if result:
            print(f"  ✓ Created report: {r['name']}")

def seed_products():
    """Seed products table."""
    print("\n=== Seeding Products ===")
    products = [
        {"name": "Enterprise License", "price": 9999.99, "stock": 100, "category": "Software"},
        {"name": "Professional License", "price": 4999.99, "stock": 250, "category": "Software"},
        {"name": "Starter License", "price": 999.99, "stock": 500, "category": "Software"},
        {"name": "Consulting Package", "price": 50000.00, "stock": 10, "category": "Services"},
        {"name": "Training Package", "price": 15000.00, "stock": 25, "category": "Services"},
    ]
    for p in products:
        result = api("POST", "/api/products", p)
        if result:
            print(f"  ✓ Created product: {p['name']} (${p['price']:,.2f})")

def seed_orders():
    """Seed orders table."""
    print("\n=== Seeding Orders ===")
    orders = [
        {"customer_id": 1, "total": 9999.99, "status": "completed", "product_id": 1},
        {"customer_id": 2, "total": 4999.99, "status": "pending", "product_id": 2},
        {"customer_id": 3, "total": 14999.98, "status": "completed", "product_id": 1},
        {"customer_id": 4, "total": 999.99, "status": "cancelled", "product_id": 3},
        {"customer_id": 5, "total": 50000.00, "status": "pending", "product_id": 4},
    ]
    for o in orders:
        result = api("POST", "/api/orders", o)
        if result:
            print(f"  ✓ Created order: ${o['total']:,.2f} ({o['status']})")

def seed_customers():
    """Seed customers table."""
    print("\n=== Seeding Customers ===")
    customers = [
        {"name": "Acme Corp", "email": "contact@acme.com", "phone": "+1-555-0101", "company": "Acme Corporation"},
        {"name": "TechStart Inc", "email": "info@techstart.io", "phone": "+1-555-0102", "company": "TechStart"},
        {"name": "Global Systems", "email": "sales@globalsys.com", "phone": "+1-555-0103", "company": "Global Systems Ltd"},
        {"name": "DataFlow", "email": "hello@dataflow.ai", "phone": "+1-555-0104", "company": "DataFlow Analytics"},
        {"name": "CloudNine", "email": "team@cloudnine.co", "phone": "+1-555-0105", "company": "CloudNine Solutions"},
    ]
    for c in customers:
        result = api("POST", "/api/customers", c)
        if result:
            print(f"  ✓ Created customer: {c['name']}")

def seed_employees():
    """Seed employees table."""
    print("\n=== Seeding Employees ===")
    employees = [
        {"name": "Ahmed Hassan", "email": "aah@a2zsoc.com", "department": "Engineering", "role": "Founder"},
        {"name": "Francis Chen", "email": "francis@example.com", "department": "Engineering", "role": "Senior Engineer"},
        {"name": "Sarah Kim", "email": "sarah@example.com", "department": "Product", "role": "Product Manager"},
        {"name": "Mike Johnson", "email": "mike@example.com", "department": "Sales", "role": "Sales Director"},
        {"name": "Emily Davis", "email": "emily@example.com", "department": "Marketing", "role": "Marketing Lead"},
    ]
    for e in employees:
        result = api("POST", "/api/employees", e)
        if result:
            print(f"  ✓ Created employee: {e['name']} ({e['department']})")

def seed_projects():
    """Seed projects table."""
    print("\n=== Seeding Projects ===")
    projects = [
        {"name": "APEX-OS Platform", "status": "active", "description": "Core platform development"},
        {"name": "CRM Integration", "status": "active", "description": "Customer relationship management"},
        {"name": "Analytics Dashboard", "status": "completed", "description": "Business intelligence dashboard"},
        {"name": "Mobile App", "status": "planning", "description": "iOS and Android applications"},
        {"name": "API Gateway", "status": "active", "description": "Unified API gateway"},
    ]
    for p in projects:
        result = api("POST", "/api/projects", p)
        if result:
            print(f"  ✓ Created project: {p['name']} ({p['status']})")

def seed_tasks():
    """Seed tasks table."""
    print("\n=== Seeding Tasks ===")
    tasks = [
        {"title": "Implement user authentication", "assignee": "Ahmed Hassan", "done": True, "project_id": 1},
        {"title": "Design database schema", "assignee": "Francis Chen", "done": True, "project_id": 1},
        {"title": "Build API endpoints", "assignee": "Francis Chen", "done": False, "project_id": 1},
        {"title": "Create UI components", "assignee": "Sarah Kim", "done": False, "project_id": 2},
        {"title": "Write documentation", "assignee": "Mike Johnson", "done": False, "project_id": 3},
    ]
    for t in tasks:
        result = api("POST", "/api/tasks", t)
        if result:
            print(f"  ✓ Created task: {t['title']}")

def seed_inventory():
    """Seed inventory table."""
    print("\n=== Seeding Inventory ===")
    items = [
        {"item": "Server Rack A1", "quantity": 5, "location": "Data Center 1"},
        {"item": "Network Switch B2", "quantity": 12, "location": "Data Center 1"},
        {"item": "Storage Array C3", "quantity": 3, "location": "Data Center 2"},
        {"item": "UPS Unit D4", "quantity": 8, "location": "Data Center 1"},
        {"item": "Cooling System E5", "quantity": 2, "location": "Data Center 2"},
    ]
    for i in items:
        result = api("POST", "/api/inventory", i)
        if result:
            print(f"  ✓ Created inventory item: {i['item']} (qty: {i['quantity']})")

def seed_payments():
    """Seed payments table."""
    print("\n=== Seeding Payments ===")
    payments = [
        {"amount": 9999.99, "method": "credit_card", "status": "completed", "customer_id": 1},
        {"amount": 4999.99, "method": "bank_transfer", "status": "pending", "customer_id": 2},
        {"amount": 14999.98, "method": "credit_card", "status": "completed", "customer_id": 3},
        {"amount": 999.99, "method": "paypal", "status": "failed", "customer_id": 4},
        {"amount": 50000.00, "method": "bank_transfer", "status": "pending", "customer_id": 5},
    ]
    for p in payments:
        result = api("POST", "/api/payments", p)
        if result:
            print(f"  ✓ Created payment: ${p['amount']:,.2f} ({p['method']})")

def seed_notifications():
    """Seed notifications table."""
    print("\n=== Seeding Notifications ===")
    notifications = [
        {"message": "New user registered: Ahmed Hassan", "type": "info", "read": False},
        {"message": "Payment received: $9,999.99", "message": "success", "read": True},
        {"message": "Server alert: High CPU usage", "type": "warning", "read": False},
        {"message": "Backup completed successfully", "type": "success", "read": True},
        {"message": "New lead assigned: Acme Corp", "type": "info", "read": False},
    ]
    for n in notifications:
        result = api("POST", "/api/notifications", n)
        if result:
            print(f"  ✓ Created notification: {n['message'][:50]}")

def seed_audit_logs():
    """Seed audit logs table."""
    print("\n=== Seeding Audit Logs ===")
    logs = [
        {"action": "user.login", "user_id": 1, "details": "Successful login from 192.168.1.1"},
        {"action": "user.create", "user_id": 1, "details": "Created user: Ahmed Hassan"},
        {"action": "lead.update", "user_id": 2, "details": "Updated lead: Acme Corp"},
        {"action": "report.generate", "user_id": 3, "details": "Generated report: Revenue Dashboard"},
        {"action": "payment.process", "user_id": 1, "details": "Processed payment: $9,999.99"},
    ]
    for l in logs:
        result = api("POST", "/api/audit-logs", l)
        if result:
            print(f"  ✓ Created audit log: {l['action']}")

def seed_journal_entries():
    """Seed journal entries table."""
    print("\n=== Seeding Journal Entries ===")
    entries = [
        {"debit": 9999.99, "credit": 0, "account": "Accounts Receivable", "description": "Invoice #001"},
        {"debit": 0, "credit": 9999.99, "account": "Revenue", "description": "Invoice #001"},
        {"debit": 5000.00, "credit": 0, "account": "Cash", "description": "Payment received"},
        {"debit": 0, "credit": 5000.00, "account": "Accounts Receivable", "description": "Payment received"},
        {"debit": 1000.00, "credit": 0, "account": "Expenses", "description": "Office supplies"},
    ]
    for e in entries:
        result = api("POST", "/api/journal-entries", e)
        if result:
            print(f"  ✓ Created journal entry: {e['description']}")

def seed_invoices():
    """Seed invoices table."""
    print("\n=== Seeding Invoices ===")
    invoices = [
        {"customer_id": 1, "amount": 9999.99, "status": "paid", "due_date": "2026-10-15"},
        {"customer_id": 2, "amount": 4999.99, "status": "pending", "due_date": "2026-10-20"},
        {"customer_id": 3, "amount": 14999.98, "status": "paid", "due_date": "2026-10-10"},
        {"customer_id": 4, "amount": 999.99, "status": "overdue", "due_date": "2026-09-30"},
        {"customer_id": 5, "amount": 50000.00, "status": "pending", "due_date": "2026-10-25"},
    ]
    for i in invoices:
        result = api("POST", "/api/invoices", i)
        if result:
            print(f"  ✓ Created invoice: ${i['amount']:,.2f} ({i['status']})")

def seed_dashboard():
    """Seed dashboard table."""
    print("\n=== Seeding Dashboard ===")
    widgets = [
        {"widget": "revenue_chart", "config": {"type": "line", "data": [100, 200, 300, 400, 500]}},
        {"widget": "user_growth", "config": {"type": "bar", "data": [50, 100, 150, 200, 250]}},
        {"widget": "conversion_funnel", "config": {"type": "funnel", "data": [1000, 500, 250, 125, 50]}},
        {"widget": "kpi_cards", "config": {"type": "cards", "metrics": ["Revenue", "Users", "Conversion", "Churn"]}},
    ]
    for w in widgets:
        result = api("POST", "/api/dashboard", w)
        if result:
            print(f"  ✓ Created dashboard widget: {w['widget']}")

def seed_accounting():
    """Seed accounting table."""
    print("\n=== Seeding Accounting ===")
    accounts = [
        {"account": "Cash", "balance": 100000.00, "type": "asset"},
        {"account": "Accounts Receivable", "balance": 50000.00, "type": "asset"},
        {"account": "Revenue", "balance": 200000.00, "type": "revenue"},
        {"account": "Expenses", "balance": 75000.00, "type": "expense"},
        {"account": "Accounts Payable", "balance": 25000.00, "type": "liability"},
    ]
    for a in accounts:
        result = api("POST", "/api/accounting", a)
        if result:
            print(f"  ✓ Created account: {a['account']} (${a['balance']:,.2f})")

def seed_analytics():
    """Seed analytics table."""
    print("\n=== Seeding Analytics ===")
    metrics = [
        {"metric": "Daily Active Users", "value": 1250, "change": 5.2},
        {"metric": "Conversion Rate", "value": 3.5, "change": -0.8},
        {"metric": "Average Order Value", "value": 299.99, "change": 12.3},
        {"metric": "Customer Lifetime Value", "value": 4500.00, "change": 8.1},
        {"metric": "Churn Rate", "value": 2.1, "change": -1.5},
    ]
    for m in metrics:
        result = api("POST", "/api/analytics", m)
        if result:
            print(f"  ✓ Created metric: {m['metric']} ({m['value']})")

def seed_agent_reach():
    """Seed agent-reach table."""
    print("\n=== Seeding Agent Reach ===")
    agents = [
        {"agent": "Sales Bot", "reach": 15000, "status": "active"},
        {"agent": "Support Bot", "reach": 25000, "status": "active"},
        {"agent": "Marketing Bot", "reach": 8000, "status": "active"},
        {"agent": "Analytics Bot", "reach": 5000, "status": "inactive"},
        {"agent": "Onboarding Bot", "reach": 12000, "status": "active"},
    ]
    for a in agents:
        result = api("POST", "/api/agent-reach", a)
        if result:
            print(f"  ✓ Created agent: {a['agent']} (reach: {a['reach']:,})")

def seed_bigdata():
    """Seed bigdata table."""
    print("\n=== Seeding Big Data ===")
    datasets = [
        {"dataset": "user_events", "size": 1024000, "format": "parquet"},
        {"dataset": "transactions", "size": 2048000, "format": "parquet"},
        {"dataset": "logs", "size": 512000, "format": "json"},
        {"dataset": "metrics", "size": 256000, "format": "csv"},
        {"dataset": "profiles", "size": 128000, "format": "json"},
    ]
    for d in datasets:
        result = api("POST", "/api/bigdata", d)
        if result:
            print(f"  ✓ Created dataset: {d['dataset']} ({d['size']:,} bytes)")

def seed_datascience():
    """Seed datascience table."""
    print("\n=== Seeding Data Science ===")
    models = [
        {"model": "churn_predictor", "accuracy": 0.89, "status": "production"},
        {"model": "revenue_forecaster", "accuracy": 0.92, "status": "production"},
        {"model": "recommendation_engine", "accuracy": 0.78, "status": "staging"},
        {"model": "fraud_detector", "accuracy": 0.95, "status": "production"},
        {"model": "sentiment_analyzer", "accuracy": 0.83, "status": "development"},
    ]
    for m in models:
        result = api("POST", "/api/datascience", m)
        if result:
            print(f"  ✓ Created model: {m['model']} (accuracy: {m['accuracy']:.0%})")

def seed_continuous_bi():
    """Seed continuous-bi table."""
    print("\n=== Seeding Continuous BI ===")
    pipelines = [
        {"pipeline": "realtime_revenue", "status": "running", "latency_ms": 150},
        {"pipeline": "user_activity", "status": "running", "latency_ms": 200},
        {"pipeline": "inventory_sync", "status": "paused", "latency_ms": 500},
        {"pipeline": "customer_360", "status": "running", "latency_ms": 300},
        {"pipeline": "predictive_analytics", "status": "failed", "latency_ms": 1000},
    ]
    for p in pipelines:
        result = api("POST", "/api/continuous-bi", p)
        if result:
            print(f"  ✓ Created pipeline: {p['pipeline']} ({p['status']})")

def main():
    """Run all seed functions."""
    print("=" * 60)
    print("APEX-OS Business Platform - Database Seeder")
    print("=" * 60)
    
    # Check backend health
    try:
        with urllib.request.urlopen(f"{BASE}/api/health", timeout=5) as resp:
            print(f"\n✓ Backend healthy: {resp.read().decode()}")
    except Exception as e:
        print(f"\n✗ Backend not reachable: {e}")
        print("Please start the backend first:")
        print("  cd web/backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000")
        return
    
    # Seed all tables
    seed_users()
    seed_leads()
    seed_reports()
    seed_products()
    seed_orders()
    seed_customers()
    seed_employees()
    seed_projects()
    seed_tasks()
    seed_inventory()
    seed_payments()
    seed_notifications()
    seed_audit_logs()
    seed_journal_entries()
    seed_invoices()
    seed_dashboard()
    seed_accounting()
    seed_analytics()
    seed_agent_reach()
    seed_bigdata()
    seed_datascience()
    seed_continuous_bi()
    
    print("\n" + "=" * 60)
    print("✓ Seeding complete!")
    print("=" * 60)
    print("\nYou can now:")
    print("  1. View data in the UI at http://localhost:3000")
    print("  2. Test CRUD operations on any table")
    print("  3. Use the Database Admin page to manage all tables")

if __name__ == "__main__":
    main()
