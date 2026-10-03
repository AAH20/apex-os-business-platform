"""Deepened compliance module: policies, risk, controls, reporting, regulatory change."""
from __future__ import annotations
import hashlib, json, uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum
from typing import Any, Optional
from collections import defaultdict


class PolicyStatus(Enum):
    DRAFT = "draft"; ACTIVE = "active"; ARCHIVED = "archived"; SUPERSEDED = "superseded"

class RiskLevel(Enum):
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

class ControlFrequency(Enum):
    DAILY = "daily"; WEEKLY = "weekly"; MONTHLY = "monthly"; QUARTERLY = "quarterly"; ANNUALLY = "annually"

class TestResult(Enum):
    PASS = "pass"; FAIL = "fail"; PARTIAL = "partial"; NOT_TESTED = "not_tested"

class ChangeStatus(Enum):
    IDENTIFIED = "identified"; ASSESSING = "assessing"; PLANNED = "planned"
    IMPLEMENTING = "implementing"; IMPLEMENTED = "implemented"; VERIFIED = "verified"


def _uid() -> str:
    return str(uuid.uuid4())[:8]

def score_to_level(score: int) -> RiskLevel:
    if score >= 20: return RiskLevel.CRITICAL
    if score >= 12: return RiskLevel.HIGH
    if score >= 6: return RiskLevel.MEDIUM
    return RiskLevel.LOW


# --- Policy Management with Version Control ---
@dataclass
class PolicyVersion:
    version: str; content: str; author: str; created_at: datetime
    change_summary: str; status: PolicyStatus
    approved_by: Optional[str] = None; effective_date: Optional[date] = None
    content_hash: str = ""
    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]

@dataclass
class Policy:
    id: str; title: str; category: str; owner: str
    versions: list[PolicyVersion] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    related_controls: list[str] = field(default_factory=list)

    @property
    def current_version(self) -> Optional[PolicyVersion]:
        active = [v for v in self.versions if v.status == PolicyStatus.ACTIVE]
        return active[-1] if active else (self.versions[-1] if self.versions else None)

    def add_version(self, content: str, author: str, change_summary: str,
                    approved_by: str = None, effective_date: date = None) -> PolicyVersion:
        ver = f"v{len(self.versions) + 1}.0"
        for v in self.versions:
            if v.status == PolicyStatus.ACTIVE: v.status = PolicyStatus.SUPERSEDED
        pv = PolicyVersion(ver, content, author, datetime.utcnow(), change_summary,
                           PolicyStatus.ACTIVE, approved_by, effective_date)
        self.versions.append(pv)
        return pv

    def get_version(self, version: str) -> Optional[PolicyVersion]:
        return next((v for v in self.versions if v.version == version), None)

    def diff_versions(self, v1: str, v2: str) -> dict:
        a, b = self.get_version(v1), self.get_version(v2)
        if not a or not b: return {"error": "version not found"}
        return {"from": v1, "to": v2, "content_changed": a.content_hash != b.content_hash,
                "author_changed": a.author != b.author,
                "days_between": (b.created_at - a.created_at).days}


# --- Risk Assessment with Scoring ---
@dataclass
class RiskAssessment:
    id: str; name: str; description: str; category: str
    likelihood: int; impact: int
    mitigating_controls: list[str] = field(default_factory=list)
    residual_likelihood: int = 0; residual_impact: int = 0
    assessor: str = ""; assessed_at: datetime = field(default_factory=datetime.utcnow)
    review_date: Optional[date] = None; status: str = "open"

    @property
    def inherent_score(self) -> int: return self.likelihood * self.impact
    @property
    def residual_score(self) -> int:
        return (self.residual_likelihood or self.likelihood) * (self.residual_impact or self.impact)
    @property
    def inherent_level(self) -> RiskLevel: return score_to_level(self.inherent_score)
    @property
    def residual_level(self) -> RiskLevel: return score_to_level(self.residual_score)
    @property
    def risk_reduction(self) -> int: return self.inherent_score - self.residual_score


# --- Control Testing with Evidence ---
@dataclass
class Evidence:
    id: str; file_name: str; file_hash: str; uploaded_by: str
    uploaded_at: datetime; description: str = ""; metadata: dict = field(default_factory=dict)

@dataclass
class ControlTest:
    id: str; control_id: str; control_name: str; test_description: str
    frequency: ControlFrequency; tester: str; executed_at: datetime
    result: TestResult; findings: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    remediation: str = ""; next_test_date: Optional[date] = None; status: str = "completed"

    def add_evidence(self, file_name: str, file_hash: str, uploaded_by: str,
                     description: str = "") -> Evidence:
        ev = Evidence(_uid(), file_name, file_hash, uploaded_by, datetime.utcnow(), description)
        self.evidence.append(ev)
        return ev

    @property
    def evidence_count(self) -> int: return len(self.evidence)


