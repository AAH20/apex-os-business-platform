"""Comprehensive tests for 10 new route modules.

Modules: accounting, crm, analytics, inventory, hr, projects,
         tasks, alerts, notifications, compliance.
"""
import pytest
from fastapi.testclient import TestClient
from web.backend.main import app, init_data


@pytest.fixture(scope="module", autouse=True)
def reseeded_store():
    """Restore the synthetic data store before this module runs.

    tests/test_all_modules.py runs earlier in the session and DELETES seeded
    entities (e.g. /api/accounts/1 -> 204). init_data() repopulates them; the
    singleton otherwise keeps the post-delete state for every later file.
    """
    init_data()


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
        assert len(r.json()) > 0

    def test_get_account(self, client, auth_headers):
        r = client.get("/api/accounts/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_account(self, client, auth_headers):
        # Real contract (OpenAPI): POST is served at the bare path
        # /api/accounts (only GET lives on the trailing-slash path).
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

    def test_get_nonexistent_account(self, client, auth_headers):
        r = client.get("/api/accounts/9999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_account_invalid_type(self, client, auth_headers):
        # POST lives at the bare path /api/accounts (see test_create_account).
        r = client.post("/api/accounts", headers=auth_headers, json={
            "name": "Bad", "type": "invalid", "code": "0000",
        })
        assert r.status_code == 422


# ── 2. CRM (/api/leads) ───────────────────────────────────────────────────

class TestCRM:
    def test_list_leads(self, client, auth_headers):
        r = client.get("/api/leads/", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_get_lead(self, client, auth_headers):
        r = client.get("/api/leads/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_lead(self, client, auth_headers):
        r = client.post("/api/leads/", headers=auth_headers, json={
            "name": "Test Lead", "email": "test@example.com",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Test Lead"

    def test_update_lead(self, client, auth_headers):
        r = client.put("/api/leads/1", headers=auth_headers, json={"status": "qualified"})
        assert r.status_code == 200
        assert r.json()["status"] == "qualified"

    def test_delete_lead(self, client, auth_headers):
        r = client.delete("/api/leads/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent_lead(self, client, auth_headers):
        r = client.get("/api/leads/9999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_lead_invalid_email(self, client, auth_headers):
        r = client.post("/api/leads/", headers=auth_headers, json={
            "name": "Bad", "email": "not-an-email",
        })
        assert r.status_code == 422


# ── 3. ANALYTICS (/api/dashboards) ────────────────────────────────────────

class TestAnalytics:
    def test_list_dashboards(self, client, auth_headers):
        r = client.get("/api/dashboards", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_dashboard(self, client, auth_headers):
        r = client.get("/api/dashboards/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_dashboard(self, client, auth_headers):
        r = client.post("/api/dashboards", headers=auth_headers, json={
            "name": "Test Dash", "description": "Test", "layout": "grid",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Test Dash"

    def test_update_dashboard(self, client, auth_headers):
        r = client.put("/api/dashboards/1", headers=auth_headers, json={"name": "Updated"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"

    def test_delete_dashboard(self, client, auth_headers):
        r = client.delete("/api/dashboards/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent_dashboard(self, client, auth_headers):
        r = client.get("/api/dashboards/9999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_dashboard_empty_name(self, client, auth_headers):
        r = client.post("/api/dashboards", headers=auth_headers, json={"name": ""})
        assert r.status_code == 422


# ── 4. INVENTORY (/api/inventory) ─────────────────────────────────────────

class TestInventory:
    def test_list_products(self, client, auth_headers):
        r = client.get("/api/inventory/products", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_product(self, client, auth_headers):
        r = client.get("/api/inventory/products/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_product(self, client, auth_headers):
        r = client.post("/api/inventory/products", headers=auth_headers, json={
            "name": "Test Product", "sku": "TEST-001", "price": 10.0,
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Test Product"

    def test_update_product(self, client, auth_headers):
        r = client.put("/api/inventory/products/1", headers=auth_headers, json={"price": 20.0})
        assert r.status_code == 200
        assert r.json()["price"] == 20.0

    def test_delete_product(self, client, auth_headers):
        r = client.delete("/api/inventory/products/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent_product(self, client, auth_headers):
        r = client.get("/api/inventory/products/9999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_product_negative_price(self, client, auth_headers):
        r = client.post("/api/inventory/products", headers=auth_headers, json={
            "name": "Bad", "sku": "BAD-001", "price": -1.0,
        })
        assert r.status_code == 422

    def test_list_categories(self, client, auth_headers):
        r = client.get("/api/inventory/categories", headers=auth_headers)
        assert r.status_code == 200

    def test_list_suppliers(self, client, auth_headers):
        r = client.get("/api/inventory/suppliers", headers=auth_headers)
        assert r.status_code == 200


# ── 5. HR (/api/hr) ──────────────────────────────────────────────────────

class TestHR:
    def test_list_employees(self, client, auth_headers):
        r = client.get("/api/hr/employees", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_get_employee(self, client, auth_headers):
        r = client.get("/api/hr/employees/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_employee(self, client, auth_headers):
        r = client.post("/api/hr/employees", headers=auth_headers, json={
            "first_name": "Test", "last_name": "User",
            "email": "test.user@apex-os.com", "department_id": 1,
            "position_id": 1, "salary": 50000.0, "hire_date": "2024-01-01",
        })
        assert r.status_code == 201
        assert r.json()["first_name"] == "Test"

    def test_update_employee(self, client, auth_headers):
        r = client.put("/api/hr/employees/1", headers=auth_headers, json={"salary": 60000.0})
        assert r.status_code == 200
        assert r.json()["salary"] == 60000.0

    def test_delete_employee(self, client, auth_headers):
        r = client.delete("/api/hr/employees/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent_employee(self, client, auth_headers):
        r = client.get("/api/hr/employees/9999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_employee_duplicate_email(self, client, auth_headers):
        # The 409 duplicate check is real (routes/employees.py compares the
        # posted email against EMPLOYEES_DB). Seed rows are shared module
        # state that other tests in this class mutate (e.g. test_delete_
        # employee removes id 1), so exercise the check on an employee this
        # test creates itself instead of a seed row.
        email = "dup.email.check@apex-os.com"
        first = client.post("/api/hr/employees", headers=auth_headers, json={
            "first_name": "Dup", "last_name": "Email",
            "email": email, "department_id": 1,
            "position_id": 1, "salary": 50000.0, "hire_date": "2024-01-01",
        })
        assert first.status_code == 201, first.text
        second = client.post("/api/hr/employees", headers=auth_headers, json={
            "first_name": "Dup", "last_name": "Email",
            "email": email, "department_id": 1,
            "position_id": 1, "salary": 50000.0, "hire_date": "2024-01-01",
        })
        assert second.status_code == 409

    def test_list_departments(self, client, auth_headers):
        r = client.get("/api/hr/departments", headers=auth_headers)
        assert r.status_code == 200

    def test_list_leave_requests(self, client, auth_headers):
        r = client.get("/api/hr/leave-requests", headers=auth_headers)
        assert r.status_code == 200


# ── 6. PROJECTS (/api/projects) ──────────────────────────────────────────

class TestProjects:
    def test_list_projects(self, client, auth_headers):
        r = client.get("/api/projects", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_get_project(self, client, auth_headers):
        r = client.get("/api/projects/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_project(self, client, auth_headers):
        r = client.post("/api/projects", headers=auth_headers, json={
            "name": "Test Project", "description": "Test", "status": "active",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Test Project"

    def test_update_project(self, client, auth_headers):
        r = client.put("/api/projects/1", headers=auth_headers, json={"status": "completed"})
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_delete_project(self, client, auth_headers):
        r = client.delete("/api/projects/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent_project(self, client, auth_headers):
        r = client.get("/api/projects/9999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_project_invalid_status(self, client, auth_headers):
        r = client.post("/api/projects", headers=auth_headers, json={
            "name": "Bad", "status": "invalid",
        })
        assert r.status_code == 422


# ── 7. TASKS (/api/tasks) ─────────────────────────────────────────────────

class TestTasks:
    def test_list_tasks(self, client, auth_headers):
        r = client.get("/api/tasks", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_task(self, client, auth_headers):
        r = client.get("/api/tasks/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_task(self, client, auth_headers):
        r = client.post("/api/tasks", headers=auth_headers, json={
            "title": "Test Task", "status": "todo", "priority": "high",
        })
        assert r.status_code == 201
        assert r.json()["title"] == "Test Task"

    def test_update_task(self, client, auth_headers):
        r = client.put("/api/tasks/1", headers=auth_headers, json={"status": "done"})
        assert r.status_code == 200
        assert r.json()["status"] == "done"

    def test_delete_task(self, client, auth_headers):
        r = client.delete("/api/tasks/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent_task(self, client, auth_headers):
        r = client.get("/api/tasks/9999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_task_invalid_priority(self, client, auth_headers):
        r = client.post("/api/tasks", headers=auth_headers, json={
            "title": "Bad", "priority": "urgent",
        })
        assert r.status_code == 422


# ── 8. ALERTS (/api/alerts) ──────────────────────────────────────────────

class TestAlerts:
    def test_list_alerts(self, client, auth_headers):
        r = client.get("/api/alerts/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_alert(self, client, auth_headers):
        r = client.get("/api/alerts/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_alert(self, client, auth_headers):
        r = client.post("/api/alerts/", headers=auth_headers, json={
            "title": "Test Alert", "message": "Test message", "severity": "info",
        })
        assert r.status_code == 201
        assert r.json()["title"] == "Test Alert"

    def test_update_alert(self, client, auth_headers):
        r = client.put("/api/alerts/1", headers=auth_headers, json={"is_read": True})
        assert r.status_code == 200
        assert r.json()["is_read"] is True

    def test_delete_alert(self, client, auth_headers):
        r = client.delete("/api/alerts/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent_alert(self, client, auth_headers):
        r = client.get("/api/alerts/9999", headers=auth_headers)
        assert r.status_code == 404


# ── 9. NOTIFICATIONS (/api/notifications) ─────────────────────────────────

class TestNotifications:
    def test_list_notifications(self, client, auth_headers):
        r = client.get("/api/notifications", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_get_notification(self, client, auth_headers):
        r = client.get("/api/notifications/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_notification(self, client, auth_headers):
        r = client.post("/api/notifications", headers=auth_headers, json={
            "title": "Test Notif", "message": "Test message", "type": "info",
        })
        assert r.status_code == 201
        assert r.json()["title"] == "Test Notif"

    def test_update_notification(self, client, auth_headers):
        r = client.put("/api/notifications/1", headers=auth_headers, json={"read": True})
        assert r.status_code == 200
        assert r.json()["read"] is True

    def test_delete_notification(self, client, auth_headers):
        r = client.delete("/api/notifications/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent_notification(self, client, auth_headers):
        r = client.get("/api/notifications/9999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_notification_invalid_type(self, client, auth_headers):
        r = client.post("/api/notifications", headers=auth_headers, json={
            "title": "Bad", "message": "Test", "type": "invalid",
        })
        assert r.status_code == 422


# ── 10. COMPLIANCE (/api/compliance) ──────────────────────────────────────

class TestCompliance:
    def test_list_frameworks(self, client, auth_headers):
        r = client.get("/api/compliance/frameworks/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_framework(self, client, auth_headers):
        r = client.get("/api/compliance/frameworks/1", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_create_framework(self, client, auth_headers):
        r = client.post("/api/compliance/frameworks/", headers=auth_headers, json={
            "name": "Test Framework", "version": "1.0", "status": "active",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Test Framework"

    def test_update_framework(self, client, auth_headers):
        r = client.put("/api/compliance/frameworks/1", headers=auth_headers, json={"status": "inactive"})
        assert r.status_code == 200
        assert r.json()["status"] == "inactive"

    def test_delete_framework(self, client, auth_headers):
        r = client.delete("/api/compliance/frameworks/1", headers=auth_headers)
        assert r.status_code == 204

    def test_get_nonexistent_framework(self, client, auth_headers):
        r = client.get("/api/compliance/frameworks/9999", headers=auth_headers)
        assert r.status_code == 404

    def test_list_controls(self, client, auth_headers):
        r = client.get("/api/compliance/controls/", headers=auth_headers)
        assert r.status_code == 200

    def test_list_audits(self, client, auth_headers):
        r = client.get("/api/compliance/audits/", headers=auth_headers)
        assert r.status_code == 200

    def test_list_findings(self, client, auth_headers):
        r = client.get("/api/compliance/findings/", headers=auth_headers)
        assert r.status_code == 200


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
