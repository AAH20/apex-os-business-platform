"""Tenant audit logging."""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import AuditLog


class TenantAuditLogger:
    """Logs tenant-scoped audit events."""

    def __init__(self) -> None:
        self._logs: Dict[str, List[AuditLog]] = {}
        self._lock = threading.Lock()

    def log(
        self,
        tenant_id: str,
        action: str = "",
        user_id: Optional[str] = None,
        resource_type: str = "",
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
        with self._lock:
            self._logs.setdefault(tenant_id, []).append(entry)
        return entry

    def get_logs(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[AuditLog]:
        """Get audit logs with optional filters."""
        with self._lock:
            if tenant_id:
                logs = list(self._logs.get(tenant_id, []))
            else:
                logs = [l for tenant_logs in self._logs.values() for l in tenant_logs]
        if user_id:
            logs = [l for l in logs if l.user_id == user_id]
        if action:
            logs = [l for l in logs if l.action == action]
        if resource_type:
            logs = [l for l in logs if l.resource_type == resource_type]
        if since:
            logs = [l for l in logs if l.timestamp >= since]
        if limit:
            logs = logs[:limit]

        return logs

    def clear(self, tenant_id: Optional[str] = None) -> None:
        """Clear audit logs, optionally filtered by tenant."""
        with self._lock:
            if tenant_id is not None:
                self._logs.pop(tenant_id, None)
            else:
                self._logs.clear()