# --- Compliance Reporting with Dashboards ---
@dataclass
class ComplianceDashboard:
    name: str; generated_at: datetime = field(default_factory=datetime.utcnow)
    period_start: Optional[date] = None; period_end: Optional[date] = None

    def generate(self, policies: list[Policy], risks: list[RiskAssessment],
                 tests: list[ControlTest]) -> dict[str, Any]:
        ps = self._policy_stats(policies); rs = self._risk_stats(risks); cs = self._control_stats(tests)
        return {"dashboard": self.name, "generated_at": self.generated_at.isoformat(),
                "period": {"start": str(self.period_start), "end": str(self.period_end)},
                "summary": {"total_policies": ps["total"], "active_policies": ps["active"],
                            "total_risks": rs["total"], "open_risks": rs["open"],
                            "critical_risks": rs["critical"], "total_tests": cs["total"],
                            "pass_rate": cs["pass_rate"]},
                "policy_breakdown": ps["by_category"], "risk_heatmap": rs["heatmap"],
                "control_effectiveness": cs["by_control"], "trends": self._trends(risks, tests)}

    def _policy_stats(self, policies: list[Policy]) -> dict:
        by_cat: dict[str, int] = defaultdict(int); active = 0
        for p in policies:
            by_cat[p.category] += 1
            if p.current_version and p.current_version.status == PolicyStatus.ACTIVE: active += 1
        return {"total": len(policies), "active": active, "by_category": dict(by_cat)}

    def _risk_stats(self, risks: list[RiskAssessment]) -> dict:
        hm: dict[str, int] = defaultdict(int); op = 0; crit = 0
        for r in risks:
            hm[r.inherent_level.value] += 1
            if r.status == "open": op += 1
            if r.inherent_level == RiskLevel.CRITICAL: crit += 1
        return {"total": len(risks), "open": op, "critical": crit, "heatmap": dict(hm)}

    def _control_stats(self, tests: list[ControlTest]) -> dict:
        bc: dict[str, dict] = defaultdict(lambda: {"total": 0, "pass": 0}); tp = 0
        for t in tests:
            bc[t.control_id]["total"] += 1
            if t.result == TestResult.PASS: bc[t.control_id]["pass"] += 1; tp += 1
        return {"total": len(tests), "pass_rate": round(tp / len(tests) * 100, 1) if tests else 0.0,
                "by_control": dict(bc)}

    def _trends(self, risks: list[RiskAssessment], tests: list[ControlTest]) -> dict:
        ai = sum(r.inherent_score for r in risks) / len(risks) if risks else 0
        ar = sum(r.residual_score for r in risks) / len(risks) if risks else 0
        return {"avg_inherent_risk": round(ai, 2), "avg_residual_risk": round(ar, 2),
                "risk_reduction_pct": round((1 - ar / ai) * 100, 1) if ai else 0}


# --- Regulatory Change Management ---
@dataclass
class RegulatoryChange:
    id: str; regulation_name: str; jurisdiction: str; issuing_body: str
    description: str; effective_date: date; status: ChangeStatus
    identified_at: datetime = field(default_factory=datetime.utcnow)
    impact_assessment: str = ""; affected_policies: list[str] = field(default_factory=list)
    affected_controls: list[str] = field(default_factory=list)
    action_items: list[dict] = field(default_factory=list)
    owner: str = ""; priority: str = "medium"; notes: str = ""

    def add_action(self, action: str, owner: str, due_date: date) -> dict:
        item = {"action": action, "owner": owner, "due_date": str(due_date),
                "status": "pending", "id": _uid()}
        self.action_items.append(item)
        return item

    def days_until_effective(self) -> int: return (self.effective_date - date.today()).days
    @property
    def is_overdue(self) -> bool:
        return self.days_until_effective() < 0 and self.status != ChangeStatus.VERIFIED
    def transition(self, new_status: ChangeStatus) -> None: self.status = new_status


# --- Module facade ---
class ComplianceEngine:
    def __init__(self):
        self.policies: dict[str, Policy] = {}; self.risks: dict[str, RiskAssessment] = {}
        self.tests: dict[str, ControlTest] = {}; self.changes: dict[str, RegulatoryChange] = {}

    def create_policy(self, title: str, category: str, owner: str,
                      content: str, author: str, tags: list[str] = None) -> Policy:
        p = Policy(_uid(), title, category, owner, tags=tags or [])
        p.add_version(content, author, "Initial version")
        self.policies[p.id] = p; return p

    def create_risk(self, name: str, description: str, category: str,
                    likelihood: int, impact: int, assessor: str,
                    mitigating_controls: list[str] = None) -> RiskAssessment:
        r = RiskAssessment(_uid(), name, description, category,
                           max(1, min(5, likelihood)), max(1, min(5, impact)),
                           mitigating_controls=mitigating_controls or [], assessor=assessor)
        self.risks[r.id] = r; return r

    def create_test(self, control_id: str, control_name: str, test_description: str,
                    frequency: ControlFrequency, tester: str, result: TestResult) -> ControlTest:
        t = ControlTest(_uid(), control_id, control_name, test_description,
                        frequency, tester, datetime.utcnow(), result)
        self.tests[t.id] = t; return t

    def create_regulatory_change(self, regulation_name: str, jurisdiction: str,
                                 issuing_body: str, description: str,
                                 effective_date: date, owner: str,
                                 priority: str = "medium") -> RegulatoryChange:
        rc = RegulatoryChange(_uid(), regulation_name, jurisdiction, issuing_body,
                              description, effective_date, ChangeStatus.IDENTIFIED,
                              owner=owner, priority=priority)
        self.changes[rc.id] = rc; return rc

    def dashboard(self, name: str = "Compliance Overview",
                  period_start: date = None, period_end: date = None) -> dict:
        d = ComplianceDashboard(name, period_start=period_start, period_end=period_end)
        return d.generate(list(self.policies.values()), list(self.risks.values()),
                          list(self.tests.values()))

    def export_json(self) -> str:
        return json.dumps({k: {kk: asdict(vv) for kk, vv in v.items()}
                           for k, v in self.__dict__.items()}, default=str, indent=2)
