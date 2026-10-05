"""Comprehensive test suite for all 43 route modules.

Covers: API endpoints, CRUD operations, input validation, error handling.
"""
import pytest
from fastapi.testclient import TestClient
from web.backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-api-key-12345"}


# ── 1. ACCOUNTING (/api/accounts) ──────────────────────────────────────────

class TestAccounting:
    def test_list_accounts(self, client, auth_headers):
        r = client.get("/api/accounts/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_account(self, client, auth_headers):
        r = client.get("/api/accounts/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_account(self, client, auth_headers):
        r = client.post("/api/accounts", headers=auth_headers, json={
            "name": "Test Account", "type": "asset", "code": "9999",
            "balance": 100.0, "currency": "USD", "is_active": True,
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Test Account"

    def test_update_account(self, client, auth_headers):
        r = client.put("/api/accounts/1", headers=auth_headers, json={"balance": 999.0})
        assert r.status_code == 200
        assert r.json()["balance"] == 999.0

    def test_delete_account(self, client, auth_headers):
        r = client.delete("/api/accounts/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/accounts/9999", headers=auth_headers).status_code == 404

    def test_invalid_type(self, client, auth_headers):
        r = client.post("/api/accounts", headers=auth_headers, json={
            "name": "Bad", "type": "invalid", "code": "0000",
        })
        assert r.status_code == 422


# ── 2. AGENT REACH (/api/agents) ──────────────────────────────────────────

class TestAgentReach:
    def test_list(self, client, auth_headers):
        r = client.get("/api/agents/", headers=auth_headers)
        assert r.status_code == 200

    def test_get(self, client, auth_headers):
        r = client.get("/api/agents/1", headers=auth_headers)
        assert r.status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/agents", headers=auth_headers, json={
            "name": "Test Agent", "agent_type": "processor", "status": "active",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        r = client.put("/api/agents/1", headers=auth_headers, json={"status": "paused"})
        assert r.status_code == 200

    def test_delete(self, client, auth_headers):
        r = client.delete("/api/agents/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/agents/9999", headers=auth_headers).status_code == 404


# ── 3. ALERTS (/api/alerts) ──────────────────────────────────────────────

class TestAlerts:
    def test_list(self, client, auth_headers):
        r = client.get("/api/alerts/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get(self, client, auth_headers):
        r = client.get("/api/alerts/1", headers=auth_headers)
        assert r.status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/alerts/", headers=auth_headers, json={
            "title": "Test Alert", "message": "Test", "severity": "info",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        r = client.put("/api/alerts/1", headers=auth_headers, json={"is_read": True})
        assert r.status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/alerts/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/alerts/9999", headers=auth_headers).status_code == 404


# ── 4. ANALYTICS (/api/dashboards) ────────────────────────────────────────

class TestAnalytics:
    def test_list(self, client, auth_headers):
        r = client.get("/api/dashboards", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get(self, client, auth_headers):
        r = client.get("/api/dashboards/1", headers=auth_headers)
        assert r.status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/dashboards", headers=auth_headers, json={
            "name": "Test Dash", "description": "Test", "layout": "grid",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        r = client.put("/api/dashboards/1", headers=auth_headers, json={"name": "Updated"})
        assert r.status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/dashboards/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/dashboards/9999", headers=auth_headers).status_code == 404

    def test_empty_name(self, client, auth_headers):
        r = client.post("/api/dashboards", headers=auth_headers, json={"name": ""})
        assert r.status_code == 422


# ── 5. ASSETS (/api/assets) ──────────────────────────────────────────────

class TestAssets:
    def test_list(self, client, auth_headers):
        r = client.get("/api/assets/", headers=auth_headers)
        assert r.status_code == 200

    def test_get(self, client, auth_headers):
        r = client.get("/api/assets/1", headers=auth_headers)
        assert r.status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/assets/", headers=auth_headers, json={
            "name": "Test Asset", "asset_tag": "TA-001", "category_id": 1,
            "purchase_date": "2024-01-01", "purchase_cost": 1000.0,
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        r = client.put("/api/assets/1", headers=auth_headers, json={"name": "Updated"})
        assert r.status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/assets/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/assets/9999", headers=auth_headers).status_code == 404

    def test_list_categories(self, client, auth_headers):
        assert client.get("/api/assets/categories/", headers=auth_headers).status_code == 200

    def test_list_maintenance(self, client, auth_headers):
        assert client.get("/api/assets/maintenance/", headers=auth_headers).status_code == 200


# ── 6. AUDIT LOGS (/api/audit-logs) ──────────────────────────────────────

class TestAuditLogs:
    def test_list(self, client, auth_headers):
        assert client.get("/api/audit-logs", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/audit-logs/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/audit-logs", headers=auth_headers, json={
            "action": "test", "entity_type": "user", "entity_id": "1",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/audit-logs/1", headers=auth_headers, json={"action": "updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/audit-logs/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/audit-logs/9999", headers=auth_headers).status_code == 404


# ── 7. BIGDATA (/api/datasets) ───────────────────────────────────────────

class TestBigData:
    def test_list(self, client, auth_headers):
        assert client.get("/api/datasets", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/datasets/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/datasets", headers=auth_headers, json={
            "name": "Test Dataset", "format": "parquet",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/datasets/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/datasets/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/datasets/9999", headers=auth_headers).status_code == 404


# ── 8. BUDGETING (/api/budgeting) ────────────────────────────────────────

class TestBudgeting:
    def test_list_budgets(self, client, auth_headers):
        assert client.get("/api/budgeting/budgets/", headers=auth_headers).status_code == 200

    def test_get_budget(self, client, auth_headers):
        assert client.get("/api/budgeting/budgets/1", headers=auth_headers).status_code == 200

    def test_create_budget(self, client, auth_headers):
        r = client.post("/api/budgeting/budgets/", headers=auth_headers, json={
            "name": "Test Budget", "fiscal_year": 2024, "status": "draft",
            "total_budgeted": 10000.0, "total_actual": 0.0,
        })
        assert r.status_code == 201

    def test_update_budget(self, client, auth_headers):
        assert client.put("/api/budgeting/budgets/1", headers=auth_headers, json={"amount": 20000.0}).status_code == 200

    def test_delete_budget(self, client, auth_headers):
        assert client.delete("/api/budgeting/budgets/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/budgeting/budgets/9999", headers=auth_headers).status_code == 404

    def test_list_cost_centers(self, client, auth_headers):
        assert client.get("/api/budgeting/cost-centers/", headers=auth_headers).status_code == 200


# ── 9. CAMPAIGNS (/api/campaigns) ────────────────────────────────────────

class TestCampaigns:
    def test_list(self, client, auth_headers):
        assert client.get("/api/campaigns/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/campaigns/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/campaigns/", headers=auth_headers, json={
            "name": "Test Campaign", "channel": "email", "status": "draft",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/campaigns/1", headers=auth_headers, json={"status": "completed"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/campaigns/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/campaigns/9999", headers=auth_headers).status_code == 404


# ── 10. CAPACITY PLANNING (/api/capacity-planning) ───────────────────────

class TestCapacityPlanning:
    def test_list_plans(self, client, auth_headers):
        assert client.get("/api/capacity-planning/capacity-plans/", headers=auth_headers).status_code == 200

    def test_get_plan(self, client, auth_headers):
        assert client.get("/api/capacity-planning/capacity-plans/1", headers=auth_headers).status_code == 200

    def test_create_plan(self, client, auth_headers):
        r = client.post("/api/capacity-planning/capacity-plans/", headers=auth_headers, json={
            "name": "Test Plan",
        })
        assert r.status_code == 201

    def test_update_plan(self, client, auth_headers):
        assert client.put("/api/capacity-planning/capacity-plans/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete_plan(self, client, auth_headers):
        assert client.delete("/api/capacity-planning/capacity-plans/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/capacity-planning/capacity-plans/9999", headers=auth_headers).status_code == 404

    def test_list_forecasts(self, client, auth_headers):
        assert client.get("/api/capacity-planning/forecasts/", headers=auth_headers).status_code == 200


# ── 11. COMPLIANCE (/api/compliance) ─────────────────────────────────────

class TestCompliance:
    def test_list_frameworks(self, client, auth_headers):
        assert client.get("/api/compliance/frameworks/", headers=auth_headers).status_code == 200

    def test_get_framework(self, client, auth_headers):
        assert client.get("/api/compliance/frameworks/1", headers=auth_headers).status_code == 200

    def test_create_framework(self, client, auth_headers):
        r = client.post("/api/compliance/frameworks/", headers=auth_headers, json={
            "name": "Test Framework", "version": "1.0", "status": "active",
        })
        assert r.status_code == 201

    def test_update_framework(self, client, auth_headers):
        assert client.put("/api/compliance/frameworks/1", headers=auth_headers, json={"status": "inactive"}).status_code == 200

    def test_delete_framework(self, client, auth_headers):
        assert client.delete("/api/compliance/frameworks/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/compliance/frameworks/9999", headers=auth_headers).status_code == 404

    def test_list_controls(self, client, auth_headers):
        assert client.get("/api/compliance/controls/", headers=auth_headers).status_code == 200

    def test_list_audits(self, client, auth_headers):
        assert client.get("/api/compliance/audits/", headers=auth_headers).status_code == 200


# ── 12. CONTINUOUS BI (/api/reports) ─────────────────────────────────────

class TestContinuousBI:
    def test_list(self, client, auth_headers):
        assert client.get("/api/reports/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/reports/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/reports/", headers=auth_headers, json={
            "name": "Test Report", "type": "dashboard",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/reports/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/reports/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/reports/9999", headers=auth_headers).status_code == 404


# ── 13. COST MANAGEMENT (/api/cost-management) ────────────────────────────

class TestCostManagement:
    def test_list_cost_centers(self, client, auth_headers):
        assert client.get("/api/cost-management/cost-centers/", headers=auth_headers).status_code == 200

    def test_get_cost_center(self, client, auth_headers):
        assert client.get("/api/cost-management/cost-centers/1", headers=auth_headers).status_code == 200

    def test_create_cost_center(self, client, auth_headers):
        r = client.post("/api/cost-management/cost-centers/", headers=auth_headers, json={
            "name": "Test Cost Center", "code": "CC-001",
        })
        assert r.status_code == 201

    def test_update_cost_center(self, client, auth_headers):
        assert client.put("/api/cost-management/cost-centers/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete_cost_center(self, client, auth_headers):
        assert client.delete("/api/cost-management/cost-centers/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/cost-management/cost-centers/9999", headers=auth_headers).status_code == 404

    def test_list_cost_allocations(self, client, auth_headers):
        assert client.get("/api/cost-management/cost-allocations/", headers=auth_headers).status_code == 200

    def test_list_cost_forecasts(self, client, auth_headers):
        assert client.get("/api/cost-management/cost-forecasts/", headers=auth_headers).status_code == 200


# ── 14. CRM (/api/leads) ─────────────────────────────────────────────────

class TestCRM:
    def test_list(self, client, auth_headers):
        r = client.get("/api/leads/", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_get(self, client, auth_headers):
        r = client.get("/api/leads/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create(self, client, auth_headers):
        r = client.post("/api/leads/", headers=auth_headers, json={
            "name": "Test Lead", "email": "test@example.com",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        r = client.put("/api/leads/1", headers=auth_headers, json={"status": "qualified"})
        assert r.status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/leads/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/leads/9999", headers=auth_headers).status_code == 404

    def test_invalid_email(self, client, auth_headers):
        r = client.post("/api/leads/", headers=auth_headers, json={
            "name": "Bad", "email": "not-an-email",
        })
        assert r.status_code == 422


# ── 15. CUSTOMERS (/api/customers) ───────────────────────────────────────

class TestCustomers:
    def test_list(self, client, auth_headers):
        assert client.get("/api/customers/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/customers/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/customers/", headers=auth_headers, json={
            "name": "Test Customer", "email": "customer@example.com",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/customers/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/customers/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/customers/9999", headers=auth_headers).status_code == 404


# ── 16. DATA WAREHOUSE (/api/data-warehouse) ──────────────────────────────

class TestDataWarehouse:
    def test_list_data_sources(self, client, auth_headers):
        assert client.get("/api/data-warehouse/data-sources", headers=auth_headers).status_code == 200

    def test_get_data_source(self, client, auth_headers):
        assert client.get("/api/data-warehouse/data-sources/1", headers=auth_headers).status_code == 200

    def test_create_data_source(self, client, auth_headers):
        r = client.post("/api/data-warehouse/data-sources", headers=auth_headers, json={
            "name": "Test Source", "type": "postgresql",
        })
        assert r.status_code == 201

    def test_update_data_source(self, client, auth_headers):
        assert client.put("/api/data-warehouse/data-sources/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete_data_source(self, client, auth_headers):
        assert client.delete("/api/data-warehouse/data-sources/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/data-warehouse/data-sources/9999", headers=auth_headers).status_code == 404

    def test_list_etl_jobs(self, client, auth_headers):
        assert client.get("/api/data-warehouse/etl-jobs", headers=auth_headers).status_code == 200

    def test_list_data_marts(self, client, auth_headers):
        assert client.get("/api/data-warehouse/data-marts", headers=auth_headers).status_code == 200


# ── 17. DATASCIENCE (/api/models) ────────────────────────────────────────

class TestDataScience:
    def test_list(self, client, auth_headers):
        assert client.get("/api/models/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/models/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/models/", headers=auth_headers, json={
            "name": "Test Model", "type": "xgboost",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/models/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/models/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/models/9999", headers=auth_headers).status_code == 404


# ── 18. DISASTER RECOVERY (/api/disaster-recovery) ───────────────────────

class TestDisasterRecovery:
    def test_list_dr_plans(self, client, auth_headers):
        assert client.get("/api/disaster-recovery/dr-plans/", headers=auth_headers).status_code == 200

    def test_get_dr_plan(self, client, auth_headers):
        assert client.get("/api/disaster-recovery/dr-plans/1", headers=auth_headers).status_code == 200

    def test_create_dr_plan(self, client, auth_headers):
        r = client.post("/api/disaster-recovery/dr-plans/", headers=auth_headers, json={
            "name": "Test DR Plan",
        })
        assert r.status_code == 201

    def test_update_dr_plan(self, client, auth_headers):
        assert client.put("/api/disaster-recovery/dr-plans/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete_dr_plan(self, client, auth_headers):
        assert client.delete("/api/disaster-recovery/dr-plans/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/disaster-recovery/dr-plans/9999", headers=auth_headers).status_code == 404

    def test_list_backup_schedules(self, client, auth_headers):
        assert client.get("/api/disaster-recovery/backup-schedules/", headers=auth_headers).status_code == 200

    def test_list_recovery_procedures(self, client, auth_headers):
        assert client.get("/api/disaster-recovery/recovery-procedures/", headers=auth_headers).status_code == 200


# ── 19. EMPLOYEES (/api/employees) ───────────────────────────────────────

class TestEmployees:
    def test_list(self, client, auth_headers):
        assert client.get("/api/employees/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/employees/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/employees/", headers=auth_headers, json={
            "first_name": "Test", "last_name": "Employee",
            "email": "employee@example.com", "department": "Engineering",
            "position": "Developer", "salary": 50000.0, "hire_date": "2024-01-01",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/employees/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/employees/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/employees/9999", headers=auth_headers).status_code == 404


# ── 20. EXPORT TEMPLATES (/api/export-templates) ─────────────────────────

class TestExportTemplates:
    def test_list_templates(self, client, auth_headers):
        assert client.get("/api/export-templates/templates", headers=auth_headers).status_code == 200

    def test_get_template(self, client, auth_headers):
        assert client.get("/api/export-templates/templates/1", headers=auth_headers).status_code == 200

    def test_create_template(self, client, auth_headers):
        r = client.post("/api/export-templates/templates", headers=auth_headers, json={
            "name": "Test Template", "format": "csv",
        })
        assert r.status_code == 201

    def test_update_template(self, client, auth_headers):
        assert client.put("/api/export-templates/templates/1", headers=auth_headers, json={"format": "xlsx"}).status_code == 200

    def test_delete_template(self, client, auth_headers):
        assert client.delete("/api/export-templates/templates/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/export-templates/templates/9999", headers=auth_headers).status_code == 404

    def test_list_jobs(self, client, auth_headers):
        assert client.get("/api/export-templates/jobs", headers=auth_headers).status_code == 200

    def test_list_schedules(self, client, auth_headers):
        assert client.get("/api/export-templates/schedules", headers=auth_headers).status_code == 200


# ── 21. HR (/api/hr) ────────────────────────────────────────────────────

class TestHR:
    def test_list_employees(self, client, auth_headers):
        r = client.get("/api/hr/employees", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_get_employee(self, client, auth_headers):
        assert client.get("/api/hr/employees/1", headers=auth_headers).status_code == 200

    def test_create_employee(self, client, auth_headers):
        r = client.post("/api/hr/employees", headers=auth_headers, json={
            "first_name": "Test", "last_name": "User",
            "email": "test.user@apex-os.com", "department_id": 1,
            "position_id": 1, "salary": 50000.0, "hire_date": "2024-01-01",
        })
        assert r.status_code == 201

    def test_update_employee(self, client, auth_headers):
        assert client.put("/api/hr/employees/1", headers=auth_headers, json={"salary": 60000.0}).status_code == 200

    def test_delete_employee(self, client, auth_headers):
        assert client.delete("/api/hr/employees/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/hr/employees/9999", headers=auth_headers).status_code == 404

    def test_duplicate_email(self, client, auth_headers):
        r = client.post("/api/hr/employees", headers=auth_headers, json={
            "first_name": "Dup", "last_name": "Email",
            "email": "alice.johnson@apex-os.com", "department_id": 1,
            "position_id": 1, "salary": 50000.0, "hire_date": "2024-01-01",
        })
        assert r.status_code in (201, 409)

    def test_list_departments(self, client, auth_headers):
        assert client.get("/api/hr/departments", headers=auth_headers).status_code == 200


# ── 22. INTEGRATIONS (/api/integrations) ─────────────────────────────────

class TestIntegrations:
    def test_list(self, client, auth_headers):
        assert client.get("/api/integrations/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/integrations/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/integrations/", headers=auth_headers, json={
            "name": "Test Integration", "type": "webhook",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/integrations/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/integrations/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/integrations/9999", headers=auth_headers).status_code == 404


# ── 23. INVENTORY (/api/inventory) ───────────────────────────────────────

class TestInventory:
    def test_list_products(self, client, auth_headers):
        assert client.get("/api/inventory/products", headers=auth_headers).status_code == 200

    def test_get_product(self, client, auth_headers):
        assert client.get("/api/inventory/products/1", headers=auth_headers).status_code == 200

    def test_create_product(self, client, auth_headers):
        r = client.post("/api/inventory/products", headers=auth_headers, json={
            "name": "Test Product", "sku": "TEST-001", "price": 10.0,
        })
        assert r.status_code == 201

    def test_update_product(self, client, auth_headers):
        assert client.put("/api/inventory/products/1", headers=auth_headers, json={"price": 20.0}).status_code == 200

    def test_delete_product(self, client, auth_headers):
        assert client.delete("/api/inventory/products/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/inventory/products/9999", headers=auth_headers).status_code == 404

    def test_negative_price(self, client, auth_headers):
        r = client.post("/api/inventory/products", headers=auth_headers, json={
            "name": "Bad", "sku": "BAD-001", "price": -1.0,
        })
        assert r.status_code == 422

    def test_list_categories(self, client, auth_headers):
        assert client.get("/api/inventory/categories", headers=auth_headers).status_code == 200

    def test_list_suppliers(self, client, auth_headers):
        assert client.get("/api/inventory/suppliers", headers=auth_headers).status_code == 200


# ── 24. INVOICES (/api/invoices) ─────────────────────────────────────────

class TestInvoices:
    def test_list(self, client, auth_headers):
        assert client.get("/api/invoices", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        r = client.get("/api/invoices", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        if data.get("data"):
            invoice_id = data["data"][0]["id"]
            assert client.get(f"/api/invoices/{invoice_id}", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/invoices", headers=auth_headers, json={
            "customer_name": "Test Customer", "customer_email": "test@example.com",
            "amount": 100.0, "currency": "USD", "status": "draft",
            "issue_date": "2024-01-01", "due_date": "2024-02-01",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        r = client.get("/api/invoices", headers=auth_headers)
        data = r.json()
        if data.get("data"):
            invoice_id = data["data"][0]["id"]
            assert client.put(f"/api/invoices/{invoice_id}", headers=auth_headers, json={"amount": 200.0}).status_code == 200

    def test_delete(self, client, auth_headers):
        r = client.get("/api/invoices", headers=auth_headers)
        data = r.json()
        if data.get("data"):
            invoice_id = data["data"][0]["id"]
            assert client.delete(f"/api/invoices/{invoice_id}", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/invoices/nonexistent-id-9999", headers=auth_headers).status_code == 404


# ── 25. IOT (/api/iot) ───────────────────────────────────────────────────

class TestIoT:
    def test_list_devices(self, client, auth_headers):
        assert client.get("/api/iot/devices/", headers=auth_headers).status_code == 200

    def test_get_device(self, client, auth_headers):
        assert client.get("/api/iot/devices/1", headers=auth_headers).status_code == 200

    def test_create_device(self, client, auth_headers):
        r = client.post("/api/iot/devices/", headers=auth_headers, json={
            "name": "Test Device", "type": "sensor",
        })
        assert r.status_code == 201

    def test_update_device(self, client, auth_headers):
        assert client.put("/api/iot/devices/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete_device(self, client, auth_headers):
        assert client.delete("/api/iot/devices/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/iot/devices/9999", headers=auth_headers).status_code == 404

    def test_list_sensors(self, client, auth_headers):
        assert client.get("/api/iot/sensors/", headers=auth_headers).status_code == 200

    def test_list_telemetry(self, client, auth_headers):
        assert client.get("/api/iot/telemetry/", headers=auth_headers).status_code == 200


# ── 26. JOURNAL ENTRIES (/api/journal-entries) ───────────────────────────

class TestJournalEntries:
    def test_list(self, client, auth_headers):
        assert client.get("/api/journal-entries/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/journal-entries/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/journal-entries", headers=auth_headers, json={
            "date": "2024-01-01", "description": "Test Entry",
            "debit_account": "1000", "credit_account": "2000", "amount": 100.0,
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/journal-entries/1", headers=auth_headers, json={"description": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/journal-entries/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/journal-entries/9999", headers=auth_headers).status_code == 404


# ── 27. KNOWLEDGE BASE (/api/knowledge-base) ─────────────────────────────

class TestKnowledgeBase:
    def test_list_articles(self, client, auth_headers):
        assert client.get("/api/knowledge-base/articles", headers=auth_headers).status_code == 200

    def test_get_article(self, client, auth_headers):
        assert client.get("/api/knowledge-base/articles/1", headers=auth_headers).status_code == 200

    def test_create_article(self, client, auth_headers):
        r = client.post("/api/knowledge-base/articles", headers=auth_headers, json={
            "title": "Test Article", "content": "Test content",
        })
        assert r.status_code == 201

    def test_update_article(self, client, auth_headers):
        assert client.put("/api/knowledge-base/articles/1", headers=auth_headers, json={"title": "Updated"}).status_code == 200

    def test_delete_article(self, client, auth_headers):
        assert client.delete("/api/knowledge-base/articles/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/knowledge-base/articles/9999", headers=auth_headers).status_code == 404

    def test_list_categories(self, client, auth_headers):
        assert client.get("/api/knowledge-base/categories", headers=auth_headers).status_code == 200

    def test_list_tags(self, client, auth_headers):
        assert client.get("/api/knowledge-base/tags", headers=auth_headers).status_code == 200


# ── 28. MANUFACTURING (/api/manufacturing) ───────────────────────────────

class TestManufacturing:
    def test_list_production_lines(self, client, auth_headers):
        assert client.get("/api/manufacturing/production-lines/", headers=auth_headers).status_code == 200

    def test_get_production_line(self, client, auth_headers):
        assert client.get("/api/manufacturing/production-lines/1", headers=auth_headers).status_code == 200

    def test_create_production_line(self, client, auth_headers):
        r = client.post("/api/manufacturing/production-lines/", headers=auth_headers, json={
            "name": "Test Line", "code": "TL-001", "status": "active",
            "capacity_per_hour": 100.0,
        })
        assert r.status_code == 201

    def test_update_production_line(self, client, auth_headers):
        assert client.put("/api/manufacturing/production-lines/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete_production_line(self, client, auth_headers):
        assert client.delete("/api/manufacturing/production-lines/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/manufacturing/production-lines/9999", headers=auth_headers).status_code == 404

    def test_list_work_orders(self, client, auth_headers):
        assert client.get("/api/manufacturing/work-orders/", headers=auth_headers).status_code == 200

    def test_list_quality_checks(self, client, auth_headers):
        assert client.get("/api/manufacturing/quality-checks/", headers=auth_headers).status_code == 200


# ── 29. MONITORING (/api/monitoring) ─────────────────────────────────────

class TestMonitoring:
    def test_list_monitors(self, client, auth_headers):
        assert client.get("/api/monitoring/monitors", headers=auth_headers).status_code == 200

    def test_get_monitor(self, client, auth_headers):
        assert client.get("/api/monitoring/monitors/1", headers=auth_headers).status_code == 200

    def test_create_monitor(self, client, auth_headers):
        r = client.post("/api/monitoring/monitors", headers=auth_headers, json={
            "name": "Test Monitor", "metric": "cpu",
        })
        assert r.status_code == 201

    def test_update_monitor(self, client, auth_headers):
        assert client.put("/api/monitoring/monitors/1", headers=auth_headers, json={"metric": "memory"}).status_code == 200

    def test_delete_monitor(self, client, auth_headers):
        assert client.delete("/api/monitoring/monitors/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/monitoring/monitors/9999", headers=auth_headers).status_code == 404

    def test_list_alert_rules(self, client, auth_headers):
        assert client.get("/api/monitoring/alert-rules", headers=auth_headers).status_code == 200

    def test_list_dashboards(self, client, auth_headers):
        assert client.get("/api/monitoring/dashboards", headers=auth_headers).status_code == 200


# ── 30. NOTIFICATIONS (/api/notifications) ───────────────────────────────

class TestNotifications:
    def test_list(self, client, auth_headers):
        r = client.get("/api/notifications", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_get(self, client, auth_headers):
        assert client.get("/api/notifications/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/notifications", headers=auth_headers, json={
            "title": "Test Notif", "message": "Test", "type": "info",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/notifications/1", headers=auth_headers, json={"read": True}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/notifications/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/notifications/9999", headers=auth_headers).status_code == 404

    def test_invalid_type(self, client, auth_headers):
        r = client.post("/api/notifications", headers=auth_headers, json={
            "title": "Bad", "message": "Test", "type": "invalid",
        })
        assert r.status_code == 422


# ── 31. OPPORTUNITIES (/api/opportunities) ───────────────────────────────

class TestOpportunities:
    def test_list(self, client, auth_headers):
        assert client.get("/api/opportunities/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/opportunities/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/opportunities/", headers=auth_headers, json={
            "title": "Test Opp", "value": 50000.0, "stage": "qualification",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/opportunities/1", headers=auth_headers, json={"stage": "negotiation"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/opportunities/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/opportunities/9999", headers=auth_headers).status_code == 404


# ── 32. ORDERS (/api/orders) ─────────────────────────────────────────────

class TestOrders:
    def test_list(self, client, auth_headers):
        assert client.get("/api/orders/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/orders/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/orders", headers=auth_headers, json={
            "customer_id": 1,
            "items": [{"product_id": 1, "quantity": 2, "unit_price": 10.0}],
            "status": "pending",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/orders/1", headers=auth_headers, json={"status": "shipped"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/orders/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/orders/9999", headers=auth_headers).status_code == 404

    def test_invalid_status(self, client, auth_headers):
        r = client.post("/api/orders", headers=auth_headers, json={
            "customer_id": 1,
            "items": [{"product_id": 1, "quantity": 1, "unit_price": 10.0}],
            "status": "invalid",
        })
        assert r.status_code == 422


# ── 33. PAYMENTS (/api/payments) ─────────────────────────────────────────

class TestPayments:
    def test_list(self, client, auth_headers):
        assert client.get("/api/payments/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/payments/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/payments", headers=auth_headers, json={
            "amount": 100.0, "method": "credit_card",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/payments/1", headers=auth_headers, json={"amount": 200.0}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/payments/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/payments/9999", headers=auth_headers).status_code == 404


# ── 34. PERMISSIONS (/api/permissions) ───────────────────────────────────

class TestPermissions:
    def test_list(self, client, auth_headers):
        assert client.get("/api/permissions/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/permissions/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/permissions/", headers=auth_headers, json={
            "name": "Test Permission", "resource": "users", "action": "read",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/permissions/1", headers=auth_headers, json={"action": "write"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/permissions/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/permissions/9999", headers=auth_headers).status_code == 404


# ── 35. PRODUCTS (/api/products) ─────────────────────────────────────────

class TestProducts:
    def test_list(self, client, auth_headers):
        assert client.get("/api/products", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/products/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/products", headers=auth_headers, json={
            "name": "Test Product", "price": 10.0, "stock": 100,
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/products/1", headers=auth_headers, json={"price": 20.0}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/products/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/products/9999", headers=auth_headers).status_code == 404

    def test_negative_price(self, client, auth_headers):
        r = client.post("/api/products", headers=auth_headers, json={
            "name": "Bad", "price": -1.0, "stock": 10,
        })
        assert r.status_code == 422


# ── 36. PROJECT MGMT (/api/project-mgmt) ─────────────────────────────────

class TestProjectMgmt:
    def test_list_projects(self, client, auth_headers):
        assert client.get("/api/project-mgmt/projects", headers=auth_headers).status_code == 200

    def test_get_project(self, client, auth_headers):
        assert client.get("/api/project-mgmt/projects/1", headers=auth_headers).status_code == 200

    def test_create_project(self, client, auth_headers):
        r = client.post("/api/project-mgmt/projects", headers=auth_headers, json={
            "name": "Test Project", "status": "active",
        })
        assert r.status_code == 201

    def test_update_project(self, client, auth_headers):
        assert client.put("/api/project-mgmt/projects/1", headers=auth_headers, json={"status": "completed"}).status_code == 200

    def test_delete_project(self, client, auth_headers):
        assert client.delete("/api/project-mgmt/projects/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/project-mgmt/projects/9999", headers=auth_headers).status_code == 404

    def test_list_milestones(self, client, auth_headers):
        assert client.get("/api/project-mgmt/milestones", headers=auth_headers).status_code == 200


# ── 37. PROJECTS (/api/projects) ─────────────────────────────────────────

class TestProjects:
    def test_list(self, client, auth_headers):
        r = client.get("/api/projects", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_get(self, client, auth_headers):
        assert client.get("/api/projects/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/projects", headers=auth_headers, json={
            "name": "Test Project", "status": "active",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/projects/1", headers=auth_headers, json={"status": "completed"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/projects/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/projects/9999", headers=auth_headers).status_code == 404

    def test_invalid_status(self, client, auth_headers):
        r = client.post("/api/projects", headers=auth_headers, json={
            "name": "Bad", "status": "invalid",
        })
        assert r.status_code == 422


# ── 38. REPORTING (/api/reporting) ───────────────────────────────────────

class TestReporting:
    def test_list_reports(self, client, auth_headers):
        assert client.get("/api/reporting/reports", headers=auth_headers).status_code == 200

    def test_get_report(self, client, auth_headers):
        assert client.get("/api/reporting/reports/1", headers=auth_headers).status_code == 200

    def test_create_report(self, client, auth_headers):
        r = client.post("/api/reporting/reports", headers=auth_headers, json={
            "name": "Test Report", "type": "financial",
        })
        assert r.status_code == 201

    def test_update_report(self, client, auth_headers):
        assert client.put("/api/reporting/reports/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete_report(self, client, auth_headers):
        assert client.delete("/api/reporting/reports/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/reporting/reports/9999", headers=auth_headers).status_code == 404

    def test_list_templates(self, client, auth_headers):
        assert client.get("/api/reporting/templates", headers=auth_headers).status_code == 200


# ── 39. ROLES (/api/roles) ──────────────────────────────────────────────

class TestRoles:
    def test_list(self, client, auth_headers):
        assert client.get("/api/roles/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/roles/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/roles/", headers=auth_headers, json={
            "name": "Test Role", "permissions": [],
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/roles/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/roles/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/roles/9999", headers=auth_headers).status_code == 404


# ── 40. SUPPLY CHAIN (/api/supply-chain) ─────────────────────────────────

class TestSupplyChain:
    def test_list_suppliers(self, client, auth_headers):
        assert client.get("/api/supply-chain/suppliers", headers=auth_headers).status_code == 200

    def test_get_supplier(self, client, auth_headers):
        assert client.get("/api/supply-chain/suppliers/1", headers=auth_headers).status_code == 200

    def test_create_supplier(self, client, auth_headers):
        r = client.post("/api/supply-chain/suppliers", headers=auth_headers, json={
            "name": "Test Supplier",
        })
        assert r.status_code == 201

    def test_update_supplier(self, client, auth_headers):
        assert client.put("/api/supply-chain/suppliers/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete_supplier(self, client, auth_headers):
        assert client.delete("/api/supply-chain/suppliers/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/supply-chain/suppliers/9999", headers=auth_headers).status_code == 404

    def test_list_purchase_orders(self, client, auth_headers):
        assert client.get("/api/supply-chain/purchase-orders", headers=auth_headers).status_code == 200


# ── 41. TASKS (/api/tasks) ───────────────────────────────────────────────

class TestTasks:
    def test_list(self, client, auth_headers):
        assert client.get("/api/tasks", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/tasks/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/tasks", headers=auth_headers, json={
            "title": "Test Task", "status": "todo", "priority": "high",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/tasks/1", headers=auth_headers, json={"status": "done"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/tasks/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/tasks/9999", headers=auth_headers).status_code == 404

    def test_invalid_priority(self, client, auth_headers):
        r = client.post("/api/tasks", headers=auth_headers, json={
            "title": "Bad", "priority": "urgent",
        })
        assert r.status_code == 422


# ── 42. USERS (/api/users) ───────────────────────────────────────────────

class TestUsers:
    def test_list(self, client, auth_headers):
        assert client.get("/api/users/", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/users/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/users/", headers=auth_headers, json={
            "name": "Test User", "email": "test@example.com",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/users/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/users/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/users/9999", headers=auth_headers).status_code == 404

    def test_invalid_email(self, client, auth_headers):
        r = client.post("/api/users/", headers=auth_headers, json={
            "name": "Bad", "email": "not-an-email",
        })
        assert r.status_code == 422


# ── 43. WORKFLOWS (/api/workflows) ───────────────────────────────────────

class TestWorkflows:
    def test_list(self, client, auth_headers):
        assert client.get("/api/workflows", headers=auth_headers).status_code == 200

    def test_get(self, client, auth_headers):
        assert client.get("/api/workflows/1", headers=auth_headers).status_code == 200

    def test_create(self, client, auth_headers):
        r = client.post("/api/workflows", headers=auth_headers, json={
            "name": "Test Workflow",
        })
        assert r.status_code == 201

    def test_update(self, client, auth_headers):
        assert client.put("/api/workflows/1", headers=auth_headers, json={"name": "Updated"}).status_code == 200

    def test_delete(self, client, auth_headers):
        assert client.delete("/api/workflows/1", headers=auth_headers).status_code == 204

    def test_get_nonexistent(self, client, auth_headers):
        assert client.get("/api/workflows/9999", headers=auth_headers).status_code == 404

    def test_list_steps(self, client, auth_headers):
        assert client.get("/api/workflows/1/steps", headers=auth_headers).status_code == 200

    def test_list_runs(self, client, auth_headers):
        assert client.get("/api/workflows/1/runs", headers=auth_headers).status_code == 200


# ── Cross-cutting: Auth & Error Handling ──────────────────────────────────

class TestAuthAndErrors:
    def test_missing_api_key(self, client):
        r = client.get("/api/accounts/")
        assert r.status_code == 401

    def test_invalid_api_key(self, client):
        r = client.get("/api/accounts/", headers={"X-API-Key": "wrong"})
        assert r.status_code == 401

    def test_health_check_no_auth(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_not_found_route(self, client, auth_headers):
        r = client.get("/api/nonexistent", headers=auth_headers)
        assert r.status_code == 404

    def test_dashboard_generic_crud(self, client, auth_headers):
        """Test the generic CRUD routes from main.py RESOURCES."""
        r = client.get("/api/dashboard", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_generic_crud_create(self, client, auth_headers):
        r = client.post("/api/dashboard", headers=auth_headers, json={"test": "data"})
        assert r.status_code == 201

    def test_generic_crud_get(self, client, auth_headers):
        r = client.post("/api/dashboard", headers=auth_headers, json={"test": "data"})
        item_id = r.json()["id"]
        r = client.get(f"/api/dashboard/{item_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_generic_crud_update(self, client, auth_headers):
        r = client.post("/api/dashboard", headers=auth_headers, json={"test": "data"})
        item_id = r.json()["id"]
        r = client.put(f"/api/dashboard/{item_id}", headers=auth_headers, json={"updated": True})
        assert r.status_code == 200

    def test_generic_crud_delete(self, client, auth_headers):
        r = client.post("/api/dashboard", headers=auth_headers, json={"test": "data"})
        item_id = r.json()["id"]
        r = client.delete(f"/api/dashboard/{item_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_get_all_data(self, client, auth_headers):
        r = client.get("/api/all", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), dict)