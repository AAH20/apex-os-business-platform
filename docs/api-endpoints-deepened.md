# APEX-OS Business Platform — Deepened API Endpoints

## 1. Accounting

### 1.1 Multi-Currency

#### POST /api/v1/accounting/multi-currency/rates
Get exchange rates for currency pairs.
- **Request:** `{ "base": "USD", "targets": ["EUR", "GBP"], "date": "2026-10-03" }`
- **Response:** `{ "base": "USD", "rates": { "EUR": 0.92, "GBP": 0.79 }, "date": "2026-10-03" }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/accounting/multi-currency/rates -d '{"base":"USD","targets":["EUR"]}'`

#### POST /api/v1/accounting/multi-currency/convert
Convert amount between currencies.
- **Request:** `{ "amount": 1000, "from": "USD", "to": "EUR" }`
- **Response:** `{ "amount": 920.00, "from": "USD", "to": "EUR", "rate": 0.92 }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/accounting/multi-currency/convert -d '{"amount":1000,"from":"USD","to":"EUR"}'`

#### GET /api/v1/accounting/multi-currency/revaluations
List pending currency revaluations.
- **Request:** —
- **Response:** `{ "revaluations": [{ "id": "rev_001", "currency": "EUR", "gain_loss": -120.50 }] }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/accounting/multi-currency/revaluations`

### 1.2 Recurring Entries

#### POST /api/v1/accounting/recurring-entries
Create a recurring journal entry.
- **Request:** `{ "description": "Monthly rent", "amount": 5000, "currency": "USD", "frequency": "monthly", "start_date": "2026-10-01", "end_date": "2027-09-30", "accounts": { "debit": "6000", "credit": "1000" } }`
- **Response:** `{ "id": "re_001", "status": "active", "next_run": "2026-11-01" }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/accounting/recurring-entries -d '{"description":"Rent","amount":5000,"frequency":"monthly"}'`

#### GET /api/v1/accounting/recurring-entries
List all recurring entries.
- **Request:** —
- **Response:** `{ "entries": [{ "id": "re_001", "description": "Monthly rent", "status": "active" }] }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/accounting/recurring-entries`

### 1.3 Financial Statements

#### POST /api/v1/accounting/financial-statements/balance-sheet
Generate balance sheet.
- **Request:** `{ "as_of": "2026-09-30", "currency": "USD" }`
- **Response:** `{ "assets": 150000, "liabilities": 60000, "equity": 90000, "as_of": "2026-09-30" }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/accounting/financial-statements/balance-sheet -d '{"as_of":"2026-09-30"}'`

#### POST /api/v1/accounting/financial-statements/income-statement
Generate income statement.
- **Request:** `{ "period_start": "2026-07-01", "period_end": "2026-09-30" }`
- **Response:** `{ "revenue": 200000, "expenses": 140000, "net_income": 60000 }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/accounting/financial-statements/income-statement -d '{"period_start":"2026-07-01","period_end":"2026-09-30"}'`

### 1.4 Budget

#### POST /api/v1/accounting/budget
Create a budget.
- **Request:** `{ "name": "Q4 2026", "period": "2026-10-01/2026-12-31", "lines": [{ "account": "6000", "amount": 50000 }] }`
- **Response:** `{ "id": "bud_001", "name": "Q4 2026", "total": 50000 }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/accounting/budget -d '{"name":"Q4","lines":[{"account":"6000","amount":50000}]}'`

#### GET /api/v1/accounting/budget/actuals-vs-budget
Compare actuals to budget.
- **Request:** —
- **Response:** `{ "budget_id": "bud_001", "actual": 42000, "variance": -8000, "pct_used": 84 }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/accounting/budget/actuals-vs-budget`

### 1.5 Tax

#### POST /api/v1/accounting/tax/calculate
Calculate tax liability.
- **Request:** `{ "jurisdiction": "US-FED", "income": 120000, "filing_status": "single", "deductions": 13850 }`
- **Response:** `{ "taxable_income": 106150, "liability": 18248, "effective_rate": 15.2 }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/accounting/tax/calculate -d '{"jurisdiction":"US-FED","income":120000}'`

