# APEX-OS Business Platform — Complete API Reference

> **Version:** 0.1.0 | **Base URL:** `/api/v1` | **Auth:** JWT Bearer Token

---

## 1. Authentication & Security

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| POST | `/auth/register` | Register user | No | `{username, email, password}` | `{id, username, email, roles}` |
| POST | `/auth/login` | Get JWT token | No | `{username, password}` | `{access_token, token_type, expires_in}` |
| POST | `/auth/refresh` | Refresh token | Yes | — | `{access_token, token_type}` |
| GET | `/auth/users` | List users | Admin | — | `[{id, username, email, roles}]` |
| GET | `/auth/users/{id}` | Get user | Yes | — | `{id, username, email, roles}` |
| PUT | `/auth/users/{id}/roles` | Assign roles | Admin | `{roles: []}` | `{id, roles}` |
| GET | `/auth/roles` | List roles | Admin | — | `[{name, permissions}]` |
| POST | `/auth/roles` | Create role | Admin | `{name, permissions}` | `{name, permissions}` |
| GET | `/auth/permissions` | List permissions | Admin | — | `[{resource, action}]` |
| POST | `/auth/authorize` | Check permission | Yes | `{resource, action}` | `{authorized: bool}` |

---

## 2. Accounting

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/accounting/accounts` | List ledger accounts | Yes | — | `[{id, name, type, balance}]` |
| POST | `/accounting/accounts` | Add account | Yes | `{name, type}` | `{id, name, type}` |
| GET | `/accounting/invoices` | List invoices | Yes | — | `[{id, customer_id, total, status}]` |
| POST | `/accounting/invoices` | Create invoice | Yes | `{customer_id, items: [{description, amount}]}` | `{id, customer_id, items, total, status}` |
| GET | `/accounting/invoices/{id}` | Get invoice | Yes | — | `{id, customer_id, items, total, status}` |
| POST | `/accounting/invoices/{id}/post` | Post to ledger | Yes | — | `{status: "posted"}` |
| GET | `/accounting/ledger` | Get ledger | Yes | — | `{entries: [{id, description, lines}]}` |
| GET | `/accounting/trial-balance` | Trial balance | Yes | — | `{balance: float}` |
| GET | `/accounting/currency` | Currency rates | Yes | — | `{base, rates: {}}` |
| POST | `/accounting/currency/convert` | Convert currency | Yes | `{from, to, amount}` | `{result: float}` |
| GET | `/accounting/tax` | Tax rates | Yes | — | `[{name, rate}]` |
| POST | `/accounting/reconciliation` | Run reconciliation | Yes | `{account_id, start, end}` | `{matched, unmatched}` |
| GET | `/accounting/recurring` | Recurring transactions | Yes | — | `[{id, amount, frequency}]` |
| POST | `/accounting/recurring` | Create recurring | Yes | `{amount, frequency, account_id}` | `{id, amount, frequency}` |

---

## 3. CRM

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/crm/contacts` | List contacts | Yes | — | `[{id, name, email, phone}]` |
| POST | `/crm/contacts` | Create contact | Yes | `{name, email, phone?}` | `{id, name, email, phone}` |
| GET | `/crm/contacts/{id}` | Get contact | Yes | — | `{id, name, email, phone}` |
| PUT | `/crm/contacts/{id}` | Update contact | Yes | `{name?, email?, phone?}` | `{id, name, email, phone}` |
| DELETE | `/crm/contacts/{id}` | Delete contact | Yes | — | 204 No Content |
| GET | `/crm/deals` | List deals | Yes | — | `[{id, title, value, stage}]` |
| POST | `/crm/deals` | Create deal | Yes | `{title, value}` | `{id, title, value, stage}` |
| GET | `/crm/deals/{id}` | Get deal | Yes | — | `{id, title, value, stage}` |
| PUT | `/crm/deals/{id}` | Update deal | Yes | `{title?, value?, stage?}` | `{id, title, value, stage}` |
| POST | `/crm/deals/{id}/link-contact` | Link to contact | Yes | `{contact_id}` | `{deal_id, contact_id}` |
| GET | `/crm/pipeline` | Pipeline report | Yes | — | `{total_deals, total_value, deals_by_stage}` |
| GET | `/crm/leads/scoring` | Lead scores | Yes | — | `[{lead_id, score}]` |
| GET | `/crm/segments` | List segments | Yes | — | `[{id, name, count}]` |
| POST | `/crm/segments` | Create segment | Yes | `{name, criteria}` | `{id, name}` |
| GET | `/crm/email-campaigns` | List campaigns | Yes | — | `[{id, name, status}]` |
| POST | `/crm/email-campaigns` | Create campaign | Yes | `{name, subject, body}` | `{id, name, status}` |
| GET | `/crm/forecasting` | CRM forecast | Yes | — | `{period, predicted_revenue}` |
| POST | `/crm/deduplication` | Run deduplication | Yes | — | `{duplicates_found, merged}` |

