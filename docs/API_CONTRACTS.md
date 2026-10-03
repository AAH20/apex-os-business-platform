# APEX-OS Business Platform — API Contracts

Base URL: `/api/v1`  
Auth: Bearer token (`Authorization: Bearer <token>`)  
Content-Type: `application/json`

---

## Users

### GET /users
List all users (paginated).

**Query:** `page=1&limit=20&role=admin&search=`

**Response (wrapped):**
```json
{ "data": [{ "id": "usr_1", "name": "Jane", "email": "jane@x.com", "role": "admin", "createdAt": "2025-01-01T00:00:00Z" }], "meta": { "page": 1, "limit": 20, "total": 100 } }
```

### POST /users
Create a user.

**Request:**
```json
{ "name": "Jane", "email": "jane@x.com", "role": "admin", "password": "secret" }
```

**Response (wrapped):**
```json
{ "data": { "id": "usr_1", "name": "Jane", "email": "jane@x.com", "role": "admin", "createdAt": "2025-01-01T00:00:00Z" } }
```

### GET /users/:id
**Response (wrapped):** `{ "data": { "id": "usr_1", "name": "Jane", "email": "jane@x.com", "role": "admin" } }`

### PUT /users/:id
**Request:** `{ "name": "Jane Doe", "role": "manager" }`  
**Response (wrapped):** `{ "data": { "id": "usr_1", "name": "Jane Doe", "role": "manager" } }`

### DELETE /users/:id
**Response:** `{ "success": true }`

---

## Leads

### GET /leads
**Query:** `page=1&limit=20&status=new&assignedTo=usr_1`

**Response (wrapped):**
```json
{ "data": [{ "id": "lead_1", "name": "Acme Corp", "email": "info@kc.com", "status": "new", "assignedTo": "usr_1", "createdAt": "2025-01-01T00:00:00Z" }], "meta": { "page": 1, "limit": 20, "total": 50 } }
```

### POST /leads
**Request:**
```json
{ "name": "Acme Corp", "email": "info@kc.com", "phone": "+1234567890", "source": "web", "notes": "Interested in enterprise plan" }
```

**Response (wrapped):**
```json
{ "data": { "id": "lead_1", "name": "Acme Corp", "status": "new", "createdAt": "2025-01-01T00:00:00Z" } }
```

### GET /leads/:id
**Response (wrapped):** `{ "data": { "id": "lead_1", "name": "Acme Corp", "status": "qualified" } }`

### PUT /leads/:id
**Request:** `{ "status": "qualified", "assignedTo": "usr_2" }`  
**Response (wrapped):** `{ "data": { "id": "lead_1", "status": "qualified" } }`

### DELETE /leads/:id
**Response:** `{ "success": true }`

---

## Reports

### GET /reports
**Query:** `page=1&limit=20&type=sales&from=2025-01-01&to=2025-12-31`

**Response (wrapped):**
```json
{ "data": [{ "id": "rpt_1", "type": "sales", "title": "Q1 Sales", "url": "/reports/rpt_1.pdf", "createdAt": "2025-04-01T00:00:00Z" }], "meta": { "page": 1, "limit": 20, "total": 10 } }
```

### POST /reports
**Request:**
```json
{ "type": "sales", "title": "Q1 Sales", "filters": { "from": "2025-01-01", "to": "2025-03-31" } }
```

**Response (wrapped):**
```json
{ "data": { "id": "rpt_1", "type": "sales", "title": "Q1 Sales", "status": "generating" } }
```

### GET /reports/:id
**Response (wrapped):** `{ "data": { "id": "rpt_1", "url": "/reports/rpt_1.pdf", "status": "ready" } }`

### DELETE /reports/:id
**Response:** `{ "success": true }`

---

## Notifications

### GET /notifications
**Query:** `page=1&limit=20&unread=true`

**Response (wrapped):**
```json
{ "data": [{ "id": "ntf_1", "title": "New lead", "message": "Acme Corp signed up", "read": false, "createdAt": "2025-01-01T00:00:00Z" }], "meta": { "page": 1, "limit": 20, "total": 5 } }
```

