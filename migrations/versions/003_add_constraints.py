"""Add foreign key constraints.

Revision ID: 003_add_constraints
Revises: 002_add_indexes
Create Date: 2026-10-03 00:02:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_add_constraints"
down_revision: Union[str, None] = "002_add_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key("fk_accounts_user", "accounts", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_transactions_account", "transactions", "accounts", ["account_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_audit_logs_user", "audit_logs", "users", ["user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_crm_deals_contact", "crm_deals", "crm_contacts", ["contact_id"], ["id"])
    op.create_foreign_key("fk_inv_stock_items_product", "inventory_stock_items", "inventory_products", ["product_id"], ["id"])
    op.create_foreign_key("fk_inv_stock_mov_product", "inventory_stock_movements", "inventory_products", ["product_id"], ["id"])
    op.create_foreign_key("fk_inv_po_lines_po", "inventory_purchase_order_lines", "inventory_purchase_orders", ["po_id"], ["id"])
    op.create_foreign_key("fk_inv_po_lines_product", "inventory_purchase_order_lines", "inventory_products", ["product_id"], ["id"])
    op.create_foreign_key("fk_inv_so_lines_so", "inventory_sales_order_lines", "inventory_sales_orders", ["so_id"], ["id"])
    op.create_foreign_key("fk_inv_so_lines_product", "inventory_sales_order_lines", "inventory_products", ["product_id"], ["id"])
    op.create_foreign_key("fk_tasks_project", "tasks", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_time_entries_task", "time_entries", "tasks", ["task_id"], ["id"])
    op.create_foreign_key("fk_billing_subs_plan", "billing_subscriptions", "billing_plans", ["plan_id"], ["id"])
    op.create_foreign_key("fk_billing_usage_sub", "billing_usage_records", "billing_subscriptions", ["subscription_id"], ["id"])
    op.create_foreign_key("fk_billing_inv_lines_inv", "billing_invoice_lines", "billing_invoices", ["invoice_id"], ["id"])
    op.create_foreign_key("fk_billing_payments_inv", "billing_payments", "billing_invoices", ["invoice_id"], ["id"])
    op.create_foreign_key("fk_billing_dunning_inv", "billing_dunning_records", "billing_invoices", ["invoice_id"], ["id"])
    op.create_foreign_key("fk_ecom_orders_customer", "ecommerce_orders", "ecommerce_customers", ["customer_id"], ["id"])
    op.create_foreign_key("fk_ecom_order_items_order", "ecommerce_order_items", "ecommerce_orders", ["order_id"], ["id"])
    op.create_foreign_key("fk_ecom_payments_order", "ecommerce_payments", "ecommerce_orders", ["order_id"], ["id"])
    op.create_foreign_key("fk_acct_accounts_parent", "accounting_accounts", "accounting_accounts", ["parent_id"], ["id"])
    op.create_foreign_key("fk_acct_trans_journal", "accounting_transactions", "accounting_journal_entries", ["journal_entry_id"], ["id"])
    op.create_foreign_key("fk_acct_trans_account", "accounting_transactions", "accounting_accounts", ["account_id"], ["id"])
    op.create_foreign_key("fk_acct_inv_lines_inv", "accounting_invoice_line_items", "accounting_invoices", ["invoice_id"], ["id"])
    op.create_foreign_key("fk_mkt_campaigns_template", "marketing_campaigns", "marketing_email_templates", ["template_id"], ["id"])
    op.create_foreign_key("fk_mkt_nurture_steps_seq", "marketing_nurture_steps", "marketing_nurture_sequences", ["sequence_id"], ["id"])
    op.create_foreign_key("fk_mkt_nurture_steps_tmpl", "marketing_nurture_steps", "marketing_email_templates", ["email_template_id"], ["id"])
    op.create_foreign_key("fk_mkt_enroll_lead", "marketing_lead_enrollments", "marketing_leads", ["lead_id"], ["id"])
    op.create_foreign_key("fk_mkt_enroll_seq", "marketing_lead_enrollments", "marketing_nurture_sequences", ["sequence_id"], ["id"])
    op.create_foreign_key("fk_mkt_ab_variants_test", "marketing_ab_variants", "marketing_ab_tests", ["test_id"], ["id"])
    op.create_foreign_key("fk_hr_leave_emp", "hr_leave_records", "hr_employees", ["employee_id"], ["id"])
    op.create_foreign_key("fk_hr_payroll_emp", "hr_payroll_records", "hr_employees", ["employee_id"], ["id"])
    op.create_foreign_key("fk_hr_perf_emp", "hr_performance_reviews", "hr_employees", ["employee_id"], ["id"])


def downgrade() -> None:
    for fk in ["fk_accounts_user","fk_transactions_account","fk_audit_logs_user",
               "fk_crm_deals_contact","fk_inv_stock_items_product","fk_inv_stock_mov_product",
               "fk_inv_po_lines_po","fk_inv_po_lines_product","fk_inv_so_lines_so",
               "fk_inv_so_lines_product","fk_tasks_project","fk_time_entries_task",
               "fk_billing_subs_plan","fk_billing_usage_sub","fk_billing_inv_lines_inv",
               "fk_billing_payments_inv","fk_billing_dunning_inv","fk_ecom_orders_customer",
               "fk_ecom_order_items_order","fk_ecom_payments_order","fk_acct_accounts_parent",
               "fk_acct_trans_journal","fk_acct_trans_account","fk_acct_inv_lines_inv",
               "fk_mkt_campaigns_template","fk_mkt_nurture_steps_seq","fk_mkt_nurture_steps_tmpl",
               "fk_mkt_enroll_lead","fk_mkt_enroll_seq","fk_mkt_ab_variants_test",
               "fk_hr_leave_emp","fk_hr_payroll_emp","fk_hr_perf_emp"]:
        op.drop_constraint(fk, type_="foreignkey")