---

## 4. Analytics

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/analytics/metrics` | List metrics | Yes | — | `[{name, value, unit, timestamp}]` |
| POST | `/analytics/metrics` | Track metric | Yes | `{name, value, unit, tags?}` | `{name, value, unit, timestamp}` |
| GET | `/analytics/metrics/{name}` | Latest value | Yes | — | `{name, value, unit}` |
| GET | `/analytics/metrics/{name}/timeseries` | Time series | Yes | — | `[{value, timestamp}]` |
| GET | `/analytics/dashboards` | List dashboards | Yes | — | `[{name, total_metrics}]` |
| POST | `/analytics/dashboards` | Create dashboard | Yes | `{name}` | `{name, metrics: []}` |
| GET | `/analytics/dashboards/{name}` | Get dashboard | Yes | — | `{name, metrics: [{name, value, unit}]}` |
| POST | `/analytics/dashboards/{name}/metrics` | Add metric | Yes | `{name, value, unit}` | `{dashboard, metric}` |
| GET | `/analytics/report` | Full report | Yes | — | `{metric_name: value}` |
| GET | `/analytics/anomalies` | Anomalies | Yes | — | `[{metric, expected, actual}]` |
| GET | `/analytics/cohorts` | Cohort analysis | Yes | — | `[{cohort, size, retention}]` |
| GET | `/analytics/funnels` | Funnel analysis | Yes | — | `[{step, count, conversion}]` |
| GET | `/analytics/forecasting` | Forecast | Yes | — | `{period, predicted}` |

---

## 5. Workflow

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/workflow/definitions` | List workflows | Yes | — | `[{name, version, steps}]` |
| POST | `/workflow/definitions` | Create workflow | Yes | `{name, steps: [{name, action}]}` | `{name, version, steps}` |
| GET | `/workflow/definitions/{name}` | Get workflow | Yes | — | `{name, version, steps}` |
| GET | `/workflow/definitions/{name}/versions` | List versions | Yes | — | `["1.0.0", "1.1.0"]` |
| POST | `/workflow/execute` | Execute workflow | Yes | `{workflow, context?}` | `{workflow, version, status, steps}` |
| GET | `/workflow/executions/{id}` | Execution status | Yes | — | `{id, status, steps}` |
| POST | `/workflow/executions/{id}/cancel` | Cancel execution | Yes | — | `{id, status: "cancelled"}` |

---

