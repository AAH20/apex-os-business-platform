"""Performance reviews, goals, and ratings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class Rating(int, Enum):
    """Performance rating scale 1–5."""

    UNSATISFACTORY = 1
    NEEDS_IMPROVEMENT = 2
    MEETS_EXPECTATIONS = 3
    EXCEEDS_EXPECTATIONS = 4
    OUTSTANDING = 5


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    SELF_REVIEW = "self_review"
    MANAGER_REVIEW = "manager_review"
    COMPLETED = "completed"


class GoalStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Goal:
    """A performance goal for an employee."""

    id: str
    employee_id: str
    title: str
    description: str
    target_date: date
    status: GoalStatus = GoalStatus.NOT_STARTED
    progress: int = 0  # 0–100
    created_date: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        if not 0 <= self.progress <= 100:
            raise ValueError("Progress must be between 0 and 100")

    def update_progress(self, value: int) -> None:
        if not 0 <= value <= 100:
            raise ValueError("Progress must be between 0 and 100")
        self.progress = value
        if value == 100:
            self.status = GoalStatus.COMPLETED
        elif value > 0:
            self.status = GoalStatus.IN_PROGRESS

    def complete(self) -> None:
        self.progress = 100
        self.status = GoalStatus.COMPLETED

    def cancel(self) -> None:
        self.status = GoalStatus.CANCELLED


@dataclass
class PerformanceReview:
    """A performance review record."""

    id: str
    employee_id: str
    reviewer_id: str
    review_period_start: date
    review_period_end: date
    status: ReviewStatus = ReviewStatus.DRAFT
    self_rating: Optional[Rating] = None
    manager_rating: Optional[Rating] = None
    self_comments: Optional[str] = None
    manager_comments: Optional[str] = None
    goals: list[Goal] = field(default_factory=list)
    created_date: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        if self.review_period_end < self.review_period_start:
            raise ValueError("Review period end cannot be before start")

    @property
    def overall_rating(self) -> Optional[Rating]:
        """Average of self and manager ratings if both exist."""
        if self.self_rating and self.manager_rating:
            avg = (self.self_rating.value + self.manager_rating.value) / 2
            return Rating(round(avg))
        return self.manager_rating or self.self_rating

    def submit_self_review(self, rating: Rating, comments: str) -> None:
        self.self_rating = rating
        self.self_comments = comments
        self.status = ReviewStatus.SELF_REVIEW

    def submit_manager_review(self, rating: Rating, comments: str) -> None:
        self.manager_rating = rating
        self.manager_comments = comments
        self.status = ReviewStatus.MANAGER_REVIEW

    def complete(self) -> None:
        if not self.self_rating or not self.manager_rating:
            raise ValueError("Both self and manager ratings are required")
        self.status = ReviewStatus.COMPLETED

    def add_goal(self, goal: Goal) -> None:
        self.goals.append(goal)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "reviewer_id": self.reviewer_id,
            "review_period_start": self.review_period_start.isoformat(),
            "review_period_end": self.review_period_end.isoformat(),
            "status": self.status.value,
            "self_rating": self.self_rating.value if self.self_rating else None,
            "manager_rating": self.manager_rating.value if self.manager_rating else None,
            "overall_rating": self.overall_rating.value if self.overall_rating else None,
            "goals": [
                {
                    "id": g.id,
                    "title": g.title,
                    "status": g.status.value,
                    "progress": g.progress,
                }
                for g in self.goals
            ],
        }


@dataclass
class ReviewCycle:
    """A review cycle (e.g. annual 2026)."""

    id: str
    name: str
    start_date: date
    end_date: date
    reviews: list[PerformanceReview] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("Cycle end cannot be before start")

    def add_review(self, review: PerformanceReview) -> None:
        self.reviews.append(review)

    def get_review(self, review_id: str) -> Optional[PerformanceReview]:
        for r in self.reviews:
            if r.id == review_id:
                return r
        return None

    def completion_rate(self) -> float:
        """Percentage of reviews completed."""
        if not self.reviews:
            return 0.0
        completed = sum(1 for r in self.reviews if r.status == ReviewStatus.COMPLETED)
        return round(completed / len(self.reviews) * 100, 1)

    def average_rating(self) -> Optional[float]:
        """Average overall rating across completed reviews."""
        ratings = [
            r.overall_rating.value
            for r in self.reviews
            if r.status == ReviewStatus.COMPLETED and r.overall_rating
        ]
        return round(sum(ratings) / len(ratings), 2) if ratings else None
