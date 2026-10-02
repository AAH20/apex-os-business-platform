"""Audit management module."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .models import Audit, AuditFinding, AuditStatus, FindingSeverity


class AuditManager:
    """Manages audit engagements and findings."""

    def __init__(self) -> None:
        self._audits: dict[str, Audit] = {}

    def create_audit(
        self,
        audit_id: str,
        name: str,
        audit_type: str,
        scope: str,
        lead_auditor: str = "",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Audit:
        """Create a new audit."""
        audit = Audit(
            id=audit_id,
            name=name,
            audit_type=audit_type,
            scope=scope,
            status=AuditStatus.PLANNED,
            lead_auditor=lead_auditor,
            start_date=start_date,
            end_date=end_date,
        )
        self._audits[audit_id] = audit
        return audit

    def get_audit(self, audit_id: str) -> Audit | None:
        """Get an audit by ID."""
        return self._audits.get(audit_id)

    def update_audit(self, audit_id: str, **kwargs: Any) -> Audit | None:
        """Update audit fields."""
        audit = self._audits.get(audit_id)
        if audit is None:
            return None
        for key, value in kwargs.items():
            if hasattr(audit, key):
                setattr(audit, key, value)
        audit.updated_at = datetime.utcnow()
        return audit

    def start_audit(self, audit_id: str) -> Audit | None:
        """Mark an audit as in progress."""
        audit = self._audits.get(audit_id)
        if audit is None:
            return None
        audit.status = AuditStatus.IN_PROGRESS
        if audit.start_date is None:
            audit.start_date = date.today()
        audit.updated_at = datetime.utcnow()
        return audit

    def complete_audit(self, audit_id: str) -> Audit | None:
        """Mark an audit as completed."""
        audit = self._audits.get(audit_id)
        if audit is None:
            return None
        audit.status = AuditStatus.COMPLETED
        if audit.end_date is None:
            audit.end_date = date.today()
        audit.updated_at = datetime.utcnow()
        return audit

    def cancel_audit(self, audit_id: str) -> Audit | None:
        """Cancel an audit."""
        audit = self._audits.get(audit_id)
        if audit is None:
            return None
        audit.status = AuditStatus.CANCELLED
        audit.updated_at = datetime.utcnow()
        return audit

    def add_finding(
        self,
        audit_id: str,
        finding_id: str,
        title: str,
        description: str,
        severity: FindingSeverity,
        recommendation: str = "",
        owner: str = "",
        due_date: date | None = None,
    ) -> AuditFinding | None:
        """Add a finding to an audit."""
        audit = self._audits.get(audit_id)
        if audit is None:
            return None
        finding = AuditFinding(
            id=finding_id,
            title=title,
            description=description,
            severity=severity,
            recommendation=recommendation,
            owner=owner,
            due_date=due_date,
        )
        audit.findings.append(finding)
        audit.updated_at = datetime.utcnow()
        return finding

    def get_finding(self, audit_id: str, finding_id: str) -> AuditFinding | None:
        """Get a specific finding from an audit."""
        audit = self._audits.get(audit_id)
        if audit is None:
            return None
        for finding in audit.findings:
            if finding.id == finding_id:
                return finding
        return None

    def update_finding_status(
        self, audit_id: str, finding_id: str, status: str
    ) -> AuditFinding | None:
        """Update the status of a finding."""
        finding = self.get_finding(audit_id, finding_id)
        if finding is None:
            return None
        finding.status = status
        if status in ("resolved", "closed"):
            finding.resolved_at = datetime.utcnow()
        audit = self._audits[audit_id]
        audit.updated_at = datetime.utcnow()
        return finding

    def remove_finding(self, audit_id: str, finding_id: str) -> bool:
        """Remove a finding from an audit."""
        audit = self._audits.get(audit_id)
        if audit is None:
            return False
        for i, finding in enumerate(audit.findings):
            if finding.id == finding_id:
                audit.findings.pop(i)
                audit.updated_at = datetime.utcnow()
                return True
        return False

    def remove_audit(self, audit_id: str) -> bool:
        """Remove an audit."""
        if audit_id in self._audits:
            del self._audits[audit_id]
            return True
        return False

    def list_audits(
        self,
        status: AuditStatus | None = None,
        audit_type: str | None = None,
        lead_auditor: str | None = None,
    ) -> list[Audit]:
        """List audits with optional filters."""
        audits = list(self._audits.values())
        if status is not None:
            audits = [a for a in audits if a.status == status]
        if audit_type is not None:
            audits = [a for a in audits if a.audit_type == audit_type]
        if lead_auditor is not None:
            audits = [a for a in audits if a.lead_auditor == lead_auditor]
        return audits

    def get_audits_by_type(self) -> dict[str, list[Audit]]:
        """Group audits by type."""
        grouped: dict[str, list[Audit]] = defaultdict(list)
        for audit in self._audits.values():
            grouped[audit.audit_type].append(audit)
        return dict(grouped)

    def get_open_findings(self) -> list[tuple[str, AuditFinding]]:
        """Get all open findings across all audits."""
        results: list[tuple[str, AuditFinding]] = []
        for audit in self._audits.values():
            for finding in audit.findings:
                if finding.status in ("open", "in_progress"):
                    results.append((audit.id, finding))
        return results

    def get_overdue_findings(self) -> list[tuple[str, AuditFinding]]:
        """Get findings past their due date."""
        today = date.today()
        results: list[tuple[str, AuditFinding]] = []
        for audit in self._audits.values():
            for finding in audit.findings:
                if (
                    finding.due_date is not None
                    and finding.due_date < today
                    and finding.status in ("open", "in_progress")
                ):
                    results.append((audit.id, finding))
        return results

    def get_finding_summary(self) -> dict[str, int]:
        """Get a summary count of findings by severity."""
        summary: dict[str, int] = defaultdict(int)
        for audit in self._audits.values():
            for finding in audit.findings:
                summary[finding.severity.value] += 1
        return dict(summary)

    def to_dict(self) -> dict[str, Any]:
        """Export all audits as a dictionary."""
        return {
            "audits": {k: v.to_dict() for k, v in self._audits.items()},
            "finding_summary": self.get_finding_summary(),
        }

    def __len__(self) -> int:
        return len(self._audits)
