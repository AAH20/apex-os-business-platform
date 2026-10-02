# APEX-OS Business Platform — API Reference

Base URL: `https://api.apex-os.com/v1` | Auth: `Authorization: Bearer <token>`

---

## 1. Authentication

### POST /auth/register
Register a new user account.
```json
// Request
{ "email": "user@example.com", "password": "SecureP@ss123", "first_name": "Jane", "last_name": "Doe", "company": "Acme Corp" }
// Response 201
{ "user_id": "usr_abc123", "email": "user@example.com", "status": "pending_verification", "created_at": "2026-10-02T10:00:00Z" }
```

### POST /auth/login
Authenticate and receive tokens.
```json
// Request
{ "email": "user@example.com", "password": "SecureP@ss123" }
// Response 200
{ "access_token": "eyJhbGciOi...", "refresh_token": "dGhpcyBpcyBh...", "expires_in": 3600, "token_type": "Bearer" }
```

### POST /auth/refresh
Exchange refresh token for new access token.
```json
// Request
{ "refresh_token": "dGhpcyBpcyBh..." }
// Response 200
{ "access_token": "eyJhbGciOi...", "expires_in": 3600 }
```

### POST /auth/logout
Invalidate current access token. **Response:** 204 No Content.

### POST /auth/forgot-password
Request password reset email.
```json
// Request
{ "email": "user@example.com" }
// Response 200
{ "message": "Reset link sent if email exists." }
```

### POST /auth/reset-password
Reset password with token from email.
```json
// Request
{ "token": "reset_tok_xyz", "new_password": "NewP@ss456" }
// Response 200
{ "message": "Password updated successfully." }
```

---

## 2. Accounting

### GET /accounting/transactions
List transactions. Query: `page`, `limit`, `start_date`, `end_date`, `account_id`, `status`
```json
// Response 200
{ "data": [{ "id": "txn_001", "date": "2026-09-15", "description": "Office supplies", "amount": -245.99, "currency": "USD", "account_id": "acc_100", "category": "expense", "status": "cleared" }], "pagination": { "page": 1, "limit": 50, "total": 1240 } }
```

### POST /accounting/transactions
Create a transaction.
```json
// Request
{ "date": "2026-10-01", "description": "Client payment", "amount": 5000.00, "currency": "USD", "account_id": "acc_100", "category": "revenue", "tags": ["invoice-2026-001"] }
// Response 201
{ "id": "txn_002", "status": "pending", "created_at": "2026-10-02T10:05:00Z" }
```

### GET /accounting/transactions/:id
Retrieve a single transaction.
```json
// Response 200
{ "id": "txn_001", "date": "2026-09-15", "description": "Office supplies", "amount": -245.99, "currency": "USD", "account_id": "acc_100", "category": "expense", "status": "cleared", "attachments": ["att_001"] }
```

### PUT /accounting/transactions/:id
Update a transaction.
```json
// Request
{ "description": "Updated description", "amount": -260.00 }
// Response 200
{ "id": "txn_001", "updated_at": "2026-10-02T10:10:00Z" }
```

### DELETE /accounting/transactions/:id
Delete a transaction. **Response:** 204 No Content.

### GET /accounting/accounts
List all accounts.
```json
// Response 200
{ "data": [{ "id": "acc_100", "name": "Operating", "type": "asset", "balance": 45230.50 }] }
```

### GET /accounting/reports/trial-balance
Trial balance report. Query: `as_of`
```json
// Response 200
{ "as_of": "2026-09-30", "debits": 125000.00, "credits": 125000.00, "balanced": true }
```

### GET /accounting/reports/pnl
Profit & Loss. Query: `start_date`, `end_date`
```json
// Response 200
{ "period": { "start": "2026-07-01", "end": "2026-09-30" }, "revenue": 180000.00, "expenses": 95000.00, "net_income": 85000.00 }
```

---

## 3. CRM

### GET /crm/contacts
List contacts. Query: `page`, `limit`, `search`, `tag`, `status`
```json
// Response 200
{ "data": [{ "id": "con_001", "first_name": "Alice", "last_name": "Smith", "email": "alice@client.com", "phone": "+1-555-0100", "company": "ClientCo", "status": "active", "tags": ["vip", "enterprise"] }], "pagination": { "page": 1, "limit": 50, "total": 320 } }
```

### POST /crm/contacts
Create a contact.
```json
// Request
{ "first_name": "Bob", "last_name": "Jones", "email": "bob@prospect.com", "company": "Prospect Inc", "tags": ["lead"] }
// Response 201
{ "id": "con_002", "status": "active", "created_at": "2026-10-02T10:15:00Z" }
```

### GET /crm/contacts/:id
Retrieve a single contact.
```json
// Response 200
{ "id": "con_001", "first_name": "Alice", "last_name": "Smith", "email": "alice@client.com", "deals": ["deal_001"], "notes": ["note_001", "note_002"] }
```