## 6. Inventory

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/inventory/products` | List products | Yes | — | `[{id, sku, name, unit_cost, is_active}]` |
| POST | `/inventory/products` | Add product | Yes | `{sku, name, unit_cost, category?}` | `{id, sku, name, unit_cost}` |
| GET | `/inventory/products/{id}` | Get product | Yes | — | `{id, sku, name, unit_cost}` |
| GET | `/inventory/products/sku/{sku}` | Get by SKU | Yes | — | `{id, sku, name, unit_cost}` |
| PUT | `/inventory/products/{id}` | Update product | Yes | `{name?, unit_cost?}` | `{id, sku, name, unit_cost}` |
| DELETE | `/inventory/products/{id}` | Delete product | Yes | — | 204 No Content |
| GET | `/inventory/stock/{product_id}` | Stock level | Yes | — | `{product_id, quantity}` |
| POST | `/inventory/stock/receive` | Receive stock | Yes | `{product_id, location, quantity, unit_cost?}` | `{status: "received"}` |
| POST | `/inventory/stock/issue` | Issue stock | Yes | `{product_id, location, quantity, method?}` | `{cost: float}` |
| GET | `/inventory/valuation` | Total value | Yes | — | `{total_value: float}` |
| GET | `/inventory/valuation/{product_id}` | Product value | Yes | — | `{product_id, value: float}` |
| GET | `/inventory/report` | Inventory report | Yes | — | `{total_products, total_inventory_value_fifo, products: []}` |
| GET | `/inventory/purchase-orders` | List POs | Yes | — | `[{id, supplier_id, status}]` |
| POST | `/inventory/purchase-orders` | Create PO | Yes | `{supplier_id, lines: [{product_id, quantity, unit_cost}]}` | `{id, supplier_id, status}` |
| POST | `/inventory/purchase-orders/{id}/receive` | Receive PO | Yes | `{location?}` | `{status: "received"}` |
| GET | `/inventory/sales-orders` | List SOs | Yes | — | `[{id, customer_id, status}]` |
| POST | `/inventory/sales-orders` | Create SO | Yes | `{customer_id, lines: [{product_id, quantity}]}` | `{id, customer_id, status}` |
| POST | `/inventory/sales-orders/{id}/fulfill` | Fulfill SO | Yes | `{location?, method?}` | `{cogs: float}` |

---

## 7. Billing

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/billing/invoices` | List invoices | Yes | — | `[{id, customer_id, status, total}]` |
| POST | `/billing/invoices` | Create invoice | Yes | `{customer_id, currency?, due_days?}` | `{id, customer_id, status: "draft"}` |
| GET | `/billing/invoices/{id}` | Get invoice | Yes | — | `{id, customer_id, lines, total, status}` |
| POST | `/billing/invoices/{id}/lines` | Add line item | Yes | `{description, quantity, unit_price}` | `{id, lines, total}` |
| POST | `/billing/invoices/{id}/tax` | Apply tax | Yes | `{tax_rate: float}` | `{id, tax, total}` |
| POST | `/billing/invoices/{id}/finalize` | Finalize invoice | Yes | — | `{id, status: "open"}` |
| POST | `/billing/invoices/{id}/void` | Void invoice | Yes | — | `{id, status: "void"}` |
| GET | `/billing/invoices/{id}/payments` | Invoice payments | Yes | — | `[{id, amount, status}]` |
| GET | `/billing/payments` | List payments | Yes | — | `[{id, invoice_id, amount, status}]` |
| POST | `/billing/payments` | Process payment | Yes | `{invoice_id, customer_id, amount, method?, currency?}` | `{id, status: "succeeded", transaction_id}` |
| POST | `/billing/payments/{id}/refund` | Refund payment | Yes | — | `{id, status: "refunded"}` |
| GET | `/billing/subscriptions` | List subscriptions | Yes | — | `[{id, customer_id, plan_id, status}]` |
| POST | `/billing/subscriptions` | Create subscription | Yes | `{customer_id, plan_id, trial_days?, auto_renew?}` | `{id, customer_id, status}` |
| GET | `/billing/subscriptions/{id}` | Get subscription | Yes | — | `{id, customer_id, plan, status}` |
| POST | `/billing/subscriptions/{id}/cancel` | Cancel subscription | Yes | — | `{id, status: "canceled"}` |
| POST | `/billing/subscriptions/{id}/renew` | Renew subscription | Yes | — | `{id, status: "active"}` |
| GET | `/billing/plans` | List plans | Yes | — | `[{id, name, price, billing_cycle}]` |
| POST | `/billing/plans` | Create plan | Yes | `{name, price, currency?, billing_cycle?, features?}` | `{id, name, price}` |
| GET | `/billing/usage/{subscription_id}` | Usage records | Yes | — | `[{metric, quantity, timestamp}]` |
| POST | `/billing/usage` | Record usage | Yes | `{customer_id, subscription_id, metric, quantity}` | `{id, metric, quantity}` |
| GET | `/billing/dunning` | Dunning records | Yes | — | `[{id, customer_id, status}]` |
| POST | `/billing/dunning` | Start dunning | Yes | `{customer_id, invoice_id, subscription_id?, max_attempts?}` | `{id, status: "pending"}` |
| POST | `/billing/dunning/{id}/execute` | Execute action | Yes | — | `{id, status: "sent", action}` |
| POST | `/billing/dunning/{id}/resolve` | Resolve dunning | Yes | — | `{id, status: "resolved"}` |

