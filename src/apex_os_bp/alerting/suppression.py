"""Alert suppression for silencing alerts based on rules."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from apex_os_bp.alerting.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    SuppressionRule,
)

logger = logging.getLogger(__name__)


class AlertSuppressor:
    """Manages alert suppression rules and suppression state."""

    def __init__(self):
        self._suppression_rules: Dict[str, SuppressionRule] = {}
        self._suppressed_alerts: Dict[str, Dict[str, Any]] = {}
        self._suppression_history: List[Dict[str, Any]] = []
        self._max_history = 10000

    def add_suppression_rule(self, rule: SuppressionRule) -> SuppressionRule:
        """Add a suppression rule."""
        self._suppression_rules[rule.id] = rule
        return rule

    def remove_suppression_rule(self, rule_id: str) -> bool:
        """Remove a suppression rule."""
        if rule_id in self._suppression_rules:
            del self._suppression_rules[rule_id]
            return True
        return False

    def get_suppression_rule(self, rule_id: str) -> Optional[SuppressionRule]:
        """Get a suppression rule by ID."""
        return self._suppression_rules.get(rule_id)

    def get_suppression_rules(
        self,
        enabled_only: bool = False,
        alert_rule_id: Optional[str] = None,
    ) -> List[SuppressionRule]:
        """Get suppression rules with optional filters."""
        rules = list(self._suppression_rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        if alert_rule_id:
            rules = [r for r in rules if r.alert_rule_id == alert_rule_id]
        return rules

    def update_suppression_rule(
        self, rule_id: str, **kwargs: Any
    ) -> Optional[SuppressionRule]:
        """Update a suppression rule."""
        rule = self._suppression_rules.get(rule_id)
        if not rule:
            return None
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        rule.updated_at = time.time()
        return rule

    def is_suppressed(self, alert: Alert) -> Optional[SuppressionRule]:
        """Check if an alert matches any active suppression rule."""
        now = time.time()

        for rule in self._suppression_rules.values():
            if not rule.enabled:
                continue

            # Check time-based suppression
            if rule.start_time and now < rule.start_time:
                continue
            if rule.end_time and now > rule.end_time:
                continue

            # Check duration-based suppression
            if rule.duration > 0:
                if rule.start_time is None:
                    continue
                if now > rule.start_time + rule.duration:
                    continue

            # Check alert rule ID match
            if rule.alert_rule_id and rule.alert_rule_id != alert.rule_id:
                continue

            # Check severity match
            if rule.severity and rule.severity != alert.severity:
                continue

            # Check source match
            if rule.source and rule.source != alert.source:
                continue

            # Check label match (all suppression labels must be present in alert)
            if rule.labels:
                if not all(
                    alert.labels.get(k) == v for k, v in rule.labels.items()
                ):
                    continue

            return rule

        return None

    def suppress_alert(
        self, alert: Alert, reason: str = "", rule_id: Optional[str] = None
    ) -> bool:
        """Suppress an alert."""
        if alert.status == AlertStatus.RESOLVED:
            return False

        alert.status = AlertStatus.SUPPRESSED
        alert.suppressed_at = time.time()
        alert.suppression_reason = reason or (f"Suppressed by rule {rule_id}" if rule_id else "Manual suppression")
        alert.updated_at = time.time()

        self._suppressed_alerts[alert.id] = {
            "alert_id": alert.id,
            "rule_id": rule_id,
            "reason": alert.suppression_reason,
            "suppressed_at": alert.suppressed_at,
        }

        self._record_suppression(alert, reason, rule_id)
        return True

    def unsuppress_alert(self, alert: Alert) -> bool:
        """Remove suppression from an alert."""
        if alert.status != AlertStatus.SUPPRESSED:
            return False

        alert.status = AlertStatus.FIRING
        alert.suppressed_at = None
        alert.suppression_reason = None
        alert.updated_at = time.time()

        self._suppressed_alerts.pop(alert.id, None)
        return True

    def check_and_suppress(self, alert: Alert) -> bool:
        """Check if an alert should be suppressed and suppress it if so."""
        rule = self.is_suppressed(alert)
        if rule:
            return self.suppress_alert(
                alert,
                reason=f"Suppressed by rule '{rule.name}'",
                rule_id=rule.id,
            )
        return False

    def _record_suppression(
        self, alert: Alert, reason: str, rule_id: Optional[str]
    ) -> None:
        """Record a suppression event."""
        entry = {
            "alert_id": alert.id,
            "rule_id": alert.rule_id,
            "suppression_rule_id": rule_id,
            "reason": reason,
            "timestamp": time.time(),
        }
        self._suppression_history.append(entry)
        if len(self._suppression_history) > self._max_history:
            self._suppression_history = self._suppression_history[-self._max_history:]

    def get_suppressed_alerts(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently suppressed alerts."""
        return dict(self._suppressed_alerts)

    def get_suppression_history(
        self,
        alert_id: Optional[str] = None,
        rule_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get suppression history with optional filters."""
        history = self._suppression_history
        if alert_id:
            history = [h for h in history if h["alert_id"] == alert_id]
        if rule_id:
            history = [h for h in history if h["rule_id"] == rule_id]
        return history

    def get_suppression_stats(self) -> Dict[str, Any]:
        """Get suppression statistics."""
        total_rules = len(self._suppression_rules)
        enabled_rules = sum(1 for r in self._suppression_rules.values() if r.enabled)

        return {
            "total_suppression_rules": total_rules,
            "enabled_suppression_rules": enabled_rules,
            "currently_suppressed_alerts": len(self._suppressed_alerts),
            "total_suppression_events": len(self._suppression_history),
        }

    def clear_history(self) -> None:
        """Clear suppression history."""
        self._suppression_history.clear()
        self._suppressed_alerts.clear()

    def cleanup_expired(self) -> int:
        """Remove expired suppression rules. Returns count removed."""
        now = time.time()
        expired = []
        for rule_id, rule in self._suppression_rules.items():
            if rule.end_time and now > rule.end_time:
                expired.append(rule_id)
            elif rule.duration > 0 and rule.start_time and now > rule.start_time + rule.duration:
                expired.append(rule_id)

        for rule_id in expired:
            del self._suppression_rules[rule_id]

        return len(expired)