### PUT /crm/contacts/:id
Update a contact.
```json
// Request
{ "status": "inactive", "tags": ["churned"] }
// Response 200
{ "id": "con_001", "updated_at": "2026-10-02T10:20:00Z" }
```

### DELETE /crm/contacts/:id
Delete a contact. **Response:** 204 No Content.

### GET /crm/deals
List deals. Query: `stage`, `owner_id`, `page`, `limit`
```json
// Response 200
{ "data": [{ "id": "deal_001", "title": "Enterprise License", "value": 50000.00, "stage": "negotiation", "contact_id": "con_001", "probability": 0.75 }] }
```

### POST /crm/deals
Create a deal.
```json
// Request
{ "title": "Annual Subscription", "value": 12000.00, "stage": "qualified", "contact_id": "con_002" }
// Response 201
{ "id": "deal_002", "stage": "qualified", "created_at": "2026-10-02T10:25:00Z" }
```

### PUT /crm/deals/:id/stage
Move deal to new stage.
```json
// Request
{ "stage": "closed_won" }
// Response 200
{ "id": "deal_001", "stage": "closed_won", "closed_at": "2026-10-02T10:30:00Z" }
```

### GET /crm/activities
List CRM activities.
```json
// Response 200
{ "data": [{ "id": "act_001", "type": "call", "contact_id": "con_001", "subject": "Follow-up call", "due_date": "2026-10-05", "completed": false }] }
```

### POST /crm/activities
Log an activity.
```json
// Request
{ "type": "email", "contact_id": "con_001", "subject": "Sent proposal", "completed": true }
// Response 201
{ "id": "act_002", "created_at": "2026-10-02T10:35:00Z" }
```

---

## 4. Analytics

### GET /analytics/dashboard
Key performance indicators.
```json
// Response 200
{ "revenue_mtd": 45000.00, "revenue_ytd": 380000.00, "active_customers": 128, "open_deals": 24, "cash_balance": 152000.00, "burn_rate": 12000.00 }
```

### GET /analytics/revenue
Revenue trends. Query: `period` (daily|weekly|monthly), `start_date`, `end_date`
```json
// Response 200
{ "period": "monthly", "data": [{ "month": "2026-07", "revenue": 120000 }, { "month": "2026-08", "revenue": 135000 }, { "month": "2026-09", "revenue": 180000 }] }
```

### GET /analytics/customer-lifetime-value
CLV metrics.
```json
// Response 200
{ "average_clv": 8500.00, "median_clv": 6200.00, "top_10_percent_clv": 22000.00 }
```

### GET /analytics/churn
Churn rate and at-risk customers.
```json
// Response 200
{ "churn_rate": 0.035, "at_risk_count": 12, "at_risk_customers": ["con_010", "con_025"] }
```

### POST /analytics/reports
Generate custom report.
```json
// Request
{ "type": "revenue_by_product", "start_date": "2026-01-01", "end_date": "2026-09-30", "group_by": "product" }
// Response 202
{ "report_id": "rpt_001", "status": "processing", "download_url": null }
```

### GET /analytics/reports/:id
Check report status.
```json
// Response 200
{ "report_id": "rpt_001", "status": "complete", "download_url": "https://api.apex-os.com/v1/analytics/reports/rpt_001/download" }
```

---

## 5. Integration

### GET /integrations
List all integrations.
```json
// Response 200
{ "data": [{ "id": "int_quickbooks", "name": "QuickBooks", "status": "connected" }, { "id": "int_stripe", "name": "Stripe", "status": "connected" }, { "id": "int_slack", "name": "Slack", "status": "available" }] }
```

### POST /integrations/:id/connect
Initiate OAuth flow.
```json
// Request
{ "redirect_uri": "https://app.apex-os.com/callback" }
// Response 200
{ "auth_url": "https://quickbooks.oauth.com/authorize?client_id=...", "state": "csrf_token_xyz" }
```

### POST /integrations/:id/disconnect
Disconnect an integration.
```json
// Response 200
{ "id": "int_slack", "status": "disconnected" }
```

### GET /integrations/:id/sync
Trigger data sync.
```json
// Response 202
{ "sync_id": "sync_001", "status": "in_progress" }
```

### GET /integrations/webhooks
List registered webhooks.
```json
// Response 200
{ "data": [{ "id": "wh_001", "url": "https://app.apex-os.com/hooks/quickbooks", "events": ["transaction.created", "transaction.updated"], "active": true }] }
```

### POST /integrations/webhooks
Register a webhook.
```json
// Request
{ "url": "https://app.apex-os.com/hooks/stripe", "events": ["invoice.paid", "customer.created"], "secret": "whsec_..." }
// Response 201
{ "id": "wh_002", "active": true, "created_at": "2026-10-02T10:40:00Z" }
```