### POST /notifications
**Request:**
```json
{ "userId": "usr_1", "title": "Alert", "message": "System update at 3pm" }
```

**Response (wrapped):**
```json
{ "data": { "id": "ntf_1", "userId": "usr_1", "title": "Alert", "read": false } }
```

### PUT /notifications/:id/read
**Response (wrapped):** `{ "data": { "id": "ntf_1", "read": true } }`

### DELETE /notifications/:id
**Response:** `{ "success": true }`

---

## Invoices

### GET /invoices
**Query:** `page=1&limit=20&status=paid&customerId=cust_1`

**Response (wrapped):**
```json
{ "data": [{ "id": "inv_1", "customerId": "cust_1", "amount": 1500.00, "status": "paid", "dueDate": "2025-02-01", "createdAt": "2025-01-15T00:00:00Z" }], "meta": { "page": 1, "limit": 20, "total": 30 } }
```

### POST /invoices
**Request:**
```json
{ "customerId": "cust_1", "items": [{ "description": "Consulting", "quantity": 10, "unitPrice": 150 }], "dueDate": "2025-02-01" }
```

**Response (wrapped):**
```json
{ "data": { "id": "inv_1", "customerId": "cust_1", "amount": 1500.00, "status": "draft" } }
```

### GET /invoices/:id
**Response (wrapped):** `{ "data": { "id": "inv_1", "amount": 1500.00, "status": "paid" } }`

### PUT /invoices/:id
**Request:** `{ "status": "sent" }`  
**Response (wrapped):** `{ "data": { "id": "inv_1", "status": "sent" } }`

### DELETE /invoices/:id
**Response:** `{ "success": true }`

---

## Orders

### GET /orders
**Query:** `page=1&limit=20&status=pending`

**Response (wrapped):**
```json
{ "data": [{ "id": "ord_1", "customerId": "cust_1", "total": 2500.00, "status": "pending", "createdAt": "2025-01-01T00:00:00Z" }], "meta": { "page": 1, "limit": 20, "total": 15 } }
```

### POST /orders
**Request:**
```json
{ "customerId": "cust_1", "items": [{ "productId": "prd_1", "quantity": 5, "unitPrice": 500 }] }
```

**Response (wrapped):**
```json
{ "data": { "id": "ord_1", "customerId": "cust_1", "total": 2500.00, "status": "pending" } }
```

### GET /orders/:id
**Response (wrapped):** `{ "data": { "id": "ord_1", "total": 2500.00, "status": "shipped" } }`

### PUT /orders/:id
**Request:** `{ "status": "shipped" }`  
**Response (wrapped):** `{ "data": { "id": "ord_1", "status": "shipped" } }`

### DELETE /orders/:id
**Response:** `{ "success": true }`

---

## Inventory

### GET /inventory
**Query:** `page=1&limit=20&lowStock=true&category=electronics`

**Response (wrapped):**
```json
{ "data": [{ "id": "prd_1", "name": "Widget", "sku": "WID-001", "quantity": 50, "category": "electronics", "price": 29.99 }], "meta": { "page": 1, "limit": 20, "total": 200 } }
```

### POST /inventory
**Request:**
```json
{ "name": "Widget", "sku": "WID-001", "quantity": 100, "category": "electronics", "price": 29.99 }
```

**Response (wrapped):**
```json
{ "data": { "id": "prd_1", "name": "Widget", "sku": "WID-001", "quantity": 100 } }
```

### GET /inventory/:id
**Response (wrapped):** `{ "data": { "id": "prd_1", "name": "Widget", "quantity": 50 } }`

### PUT /inventory/:id
**Request:** `{ "quantity": 75, "price": 24.99 }`  
**Response (wrapped):** `{ "data": { "id": "prd_1", "quantity": 75, "price": 24.99 } }`

### DELETE /inventory/:id
**Response:** `{ "success": true }`

