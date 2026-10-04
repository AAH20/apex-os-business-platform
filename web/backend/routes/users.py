"""User CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/users", tags=["users"])

# Synthetic in-memory data store
_users_db = {
    1: {"id": 1, "name": "Alice Johnson", "email": "alice@example.com",
        "role": "admin", "is_active": True, "created_at": "2024-01-15T10:30:00"},
    2: {"id": 2, "name": "Bob Smith", "email": "bob@example.com",
        "role": "user", "is_active": True, "created_at": "2024-02-20T14:00:00"},
    3: {"id": 3, "name": "Carol White", "email": "carol@example.com",
        "role": "user", "is_active": False, "created_at": "2024-03-10T09:15:00"},
    4: {"id": 4, "name": "David Brown", "email": "david@example.com",
        "role": "manager", "is_active": True, "created_at": "2024-04-05T16:45:00"},
    5: {"id": 5, "name": "Eve Davis", "email": "eve@example.com",
        "role": "user", "is_active": True, "created_at": "2024-05-12T11:20:00"},
}
_next_id = 6


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: str = "user"
    is_active: bool = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: str


@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
 -> list[UserResponse]:
    """List all users with pagination and optional filters."""
    try:
        users = list(_users_db.values())
        if role:
            users = [u for u in users if u["role"] == role]
        if is_active is not None:
            users = [u for u in users if u["is_active"] == is_active]
        return users[skip : skip + limit]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    """Get a single user by ID."""
    try:
        user = _users_db.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate) -> UserResponse:
    """Create a new user."""
    try:
        global _next_id
        if any(u["email"] == user.email for u in _users_db.values()):
            raise HTTPException(status_code=409, detail="Email already registered")
        new_user = {
            "id": _next_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": datetime.utcnow().isoformat(),
        }
        _users_db[_next_id] = new_user
        _next_id += 1
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user: UserUpdate) -> UserResponse:
    """Update an existing user."""
    try:
        existing = _users_db.get(user_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        if user.email and user.email != existing["email"]:
            if any(u["email"] == user.email for u in _users_db.values()):
                raise HTTPException(status_code=409, detail="Email already registered")
        for field, value in user.model_dump(exclude_unset=True).items():
            existing[field] = value
        return existing
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int) -> None:
    """Delete a user by ID."""
    try:
        if user_id not in _users_db:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        del _users_db[user_id]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
