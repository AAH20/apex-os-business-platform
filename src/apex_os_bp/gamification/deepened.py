"""Deepened gamification module: points, badges, leaderboards, quests, challenges."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Rarity(Enum):
    COMMON = 1
    RARE = 2
    EPIC = 3
    LEGENDARY = 4


@dataclass
class PointsProfile:
    user_id: str
    total_points: int = 0
    lifetime_points: int = 0
    level: int = 1
    xp_to_next: int = 100
    history: list[dict[str, Any]] = field(default_factory=list)

    LEVEL_THRESHOLDS = (0, 100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000)

    def add_points(self, amount: int, reason: str = "") -> int:
        if amount <= 0:
            return self.level
        self.total_points += amount
        self.lifetime_points += amount
        self.history.append({"amount": amount, "reason": reason})
        self._recalculate_level()
        return self.level

    def _recalculate_level(self) -> None:
        new_level = 1
        for i, threshold in enumerate(self.LEVEL_THRESHOLDS):
            if self.lifetime_points >= threshold:
                new_level = i + 1
        self.level = new_level
        next_threshold = (
            self.LEVEL_THRESHOLDS[new_level]
            if new_level < len(self.LEVEL_THRESHOLDS)
            else self.LEVEL_THRESHOLDS[-1] * 2
        )
        self.xp_to_next = max(0, next_threshold - self.lifetime_points)

    def spend(self, amount: int) -> bool:
        if amount > self.total_points:
            return False
        self.total_points -= amount
        return True


@dataclass
class Badge:
    badge_id: str
    name: str
    description: str
    rarity: Rarity
    icon: str = "🏆"
    criteria: dict[str, Any] = field(default_factory=dict)
    hidden: bool = False

    def check_unlock(self, profile: PointsProfile, stats: dict[str, Any]) -> bool:
        for key, target in self.criteria.items():
            if stats.get(key, 0) < target:
                return False
        return True


@dataclass
class Achievement:
    achievement_id: str
    name: str
    description: str
    badge: Badge
    points_reward: int = 50
    unlocked_at: str | None = None
    progress: float = 0.0

    def update_progress(self, current: int, target: int) -> bool:
        self.progress = min(1.0, current / target) if target > 0 else 1.0
        if self.progress >= 1.0 and self.unlocked_at is None:
            return True
        return False


@dataclass
class LeaderboardEntry:
    user_id: str
    score: int
    rank: int = 0
    previous_rank: int = 0
    trend: str = "stable"

    def update_rank(self, new_rank: int) -> None:
        self.previous_rank = self.rank or new_rank
        if new_rank < self.previous_rank:
            self.trend = "up"
        elif new_rank > self.previous_rank:
            self.trend = "down"
        else:
            self.trend = "stable"
        self.rank = new_rank


class Leaderboard:
    def __init__(self, name: str, metric: str = "total_points", period: str = "all_time"):
        self.name = name
        self.metric = metric
        self.period = period
        self.entries: dict[str, LeaderboardEntry] = {}

    def submit_score(self, user_id: str, score: int) -> int:
        if user_id not in self.entries:
            self.entries[user_id] = LeaderboardEntry(user_id=user_id, score=score)
        else:
            self.entries[user_id].score = score
        return self._rank()

    def _rank(self) -> int:
        sorted_entries = sorted(self.entries.values(), key=lambda e: -e.score)
        for i, entry in enumerate(sorted_entries, 1):
            entry.update_rank(i)
        return sorted_entries[0].rank if sorted_entries else 0

    def top(self, n: int = 10) -> list[LeaderboardEntry]:
        return sorted(self.entries.values(), key=lambda e: e.rank)[:n]

    def get_rank(self, user_id: str) -> int | None:
        entry = self.entries.get(user_id)
        return entry.rank if entry else None


@dataclass
class Quest:
    quest_id: str
    title: str
    description: str
    objectives: list[dict[str, Any]]
    rewards: dict[str, Any]
    expires_at: str | None = None
    completed: bool = False
    progress: dict[str, int] = field(default_factory=dict)

    def update_objective(self, objective_id: str, value: int) -> bool:
        self.progress[objective_id] = value
        for obj in self.objectives:
            if obj["id"] == objective_id and value >= obj["target"]:
                self._check_completion()
        return self.completed

    def _check_completion(self) -> None:
        self.completed = all(
            self.progress.get(obj["id"], 0) >= obj["target"] for obj in self.objectives
        )

    def claim_rewards(self, profile: PointsProfile) -> dict[str, Any]:
        if not self.completed:
            return {}
        points = self.rewards.get("points", 0)
        if points:
            profile.add_points(points, f"quest:{self.quest_id}")
        return self.rewards


@dataclass
class Challenge:
    challenge_id: str
    title: str
    description: str
    participants: dict[str, int] = field(default_factory=dict)
    rewards: dict[str, Any] = field(default_factory=dict)
    start_time: str = ""
    end_time: str = ""
    status: str = "pending"
    winner: str | None = None

    def join(self, user_id: str) -> bool:
        if self.status != "pending":
            return False
        self.participants[user_id] = 0
        return True

    def submit_score(self, user_id: str, score: int) -> None:
        if user_id in self.participants:
            self.participants[user_id] = max(self.participants[user_id], score)

    def start(self) -> None:
        self.status = "active"

    def finalize(self) -> str | None:
        if not self.participants:
            self.status = "completed"
            return None
        self.winner = max(self.participants, key=lambda u: self.participants[u])
        self.status = "completed"
        return self.winner

    def get_standings(self) -> list[tuple[str, int]]:
        return sorted(self.participants.items(), key=lambda x: -x[1])


class GamificationEngine:
    def __init__(self):
        self.profiles: dict[str, PointsProfile] = {}
        self.badges: dict[str, Badge] = {}
        self.achievements: dict[str, Achievement] = {}
        self.leaderboards: dict[str, Leaderboard] = {}
        self.quests: dict[str, Quest] = {}
        self.challenges: dict[str, Challenge] = {}

    def get_or_create_profile(self, user_id: str) -> PointsProfile:
        if user_id not in self.profiles:
            self.profiles[user_id] = PointsProfile(user_id=user_id)
        return self.profiles[user_id]

    def register_badge(self, badge: Badge) -> None:
        self.badges[badge.badge_id] = badge

    def check_badges(self, user_id: str, stats: dict[str, Any]) -> list[Badge]:
        profile = self.get_or_create_profile(user_id)
        unlocked = []
        for badge in self.badges.values():
            if badge.check_unlock(profile, stats):
                unlocked.append(badge)
        return unlocked

    def create_leaderboard(self, name: str, metric: str = "total_points") -> Leaderboard:
        lb = Leaderboard(name=name, metric=metric)
        self.leaderboards[name] = lb
        return lb

    def create_quest(self, quest: Quest) -> None:
        self.quests[quest.quest_id] = quest

    def create_challenge(self, challenge: Challenge) -> None:
        self.challenges[challenge.challenge_id] = challenge

    def award_points(self, user_id: str, amount: int, reason: str = "") -> PointsProfile:
        profile = self.get_or_create_profile(user_id)
        profile.add_points(amount, reason)
        for lb in self.leaderboards.values():
            lb.submit_score(user_id, profile.total_points)
        return profile
