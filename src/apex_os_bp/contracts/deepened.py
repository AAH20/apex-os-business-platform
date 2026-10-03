"""Deepened contracts module: lifecycle, templates, negotiation, compliance, analytics."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any


# ── 1. Contract Lifecycle with Renewal ──────────────────────────────────────

class LifecycleState(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    RENEWED = "renewed"


@dataclass
class RenewalTerms:
    auto_renew: bool = False
    notice_days: int = 30
    renewal_period_months: int = 12
    max_renewals: int = 0  # 0 = unlimited
    renewal_count: int = 0


@dataclass
class ContractLifecycle:
    state: LifecycleState = LifecycleState.DRAFT
    effective_date: date | None = None
    expiry_date: date | None = None
    renewal_terms: RenewalTerms = field(default_factory=RenewalTerms)
    history: list[dict[str, Any]] = field(default_factory=list)

    def activate(self, effective: date, expiry: date) -> None:
        self.state = LifecycleState.ACTIVE
        self.effective_date = effective
        self.expiry_date = expiry
        self._log("activated", {"effective": str(effective), "expiry": str(expiry)})

    def check_expiry(self, today: date | None = None) -> LifecycleState:
        today = today or date.today()
        if self.state != LifecycleState.ACTIVE or not self.expiry_date:
            return self.state
        notice = self.renewal_terms.notice_days
        if today >= self.expiry_date:
            self.state = LifecycleState.EXPIRED
            self._log("expired", {})
        elif today >= self.expiry_date - timedelta(days=notice):
            self.state = LifecycleState.EXPIRING
            self._log("expiring_soon", {"days_left": (self.expiry_date - today).days})
        return self.state

    def renew(self, new_expiry: date | None = None) -> bool:
        if not self.renewal_terms.auto_renew:
            return False
        if (self.renewal_terms.max_renewals > 0
                and self.renewal_terms.renewal_count >= self.renewal_terms.max_renewals):
            return False
        self.renewal_terms.renewal_count += 1
        months = self.renewal_terms.renewal_period_months
        self.expiry_date = new_expiry or (self.expiry_date + timedelta(days=30 * months))
        self.state = LifecycleState.RENEWED
        self._log("renewed", {"new_expiry": str(self.expiry_date)})
        return True

    def terminate(self, reason: str = "") -> None:
        self.state = LifecycleState.TERMINATED
        self._log("terminated", {"reason": reason})

    def _log(self, event: str, data: dict[str, Any]) -> None:
        self.history.append({"event": event, "data": data})


# ── 2. Contract Templates with Clauses ──────────────────────────────────────

class ClauseType(str, Enum):
    PAYMENT = "payment"
    TERMINATION = "termination"
    LIABILITY = "liability"
    CONFIDENTIALITY = "confidentiality"
    INDEMNITY = "indemnity"
    SLA = "sla"
    CUSTOM = "custom"


@dataclass
class Clause:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    clause_type: ClauseType = ClauseType.CUSTOM
    text: str = ""
    required: bool = True
    negotiable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractTemplate:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    clauses: list[Clause] = field(default_factory=list)
    version: int = 1

    def add_clause(self, clause: Clause) -> None:
        self.clauses.append(clause)

    def remove_clause(self, clause_id: str) -> bool:
        before = len(self.clauses)
        self.clauses = [c for c in self.clauses if c.id != clause_id]
        return len(self.clauses) < before

    def instantiate(self) -> list[Clause]:
        return [Clause(name=c.name, clause_type=c.clause_type, text=c.text,
                       required=c.required, negotiable=c.negotiable)
                for c in self.clauses]


# ── 3. Contract Negotiation with Redlining ──────────────────────────────────

class ChangeType(str, Enum):
    INSERTION = "insertion"
    DELETION = "deletion"
    MODIFICATION = "modification"


@dataclass
class RedlineChange:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    clause_id: str = ""
    change_type: ChangeType = ChangeType.MODIFICATION
    original_text: str = ""
    proposed_text: str = ""
    author: str = ""
    status: str = "pending"  # pending, accepted, rejected
    comment: str = ""


@dataclass
class NegotiationSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    contract_id: str = ""
    base_text: str = ""
    changes: list[RedlineChange] = field(default_factory=list)
    round_number: int = 1

    def propose(self, change: RedlineChange) -> None:
        self.changes.append(change)

    def accept(self, change_id: str) -> bool:
        for c in self.changes:
            if c.id == change_id:
                c.status = "accepted"
                return True
        return False

    def reject(self, change_id: str) -> bool:
        for c in self.changes:
            if c.id == change_id:
                c.status = "rejected"
                return True
        return False

    def apply_accepted(self) -> str:
        result = self.base_text
        for c in self.changes:
            if c.status == "accepted":
                if c.change_type == ChangeType.MODIFICATION:
                    result = result.replace(c.original_text, c.proposed_text)
                elif c.change_type == ChangeType.DELETION:
                    result = result.replace(c.original_text, "")
                elif c.change_type == ChangeType.INSERTION:
                    result += "\n" + c.proposed_text
        return result

    def pending_count(self) -> int:
        return sum(1 for c in self.changes if c.status == "pending")


# ── 4. Contract Compliance with Obligations ────────────────────────────────

class ObligationStatus(str, Enum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    OVERDUE = "overdue"
    WAIVED = "waived"
    BREACHED = "breached"


@dataclass
class Obligation:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    due_date: date | None = None
    status: ObligationStatus = ObligationStatus.PENDING
    owner: str = ""
    evidence: str = ""
    recurring: bool = False
    recurrence_interval_days: int = 0

    def mark_fulfilled(self, evidence: str = "") -> None:
        self.status = ObligationStatus.FULFILLED
        self.evidence = evidence

    def check_overdue(self, today: date | None = None) -> ObligationStatus:
        today = today or date.today()
        if self.status == ObligationStatus.PENDING and self.due_date and today > self.due_date:
            self.status = ObligationStatus.OVERDUE
        return self.status


@dataclass
class ComplianceTracker:
    contract_id: str = ""
    obligations: list[Obligation] = field(default_factory=list)

    def add_obligation(self, obl: Obligation) -> None:
        self.obligations.append(obl)

    def compliance_rate(self) -> float:
        if not self.obligations:
            return 1.0
        fulfilled = sum(1 for o in self.obligations if o.status == ObligationStatus.FULFILLED)
        return fulfilled / len(self.obligations)

    def overdue_items(self) -> list[Obligation]:
        return [o for o in self.obligations if o.status == ObligationStatus.OVERDUE]

    def check_all(self, today: date | None = None) -> None:
        for o in self.obligations:
            o.check_overdue(today)


# ── 5. Contract Analytics with Risk Scoring ────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskFactor:
    name: str = ""
    weight: float = 1.0
    score: float = 0.0  # 0-100


@dataclass
class ContractAnalytics:
    contract_id: str = ""
    risk_factors: list[RiskFactor] = field(default_factory=list)
    total_value: float = 0.0
    compliance_tracker: ComplianceTracker | None = None
    lifecycle: ContractLifecycle | None = None

    def add_factor(self, factor: RiskFactor) -> None:
        self.risk_factors.append(factor)

    def compute_risk_score(self) -> float:
        if not self.risk_factors:
            return 0.0
        total_weight = sum(f.weight for f in self.risk_factors)
        if total_weight == 0:
            return 0.0
        weighted = sum(f.score * f.weight for f in self.risk_factors)
        return round(weighted / total_weight, 2)

    def risk_level(self) -> RiskLevel:
        score = self.compute_risk_score()
        if score >= 80:
            return RiskLevel.CRITICAL
        if score >= 60:
            return RiskLevel.HIGH
        if score >= 30:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def summary(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "risk_score": self.compute_risk_score(),
            "risk_level": self.risk_level().value,
            "total_value": self.total_value,
            "compliance_rate": self.compliance_tracker.compliance_rate() if self.compliance_tracker else None,
            "lifecycle_state": self.lifecycle.state.value if self.lifecycle else None,
            "factors": [{"name": f.name, "score": f.score, "weight": f.weight} for f in self.risk_factors],
        }
