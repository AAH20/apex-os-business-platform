"""Alert history for tracking all alert lifecycle events."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from apex_os_bp.alerting.models import (
    Alert,
    AlertHistoryEntry,
    AlertSeverity,
    AlertStatus,
)

logger = logging.getLogger(__name__)


class AlertHistory:
    """Stores and queries alert history entries."""

    def __init__(self, max_entries: int = 50000):
        self._entries: List[AlertHistoryEntry] = []
        self._max_entries = max_entries
        self._index_by_alert: Dict[str, List[int]] = {}
        self._index_by_rule: Dict[str, List[int]] = {}
        self._index_by_status: Dict[str, List[int]] = {}
        self._index_by_action: Dict[str, List[int]] = {}

    def record(
        self,
        alert: Alert,
        action: str,
        actor: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> AlertHistoryEntry:
        """Record an alert lifecycle event."""
        entry = AlertHistoryEntry(
            alert_id=alert.id,
            rule_id=alert.rule_id,
            rule_name=alert.rule_name,
            severity=alert.severity,
            status=alert.status,
            message=alert.message,
            source=alert.source,
            value=alert.value,
            threshold=alert.threshold,
            escalation_level=alert.escalation_level,
            action=action,
            actor=actor,
            details=details or {},
            timestamp=time.time(),
        )

        idx = len(self._entries)
        self._entries.append(entry)

        # Update indexes
        self._index_by_alert.setdefault(alert.id, []).append(idx)
        self._index_by_rule.setdefault(alert.rule_id, []).append(idx)
        self._index_by_status.setdefault(alert.status.value, []).append(idx)
        self._index_by_action.setdefault(action, []).append(idx)

        # Enforce max entries limit
        if len(self._entries) > self._max_entries:
            self._trim()

        return entry

    def _trim(self) -> None:
        """Trim oldest entries to maintain max size."""
        overflow = len(self._entries) - self._max_entries
        self._entries = self._entries[overflow:]
        # Rebuild indexes
        self._index_by_alert.clear()
        self._index_by_rule.clear()
        self._index_by_status.clear()
        self._index_by_action.clear()
        for idx, entry in enumerate(self._entries):
            self._index_by_alert.setdefault(entry.alert_id, []).append(idx)
            self._index_by_rule.setdefault(entry.rule_id, []).append(idx)
            self._index_by_status.setdefault(entry.status.value, []).append(idx)
            self._index_by_action.setdefault(entry.action, []).append(idx)

    def get_entries(
        self,
        alert_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        action: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        source: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
    ) -> List[AlertHistoryEntry]:
        """Get history entries with optional filters."""
        # Use indexes for the most selective filter
        candidate_indices: Optional[List[int]] = None

        if alert_id and alert_id in self._index_by_alert:
            candidate_indices = self._index_by_alert[alert_id]
        elif rule_id and rule_id in self._index_by_rule:
            candidate_indices = self._index_by_rule[rule_id]
        elif status and status.value in self._index_by_status:
            candidate_indices = self._index_by_status[status]
        elif action and action in self._index_by_action:
            candidate_indices = self._index_by_action[action]

        if candidate_indices is not None:
            entries = [self._entries[i] for i in candidate_indices]
        else:
            entries = list(self._entries)

        # Apply remaining filters
        if alert_id and candidate_indices is None:
            entries = [e for e in entries if e.alert_id == alert_id]
        if rule_id and candidate_indices is None:
            entries = [e for e in entries if e.rule_id == rule_id]
        if status and candidate_indices is None:
            entries = [e for e in entries if e.status == status]
        if action and candidate_indices is None:
            entries = [e for e in entries if e.action == action]
        if severity:
            entries = [e for e in entries if e.severity == severity]
        if source:
            entries = [e for e in entries if e.source == source]
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]

        # Return most recent first, limited
        entries.reverse()
        return entries[:limit]

    def get_entry(self, entry_id: str) -> Optional[AlertHistoryEntry]:
        """Get a specific history entry by ID."""
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    def get_alert_timeline(self, alert_id: str) -> List[AlertHistoryEntry]:
        """Get the full timeline of events for an alert."""
        return self.get_entries(alert_id=alert_id, limit=self._max_entries)

    def get_rule_history(
        self, rule_id: str, limit: int = 100
    ) -> List[AlertHistoryEntry]:
        """Get history for a specific rule."""
        return self.get_entries(rule_id=rule_id, limit=limit)

    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics."""
        by_action: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}

        for entry in self._entries:
            by_action[entry.action] = by_action.get(entry.action, 0) + 1
            by_status[entry.status.value] = by_status.get(entry.status.value, 0) + 1
            by_severity[entry.severity.value] = by_severity.get(entry.severity.value, 0) + 1

        return {
            "total_entries": len(self._entries),
            "unique_alerts": len(self._index_by_alert),
            "unique_rules": len(self._index_by_rule),
            "by_action": by_action,
            "by_status": by_status,
            "by_severity": by_severity,
            "max_entries": self._max_entries,
        }

    def clear(self) -> None:
        """Clear all history."""
        self._entries.clear()
        self._index_by_alert.clear()
        self._index_by_rule.clear()
        self._index_by_status.clear()
        self._index_by_action.clear()

    def export_entries(
        self,
        format: str = "list",
        **filters: Any,
    ) -> Any:
        """Export history entries in various formats."""
        entries = self.get_entries(**filters)

        if format == "list":
            return [e.to_dict() for e in entries]
        elif format == "dict":
            return {e.id: e.to_dict() for e in entries}
        elif format == "count":
            return len(entries)
        else:
            return [e.to_dict() for e in entries]