---

## 8. HR

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/hr/employees` | List employees | Yes | — | `[{id, full_name, email, department_id, status}]` |
| POST | `/hr/employees` | Add employee | Yes | `{first_name, last_name, email, department_id, job_title, hire_date, salary}` | `{id, full_name, email, status: "active"}` |
| GET | `/hr/employees/{id}` | Get employee | Yes | — | `{id, full_name, email, department_id, job_title, salary, status, tenure_years}` |
| PUT | `/hr/employees/{id}` | Update employee | Yes | `{first_name?, last_name?, email?, job_title?, salary?, status?}` | `{id, full_name, ...}` |
| DELETE | `/hr/employees/{id}` | Remove employee | Yes | — | 204 No Content |
| GET | `/hr/employees/search` | Search employees | Yes | `?query={q}` | `[{id, full_name, email, job_title}]` |
| GET | `/hr/departments` | List departments | Yes | — | `[{id, name, manager_id}]` |
| POST | `/hr/departments` | Add department | Yes | `{name, manager_id?, cost_center?}` | `{id, name}` |
| GET | `/hr/departments/{id}` | Get department | Yes | — | `{id, name, manager_id}` |
| GET | `/hr/departments/{id}/employees` | Dept employees | Yes | — | `[{id, full_name, job_title}]` |
| GET | `/hr/employees/{id}/subordinates` | Subordinates | Yes | — | `[{id, full_name, job_title}]` |
| GET | `/hr/leave` | Leave records | Yes | — | `[{id, employee_id, start, end, status}]` |
| POST | `/hr/leave` | Request leave | Yes | `{employee_id, start, end, type}` | `{id, status: "pending"}` |
| GET | `/hr/payroll` | Payroll records | Yes | — | `[{id, employee_id, period, net_pay}]` |
| POST | `/hr/payroll` | Run payroll | Yes | `{period}` | `{processed: int, total: float}` |
| GET | `/hr/performance` | Performance reviews | Yes | — | `[{id, employee_id, period, rating}]` |
| POST | `/hr/performance` | Create review | Yes | `{employee_id, period, rating, comments}` | `{id, employee_id, rating}` |
| GET | `/hr/recruitment` | Job postings | Yes | — | `[{id, title, department, status}]` |
| POST | `/hr/recruitment` | Create posting | Yes | `{title, department, description}` | `{id, title, status: "open"}` |

---

## 9. Projects

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/projects` | List projects | Yes | — | `[{id, name, status}]` |
| POST | `/projects` | Create project | Yes | `{name, description?, start_date?, end_date?}` | `{id, name, status}` |
| GET | `/projects/{id}` | Get project | Yes | — | `{id, name, description, status}` |
| PUT | `/projects/{id}` | Update project | Yes | `{name?, description?, status?}` | `{id, name, status}` |
| DELETE | `/projects/{id}` | Delete project | Yes | — | 204 No Content |
| GET | `/projects/{id}/tasks` | Project tasks | Yes | — | `[{id, title, status}]` |
| GET | `/projects/{id}/timeline` | Timeline | Yes | — | `[{date, event}]` |
| GET | `/projects/{id}/status` | Status | Yes | — | `{status, progress}` |

