"""Seed synthetic data for all modules.

Revision ID: 004_seed_data
Revises: 003_add_constraints
Create Date: 2026-10-03 00:03:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision: str = "004_seed_data"
down_revision: Union[str, None] = "003_add_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.utcnow().isoformat()
    # Users
    op.execute(sa.text(
        "INSERT INTO users (username,email,full_name,role,is_active,created_at,updated_at) VALUES "
        "('admin','admin@apex-os.com','System Admin','ADMIN',1,'"+now+"','"+now+"'),"
        "('manager1','manager@apex-os.com','Manager One','MANAGER',1,'"+now+"','"+now+"'),"
        "('accountant1','accountant@apex-os.com','Accountant One','ACCOUNTANT',1,'"+now+"','"+now+"'),"
        "('viewer1','viewer@apex-os.com','Viewer One','VIEWER',1,'"+now+"','"+now+"')"))
    # Accounts
    op.execute(sa.text(
        "INSERT INTO accounts (user_id,name,account_number,balance,currency,status,created_at,updated_at) VALUES "
        "(1,'Operating Account','ACC-0001',10000.00,'USD','ACTIVE','"+now+"','"+now+"'),"
        "(1,'Savings Account','ACC-0002',50000.00,'USD','ACTIVE','"+now+"','"+now+"'),"
        "(2,'Payroll Account','ACC-0003',25000.00,'USD','ACTIVE','"+now+"','"+now+"')"))
    # Transactions
    op.execute(sa.text(
        "INSERT INTO transactions (account_id,amount,type,description,reference,created_at) VALUES "
        "(1,1000.00,'CREDIT','Initial deposit','REF-001','"+now+"'),"
        "(1,-250.00,'DEBIT','Office supplies','REF-002','"+now+"'),"
        "(2,5000.00,'CREDIT','Transfer from operating','REF-003','"+now+"'),"
        "(3,10000.00,'CREDIT','Payroll funding','REF-004','"+now+"')"))
    # Audit logs
    op.execute(sa.text(
        "INSERT INTO audit_logs (user_id,action,entity_type,entity_id,details,ip_address,created_at) VALUES "
        "(1,'CREATE','user','1','Created admin user','127.0.0.1','"+now+"'),"
        "(1,'UPDATE','account','1','Updated balance','127.0.0.1','"+now+"'),"
        "(2,'CREATE','transaction','1','Initial deposit','127.0.0.1','"+now+"')"))
    # CRM
    op.execute(sa.text(
        "INSERT INTO crm_contacts (id,name,email,phone,company,metadata) VALUES "
        "('c1','John Smith','john@example.com','555-0101','Acme Corp','{}'),"
        "('c2','Jane Doe','jane@example.com','555-0102','Globex','{}'),"
        "('c3','Bob Wilson','bob@example.com','555-0103','Initech','{}')"))
    op.execute(sa.text(
        "INSERT INTO crm_deals (id,title,value,stage,contact_id,metadata) VALUES "
        "('d1','Acme Enterprise Deal',50000.00,'PROPOSAL','c1','{}'),"
        "('d2','Globex License',25000.00,'NEGOTIATION','c2','{}'),"
        "('d3','Initech Pilot',10000.00,'LEAD','c3','{}')"))
    op.execute(sa.text(
        "INSERT INTO crm_pipelines (id,name,deal_ids) VALUES "
        "('p1','Q4 Sales','[\"d1\",\"d2\",\"d3\"]')"))
    # Inventory
    op.execute(sa.text(
        "INSERT INTO inventory_products (id,sku,name,category,unit_price,unit_cost,unit_of_measure,description,reorder_point,reorder_quantity,is_active,created_at,metadata) VALUES "
        "('pr1','SKU-001','Widget A','FINISHED_GOOD',29.99,15.00,'ea','Standard widget',10,50,1,'"+now+"','{}'),"
        "('pr2','SKU-002','Widget B','FINISHED_GOOD',49.99,25.00,'ea','Premium widget',5,25,1,'"+now+"','{}'),"
        "('pr3','SKU-003','Raw Material X','RAW_MATERIAL',5.99,2.50,'kg','Base material',100,500,1,'"+now+"','{}')"))
    op.execute(sa.text(
        "INSERT INTO inventory_stock_items (product_id,location,quantity,reserved_quantity,lot_number,expiry_date,last_updated) VALUES "
        "('pr1','WH-A',100,10,'LOT-001','2027-01-01','"+now+"'),"
        "('pr2','WH-A',50,5,'LOT-002','2027-06-01','"+now+"'),"
        "('pr3','WH-B',1000,0,'LOT-003','2027-12-01','"+now+"')"))
    op.execute(sa.text(
        "INSERT INTO inventory_stock_movements (id,product_id,location,quantity,movement_type,reference,unit_cost,timestamp,notes) VALUES "
        "('sm1','pr1','WH-A',100,'in','PO-001',15.00,'"+now+"','Initial stock'),"
        "('sm2','pr1','WH-A',-10,'out','SO-001',15.00,'"+now+"','Customer order'),"
        "('sm3','pr2','WH-A',50,'in','PO-002',25.00,'"+now+"','Restock')"))
    op.execute(sa.text(
        "INSERT INTO inventory_purchase_orders (id,supplier_id,status,order_date,expected_date,received_date,notes,metadata) VALUES "
        "('po1','sup1','RECEIVED','"+now+"','"+now+"','"+now+"','Initial PO','{}'),"
        "('po2','sup2','PENDING','"+now+"','"+now+"',NULL,'Pending PO','{}')"))
    op.execute(sa.text(
        "INSERT INTO inventory_purchase_order_lines (po_id,product_id,quantity,unit_cost,received_quantity) VALUES "
        "('po1','pr1',100,15.00,100),"
        "('po1','pr3',1000,2.50,1000),"
        "('po2','pr2',50,25.00,0)"))
    op.execute(sa.text(
        "INSERT INTO inventory_sales_orders (id,customer_id,status,order_date,required_date,shipped_date,notes,metadata) VALUES "
        "('so1','c1','SHIPPED','"+now+"','"+now+"','"+now+"','Customer order','{}'),"
        "('so2','c2','DRAFT','"+now+"','"+now+"',NULL,'Draft order','{}')"))
    op.execute(sa.text(
        "INSERT INTO inventory_sales_order_lines (so_id,product_id,quantity,unit_price,fulfilled_quantity) VALUES "
        "('so1','pr1',10,29.99,10),"
        "('so2','pr2',5,49.99,0)"))
    # Projects
    op.execute(sa.text(
        "INSERT INTO projects (id,name,description,start_date,end_date,status,budget,metadata) VALUES "
        "('proj1','Website Redesign','Redesign company website','"+now+"','"+now+"','ACTIVE',50000.00,'{}'),"
        "('proj2','Mobile App','Build mobile application','"+now+"','"+now+"','PLANNING',100000.00,'{}')"))
    op.execute(sa.text(
        "INSERT INTO tasks (id,project_id,name,description,start_date,end_date,duration_days,dependencies,assigned_to,status,priority,completion_percentage,metadata) VALUES "
        "('t1','proj1','Design mockups','Create design mockups','"+now+"','"+now+"',5,NULL,'u1','COMPLETED',3,100.0,'{}'),"
        "('t2','proj1','Frontend dev','Implement frontend','"+now+"','"+now+"',10,'[\"t1\"]','u2','IN_PROGRESS',3,50.0,'{}'),"
        "('t3','proj2','Requirements','Gather requirements','"+now+"','"+now+"',7,NULL,'u1','NOT_STARTED',2,0.0,'{}')"))
    op.execute(sa.text(
        "INSERT INTO resources (id,name,type,capacity,cost_rate,unit,metadata) VALUES "
        "('r1','Developer 1','HUMAN',40.0,75.00,'hour','{}'),"
        "('r2','Designer 1','HUMAN',40.0,65.00,'hour','{}')"))
    op.execute(sa.text(
        "INSERT INTO time_entries (id,task_id,user_id,start_time,end_time,hours,description,billable,metadata) VALUES "
        "('te1','t1','u1','"+now+"','"+now+"',8.0,'Design work',1,'{}'),"
        "('te2','t2','u2','"+now+"','"+now+"',6.0,'Frontend work',1,'{}')"))
    # Billing
    op.execute(sa.text(
        "INSERT INTO billing_plans (id,name,price,currency,billing_cycle,features,usage_limits,overage_rates) VALUES "
        "('plan1','Basic',29.99,'USD','MONTHLY','[\"feature1\",\"feature2\"]','{\"api_calls\":1000}','{\"api_calls\":0.01}'),"
        "('plan2','Pro',99.99,'USD','MONTHLY','[\"feature1\",\"feature2\",\"feature3\"]','{\"api_calls\":10000}','{\"api_calls\":0.005}'),"
        "('plan3','Enterprise',299.99,'USD','MONTHLY','[\"all\"]','{\"api_calls\":100000}','{\"api_calls\":0.001}')"))
    op.execute(sa.text(
        "INSERT INTO billing_subscriptions (id,customer_id,plan_id,status,start_date,end_date,trial_end,auto_renew,metadata) VALUES "
        "('sub1','c1','plan2','ACTIVE','"+now+"','"+now+"',NULL,1,'{}'),"
        "('sub2','c2','plan1','ACTIVE','"+now+"','"+now+"',NULL,1,'{}')"))
    op.execute(sa.text(
        "INSERT INTO billing_usage_records (id,customer_id,subscription_id,metric,quantity,timestamp,metadata) VALUES "
        "('ur1','c1','sub1','api_calls',500,'"+now+"','{}'),"
        "('ur2','c2','sub2','api_calls',200,'"+now+"','{}')"))
    op.execute(sa.text(
        "INSERT INTO billing_invoices (id,customer_id,subscription_id,status,subtotal,tax,total,currency,due_date,paid_at,created_at,metadata) VALUES "
        "('inv1','c1','sub1','PAID',99.99,8.00,107.99,'USD','"+now+"','"+now+"','"+now+"','{}'),"
        "('inv2','c2','sub2','OPEN',29.99,2.40,32.39,'USD','"+now+"',NULL,'"+now+"','{}')"))
    op.execute(sa.text(
        "INSERT INTO billing_invoice_lines (invoice_id,description,quantity,unit_price,amount,metadata) VALUES "
        "('inv1','Pro plan monthly',1,99.99,99.99,'{}'),"
        "('inv2','Basic plan monthly',1,29.99,29.99,'{}')"))
    op.execute(sa.text(
        "INSERT INTO billing_payments (id,invoice_id,customer_id,amount,currency,method,status,transaction_id,failure_reason,created_at,metadata) VALUES "
        "('pay1','inv1','c1',107.99,'USD','CREDIT_CARD','SUCCEEDED','txn-001',NULL,'"+now+"','{}')"))
    op.execute(sa.text(
        "INSERT INTO billing_dunning_records (id,customer_id,invoice_id,subscription_id,status,attempt,max_attempts,actions,created_at,resolved_at,metadata) VALUES "
        "('dr1','c2','inv2','sub2','PENDING',0,3,'[]','"+now+"',NULL,'{}')"))
    # Ecommerce
    op.execute(sa.text(
        "INSERT INTO ecommerce_customers (id,name,email,shipping_address,billing_address) VALUES "
        "('ec1','Alice Brown','alice@example.com','{\"street\":\"123 Main St\",\"city\":\"Springfield\"}','{\"street\":\"123 Main St\",\"city\":\"Springfield\"}'),"
        "('ec2','Charlie Davis','charlie@example.com','{\"street\":\"456 Oak Ave\",\"city\":\"Shelbyville\"}','{\"street\":\"456 Oak Ave\",\"city\":\"Shelbyville\"}')"))
    op.execute(sa.text(
        "INSERT INTO ecommerce_products (id,name,description,price,sku,stock_quantity,category,image_url,is_active,created_at) VALUES "
        "('ep1','Gadget X','A cool gadget',39.99,'GAD-X',50,'Electronics',NULL,1,'"+now+"'),"
        "('ep2','Gadget Y','Another gadget',59.99,'GAD-Y',30,'Electronics',NULL,1,'"+now+"')"))
    op.execute(sa.text(
        "INSERT INTO ecommerce_orders (id,customer_id,status,shipping_address,billing_address,subtotal,tax,shipping_cost,total,payment_id,notes,created_at,updated_at) VALUES "
        "('eo1','ec1','DELIVERED','{\"street\":\"123 Main St\"}','{\"street\":\"123 Main St\"}',39.99,3.20,5.00,48.19,'epay1','Delivered','"+now+"','"+now+"'),"
        "('eo2','ec2','PENDING','{\"street\":\"456 Oak Ave\"}','{\"street\":\"456 Oak Ave\"}',59.99,4.80,5.00,69.79,NULL,NULL,'"+now+"','"+now+"')"))
    op.execute(sa.text(
        "INSERT INTO ecommerce_order_items (order_id,product_id,product_name,quantity,unit_price) VALUES "
        "('eo1','ep1','Gadget X',1,39.99),"
        "('eo2','ep2','Gadget Y',1,59.99)"))
    op.execute(sa.text(
        "INSERT INTO ecommerce_payments (id,order_id,amount,method,status,transaction_id,currency,created_at,updated_at) VALUES "
        "('epay1','eo1',48.19,'CREDIT_CARD','CAPTURED','txn-ecom-001','USD','"+now+"','"+now+"')"))
    # Accounting
    op.execute(sa.text(
        "INSERT INTO accounting_accounts (id,name,account_type,currency,parent_id,is_active) VALUES "
        "('aa1','Cash','ASSET','USD',NULL,1),"
        "('aa2','Accounts Receivable','ASSET','USD',NULL,1),"
        "('aa3','Revenue','REVENUE','USD',NULL,1),"
        "('aa4','Expenses','EXPENSE','USD',NULL,1)"))
    op.execute(sa.text(
        "INSERT INTO accounting_journal_entries (id,date,description,reference) VALUES "
        "('je1','"+now+"','Initial funding','REF-JE-001'),"
        "('je2','"+now+"','Revenue recognition','REF-JE-002')"))
    op.execute(sa.text(
        "INSERT INTO accounting_transactions (id,journal_entry_id,account_id,amount,currency,description,date,reference) VALUES "
        "('at1','je1','aa1',10000.00,'USD','Cash deposit','"+now+"','REF-JE-001'),"
        "('at2','je1','aa3',-10000.00,'USD','Revenue offset','"+now+"','REF-JE-001'),"
        "('at3','je2','aa3',5000.00,'USD','Revenue','"+now+"','REF-JE-002'),"
        "('at4','je2','aa2',-5000.00,'USD','AR offset','"+now+"','REF-JE-002')"))
    op.execute(sa.text(
        "INSERT INTO accounting_invoices (id,customer_id,issue_date,due_date,currency,status,notes) VALUES "
        "('ainv1','c1','"+now+"','"+now+"','USD','paid','Paid invoice'),"
        "('ainv2','c2','"+now+"','"+now+"','USD','sent','Sent invoice')"))
    op.execute(sa.text(
        "INSERT INTO accounting_invoice_line_items (invoice_id,description,quantity,unit_price,currency,discount_percent,tax_rate) VALUES "
        "('ainv1','Consulting services',10,500.00,'USD',0,0.1),"
        "('ainv2','Software license',1,1000.00,'USD',0,0.1)"))
    # Marketing
    op.execute(sa.text(
        "INSERT INTO marketing_email_templates (id,name,subject,body,created_at) VALUES "
        "('et1','Welcome Email','Welcome to APEX-OS','Hello, welcome!','"+now+"'),"
        "('et2','Newsletter','Monthly Newsletter','Here is the news...','"+now+"')"))
    op.execute(sa.text(
        "INSERT INTO marketing_campaigns (id,name,subject,body,status,segments,template_id,metrics,created_at,sent_at,metadata) VALUES "
        "('mc1','Welcome Campaign','Welcome!','Welcome body','SENT','[\"all\"]','et1','{\"sent\":100,\"opened\":80}','"+now+"','"+now+"','{}'),"
        "('mc2','Newsletter Oct','October News','News body','DRAFT','[\"subscribers\"]','et2',NULL,'"+now+"',NULL,'{}')"))
    op.execute(sa.text(
        "INSERT INTO marketing_leads (id,name,email,score,status,source,tags,created_at,last_activity,metadata) VALUES "
        "('ml1','Lead One','lead1@example.com',75.0,'ENGAGED','web','[\"web\",\"campaign\"]','"+now+"','"+now+"','{}'),"
        "('ml2','Lead Two','lead2@example.com',50.0,'NEW','referral','[\"referral\"]','"+now+"',NULL,'{}')"))
    op.execute(sa.text(
        "INSERT INTO marketing_nurture_sequences (id,name,status,created_at,metadata) VALUES "
        "('ns1','Onboarding','active','"+now+"','{}')"))
    op.execute(sa.text(
        "INSERT INTO marketing_nurture_steps (id,sequence_id,email_template_id,delay_days,condition,\"order\") VALUES "
        "('nst1','ns1','et1',0,NULL,1),"
        "('nst2','ns1','et2',7,'opened_email',2)"))
    op.execute(sa.text(
        "INSERT INTO marketing_lead_enrollments (id,lead_id,sequence_id,current_step,status,enrolled_at,last_sent_at) VALUES "
        "('mle1','ml1','ns1',1,'active','"+now+"','"+now+"')"))
    op.execute(sa.text(
        "INSERT INTO marketing_ab_tests (id,name,status,start_date,end_date,winner_variant_id,confidence_level,created_at,metadata) VALUES "
        "('abt1','Subject Line Test','COMPLETED','"+now+"','"+now+"','av1',0.95,'"+now+"','{}')"))
    op.execute(sa.text(
        "INSERT INTO marketing_ab_variants (id,test_id,name,subject,body,metrics,traffic_allocation) VALUES "
        "('av1','abt1','Variant A','Subject A','Body A','{\"sent\":50,\"opened\":30}',0.5),"
        "('av2','abt1','Variant B','Subject B','Body B','{\"sent\":50,\"opened\":25}',0.5)"))
    # Notifications
    op.execute(sa.text(
        "INSERT INTO notifications (id,title,body,channels,recipients,priority,status,template_id,template_data,metadata,created_at,sent_at,delivered_at,error_message,retry_count,max_retries) VALUES "
        "('n1','Welcome','Welcome to the platform','[\"email\"]','[\"user1@example.com\"]','NORMAL','SENT','et1','{}','{}',"+now+","+now+","+now+",NULL,0,3),"
        "('n2','Alert','System alert','[\"email\",\"sms\"]','[\"admin@example.com\"]','HIGH','PENDING',NULL,'{}','{}',"+now+",NULL,NULL,NULL,0,3)"))
    # HR
    op.execute(sa.text(
        "INSERT INTO hr_employees (id,name,email,department,position,salary,hire_date,status,metadata) VALUES "
        "('emp1','John Worker','john@company.com','Engineering','Developer',80000.00,'"+now+"','ACTIVE','{}'),"
        "('emp2','Jane Manager','jane@company.com','Engineering','Manager',120000.00,'"+now+"','ACTIVE','{}')"))
    op.execute(sa.text(
        "INSERT INTO hr_leave_records (id,employee_id,leave_type,start_date,end_date,status,notes) VALUES "
        "('lr1','emp1','VACATION','"+now+"','"+now+"','APPROVED','Annual leave')"))
    op.execute(sa.text(
        "INSERT INTO hr_payroll_records (id,employee_id,period_start,period_end,gross_pay,deductions,net_pay,status,paid_at) VALUES "
        "('pr1','emp1','"+now+"','"+now+"',6666.67,1666.67,5000.00,'PAID','"+now+"'),"
        "('pr2','emp2','"+now+"','"+now+"',10000.00,2500.00,7500.00,'PAID','"+now+"')"))
    op.execute(sa.text(
        "INSERT INTO hr_performance_reviews (id,employee_id,review_period,rating,goals,feedback,reviewer_id,created_at) VALUES "
        "('pfr1','emp1','2026-Q3',4.5,'[\"Improve testing\",\"Learn new framework\"]','Good progress','emp2','"+now+"')"))


def downgrade() -> None:
    for t in ["hr_performance_reviews","hr_payroll_records","hr_leave_records","hr_employees",
              "notifications","marketing_ab_variants","marketing_ab_tests","marketing_lead_enrollments",
              "marketing_nurture_steps","marketing_nurture_sequences","marketing_leads",
              "marketing_campaigns","marketing_email_templates","accounting_invoice_line_items",
              "accounting_invoices","accounting_transactions","accounting_journal_entries",
              "accounting_accounts","ecommerce_payments","ecommerce_order_items","ecommerce_orders",
              "ecommerce_products","ecommerce_customers","billing_dunning_records","billing_payments",
              "billing_invoice_lines","billing_invoices","billing_usage_records","billing_subscriptions",
              "billing_plans","time_entries","resources","tasks","projects",
              "inventory_sales_order_lines","inventory_sales_orders","inventory_purchase_order_lines",
              "inventory_purchase_orders","inventory_stock_movements","inventory_stock_items",
              "inventory_products","crm_pipelines","crm_deals","crm_contacts",
              "audit_logs","transactions","accounts","users"]:
        op.execute(sa.text(f"DELETE FROM {t}"))
