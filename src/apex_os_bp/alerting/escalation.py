"""Alert escalation for progressively notifying higher-level responders."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from apex_os_bp.alerting.models import (
    Alert,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    EscalationPolicy,
    EscalationRule,
)

logger = logging.getLogger(__name__)


class AlertEscalator:
    """Manages alert escalation policies and escalation state."""

    def __init__(self):
        self._escalation_rules: Dict[str, EscalationRule] = {}
        self._alert_escalation_state: Dict[str, Dict[str, Any]] = {}
        self._escalation_history: List[Dict[str, Any]] = []
        self._max_history = 10000

    def add_escalation_rule(self, rule: EscalationRule) -> EscalationRule:
        """Add an escalation rule."""
        self._escalation_rules[rule.id] = rule
        return rule

    def remove_escalation_rule(self, rule_id: str) -> bool:
        """Remove an escalation rule."""
        if rule_id in self._escalation_rules:
            del self._escalation_rules[rule_id]
            return True
        return False

    def get_escalation_rule(self, rule_id: str) -> Optional[EscalationRule]:
        """Get an escalation rule by ID."""
        return self._escalation_rules.get(rule_id)

    def get_escalation_rules(
        self,
        enabled_only: bool = False,
        alert_rule_id: Optional[str] = None,
    ) -> List[EscalationRule]:
        """Get escalation rules with optional filters."""
        rules = list(self._escalation_rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        if alert_rule_id:
            rules = [r for r in rules if r.alert_rule_id == alert_rule_id]
        return rules

    def update_escalation_rule(
        self, rule_id: str, **kwargs: Any
    ) -> Optional[EscalationRule]:
        """Update an escalation rule."""
        rule = self._escalation_rules.get(rule_id)
        if not rule:
            return None
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        rule.updated_at = time.time()
        return rule

    def check_escalation(self, alert: Alert, rule: Optional[AlertRule] = None) -> bool:
        """Check if an alert should be escalated."""
        if alert.status in (AlertStatus.RESOLVED, AlertStatus.SUPPRESSED):
            return False

        # Find applicable escalation rule
        esc_rule = self._find_escalation_rule(alert, rule)
        if not esc_rule or not esc_rule.enabled:
            return False

        # Get or initialize escalation state
        state = self._alert_escalation_state.setdefault(
            alert.id,
            {
                "current_level": 0,
                "last_escalation_time": alert.created_at,
                "escalation_count": 0,
            },
        )

        current_level = state["current_level"]
        if current_level >= esc_rule.max_level:
            return False

        # Calculate next escalation delay based on policy
        next_delay = self._calculate_escalation_delay(
            esc_rule.escalation_policy,
            esc_rule.escalation_delay,
            current_level,
        )

        # Check if enough time has passed
        now = time.time()
        time_since_last = now - state["last_escalation_time"]
        if time_since_last < next_delay:
            return False

        # Perform escalation
        new_level = current_level + 1
        state["current_level"] = new_level
        state["last_escalation_time"] = now
        state["escalation_count"] += 1

        alert.escalation_level = new_level
        alert.status = AlertStatus.ESCALATED
        alert.escalated_at = now
        alert.updated_at = now

        # Record escalation
        self._record_escalation(alert, esc_rule, new_level)

        logger.warning(
            f"Alert {alert.id} escalated to level {new_level} "
            f"(rule: {esc_rule.name})"
        )
        return True

    def _find_escalation_rule(
        self, alert: Alert, rule: Optional[AlertRule]
    ) -> Optional[EscalationRule]:
        """Find the applicable escalation rule for an alert."""
        # First try by alert rule ID
        for esc_rule in self._escalation_rules.values():
            if esc_rule.alert_rule_id == alert.rule_id and esc_rule.enabled:
                return esc_rule

        # Then try by severity
        for esc_rule in self._escalation_rules.values():
            if esc_rule.severity == alert.severity and esc_rule.enabled:
                return esc_rule

        # Fall back to default (first enabled rule)
        for esc_rule in self._escalation_rules.values():
            if esc_rule.enabled:
                return esc_rule

        return None

    def _calculate_escalation_delay(
        self,
        policy: EscalationPolicy,
        base_delay: int,
        current_level: int,
    ) -> int:
        """Calculate the delay before the next escalation."""
        if policy == EscalationPolicy.FIXED:
            return base_delay
        elif policy == EscalationPolicy.LINEAR:
            return base_delay * (current_level + 1)
        elif policy == EscalationPolicy.EXPONENTIAL:
            return base_delay * (2 ** current_level)
        return base_delay

    def _record_escalation(
        self, alert: Alert, esc_rule: EscalationRule, new_level: int
    ) -> None:
        """Record an escalation event."""
        entry = {
            "alert_id": alert.id,
            "rule_id": alert.rule_id,
            "escalation_rule_id": esc_rule.id,
            "escalation_rule_name": esc_rule.name,
            "previous_level": new_level - 1,
            "new_level": new_level,
            "timestamp": time.time(),
        }
        self._escalation_history.append(entry)
        if len(self._escalation_history) > self._max_history:
            self._escalation_history = self._escalation_history[-self._max_history:]

    def acknowledge_alert(
        self, alert: Alert, acknowledged_by: str = ""
    ) -> bool:
        """Acknowledge an alert, stopping further escalation."""
        if alert.status == AlertStatus.RESOLVED:
            return False

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = time.time()
        alert.acknowledged_by = acknowledged_by
        alert.updated_at = time.time()

        # Reset escalation state
        state = self._alert_escalation_state.get(alert.id)
        if state:
            state["current_level"] = 0

        self._record_escalation(alert, EscalationRule(name="acknowledge"), 0)
        return True

    def resolve_alert(self, alert: Alert) -> bool:
        """Resolve an alert."""
        if alert.status == AlertStatus.RESOLVED:
            return False

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = time.time()
        alert.updated_at = time.time()

        # Clean up escalation state
        self._alert_escalation_state.pop(alert.id, None)
        return True

    def get_escalation_state(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get the escalation state for an alert."""
        return self._alert_escalation_state.get(alert_id)

    def get_escalation_history(
        self,
        alert_id: Optional[str] = None,
        rule_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get escalation history with optional filters."""
        history = self._escalation_history
        if alert_id:
            history = [h for h in history if h["alert_id"] == alert_id]
        if rule_id:
            history = [h for h in history if h["rule_id"] == rule_id]
        return history

    def get_escalation_stats(self) -> Dict[str, Any]:
        """Get escalation statistics."""
        total_alerts = len(self._alert_escalation_state)
        escalated_alerts = sum(
            1 for s in self._alert_escalation_state.values() if s["escalation_count"] > 0
        )
        total_escalations = sum(
            s["escalation_count"] for s in self._alert_escalation_state.values()
        )

        return {
            "total_alerts_tracked": total_alerts,
            "escalated_alerts": escalated_alerts,
            "total_escalation_events": total_escalations,
            "escalation_rules": len(self._escalation_rules),
            "enabled_escalation_rules": sum(
                1 for r in self._escalation_rules.values() if r.enabled
            ),
        }

    def clear_history(self) -> None:
        """Clear escalation history."""
        self._escalation_history.clear()
        self._alert_escalation_state.clear()
