"""Role-Based Access Control (RBAC) for APEX-OS Business Platform."""

from enum import Enum
from functools import wraps
from typing import Callable, Dict, List, Optional, Set


class Permission(Enum):
    """All available permissions in the system."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    USER_MANAGE = "user_manage"
    AUDIT_READ = "audit_read"
    AUDIT_WRITE = "audit_write"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    RATE_LIMIT_OVERRIDE = "rate_limit_override"


class Role(Enum):
    """Predefined system roles."""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"


# Default permission mappings for each role
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.READ, Permission.WRITE, Permission.DELETE,
        Permission.ADMIN, Permission.USER_MANAGE,
        Permission.AUDIT_READ, Permission.AUDIT_WRITE,
        Permission.ENCRYPT, Permission.DECRYPT,
        Permission.RATE_LIMIT_OVERRIDE,
    },
    Role.MANAGER: {
        Permission.READ, Permission.WRITE,
        Permission.USER_MANAGE, Permission.AUDIT_READ,
        Permission.ENCRYPT, Permission.DECRYPT,
    },
    Role.USER: {
        Permission.READ, Permission.WRITE,
        Permission.ENCRYPT, Permission.DECRYPT,
    },
    Role.VIEWER: {
        Permission.READ,
    },
}


class RBACError(Exception):
    """Base exception for RBAC errors."""
    pass


class PermissionDeniedError(RBACError):
    """Raised when a user lacks the required permission."""
    pass


class RBACManager:
    """Manages role-based access control with support for custom roles."""

    def __init__(self):
        """Initialize RBAC with default role-permission mappings."""
        self._role_permissions: Dict[Role, Set[Permission]] = {
            role: set(perms) for role, perms in ROLE_PERMISSIONS.items()
        }
        self._custom_roles: Dict[str, Set[Permission]] = {}

    def get_permissions(self, roles: List[str]) -> Set[Permission]:
        """Get the union of all permissions for a list of roles.

        Args:
            roles: List of role name strings.

        Returns:
            Set of Permission enums the roles collectively have.
        """
        permissions: Set[Permission] = set()
        for role_name in roles:
            try:
                role = Role(role_name)
                permissions.update(self._role_permissions.get(role, set()))
            except ValueError:
                permissions.update(self._custom_roles.get(role_name, set()))
        return permissions

    def has_permission(self, roles: List[str], required: Permission) -> bool:
        """Check if any of the given roles has the required permission.

        Args:
            roles: List of role name strings.
            required: The permission to check for.

        Returns:
            True if at least one role grants the permission.
        """
        return required in self.get_permissions(roles)

    def has_any_permission(self, roles: List[str], required: List[Permission]) -> bool:
        """Check if any of the given roles has any of the required permissions.

        Args:
            roles: List of role name strings.
            required: List of permissions, any one of which suffices.

        Returns:
            True if at least one required permission is granted.
        """
        user_perms = self.get_permissions(roles)
        return any(p in user_perms for p in required)

    def has_all_permissions(self, roles: List[str], required: List[Permission]) -> bool:
        """Check if the given roles collectively have all required permissions.

        Args:
            roles: List of role name strings.
            required: List of permissions that must all be granted.

        Returns:
            True if all required permissions are granted.
        """
        user_perms = self.get_permissions(roles)
        return all(p in user_perms for p in required)

    def add_custom_role(self, name: str, permissions: List[Permission]) -> None:
        """Add a custom role with a specific set of permissions.

        Args:
            name: Unique name for the custom role.
            permissions: List of Permission enums for this role.
        """
        self._custom_roles[name] = set(permissions)

    def remove_custom_role(self, name: str) -> None:
        """Remove a custom role.

        Args:
            name: Name of the custom role to remove.
        """
        self._custom_roles.pop(name, None)

    def require_permission(self, permission: Permission) -> Callable:
        """Decorator factory that enforces a permission requirement.

        The decorated function must receive a ``roles`` keyword argument
        (or its first positional argument must have a ``roles`` attribute
        or be a dict with a ``roles`` key).

        Args:
            permission: The Permission required to call the function.

        Returns:
            Decorator that checks permission before invoking the function.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                roles = kwargs.get("roles", [])
                if not roles and args:
                    first_arg = args[0]
                    if hasattr(first_arg, "roles"):
                        roles = first_arg.roles
                    elif isinstance(first_arg, dict):
                        roles = first_arg.get("roles", [])
                if not self.has_permission(roles, permission):
                    raise PermissionDeniedError(
                        f"Permission '{permission.value}' required"
                    )
                return func(*args, **kwargs)
            return wrapper
        return decorator