---

## Payments

### GET /payments
**Query:** `page=1&limit=20&status=completed&method=card`

**Response (wrapped):**
```json
{ "data": [{ "id": "pay_1", "invoiceId": "inv_1", "amount": 1500.00, "method": "card", "status": "completed", "createdAt": "2025-01-20T00:00:00Z" }], "meta": { "page": 1, "limit": 20, "total": 45 } }
```

### POST /payments
**Request:**
```json
{ "invoiceId": "inv_1", "amount": 1500.00, "method": "card", "token": "tok_visa" }
```

**Response (wrapped):**
```json
{ "data": { "id": "pay_1", "invoiceId": "inv_1", "amount": 1500.00, "status": "completed" } }
```

### GET /payments/:id
**Response (wrapped):** `{ "data": { "id": "pay_1", "amount": 1500.00, "status": "completed" } }`

### POST /payments/:id/refund
**Request:** `{ "amount": 500.00, "reason": "Customer request" }`  
**Response (wrapped):** `{ "data": { "id": "ref_1", "paymentId": "pay_1", "amount": 500.00, "status": "refunded" } }`

---

## Journal Entries

### GET /journal-entries
**Query:** `page=1&limit=20&account=acc_revenue&from=2025-01-01&to=2025-12-31`

**Response (wrapped):**
```json
{ "data": [{ "id": "je_1", "date": "2025-01-15", "account": "acc_revenue", "debit": 0, "credit": 1500.00, "description": "Invoice inv_1" }], "meta": { "page": 1, "limit": 20, "total": 120 } }
```

### POST /journal-entries
**Request:**
```json
{ "date": "2025-01-15", "entries": [{ "account": "acc_revenue", "debit": 0, "credit": 1500.00 }, { "account": "acc_receivable", "debit": 1500.00, "credit": 0 }], "description": "Invoice inv_1" }
```

**Response (wrapped):**
```json
{ "data": { "id": "je_1", "date": "2025-01-15", "balanced": true } }
```

### GET /journal-entries/:id
**Response (wrapped):** `{ "data": { "id": "je_1", "date": "2025-01-15", "balanced": true } }`

### DELETE /journal-entries/:id
**Response:** `{ "success": true }`

---

## Dashboard

### GET /dashboard
**Query:** `period=30d`

**Response (wrapped):**
```json
{ "data": { "revenue": 150000, "expenses": 80000, "profit": 70000, "activeUsers": 1200, "newLeads": 45, "conversionRate": 12.5, "recentActivity": [{ "type": "sale", "amount": 5000, "timestamp": "2025-01-01T00:00:00Z" }] } }
```

### GET /dashboard/metrics
**Query:** `metric=revenue&from=2025-01-01&to=2025-12-31`

**Response (wrapped):**
```json
{ "data": { "metric": "revenue", "values": [{ "date": "2025-01-01", "value": 5000 }, { "date": "2025-01-02", "value": 7200 }] } }
```

---

## Accounting

### GET /accounting/accounts
**Query:** `page=1&limit=20&type=asset`

**Response (wrapped):**
```json
{ "data": [{ "id": "acc_1", "name": "Cash", "type": "asset", "balance": 50000.00 }], "meta": { "page": 1, "limit": 20, "total": 25 } }
```

### POST /accounting/accounts
**Request:**
```json
{ "name": "Cash", "type": "asset", "description": "Main cash account" }
```

**Response (wrapped):**
```json
{ "data": { "id": "acc_1", "name": "Cash", "type": "asset", "balance": 0 } }
```

### GET /accounting/trial-balance
**Query:** `asOf=2025-01-31`

**Response (wrapped):**
```json
{ "data": { "asOf": "2025-01-31", "accounts": [{ "id": "acc_1", "name": "Cash", "debit": 50000, "credit": 0 }], "totals": { "debit": 100000, "credit": 100000 } } }
```

### GET /accounting/ledger/:accountId
**Query:** `page=1&limit=20&from=2025-01-01&to=2025-12-31`

