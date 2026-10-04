"""Feature flag manager — CRUD operations and lifecycle management."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .models import (
    Flag,
    FlagState,
    TargetingRule,
    RolloutConfig,
    RolloutStrategy,
    FlagAnalytics,
)
from .targeting import TargetingEngine
from .rollout import RolloutEngine
from .analytics import AnalyticsEngine
from .dependencies import DependencyEngine


class FeatureFlagManager:
    """Central manager for feature flags.

    Provides create, read, update, delete operations plus
    evaluation with targeting, rollout, and dependency resolution.
    """

    def __init__(self) -> None:
        self._flags: Dict[str, Flag] = {}
        self._analytics: Dict[str, FlagAnalytics] = {}
        self._targeting = TargetingEngine()
        self._rollout = RolloutEngine()
        self._analytics_engine = AnalyticsEngine()
        self._dependencies = DependencyEngine()

    # ── CRUD ──────────────────────────────────────────────────────────

    def create_flag(
        self,
        name: str,
        description: str = "",
        state: FlagState = FlagState.DISABLED,
        targeting_rules: Optional[List[TargetingRule]] = None,
        rollout_config: Optional[RolloutConfig] = None,
        dependencies: Optional[Set[str]] = None,
        tags: Optional[Set[str]] = None,
    ) -> Flag:
        """Create a new feature flag."""
        if name in self._flags:
            raise ValueError(f"Flag '{name}' already exists")

        flag = Flag(
            name=name,
            description=description,
            state=state,
            targeting_rules=targeting_rules or [],
            rollout_config=rollout_config or RolloutConfig(),
            dependencies=dependencies or set(),
            tags=tags or set(),
        )
        self._flags[name] = flag
        self._analytics[name] = FlagAnalytics(flag_name=name)

        # Register dependencies
        for dep in flag.dependencies:
            self._dependencies.add_dependency(name, dep)

        return flag

    def get_flag(self, name: str) -> Optional[Flag]:
        """Retrieve a flag by name."""
        return self._flags.get(name)

    def list_flags(
        self,
        state: Optional[FlagState] = None,
        tags: Optional[Set[str]] = None,
    ) -> List[Flag]:
        """List all flags, optionally filtered by state and tags."""
        flags = list(self._flags.values())
        if state is not None:
            flags = [f for f in flags if f.state == state]
        if tags:
            flags = [f for f in flags if tags.issubset(f.tags)]
        return flags

    def update_flag(self, flag_name: str, **kwargs: Any) -> Flag:
        """Update flag attributes."""
        flag = self._flags.get(flag_name)
        if flag is None:
            raise KeyError(f"Flag '{flag_name}' not found")

        allowed = {
            "description",
            "state",
            "targeting_rules",
            "rollout_config",
            "dependencies",
            "tags",
        }
        for key, value in kwargs.items():
            if key not in allowed:
                raise ValueError(f"Cannot update '{key}'")
            setattr(flag, key, value)

        # Update dependency graph if dependencies changed
        if "dependencies" in kwargs:
            self._dependencies.clear_dependencies(flag_name)
            for dep in flag.dependencies:
                self._dependencies.add_dependency(flag_name, dep)

        flag.bump_version()
        return flag

    def delete_flag(self, name: str) -> None:
        """Delete a flag and its analytics."""
        if name not in self._flags:
            raise KeyError(f"Flag '{name}' not found")

        del self._flags[name]
        self._analytics.pop(name, None)
        self._dependencies.clear_dependencies(name)

        # Remove this flag from other flags' dependencies
        for flag in self._flags.values():
            flag.dependencies.discard(name)

    # ── Evaluation ────────────────────────────────────────────────────

    def is_enabled(
        self,
        name: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """Evaluate whether a flag is enabled for the given context.

        Resolution order:
        1. Check flag exists and is not disabled/archived.
        2. Check dependencies are satisfied.
        3. Check targeting rules.
        4. Check rollout configuration.
        """
        context = context or {}
        flag = self._flags.get(name)
        if flag is None:
            return False

        if flag.state == FlagState.DISABLED:
            self._record(name, user_id, False)
            return False

        if flag.state == FlagState.ARCHIVED:
            self._record(name, user_id, False)
            return False

        # Check dependencies
        if not self._dependencies.are_satisfied(name, self.is_enabled, context, user_id):
            self._record(name, user_id, False)
            return False

        # Check targeting rules
        if flag.targeting_rules:
            if not self._targeting.evaluate(flag.targeting_rules, context):
                self._record(name, user_id, False)
                return False

        # Check rollout
        if flag.state == FlagState.ROLLOUT:
            if user_id is None:
                self._record(name, user_id, False)
                return False
            if not self._rollout.is_in_rollout(flag.rollout_config, user_id):
                self._record(name, user_id, False)
                return False

        self._record(name, user_id, True)
        return True

    def evaluate_all(
        self,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Evaluate all flags and return a mapping of name -> enabled."""
        return {
            name: self.is_enabled(name, context, user_id)
            for name in self._flags
        }

    # ── Analytics ─────────────────────────────────────────────────────

    def get_analytics(self, name: str) -> Optional[FlagAnalytics]:
        """Get analytics for a specific flag."""
        return self._analytics.get(name)

    def get_all_analytics(self) -> Dict[str, FlagAnalytics]:
        """Get analytics for all flags."""
        return dict(self._analytics)

    def _record(self, name: str, user_id: Optional[str], enabled: bool) -> None:
        """Record an evaluation event."""
        if name in self._analytics:
            uid = user_id or "anonymous"
            self._analytics[name].record_evaluation(uid, enabled)

    # ── Dependencies ──────────────────────────────────────────────────

    def add_dependency(self, flag_name: str, depends_on: str) -> None:
        """Add a dependency: flag_name requires depends_on to be enabled."""
        flag = self._flags.get(flag_name)
        if flag is None:
            raise KeyError(f"Flag '{flag_name}' not found")
        if depends_on not in self._flags:
            raise KeyError(f"Dependency flag '{depends_on}' not found")

        flag.dependencies.add(depends_on)
        self._dependencies.add_dependency(flag_name, depends_on)
        flag.bump_version()

    def remove_dependency(self, flag_name: str, depends_on: str) -> None:
        """Remove a dependency."""
        flag = self._flags.get(flag_name)
        if flag is None:
            raise KeyError(f"Flag '{flag_name}' not found")

        flag.dependencies.discard(depends_on)
        self._dependencies.remove_dependency(flag_name, depends_on)
        flag.bump_version()

    def get_dependencies(self, flag_name: str) -> Set[str]:
        """Get all dependencies for a flag."""
        flag = self._flags.get(flag_name)
        if flag is None:
            raise KeyError(f"Flag '{flag_name}' not found")
        return set(flag.dependencies)

    def get_dependents(self, flag_name: str) -> Set[str]:
        """Get all flags that depend on the given flag."""
        return self._dependencies.get_dependents(flag_name)

    # ── Rollout Management ────────────────────────────────────────────

    def set_rollout_percentage(self, name: str, percentage: float) -> None:
        """Set the rollout percentage for a flag."""
        flag = self._flags.get(name)
        if flag is None:
            raise KeyError(f"Flag '{name}' not found")
        flag.rollout_config.percentage = max(0.0, min(100.0, percentage))
        flag.bump_version()

    def advance_rollout_ring(self, name: str) -> None:
        """Advance to the next ring in a ring-based rollout."""
        flag = self._flags.get(name)
        if flag is None:
            raise KeyError(f"Flag '{name}' not found")
        if flag.rollout_config.strategy != RolloutStrategy.RING:
            raise ValueError(f"Flag '{name}' is not using ring strategy")
        if flag.rollout_config.current_ring < len(flag.rollout_config.rings) - 1:
            flag.rollout_config.current_ring += 1
            flag.bump_version()

    def add_user_to_rollout(self, name: str, user_id: str) -> None:
        """Add a specific user to the rollout user list."""
        flag = self._flags.get(name)
        if flag is None:
            raise KeyError(f"Flag '{name}' not found")
        flag.rollout_config.user_ids.add(user_id)
        flag.bump_version()

    def remove_user_from_rollout(self, name: str, user_id: str) -> None:
        """Remove a user from the rollout user list."""
        flag = self._flags.get(name)
        if flag is None:
            raise KeyError(f"Flag '{name}' not found")
        flag.rollout_config.user_ids.discard(user_id)
        flag.bump_version()
