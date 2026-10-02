"""Challenge system for gamification.

Challenges are time-bound tasks that users can complete for points
and badge rewards. They can be daily, weekly, or custom duration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set


class ChallengeStatus(str, Enum):
    """Status of a challenge."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ChallengeDifficulty(str, Enum):
    """Difficulty levels for challenges."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"
    LEGENDARY = "legendary"


@dataclass
class Challenge:
    """Represents a challenge that users can complete."""

    name: str
    description: str
    difficulty: ChallengeDifficulty
    points_reward: int
    challenge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    badge_reward_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_completions: Optional[int] = None  # None means unlimited
    required_actions: int = 1
    tags: Set[str] = field(default_factory=set)
    is_recurring: bool = False
    recurrence_interval: Optional[timedelta] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Challenge name cannot be empty")
        if self.points_reward < 0:
            raise ValueError("Points reward cannot be negative")
        if self.required_actions < 1:
            raise ValueError("Required actions must be at least 1")
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time")

    @property
    def is_active(self) -> bool:
        """Check if the challenge is currently active."""
        now = datetime.now(timezone.utc)
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True

    @property
    def duration(self) -> Optional[timedelta]:
        """Get the challenge duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def time_remaining(self) -> Optional[timedelta]:
        """Get time remaining until challenge ends."""
        if self.end_time is None:
            return None
        remaining = self.end_time - datetime.now(timezone.utc)
        return max(remaining, timedelta(0))


@dataclass
class UserChallenge:
    """A user's progress on a challenge."""

    user_id: str
    challenge: Challenge
    status: ChallengeStatus = ChallengeStatus.PENDING
    progress: int = 0
    user_challenge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def progress_percentage(self) -> float:
        """Get completion percentage."""
        if self.challenge.required_actions == 0:
            return 100.0
        return min(100.0, (self.progress / self.challenge.required_actions) * 100)

    @property
    def is_complete(self) -> bool:
        """Check if the challenge is complete."""
        return self.progress >= self.challenge.required_actions


