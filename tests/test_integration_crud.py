"""Comprehensive integration tests for all CRUD operations."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from typing import Any, Dict


@pytest_asyncio.fixture
async def client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_user(client):
    r = await client.post("/api/v1/users/", json={"name": "Test User", "email": "test@example.com", "role": "member"})
    assert r.status_code == 201
    return r.json()


@pytest_asyncio.fixture
async def sample_project(client):
    r = await client.post("/api/v1/projects/", json={"name": "Test Project", "description": "A test project", "status": "active", "priority": "medium"})
    assert r.status_code == 201
    return r.json()


@pytest_asyncio.fixture
async def sample_task(client, sample_project):
    r = await client.post("/api/v1/tasks/", json={"title": "Test Task", "description": "A test task", "project_id": sample_project["id"], "status": "todo", "priority": "high"})
    assert r.status_code == 201
    return r.json()


class TestUserCRUD:
    @pytest.mark.asyncio
    async def test_create_user(self, client):
        r = await client.post("/api/v1/users/", json={"name": "John", "email": "john@example.com", "role": "admin"})
        assert r.status_code == 201
        d = r.json()
        assert d["name"] == "John" and d["email"] == "john@example.com" and "id" in d

    @pytest.mark.asyncio
    async def test_get_user(self, client, sample_user):
        r = await client.get(f"/api/v1/users/{sample_user['id']}")
        assert r.status_code == 200 and r.json()["id"] == sample_user["id"]

    @pytest.mark.asyncio
    async def test_list_users(self, client):
        r = await client.get("/api/v1/users/")
        assert r.status_code == 200 and isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_update_user(self, client, sample_user):
        r = await client.put(f"/api/v1/users/{sample_user['id']}", json={"name": "Updated", "email": "updated@example.com", "role": "admin"})
        assert r.status_code == 200 and r.json()["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_user(self, client, sample_user):
        r = await client.delete(f"/api/v1/users/{sample_user['id']}")
        assert r.status_code == 204
        assert (await client.get(f"/api/v1/users/{sample_user['id']}")).status_code == 404


class TestProjectCRUD:
    @pytest.mark.asyncio
    async def test_create_project(self, client):
        r = await client.post("/api/v1/projects/", json={"name": "New Project", "description": "Desc", "status": "active", "priority": "high"})
        assert r.status_code == 201 and r.json()["name"] == "New Project" and "id" in r.json()

    @pytest.mark.asyncio
    async def test_get_project(self, client, sample_project):
        r = await client.get(f"/api/v1/projects/{sample_project['id']}")
        assert r.status_code == 200 and r.json()["id"] == sample_project["id"]

    @pytest.mark.asyncio
    async def test_list_projects(self, client):
        r = await client.get("/api/v1/projects/")
        assert r.status_code == 200 and isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_update_project(self, client, sample_project):
        r = await client.put(f"/api/v1/projects/{sample_project['id']}", json={"name": "Updated", "description": "Updated", "status": "completed", "priority": "low"})
        assert r.status_code == 200 and r.json()["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_project(self, client, sample_project):
        r = await client.delete(f"/api/v1/projects/{sample_project['id']}")
        assert r.status_code == 204
        assert (await client.get(f"/api/v1/projects/{sample_project['id']}")).status_code == 404


class TestTaskCRUD:
    @pytest.mark.asyncio
    async def test_create_task(self, client, sample_project):
        r = await client.post("/api/v1/tasks/", json={"title": "New Task", "description": "Desc", "project_id": sample_project["id"], "status": "todo", "priority": "medium"})
        assert r.status_code == 201 and r.json()["title"] == "New Task" and "id" in r.json()

    @pytest.mark.asyncio
    async def test_get_task(self, client, sample_task):
        r = await client.get(f"/api/v1/tasks/{sample_task['id']}")
        assert r.status_code == 200 and r.json()["id"] == sample_task["id"]

    @pytest.mark.asyncio
    async def test_list_tasks(self, client):
        r = await client.get("/api/v1/tasks/")
        assert r.status_code == 200 and isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_update_task(self, client, sample_task):
        r = await client.put(f"/api/v1/tasks/{sample_task['id']}", json={"title": "Updated", "description": "Updated", "status": "done", "priority": "low"})
        assert r.status_code == 200 and r.json()["title"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_task(self, client, sample_task):
        r = await client.delete(f"/api/v1/tasks/{sample_task['id']}")
        assert r.status_code == 204
        assert (await client.get(f"/api/v1/tasks/{sample_task['id']}")).status_code == 404


class TestDataValidation:
    @pytest.mark.asyncio
    async def test_user_missing_fields(self, client):
        assert (await client.post("/api/v1/users/", json={"name": "Only Name"})).status_code == 422

    @pytest.mark.asyncio
    async def test_user_invalid_email(self, client):
        r = await client.post("/api/v1/users/", json={"name": "Test", "email": "bad", "role": "member"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_project_missing_name(self, client):
        r = await client.post("/api/v1/projects/", json={"description": "No name", "status": "active", "priority": "low"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_task_invalid_project(self, client):
        r = await client.post("/api/v1/tasks/", json={"title": "Orphan", "description": "No project", "project_id": "non-existent", "status": "todo", "priority": "low"})
        assert r.status_code in (404, 422)

    @pytest.mark.asyncio
    async def test_user_invalid_role(self, client):
        r = await client.post("/api/v1/users/", json={"name": "Test", "email": "t@e.com", "role": "superuser"})
        assert r.status_code == 422


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, client):
        assert (await client.get("/api/v1/users/non-existent-id")).status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, client):
        assert (await client.get("/api/v1/projects/non-existent-id")).status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, client):
        assert (await client.get("/api/v1/tasks/non-existent-id")).status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_user(self, client):
        r = await client.put("/api/v1/users/non-existent-id", json={"name": "Ghost", "email": "g@e.com", "role": "member"})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, client):
        assert (await client.delete("/api/v1/users/non-existent-id")).status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client):
        assert (await client.patch("/api/v1/users/")).status_code == 405


class TestPagination:
    @pytest.mark.asyncio
    async def test_users_pagination(self, client):
        for i in range(5):
            await client.post("/api/v1/users/", json={"name": f"U{i}", "email": f"u{i}@e.com", "role": "member"})
        r = await client.get("/api/v1/users/?limit=2&offset=0")
        assert r.status_code == 200 and len(r.json()) <= 2

    @pytest.mark.asyncio
    async def test_projects_pagination(self, client):
        for i in range(5):
            await client.post("/api/v1/projects/", json={"name": f"P{i}", "description": "D", "status": "active", "priority": "low"})
        r = await client.get("/api/v1/projects/?limit=3&offset=0")
        assert r.status_code == 200 and len(r.json()) <= 3

    @pytest.mark.asyncio
    async def test_tasks_pagination(self, client, sample_project):
        for i in range(5):
            await client.post("/api/v1/tasks/", json={"title": f"T{i}", "description": "D", "project_id": sample_project["id"], "status": "todo", "priority": "low"})
        r = await client.get("/api/v1/tasks/?limit=2&offset=0")
        assert r.status_code == 200 and len(r.json()) <= 2

    @pytest.mark.asyncio
    async def test_pagination_offset(self, client):
        for i in range(5):
            await client.post("/api/v1/users/", json={"name": f"PU{i}", "email": f"pu{i}@e.com", "role": "member"})
        r1 = await client.get("/api/v1/users/?limit=2&offset=0")
        r2 = await client.get("/api/v1/users/?limit=2&offset=2")
        assert r1.status_code == 200 and r2.status_code == 200
        d1, d2 = r1.json(), r2.json()
        if d1 and d2:
            assert d1[0]["id"] != d2[0]["id"]


class TestCrossModuleIntegration:
    @pytest.mark.asyncio
    async def test_project_with_tasks(self, client):
        p = (await client.post("/api/v1/projects/", json={"name": "IntProj", "description": "D", "status": "active", "priority": "high"})).json()
        for i in range(3):
            await client.post("/api/v1/tasks/", json={"title": f"T{i}", "description": "D", "project_id": p["id"], "status": "todo", "priority": "medium"})
        r = await client.get(f"/api/v1/tasks/?project_id={p['id']}")
        assert r.status_code == 200 and len(r.json()) == 3

    @pytest.mark.asyncio
    async def test_cascade_delete(self, client):
        p = (await client.post("/api/v1/projects/", json={"name": "Cascade", "description": "D", "status": "active", "priority": "low"})).json()
        await client.post("/api/v1/tasks/", json={"title": "CT", "description": "D", "project_id": p["id"], "status": "todo", "priority": "low"})
        assert (await client.delete(f"/api/v1/projects/{p['id']}")).status_code == 204
        r = await client.get(f"/api/v1/tasks/?project_id={p['id']}")
        assert r.status_code == 200 and len(r.json()) == 0