**Response (wrapped):**
```json
{ "data": [{ "id": "je_1", "date": "2025-01-15", "debit": 0, "credit": 1500.00, "description": "Invoice inv_1" }], "meta": { "page": 1, "limit": 20, "total": 30 } }
```

---

## CRM

### GET /crm/contacts
**Query:** `page=1&limit=20&company=Acme`

**Response (wrapped):**
```json
{ "data": [{ "id": "con_1", "name": "John Smith", "email": "john@acme.com", "company": "Acme Corp", "phone": "+1234567890" }], "meta": { "page": 1, "limit": 20, "total": 80 } }
```

### POST /crm/contacts
**Request:**
```json
{ "name": "John Smith", "email": "john@acme.com", "company": "Acme Corp", "phone": "+1234567890" }
```

**Response (wrapped):**
```json
{ "data": { "id": "con_1", "name": "John Smith", "email": "john@acme.com" } }
```

### GET /crm/contacts/:id
**Response (wrapped):** `{ "data": { "id": "con_1", "name": "John Smith", "company": "Acme Corp" } }`

### PUT /crm/contacts/:id
**Request:** `{ "phone": "+0987654321" }`  
**Response (wrapped):** `{ "data": { "id": "con_1", "phone": "+0987654321" } }`

### DELETE /crm/contacts/:id
**Response:** `{ "success": true }`

### GET /crm/deals
**Query:** `page=1&limit=20&stage=negotiation`

**Response (wrapped):**
```json
{ "data": [{ "id": "deal_1", "title": "Acme Enterprise", "value": 50000, "stage": "negotiation", "contactId": "con_1" }], "meta": { "page": 1, "limit": 20, "total": 12 } }
```

### POST /crm/deals
**Request:**
```json
{ "title": "Acme Enterprise", "value": 50000, "stage": "prospecting", "contactId": "con_1" }
```

**Response (wrapped):**
```json
{ "data": { "id": "deal_1", "title": "Acme Enterprise", "value": 50000, "stage": "prospecting" } }
```

### PUT /crm/deals/:id
**Request:** `{ "stage": "won" }`  
**Response (wrapped):** `{ "data": { "id": "deal_1", "stage": "won" } }`

### DELETE /crm/deals/:id
**Response:** `{ "success": true }`

---

## Analytics

### GET /analytics/summary
**Query:** `period=30d&metrics=revenue,users,conversion`

**Response (wrapped):**
```json
{ "data": { "revenue": 150000, "users": 1200, "conversion": 12.5, "period": "30d" } }
```

### GET /analytics/trends
**Query:** `metric=revenue&interval=daily&from=2025-01-01&to=2025-01-31`

**Response (wrapped):**
```json
{ "data": { "metric": "revenue", "interval": "daily", "points": [{ "date": "2025-01-01", "value": 5000 }] } }
```

### GET /analytics/funnel
**Query:** `from=2025-01-01&to=2025-12-31`

**Response (wrapped):**
```json
{ "data": { "stages": [{ "name": "visit", "count": 10000 }, { "name": "signup", "count": 2000 }, { "name": "purchase", "count": 500 }] } }
```

---

## Agent Reach

### GET /agent-reach/campaigns
**Query:** `page=1&limit=20&status=active`

**Response (wrapped):**
```json
{ "data": [{ "id": "cmp_1", "name": "Q1 Outreach", "status": "active", "sentCount": 5000, "openRate": 45.2 }], "meta": { "page": 1, "limit": 20, "total": 8 } }
```

### POST /agent-reach/campaigns
**Request:**
```json
{ "name": "Q1 Outreach", "template": "Hello {{name}}, ...", "audience": { "segment": "enterprise" } }
```

**Response (wrapped):**
```json
{ "data": { "id": "cmp_1", "name": "Q1 Outreach", "status": "draft" } }
```

### GET /agent-reach/campaigns/:id
**Response (wrapped):** `{ "data": { "id": "cmp_1", "name": "Q1 Outreach", "status": "active" } }`

