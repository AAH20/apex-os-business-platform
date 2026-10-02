#!/usr/bin/env python3
"""Demo: Data Warehouse — creation, ETL, querying, reporting, quality monitoring."""
import sqlite3, os, random, datetime

DB = "warehouse_demo.db"

def create_warehouse():
    """(1) Create warehouse schema."""
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY, name TEXT, segment TEXT, region TEXT
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL
        );
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY, customer_id INTEGER, product_id INTEGER,
            quantity INTEGER, sale_date TEXT, amount REAL
        );
        CREATE TABLE etl_log (
            id INTEGER PRIMARY KEY, step TEXT, rows_affected INTEGER, ts TEXT
        );
    """)
    conn.commit()
    conn.close()
    print("[1] Warehouse created: 4 tables (customers, products, sales, etl_log)")

def run_etl():
    """(2) Run ETL — extract, transform, load sample data."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    random.seed(42)
    segments = ["Enterprise", "SMB", "Consumer"]
    regions = ["NA", "EU", "APAC"]
    categories = ["Electronics", "Clothing", "Food"]
    customers = [(i, f"Customer_{i}", random.choice(segments), random.choice(regions))
                 for i in range(1, 21)]
    products = [(i, f"Product_{i}", random.choice(categories), round(random.uniform(10, 500), 2))
                for i in range(1, 11)]
    sales = []
    for i in range(1, 101):
        cust = random.randint(1, 20)
        prod = random.randint(1, 10)
        qty = random.randint(1, 5)
        price = products[prod - 1][3]
        amt = round(qty * price, 2)
        date = (datetime.date(2024, 1, 1) + datetime.timedelta(days=random.randint(0, 364))).isoformat()
        sales.append((i, cust, prod, qty, date, amt))
    c.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)
    c.executemany("INSERT INTO products VALUES (?,?,?,?)", products)
    c.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?)", sales)
    c.execute("INSERT INTO etl_log VALUES (?,?,?,?)",
              (1, "load_customers", len(customers), datetime.datetime.now().isoformat()))
    c.execute("INSERT INTO etl_log VALUES (?,?,?,?)",
              (2, "load_products", len(products), datetime.datetime.now().isoformat()))
    c.execute("INSERT INTO etl_log VALUES (?,?,?,?)",
              (3, "load_sales", len(sales), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print(f"[2] ETL complete: {len(customers)} customers, {len(products)} products, {len(sales)} sales loaded")

def query_data():
    """(3) Query data — top customers, category revenue, monthly trend."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    print("[3] Query results:")
    c.execute("""
        SELECT cu.name, SUM(s.amount) as total
        FROM sales s JOIN customers cu ON s.customer_id = cu.id
        GROUP BY cu.name ORDER BY total DESC LIMIT 5
    """)
    print("  Top 5 customers by revenue:")
    for row in c.fetchall():
        print(f"    {row[0]}: ${row[1]:,.2f}")
    c.execute("""
        SELECT p.category, SUM(s.amount) as revenue
        FROM sales s JOIN products p ON s.product_id = p.id
        GROUP BY p.category ORDER BY revenue DESC
    """)
    print("  Revenue by category:")
    for row in c.fetchall():
        print(f"    {row[0]}: ${row[1]:,.2f}")
    c.execute("""
        SELECT strftime('%Y-%m', sale_date) as month, COUNT(*) as orders
        FROM sales GROUP BY month ORDER BY month LIMIT 3
    """)
    print("  Monthly orders (first 3 months):")
    for row in c.fetchall():
        print(f"    {row[0]}: {row[1]} orders")
    conn.close()

def generate_report():
    """(4) Generate summary report."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(amount), AVG(amount) FROM sales")
    total_orders, total_revenue, avg_order = c.fetchone()
    c.execute("SELECT COUNT(*) FROM customers")
    total_customers = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM products")
    total_products = c.fetchone()[0]
    conn.close()
    print("[4] === SALES REPORT ===")
    print(f"  Period: 2024-01-01 to 2024-12-31")
    print(f"  Total Customers: {total_customers}")
    print(f"  Total Products:   {total_products}")
    print(f"  Total Orders:     {total_orders}")
    print(f"  Total Revenue:    ${total_revenue:,.2f}")
    print(f"  Avg Order Value:  ${avg_order:,.2f}")
    print("  ======================")

def monitor_quality():
    """(5) Monitor data quality — nulls, duplicates, referential integrity."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    print("[5] Data Quality Checks:")
    c.execute("SELECT COUNT(*) FROM sales WHERE amount IS NULL OR amount <= 0")
    bad_amounts = c.fetchone()[0]
    print(f"  Invalid amounts:     {bad_amounts} {'PASS' if bad_amounts == 0 else 'FAIL'}")
    c.execute("""
        SELECT COUNT(*) FROM sales s
        LEFT JOIN customers cu ON s.customer_id = cu.id
        WHERE cu.id IS NULL
    """)
    orphan_cust = c.fetchone()[0]
    print(f"  Orphan customers:    {orphan_cust} {'PASS' if orphan_cust == 0 else 'FAIL'}")
    c.execute("""
        SELECT COUNT(*) FROM sales s
        LEFT JOIN products p ON s.product_id = p.id
        WHERE p.id IS NULL
    """)
    orphan_prod = c.fetchone()[0]
    print(f"  Orphan products:     {orphan_prod} {'PASS' if orphan_prod == 0 else 'FAIL'}")
    c.execute("SELECT COUNT(*) FROM (SELECT customer_id, product_id, sale_date, COUNT(*) as cnt FROM sales GROUP BY 1,2,3 HAVING cnt > 1)")
    dupes = c.fetchone()[0]
    print(f"  Duplicate records:   {dupes} {'PASS' if dupes == 0 else 'FAIL'}")
    c.execute("SELECT COUNT(*) FROM etl_log")
    etl_runs = c.fetchone()[0]
    print(f"  ETL runs logged:     {etl_runs} {'PASS' if etl_runs >= 3 else 'FAIL'}")
    conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("  DATA WAREHOUSE DEMO")
    print("=" * 50)
    create_warehouse()
    run_etl()
    query_data()
    generate_report()
    monitor_quality()
    print("=" * 50)
    print("  DEMO COMPLETE")
    print("=" * 50)
