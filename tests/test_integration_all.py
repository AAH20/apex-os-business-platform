"""Comprehensive integration tests for all APEX-OS Business Platform modules."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from apex_os_bp.api.app import create_api_app
from apex_os_bp.core.config import Config


@pytest.fixture
def app():
    config = Config()
    config.set("api.rate_limit.max_requests", 1000)
    config.set("api.rate_limit.window_seconds", 60)
    return create_api_app(config)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    # ADMIN_PASSWORD env (default 'admin', see conftest) seeds the admin
    # user's password; username is hardcoded 'admin' in the app.
    import os as _os
    pw = _os.environ.get("ADMIN_PASSWORD", "admin")
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": pw})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestHealth:
    def test_health_returns_200(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "healthy" and "version" in d and "components" in d

    def test_health_no_auth_required(self, client):
        assert client.get("/api/v1/health").status_code == 200

class TestAuth:
    def test_login_success(self, client):
        # credential = admin / ADMIN_PASSWORD (default 'admin', see conftest)
        import os as _os
        pw = _os.environ.get("ADMIN_PASSWORD", "admin")
        r = client.post("/api/v1/auth/login",
                        json={"username": "admin", "password": pw})
        assert r.status_code == 200 and "access_token" in r.json() \
            and r.json()["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401

    def test_login_missing_fields(self, client):
        assert client.post("/api/v1/auth/login", json={"username": "admin"}).status_code == 422

    def test_register_success(self, client):
        r = client.post("/api/v1/auth/register", json={"username": "newuser", "email": "new@example.com", "password": "password123"})
        assert r.status_code == 201 and r.json()["username"] == "newuser"

    def test_register_duplicate_username(self, client):
        r = client.post("/api/v1/auth/register", json={"username": "admin", "email": "other@example.com", "password": "password123"})
        assert r.status_code == 409

    def test_get_current_user(self, client, auth_headers):
        r = client.get("/api/v1/auth/me", headers=auth_headers)
        assert r.status_code == 200 and r.json()["username"] == "admin"

    def test_get_current_user_no_auth(self, client):
        assert client.get("/api/v1/auth/me").status_code == 401

    def test_logout(self, client, auth_headers):
        assert client.post("/api/v1/auth/logout", headers=auth_headers).status_code == 200

    def test_protected_route_without_token(self, client):
        assert client.get("/api/v1/crm/contacts").status_code == 401

    def test_protected_route_with_invalid_token(self, client):
        r = client.get("/api/v1/crm/contacts", headers={"Authorization": "Bearer invalid-token"})
        assert r.status_code == 401


class TestCRMContacts:
    def test_create_contact(self, client, auth_headers):
        r = client.post("/api/v1/crm/contacts", headers=auth_headers, json={"name": "John Doe", "email": "john@example.com"})
        assert r.status_code == 201 and r.json()["name"] == "John Doe" and "id" in r.json()

    def test_create_contact_invalid_email(self, client, auth_headers):
        r = client.post("/api/v1/crm/contacts", headers=auth_headers, json={"name": "John", "email": "not-an-email"})
        assert r.status_code == 422

    def test_list_contacts(self, client, auth_headers):
        client.post("/api/v1/crm/contacts", headers=auth_headers, json={"name": "Test", "email": "test@example.com"})
        r = client.get("/api/v1/crm/contacts", headers=auth_headers)
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_get_contact(self, client, auth_headers):
        cid = client.post("/api/v1/crm/contacts", headers=auth_headers, json={"name": "Test", "email": "test@example.com"}).json()["id"]
        r = client.get(f"/api/v1/crm/contacts/{cid}", headers=auth_headers)
        assert r.status_code == 200 and r.json()["name"] == "Test"

    def test_get_contact_not_found(self, client, auth_headers):
        assert client.get("/api/v1/crm/contacts/nonexistent", headers=auth_headers).status_code == 404

    def test_update_contact(self, client, auth_headers):
        cid = client.post("/api/v1/crm/contacts", headers=auth_headers, json={"name": "Test", "email": "test@example.com"}).json()["id"]
        r = client.put(f"/api/v1/crm/contacts/{cid}", headers=auth_headers, json={"name": "Updated"})
        assert r.status_code == 200 and r.json()["name"] == "Updated"

    def test_delete_contact(self, client, auth_headers):
        cid = client.post("/api/v1/crm/contacts", headers=auth_headers, json={"name": "Test", "email": "test@example.com"}).json()["id"]
        assert client.delete(f"/api/v1/crm/contacts/{cid}", headers=auth_headers).status_code == 204
        assert client.get(f"/api/v1/crm/contacts/{cid}", headers=auth_headers).status_code == 404


class TestCRMDeals:
    def test_create_deal(self, client, auth_headers):
        r = client.post("/api/v1/crm/deals", headers=auth_headers, json={"title": "Big Deal", "value": 10000.0})
        assert r.status_code == 201 and r.json()["title"] == "Big Deal" and r.json()["stage"] == "lead"

    def test_create_deal_invalid_value(self, client, auth_headers):
        assert client.post("/api/v1/crm/deals", headers=auth_headers, json={"title": "Deal", "value": -100}).status_code == 422

    def test_list_deals(self, client, auth_headers):
        client.post("/api/v1/crm/deals", headers=auth_headers, json={"title": "Deal 1", "value": 1000.0})
        r = client.get("/api/v1/crm/deals", headers=auth_headers)
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_get_deal_not_found(self, client, auth_headers):
        assert client.get("/api/v1/crm/deals/nonexistent", headers=auth_headers).status_code == 404

    def test_update_deal(self, client, auth_headers):
        did = client.post("/api/v1/crm/deals", headers=auth_headers, json={"title": "Deal", "value": 1000.0}).json()["id"]
        r = client.put(f"/api/v1/crm/deals/{did}", headers=auth_headers, json={"stage": "qualified"})
        assert r.status_code == 200 and r.json()["stage"] == "qualified"

    def test_delete_deal(self, client, auth_headers):
        did = client.post("/api/v1/crm/deals", headers=auth_headers, json={"title": "Deal", "value": 1000.0}).json()["id"]
        assert client.delete(f"/api/v1/crm/deals/{did}", headers=auth_headers).status_code == 204

    def test_pipeline_report(self, client, auth_headers):
        client.post("/api/v1/crm/deals", headers=auth_headers, json={"title": "Deal 1", "value": 1000.0})
        r = client.get("/api/v1/crm/pipeline", headers=auth_headers)
        assert r.status_code == 200 and "total_deals" in r.json() and "total_value" in r.json()


class TestAccounting:
    def test_list_accounts(self, client, auth_headers):
        r = client.get("/api/v1/accounting/accounts", headers=auth_headers)
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_create_account(self, client, auth_headers):
        r = client.post("/api/v1/accounting/accounts", headers=auth_headers, json={"name": "Cash", "type": "asset"})
        assert r.status_code == 201 and r.json()["name"] == "Cash"

    def test_create_account_invalid_type(self, client, auth_headers):
        assert client.post("/api/v1/accounting/accounts", headers=auth_headers, json={"name": "Test", "type": "invalid"}).status_code == 422

    def test_get_account_not_found(self, client, auth_headers):
        assert client.get("/api/v1/accounting/accounts/nonexistent", headers=auth_headers).status_code == 404

    def test_create_invoice(self, client, auth_headers):
        r = client.post("/api/v1/accounting/invoices", headers=auth_headers, json={"customer_id": "cust-1", "items": [{"description": "Widget", "quantity": 2, "unit_price": 50.0}]})
        assert r.status_code == 201 and r.json()["total"] == 100.0 and r.json()["status"] == "draft"

    def test_create_invoice_empty_items(self, client, auth_headers):
        assert client.post("/api/v1/accounting/invoices", headers=auth_headers, json={"customer_id": "cust-1", "items": []}).status_code == 422

    def test_post_invoice(self, client, auth_headers):
        iid = client.post("/api/v1/accounting/invoices", headers=auth_headers, json={"customer_id": "cust-1", "items": [{"description": "Widget", "quantity": 1, "unit_price": 100.0}]}).json()["id"]
        r = client.post(f"/api/v1/accounting/invoices/{iid}/post", headers=auth_headers)
        assert r.status_code == 200 and r.json()["status"] == "posted"

    def test_create_journal_entry(self, client, auth_headers):
        accts = client.get("/api/v1/accounting/accounts", headers=auth_headers).json()
        ar = next(a for a in accts if a["name"] == "Accounts Receivable")
        rev = next(a for a in accts if a["name"] == "Revenue")
        r = client.post("/api/v1/accounting/journal-entries", headers=auth_headers, json={"description": "Test entry", "lines": [{"account_id": ar["id"], "debit": 100.0, "credit": 0.0}, {"account_id": rev["id"], "debit": 0.0, "credit": 100.0}]})
        assert r.status_code == 201 and len(r.json()["lines"]) == 2

    def test_create_journal_entry_unbalanced(self, client, auth_headers):
        accts = client.get("/api/v1/accounting/accounts", headers=auth_headers).json()
        ar = next(a for a in accts if a["name"] == "Accounts Receivable")
        rev = next(a for a in accts if a["name"] == "Revenue")
        r = client.post("/api/v1/accounting/journal-entries", headers=auth_headers, json={"description": "Bad entry", "lines": [{"account_id": ar["id"], "debit": 100.0, "credit": 0.0}, {"account_id": rev["id"], "debit": 0.0, "credit": 50.0}]})
        assert r.status_code == 400

    def test_trial_balance(self, client, auth_headers):
        r = client.get("/api/v1/accounting/trial-balance", headers=auth_headers)
        assert r.status_code == 200 and "trial_balance" in r.json() and "is_balanced" in r.json()


class TestAnalytics:
    def test_track_metric(self, client, auth_headers):
        r = client.post("/api/v1/analytics/metrics", headers=auth_headers, json={"name": "revenue", "value": 1000.0, "unit": "USD"})
        assert r.status_code == 201 and r.json()["name"] == "revenue"

    def test_list_metrics(self, client, auth_headers):
        client.post("/api/v1/analytics/metrics", headers=auth_headers, json={"name": "test_metric", "value": 42.0, "unit": "count"})
        r = client.get("/api/v1/analytics/metrics", headers=auth_headers)
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_get_metric_history(self, client, auth_headers):
        client.post("/api/v1/analytics/metrics", headers=auth_headers, json={"name": "history_test", "value": 1.0, "unit": "count"})
        client.post("/api/v1/analytics/metrics", headers=auth_headers, json={"name": "history_test", "value": 2.0, "unit": "count"})
        r = client.get("/api/v1/analytics/metrics/history_test", headers=auth_headers)
        assert r.status_code == 200 and len(r.json()) == 2

    def test_get_metric_not_found(self, client, auth_headers):
        assert client.get("/api/v1/analytics/metrics/nonexistent", headers=auth_headers).status_code == 404

    def test_create_dashboard(self, client, auth_headers):
        r = client.post("/api/v1/analytics/dashboards", headers=auth_headers, json={"name": "Test Dashboard"})
        assert r.status_code == 201 and r.json()["name"] == "Test Dashboard"

    def test_get_dashboard_not_found(self, client, auth_headers):
        assert client.get("/api/v1/analytics/dashboards/nonexistent", headers=auth_headers).status_code == 404

    def test_add_metric_to_dashboard(self, client, auth_headers):
        client.post("/api/v1/analytics/dashboards", headers=auth_headers, json={"name": "Test Dashboard"})
        r = client.post("/api/v1/analytics/dashboards/Test Dashboard/metrics", headers=auth_headers, json={"name": "dash_metric", "value": 42.0, "unit": "count"})
        assert r.status_code == 200 and r.json()["total_metrics"] == 1


class TestWorkflows:
    def test_create_workflow(self, client, auth_headers):
        r = client.post("/api/v1/workflows", headers=auth_headers, json={"name": "Test Workflow", "steps": [{"name": "step1", "action": "test.action"}]})
        assert r.status_code == 201 and r.json()["name"] == "Test Workflow"

    def test_list_workflows(self, client, auth_headers):
        r = client.get("/api/v1/workflows", headers=auth_headers)
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_get_workflow_not_found(self, client, auth_headers):
        assert client.get("/api/v1/workflows/nonexistent", headers=auth_headers).status_code == 404

    def test_execute_workflow(self, client, auth_headers):
        client.post("/api/v1/workflows", headers=auth_headers, json={"name": "ExecWorkflow", "steps": [{"name": "step1", "action": "test.action"}]})
        r = client.post("/api/v1/workflows/ExecWorkflow/execute", headers=auth_headers)
        assert r.status_code == 200 and r.json()["status"] == "completed"

    def test_execute_workflow_not_found(self, client, auth_headers):
        assert client.post("/api/v1/workflows/nonexistent/execute", headers=auth_headers).status_code == 404

    def test_delete_workflow(self, client, auth_headers):
        client.post("/api/v1/workflows", headers=auth_headers, json={"name": "DeleteWorkflow", "steps": []})
        assert client.delete("/api/v1/workflows/DeleteWorkflow", headers=auth_headers).status_code == 204


class TestValidation:
    def test_contact_name_too_long(self, client, auth_headers):
        assert client.post("/api/v1/crm/contacts", headers=auth_headers, json={"name": "x" * 300, "email": "test@example.com"}).status_code == 422

    def test_deal_title_too_long(self, client, auth_headers):
        assert client.post("/api/v1/crm/deals", headers=auth_headers, json={"title": "x" * 600, "value": 100.0}).status_code == 422

    def test_invoice_negative_quantity(self, client, auth_headers):
        r = client.post("/api/v1/accounting/invoices", headers=auth_headers, json={"customer_id": "cust-1", "items": [{"description": "Widget", "quantity": -1, "unit_price": 10.0}]})
        assert r.status_code == 422

    def test_journal_entry_single_line(self, client, auth_headers):
        r = client.post("/api/v1/accounting/journal-entries", headers=auth_headers, json={"description": "Bad entry", "lines": [{"account_id": "acc-1", "debit": 100.0, "credit": 0.0}]})
        assert r.status_code == 422

    def test_register_short_password(self, client):
        assert client.post("/api/v1/auth/register", json={"username": "test", "email": "test@example.com", "password": "short"}).status_code == 422

    def test_register_invalid_email(self, client):
        assert client.post("/api/v1/auth/register", json={"username": "test", "email": "not-an-email", "password": "password123"}).status_code == 422


class TestErrorHandling:
    def test_404_for_nonexistent_resource(self, client, auth_headers):
        r = client.get("/api/v1/crm/contacts/nonexistent", headers=auth_headers)
        assert r.status_code == 404 and "detail" in r.json()

    def test_401_for_unauthenticated(self, client):
        assert client.get("/api/v1/crm/contacts").status_code == 401

    def test_422_for_invalid_json(self, client, auth_headers):
        assert client.post("/api/v1/crm/contacts", headers=auth_headers, json={"invalid": "data"}).status_code == 422

    def test_400_for_unbalanced_journal(self, client, auth_headers):
        accts = client.get("/api/v1/accounting/accounts", headers=auth_headers).json()
        ar = next(a for a in accts if a["name"] == "Accounts Receivable")
        rev = next(a for a in accts if a["name"] == "Revenue")
        r = client.post("/api/v1/accounting/journal-entries", headers=auth_headers, json={"description": "Bad entry", "lines": [{"account_id": ar["id"], "debit": 100.0, "credit": 0.0}, {"account_id": rev["id"], "debit": 0.0, "credit": 50.0}]})
        assert r.status_code == 400

    def test_409_for_duplicate_registration(self, client):
        assert client.post("/api/v1/auth/register", json={"username": "admin", "email": "other@example.com", "password": "password123"}).status_code == 409


class TestRateLimiting:
    def test_rate_limit_headers_present(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200 and "X-RateLimit-Limit" in r.headers and "X-RateLimit-Remaining" in r.headers

    def test_rate_limit_exceeded(self):
        config = Config()
        config.set("api.rate_limit.max_requests", 2)
        config.set("api.rate_limit.window_seconds", 60)
        tc = TestClient(create_api_app(config))
        assert tc.get("/api/v1/health").status_code == 200
        assert tc.get("/api/v1/health").status_code == 200
        assert tc.get("/api/v1/health").status_code == 429
