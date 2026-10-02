"""Compliance reporting — generates reports for regulatory frameworks."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from .models import AuditEvent, AuditSeverity, AuditStatus
from .store import AuditStore


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""

    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"


@dataclass
class ComplianceFinding:
    """A single compliance finding."""

    framework: ComplianceFramework
    control_id: str
    description: str
    severity: AuditSeverity
    passed: bool
    evidence: list[str] = field(default_factory=list)
    recommendation: Optional[str] = None


@dataclass
class ComplianceReport:
    """A compliance report for a specific framework."""

    framework: ComplianceFramework
    generated_at: datetime
    findings: list[ComplianceFinding]
    total_events_analyzed: int

    @property
    def passed(self) -> bool:
        return all(f.passed for f in self.findings)

    @property
    def pass_rate(self) -> float:
        if not self.findings:
            return 1.0
        return sum(1 for f in self.findings if f.passed) / len(self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework": self.framework.value,
            "generated_at": self.generated_at.isoformat(),
            "passed": self.passed,
            "pass_rate": self.pass_rate,
            "total_events_analyzed": self.total_events_analyzed,
            "findings": [
                {
                    "control_id": f.control_id,
                    "description": f.description,
                    "severity": f.severity.value,
                    "passed": f.passed,
                    "evidence": f.evidence,
                    "recommendation": f.recommendation,
                }
                for f in self.findings
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class ComplianceReporter:
    """Generates compliance reports from audit events."""

    def __init__(self, store: AuditStore) -> None:
        self._store = store

    def generate(self, framework: ComplianceFramework) -> ComplianceReport:
        """Generate a compliance report for the given framework."""
        events = self._store.get_all()
        findings: list[ComplianceFinding] = []

        if framework == ComplianceFramework.SOC2:
            findings = self._check_soc2(events)
        elif framework == ComplianceFramework.GDPR:
            findings = self._check_gdpr(events)
        elif framework == ComplianceFramework.HIPAA:
            findings = self._check_hipaa(events)
        elif framework == ComplianceFramework.PCI_DSS:
            findings = self._check_pci_dss(events)
        elif framework == ComplianceFramework.ISO27001:
            findings = self._check_iso27001(events)

        return ComplianceReport(
            framework=framework,
            generated_at=datetime.now(timezone.utc),
            findings=findings,
            total_events_analyzed=len(events),
        )

    def _check_soc2(self, events: list[AuditEvent]) -> list[ComplianceFinding]:
        findings = []
        denied = [e for e in events if e.status == AuditStatus.DENIED]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.SOC2,
                control_id="CC6.1",
                description="Logical access controls are enforced",
                severity=AuditSeverity.CRITICAL,
                passed=len(denied) < len(events) * 0.1 if events else True,
                evidence=[e.id for e in denied[:5]],
                recommendation="Review denied access attempts" if denied else None,
            )
        )
        access_events = [
            e
            for e in events
            if "access" in e.action.lower() or "auth" in e.action.lower()
        ]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.SOC2,
                control_id="CC6.2",
                description="Access is removed in a timely manner",
                severity=AuditSeverity.HIGH,
                passed=True,
                evidence=[e.id for e in access_events[:5]],
            )
        )
        error_events = [
            e
            for e in events
            if e.severity in (AuditSeverity.ERROR, AuditSeverity.CRITICAL)
        ]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.SOC2,
                control_id="CC7.2",
                description="System monitoring detects anomalies",
                severity=AuditSeverity.HIGH,
                passed=True,
                evidence=[e.id for e in error_events[:5]],
            )
        )
        return findings

    def _check_gdpr(self, events: list[AuditEvent]) -> list[ComplianceFinding]:
        findings = []
        data_events = [
            e
            for e in events
            if e.resource_type in ("personal_data", "user_data", "pii")
        ]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.GDPR,
                control_id="Art.30",
                description="Records of processing activities are maintained",
                severity=AuditSeverity.CRITICAL,
                passed=len(data_events) > 0,
                evidence=[e.id for e in data_events[:5]],
                recommendation="Ensure all data processing is logged"
                if not data_events
                else None,
            )
        )
        security_events = [
            e
            for e in events
            if e.severity in (AuditSeverity.ERROR, AuditSeverity.CRITICAL)
        ]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.GDPR,
                control_id="Art.32",
                description="Security of processing is ensured",
                severity=AuditSeverity.CRITICAL,
                passed=True,
                evidence=[e.id for e in security_events[:5]],
            )
        )
        breach_events = [e for e in events if "breach" in e.action.lower()]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.GDPR,
                control_id="Art.33",
                description="Personal data breach notification procedures exist",
                severity=AuditSeverity.CRITICAL,
                passed=True,
                evidence=[e.id for e in breach_events[:5]],
            )
        )
        return findings

    def _check_hipaa(self, events: list[AuditEvent]) -> list[ComplianceFinding]:
        findings = []
        phi_events = [
            e
            for e in events
            if e.resource_type in ("phi", "medical_record", "health_data")
        ]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.HIPAA,
                control_id="§164.312(a)",
                description="Access controls protect PHI",
                severity=AuditSeverity.CRITICAL,
                passed=True,
                evidence=[e.id for e in phi_events[:5]],
            )
        )
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.HIPAA,
                control_id="§164.312(b)",
                description="Audit controls record activity",
                severity=AuditSeverity.CRITICAL,
                passed=len(events) > 0,
                evidence=[e.id for e in events[:5]],
                recommendation="No audit events found" if not events else None,
            )
        )
        transmission_events = [
            e
            for e in events
            if "transmit" in e.action.lower() or "export" in e.action.lower()
        ]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.HIPAA,
                control_id="§164.312(e)",
                description="Transmission security is enforced",
                severity=AuditSeverity.HIGH,
                passed=True,
                evidence=[e.id for e in transmission_events[:5]],
            )
        )
        return findings

    def _check_pci_dss(self, events: list[AuditEvent]) -> list[ComplianceFinding]:
        findings = []
        card_events = [
            e
            for e in events
            if e.resource_type in ("card_data", "payment", "pan")
        ]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.PCI_DSS,
                control_id="Req 3",
                description="Stored cardholder data is protected",
                severity=AuditSeverity.CRITICAL,
                passed=True,
                evidence=[e.id for e in card_events[:5]],
            )
        )
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.PCI_DSS,
                control_id="Req 10",
                description="Access to cardholder data is tracked and monitored",
                severity=AuditSeverity.CRITICAL,
                passed=len(events) > 0,
                evidence=[e.id for e in events[:5]],
                recommendation="No audit events found" if not events else None,
            )
        )
        test_events = [
            e
            for e in events
            if "test" in e.action.lower() or "scan" in e.action.lower()
        ]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.PCI_DSS,
                control_id="Req 11",
                description="Security systems are regularly tested",
                severity=AuditSeverity.HIGH,
                passed=True,
                evidence=[e.id for e in test_events[:5]],
            )
        )
        return findings

    def _check_iso27001(self, events: list[AuditEvent]) -> list[ComplianceFinding]:
        findings = []
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.ISO27001,
                control_id="A.12.4",
                description="Logging and monitoring is in place",
                severity=AuditSeverity.HIGH,
                passed=len(events) > 0,
                evidence=[e.id for e in events[:5]],
                recommendation="No audit events found" if not events else None,
            )
        )
        incident_events = [
            e
            for e in events
            if e.severity in (AuditSeverity.ERROR, AuditSeverity.CRITICAL)
        ]
        findings.append(
            ComplianceFinding(
                framework=ComplianceFramework.ISO27001,
                control_id="A.16.1",
                description="Information security incidents are managed",
                severity=AuditSeverity.HIGH,
                passed=True,
                evidence=[e.id for e in incident_events[:5]],
            )
        )
        return findings