---

## 10. Tasks

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/tasks` | List tasks | Yes | — | `[{id, title, status, assignee_id}]` |
| POST | `/tasks` | Create task | Yes | `{title, description?, assignee_id?, due_date?}` | `{id, title, status: "pending"}` |
| GET | `/tasks/{id}` | Get task | Yes | — | `{id, title, description, status, assignee_id}` |
| PUT | `/tasks/{id}` | Update task | Yes | `{title?, description?, status?, assignee_id?}` | `{id, title, status}` |
| DELETE | `/tasks/{id}` | Delete task | Yes | — | 204 No Content |
| POST | `/tasks/{id}/assign` | Assign task | Yes | `{assignee_id}` | `{id, assignee_id}` |
| POST | `/tasks/{id}/complete` | Complete task | Yes | — | `{id, status: "completed"}` |
| GET | `/tasks/scheduled` | Scheduled tasks | Yes | — | `[{id, title, due_date}]` |
| GET | `/tasks/notifications` | Task notifications | Yes | — | `[{id, task_id, message}]` |

---

## 11. Support

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/support/tickets` | List tickets | Yes | — | `[{id, subject, status, priority}]` |
| POST | `/support/tickets` | Create ticket | Yes | `{subject, description, priority?}` | `{id, subject, status: "open"}` |
| GET | `/support/tickets/{id}` | Get ticket | Yes | — | `{id, subject, description, status, replies}` |
| PUT | `/support/tickets/{id}` | Update ticket | Yes | `{status?, priority?}` | `{id, status}` |
| POST | `/support/tickets/{id}/reply` | Reply | Yes | `{message}` | `{id, message, timestamp}` |
| GET | `/support/sla` | SLA records | Yes | — | `[{id, ticket_id, target, actual}]` |
| GET | `/support/satisfaction` | Satisfaction | Yes | — | `[{id, ticket_id, score}]` |
| GET | `/support/knowledge-base` | KB articles | Yes | — | `[{id, title, category}]` |
| POST | `/support/knowledge-base` | Create article | Yes | `{title, body, category}` | `{id, title}` |
| GET | `/support/live-chat` | Chat sessions | Yes | — | `[{id, customer_id, status}]` |
| POST | `/support/live-chat` | Start chat | Yes | `{customer_id}` | `{id, status: "active"}` |

---

## 12. Documents

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/documents` | List documents | Yes | — | `[{id, name, type, size}]` |
| POST | `/documents` | Upload document | Yes | `{name, content, type}` | `{id, name, type}` |
| GET | `/documents/{id}` | Get document | Yes | — | `{id, name, content, type}` |
| PUT | `/documents/{id}` | Update document | Yes | `{name?, content?}` | `{id, name}` |
| DELETE | `/documents/{id}` | Delete document | Yes | — | 204 No Content |
| GET | `/documents/search` | Search | Yes | `?query={q}` | `[{id, name, type}]` |
| GET | `/documents/{id}/versions` | Versions | Yes | — | `[{version, timestamp}]` |
| POST | `/documents/{id}/share` | Share | Yes | `{user_ids: []}` | `{id, shared_with: []}` |
| GET | `/documents/shared` | Shared docs | Yes | — | `[{id, name, owner_id}]` |

---

## 13. Knowledge

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/knowledge` | List entries | Yes | — | `[{id, title, category}]` |
| POST | `/knowledge` | Create entry | Yes | `{title, body, category}` | `{id, title}` |
| GET | `/knowledge/search` | Search | Yes | `?query={q}` | `[{id, title, score}]` |
| GET | `/knowledge/experts` | Find experts | Yes | `?skill={s}` | `[{id, name, skills}]` |
| GET | `/knowledge/graph` | Knowledge graph | Yes | — | `{nodes: [], edges: []}` |
| GET | `/knowledge/recommendations` | Recommendations | Yes | — | `[{id, title, score}]` |