### POST /agent-reach/campaigns/:id/send
**Response (wrapped):** `{ "data": { "id": "cmp_1", "status": "sending" } }`

### DELETE /agent-reach/campaigns/:id
**Response:** `{ "success": true }`

---

## BigData

### GET /bigdata/jobs
**Query:** `page=1&limit=20&status=running`

**Response (wrapped):**
```json
{ "data": [{ "id": "job_1", "name": "Daily ETL", "status": "running", "progress": 65, "startedAt": "2025-01-01T00:00:00Z" }], "meta": { "page": 1, "limit": 20, "total": 5 } }
```

### POST /bigdata/jobs
**Request:**
```json
{ "name": "Daily ETL", "source": "s3://bucket/data", "destination": "warehouse.daily", "schedule": "0 2 * * *" }
```

**Response (wrapped):**
```json
{ "data": { "id": "job_1", "name": "Daily ETL", "status": "queued" } }
```

### GET /bigdata/jobs/:id
**Response (wrapped):** `{ "data": { "id": "job_1", "status": "completed", "progress": 100 } }`

### DELETE /bigdata/jobs/:id
**Response:** `{ "success": true }`

---

## DataScience

### GET /datascience/models
**Query:** `page=1&limit=20&status=deployed`

**Response (wrapped):**
```json
{ "data": [{ "id": "mdl_1", "name": "Churn Predictor", "type": "classification", "status": "deployed", "accuracy": 0.89 }], "meta": { "page": 1, "limit": 20, "total": 6 } }
```

### POST /datascience/models
**Request:**
```json
{ "name": "Churn Predictor", "type": "classification", "datasetId": "ds_1", "hyperparams": { "maxDepth": 10 } }
```

**Response (wrapped):**
```json
{ "data": { "id": "mdl_1", "name": "Churn Predictor", "status": "training" } }
```

### GET /datascience/models/:id
**Response (wrapped):** `{ "data": { "id": "mdl_1", "name": "Churn Predictor", "status": "deployed", "accuracy": 0.89 } }`

### POST /datascience/models/:id/predict
**Request:**
```json
{ "input": { "age": 35, "tenure": 24, "monthlySpend": 120 } }
```

**Response (wrapped):**
```json
{ "data": { "prediction": "churn", "probability": 0.78 } }
```

### DELETE /datascience/models/:id
**Response:** `{ "success": true }`

---

## Continuous BI

### GET /continuous-bi/streams
**Query:** `page=1&limit=20&status=active`

**Response (wrapped):**
```json
{ "data": [{ "id": "str_1", "name": "Sales Stream", "status": "active", "throughput": 1200 }], "meta": { "page": 1, "limit": 20, "total": 4 } }
```

### POST /continuous-bi/streams
**Request:**
```json
{ "name": "Sales Stream", "source": "kafka://sales-topic", "transform": "aggregate_by_minute" }
```

**Response (wrapped):**
```json
{ "data": { "id": "str_1", "name": "Sales Stream", "status": "active" } }
```

### GET /continuous-bi/streams/:id
**Response (wrapped):** `{ "data": { "id": "str_1", "name": "Sales Stream", "status": "active" } }`

### GET /continuous-bi/streams/:id/metrics
**Response (wrapped):**
```json
{ "data": { "throughput": 1200, "latency": 45, "errorRate": 0.01 } }
```

### DELETE /continuous-bi/streams/:id
**Response:** `{ "success": true }`

---

## Error Codes

| Code | HTTP | Message |
|------|------|---------|
| `VALIDATION_ERROR` | 400 | Invalid request body or parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists or state conflict |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |

**Error Response Format:**
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Email is required", "details": [{ "field": "email", "message": "Required" }] } }
```

---

## Pagination

All list endpoints support:
- `page` (default: 1)
- `limit` (default: 20, max: 100)

Response includes `meta`: `{ "page": 1, "limit": 20, "total": 100 }`
