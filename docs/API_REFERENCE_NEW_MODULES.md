# API Reference — New Modules

Base URL: `https://api.apex-os.example.com/v1`

All endpoints require `Authorization: Bearer <token>` header.

---

## 1. Reporting

### GET /reporting/reports/
List all report definitions.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "Sales Summary", "report_type": "summary", "status": "draft" }], "count": 1 }
```

### POST /reporting/reports/
Create a report definition.

**Request Body:**
```json
{ "name": "Q4 Sales", "report_type": "summary", "data_source": "sales_db", "columns": [{ "name": "region", "label": "Region", "data_type": "string" }], "filters": [], "group_by": ["region"], "order_by": ["-total_sales"], "limit": 100 }
```

**Response (201):**
```json
{ "id": "uuid", "name": "Q4 Sales", "status": "draft", "created_at": "2026-10-04T12:00:00Z" }
```

### POST /reporting/reports/{id}/build
Execute a report and return results.

**Response (200):**
```json
{ "definition": {}, "rows": [{ "region": "EMEA", "total_sales": 150000 }], "total_count": 1, "execution_time_ms": 45.2, "status": "ready" }
```

### POST /reporting/reports/{id}/export
Export a report to file.

**Request Body:**
```json
{ "format": "csv" }
```

**Response (200):**
```json
{ "format": "csv", "file_path": "/tmp/report_uuid.csv", "file_size": 2048, "row_count": 1 }
```

### GET /reporting/schedules/
List report schedules.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "Daily Sales", "frequency": "daily", "status": "pending" }], "count": 1 }
```

### POST /reporting/schedules/
Create a report schedule.

**Request Body:**
```json
{ "name": "Daily Sales", "frequency": "daily", "report_definition_id": "uuid", "start_time": "2026-10-05T08:00:00Z" }
```

**Response (201):**
```json
{ "id": "uuid", "status": "pending", "next_run": "2026-10-05T08:00:00Z" }
```

### GET /reporting/templates/
List report templates.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "Sales Summary", "report_type": "summary" }], "count": 5 }
```

---

## 2. Compliance

### GET /compliance/frameworks/
List compliance frameworks.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "GDPR", "category": "data_privacy", "status": "compliant" }], "count": 1 }
```

### POST /compliance/items/
Add a compliance item.

**Request Body:**
```json
{ "name": "Data Retention Policy", "description": "Ensure data retention", "regulation": "GDPR", "category": "data_privacy", "owner": "compliance@example.com", "due_date": "2026-12-31" }
```

**Response (201):**
```json
{ "id": "uuid", "status": "not_assessed", "created_at": "2026-10-04T12:00:00Z" }
```

### PATCH /compliance/items/{id}/status
Update compliance item status.

**Request Body:**
```json
{ "status": "compliant", "notes": "Evidence verified" }
```

**Response (200):**
```json
{ "id": "uuid", "status": "compliant", "last_assessed": "2026-10-04T12:00:00Z" }
```

### GET /compliance/policies/
List policies.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "title": "Access Control Policy", "version": "1.0", "status": "active" }], "count": 1 }
```

### POST /compliance/policies/
Create a policy.

**Request Body:**
```json
{ "title": "Access Control Policy", "version": "1.0", "content": "Policy text...", "category": "security", "author": "admin@example.com" }
```

**Response (201):**
```json
{ "id": "uuid", "status": "draft", "created_at": "2026-10-04T12:00:00Z" }
```

### GET /compliance/risks/
List risk assessments.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "Data Breach", "risk_level": "high", "risk_score": 12, "status": "open" }], "count": 1 }
```

### POST /compliance/risks/
Create a risk assessment.

**Request Body:**
```json
{ "name": "Data Breach", "description": "Unauthorized access risk", "category": "security", "likelihood": 3, "impact": 4, "owner": "security@example.com" }
```

**Response (201):**
```json
{ "id": "uuid", "risk_level": "high", "risk_score": 12, "status": "open" }
```

