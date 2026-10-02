"""Tenant audit logging."""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import AuditLog


class TenantAuditLogger:
    """Logs tenant-scoped audit events."""

    def __init__(self) -> None:
        self._logs: List[AuditLog] = []
        self._lock = threading.Lock()

    def log(
        self,
        action: str,
        tenant_id: str = "",
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
            self._logs.append(entry)
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
            logs = list(self._logs)

        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]
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

    def clear(self) -> None:
        """Clear all audit logs."""
        with self._lock:
            self._logs.clear()