#### GET /api/v1/accounting/tax/rates
Get tax rates for jurisdiction.
- **Request:** —
- **Response:** `{ "jurisdiction": "US-FED", "brackets": [{ "min": 0, "rate": 0.10 }, { "min": 11600, "rate": 0.12 }] }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/accounting/tax/rates?jurisdiction=US-FED`

#### POST /api/v1/accounting/tax/filing
Submit tax filing.
- **Request:** `{ "jurisdiction": "US-FED", "tax_year": 2025, "return_data": { "income": 120000, "withheld": 20000 } }`
- **Response:** `{ "filing_id": "fil_001", "status": "submitted", "refund_due": 1752 }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/accounting/tax/filing -d '{"jurisdiction":"US-FED","tax_year":2025}'`

---

## 2. CRM

### 2.1 Lead Scoring

#### POST /api/v1/crm/leads/score
Score a lead.
- **Request:** `{ "lead_id": "lead_001", "signals": { "email_opens": 5, "site_visits": 12, "form_submissions": 2 } }`
- **Response:** `{ "lead_id": "lead_001", "score": 78, "grade": "A", "factors": [{ "signal": "email_opens", "weight": 0.3, "contribution": 15 }] }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/crm/leads/score -d '{"lead_id":"lead_001","signals":{"email_opens":5}}'`

#### GET /api/v1/crm/leads/scores
Get scores for all leads.
- **Request:** —
- **Response:** `{ "scores": [{ "lead_id": "lead_001", "score": 78, "grade": "A" }] }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/crm/leads/scores`

### 2.2 Pipeline

#### POST /api/v1/crm/pipeline
Create pipeline stage.
- **Request:** `{ "name": "Negotiation", "order": 4, "probability": 0.75 }`
- **Response:** `{ "id": "stage_004", "name": "Negotiation", "order": 4 }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/crm/pipeline -d '{"name":"Negotiation","order":4}'`

#### GET /api/v1/crm/pipeline
Get full pipeline with deals.
- **Request:** —
- **Response:** `{ "stages": [{ "id": "stage_001", "name": "Prospecting", "deals": [{ "id": "deal_001", "value": 25000 }] }] }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/crm/pipeline`

### 2.3 Email Tracking

#### POST /api/v1/crm/email-tracking/open
Track email open event.
- **Request:** `{ "email_id": "em_001", "lead_id": "lead_001", "timestamp": "2026-10-03T10:00:00Z" }`
- **Response:** `{ "tracked": true, "email_id": "em_001" }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/crm/email-tracking/open -d '{"email_id":"em_001","lead_id":"lead_001"}'`

#### POST /api/v1/crm/email-tracking/click
Track email link click.
- **Request:** `{ "email_id": "em_001", "lead_id": "lead_001", "url": "https://example.com/pricing" }`
- **Response:** `{ "tracked": true, "email_id": "em_001" }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/crm/email-tracking/click -d '{"email_id":"em_001","url":"https://example.com"}'`

### 2.4 Segmentation

#### POST /api/v1/crm/segments
Create a dynamic segment.
- **Request:** `{ "name": "High-Value Prospects", "criteria": { "field": "lifetime_value", "operator": "gt", "value": 10000 } }`
- **Response:** `{ "id": "seg_001", "name": "High-Value Prospects", "member_count": 342 }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/crm/segments -d '{"name":"High-Value","criteria":{"field":"ltv","operator":"gt","value":10000}}'`

#### GET /api/v1/crm/segments/{id}/members
Get members of a segment.
- **Request:** —
- **Response:** `{ "segment_id": "seg_001", "members": [{ "lead_id": "lead_001", "name": "Acme Corp" }] }`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v1/crm/segments/seg_001/members`

### 2.5 Churn

#### GET /api/v1/crm/churn/predict
Predict churn probability for a customer.
- **Request:** —
- **Response:** `{ "customer_id": "cust_001", "churn_probability": 0.23, "risk_level": "low", "factors": [{ "factor": "support_tickets", "impact": -0.05 }] }`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v1/crm/churn/predict?customer_id=cust_001`

