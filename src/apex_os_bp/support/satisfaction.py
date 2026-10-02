"""Customer satisfaction (CSAT) measurement module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class CSATRating(int, Enum):
    """Standard CSAT rating scale (1-5)."""

    VERY_DISSATISFIED = 1
    DISSATISFIED = 2
    NEUTRAL = 3
    SATISFIED = 4
    VERY_SATISFIED = 5


@dataclass
class CSATSurvey:
    """Represents a customer satisfaction survey response."""

    ticket_id: str
    customer_id: str
    rating: CSATRating
    comment: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: Optional[str] = None
    category: str = "general"
    follow_up_required: bool = False
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize survey to dictionary."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "customer_id": self.customer_id,
            "rating": self.rating.value,
            "comment": self.comment,
            "submitted_at": self.submitted_at.isoformat(),
            "agent_id": self.agent_id,
            "category": self.category,
            "follow_up_required": self.follow_up_required,
            "tags": self.tags,
        }


class SatisfactionManager:
    """Manages CSAT surveys and satisfaction reporting."""

    def __init__(self) -> None:
        self._surveys: dict[str, CSATSurvey] = {}

    def submit_survey(
        self,
        ticket_id: str,
        customer_id: str,
        rating: CSATRating,
        *,
        comment: str = "",
        agent_id: Optional[str] = None,
        category: str = "general",
        tags: Optional[list[str]] = None,
    ) -> CSATSurvey:
        """Submit a new CSAT survey response."""
        follow_up = rating in (CSATRating.VERY_DISSATISFIED, CSATRating.DISSATISFIED)
        survey = CSATSurvey(
            ticket_id=ticket_id,
            customer_id=customer_id,
            rating=rating,
            comment=comment,
            agent_id=agent_id,
            category=category,
            follow_up_required=follow_up,
            tags=tags or [],
        )
        self._surveys[survey.id] = survey
        return survey

    def get_survey(self, survey_id: str) -> Optional[CSATSurvey]:
        """Retrieve a survey by ID."""
        return self._surveys.get(survey_id)

    def get_surveys_for_ticket(self, ticket_id: str) -> list[CSATSurvey]:
        """Return all surveys for a specific ticket."""
        return [s for s in self._surveys.values() if s.ticket_id == ticket_id]

    def get_surveys_for_customer(self, customer_id: str) -> list[CSATSurvey]:
        """Return all surveys for a specific customer."""
        return [s for s in self._surveys.values() if s.customer_id == customer_id]

    def get_surveys_for_agent(self, agent_id: str) -> list[CSATSurvey]:
        """Return all surveys for a specific agent."""
        return [s for s in self._surveys.values() if s.agent_id == agent_id]

    def get_average_rating(self) -> float:
        """Return the average CSAT rating across all surveys."""
        if not self._surveys:
            return 0.0
        total = sum(s.rating.value for s in self._surveys.values())
        return total / len(self._surveys)

    def get_rating_distribution(self) -> dict[int, int]:
        """Return distribution of ratings (1-5)."""
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for survey in self._surveys.values():
            dist[survey.rating.value] += 1
        return dist

    def get_nps_score(self) -> float:
        """Calculate NPS-style score from CSAT ratings.

        Promoters (4-5) minus Detractors (1-2) as percentage.
        """
        if not self._surveys:
            return 0.0
        promoters = len(
            [
                s
                for s in self._surveys.values()
                if s.rating in (CSATRating.SATISFIED, CSATRating.VERY_SATISFIED)
            ]
        )
        detractors = len(
            [
                s
                for s in self._surveys.values()
                if s.rating
                in (CSATRating.VERY_DISSATISFIED, CSATRating.DISSATISFIED)
            ]
        )
        total = len(self._surveys)
        return ((promoters - detractors) / total) * 100.0

    def get_follow_up_required(self) -> list[CSATSurvey]:
        """Return surveys that require follow-up."""
        return [s for s in self._surveys.values() if s.follow_up_required]

    def get_survey_count(self) -> int:
        """Return total number of surveys."""
        return len(self._surveys)

    def get_category_ratings(self) -> dict[str, float]:
        """Return average rating per category."""
        category_totals: dict[str, list[int]] = {}
        for survey in self._surveys.values():
            if survey.category not in category_totals:
                category_totals[survey.category] = []
            category_totals[survey.category].append(survey.rating.value)
        return {
            cat: sum(ratings) / len(ratings)
            for cat, ratings in category_totals.items()
        }

    def get_agent_ratings(self) -> dict[str, float]:
        """Return average rating per agent."""
        agent_totals: dict[str, list[int]] = {}
        for survey in self._surveys.values():
            if survey.agent_id is None:
                continue
            if survey.agent_id not in agent_totals:
                agent_totals[survey.agent_id] = []
            agent_totals[survey.agent_id].append(survey.rating.value)
        return {
            agent: sum(ratings) / len(ratings)
            for agent, ratings in agent_totals.items()
        }

    def get_recent_surveys(self, limit: int = 10) -> list[CSATSurvey]:
        """Return most recent surveys."""
        sorted_surveys = sorted(
            self._surveys.values(), key=lambda s: s.submitted_at, reverse=True
        )
        return sorted_surveys[:limit]

    def get_low_rated_surveys(
        self, threshold: CSATRating = CSATRating.DISSATISFIED
    ) -> list[CSATSurvey]:
        """Return surveys at or below a rating threshold."""
        return [
            s for s in self._surveys.values() if s.rating <= threshold
        ]

    def generate_report(self) -> dict:
        """Generate a comprehensive satisfaction report."""
        return {
            "total_surveys": self.get_survey_count(),
            "average_rating": self.get_average_rating(),
            "nps_score": self.get_nps_score(),
            "rating_distribution": self.get_rating_distribution(),
            "follow_up_required": len(self.get_follow_up_required()),
            "category_ratings": self.get_category_ratings(),
            "agent_ratings": self.get_agent_ratings(),
        }
