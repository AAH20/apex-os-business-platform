"""Rollout engine — manages gradual rollout strategies."""

from __future__ import annotations

from .models import RolloutConfig, RolloutStrategy


class RolloutEngine:
    """Determines whether a user is included in a gradual rollout."""

    def is_in_rollout(self, config: RolloutConfig, user_id: str) -> bool:
        """Check if a user is in the rollout based on the config strategy."""
        return config.is_user_in_rollout(user_id)

    def get_percentage(self, config: RolloutConfig) -> float:
        """Get the current rollout percentage."""
        return config.percentage

    def set_percentage(self, config: RolloutConfig, percentage: float) -> None:
        """Set the rollout percentage, clamped to [0, 100]."""
        config.percentage = max(0.0, min(100.0, percentage))

    def get_active_ring_users(self, config: RolloutConfig) -> set:
        """Get all users in the currently active rings."""
        if config.strategy != RolloutStrategy.RING or not config.rings:
            return set()
        active = config.rings[: config.current_ring + 1]
        users = set()
        for ring in active:
            users.update(ring)
        return users