#### POST /api/v1/crm/churn/risk-scores
Batch churn risk scoring.
- **Request:** `{ "customer_ids": ["cust_001", "cust_002"] }`
- **Response:** `{ "scores": [{ "customer_id": "cust_001", "risk": 0.23 }, { "customer_id": "cust_002", "risk": 0.67 }] }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/crm/churn/risk-scores -d '{"customer_ids":["cust_001","cust_002"]}'`

---

## 3. Analytics

### 3.1 Cohort Analysis

#### POST /api/v1/analytics/cohorts
Create cohort analysis.
- **Request:** `{ "cohort_field": "signup_month", "metric": "retention", "periods": [1, 3, 6, 12] }`
- **Response:** `{ "id": "coh_001", "cohorts": [{ "cohort": "2026-01", "size": 500, "retention": { "1": 0.85, "3": 0.62, "6": 0.41 } }] }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/analytics/cohorts -d '{"cohort_field":"signup_month","metric":"retention"}'`

#### GET /api/v1/analytics/cohorts/{id}
Get cohort analysis results.
- **Request:** —
- **Response:** `{ "id": "coh_001", "cohorts": [{ "cohort": "2026-01", "retention": { "1": 0.85 } }] }`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v1/analytics/cohorts/coh_001`

### 3.2 Funnel Analysis

#### POST /api/v1/analytics/funnels
Create funnel analysis.
- **Request:** `{ "name": "Signup Flow", "steps": ["landing", "register", "activate", "purchase"] }`
- **Response:** `{ "id": "fun_001", "steps": [{ "step": "landing", "count": 10000, "conversion": 1.0 }, { "step": "register", "count": 3000, "conversion": 0.30 }] }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/analytics/funnels -d '{"name":"Signup","steps":["landing","register","purchase"]}'`

#### GET /api/v1/analytics/funnels/{id}
Get funnel results.
- **Request:** —
- **Response:** `{ "id": "fun_001", "steps": [{ "step": "landing", "count": 10000 }] }`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v1/analytics/funnels/fun_001`

### 3.3 Forecasting

#### POST /api/v1/analytics/forecasting
Generate a forecast.
- **Request:** `{ "metric": "revenue", "horizon": 90, "interval": "day", "method": "arima" }`
- **Response:** `{ "id": "fc_001", "forecast": [{ "date": "2026-10-04", "value": 15200, "lower": 14800, "upper": 15600 }] }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/analytics/forecasting -d '{"metric":"revenue","horizon":90}'`

#### GET /api/v1/analytics/forecasting/{id}
Get forecast results.
- **Request:** —
- **Response:** `{ "id": "fc_001", "forecast": [{ "date": "2026-10-04", "value": 15200 }] }`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v1/analytics/forecasting/fc_001`

### 3.4 Anomaly Detection

#### POST /api/v1/analytics/anomaly-detection
Run anomaly detection.
- **Request:** `{ "metric": "api_latency", "sensitivity": 0.95, "window": "7d" }`
- **Response:** `{ "id": "ano_001", "anomalies": [{ "timestamp": "2026-10-02T14:00:00Z", "value": 2500, "expected": 450, "severity": "high" }] }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/analytics/anomaly-detection -d '{"metric":"api_latency","sensitivity":0.95}'`

#### GET /api/v1/analytics/anomalies
List detected anomalies.
- **Request:** —
- **Response:** `{ "anomalies": [{ "id": "ano_001", "metric": "api_latency", "severity": "high" }] }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/analytics/anomalies`

### 3.5 Correlation

#### POST /api/v1/analytics/correlation
Run correlation analysis.
- **Request:** `{ "metrics": ["marketing_spend", "revenue"], "period": "2026-01-01/2026-09-30" }`
- **Response:** `{ "id": "cor_001", "correlations": [{ "pair": ["marketing_spend", "revenue"], "coefficient": 0.87, "p_value": 0.001 }] }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/analytics/correlation -d '{"metrics":["marketing_spend","revenue"]}'`

#### GET /api/v1/analytics/correlation/{id}
Get correlation results.
- **Request:** —
- **Response:** `{ "id": "cor_001", "correlations": [{ "pair": ["marketing_spend", "revenue"], "coefficient": 0.87 }] }`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v1/analytics/correlation/cor_001`

---

## 4. Security

### 4.1 JWT