---

## 14. Compliance

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/compliance/policies` | List policies | Yes | — | `[{id, name, status}]` |
| POST | `/compliance/policies` | Create policy | Yes | `{name, description}` | `{id, name}` |
| GET | `/compliance/audit` | Audit | Yes | — | `{id, date, findings}` |
| GET | `/compliance/risk` | Risk assessment | Yes | — | `[{id, risk, level}]` |
| GET | `/compliance/tracking` | Tracking | Yes | — | `[{id, policy_id, status}]` |
| GET | `/compliance/reporting` | Reports | Yes | — | `[{id, period, status}]` |

---

## 15. Integration

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/integration/routes` | List routes | Yes | — | `[{path, method, handler}]` |
| POST | `/integration/routes` | Add route | Yes | `{path, method, handler}` | `{path, method}` |
| GET | `/integration/webhooks` | List webhooks | Yes | — | `[{id, url, events}]` |
| POST | `/integration/webhooks` | Register webhook | Yes | `{url, events: []}` | `{id, url}` |
| POST | `/integration/data-transform` | Transform data | Yes | `{data, mapping}` | `{result: {}}` |
| GET | `/integration/kafka` | Kafka status | Yes | — | `{connected, topics}` |
| GET | `/integration/rate-limits` | Rate limits | Yes | — | `{max_requests, window}` |

---

## 16. Cache

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/cache/stats` | Cache stats | Yes | — | `{hits, misses, hit_rate}` |
| POST | `/cache/warm` | Warm cache | Yes | `{keys: []}` | `{warmed: int}` |
| POST | `/cache/invalidate` | Invalidate | Yes | `{keys: []}` | `{invalidated: int}` |
| DELETE | `/cache/{key}` | Delete entry | Yes | — | 204 No Content |

---

## 17. AI

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| POST | `/ai/orchestrate` | Run orchestration | Yes | `{task, context?}` | `{result, steps}` |
| POST | `/ai/plan` | Generate plan | Yes | `{goal}` | `{steps: []}` |
| POST | `/ai/reflect` | Run reflection | Yes | `{experience}` | `{insights: []}` |
| GET | `/ai/tools` | List tools | Yes | — | `[{name, description}]` |
| POST | `/ai/memory` | Store memory | Yes | `{key, value}` | `{id, key}` |
| GET | `/ai/memory` | Retrieve memory | Yes | `?key={k}` | `{key, value}` |

---

## 18. ML

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| POST | `/ml/train` | Train model | Yes | `{dataset, algorithm, params?}` | `{model_id, status}` |
| POST | `/ml/serving` | Serve model | Yes | `{model_id, input}` | `{prediction}` |
| GET | `/ml/monitoring` | Monitoring | Yes | — | `{model_id, metrics}` |
| GET | `/ml/feature-store` | Feature store | Yes | — | `[{name, type}]` |
| POST | `/ml/ab-testing` | A/B test | Yes | `{variants, metric}` | `{winner, confidence}` |

---

## 19. Data Exchange

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| POST | `/data-exchange/import` | Import data | Yes | `{format, data}` | `{imported: int}` |
| POST | `/data-exchange/export` | Export data | Yes | `{format, query}` | `{data: {}}` |
| GET | `/data-exchange/formats` | Formats | Yes | — | `["csv", "excel", "json"]` |

---

## 20. Data Warehouse

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| POST | `/data-warehouse/etl` | Run ETL | Yes | `{source, target, transform?}` | `{job_id, status}` |
| GET | `/data-warehouse/etl/status` | ETL status | Yes | — | `{job_id, status, progress}` |

---

## 21. Database

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/database/models` | List models | Yes | — | `[{name, table}]` |
| GET | `/database/query` | Execute query | Yes | `{sql}` | `{rows: []}` |
| POST | `/database/transaction` | Begin transaction | Yes | — | `{transaction_id}` |
| GET | `/database/migrations` | List migrations | Yes | — | `[{id, name, applied}]` |
| POST | `/database/migrations/run` | Run migrations | Yes | — | `{applied: int}` |

