"""Data models for the compliance management system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class ComplianceStatus(str, Enum):
    """Status of a compliance item."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    PENDING = "pending"
    NOT_ASSESSED = "not_assessed"
    EXEMPTED = "exempted"


class RiskLevel(str, Enum):
    """Risk severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class AuditStatus(str, Enum):
    """Status of an audit."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FindingSeverity(str, Enum):
    """Severity of an audit finding."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"


@dataclass
class ComplianceItem:
    """A single compliance requirement or control."""

    id: str
    name: str
    description: str
    regulation: str
    category: str
    status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    owner: str = ""
    evidence: list[str] = field(default_factory=list)
    notes: str = ""
    due_date: date | None = None
    last_assessed: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "regulation": self.regulation,
            "category": self.category,
            "status": self.status.value,
            "owner": self.owner,
            "evidence": list(self.evidence),
            "notes": self.notes,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "last_assessed": self.last_assessed.isoformat() if self.last_assessed else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": dict(self.metadata),
        }


@dataclass
class Policy:
    """A compliance policy document."""

    id: str
    title: str
    version: str
    content: str
    category: str
    author: str = ""
    approver: str = ""
    effective_date: date | None = None
    review_date: date | None = None
    status: str = "draft"  # draft, active, deprecated, archived
    tags: list[str] = field(default_factory=list)
    related_regulations: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "version": self.version,
            "content": self.content,
            "category": self.category,
            "author": self.author,
            "approver": self.approver,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "status": self.status,
            "tags": list(self.tags),
            "related_regulations": list(self.related_regulations),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class RiskAssessment:
    """A risk assessment entry."""

    id: str
    name: str
    description: str
    category: str
    likelihood: int = 3  # 1-5 scale
    impact: int = 3  # 1-5 scale
    risk_level: RiskLevel = RiskLevel.LOW
    mitigations: list[str] = field(default_factory=list)
    owner: str = ""
    status: str = "open"  # open, mitigated, accepted, transferred, closed
    review_date: date | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self.risk_level = self._calculate_risk_level()

    def _calculate_risk_level(self) -> RiskLevel:
        score = self.likelihood * self.impact
        if score >= 20:
            return RiskLevel.CRITICAL
        if score >= 10:
            return RiskLevel.HIGH
        if score >= 6:
            return RiskLevel.MEDIUM
        if score >= 2:
            return RiskLevel.LOW
        return RiskLevel.NEGLIGIBLE

    @property
    def risk_score(self) -> int:
        return self.likelihood * self.impact

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "likelihood": self.likelihood,
            "impact": self.impact,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "mitigations": list(self.mitigations),
            "owner": self.owner,
            "status": self.status,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class AuditFinding:
    """A finding from an audit."""

    id: str
    title: str
    description: str
    severity: FindingSeverity
    recommendation: str = ""
    owner: str = ""
    due_date: date | None = None
    status: str = "open"  # open, in_progress, resolved, closed, accepted
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "recommendation": self.recommendation,
            "owner": self.owner,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class Audit:
    """An audit engagement."""

    id: str
    name: str
    audit_type: str
    scope: str
    status: AuditStatus = AuditStatus.PLANNED
    lead_auditor: str = ""
    start_date: date | None = None
    end_date: date | None = None
    findings: list[AuditFinding] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def open_finding_count(self) -> int:
        return sum(1 for f in self.findings if f.status in ("open", "in_progress"))

    @property
    def critical_finding_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.severity == FindingSeverity.CRITICAL and f.status in ("open", "in_progress")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "audit_type": self.audit_type,
            "scope": self.scope,
            "status": self.status.value,
            "lead_auditor": self.lead_auditor,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "findings": [f.to_dict() for f in self.findings],
            "notes": self.notes,
            "finding_count": self.finding_count,
            "open_finding_count": self.open_finding_count,
            "critical_finding_count": self.critical_finding_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class RegulatoryReport:
    """A regulatory report submission."""

    id: str
    name: str
    regulation: str
    reporting_period: str
    submission_date: date | None = None
    due_date: date | None = None
    status: str = "draft"  # draft, in_review, submitted, accepted, rejected
    submitted_by: str = ""
    reference_number: str = ""
    notes: str = ""
    attachments: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_overdue(self) -> bool:
        if self.due_date and self.status not in ("submitted", "accepted"):
            return date.today() > self.due_date
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "regulation": self.regulation,
            "reporting_period": self.reporting_period,
            "submission_date": self.submission_date.isoformat() if self.submission_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "submitted_by": self.submitted_by,
            "reference_number": self.reference_number,
            "notes": self.notes,
            "attachments": list(self.attachments),
            "is_overdue": self.is_overdue,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
