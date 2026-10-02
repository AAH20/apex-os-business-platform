"""Personalization rules engine."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from apex_os_bp.personalization.profiles import UserProfile


@dataclass
class RuleCondition:
    """A single condition to evaluate against a user profile.

    Attributes:
        field: The field path to check ('segments', 'preferences.X', 'attributes.Y').
        operator: Comparison operator ('eq', 'ne', 'gt', 'lt', 'gte', 'lte',
            'contains', 'in', 'not_in', 'exists').
        value: The value to compare against.
    """

    field: str
    operator: str
    value: Any

    _OPERATORS: dict[str, Callable[[Any, Any], bool]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self._OPERATORS = {
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
            "gt": lambda a, b: a is not None and b is not None and a > b,
            "lt": lambda a, b: a is not None and b is not None and a < b,
            "gte": lambda a, b: a is not None and b is not None and a >= b,
            "lte": lambda a, b: a is not None and b is not None and a <= b,
            "contains": lambda a, b: b in a if a is not None else False,
            "in": lambda a, b: a in b if b is not None else False,
            "not_in": lambda a, b: a not in b if b is not None else True,
            "exists": lambda a, b: (a is not None) == b,
        }

    def evaluate(self, profile: UserProfile) -> bool:
        """Evaluate this condition against a user profile."""
        actual = self._resolve_field(profile)
        op_func = self._OPERATORS.get(self.operator)
        if op_func is None:
            raise ValueError(f"Unknown operator: {self.operator}")
        return op_func(actual, self.value)

    def _resolve_field(self, profile: UserProfile) -> Any:
        """Resolve a field path against a profile."""
        parts = self.field.split(".")
        if parts[0] == "segments":
            if len(parts) == 1:
                return profile.segments
            return parts[1] if parts[1] in profile.segments else None
        elif parts[0] == "preferences":
            return profile.get_preference(parts[1]) if len(parts) > 1 else None
        elif parts[0] == "attributes":
            return profile.get_attribute(parts[1]) if len(parts) > 1 else None
        return None


@dataclass
class PersonalizationRule:
    """A personalization rule with conditions and an action.

    Attributes:
        rule_id: Unique identifier for the rule.
        name: Human-readable rule name.
        conditions: List of conditions (all must pass).
        action: The action to take when conditions match (arbitrary data).
        priority: Higher priority rules are evaluated first.
        enabled: Whether the rule is active.
        created_at: Unix timestamp of rule creation.
    """

    rule_id: str
    name: str
    conditions: list[RuleCondition] = field(default_factory=list)
    action: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def evaluate(self, profile: UserProfile) -> bool:
        """Check if all conditions match the given profile."""
        if not self.enabled:
            return False
        return all(cond.evaluate(profile) for cond in self.conditions)

    def to_dict(self) -> dict[str, Any]:
        """Serialize rule to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "conditions": [
                {"field": c.field, "operator": c.operator, "value": c.value}
                for c in self.conditions
            ],
            "action": dict(self.action),
            "priority": self.priority,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


class RuleEngine:
    """Engine for managing and evaluating personalization rules."""

    def __init__(self) -> None:
        self._rules: dict[str, PersonalizationRule] = {}

    def add_rule(self, rule: PersonalizationRule) -> None:
        """Add a rule to the engine."""
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if removed."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> PersonalizationRule | None:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def evaluate(self, profile: UserProfile) -> list[dict[str, Any]]:
        """Evaluate all enabled rules against a profile.

        Returns actions from matching rules, sorted by priority (descending).
        """
        matching: list[tuple[int, dict[str, Any]]] = []
        for rule in self._rules.values():
            if rule.evaluate(profile):
                matching.append((rule.priority, rule.action))
        matching.sort(key=lambda x: x[0], reverse=True)
        return [action for _, action in matching]

    def evaluate_single(
        self, profile: UserProfile, rule_id: str
    ) -> dict[str, Any] | None:
        """Evaluate a single rule against a profile."""
        rule = self._rules.get(rule_id)
        if rule and rule.evaluate(profile):
            return rule.action
        return None

    def list_rules(self) -> list[PersonalizationRule]:
        """Return all rules sorted by priority."""
        return sorted(self._rules.values(), key=lambda r: r.priority, reverse=True)

    def count(self) -> int:
        """Return the number of rules in the engine."""
        return len(self._rules)
