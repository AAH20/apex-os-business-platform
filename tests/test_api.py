"""Tests for the REST API layer."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apex_os_bp.api.app import create_api_app
from apex_os_bp.core.config import Config


@pytest.fixture
def app(monkeypatch):
    """Create a test FastAPI app."""
    monkeypatch.setenv("ADMIN_PASSWORD", "admin12345")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key")
    config = Config()
    config.set("api.rate_limit.max_requests", 1000)
    config.set("api.rate_limit.window_seconds", 60)
    return create_api_app(config)


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers by logging in as admin."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin12345"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Health ───────────────────────────────────────────────────────────────────

class TestHealth:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Health check returns 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "components" in data

    def test_health_check_no_auth_required(self, client):
        """Health check does not require authentication."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200


# ─── Auth ─────────────────────────────────────────────────────────────────────

class TestAuth:
    """Test authentication endpoints."""

    def test_login_success(self, client):
        """Admin can login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600

    def test_login_invalid_credentials(self, client):
        """Invalid credentials return 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """Missing fields return 422."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin"},
        )
        assert response.status_code == 422

    def test_register_success(self, client):
        """New user can register."""
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "email": "new@example.com", "password": "password123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"

    def test_register_duplicate_username(self, client):
        """Duplicate username returns 409."""
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "admin", "email": "other@example.com", "password": "password123"},
        )
        assert response.status_code == 409

    def test_register_invalid_email(self, client):
        """Invalid email returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "test", "email": "not-an-email", "password": "password123"},
        )
        assert response.status_code == 422

    def test_register_short_password(self, client):
        """Short password returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "test", "email": "test@example.com", "password": "short"},
        )
        assert response.status_code == 422

    def test_get_current_user(self, client, auth_headers):
        """Authenticated user can get their profile."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"

    def test_get_current_user_no_auth(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_logout(self, client, auth_headers):
        """User can logout."""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200

    def test_protected_route_without_token(self, client):
        """Protected route returns 401 without token."""
        response = client.get("/api/v1/crm/contacts")
        assert response.status_code == 401

    def test_protected_route_with_invalid_token(self, client):
        """Protected route returns 401 with invalid token."""
        response = client.get(
            "/api/v1/crm/contacts",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


# ─── CRM Contacts ─────────────────────────────────────────────────────────────

class TestCRMContacts:
    """Test CRM contact endpoints."""

    def test_create_contact(self, client, auth_headers):
        """Create a new contact."""
        response = client.post(
            "/api/v1/crm/contacts",
            headers=auth_headers,
            json={"name": "John Doe", "email": "john@example.com"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert "id" in data

    def test_create_contact_with_optional_fields(self, client, auth_headers):
        """Create contact with all fields."""
        response = client.post(
            "/api/v1/crm/contacts",
            headers=auth_headers,
            json={
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "+1234567890",
                "company": "Acme Inc",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["phone"] == "+1234567890"
        assert data["company"] == "Acme Inc"

    def test_create_contact_invalid_email(self, client, auth_headers):
        """Invalid email returns 422."""
        response = client.post(
            "/api/v1/crm/contacts",
            headers=auth_headers,
            json={"name": "John", "email": "not-an-email"},
        )
        assert response.status_code == 422

    def test_list_contacts(self, client, auth_headers):
        """List all contacts."""
        # Create a contact first
        client.post(
            "/api/v1/crm/contacts",
            headers=auth_headers,
            json={"name": "Test", "email": "test@example.com"},
        )
        response = client.get("/api/v1/crm/contacts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_contact(self, client, auth_headers):
        """Get a contact by ID."""
        create_resp = client.post(
            "/api/v1/crm/contacts",
            headers=auth_headers,
            json={"name": "Test", "email": "test@example.com"},
        )
        contact_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/crm/contacts/{contact_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Test"

    def test_get_contact_not_found(self, client, auth_headers):
        """Non-existent contact returns 404."""
        response = client.get("/api/v1/crm/contacts/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_update_contact(self, client, auth_headers):
        """Update a contact."""
        create_resp = client.post(
            "/api/v1/crm/contacts",
            headers=auth_headers,
            json={"name": "Test", "email": "test@example.com"},
        )
        contact_id = create_resp.json()["id"]
        response = client.put(
            f"/api/v1/crm/contacts/{contact_id}",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_update_contact_not_found(self, client, auth_headers):
        """Updating non-existent contact returns 404."""
        response = client.put(
            "/api/v1/crm/contacts/nonexistent",
            headers=auth_headers,
            json={"name": "Updated"},
        )
        assert response.status_code == 404

    def test_delete_contact(self, client, auth_headers):
        """Delete a contact."""
        create_resp = client.post(
            "/api/v1/crm/contacts",
            headers=auth_headers,
            json={"name": "Test", "email": "test@example.com"},
        )
        contact_id = create_resp.json()["id"]
        response = client.delete(f"/api/v1/crm/contacts/{contact_id}", headers=auth_headers)
        assert response.status_code == 204
        # Verify it's gone
        get_resp = client.get(f"/api/v1/crm/contacts/{contact_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_delete_contact_not_found(self, client, auth_headers):
        """Deleting non-existent contact returns 404."""
        response = client.delete("/api/v1/crm/contacts/nonexistent", headers=auth_headers)
        assert response.status_code == 404


# ─── CRM Deals ────────────────────────────────────────────────────────────────

class TestCRMDeals:
    """Test CRM deal endpoints."""

    def test_create_deal(self, client, auth_headers):
        """Create a new deal."""
        response = client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "Big Deal", "value": 10000.0},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Big Deal"
        assert data["value"] == 10000.0
        assert data["stage"] == "lead"

    def test_create_deal_with_contact(self, client, auth_headers):
        """Create a deal linked to a contact."""
        contact_resp = client.post(
            "/api/v1/crm/contacts",
            headers=auth_headers,
            json={"name": "Test", "email": "test@example.com"},
        )
        contact_id = contact_resp.json()["id"]
        response = client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "Deal", "value": 5000.0, "contact_id": contact_id},
        )
        assert response.status_code == 201
        assert response.json()["contact_id"] == contact_id

    def test_create_deal_invalid_value(self, client, auth_headers):
        """Negative value returns 422."""
        response = client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "Deal", "value": -100},
        )
        assert response.status_code == 422

    def test_list_deals(self, client, auth_headers):
        """List all deals."""
        client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "Deal 1", "value": 1000.0},
        )
        response = client.get("/api/v1/crm/deals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_deal(self, client, auth_headers):
        """Get a deal by ID."""
        create_resp = client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "Test Deal", "value": 1000.0},
        )
        deal_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/crm/deals/{deal_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Test Deal"

    def test_get_deal_not_found(self, client, auth_headers):
        """Non-existent deal returns 404."""
        response = client.get("/api/v1/crm/deals/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_update_deal(self, client, auth_headers):
        """Update a deal."""
        create_resp = client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "Deal", "value": 1000.0},
        )
        deal_id = create_resp.json()["id"]
        response = client.put(
            f"/api/v1/crm/deals/{deal_id}",
            headers=auth_headers,
            json={"stage": "qualified"},
        )
        assert response.status_code == 200
        assert response.json()["stage"] == "qualified"

    def test_delete_deal(self, client, auth_headers):
        """Delete a deal."""
        create_resp = client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "Deal", "value": 1000.0},
        )
        deal_id = create_resp.json()["id"]
        response = client.delete(f"/api/v1/crm/deals/{deal_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_pipeline_report(self, client, auth_headers):
        """Get pipeline report."""
        client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "Deal 1", "value": 1000.0},
        )
        client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "Deal 2", "value": 2000.0},
        )
        response = client.get("/api/v1/crm/pipeline", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_deals"] >= 2
        assert data["total_value"] >= 3000.0
        assert "deals_by_stage" in data


# ─── Accounting ───────────────────────────────────────────────────────────────

class TestAccounting:
    """Test accounting endpoints."""

    def test_list_accounts(self, client, auth_headers):
        """List all accounts."""
        response = client.get("/api/v1/accounting/accounts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # AR and Revenue

    def test_create_account(self, client, auth_headers):
        """Create a new account."""
        response = client.post(
            "/api/v1/accounting/accounts",
            headers=auth_headers,
            json={"name": "Cash", "type": "asset"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Cash"
        assert data["type"] == "asset"

    def test_create_account_invalid_type(self, client, auth_headers):
        """Invalid account type returns 422."""
        response = client.post(
            "/api/v1/accounting/accounts",
            headers=auth_headers,
            json={"name": "Test", "type": "invalid"},
        )
        assert response.status_code == 422

    def test_get_account(self, client, auth_headers):
        """Get an account by ID."""
        create_resp = client.post(
            "/api/v1/accounting/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "type": "expense"},
        )
        account_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/accounting/accounts/{account_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Test Account"

    def test_update_account(self, client, auth_headers):
        """Update an account."""
        create_resp = client.post(
            "/api/v1/accounting/accounts",
            headers=auth_headers,
            json={"name": "Test", "type": "expense"},
        )
        account_id = create_resp.json()["id"]
        response = client.put(
            f"/api/v1/accounting/accounts/{account_id}",
            headers=auth_headers,
            json={"name": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_delete_account(self, client, auth_headers):
        """Delete an account."""
        create_resp = client.post(
            "/api/v1/accounting/accounts",
            headers=auth_headers,
            json={"name": "Test", "type": "expense"},
        )
        account_id = create_resp.json()["id"]
        response = client.delete(f"/api/v1/accounting/accounts/{account_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_create_invoice(self, client, auth_headers):
        """Create a new invoice."""
        response = client.post(
            "/api/v1/accounting/invoices",
            headers=auth_headers,
            json={
                "customer_id": "cust-1",
                "items": [
                    {"description": "Widget", "quantity": 2, "unit_price": 50.0},
                    {"description": "Gadget", "quantity": 1, "unit_price": 100.0},
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["customer_id"] == "cust-1"
        assert data["total"] == 200.0
        assert data["status"] == "draft"

    def test_create_invoice_empty_items(self, client, auth_headers):
        """Empty items list returns 422."""
        response = client.post(
            "/api/v1/accounting/invoices",
            headers=auth_headers,
            json={"customer_id": "cust-1", "items": []},
        )
        assert response.status_code == 422

    def test_list_invoices(self, client, auth_headers):
        """List all invoices."""
        response = client.get("/api/v1/accounting/invoices", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_invoice(self, client, auth_headers):
        """Get an invoice by ID."""
        create_resp = client.post(
            "/api/v1/accounting/invoices",
            headers=auth_headers,
            json={
                "customer_id": "cust-1",
                "items": [{"description": "Widget", "quantity": 1, "unit_price": 100.0}],
            },
        )
        invoice_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/accounting/invoices/{invoice_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_post_invoice(self, client, auth_headers):
        """Post an invoice to the ledger."""
        create_resp = client.post(
            "/api/v1/accounting/invoices",
            headers=auth_headers,
            json={
                "customer_id": "cust-1",
                "items": [{"description": "Widget", "quantity": 1, "unit_price": 100.0}],
            },
        )
        invoice_id = create_resp.json()["id"]
        response = client.post(
            f"/api/v1/accounting/invoices/{invoice_id}/post",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "posted"

    def test_post_invoice_not_found(self, client, auth_headers):
        """Posting non-existent invoice returns 404."""
        response = client.post(
            "/api/v1/accounting/invoices/nonexistent/post",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_create_journal_entry(self, client, auth_headers):
        """Create a balanced journal entry."""
        # Get account IDs
        accounts_resp = client.get("/api/v1/accounting/accounts", headers=auth_headers)
        accounts = accounts_resp.json()
        ar_account = next(a for a in accounts if a["name"] == "Accounts Receivable")
        revenue_account = next(a for a in accounts if a["name"] == "Revenue")

        response = client.post(
            "/api/v1/accounting/journal-entries",
            headers=auth_headers,
            json={
                "description": "Test entry",
                "lines": [
                    {"account_id": ar_account["id"], "debit": 100.0, "credit": 0.0},
                    {"account_id": revenue_account["id"], "debit": 0.0, "credit": 100.0},
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Test entry"
        assert len(data["lines"]) == 2

    def test_create_journal_entry_unbalanced(self, client, auth_headers):
        """Unbalanced journal entry returns 400."""
        accounts_resp = client.get("/api/v1/accounting/accounts", headers=auth_headers)
        accounts = accounts_resp.json()
        ar_account = next(a for a in accounts if a["name"] == "Accounts Receivable")
        revenue_account = next(a for a in accounts if a["name"] == "Revenue")

        response = client.post(
            "/api/v1/accounting/journal-entries",
            headers=auth_headers,
            json={
                "description": "Bad entry",
                "lines": [
                    {"account_id": ar_account["id"], "debit": 100.0, "credit": 0.0},
                    {"account_id": revenue_account["id"], "debit": 0.0, "credit": 50.0},
                ],
            },
        )
        assert response.status_code == 400

    def test_list_journal_entries(self, client, auth_headers):
        """List all journal entries."""
        response = client.get("/api/v1/accounting/journal-entries", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_trial_balance(self, client, auth_headers):
        """Get trial balance."""
        response = client.get("/api/v1/accounting/trial-balance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "trial_balance" in data
        assert "is_balanced" in data


# ─── Analytics ────────────────────────────────────────────────────────────────

class TestAnalytics:
    """Test analytics endpoints."""

    def test_track_metric(self, client, auth_headers):
        """Track a new metric."""
        response = client.post(
            "/api/v1/analytics/metrics",
            headers=auth_headers,
            json={"name": "revenue", "value": 1000.0, "unit": "USD"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "revenue"
        assert data["value"] == 1000.0

    def test_list_metrics(self, client, auth_headers):
        """List all metrics."""
        client.post(
            "/api/v1/analytics/metrics",
            headers=auth_headers,
            json={"name": "test_metric", "value": 42.0, "unit": "count"},
        )
        response = client.get("/api/v1/analytics/metrics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_metric_history(self, client, auth_headers):
        """Get metric time series."""
        client.post(
            "/api/v1/analytics/metrics",
            headers=auth_headers,
            json={"name": "history_test", "value": 1.0, "unit": "count"},
        )
        client.post(
            "/api/v1/analytics/metrics",
            headers=auth_headers,
            json={"name": "history_test", "value": 2.0, "unit": "count"},
        )
        response = client.get("/api/v1/analytics/metrics/history_test", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_metric_not_found(self, client, auth_headers):
        """Non-existent metric returns 404."""
        response = client.get("/api/v1/analytics/metrics/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_get_report(self, client, auth_headers):
        """Get analytics report."""
        client.post(
            "/api/v1/analytics/metrics",
            headers=auth_headers,
            json={"name": "report_test", "value": 100.0, "unit": "USD"},
        )
        response = client.get("/api/v1/analytics/report", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data

    def test_create_dashboard(self, client, auth_headers):
        """Create a new dashboard."""
        response = client.post(
            "/api/v1/analytics/dashboards",
            headers=auth_headers,
            json={"name": "Test Dashboard"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Dashboard"

    def test_list_dashboards(self, client, auth_headers):
        """List all dashboards."""
        response = client.get("/api/v1/analytics/dashboards", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_dashboard(self, client, auth_headers):
        """Get a dashboard by name."""
        client.post(
            "/api/v1/analytics/dashboards",
            headers=auth_headers,
            json={"name": "Test Dashboard"},
        )
        response = client.get("/api/v1/analytics/dashboards/Test Dashboard", headers=auth_headers)
        assert response.status_code == 200

    def test_get_dashboard_not_found(self, client, auth_headers):
        """Non-existent dashboard returns 404."""
        response = client.get("/api/v1/analytics/dashboards/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_add_metric_to_dashboard(self, client, auth_headers):
        """Add a metric to a dashboard."""
        client.post(
            "/api/v1/analytics/dashboards",
            headers=auth_headers,
            json={"name": "Test Dashboard"},
        )
        response = client.post(
            "/api/v1/analytics/dashboards/Test Dashboard/metrics",
            headers=auth_headers,
            json={"name": "dash_metric", "value": 42.0, "unit": "count"},
        )
        assert response.status_code == 200
        assert response.json()["total_metrics"] == 1


# ─── Workflows ────────────────────────────────────────────────────────────────

class TestWorkflows:
    """Test workflow endpoints."""

    def test_create_workflow(self, client, auth_headers):
        """Create a new workflow."""
        response = client.post(
            "/api/v1/workflows",
            headers=auth_headers,
            json={
                "name": "Test Workflow",
                "steps": [
                    {"name": "step1", "action": "test.action"},
                    {"name": "step2", "action": "test.action2"},
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert len(data["steps"]) == 2

    def test_list_workflows(self, client, auth_headers):
        """List all workflows."""
        response = client.get("/api/v1/workflows", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_workflow(self, client, auth_headers):
        """Get a workflow by name."""
        client.post(
            "/api/v1/workflows",
            headers=auth_headers,
            json={"name": "Test Workflow", "steps": []},
        )
        response = client.get("/api/v1/workflows/Test Workflow", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Test Workflow"

    def test_get_workflow_not_found(self, client, auth_headers):
        """Non-existent workflow returns 404."""
        response = client.get("/api/v1/workflows/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_execute_workflow(self, client, auth_headers):
        """Execute a workflow."""
        client.post(
            "/api/v1/workflows",
            headers=auth_headers,
            json={
                "name": "ExecWorkflow",
                "steps": [{"name": "step1", "action": "test.action"}],
            },
        )
        response = client.post("/api/v1/workflows/ExecWorkflow/execute", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["workflow"] == "ExecWorkflow"
        assert data["status"] == "completed"

    def test_execute_workflow_not_found(self, client, auth_headers):
        """Executing non-existent workflow returns 404."""
        response = client.post("/api/v1/workflows/nonexistent/execute", headers=auth_headers)
        assert response.status_code == 404

    def test_add_step_to_workflow(self, client, auth_headers):
        """Add a step to a workflow."""
        client.post(
            "/api/v1/workflows",
            headers=auth_headers,
            json={"name": "StepWorkflow", "steps": []},
        )
        response = client.post(
            "/api/v1/workflows/StepWorkflow/steps",
            headers=auth_headers,
            json={"name": "new_step", "action": "new.action"},
        )
        assert response.status_code == 200
        assert len(response.json()["steps"]) == 1

    def test_delete_workflow(self, client, auth_headers):
        """Delete a workflow."""
        create_resp = client.post(
            "/api/v1/workflows",
            headers=auth_headers,
            json={"name": "DeleteWorkflow", "steps": []},
        )
        assert create_resp.status_code == 201
        response = client.delete("/api/v1/workflows/DeleteWorkflow", headers=auth_headers)
        assert response.status_code == 204


# ─── Rate Limiting ────────────────────────────────────────────────────────────

class TestRateLimiting:
    """Test rate limiting middleware."""

    def test_rate_limit_headers_present(self, client):
        """Rate limit headers are present in responses."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_exceeded(self, app):
        """Rate limit returns 429 when exceeded."""
        # Create app with very low rate limit
        from apex_os_bp.core.config import Config
        config = Config()
        config.set("api.rate_limit.max_requests", 2)
        config.set("api.rate_limit.window_seconds", 60)
        test_app = create_api_app(config)
        test_client = TestClient(test_app)

        # Make requests up to the limit
        response1 = test_client.get("/api/v1/health")
        assert response1.status_code == 200
        response2 = test_client.get("/api/v1/health")
        assert response2.status_code == 200
        # Third request should be rate limited
        response3 = test_client.get("/api/v1/health")
        assert response3.status_code == 429


# ─── Validation ───────────────────────────────────────────────────────────────

class TestValidation:
    """Test request validation."""

    def test_contact_name_too_long(self, client, auth_headers):
        """Contact name exceeding max length returns 422."""
        response = client.post(
            "/api/v1/crm/contacts",
            headers=auth_headers,
            json={"name": "x" * 300, "email": "test@example.com"},
        )
        assert response.status_code == 422

    def test_deal_title_too_long(self, client, auth_headers):
        """Deal title exceeding max length returns 422."""
        response = client.post(
            "/api/v1/crm/deals",
            headers=auth_headers,
            json={"title": "x" * 600, "value": 100.0},
        )
        assert response.status_code == 422

    def test_invoice_negative_quantity(self, client, auth_headers):
        """Negative quantity returns 422."""
        response = client.post(
            "/api/v1/accounting/invoices",
            headers=auth_headers,
            json={
                "customer_id": "cust-1",
                "items": [{"description": "Widget", "quantity": -1, "unit_price": 10.0}],
            },
        )
        assert response.status_code == 422

    def test_journal_entry_single_line(self, client, auth_headers):
        """Journal entry with single line returns 422."""
        response = client.post(
            "/api/v1/accounting/journal-entries",
            headers=auth_headers,
            json={
                "description": "Bad entry",
                "lines": [{"account_id": "acc-1", "debit": 100.0, "credit": 0.0}],
            },
        )
        assert response.status_code == 422