### GET /compliance/audits/
List audits.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "Q3 Security Audit", "audit_type": "internal", "status": "in_progress" }], "count": 1 }
```

### POST /compliance/audits/
Create an audit.

**Request Body:**
```json
{ "name": "Q3 Security Audit", "audit_type": "internal", "scope": "All systems", "lead_auditor": "auditor@example.com" }
```

**Response (201):**
```json
{ "id": "uuid", "status": "planned", "finding_count": 0 }
```

### GET /compliance/reports/
List regulatory reports.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "GDPR Annual Report", "regulation": "GDPR", "status": "draft" }], "count": 1 }
```

### POST /compliance/reports/
Create a regulatory report.

**Request Body:**
```json
{ "name": "GDPR Annual Report", "regulation": "GDPR", "reporting_period": "2026", "due_date": "2026-12-31" }
```

**Response (201):**
```json
{ "id": "uuid", "status": "draft", "is_overdue": false }
```

---

## 3. Asset Management

### GET /assets/assets/
List all assets.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "MacBook Pro", "category": "electronics", "status": "active", "purchase_cost": 2499.00 }], "count": 1 }
```

### POST /assets/assets/
Register a new asset.

**Request Body:**
```json
{ "name": "MacBook Pro", "category": "electronics", "purchase_date": "2026-01-15", "purchase_cost": 2499.00, "salvage_value": 200, "useful_life_years": 5, "depreciation_method": "straight_line", "location": "HQ", "assigned_to": "user@example.com" }
```

**Response (201):**
```json
{ "id": "uuid", "status": "active", "created_at": "2026-10-04T12:00:00Z" }
```

### GET /assets/{id}
Get asset details.

**Response (200):**
```json
{ "id": "uuid", "name": "MacBook Pro", "status": "active", "purchase_cost": 2499.00, "book_value": 1999.20 }
```

### PATCH /assets/{id}
Update asset properties.

**Request Body:**
```json
{ "location": "Remote", "status": "active" }
```

**Response (200):**
```json
{ "id": "uuid", "location": "Remote", "updated_at": "2026-10-04T12:00:00Z" }
```

### GET /assets/{id}/depreciation
Get depreciation schedule.

**Response (200):**
```json
{ "asset_id": "uuid", "schedule": [{ "year": 1, "depreciation_amount": 459.80, "book_value": 2039.20 }] }
```

### POST /assets/{id}/maintenance
Schedule maintenance.

**Request Body:**
```json
{ "maintenance_type": "preventive", "scheduled_date": "2026-11-01", "description": "Annual checkup", "cost": 150.00 }
```

**Response (201):**
```json
{ "id": "uuid", "status": "scheduled", "scheduled_date": "2026-11-01" }
```

### POST /assets/{id}/valuation
Record a valuation.

**Request Body:**
```json
{ "market_value": 1800.00, "book_value": 1999.20, "valuation_method": "market_comparison", "appraiser": "valuer@example.com" }
```

**Response (201):**
```json
{ "id": "uuid", "valuation_date": "2026-10-04", "market_value": 1800.00 }
```

### POST /assets/{id}/disposal
Dispose of an asset.

**Request Body:**
```json
{ "disposal_method": "sale", "proceeds": 1500.00, "book_value_at_disposal": 1999.20, "buyer": "third-party", "reason": "End of life" }
```

**Response (201):**
```json
{ "id": "uuid", "gain_loss": -499.20, "disposal_date": "2026-10-04" }
```

---

## 4. Budgeting

### GET /budgeting/budgets/
List all budgets.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "Q4 Marketing", "amount": 50000, "spent": 32000, "status": "active" }], "count": 1 }
```

### POST /budgeting/budgets/
Create a budget.

**Request Body:**
```json
{ "name": "Q4 Marketing", "department_id": "dept-001", "amount": 50000, "currency": "USD", "period": "quarterly", "start_date": "2026-10-01T00:00:00Z", "end_date": "2026-12-31T23:59:59Z", "alert_threshold": 0.8 }
```

**Response (201):**
```json
{ "id": "uuid", "status": "draft", "utilization_rate": 0.0 }
```

### GET /budgeting/budgets/{id}
Get budget details.