#### POST /api/v1/security/jwt/issue
Issue a JWT token.
- **Request:** `{ "sub": "user_001", "roles": ["admin"], "ttl": 3600 }`
- **Response:** `{ "token": "eyJhbGciOi...", "expires_in": 3600, "token_type": "Bearer" }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/security/jwt/issue -d '{"sub":"user_001","roles":["admin"]}'`

#### POST /api/v1/security/jwt/refresh
Refresh a JWT token.
- **Request:** `{ "refresh_token": "rt_abc123" }`
- **Response:** `{ "token": "eyJhbGciOi...", "expires_in": 3600 }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/security/jwt/refresh -d '{"refresh_token":"rt_abc123"}'`

### 4.2 OAuth2

#### POST /api/v1/security/oauth2/token
OAuth2 token endpoint.
- **Request:** `{ "grant_type": "authorization_code", "code": "ac_123", "redirect_uri": "https://app.example.com/callback" }`
- **Response:** `{ "access_token": "eyJhbGciOi...", "token_type": "Bearer", "expires_in": 3600, "refresh_token": "rt_abc123" }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/security/oauth2/token -d '{"grant_type":"authorization_code","code":"ac_123"}'`

#### POST /api/v1/security/oauth2/authorize
OAuth2 authorization endpoint.
- **Request:** `{ "client_id": "app_001", "redirect_uri": "https://app.example.com/callback", "scope": "read write", "state": "xyz" }`
- **Response:** `{ "code": "ac_123", "state": "xyz" }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/security/oauth2/authorize -d '{"client_id":"app_001","scope":"read"}'`

### 4.3 SAML

#### POST /api/v1/security/saml/acs
SAML Assertion Consumer Service.
- **Request:** `{ "SAMLResponse": "PHNhbWxw...", "RelayState": "/dashboard" }`
- **Response:** `{ "redirect": "/dashboard", "session_id": "sess_001" }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/security/saml/acs -d '{"SAMLResponse":"PHNhbWxw..."}'`

#### GET /api/v1/security/saml/metadata
SAML service provider metadata.
- **Request:** —
- **Response:** `{ "entity_id": "https://api.example.com/saml", "acs_url": "https://api.example.com/api/v1/security/saml/acs", "certificate": "MIIC..." }`
- **Status:** 200
- **Example:** `curl /api/v1/security/saml/metadata`

### 4.4 ABAC

#### POST /api/v1/security/abac/policies
Create ABAC policy.
- **Request:** `{ "name": "Finance Admin", "subject": { "role": "admin" }, "resource": { "type": "report" }, "action": "read", "conditions": { "department": "finance" } }`
- **Response:** `{ "id": "pol_001", "name": "Finance Admin", "effect": "allow" }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/security/abac/policies -d '{"name":"Finance Admin","subject":{"role":"admin"}}'`

#### GET /api/v1/security/abac/policies
List ABAC policies.
- **Request:** —
- **Response:** `{ "policies": [{ "id": "pol_001", "name": "Finance Admin", "effect": "allow" }] }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/security/abac/policies`

### 4.5 Security Headers

#### POST /api/v1/security/headers/validate
Validate security headers.
- **Request:** `{ "headers": { "content-security-policy": "default-src 'self'", "x-frame-options": "DENY" } }`
- **Response:** `{ "valid": true, "score": 95, "missing": [], "recommendations": ["Add Strict-Transport-Security"] }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/security/headers/validate -d '{"headers":{"x-frame-options":"DENY"}}'`

#### GET /api/v1/security/headers/recommendations
Get recommended security headers.
- **Request:** —
- **Response:** `{ "recommendations": [{ "header": "Strict-Transport-Security", "value": "max-age=31536000", "reason": "Enforce HTTPS" }] }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/security/headers/recommendations`

---

## 5. Workflow

### 5.1 Parallel Execution

#### POST /api/v1/workflows/parallel
Execute tasks in parallel.
- **Request:** `{ "tasks": [{ "id": "t1", "type": "http", "config": { "url": "https://api.example.com/a" } }, { "id": "t2", "type": "http", "config": { "url": "https://api.example.com/b" } }] }`
- **Response:** `{ "execution_id": "ex_001", "status": "running", "tasks": [{ "id": "t1", "status": "pending" }, { "id": "t2", "status": "pending" }] }`
- **Status:** 202, 400, 401
- **Example:** `curl -X POST /api/v1/workflows/parallel -d '{"tasks":[{"id":"t1","type":"http"}]}'`

