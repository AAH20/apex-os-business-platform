# APEX-OS Business Platform — Database Schema

## 1. Database Schema

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1e1e2e','primaryTextColor':'#cdd6f4','primaryBorderColor':'#89b4fa','lineColor':'#cdd6f4','secondaryColor':'#313244','tertiaryColor':'#45475a','background':'#11111b','mainBkg':'#1e1e2e','secondBkg':'#313244','tertiaryBkg':'#45475a','textColor':'#cdd6f4','fontSize':'14px'}}}%%
erDiagram
    USERS ||--o{ ORG_MEMBERSHIPS : has
    ORGANIZATIONS ||--o{ ORG_MEMBERSHIPS : has
    ORGANIZATIONS ||--o{ PRODUCTS : owns
    ORGANIZATIONS ||--o{ ORDERS : places
    ORGANIZATIONS ||--o{ INVOICES : billed
    ORGANIZATIONS ||--o{ PAYMENTS : receives
    ORGANIZATIONS ||--o{ CUSTOMERS : manages
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--|{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : included_in
    ORDERS ||--o| INVOICES : generates
    INVOICES ||--o{ PAYMENTS : settled_by
    PRODUCTS ||--o{ INVENTORY_LOGS : tracks
    USERS ||--o{ AUDIT_LOGS : creates
    ORGANIZATIONS ||--o{ AUDIT_LOGS : scoped_to

    USERS {
        uuid id PK
        varchar email UK
        varchar password_hash
        varchar full_name
        varchar role
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    ORGANIZATIONS {
        uuid id PK
        varchar name UK
        varchar slug UK
        varchar plan
        varchar status
        timestamp created_at
        timestamp updated_at
    }
    ORG_MEMBERSHIPS {
        uuid id PK
        uuid user_id FK
        uuid org_id FK
        varchar role
        timestamp joined_at
    }
    CUSTOMERS {
        uuid id PK
        uuid org_id FK
        varchar name
        varchar email
        varchar phone
        text address
        timestamp created_at
    }
    PRODUCTS {
        uuid id PK
        uuid org_id FK
        varchar sku UK
        varchar name
        text description
        numeric price
        integer stock_quantity
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    ORDERS {
        uuid id PK
        uuid org_id FK
        uuid customer_id FK
        varchar status
        numeric total_amount
        timestamp created_at
        timestamp updated_at
    }
    ORDER_ITEMS {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        integer quantity
        numeric unit_price
        numeric subtotal
    }
    INVOICES {
        uuid id PK
        uuid org_id FK
        uuid order_id FK
        varchar invoice_number UK
        varchar status
        numeric amount_due
        numeric amount_paid
        date due_date
        timestamp created_at
    }
    PAYMENTS {
        uuid id PK
        uuid invoice_id FK
        uuid org_id FK
        numeric amount
        varchar method
        varchar status
        varchar transaction_ref
        timestamp paid_at
    }
    INVENTORY_LOGS {
        uuid id PK
        uuid product_id FK
        uuid org_id FK
        integer quantity_change
        varchar reason
        timestamp created_at
    }
    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        uuid org_id FK
        varchar action
        varchar entity_type
        uuid entity_id
        jsonb metadata
        timestamp created_at
    }
```

## 2. Table Relationships

| Relationship | Type | Description |
|---|---|---|
| USERS ↔ ORGANIZATIONS | Many-to-Many | Via ORG_MEMBERSHIPS; a user can belong to multiple orgs |
| ORGANIZATIONS → PRODUCTS | One-to-Many | Each product belongs to one org |
| ORGANIZATIONS → CUSTOMERS | One-to-Many | Customers are scoped per org |
| ORGANIZATIONS → ORDERS | One-to-Many | Orders are placed within an org |
| CUSTOMERS → ORDERS | One-to-Many | A customer can have many orders |
| ORDERS → ORDER_ITEMS | One-to-Many | Each order has multiple line items |
| PRODUCTS → ORDER_ITEMS | One-to-Many | A product appears in many order items |
| ORDERS → INVOICES | One-to-One | Each order generates at most one invoice |
| INVOICES → PAYMENTS | One-to-Many | An invoice can have multiple partial payments |
| PRODUCTS → INVENTORY_LOGS | One-to-Many | Stock movement history per product |
| USERS → AUDIT_LOGS | One-to-Many | Audit trail per user action |
| ORGANIZATIONS → AUDIT_LOGS | One-to-Many | Audit trail scoped per org |

## 3. Indexing Strategy

| Table | Index | Columns | Purpose |
|---|---|---|---|
| USERS | idx_users_email | email | Login lookup |
| ORGANIZATIONS | idx_org_slug | slug | Public-facing org pages |
| ORG_MEMBERSHIPS | idx_orgmem_user | user_id | List user's orgs |
| ORG_MEMBERSHIPS | idx_orgmem_org | org_id | List org members |
| CUSTOMERS | idx_customers_org | org_id | Filter customers by org |
| CUSTOMERS | idx_customers_email | org_id, email | Unique email per org |
| PRODUCTS | idx_products_org | org_id | List org products |
| PRODUCTS | idx_products_sku | org_id, sku | SKU lookup per org |
| ORDERS | idx_orders_org | org_id | List org orders |
| ORDERS | idx_orders_customer | customer_id | Customer order history |
| ORDERS | idx_orders_status | org_id, status | Filter by status |
| ORDER_ITEMS | idx_orderitems_order | order_id | Fetch order line items |
| INVOICES | idx_invoices_org | org_id | List org invoices |
| INVOICES | idx_invoices_status | org_id, status | Filter by status |
| PAYMENTS | idx_payments_invoice | invoice_id | Payments per invoice |
| INVENTORY_LOGS | idx_invlog_product | product_id | Stock history per product |
| AUDIT_LOGS | idx_audit_org | org_id | Audit trail per org |
| AUDIT_LOGS | idx_audit_entity | entity_type, entity_id | Entity audit lookup |

**Additional Notes:**
- All primary keys are UUID v7 (time-ordered) for index locality.
- Foreign keys are indexed by default; composite indexes follow leftmost-prefix rule.
- Partial indexes on `is_active = true` for USERS and PRODUCTS.
- GIN index on `AUDIT_LOGS.metadata` (jsonb) for flexible querying.

## 4. Partitioning Strategy

| Table | Partition Key | Strategy | Rationale |
|---|---|---|---|
| ORDERS | created_at | RANGE (monthly) | High write volume; time-based queries |
| ORDER_ITEMS | order_id | REFERENCE (via ORDERS) | Cascade partition with parent |
| INVOICES | created_at | RANGE (monthly) | Time-series billing data |
| PAYMENTS | paid_at | RANGE (monthly) | High-volume transactional data |
| INVENTORY_LOGS | created_at | RANGE (monthly) | Append-only log; archival candidate |
| AUDIT_LOGS | created_at | RANGE (monthly) | Compliance retention; time-scoped queries |

**Partition Management:**
- Monthly partitions created 3 months ahead via pg_cron job.
- Partitions older than 24 months moved to cold storage (S3) and detached.
- Hot partitions remain on SSD-backed tablespaces.
- Archive partitions compressed with ZFS gzip-9.

## 5. Backup Strategy

| Layer | Method | Frequency | Retention |
|---|---|---|---|
| WAL Archiving | Continuous (archive_command) | Real-time | 7 days |
| Full Backup | pg_basebackup | Daily (02:00 UTC) | 30 days |
| Incremental | pgBackRest delta | Every 6 hours | 14 days |
| Logical Dump | pg_dump (schema + data) | Weekly (Sunday) | 90 days |
| Cross-Region | Replica to secondary region | Continuous | N/A |
| Point-in-Time | PITR via WAL replay | On-demand | 35 days |

**Recovery Objectives:**
- **RPO:** ≤ 5 minutes (WAL streaming)
- **RTO:** ≤ 30 minutes (automated failover to standby)

**Backup Verification:**
- Weekly automated restore to staging cluster.
- Monthly disaster recovery drill with full PITR test.
- Checksum validation on all backup files.
- Encryption at rest (AES-256) and in transit (TLS 1.3).
