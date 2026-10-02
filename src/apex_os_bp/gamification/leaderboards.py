"""Leaderboard system for gamification.

Leaderboards rank users by points, badges, or custom metrics.
They support different time windows and categories.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable


class LeaderboardTimeWindow(str, Enum):
    """Time windows for leaderboard rankings."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL_TIME = "all_time"


class LeaderboardCategory(str, Enum):
    """Categories of leaderboards."""

    POINTS = "points"
    BADGES = "badges"
    CHALLENGES = "challenges"
    STREAK = "streak"
    CUSTOM = "custom"


@dataclass
class LeaderboardEntry:
    """A single entry on a leaderboard."""

    user_id: str
    score: float
    rank: int = 0
    previous_rank: int = 0
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def rank_change(self) -> int:
        """Positive means moved up, negative means moved down."""
        if self.previous_rank == 0:
            return 0
        return self.previous_rank - self.rank


@dataclass
class Leaderboard:
    """A ranked list of users by some metric."""

    name: str
    category: LeaderboardCategory
    time_window: LeaderboardTimeWindow
    leaderboard_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    is_active: bool = True
    max_entries: int = 100
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Leaderboard name cannot be empty")
        if self.max_entries < 1:
            raise ValueError("Max entries must be at least 1")


class LeaderboardManager:
    """Manages leaderboards and their entries."""

    def __init__(self) -> None:
        self._leaderboards: Dict[str, Leaderboard] = {}
        self._entries: Dict[str, Dict[str, LeaderboardEntry]] = {}  # lb_id -> {user_id -> entry}

    def create_leaderboard(
        self,
        name: str,
        category: LeaderboardCategory,
        time_window: LeaderboardTimeWindow,
        description: str = "",
        max_entries: int = 100,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Leaderboard:
        """Create a new leaderboard."""
        leaderboard = Leaderboard(
            name=name,
            category=category,
            time_window=time_window,
            description=description,
            max_entries=max_entries,
            metadata=metadata or {},
        )
        self._leaderboards[leaderboard.leaderboard_id] = leaderboard
        self._entries[leaderboard.leaderboard_id] = {}
        return leaderboard

    def get_leaderboard(self, leaderboard_id: str) -> Optional[Leaderboard]:
        """Get a leaderboard by ID."""
        return self._leaderboards.get(leaderboard_id)

    def get_all_leaderboards(self) -> List[Leaderboard]:
        """Get all leaderboards."""
        return list(self._leaderboards.values())

    def get_leaderboards_by_category(self, category: LeaderboardCategory) -> List[Leaderboard]:
        """Get leaderboards filtered by category."""
        return [lb for lb in self._leaderboards.values() if lb.category == category]

    def get_leaderboards_by_time_window(
        self, time_window: LeaderboardTimeWindow
    ) -> List[Leaderboard]:
        """Get leaderboards filtered by time window."""
        return [lb for lb in self._leaderboards.values() if lb.time_window == time_window]

    def submit_score(
        self,
        leaderboard_id: str,
        user_id: str,
        score: float,
        metadata: Optional[Dict[str, str]] = None,
    ) -> LeaderboardEntry:
        """Submit or update a user's score on a leaderboard.

        Args:
            leaderboard_id: The leaderboard to submit to.
            user_id: The user submitting the score.
            score: The score value.
            metadata: Optional additional data.

        Returns:
            The updated leaderboard entry.

        Raises:
            ValueError: If leaderboard doesn't exist or is inactive.
        """
        leaderboard = self._leaderboards.get(leaderboard_id)
        if leaderboard is None:
            raise ValueError(f"Leaderboard {leaderboard_id} not found")
        if not leaderboard.is_active:
            raise ValueError(f"Leaderboard {leaderboard_id} is not active")

        entries = self._entries.setdefault(leaderboard_id, {})

        previous_rank = 0
        if user_id in entries:
            previous_rank = entries[user_id].rank

        entry = LeaderboardEntry(
            user_id=user_id,
            score=score,
            previous_rank=previous_rank,
            metadata=metadata or {},
        )
        entries[user_id] = entry

        self._recalculate_ranks(leaderboard_id)
        return entry

    def _recalculate_ranks(self, leaderboard_id: str) -> None:
        """Recalculate ranks for all entries on a leaderboard."""
        leaderboard = self._leaderboards[leaderboard_id]
        entries = self._entries.get(leaderboard_id, {})

        sorted_entries = sorted(entries.values(), key=lambda e: e.score, reverse=True)

        for rank, entry in enumerate(sorted_entries, start=1):
            if rank <= leaderboard.max_entries:
                entry.rank = rank
            else:
                entry.rank = 0  # Beyond max_entries

    def get_rankings(
        self,
        leaderboard_id: str,
        limit: Optional[int] = None,
    ) -> List[LeaderboardEntry]:
        """Get ranked entries for a leaderboard.

        Args:
            leaderboard_id: The leaderboard to query.
            limit: Maximum number of entries to return.

        Returns:
            List of entries sorted by rank.
        """
        leaderboard = self._leaderboards.get(leaderboard_id)
        if leaderboard is None:
            raise ValueError(f"Leaderboard {leaderboard_id} not found")

        entries = self._entries.get(leaderboard_id, {})
        # Only include entries that are actually ranked (rank > 0)
        ranked_entries = [e for e in entries.values() if e.rank > 0]
        sorted_entries = sorted(ranked_entries, key=lambda e: e.rank)

        if limit is not None:
            sorted_entries = sorted_entries[:limit]
        return sorted_entries

    def get_user_rank(self, leaderboard_id: str, user_id: str) -> Optional[LeaderboardEntry]:
        """Get a user's entry on a specific leaderboard."""
        entries = self._entries.get(leaderboard_id, {})
        return entries.get(user_id)

    def get_user_rank_number(self, leaderboard_id: str, user_id: str) -> Optional[int]:
        """Get a user's rank number on a leaderboard."""
        entry = self.get_user_rank(leaderboard_id, user_id)
        return entry.rank if entry else None

    def get_top_users(self, leaderboard_id: str, count: int = 10) -> List[LeaderboardEntry]:
        """Get the top N users on a leaderboard."""
        return self.get_rankings(leaderboard_id, limit=count)

    def get_user_percentile(self, leaderboard_id: str, user_id: str) -> Optional[float]:
        """Get a user's percentile (0-100) on a leaderboard."""
        entries = self._entries.get(leaderboard_id, {})
        if not entries or user_id not in entries:
            return None

        user_entry = entries[user_id]
        total = len(entries)
        if total <= 1:
            return 100.0

        return round((1 - (user_entry.rank - 1) / (total - 1)) * 100, 2)

    def remove_entry(self, leaderboard_id: str, user_id: str) -> bool:
        """Remove a user from a leaderboard. Returns True if removed."""
        entries = self._entries.get(leaderboard_id, {})
        if user_id in entries:
            del entries[user_id]
            self._recalculate_ranks(leaderboard_id)
            return True
        return False

    def reset_leaderboard(self, leaderboard_id: str) -> None:
        """Clear all entries from a leaderboard."""
        if leaderboard_id in self._entries:
            self._entries[leaderboard_id] = {}

    def deactivate_leaderboard(self, leaderboard_id: str) -> None:
        """Deactivate a leaderboard (stops accepting new scores)."""
        leaderboard = self._leaderboards.get(leaderboard_id)
        if leaderboard:
            leaderboard.is_active = False

    def activate_leaderboard(self, leaderboard_id: str) -> None:
        """Activate a leaderboard."""
        leaderboard = self._leaderboards.get(leaderboard_id)
        if leaderboard:
            leaderboard.is_active = True

    def get_rank_changes(self, leaderboard_id: str) -> List[LeaderboardEntry]:
        """Get entries with rank changes (for notifications)."""
        entries = self._entries.get(leaderboard_id, {})
        return [e for e in entries.values() if e.rank_change != 0]