### 5.2 Conditional Execution

#### POST /api/v1/workflows/conditional
Execute conditional workflow.
- **Request:** `{ "condition": { "field": "amount", "operator": "gt", "value": 10000 }, "then": { "task": "approve" }, "else": { "task": "review" } }`
- **Response:** `{ "execution_id": "ex_002", "branch": "then", "task": "approve" }`
- **Status:** 202, 400, 401
- **Example:** `curl -X POST /api/v1/workflows/conditional -d '{"condition":{"field":"amount","operator":"gt","value":10000}}'`

### 5.3 Sub-Workflows

#### POST /api/v1/workflows/sub-workflows
Create a sub-workflow.
- **Request:** `{ "name": "Data Enrichment", "steps": [{ "type": "transform", "config": { "mapping": { "name": "full_name" } } }] }`
- **Response:** `{ "id": "sw_001", "name": "Data Enrichment", "step_count": 1 }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/workflows/sub-workflows -d '{"name":"Data Enrichment","steps":[]}'`

### 5.4 Versioning

#### POST /api/v1/workflows/versioning
Create a new workflow version.
- **Request:** `{ "workflow_id": "wf_001", "version": "2.0.0", "definition": { "steps": [{ "type": "http", "config": { "url": "https://api.example.com/v2" } }] } }`
- **Response:** `{ "workflow_id": "wf_001", "version": "2.0.0", "status": "draft" }`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v1/workflows/versioning -d '{"workflow_id":"wf_001","version":"2.0.0"}'`

#### GET /api/v1/workflows/versions
List workflow versions.
- **Request:** —
- **Response:** `{ "versions": [{ "workflow_id": "wf_001", "version": "2.0.0", "status": "draft" }, { "workflow_id": "wf_001", "version": "1.0.0", "status": "active" }] }`
- **Status:** 200, 401
- **Example:** `curl /api/v1/workflows/versions?workflow_id=wf_001`

### 5.5 Workflow Analytics

#### POST /api/v1/workflows/analytics
Get workflow execution analytics.
- **Request:** `{ "workflow_id": "wf_001", "period": "2026-09-01/2026-09-30" }`
- **Response:** `{ "id": "wa_001", "total_executions": 150, "success_rate": 0.94, "avg_duration_ms": 2300, "bottlenecks": [{ "step": "http_call", "avg_duration_ms": 1800 }] }`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v1/workflows/analytics -d '{"workflow_id":"wf_001","period":"2026-09-01/2026-09-30"}'`

#### GET /api/v1/workflows/analytics/{id}
Get workflow analytics by ID.
- **Request:** —
- **Response:** `{ "id": "wa_001", "total_executions": 150, "success_rate": 0.94 }`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v1/workflows/analytics/wa_001`

### 5.6 Workflow Execution

#### POST /api/v1/workflows/{id}/execute
Execute a workflow.
- **Request:** `{ "input": { "customer_id": "cust_001" } }`
- **Response:** `{ "execution_id": "ex_003", "status": "running", "workflow_id": "wf_001" }`
- **Status:** 202, 400, 401, 404
- **Example:** `curl -X POST /api/v1/workflows/wf_001/execute -d '{"input":{"customer_id":"cust_001"}}'`

#### GET /api/v1/workflows/{id}/status
Get workflow execution status.
- **Request:** —
- **Response:** `{ "execution_id": "ex_003", "status": "completed", "started_at": "2026-10-03T10:00:00Z", "finished_at": "2026-10-03T10:00:05Z" }`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v1/workflows/wf_001/status?execution_id=ex_003`

#### POST /api/v1/workflows/{id}/cancel
Cancel a running workflow.
- **Request:** —
- **Response:** `{ "execution_id": "ex_003", "status": "cancelled" }`
- **Status:** 200, 401, 404, 409
- **Example:** `curl -X POST /api/v1/workflows/wf_001/cancel -d '{"execution_id":"ex_003"}'`
