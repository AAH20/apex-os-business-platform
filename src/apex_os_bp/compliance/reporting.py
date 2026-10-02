"""Regulatory reporting module."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .models import RegulatoryReport


class RegulatoryReporter:
    """Manages regulatory report submissions."""

    def __init__(self) -> None:
        self._reports: dict[str, RegulatoryReport] = {}

    def create_report(
        self,
        report_id: str,
        name: str,
        regulation: str,
        reporting_period: str,
        due_date: date | None = None,
        submitted_by: str = "",
        notes: str = "",
        attachments: list[str] | None = None,
    ) -> RegulatoryReport:
        """Create a new regulatory report."""
        report = RegulatoryReport(
            id=report_id,
            name=name,
            regulation=regulation,
            reporting_period=reporting_period,
            due_date=due_date,
            submitted_by=submitted_by,
            notes=notes,
            attachments=attachments or [],
        )
        self._reports[report_id] = report
        return report

    def get_report(self, report_id: str) -> RegulatoryReport | None:
        """Get a report by ID."""
        return self._reports.get(report_id)

    def update_report(self, report_id: str, **kwargs: Any) -> RegulatoryReport | None:
        """Update report fields."""
        report = self._reports.get(report_id)
        if report is None:
            return None
        for key, value in kwargs.items():
            if hasattr(report, key):
                setattr(report, key, value)
        report.updated_at = datetime.utcnow()
        return report

    def submit_report(
        self, report_id: str, submitted_by: str, reference_number: str = ""
    ) -> RegulatoryReport | None:
        """Submit a regulatory report."""
        report = self._reports.get(report_id)
        if report is None:
            return None
        report.status = "submitted"
        report.submission_date = date.today()
        report.submitted_by = submitted_by
        if reference_number:
            report.reference_number = reference_number
        report.updated_at = datetime.utcnow()
        return report

    def accept_report(self, report_id: str) -> RegulatoryReport | None:
        """Mark a report as accepted."""
        report = self._reports.get(report_id)
        if report is None:
            return None
        report.status = "accepted"
        report.updated_at = datetime.utcnow()
        return report

    def reject_report(self, report_id: str, notes: str = "") -> RegulatoryReport | None:
        """Reject a report."""
        report = self._reports.get(report_id)
        if report is None:
            return None
        report.status = "rejected"
        if notes:
            report.notes = notes
        report.updated_at = datetime.utcnow()
        return report

    def add_attachment(self, report_id: str, attachment: str) -> RegulatoryReport | None:
        """Add an attachment to a report."""
        report = self._reports.get(report_id)
        if report is None:
            return None
        report.attachments.append(attachment)
        report.updated_at = datetime.utcnow()
        return report

    def remove_attachment(self, report_id: str, index: int) -> RegulatoryReport | None:
        """Remove an attachment by index."""
        report = self._reports.get(report_id)
        if report is None:
            return None
        if 0 <= index < len(report.attachments):
            report.attachments.pop(index)
            report.updated_at = datetime.utcnow()
        return report

    def remove_report(self, report_id: str) -> bool:
        """Remove a report."""
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False

    def list_reports(
        self,
        status: str | None = None,
        regulation: str | None = None,
        reporting_period: str | None = None,
    ) -> list[RegulatoryReport]:
        """List reports with optional filters."""
        reports = list(self._reports.values())
        if status is not None:
            reports = [r for r in reports if r.status == status]
        if regulation is not None:
            reports = [r for r in reports if r.regulation == regulation]
        if reporting_period is not None:
            reports = [r for r in reports if r.reporting_period == reporting_period]
        return reports

    def get_reports_by_regulation(self) -> dict[str, list[RegulatoryReport]]:
        """Group reports by regulation."""
        grouped: dict[str, list[RegulatoryReport]] = defaultdict(list)
        for report in self._reports.values():
            grouped[report.regulation].append(report)
        return dict(grouped)

    def get_reports_by_status(self) -> dict[str, list[RegulatoryReport]]:
        """Group reports by status."""
        grouped: dict[str, list[RegulatoryReport]] = defaultdict(list)
        for report in self._reports.values():
            grouped[report.status].append(report)
        return dict(grouped)

    def get_overdue_reports(self) -> list[RegulatoryReport]:
        """Get all overdue reports."""
        return [r for r in self._reports.values() if r.is_overdue]

    def get_upcoming_deadlines(self, days: int = 30) -> list[RegulatoryReport]:
        """Get reports with deadlines within the specified number of days."""
        today = date.today()
        upcoming: list[RegulatoryReport] = []
        for report in self._reports.values():
            if (
                report.due_date is not None
                and report.status not in ("submitted", "accepted")
                and 0 <= (report.due_date - today).days <= days
            ):
                upcoming.append(report)
        return sorted(upcoming, key=lambda r: r.due_date or date.max)

    def get_submission_rate(self) -> float:
        """Get the submission rate as a percentage."""
        if not self._reports:
            return 0.0
        submitted = sum(
            1 for r in self._reports.values()
            if r.status in ("submitted", "accepted")
        )
        return (submitted / len(self._reports)) * 100.0

    def to_dict(self) -> dict[str, Any]:
        """Export all reports as a dictionary."""
        return {
            "reports": {k: v.to_dict() for k, v in self._reports.items()},
            "by_status": {k: len(v) for k, v in self.get_reports_by_status().items()},
            "submission_rate": self.get_submission_rate(),
        }

    def __len__(self) -> int:
        return len(self._reports)
