"""Lead scoring engine for CRM.

Scores leads based on engagement, demographic fit, and behavioral signals.
Produces a 0-100 score with a category (hot, warm, cold) and factor breakdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LeadCategory(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


@dataclass
class LeadScore:
    """Result of scoring a lead."""

    lead_id: str
    total_score: float
    category: LeadCategory
    factors: dict[str, float] = field(default_factory=dict)
    max_possible: float = 100.0

    @property
    def percentage(self) -> float:
        """Score as a percentage of max possible."""
        if self.max_possible <= 0:
            return 0.0
        return round((self.total_score / self.max_possible) * 100, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "total_score": self.total_score,
            "category": self.category.value,
            "factors": self.factors,
            "max_possible": self.max_possible,
            "percentage": self.percentage,
        }


@dataclass
class ScoringRule:
    """A single scoring rule with weight and evaluator."""

    name: str
    weight: float
    evaluator: Any  # Callable[[dict], float]
    description: str = ""


class LeadScoringEngine:
    """Configurable lead scoring engine.

    Default rules cover: email engagement, website visits, job title
    seniority, company size, and recency of activity.
    """

    # Seniority keywords mapped to scores
    SENIORITY_MAP: dict[str, float] = {
        "c-level": 25,
        "ceo": 25, "cto": 25, "cfo": 25, "coo": 25, "cmo": 25,
        "vp": 20, "vice president": 20,
        "director": 15,
        "manager": 10,
        "senior": 8,
        "lead": 8,
        "junior": 3,
        "intern": 1,
    }

    # Company size tiers (employees) mapped to scores
    COMPANY_SIZE_TIERS: list[tuple[int, float]] = [
        (10_000, 20),
        (5_000, 18),
        (1_000, 15),
        (500, 12),
        (200, 10),
        (50, 6),
        (10, 3),
        (0, 1),
    ]

    def __init__(self, rules: list[ScoringRule] | None = None):
        self.rules = rules or self._default_rules()

    def _default_rules(self) -> list[ScoringRule]:
        return [
            ScoringRule("email_engagement", 25, self._score_email_engagement,
                        "Opens and clicks on emails"),
            ScoringRule("website_visits", 20, self._score_website_visits,
                        "Number of website visits"),
            ScoringRule("job_seniority", 20, self._score_job_seniority,
                        "Seniority of job title"),
            ScoringRule("company_size", 15, self._score_company_size,
                        "Company employee count"),
            ScoringRule("recency", 15, self._score_recency,
                        "Days since last activity"),
            ScoringRule("form_submissions", 5, self._score_form_submissions,
                        "Number of form submissions"),
        ]

    # ── Evaluators ──────────────────────────────────────────────

    @staticmethod
    def _score_email_engagement(lead: dict) -> float:
        opens = lead.get("email_opens", 0)
        clicks = lead.get("email_clicks", 0)
        # Each open = 1 pt, each click = 3 pts, cap at 25
        return min(25.0, opens * 1.0 + clicks * 3.0)

    @staticmethod
    def _score_website_visits(lead: dict) -> float:
        visits = lead.get("website_visits", 0)
        # 2 pts per visit, cap at 20
        return min(20.0, visits * 2.0)

    @classmethod
    def _score_job_seniority(cls, lead: dict) -> float:
        title = lead.get("job_title", "").lower()
        for keyword, score in cls.SENIORITY_MAP.items():
            if keyword in title:
                return score
        return 0.0

    @classmethod
    def _score_company_size(self, lead: dict) -> float:
        size = lead.get("company_size", 0)
        if size == 0:
            return 0
        for threshold, score in self.COMPANY_SIZE_TIERS:
            if size >= threshold:
                return score
        return 0

    @staticmethod
    def _score_recency(lead: dict) -> float:
        days = lead.get("days_since_last_activity", 999)
        if days <= 1:
            return 15.0
        if days <= 7:
            return 12.0
        if days <= 14:
            return 8.0
        if days <= 30:
            return 4.0
        if days <= 60:
            return 1.0
        return 0.0

    @staticmethod
    def _score_form_submissions(lead: dict) -> float:
        subs = lead.get("form_submissions", 0)
        return min(5.0, subs * 2.5)

    # ── Public API ──────────────────────────────────────────────

    def score(self, lead: dict) -> LeadScore:
        """Score a single lead dict.

        Expected keys (all optional, defaults to 0):
            lead_id, email_opens, email_clicks, website_visits,
            job_title, company_size, days_since_last_activity,
            form_submissions
        """
        lead_id = lead.get("lead_id", "unknown")
        factors: dict[str, float] = {}
        total = 0.0
        max_possible = 0.0

        for rule in self.rules:
            raw = rule.evaluator(lead)
            weighted = raw  # raw is already scaled to rule weight
            factors[rule.name] = round(weighted, 2)
            total += weighted
            max_possible += rule.weight

        total = round(min(total, max_possible), 2)

        if total >= 70:
            category = LeadCategory.HOT
        elif total >= 40:
            category = LeadCategory.WARM
        else:
            category = LeadCategory.COLD

        return LeadScore(
            lead_id=lead_id,
            total_score=total,
            category=category,
            factors=factors,
            max_possible=max_possible,
        )

    def score_many(self, leads: list[dict]) -> list[LeadScore]:
        """Score multiple leads, returned sorted by score descending."""
        scores = [self.score(lead) for lead in leads]
        return sorted(scores, key=lambda s: s.total_score, reverse=True)

    def add_rule(self, rule: ScoringRule) -> None:
        """Add a custom scoring rule."""
        self.rules.append(rule)

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name. Returns True if found and removed."""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                self.rules.pop(i)
                return True
        return False
