"""Role CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/roles", tags=["roles"])

_roles_db = {
    1: {"id": 1, "name": "admin", "description": "Full system access",
        "is_active": True, "created_at": "2024-01-15T10:30:00"},
    2: {"id": 2, "name": "manager", "description": "Team management access",
        "is_active": True, "created_at": "2024-02-20T14:00:00"},
    3: {"id": 3, "name": "user", "description": "Standard user access",
        "is_active": True, "created_at": "2024-03-10T09:15:00"},
    4: {"id": 4, "name": "viewer", "description": "Read-only access",
        "is_active": False, "created_at": "2024-04-05T16:45:00"},
}
_next_id = 5


class RoleCreate(BaseModel):
    name: str
    description: str = ""
    is_active: bool = True


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    created_at: str


@router.get("/", response_model=list[RoleResponse])
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = None,
):
    """List all roles with pagination and optional filters."""
    roles = list(_roles_db.values())
    if is_active is not None:
        roles = [r for r in roles if r["is_active"] == is_active]
    return roles[skip : skip + limit]


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(role_id: int):
    """Get a single role by ID."""
    role = _roles_db.get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found")
    return role


@router.post("/", response_model=RoleResponse, status_code=201)
async def create_role(role: RoleCreate):
    """Create a new role."""
    global _next_id
    if any(r["name"] == role.name for r in _roles_db.values()):
        raise HTTPException(status_code=409, detail="Role name already exists")
    new_role = {
        "id": _next_id,
        "name": role.name,
        "description": role.description,
        "is_active": role.is_active,
        "created_at": datetime.utcnow().isoformat(),
    }
    _roles_db[_next_id] = new_role
    _next_id += 1
    return new_role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(role_id: int, role: RoleUpdate):
    """Update an existing role."""
    existing = _roles_db.get(role_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found")
    if role.name and role.name != existing["name"]:
        if any(r["name"] == role.name for r in _roles_db.values()):
            raise HTTPException(status_code=409, detail="Role name already exists")
    for field, value in role.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/{role_id}", status_code=204)
async def delete_role(role_id: int):
    """Delete a role by ID."""
    if role_id not in _roles_db:
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found")
    del _roles_db[role_id]