### DELETE /integrations/webhooks/:id
Remove a webhook. **Response:** 204 No Content.

---

## 6. Security

### GET /security/audit-log
Audit trail. Query: `page`, `limit`, `user_id`, `action`, `start_date`, `end_date`
```json
// Response 200
{ "data": [{ "id": "log_001", "user_id": "usr_abc123", "action": "transaction.delete", "resource_id": "txn_001", "ip_address": "192.168.1.1", "timestamp": "2026-10-02T09:00:00Z" }], "pagination": { "page": 1, "limit": 50, "total": 5000 } }
```

### GET /security/sessions
List active sessions.
```json
// Response 200
{ "data": [{ "session_id": "sess_001", "ip_address": "10.0.0.1", "user_agent": "Chrome 128 / macOS", "last_active": "2026-10-02T10:00:00Z", "current": true }] }
```

### DELETE /security/sessions/:id
Revoke a session. **Response:** 204 No Content.

### GET /security/roles
List roles and permissions.
```json
// Response 200
{ "data": [{ "role": "admin", "permissions": ["*"], "user_count": 3 }, { "role": "accountant", "permissions": ["transactions.read", "transactions.write", "reports.read"], "user_count": 8 }] }
```

### POST /security/roles
Create a role.
```json
// Request
{ "name": "sales_manager", "permissions": ["contacts.read", "contacts.write", "deals.read", "deals.write"] }
// Response 201
{ "id": "role_004", "name": "sales_manager", "created_at": "2026-10-02T10:45:00Z" }
```

### PUT /security/roles/:id
Update role permissions.
```json
// Request
{ "permissions": ["contacts.read", "contacts.write", "deals.read", "deals.write", "reports.read"] }
// Response 200
{ "id": "role_004", "updated_at": "2026-10-02T10:50:00Z" }
```

### GET /security/api-keys
List API keys.
```json
// Response 200
{ "data": [{ "id": "key_001", "name": "Production Server", "prefix": "ak_live_...", "last_used": "2026-10-01T15:00:00Z", "created_at": "2026-01-15T08:00:00Z" }] }
```

### POST /security/api-keys
Generate API key.
```json
// Request
{ "name": "CI Pipeline", "expires_in_days": 90 }
// Response 201
{ "id": "key_002", "name": "CI Pipeline", "key": "ak_live_abc123xyz", "expires_at": "2026-12-31T00:00:00Z" }
```

### DELETE /security/api-keys/:id
Revoke API key. **Response:** 204 No Content.

---

## 7. Workflow

### GET /workflows
List all workflows.
```json
// Response 200
{ "data": [{ "id": "wf_001", "name": "Invoice Approval", "status": "active", "trigger": "transaction.created", "steps_count": 3 }] }
```

### POST /workflows
Create a workflow.
```json
// Request
{ "name": "Expense Approval", "trigger": "transaction.created", "conditions": [{ "field": "amount", "operator": "gt", "value": 1000 }], "steps": [{ "order": 1, "type": "approval", "assignee_role": "manager" }, { "order": 2, "type": "notification", "channel": "email" }] }
// Response 201
{ "id": "wf_002", "status": "draft", "created_at": "2026-10-02T10:55:00Z" }
```

### GET /workflows/:id
Retrieve workflow details.
```json
// Response 200
{ "id": "wf_001", "name": "Invoice Approval", "status": "active", "trigger": "transaction.created", "steps": [{ "id": "step_1", "order": 1, "type": "approval", "assignee_role": "manager" }, { "id": "step_2", "order": 2, "type": "notification", "channel": "slack" }] }
```

### PUT /workflows/:id
Update a workflow.
```json
// Request
{ "status": "active" }
// Response 200
{ "id": "wf_002", "status": "active", "updated_at": "2026-10-02T11:00:00Z" }
```

### DELETE /workflows/:id
Delete a workflow. **Response:** 204 No Content.

### GET /workflows/:id/runs
List workflow runs.
```json
// Response 200
{ "data": [{ "run_id": "run_001", "workflow_id": "wf_001", "status": "completed", "started_at": "2026-10-01T09:00:00Z", "completed_at": "2026-10-01T09:05:00Z" }] }
```

### POST /workflows/:id/runs/:runId/retry
Retry a failed run.
```json
// Response 202
{ "run_id": "run_001", "status": "retrying" }
```

### GET /workflows/triggers
List available triggers.
```json
// Response 200
{ "data": [{ "id": "transaction.created", "description": "Fires when a transaction is created" }, { "id": "deal.stage_changed", "description": "Fires when a deal changes stage" }, { "id": "contact.created", "description": "Fires when a new contact is added" }] }
```

---

*Last updated: 2026-10-02*
