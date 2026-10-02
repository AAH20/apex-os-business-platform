"""Data models for the feature flag system."""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


class FlagState(enum.Enum):
    """Possible states of a feature flag."""

    DISABLED = "disabled"
    ENABLED = "enabled"
    ROLLOUT = "rollout"
    ARCHIVED = "archived"


class RolloutStrategy(enum.Enum):
    """Strategies for gradual rollout."""

    PERCENTAGE = "percentage"
    USER_LIST = "user_list"
    RING = "ring"


@dataclass
class TargetingRule:
    """A targeting rule that determines who sees a flag.

    Attributes:
        attribute: The user attribute to evaluate (e.g., "email", "plan", "country").
        operator: The comparison operator ("eq", "ne", "in", "not_in", "gt", "lt", "contains").
        value: The value to compare against.
        priority: Higher priority rules are evaluated first.
    """

    attribute: str
    operator: str
    value: Any
    priority: int = 0

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if the given context matches this rule."""
        actual = context.get(self.attribute)
        if actual is None:
            return False

        ops = {
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
            "in": lambda a, b: a in b if isinstance(b, (list, set, tuple, str)) else False,
            "not_in": lambda a, b: a not in b if isinstance(b, (list, set, tuple, str)) else True,
            "gt": lambda a, b: a > b if isinstance(a, (int, float)) and isinstance(b, (int, float)) else False,
            "lt": lambda a, b: a < b if isinstance(a, (int, float)) and isinstance(b, (int, float)) else False,
            "contains": lambda a, b: b in a if isinstance(a, str) and isinstance(b, str) else False,
        }

        fn = ops.get(self.operator)
        if fn is None:
            return False
        return fn(actual, self.value)


@dataclass
class RolloutConfig:
    """Configuration for gradual rollout.

    Attributes:
        strategy: The rollout strategy to use.
        percentage: Percentage of users to enable (0-100).
        user_ids: Specific user IDs to include.
        rings: Ordered rings for progressive rollout.
        current_ring: The currently active ring index.
    """

    strategy: RolloutStrategy = RolloutStrategy.PERCENTAGE
    percentage: float = 0.0
    user_ids: Set[str] = field(default_factory=set)
    rings: List[Set[str]] = field(default_factory=list)
    current_ring: int = 0

    def is_user_in_rollout(self, user_id: str) -> bool:
        """Determine if a user should see the flag based on rollout config."""
        if self.strategy == RolloutStrategy.USER_LIST:
            return user_id in self.user_ids

        if self.strategy == RolloutStrategy.RING:
            if not self.rings:
                return False
            active_rings = self.rings[: self.current_ring + 1]
            return any(user_id in ring for ring in active_rings)

        # PERCENTAGE strategy — deterministic hash-based bucketing
        if self.percentage >= 100:
            return True
        if self.percentage <= 0:
            return False
        bucket = (hash(user_id) % 10000) / 100.0
        return bucket < self.percentage


@dataclass
class Flag:
    """A feature flag.

    Attributes:
        name: Unique identifier for the flag.
        description: Human-readable description.
        state: Current state of the flag.
        targeting_rules: List of targeting rules.
        rollout_config: Rollout configuration.
        dependencies: Set of flag names this flag depends on.
        tags: Arbitrary tags for organization.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        version: Version number for optimistic locking.
    """

    name: str
    description: str = ""
    state: FlagState = FlagState.DISABLED
    targeting_rules: List[TargetingRule] = field(default_factory=list)
    rollout_config: RolloutConfig = field(default_factory=RolloutConfig)
    dependencies: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1

    def bump_version(self) -> None:
        """Increment version and update timestamp."""
        self.version += 1
        self.updated_at = time.time()


@dataclass
class FlagAnalytics:
    """Analytics data for a feature flag.

    Attributes:
        flag_name: Name of the flag.
        evaluations: Total number of evaluations.
        hits: Number of times the flag was enabled.
        misses: Number of times the flag was disabled.
        unique_users: Set of unique user IDs who have been evaluated.
        last_evaluated_at: Timestamp of last evaluation.
        daily_counts: Dict mapping date strings to evaluation counts.
    """

    flag_name: str
    evaluations: int = 0
    hits: int = 0
    misses: int = 0
    unique_users: Set[str] = field(default_factory=set)
    last_evaluated_at: Optional[float] = None
    daily_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def hit_rate(self) -> float:
        """Calculate the hit rate as a percentage."""
        if self.evaluations == 0:
            return 0.0
        return (self.hits / self.evaluations) * 100.0

    def record_evaluation(self, user_id: str, enabled: bool) -> None:
        """Record a single evaluation event."""
        self.evaluations += 1
        if enabled:
            self.hits += 1
        else:
            self.misses += 1
        self.unique_users.add(user_id)
        self.last_evaluated_at = time.time()

        from datetime import date

        today = date.today().isoformat()
        self.daily_counts[today] = self.daily_counts.get(today, 0) + 1


@dataclass
class FlagDependency:
    """Represents a dependency between two flags.

    Attributes:
        flag_name: The flag that has the dependency.
        depends_on: The flag that must be enabled.
        requirement: Whether the dependency is "required" or "optional".
    """

    flag_name: str
    depends_on: str
    requirement: str = "required"
