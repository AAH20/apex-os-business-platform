"""Badge system for gamification.

Badges are achievements users earn by meeting specific criteria.
They come in tiers (bronze, silver, gold, platinum) and can be
displayed on user profiles.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set


class BadgeTier(str, Enum):
    """Badge rarity tiers."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


@dataclass
class Badge:
    """Represents an achievement badge."""

    name: str
    description: str
    tier: BadgeTier
    icon: str = "🏅"
    badge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    criteria: str = ""
    points_bonus: int = 0
    is_hidden: bool = False
    max_awards: Optional[int] = None  # None means unlimited
    tags: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Badge name cannot be empty")
        if self.points_bonus < 0:
            raise ValueError("Points bonus cannot be negative")


@dataclass
class UserBadge:
    """A badge awarded to a specific user."""

    user_id: str
    badge: Badge
    awarded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    awarded_by: str = "system"
    user_badge_id: str = field(default_factory=lambda: str(uuid.uuid4))


class BadgeManager:
    """Manages badge definitions and user badge awards."""

    def __init__(self) -> None:
        self._badges: Dict[str, Badge] = {}
        self._user_badges: Dict[str, List[UserBadge]] = {}
        self._badge_counts: Dict[str, int] = {}  # badge_id -> times awarded

    def register_badge(self, badge: Badge) -> Badge:
        """Register a new badge definition.

        Raises:
            ValueError: If a badge with the same ID already exists.
        """
        if badge.badge_id in self._badges:
            raise ValueError(f"Badge with ID {badge.badge_id} already exists")
        self._badges[badge.badge_id] = badge
        self._badge_counts[badge.badge_id] = 0
        return badge

    def get_badge(self, badge_id: str) -> Optional[Badge]:
        """Get a badge definition by ID."""
        return self._badges.get(badge_id)

    def get_all_badges(self) -> List[Badge]:
        """Get all registered badges."""
        return list(self._badges.values())

    def get_badges_by_tier(self, tier: BadgeTier) -> List[Badge]:
        """Get all badges of a specific tier."""
        return [b for b in self._badges.values() if b.tier == tier]

    def get_badges_by_tag(self, tag: str) -> List[Badge]:
        """Get all badges with a specific tag."""
        return [b for b in self._badges.values() if tag in b.tags]

    def award_badge(
        self,
        user_id: str,
        badge_id: str,
        awarded_by: str = "system",
    ) -> UserBadge:
        """Award a badge to a user.

        Args:
            user_id: The user receiving the badge.
            badge_id: The badge to award.
            awarded_by: Who or what awarded the badge.

        Returns:
            The UserBadge record.

        Raises:
            ValueError: If badge doesn't exist, user already has it, or max awards reached.
        """
        badge = self._badges.get(badge_id)
        if badge is None:
            raise ValueError(f"Badge {badge_id} not found")

        user_badges = self._user_badges.get(user_id, [])
        if any(ub.badge.badge_id == badge_id for ub in user_badges):
            raise ValueError(f"User {user_id} already has badge {badge_id}")

        current_count = self._badge_counts.get(badge_id, 0)
        if badge.max_awards is not None and current_count >= badge.max_awards:
            raise ValueError(f"Badge {badge_id} has reached max awards ({badge.max_awards})")

        user_badge = UserBadge(
            user_id=user_id,
            badge=badge,
            awarded_by=awarded_by,
        )

        if user_id not in self._user_badges:
            self._user_badges[user_id] = []
        self._user_badges[user_id].append(user_badge)
        self._badge_counts[badge_id] = current_count + 1

        return user_badge

    def get_user_badges(self, user_id: str) -> List[UserBadge]:
        """Get all badges awarded to a user."""
        return list(self._user_badges.get(user_id, []))

    def get_user_badge_ids(self, user_id: str) -> Set[str]:
        """Get set of badge IDs a user has earned."""
        return {ub.badge.badge_id for ub in self._user_badges.get(user_id, [])}

    def has_badge(self, user_id: str, badge_id: str) -> bool:
        """Check if a user has a specific badge."""
        return any(
            ub.badge.badge_id == badge_id
            for ub in self._user_badges.get(user_id, [])
        )

    def get_badge_count(self, badge_id: str) -> int:
        """Get how many times a badge has been awarded."""
        return self._badge_counts.get(badge_id, 0)

    def get_user_badge_count(self, user_id: str) -> int:
        """Get total number of badges a user has earned."""
        return len(self._user_badges.get(user_id, []))

    def get_user_badges_by_tier(self, user_id: str, tier: BadgeTier) -> List[UserBadge]:
        """Get user's badges filtered by tier."""
        return [ub for ub in self._user_badges.get(user_id, []) if ub.badge.tier == tier]

    def get_recent_badges(self, user_id: str, limit: int = 5) -> List[UserBadge]:
        """Get most recently awarded badges for a user."""
        badges = self.get_user_badges(user_id)
        return sorted(badges, key=lambda ub: ub.awarded_at, reverse=True)[:limit]

    def remove_badge(self, user_id: str, badge_id: str) -> bool:
        """Remove a badge from a user. Returns True if removed."""
        user_badges = self._user_badges.get(user_id, [])
        for i, ub in enumerate(user_badges):
            if ub.badge.badge_id == badge_id:
                user_badges.pop(i)
                self._badge_counts[badge_id] = max(0, self._badge_counts.get(badge_id, 1) - 1)
                return True
        return False

    def get_leaderboard_badges(self, limit: int = 10) -> List[Badge]:
        """Get the most awarded badges."""
        sorted_badges = sorted(
            self._badges.values(),
            key=lambda b: self._badge_counts.get(b.badge_id, 0),
            reverse=True,
        )
        return sorted_badges[:limit]
