"""Contract compliance feature."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Optional

from .models import Contract, ContractStatus, ContractType


class ComplianceSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    EXEMPT = "exempt"


@dataclass
class ComplianceRule:
    """A compliance rule that can be checked against contracts."""
    name: str
    description: str
    severity: ComplianceSeverity
    check_function: Callable[[Contract], bool] = field(repr=False)
    applicable_types: list[ContractType] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def evaluate(self, contract: Contract) -> bool:
        """Evaluate the rule against a contract. Returns True if compliant."""
        if self.applicable_types and contract.contract_type not in self.applicable_types:
            return True  # Rule doesn't apply
        return self.check_function(contract)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "applicable_types": [t.value for t in self.applicable_types],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ComplianceCheckResult:
    """The result of a compliance check."""
    rule_id: str
    rule_name: str
    severity: ComplianceSeverity
    passed: bool
    message: str
    checked_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "passed": self.passed,
            "message": self.message,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class ComplianceReport:
    """A compliance report for a contract."""
    contract_id: str
    contract_title: str
    results: list[ComplianceCheckResult] = field(default_factory=list)
    overall_status: ComplianceStatus = ComplianceStatus.COMPLIANT
    generated_at: datetime = field(default_factory=datetime.utcnow)
    generated_by: str = ""
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def compliance_score(self) -> float:
        if not self.results:
            return 100.0
        return (self.passed_count / len(self.results)) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "contract_title": self.contract_title,
            "results": [r.to_dict() for r in self.results],
            "overall_status": self.overall_status.value,
            "generated_at": self.generated_at.isoformat(),
            "generated_by": self.generated_by,
            "notes": self.notes,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "compliance_score": self.compliance_score,
        }


class ComplianceChecker:
    """Checks contracts against compliance rules."""

    def __init__(self) -> None:
        self._rules: dict[str, ComplianceRule] = {}
        self._reports: dict[str, ComplianceReport] = {}

    def add_rule(self, rule: ComplianceRule) -> ComplianceRule:
        """Add a compliance rule."""
        self._rules[rule.id] = rule
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a compliance rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[ComplianceRule]:
        """Retrieve a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(
        self,
        active_only: bool = True,
        severity: Optional[ComplianceSeverity] = None,
        contract_type: Optional[ContractType] = None,
    ) -> list[ComplianceRule]:
        """List compliance rules with optional filters."""
        rules = list(self._rules.values())
        if active_only:
            rules = [r for r in rules if r.is_active]
        if severity:
            rules = [r for r in rules if r.severity == severity]
        if contract_type:
            rules = [r for r in rules if not r.applicable_types or contract_type in r.applicable_types]
        return rules

    def check_contract(
        self,
        contract: Contract,
        rule_ids: Optional[list[str]] = None,
        generated_by: str = "",
    ) -> ComplianceReport:
        """Run compliance checks against a contract."""
        rules_to_check: list[ComplianceRule]
        if rule_ids:
            rules_to_check = [self._rules[rid] for rid in rule_ids if rid in self._rules]
        else:
            rules_to_check = [r for r in self._rules.values() if r.is_active]

        results: list[ComplianceCheckResult] = []
        for rule in rules_to_check:
            passed = rule.evaluate(contract)
            message = (
                f"Contract passes rule: {rule.name}"
                if passed
                else f"Contract violates rule: {rule.name} - {rule.description}"
            )
            result = ComplianceCheckResult(
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                passed=passed,
                message=message,
            )
            results.append(result)

        # Determine overall status
        has_critical = any(not r.passed and r.severity == ComplianceSeverity.CRITICAL for r in results)
        has_violation = any(not r.passed and r.severity == ComplianceSeverity.VIOLATION for r in results)
        has_warning = any(not r.passed and r.severity == ComplianceSeverity.WARNING for r in results)

        if has_critical:
            overall = ComplianceStatus.NON_COMPLIANT
        elif has_violation:
            overall = ComplianceStatus.NON_COMPLIANT
        elif has_warning:
            overall = ComplianceStatus.PENDING_REVIEW
        else:
            overall = ComplianceStatus.COMPLIANT

        report = ComplianceReport(
            contract_id=contract.id,
            contract_title=contract.title,
            results=results,
            overall_status=overall,
            generated_by=generated_by,
        )
        self._reports[report.id] = report

        # Store check results on the contract
        contract.compliance_checks.append({
            "report_id": report.id,
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall.value,
            "score": report.compliance_score,
        })

        return report

    def get_report(self, report_id: str) -> Optional[ComplianceReport]:
        """Retrieve a compliance report by ID."""
        return self._reports.get(report_id)

    def list_reports(
        self,
        contract_id: Optional[str] = None,
        status: Optional[ComplianceStatus] = None,
    ) -> list[ComplianceReport]:
        """List compliance reports with optional filters."""
        reports = list(self._reports.values())
        if contract_id:
            reports = [r for r in reports if r.contract_id == contract_id]
        if status:
            reports = [r for r in reports if r.overall_status == status]
        return reports

    def get_contract_compliance_history(self, contract_id: str) -> list[ComplianceReport]:
        """Get all compliance reports for a contract."""
        return [r for r in self._reports.values() if r.contract_id == contract_id]

    def create_builtin_rules(self) -> list[ComplianceRule]:
        """Create a set of built-in compliance rules."""
        rules: list[ComplianceRule] = []

        # Rule: Contract must have at least two parties
        rules.append(ComplianceRule(
            name="minimum_parties",
            description="Contract must have at least two parties.",
            severity=ComplianceSeverity.VIOLATION,
            check_function=lambda c: len(c.parties) >= 2,
        ))

        # Rule: Contract must have a positive value
        rules.append(ComplianceRule(
            name="positive_value",
            description="Contract value must be positive.",
            severity=ComplianceSeverity.WARNING,
            check_function=lambda c: c.value > 0,
        ))

        # Rule: Contract must have terms defined
        rules.append(ComplianceRule(
            name="terms_defined",
            description="Contract must have at least one term defined.",
            severity=ComplianceSeverity.WARNING,
            check_function=lambda c: len(c.terms) > 0,
        ))

        # Rule: Contract must have a description
        rules.append(ComplianceRule(
            name="description_present",
            description="Contract must have a description.",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: len(c.description) > 0,
        ))

        # Rule: Contract end date must be in the future
        rules.append(ComplianceRule(
            name="end_date_future",
            description="Contract end date must be in the future.",
            severity=ComplianceSeverity.CRITICAL,
            check_function=lambda c: c.end_date > date.today(),
        ))

        # Rule: Contract must have contact email for all parties
        rules.append(ComplianceRule(
            name="party_contact_email",
            description="All parties must have a contact email.",
            severity=ComplianceSeverity.WARNING,
            check_function=lambda c: all(p.contact_email for p in c.parties),
        ))

        # Rule: NDA contracts must have a confidentiality clause
        rules.append(ComplianceRule(
            name="nda_confidentiality_clause",
            description="NDA contracts must include a confidentiality clause.",
            severity=ComplianceSeverity.VIOLATION,
            check_function=lambda c: "confidentiality" in c.clauses or "non-disclosure" in c.clauses,
            applicable_types=[ContractType.NDA],
        ))

        # Rule: Employment contracts must have a termination clause
        rules.append(ComplianceRule(
            name="employment_termination_clause",
            description="Employment contracts must include a termination clause.",
            severity=ComplianceSeverity.VIOLATION,
            check_function=lambda c: "termination" in c.clauses,
            applicable_types=[ContractType.EMPLOYMENT],
        ))

        # Rule: High-value contracts must be approved
        rules.append(ComplianceRule(
            name="high_value_approval",
            description="Contracts valued over 100,000 must be approved.",
            severity=ComplianceSeverity.CRITICAL,
            check_function=lambda c: c.value <= 100000 or c.status in (
                ContractStatus.APPROVED, ContractStatus.ACTIVE, ContractStatus.RENEWED
            ),
        ))

        # Rule: Contract duration should not exceed 5 years
        rules.append(ComplianceRule(
            name="max_duration",
            description="Contract duration should not exceed 5 years (1825 days).",
            severity=ComplianceSeverity.WARNING,
            check_function=lambda c: c.duration_days <= 1825,
        ))

        # Rule: Active contracts must have tags
        rules.append(ComplianceRule(
            name="active_contract_tags",
            description="Active contracts must have at least one tag.",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: c.status != ContractStatus.ACTIVE or len(c.tags) > 0,
        ))

        for rule in rules:
            self.add_rule(rule)

        return rules

    def get_compliance_summary(
        self,
        contracts: list[Contract],
    ) -> dict[str, Any]:
        """Get a compliance summary across multiple contracts."""
        total = len(contracts)
        if total == 0:
            return {
                "total_contracts": 0,
                "compliant": 0,
                "non_compliant": 0,
                "pending_review": 0,
                "average_score": 0.0,
            }

        compliant = 0
        non_compliant = 0
        pending_review = 0
        total_score = 0.0

        for contract in contracts:
            report = self.check_contract(contract)
            if report.overall_status == ComplianceStatus.COMPLIANT:
                compliant += 1
            elif report.overall_status == ComplianceStatus.NON_COMPLIANT:
                non_compliant += 1
            elif report.overall_status == ComplianceStatus.PENDING_REVIEW:
                pending_review += 1
            total_score += report.compliance_score

        return {
            "total_contracts": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "pending_review": pending_review,
            "average_score": round(total_score / total, 2),
        }
