"""Permission CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/permissions", tags=["permissions"])

_permissions_db = {
    1: {"id": 1, "name": "read:users", "description": "View users",
        "resource": "users", "action": "read", "is_active": True,
        "created_at": "2024-01-15T10:30:00"},
    2: {"id": 2, "name": "write:users", "description": "Create and edit users",
        "resource": "users", "action": "write", "is_active": True,
        "created_at": "2024-02-20T14:00:00"},
    3: {"id": 3, "name": "delete:users", "description": "Delete users",
        "resource": "users", "action": "delete", "is_active": True,
        "created_at": "2024-03-10T09:15:00"},
    4: {"id": 4, "name": "read:reports", "description": "View reports",
        "resource": "reports", "action": "read", "is_active": True,
        "created_at": "2024-04-05T16:45:00"},
    5: {"id": 5, "name": "admin:all", "description": "Full admin access",
        "resource": "*", "action": "*", "is_active": False,
        "created_at": "2024-05-12T11:20:00"},
}
_next_id = 6


class PermissionCreate(BaseModel):
    name: str
    description: str = ""
    resource: str
    action: str
    is_active: bool = True


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionResponse(BaseModel):
    id: int
    name: str
    description: str
    resource: str
    action: str
    is_active: bool
    created_at: str


@router.get("/", response_model=list[PermissionResponse])
async def list_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    resource: Optional[str] = None,
    action: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """List all permissions with pagination and optional filters."""
    perms = list(_permissions_db.values())
    if resource:
        perms = [p for p in perms if p["resource"] == resource]
    if action:
        perms = [p for p in perms if p["action"] == action]
    if is_active is not None:
        perms = [p for p in perms if p["is_active"] == is_active]
    return perms[skip : skip + limit]


@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(permission_id: int):
    """Get a single permission by ID."""
    perm = _permissions_db.get(permission_id)
    if not perm:
        raise HTTPException(status_code=404, detail=f"Permission {permission_id} not found")
    return perm


@router.post("/", response_model=PermissionResponse, status_code=201)
async def create_permission(permission: PermissionCreate):
    """Create a new permission."""
    global _next_id
    if any(p["name"] == permission.name for p in _permissions_db.values()):
        raise HTTPException(status_code=409, detail="Permission name already exists")
    new_perm = {
        "id": _next_id,
        "name": permission.name,
        "description": permission.description,
        "resource": permission.resource,
        "action": permission.action,
        "is_active": permission.is_active,
        "created_at": datetime.utcnow().isoformat(),
    }
    _permissions_db[_next_id] = new_perm
    _next_id += 1
    return new_perm


@router.put("/{permission_id}", response_model=PermissionResponse)
async def update_permission(permission_id: int, permission: PermissionUpdate):
    """Update an existing permission."""
    existing = _permissions_db.get(permission_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Permission {permission_id} not found")
    if permission.name and permission.name != existing["name"]:
        if any(p["name"] == permission.name for p in _permissions_db.values()):
            raise HTTPException(status_code=409, detail="Permission name already exists")
    for field, value in permission.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/{permission_id}", status_code=204)
async def delete_permission(permission_id: int):
    """Delete a permission by ID."""
    if permission_id not in _permissions_db:
        raise HTTPException(status_code=404, detail=f"Permission {permission_id} not found")
    del _permissions_db[permission_id]
