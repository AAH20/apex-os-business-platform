"""Authentication and authorization for APEX-OS Business Platform."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Permission:
    """Permission data structure."""
    resource: str
    action: str


@dataclass
class Role:
    """Role data structure."""
    name: str
    permissions: List[Permission] = field(default_factory=list)


@dataclass
class User:
    """User data structure."""
    id: str
    username: str
    email: str
    password_hash: str = ""
    salt: str = ""
    roles: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class Authenticator:
    """Authentication and authorization engine."""

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._roles: Dict[str, Role] = {}
        self._init_default_roles()

    def _init_default_roles(self) -> None:
        """Initialize default roles."""
        self._roles["admin"] = Role(
            name="admin",
            permissions=[Permission(resource="*", action="*")],
        )
        self._roles["user"] = Role(
            name="user",
            permissions=[
                Permission(resource="invoice", action="read"),
                Permission(resource="contact", action="read"),
                Permission(resource="contact", action="write"),
            ],
        )

    def register(self, username: str, email: str, password: str) -> User:
        """Register a new user."""
        user_id = str(uuid.uuid4())
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
        )
        self._users[user_id] = user
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        for user in self._users.values():
            if user.username == username:
                password_hash = self._hash_password(password, user.salt)
                if password_hash == user.password_hash:
                    return user
        return None

    def assign_role(self, user_id: str, role_name: str) -> None:
        """Assign role to user."""
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        if role_name not in user.roles:
            user.roles.append(role_name)

    def authorize(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user is authorized for resource and action."""
        user = self._users.get(user_id)
        if not user:
            return False

        for role_name in user.roles:
            role = self._roles.get(role_name)
            if not role:
                continue
            for perm in role.permissions:
                if perm.resource == "*" and perm.action == "*":
                    return True
                if perm.resource == resource and perm.action == "*":
                    return True
                if perm.resource == "*" and perm.action == action:
                    return True
                if perm.resource == resource and perm.action == action:
                    return True
        return False

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Hash password with salt."""
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
