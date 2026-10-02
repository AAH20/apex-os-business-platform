"""Alert rules engine for evaluating conditions and triggering alerts."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from apex_os_bp.alerting.models import Alert, AlertRule, AlertSeverity, AlertStatus

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Evaluates alert conditions against metric values."""

    COMPARISONS: Dict[str, Callable[[float, float], bool]] = {
        "gt": lambda a, b: a > b,
        "lt": lambda a, b: a < b,
        "eq": lambda a, b: a == b,
        "gte": lambda a, b: a >= b,
        "lte": lambda a, b: a <= b,
        "neq": lambda a, b: a != b,
    }

    def __init__(self):
        self._custom_comparisons: Dict[str, Callable[[float, float], bool]] = {}

    def register_comparison(
        self, name: str, func: Callable[[float, float], bool]
    ) -> None:
        """Register a custom comparison function."""
        self._custom_comparisons[name] = func

    def evaluate(self, value: float, threshold: float, comparison: str) -> bool:
        """Evaluate a condition."""
        func = self._custom_comparisons.get(comparison) or self.COMPARISONS.get(comparison)
        if func is None:
            logger.error(f"Unknown comparison operator: {comparison}")
            return False
        return func(value, threshold)

    def evaluate_expression(self, expression: str, context: Dict[str, Any]) -> bool:
        """Evaluate a boolean expression string."""
        try:
            # Safe evaluation with limited builtins
            allowed_names = {k: v for k, v in context.items() if isinstance(v, (int, float, bool, str))}
            allowed_names.update({"True": True, "False": False, "None": None})
            return bool(eval(expression, {"__builtins__": {}}, allowed_names))
        except Exception as e:
            logger.error(f"Failed to evaluate expression '{expression}': {e}")
            return False


class AlertRuleEngine:
    """Engine for managing alert rules and evaluating conditions."""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._evaluator = ConditionEvaluator()
        self._condition_history: Dict[str, List[Tuple[float, bool]]] = {}
        self._max_history_per_rule = 1000

    @property
    def evaluator(self) -> ConditionEvaluator:
        """Get the condition evaluator."""
        return self._evaluator

    def add_rule(self, rule: AlertRule) -> AlertRule:
        """Add an alert rule."""
        self._rules[rule.id] = rule
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            self._condition_history.pop(rule_id, None)
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get an alert rule by ID."""
        return self._rules.get(rule_id)

    def get_rules(
        self,
        enabled_only: bool = False,
        severity: Optional[AlertSeverity] = None,
    ) -> List[AlertRule]:
        """Get all alert rules with optional filters."""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        if severity:
            rules = [r for r in rules if r.severity == severity]
        return rules

    def update_rule(self, rule_id: str, **kwargs: Any) -> Optional[AlertRule]:
        """Update an alert rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        rule.updated_at = time.time()
        return rule

    def enable_rule(self, rule_id: str) -> bool:
        """Enable an alert rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            rule.updated_at = time.time()
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable an alert rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            rule.updated_at = time.time()
            return True
        return False

    def evaluate_rule(
        self, rule: AlertRule, value: float, source: str = ""
    ) -> Optional[Alert]:
        """Evaluate a rule against a metric value."""
        if not rule.enabled:
            return None

        triggered = self._evaluator.evaluate(value, rule.threshold, rule.comparison)

        # Track condition history for duration-based rules
        now = time.time()
        history = self._condition_history.setdefault(rule.id, [])
        history.append((now, triggered))
        if len(history) > self._max_history_per_rule:
            history = history[-self._max_history_per_rule:]
            self._condition_history[rule.id] = history

        if not triggered:
            return None

        # Check duration requirement
        if rule.duration > 0:
            # Condition must be continuously true for `duration` seconds
            if not history:
                return None
            # Find the start of the current true streak
            streak_start = now
            for ts, result in reversed(history):
                if result:
                    streak_start = ts
                else:
                    break
            if (now - streak_start) < rule.duration:
                return None

        # Create alert
        alert = Alert(
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            message=f"Alert '{rule.name}' triggered: {rule.condition} (value={value}, threshold={rule.threshold})",
            source=source,
            labels=dict(rule.labels),
            annotations=dict(rule.annotations),
            value=value,
            threshold=rule.threshold,
            notification_channels=list(rule.notification_channels),
        )
        return alert

    def evaluate_all(
        self, metrics: Dict[str, float], source: str = ""
    ) -> List[Alert]:
        """Evaluate all enabled rules against a set of metrics."""
        alerts = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            # Try to match metric by rule name or condition
            value = metrics.get(rule.name)
            if value is None:
                value = metrics.get(rule.condition)
            if value is None:
                continue
            alert = self.evaluate_rule(rule, value, source)
            if alert:
                alerts.append(alert)
        return alerts

    def check_rule_health(self, rule_id: str) -> Dict[str, Any]:
        """Check the health of a rule's condition history."""
        history = self._condition_history.get(rule_id, [])
        if not history:
            return {"rule_id": rule_id, "total_evaluations": 0, "triggered_count": 0, "trigger_ratio": 0.0}

        triggered = sum(1 for _, result in history if result)
        return {
            "rule_id": rule_id,
            "total_evaluations": len(history),
            "triggered_count": triggered,
            "trigger_ratio": triggered / len(history) if history else 0.0,
        }

    def clear_history(self, rule_id: Optional[str] = None) -> None:
        """Clear condition history for a rule or all rules."""
        if rule_id:
            self._condition_history.pop(rule_id, None)
        else:
            self._condition_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        total_rules = len(self._rules)
        enabled_rules = sum(1 for r in self._rules.values() if r.enabled)
        by_severity: Dict[str, int] = {}
        for rule in self._rules.values():
            sev = rule.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "by_severity": by_severity,
            "total_condition_history": sum(
                len(h) for h in self._condition_history.values()
            ),
        }