**Response (200):**
```json
{ "id": "uuid", "name": "Q4 Marketing", "amount": 50000, "spent": 32000, "remaining": 18000, "utilization_rate": 0.64, "status": "active" }
```

### POST /budgeting/budgets/{id}/spend
Record spending.

**Request Body:**
```json
{ "amount": 5000 }
```

**Response (200):**
```json
{ "id": "uuid", "spent": 37000, "remaining": 13000, "utilization_rate": 0.74 }
```

### PATCH /budgeting/budgets/{id}/status
Change budget status.

**Request Body:**
```json
{ "status": "frozen" }
```

**Response (200):**
```json
{ "id": "uuid", "status": "frozen" }
```

### GET /budgeting/alerts/
List budget alerts.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "budget_id": "uuid", "message": "Budget near limit: 80% utilized", "severity": "warning" }], "count": 1 }
```

### POST /budgeting/alerts/{id}/acknowledge
Acknowledge an alert.

**Response (200):**
```json
{ "id": "uuid", "acknowledged": true }
```

---

## 5. Project Management

### GET /project-mgmt/projects/
List all projects.

**Response (200):**
```json
{ "data": [{ "id": "uuid", "name": "Website Redesign", "status": "active", "progress_percentage": 45.0 }], "count": 1 }
```

### POST /project-mgmt/projects/
Create a project.

**Request Body:**
```json
{ "name": "Website Redesign", "description": "Redesign company website", "start_date": "2026-10-01", "end_date": "2026-12-15", "budget": 25000 }
```

**Response (201):**
```json
{ "id": "uuid", "status": "planning", "created_at": "2026-10-04T12:00:00Z" }
```

### GET /project-mgmt/projects/{id}
Get project details.

**Response (200):**
```json
{ "id": "uuid", "name": "Website Redesign", "status": "active", "progress_percentage": 45.0, "total_tasks": 10, "completed_tasks": 4, "budget": 25000 }
```

### POST /project-mgmt/projects/{id}/tasks
Create a task.

**Request Body:**
```json
{ "name": "Design Homepage", "description": "Create new homepage design", "start_date": "2026-10-05", "end_date": "2026-10-12", "duration_days": 7, "priority": "high", "assigned_to": "designer@example.com" }
```

**Response (201):**
```json
{ "id": "uuid", "status": "not_started", "completion_percentage": 0.0 }
```

### PATCH /project-mgmt/tasks/{id}
Update a task.

**Request Body:**
```json
{ "status": "in_progress", "completion_percentage": 50.0 }
```

**Response (200):**
```json
{ "id": "uuid", "status": "in_progress", "completion_percentage": 50.0 }
```

### GET /project-mgmt/projects/{id}/gantt
Get Gantt chart data.

**Response (200):**
```json
{ "id": "uuid", "project_id": "uuid", "name": "Website Redesign Gantt", "tasks": [{ "task_id": "uuid", "name": "Design Homepage", "start_date": "2026-10-05", "end_date": "2026-10-12", "progress_percentage": 50.0 }] }
```

### POST /project-mgmt/projects/{id}/resources
Add a resource.

**Request Body:**
```json
{ "name": "John Designer", "type": "human", "capacity": 40, "cost_rate": 75.00, "unit": "hour" }
```

**Response (201):**
```json
{ "id": "uuid", "type": "human", "utilization_percentage": 0.0 }
```

### POST /project-mgmt/tasks/{id}/time-entries
Start time tracking.

**Request Body:**
```json
{ "user_id": "user-001", "description": "Working on homepage", "billable": true }
```

**Response (201):**
```json
{ "id": "uuid", "start_time": "2026-10-04T12:00:00Z", "is_running": true }
```

### GET /project-mgmt/projects/{id}/report
Get project report.

**Response (200):**
```json
{ "project": { "name": "Website Redesign", "progress_percentage": 45.0 }, "time": { "total_hours": 120, "billable_hours": 100 }, "resources": { "total_resources": 3 }, "critical_path": ["task-1", "task-3", "task-5"] }
```
