"""
CRUD endpoint tests for APEX-OS Business Platform.
Tests roles, permissions, opportunities, campaigns, and alerts endpoints.
"""
import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web", "backend"))

from main import app, API_KEY


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def api_key_headers():
    return {"X-API-Key": API_KEY}


# ===========================================================================
# ROLES CRUD
# ===========================================================================

class TestRolesCRUD:
    """Test /api/roles endpoints."""

    def test_list_roles(self, client, api_key_headers):
        response = client.get("/api/roles/", headers=api_key_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_roles_pagination(self, client, api_key_headers):
        response = client.get("/api/roles/?skip=0&limit=2", headers=api_key_headers)
        assert response.status_code == 200
        assert len(response.json()) <= 2

    def test_list_roles_filter_active(self, client, api_key_headers):
        response = client.get("/api/roles/?is_active=true", headers=api_key_headers)
        assert response.status_code == 200
        for role in response.json():
            assert role["is_active"] is True

    def test_get_role_by_id(self, client, api_key_headers):
        response = client.get("/api/roles/1", headers=api_key_headers)
        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert "name" in response.json()

    def test_get_role_not_found(self, client, api_key_headers):
        response = client.get("/api/roles/9999", headers=api_key_headers)
        assert response.status_code == 404

    def test_create_role(self, client, api_key_headers):
        response = client.post(
            "/api/roles/",
            json={"name": "test_role", "description": "Test role"},
            headers=api_key_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_role"
        assert "id" in data

    def test_create_role_duplicate_name(self, client, api_key_headers):
        # First create
        client.post(
            "/api/roles/",
            json={"name": "dup_role", "description": "First"},
            headers=api_key_headers,
        )
        # Try duplicate
        response = client.post(
            "/api/roles/",
            json={"name": "dup_role", "description": "Second"},
            headers=api_key_headers,
        )
        assert response.status_code == 409

    def test_update_role(self, client, api_key_headers):
        # Create first
        create_resp = client.post(
            "/api/roles/",
            json={"name": "update_role", "description": "Original"},
            headers=api_key_headers,
        )
        role_id = create_resp.json()["id"]
        # Update
        response = client.put(
            f"/api/roles/{role_id}",
            json={"description": "Updated description"},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"

    def test_update_role_not_found(self, client, api_key_headers):
        response = client.put(
            "/api/roles/9999",
            json={"description": "test"},
            headers=api_key_headers,
        )
        assert response.status_code == 404

    def test_delete_role(self, client, api_key_headers):
        # Create first
        create_resp = client.post(
            "/api/roles/",
            json={"name": "delete_role", "description": "To delete"},
            headers=api_key_headers,
        )
        role_id = create_resp.json()["id"]
        # Delete
        response = client.delete(f"/api/roles/{role_id}", headers=api_key_headers)
        assert response.status_code == 204
        # Verify gone
        get_resp = client.get(f"/api/roles/{role_id}", headers=api_key_headers)
        assert get_resp.status_code == 404

    def test_delete_role_not_found(self, client, api_key_headers):
        response = client.delete("/api/roles/9999", headers=api_key_headers)
        assert response.status_code == 404

    def test_roles_require_api_key(self, client):
        response = client.get("/api/roles/")
        assert response.status_code == 401


# ===========================================================================
# PERMISSIONS CRUD
# ===========================================================================

class TestPermissionsCRUD:
    """Test /api/permissions endpoints."""

    def test_list_permissions(self, client, api_key_headers):
        response = client.get("/api/permissions/", headers=api_key_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_permissions_filter_by_resource(self, client, api_key_headers):
        response = client.get("/api/permissions/?resource=users", headers=api_key_headers)
        assert response.status_code == 200
        for perm in response.json():
            assert perm["resource"] == "users"

    def test_list_permissions_filter_by_action(self, client, api_key_headers):
        response = client.get("/api/permissions/?action=read", headers=api_key_headers)
        assert response.status_code == 200
        for perm in response.json():
            assert perm["action"] == "read"

    def test_get_permission_by_id(self, client, api_key_headers):
        response = client.get("/api/permissions/1", headers=api_key_headers)
        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_get_permission_not_found(self, client, api_key_headers):
        response = client.get("/api/permissions/9999", headers=api_key_headers)
        assert response.status_code == 404

    def test_create_permission(self, client, api_key_headers):
        response = client.post(
            "/api/permissions/",
            json={
                "name": "test:permission",
                "description": "Test permission",
                "resource": "test_resource",
                "action": "read",
            },
            headers=api_key_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test:permission"
        assert data["resource"] == "test_resource"

    def test_create_permission_duplicate_name(self, client, api_key_headers):
        client.post(
            "/api/permissions/",
            json={
                "name": "dup_perm",
                "description": "First",
                "resource": "r1",
                "action": "read",
            },
            headers=api_key_headers,
        )
        response = client.post(
            "/api/permissions/",
            json={
                "name": "dup_perm",
                "description": "Second",
                "resource": "r2",
                "action": "write",
            },
            headers=api_key_headers,
        )
        assert response.status_code == 409

    def test_update_permission(self, client, api_key_headers):
        create_resp = client.post(
            "/api/permissions/",
            json={
                "name": "update_perm",
                "description": "Original",
                "resource": "res",
                "action": "read",
            },
            headers=api_key_headers,
        )
        perm_id = create_resp.json()["id"]
        response = client.put(
            f"/api/permissions/{perm_id}",
            json={"action": "write"},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["action"] == "write"

    def test_delete_permission(self, client, api_key_headers):
        create_resp = client.post(
            "/api/permissions/",
            json={
                "name": "delete_perm",
                "description": "To delete",
                "resource": "res",
                "action": "read",
            },
            headers=api_key_headers,
        )
        perm_id = create_resp.json()["id"]
        response = client.delete(f"/api/permissions/{perm_id}", headers=api_key_headers)
        assert response.status_code == 204

    def test_permissions_require_api_key(self, client):
        response = client.get("/api/permissions/")
        assert response.status_code == 401


# ===========================================================================
# OPPORTUNITIES CRUD
# ===========================================================================

class TestOpportunitiesCRUD:
    """Test /api/opportunities endpoints."""

    def test_list_opportunities(self, client, api_key_headers):
        response = client.get("/api/opportunities/", headers=api_key_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_opportunities_filter_by_stage(self, client, api_key_headers):
        response = client.get("/api/opportunities/?stage=qualification", headers=api_key_headers)
        assert response.status_code == 200
        for opp in response.json():
            assert opp["stage"] == "qualification"

    def test_get_opportunity_by_id(self, client, api_key_headers):
        response = client.get("/api/opportunities/1", headers=api_key_headers)
        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_get_opportunity_not_found(self, client, api_key_headers):
        response = client.get("/api/opportunities/9999", headers=api_key_headers)
        assert response.status_code == 404

    def test_create_opportunity(self, client, api_key_headers):
        response = client.post(
            "/api/opportunities/",
            json={
                "title": "Test Opportunity",
                "value": 50000.0,
                "stage": "qualification",
                "probability": 0.5,
                "contact_email": "test@example.com",
            },
            headers=api_key_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Opportunity"
        assert data["value"] == 50000.0

    def test_update_opportunity(self, client, api_key_headers):
        create_resp = client.post(
            "/api/opportunities/",
            json={
                "title": "Update Opp",
                "value": 10000.0,
                "stage": "qualification",
                "probability": 0.3,
                "contact_email": "u@example.com",
            },
            headers=api_key_headers,
        )
        opp_id = create_resp.json()["id"]
        response = client.put(
            f"/api/opportunities/{opp_id}",
            json={"stage": "negotiation", "probability": 0.8},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["stage"] == "negotiation"
        assert response.json()["probability"] == 0.8

    def test_delete_opportunity(self, client, api_key_headers):
        create_resp = client.post(
            "/api/opportunities/",
            json={
                "title": "Delete Opp",
                "value": 5000.0,
                "stage": "qualification",
                "probability": 0.1,
                "contact_email": "d@example.com",
            },
            headers=api_key_headers,
        )
        opp_id = create_resp.json()["id"]
        response = client.delete(f"/api/opportunities/{opp_id}", headers=api_key_headers)
        assert response.status_code == 204

    def test_opportunities_require_api_key(self, client):
        response = client.get("/api/opportunities/")
        assert response.status_code == 401


# ===========================================================================
# CAMPAIGNS CRUD
# ===========================================================================

class TestCampaignsCRUD:
    """Test /api/campaigns endpoints."""

    def test_list_campaigns(self, client, api_key_headers):
        response = client.get("/api/campaigns/", headers=api_key_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_campaigns_filter_by_status(self, client, api_key_headers):
        response = client.get("/api/campaigns/?status=active", headers=api_key_headers)
        assert response.status_code == 200
        for c in response.json():
            assert c["status"] == "active"

    def test_list_campaigns_filter_by_channel(self, client, api_key_headers):
        response = client.get("/api/campaigns/?channel=email", headers=api_key_headers)
        assert response.status_code == 200
        for c in response.json():
            assert c["channel"] == "email"

    def test_get_campaign_by_id(self, client, api_key_headers):
        response = client.get("/api/campaigns/1", headers=api_key_headers)
        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_get_campaign_not_found(self, client, api_key_headers):
        response = client.get("/api/campaigns/9999", headers=api_key_headers)
        assert response.status_code == 404

    def test_create_campaign(self, client, api_key_headers):
        response = client.post(
            "/api/campaigns/",
            json={
                "name": "Test Campaign",
                "channel": "email",
                "status": "draft",
                "budget": 5000.0,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
            headers=api_key_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Campaign"
        assert data["budget"] == 5000.0

    def test_update_campaign(self, client, api_key_headers):
        create_resp = client.post(
            "/api/campaigns/",
            json={
                "name": "Update Campaign",
                "channel": "social",
                "status": "draft",
                "budget": 1000.0,
                "start_date": "2024-01-01",
                "end_date": "2024-06-30",
            },
            headers=api_key_headers,
        )
        camp_id = create_resp.json()["id"]
        response = client.put(
            f"/api/campaigns/{camp_id}",
            json={"status": "active", "budget": 2000.0},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"
        assert response.json()["budget"] == 2000.0

    def test_delete_campaign(self, client, api_key_headers):
        create_resp = client.post(
            "/api/campaigns/",
            json={
                "name": "Delete Campaign",
                "channel": "email",
                "status": "draft",
                "budget": 100.0,
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
            },
            headers=api_key_headers,
        )
        camp_id = create_resp.json()["id"]
        response = client.delete(f"/api/campaigns/{camp_id}", headers=api_key_headers)
        assert response.status_code == 204

    def test_campaigns_require_api_key(self, client):
        response = client.get("/api/campaigns/")
        assert response.status_code == 401


# ===========================================================================
# ALERTS CRUD
# ===========================================================================

class TestAlertsCRUD:
    """Test /api/alerts endpoints."""

    def test_list_alerts(self, client, api_key_headers):
        response = client.get("/api/alerts/", headers=api_key_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_alerts_filter_by_severity(self, client, api_key_headers):
        response = client.get("/api/alerts/?severity=critical", headers=api_key_headers)
        assert response.status_code == 200
        for a in response.json():
            assert a["severity"] == "critical"

    def test_list_alerts_filter_by_source(self, client, api_key_headers):
        response = client.get("/api/alerts/?source=monitoring", headers=api_key_headers)
        assert response.status_code == 200
        for a in response.json():
            assert a["source"] == "monitoring"

    def test_list_alerts_filter_unread(self, client, api_key_headers):
        response = client.get("/api/alerts/?is_read=false", headers=api_key_headers)
        assert response.status_code == 200
        for a in response.json():
            assert a["is_read"] is False

    def test_get_alert_by_id(self, client, api_key_headers):
        response = client.get("/api/alerts/1", headers=api_key_headers)
        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_get_alert_not_found(self, client, api_key_headers):
        response = client.get("/api/alerts/9999", headers=api_key_headers)
        assert response.status_code == 404

    def test_create_alert(self, client, api_key_headers):
        response = client.post(
            "/api/alerts/",
            json={
                "title": "Test Alert",
                "message": "This is a test alert",
                "severity": "warning",
                "source": "test",
            },
            headers=api_key_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Alert"
        assert data["severity"] == "warning"

    def test_update_alert(self, client, api_key_headers):
        create_resp = client.post(
            "/api/alerts/",
            json={
                "title": "Update Alert",
                "message": "Original message",
                "severity": "info",
                "source": "test",
            },
            headers=api_key_headers,
        )
        alert_id = create_resp.json()["id"]
        response = client.put(
            f"/api/alerts/{alert_id}",
            json={"is_read": True, "severity": "critical"},
            headers=api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_read"] is True
        assert response.json()["severity"] == "critical"

    def test_delete_alert(self, client, api_key_headers):
        create_resp = client.post(
            "/api/alerts/",
            json={
                "title": "Delete Alert",
                "message": "To be deleted",
                "severity": "info",
                "source": "test",
            },
            headers=api_key_headers,
        )
        alert_id = create_resp.json()["id"]
        response = client.delete(f"/api/alerts/{alert_id}", headers=api_key_headers)
        assert response.status_code == 204

    def test_alerts_require_api_key(self, client):
        response = client.get("/api/alerts/")
        assert response.status_code == 401
