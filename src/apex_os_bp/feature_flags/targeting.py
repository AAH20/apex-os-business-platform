"""Targeting engine — evaluates targeting rules against user context."""

from __future__ import annotations

from typing import Any, Dict, List

from .models import TargetingRule


class TargetingEngine:
    """Evaluates targeting rules to determine flag visibility."""

    def evaluate(self, rules: List[TargetingRule], context: Dict[str, Any]) -> bool:
        """Evaluate all rules against the given context.

        Rules are sorted by priority (highest first). All rules must pass
        (AND logic). If no rules are provided, the flag is visible to all.
        """
        if not rules:
            return True

        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        return all(rule.matches(context) for rule in sorted_rules)

    def evaluate_any(self, rules: List[TargetingRule], context: Dict[str, Any]) -> bool:
        """Evaluate rules with OR logic — at least one must match."""
        if not rules:
            return True
        return any(rule.matches(context) for rule in rules)

    def add_rule(
        self,
        rules: List[TargetingRule],
        attribute: str,
        operator: str,
        value: Any,
        priority: int = 0,
    ) -> List[TargetingRule]:
        """Add a new targeting rule and return the updated list."""
        rules.append(TargetingRule(attribute=attribute, operator=operator, value=value, priority=priority))
        return rules