class ChallengeManager:
    """Manages challenges and user progress."""

    def __init__(self) -> None:
        self._challenges: Dict[str, Challenge] = {}
        self._user_challenges: Dict[str, List[UserChallenge]] = {}
        self._completion_counts: Dict[str, int] = {}  # challenge_id -> completions

    def create_challenge(
        self,
        name: str,
        description: str,
        difficulty: ChallengeDifficulty,
        points_reward: int,
        badge_reward_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_completions: Optional[int] = None,
        required_actions: int = 1,
        tags: Optional[Set[str]] = None,
        is_recurring: bool = False,
        recurrence_interval: Optional[timedelta] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Challenge:
        """Create a new challenge."""
        challenge = Challenge(
            name=name,
            description=description,
            difficulty=difficulty,
            points_reward=points_reward,
            badge_reward_id=badge_reward_id,
            start_time=start_time,
            end_time=end_time,
            max_completions=max_completions,
            required_actions=required_actions,
            tags=tags or set(),
            is_recurring=is_recurring,
            recurrence_interval=recurrence_interval,
            metadata=metadata or {},
        )
        self._challenges[challenge.challenge_id] = challenge
        self._completion_counts[challenge.challenge_id] = 0
        return challenge

    def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Get a challenge by ID."""
        return self._challenges.get(challenge_id)

    def get_all_challenges(self) -> List[Challenge]:
        """Get all challenges."""
        return list(self._challenges.values())

    def get_active_challenges(self) -> List[Challenge]:
        """Get all currently active challenges."""
        return [c for c in self._challenges.values() if c.is_active]

    def get_challenges_by_difficulty(self, difficulty: ChallengeDifficulty) -> List[Challenge]:
        """Get challenges filtered by difficulty."""
        return [c for c in self._challenges.values() if c.difficulty == difficulty]

    def get_challenges_by_tag(self, tag: str) -> List[Challenge]:
        """Get challenges filtered by tag."""
        return [c for c in self._challenges.values() if tag in c.tags]

    def get_upcoming_challenges(self) -> List[Challenge]:
        """Get challenges that haven't started yet."""
        now = datetime.now(timezone.utc)
        return [c for c in self._challenges.values() if c.start_time and c.start_time > now]

    def get_expired_challenges(self) -> List[Challenge]:
        """Get challenges that have ended."""
        now = datetime.now(timezone.utc)
        return [c for c in self._challenges.values() if c.end_time and c.end_time < now]

    def start_challenge(self, user_id: str, challenge_id: str) -> UserChallenge:
        """Start a challenge for a user.

        Raises:
            ValueError: If challenge doesn't exist, is not active, or max completions reached.
        """
        challenge = self._challenges.get(challenge_id)
        if challenge is None:
            raise ValueError(f"Challenge {challenge_id} not found")
        if not challenge.is_active:
            raise ValueError(f"Challenge {challenge_id} is not active")

        current_completions = self._completion_counts.get(challenge_id, 0)
        if challenge.max_completions is not None and current_completions >= challenge.max_completions:
            raise ValueError(f"Challenge {challenge_id} has reached max completions")

        user_challenges = self._user_challenges.get(user_id, [])
        existing = next(
            (uc for uc in user_challenges if uc.challenge.challenge_id == challenge_id), None
        )
        if existing and existing.status == ChallengeStatus.ACTIVE:
            raise ValueError(f"User {user_id} already has an active challenge {challenge_id}")
        if existing and existing.status == ChallengeStatus.COMPLETED:
            raise ValueError(f"User {user_id} already completed challenge {challenge_id}")

        user_challenge = UserChallenge(
            user_id=user_id,
            challenge=challenge,
            status=ChallengeStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        if user_id not in self._user_challenges:
            self._user_challenges[user_id] = []
        self._user_challenges[user_id].append(user_challenge)
        return user_challenge

    def update_progress(
        self,
        user_id: str,
        challenge_id: str,
        progress_increment: int = 1,
    ) -> UserChallenge:
        """Update a user's progress on a challenge.

        Returns:
            The updated UserChallenge.

        Raises:
            ValueError: If user doesn't have an active challenge.
        """
        user_challenges = self._user_challenges.get(user_id, [])
        user_challenge = next(
            (uc for uc in user_challenges if uc.challenge.challenge_id == challenge_id), None
        )
        if user_challenge is None:
            raise ValueError(f"User {user_id} has no challenge {challenge_id}")
        if user_challenge.status != ChallengeStatus.ACTIVE:
            raise ValueError(f"Challenge {challenge_id} is not active for user {user_id}")

        user_challenge.progress += progress_increment

        if user_challenge.is_complete:
            user_challenge.status = ChallengeStatus.COMPLETED
            user_challenge.completed_at = datetime.now(timezone.utc)
            self._completion_counts[challenge_id] = (
                self._completion_counts.get(challenge_id, 0) + 1
            )

        return user_challenge

    def complete_challenge(self, user_id: str, challenge_id: str) -> UserChallenge:
        """Mark a challenge as complete (sets progress to required actions)."""
        user_challenges = self._user_challenges.get(user_id, [])
        user_challenge = next(
            (uc for uc in user_challenges if uc.challenge.challenge_id == challenge_id), None
        )
        if user_challenge is None:
            raise ValueError(f"User {user_id} has no challenge {challenge_id}")

        user_challenge.progress = user_challenge.challenge.required_actions
        user_challenge.status = ChallengeStatus.COMPLETED
        user_challenge.completed_at = datetime.now(timezone.utc)
        self._completion_counts[challenge_id] = (
            self._completion_counts.get(challenge_id, 0) + 1
        )
        return user_challenge

    def fail_challenge(self, user_id: str, challenge_id: str) -> UserChallenge:
        """Mark a challenge as failed for a user."""
        user_challenges = self._user_challenges.get(user_id, [])
        user_challenge = next(
            (uc for uc in user_challenges if uc.challenge.challenge_id == challenge_id), None
        )
        if user_challenge is None:
            raise ValueError(f"User {user_id} has no challenge {challenge_id}")

        user_challenge.status = ChallengeStatus.FAILED
        return user_challenge

    def get_user_challenges(
        self,
        user_id: str,
        status: Optional[ChallengeStatus] = None,
    ) -> List[UserChallenge]:
        """Get challenges for a user, optionally filtered by status."""
        user_challenges = self._user_challenges.get(user_id, [])
        if status is not None:
            user_challenges = [uc for uc in user_challenges if uc.status == status]
        return list(user_challenges)

    def get_user_active_challenges(self, user_id: str) -> List[UserChallenge]:
        """Get all active challenges for a user."""
        return self.get_user_challenges(user_id, ChallengeStatus.ACTIVE)

    def get_user_completed_challenges(self, user_id: str) -> List[UserChallenge]:
        """Get all completed challenges for a user."""
        return self.get_user_challenges(user_id, ChallengeStatus.COMPLETED)

    def get_user_challenge_count(
        self,
        user_id: str,
        status: Optional[ChallengeStatus] = None,
    ) -> int:
        """Get count of user's challenges, optionally filtered by status."""
        return len(self.get_user_challenges(user_id, status))

    def get_challenge_completion_count(self, challenge_id: str) -> int:
        """Get how many users have completed a challenge."""
        return self._completion_counts.get(challenge_id, 0)

    def get_challenge_leaderboard(self, challenge_id: str) -> List[UserChallenge]:
        """Get user challenges sorted by completion time (fastest first)."""
        all_ucs = []
        for user_challenges in self._user_challenges.values():
            for uc in user_challenges:
                if uc.challenge.challenge_id == challenge_id:
                    all_ucs.append(uc)

        return sorted(
            all_ucs,
            key=lambda uc: (
                uc.completed_at or datetime.max.replace(tzinfo=timezone.utc),
                -uc.progress,
            ),
        )

    def cancel_challenge(self, user_id: str, challenge_id: str) -> bool:
        """Cancel a user's challenge. Returns True if cancelled."""
        user_challenges = self._user_challenges.get(user_id, [])
        for uc in user_challenges:
            if uc.challenge.challenge_id == challenge_id and uc.status == ChallengeStatus.ACTIVE:
                uc.status = ChallengeStatus.CANCELLED
                return True
        return False

    def get_available_challenges(self, user_id: str) -> List[Challenge]:
        """Get challenges the user can still start (not already active/completed)."""
        user_challenges = self._user_challenges.get(user_id, [])
        taken_ids = {uc.challenge.challenge_id for uc in user_challenges}
        return [
            c
            for c in self._challenges.values()
            if c.is_active and c.challenge_id not in taken_ids
        ]