---

## 22. Notifications

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/notifications` | List notifications | Yes | — | `[{id, message, read}]` |
| POST | `/notifications` | Send notification | Yes | `{recipient, message, channel?}` | `{id, status: "sent"}` |
| GET | `/notifications/channels` | Channels | Yes | — | `[{name, type}]` |
| GET | `/notifications/templates` | Templates | Yes | — | `[{id, name, body}]` |
| POST | `/notifications/templates` | Create template | Yes | `{name, body}` | `{id, name}` |

---

## 23. Reporting

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/reporting/reports` | List reports | Yes | — | `[{id, name, type}]` |
| POST | `/reporting/reports` | Generate report | Yes | `{type, params}` | `{id, data}` |
| GET | `/reporting/templates` | Templates | Yes | — | `[{id, name}]` |
| POST | `/reporting/schedule` | Schedule report | Yes | `{report_id, frequency, recipients}` | `{id, schedule}` |
| GET | `/reporting/distribute` | Distribution | Yes | — | `[{id, report_id, recipients}]` |
| POST | `/reporting/export` | Export report | Yes | `{report_id, format}` | `{download_url}` |

---

## 24. Assets

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/assets` | List assets | Yes | — | `[{id, name, value, status}]` |
| POST | `/assets` | Add asset | Yes | `{name, value, category}` | `{id, name, value}` |
| GET | `/assets/{id}` | Get asset | Yes | — | `{id, name, value, status}` |
| PUT | `/assets/{id}` | Update asset | Yes | `{name?, value?, status?}` | `{id, name, value}` |
| DELETE | `/assets/{id}` | Delete asset | Yes | — | 204 No Content |
| GET | `/assets/depreciation` | Depreciation | Yes | — | `[{id, asset_id, amount, period}]` |
| GET | `/assets/maintenance` | Maintenance | Yes | — | `[{id, asset_id, date, description}]` |
| POST | `/assets/disposal` | Dispose asset | Yes | `{asset_id, reason}` | `{id, status: "disposed"}` |
| GET | `/assets/valuation` | Valuation | Yes | — | `{total_value, assets: []}` |

---

## 25. Audit

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/audit/logs` | Audit logs | Yes | — | `[{id, timestamp, action, user_id}]` |
| GET | `/audit/trail` | Audit trail | Yes | — | `[{id, entity, action, timestamp}]` |
| GET | `/audit/compliance` | Compliance audit | Yes | — | `{id, date, findings}` |
| GET | `/audit/retention` | Retention policy | Yes | — | `{period, policy}` |
| GET | `/audit/search` | Search logs | Yes | `?query={q}` | `[{id, action, timestamp}]` |

---

## 26. BI

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/bi/kpi` | KPIs | Yes | — | `[{name, value, target}]` |
| GET | `/bi/executive` | Executive dashboard | Yes | — | `{revenue, expenses, profit}` |
| GET | `/bi/benchmarking` | Benchmarking | Yes | — | `[{metric, value, benchmark}]` |
| GET | `/bi/predictive` | Predictive | Yes | — | `{forecast, confidence}` |
| GET | `/bi/visualization` | Visualizations | Yes | — | `[{id, type, data}]` |

---

## 27. E-Commerce

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/ecommerce/products` | List products | Yes | — | `[{id, name, price}]` |
| GET | `/ecommerce/cart` | Get cart | Yes | — | `{items: [], total}` |
| POST | `/ecommerce/cart` | Add to cart | Yes | `{product_id, quantity}` | `{items: [], total}` |
| GET | `/ecommerce/orders` | List orders | Yes | — | `[{id, status, total}]` |
| POST | `/ecommerce/orders` | Create order | Yes | `{items: [{product_id, quantity}]}` | `{id, status: "pending"}` |
| POST | `/ecommerce/checkout` | Checkout | Yes | `{cart_id, payment_method}` | `{order_id, status}` |
| POST | `/ecommerce/payment` | Process payment | Yes | `{order_id, amount, method}` | `{status: "succeeded"}` |

