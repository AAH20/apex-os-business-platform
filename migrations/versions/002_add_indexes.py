"""Add performance indexes.

Revision ID: 002_add_indexes
Revises: 001_initial_schema
Create Date: 2026-10-03 00:01:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_add_indexes"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])
    op.create_index("ix_accounts_status", "accounts", ["status"])
    op.create_index("ix_accounts_user_status", "accounts", ["user_id", "status"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_type", "transactions", ["type"])
    op.create_index("ix_transactions_account_created", "transactions", ["account_id", "created_at"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])
    op.create_index("ix_crm_deals_contact_id", "crm_deals", ["contact_id"])
    op.create_index("ix_crm_deals_stage", "crm_deals", ["stage"])
    op.create_index("ix_inventory_products_sku", "inventory_products", ["sku"])
    op.create_index("ix_inventory_products_category", "inventory_products", ["category"])
    op.create_index("ix_inventory_stock_items_product", "inventory_stock_items", ["product_id"])
    op.create_index("ix_inventory_stock_movements_product", "inventory_stock_movements", ["product_id"])
    op.create_index("ix_inventory_stock_movements_timestamp", "inventory_stock_movements", ["timestamp"])
    op.create_index("ix_inventory_po_lines_po", "inventory_purchase_order_lines", ["po_id"])
    op.create_index("ix_inventory_so_lines_so", "inventory_sales_order_lines", ["so_id"])
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_assigned_to", "tasks", ["assigned_to"])
    op.create_index("ix_time_entries_task_id", "time_entries", ["task_id"])
    op.create_index("ix_time_entries_user_id", "time_entries", ["user_id"])
    op.create_index("ix_billing_subs_customer", "billing_subscriptions", ["customer_id"])
    op.create_index("ix_billing_subs_plan", "billing_subscriptions", ["plan_id"])
    op.create_index("ix_billing_subs_status", "billing_subscriptions", ["status"])
    op.create_index("ix_billing_usage_sub", "billing_usage_records", ["subscription_id"])
    op.create_index("ix_billing_invoices_customer", "billing_invoices", ["customer_id"])
    op.create_index("ix_billing_invoices_status", "billing_invoices", ["status"])
    op.create_index("ix_billing_payments_invoice", "billing_payments", ["invoice_id"])
    op.create_index("ix_billing_payments_customer", "billing_payments", ["customer_id"])
    op.create_index("ix_ecom_orders_customer", "ecommerce_orders", ["customer_id"])
    op.create_index("ix_ecom_orders_status", "ecommerce_orders", ["status"])
    op.create_index("ix_ecom_order_items_order", "ecommerce_order_items", ["order_id"])
    op.create_index("ix_ecom_payments_order", "ecommerce_payments", ["order_id"])
    op.create_index("ix_acct_accounts_type", "accounting_accounts", ["account_type"])
    op.create_index("ix_acct_journal_date", "accounting_journal_entries", ["date"])
    op.create_index("ix_acct_trans_journal", "accounting_transactions", ["journal_entry_id"])
    op.create_index("ix_acct_trans_account", "accounting_transactions", ["account_id"])
    op.create_index("ix_acct_inv_customer", "accounting_invoices", ["customer_id"])
    op.create_index("ix_acct_inv_status", "accounting_invoices", ["status"])
    op.create_index("ix_acct_inv_lines_inv", "accounting_invoice_line_items", ["invoice_id"])
    op.create_index("ix_mkt_campaigns_status", "marketing_campaigns", ["status"])
    op.create_index("ix_mkt_leads_email", "marketing_leads", ["email"])
    op.create_index("ix_mkt_leads_status", "marketing_leads", ["status"])
    op.create_index("ix_mkt_nurture_steps_seq", "marketing_nurture_steps", ["sequence_id"])
    op.create_index("ix_mkt_enrollments_lead", "marketing_lead_enrollments", ["lead_id"])
    op.create_index("ix_mkt_enrollments_seq", "marketing_lead_enrollments", ["sequence_id"])
    op.create_index("ix_mkt_ab_variants_test", "marketing_ab_variants", ["test_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_priority", "notifications", ["priority"])
    op.create_index("ix_hr_employees_email", "hr_employees", ["email"])
    op.create_index("ix_hr_employees_dept", "hr_employees", ["department"])
    op.create_index("ix_hr_leave_emp", "hr_leave_records", ["employee_id"])
    op.create_index("ix_hr_payroll_emp", "hr_payroll_records", ["employee_id"])
    op.create_index("ix_hr_perf_emp", "hr_performance_reviews", ["employee_id"])


def downgrade() -> None:
    for t, cols in [("users",["username","email","role","is_active"]),
                    ("accounts",["user_id","status"]),
                    ("transactions",["account_id","type"]),
                    ("audit_logs",["user_id","entity_type","created_at"]),
                    ("crm_deals",["contact_id","stage"]),
                    ("inventory_products",["sku","category"]),
                    ("inventory_stock_items",["product_id"]),
                    ("inventory_stock_movements",["product_id","timestamp"]),
                    ("inventory_purchase_order_lines",["po_id"]),
                    ("inventory_sales_order_lines",["so_id"]),
                    ("tasks",["project_id","status","assigned_to"]),
                    ("time_entries",["task_id","user_id"]),
                    ("billing_subscriptions",["customer_id","plan_id","status"]),
                    ("billing_usage_records",["subscription_id"]),
                    ("billing_invoices",["customer_id","status"]),
                    ("billing_payments",["invoice_id","customer_id"]),
                    ("ecommerce_orders",["customer_id","status"]),
                    ("ecommerce_order_items",["order_id"]),
                    ("ecommerce_payments",["order_id"]),
                    ("accounting_accounts",["account_type"]),
                    ("accounting_journal_entries",["date"]),
                    ("accounting_transactions",["journal_entry_id","account_id"]),
                    ("accounting_invoices",["customer_id","status"]),
                    ("accounting_invoice_line_items",["invoice_id"]),
                    ("marketing_campaigns",["status"]),
                    ("marketing_leads",["email","status"]),
                    ("marketing_nurture_steps",["sequence_id"]),
                    ("marketing_lead_enrollments",["lead_id","sequence_id"]),
                    ("marketing_ab_variants",["test_id"]),
                    ("notifications",["status","priority"]),
                    ("hr_employees",["email","department"]),
                    ("hr_leave_records",["employee_id"]),
                    ("hr_payroll_records",["employee_id"]),
                    ("hr_performance_reviews",["employee_id"])]:
        for c in cols:
            op.drop_index(f"ix_{t}_{c}".replace("_entity_type","_entity").replace("_created_at","_created"), table_name=t)
