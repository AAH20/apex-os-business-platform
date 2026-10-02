"""Risk assessment module."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .models import RiskAssessment, RiskLevel


class RiskAssessor:
    """Manages risk assessments."""

    def __init__(self) -> None:
        self._risks: dict[str, RiskAssessment] = {}

    def create_risk(
        self,
        risk_id: str,
        name: str,
        description: str,
        category: str,
        likelihood: int = 3,
        impact: int = 3,
        mitigations: list[str] | None = None,
        owner: str = "",
        review_date: date | None = None,
    ) -> RiskAssessment:
        """Create a new risk assessment."""
        risk = RiskAssessment(
            id=risk_id,
            name=name,
            description=description,
            category=category,
            likelihood=max(1, min(5, likelihood)),
            impact=max(1, min(5, impact)),
            mitigations=mitigations or [],
            owner=owner,
            review_date=review_date,
        )
        self._risks[risk_id] = risk
        return risk

    def get_risk(self, risk_id: str) -> RiskAssessment | None:
        """Get a risk assessment by ID."""
        return self._risks.get(risk_id)

    def update_risk(self, risk_id: str, **kwargs: Any) -> RiskAssessment | None:
        """Update risk assessment fields."""
        risk = self._risks.get(risk_id)
        if risk is None:
            return None
        for key, value in kwargs.items():
            if hasattr(risk, key) and key != "risk_level":
                setattr(risk, key, value)
        # Recalculate risk level if likelihood or impact changed
        if "likelihood" in kwargs or "impact" in kwargs:
            risk.likelihood = max(1, min(5, risk.likelihood))
            risk.impact = max(1, min(5, risk.impact))
            risk.risk_level = risk._calculate_risk_level()
        risk.updated_at = datetime.utcnow()
        return risk

    def add_mitigation(self, risk_id: str, mitigation: str) -> RiskAssessment | None:
        """Add a mitigation to a risk."""
        risk = self._risks.get(risk_id)
        if risk is None:
            return None
        risk.mitigations.append(mitigation)
        risk.updated_at = datetime.utcnow()
        return risk

    def remove_mitigation(self, risk_id: str, index: int) -> RiskAssessment | None:
        """Remove a mitigation by index."""
        risk = self._risks.get(risk_id)
        if risk is None:
            return None
        if 0 <= index < len(risk.mitigations):
            risk.mitigations.pop(index)
            risk.updated_at = datetime.utcnow()
        return risk

    def update_status(self, risk_id: str, status: str) -> RiskAssessment | None:
        """Update risk status."""
        risk = self._risks.get(risk_id)
        if risk is None:
            return None
        risk.status = status
        risk.updated_at = datetime.utcnow()
        return risk

    def remove_risk(self, risk_id: str) -> bool:
        """Remove a risk assessment."""
        if risk_id in self._risks:
            del self._risks[risk_id]
            return True
        return False

    def list_risks(
        self,
        risk_level: RiskLevel | None = None,
        category: str | None = None,
        status: str | None = None,
        owner: str | None = None,
    ) -> list[RiskAssessment]:
        """List risks with optional filters."""
        risks = list(self._risks.values())
        if risk_level is not None:
            risks = [r for r in risks if r.risk_level == risk_level]
        if category is not None:
            risks = [r for r in risks if r.category == category]
        if status is not None:
            risks = [r for r in risks if r.status == status]
        if owner is not None:
            risks = [r for r in risks if r.owner == owner]
        return risks

    def get_risks_by_level(self) -> dict[str, list[RiskAssessment]]:
        """Group risks by risk level."""
        grouped: dict[str, list[RiskAssessment]] = defaultdict(list)
        for risk in self._risks.values():
            grouped[risk.risk_level.value].append(risk)
        return dict(grouped)

    def get_risks_by_category(self) -> dict[str, list[RiskAssessment]]:
        """Group risks by category."""
        grouped: dict[str, list[RiskAssessment]] = defaultdict(list)
        for risk in self._risks.values():
            grouped[risk.category].append(risk)
        return dict(grouped)

    def get_open_risks(self) -> list[RiskAssessment]:
        """Get all open risks."""
        return [r for r in self._risks.values() if r.status == "open"]

    def get_critical_risks(self) -> list[RiskAssessment]:
        """Get all critical risks."""
        return [
            r for r in self._risks.values()
            if r.risk_level == RiskLevel.CRITICAL and r.status == "open"
        ]

    def get_overdue_reviews(self) -> list[RiskAssessment]:
        """Get risks with overdue reviews."""
        today = date.today()
        return [
            r for r in self._risks.values()
            if r.review_date is not None
            and r.review_date < today
            and r.status == "open"
        ]

    def get_risk_matrix(self) -> dict[str, dict[str, int]]:
        """Get a risk matrix (likelihood x impact) with counts."""
        matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for risk in self._risks.values():
            matrix[str(risk.likelihood)][str(risk.impact)] += 1
        return {k: dict(v) for k, v in matrix.items()}

    def get_average_risk_score(self) -> float:
        """Get the average risk score across all risks."""
        if not self._risks:
            return 0.0
        return sum(r.risk_score for r in self._risks.values()) / len(self._risks)

    def to_dict(self) -> dict[str, Any]:
        """Export all risks as a dictionary."""
        return {
            "risks": {k: v.to_dict() for k, v in self._risks.items()},
            "by_level": {k: len(v) for k, v in self.get_risks_by_level().items()},
            "average_score": self.get_average_risk_score(),
        }

    def __len__(self) -> int:
        return len(self._risks)