---

## 28. Supply Chain

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/supplychain/suppliers` | List suppliers | Yes | — | `[{id, name, rating}]` |
| POST | `/supplychain/suppliers` | Add supplier | Yes | `{name, contact}` | `{id, name}` |
| GET | `/supplychain/purchase-orders` | List POs | Yes | — | `[{id, supplier_id, status}]` |
| POST | `/supplychain/purchase-orders` | Create PO | Yes | `{supplier_id, lines: []}` | `{id, status}` |
| GET | `/supplychain/logistics` | Logistics | Yes | — | `[{id, shipment_id, status}]` |
| GET | `/supplychain/warehouse` | Warehouse | Yes | — | `{id, location, capacity}` |
| GET | `/supplychain/demand-forecast` | Demand forecast | Yes | — | `{period, forecast}` |

---

## 29. Manufacturing

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/manufacturing/bom` | Bill of materials | Yes | — | `[{id, product_id, components: []}]` |
| GET | `/manufacturing/production-planning` | Production plan | Yes | — | `[{id, product_id, quantity, due_date}]` |
| GET | `/manufacturing/quality-control` | QC data | Yes | — | `[{id, batch_id, result}]` |
| GET | `/manufacturing/shop-floor` | Shop floor | Yes | — | `[{id, station, status}]` |
| GET | `/manufacturing/maintenance` | Maintenance | Yes | — | `[{id, equipment_id, date, type}]` |

---

## 30. Contracts

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/contracts` | List contracts | Yes | — | `[{id, title, status}]` |
| POST | `/contracts` | Create contract | Yes | `{title, body, parties: []}` | `{id, title, status: "draft"}` |
| GET | `/contracts/{id}` | Get contract | Yes | — | `{id, title, body, status}` |
| PUT | `/contracts/{id}` | Update contract | Yes | `{title?, body?, status?}` | `{id, title, status}` |
| POST | `/contracts/{id}/approve` | Approve | Yes | — | `{id, status: "approved"}` |
| POST | `/contracts/{id}/renew` | Renew | Yes | — | `{id, status: "active"}` |
| GET | `/contracts/templates` | Templates | Yes | — | `[{id, name}]` |
| GET | `/contracts/compliance` | Compliance | Yes | — | `[{id, contract_id, status}]` |

---

## 31. Integration Hub

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/integration-hub/orchestration` | Orchestration | Yes | — | `{id, status, steps}` |
| GET | `/integration-hub/data-mapping` | Data mappings | Yes | — | `[{id, source, target}]` |
| GET | `/integration-hub/event-routing` | Event routing | Yes | — | `[{id, event, handler}]` |
| GET | `/integration-hub/monitoring` | Monitoring | Yes | — | `{id, status, metrics}` |
| GET | `/integration-hub/error-handling` | Error handling | Yes | — | `[{id, error, status}]` |

---

## 32. Health & Platform

| Method | Path | Description | Auth | Request Body | Response Body |
|--------|------|-------------|------|--------------|---------------|
| GET | `/health` | Health check | No | — | `{status: "healthy", version}` |
| GET | `/health/components` | Component health | No | — | `{accounting: true, crm: true, ...}` |
| GET | `/metrics` | Platform metrics | Yes | — | `{requests, errors, latency}` |
| GET | `/config` | Get configuration | Admin | — | `{key: value}` |
| PUT | `/config` | Update configuration | Admin | `{key, value}` | `{key, value}` |

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Unprocessable Entity |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

---

## Authentication

All endpoints except `/health` and `/auth/register` require a JWT Bearer token:

```
Authorization: Bearer <jwt_token>
```

Tokens are obtained via `POST /auth/login` and expire after 3600 seconds.

---

## Rate Limiting

Default: 100 requests per 60 seconds per client. Configured via `RateLimiter`.

---

*Generated from APEX-OS Business Platform source code.*
