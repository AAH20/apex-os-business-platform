"""Tests for the compliance management system."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from apex_os_bp.compliance.models import (
    Audit,
    AuditFinding,
    AuditStatus,
    ComplianceItem,
    ComplianceStatus,
    FindingSeverity,
    Policy,
    RegulatoryReport,
    RiskAssessment,
    RiskLevel,
)
from apex_os_bp.compliance.tracking import ComplianceTracker
from apex_os_bp.compliance.policies import PolicyManager
from apex_os_bp.compliance.risk import RiskAssessor
from apex_os_bp.compliance.audit import AuditManager
from apex_os_bp.compliance.reporting import RegulatoryReporter


# ============================================================================
# Compliance Tracking Tests
# ============================================================================


class TestComplianceTracker:
    """Tests for ComplianceTracker."""

    def setup_method(self) -> None:
        self.tracker = ComplianceTracker()

    def test_add_item(self) -> None:
        item = ComplianceItem(
            id="c1",
            name="Data Encryption",
            description="All data must be encrypted at rest",
            regulation="GDPR",
            category="data_protection",
        )
        result = self.tracker.add_item(item)
        assert result.id == "c1"
        assert len(self.tracker) == 1

    def test_get_item(self) -> None:
        item = ComplianceItem(
            id="c1",
            name="Data Encryption",
            description="All data must be encrypted at rest",
            regulation="GDPR",
            category="data_protection",
        )
        self.tracker.add_item(item)
        found = self.tracker.get_item("c1")
        assert found is not None
        assert found.name == "Data Encryption"

    def test_get_item_not_found(self) -> None:
        assert self.tracker.get_item("nonexistent") is None

    def test_update_status(self) -> None:
        item = ComplianceItem(
            id="c1",
            name="Data Encryption",
            description="All data must be encrypted at rest",
            regulation="GDPR",
            category="data_protection",
        )
        self.tracker.add_item(item)
        updated = self.tracker.update_status("c1", ComplianceStatus.COMPLIANT)
        assert updated is not None
        assert updated.status == ComplianceStatus.COMPLIANT
        assert updated.last_assessed is not None

    def test_update_status_not_found(self) -> None:
        assert self.tracker.update_status("nonexistent", ComplianceStatus.COMPLIANT) is None

    def test_add_evidence(self) -> None:
        item = ComplianceItem(
            id="c1",
            name="Data Encryption",
            description="All data must be encrypted at rest",
            regulation="GDPR",
            category="data_protection",
        )
        self.tracker.add_item(item)
        updated = self.tracker.add_evidence("c1", "evidence.pdf")
        assert updated is not None
        assert "evidence.pdf" in updated.evidence

    def test_add_evidence_not_found(self) -> None:
        assert self.tracker.add_evidence("nonexistent", "evidence.pdf") is None

    def test_remove_item(self) -> None:
        item = ComplianceItem(
            id="c1",
            name="Data Encryption",
            description="All data must be encrypted at rest",
            regulation="GDPR",
            category="data_protection",
        )
        self.tracker.add_item(item)
        assert self.tracker.remove_item("c1") is True
        assert len(self.tracker) == 0

    def test_remove_item_not_found(self) -> None:
        assert self.tracker.remove_item("nonexistent") is False

    def test_list_items_no_filter(self) -> None:
        for i in range(3):
            self.tracker.add_item(
                ComplianceItem(
                    id=f"c{i}",
                    name=f"Item {i}",
                    description=f"Description {i}",
                    regulation="GDPR",
                    category="data_protection",
                )
            )
        assert len(self.tracker.list_items()) == 3

    def test_list_items_filter_by_status(self) -> None:
        item1 = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
            status=ComplianceStatus.COMPLIANT,
        )
        item2 = ComplianceItem(
            id="c2",
            name="Item 2",
            description="Desc 2",
            regulation="GDPR",
            category="data_protection",
            status=ComplianceStatus.NON_COMPLIANT,
        )
        self.tracker.add_item(item1)
        self.tracker.add_item(item2)
        results = self.tracker.list_items(status=ComplianceStatus.COMPLIANT)
        assert len(results) == 1
        assert results[0].id == "c1"

    def test_list_items_filter_by_category(self) -> None:
        item1 = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
        )
        item2 = ComplianceItem(
            id="c2",
            name="Item 2",
            description="Desc 2",
            regulation="GDPR",
            category="access_control",
        )
        self.tracker.add_item(item1)
        self.tracker.add_item(item2)
        results = self.tracker.list_items(category="data_protection")
        assert len(results) == 1
        assert results[0].id == "c1"

    def test_list_items_filter_by_regulation(self) -> None:
        item1 = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
        )
        item2 = ComplianceItem(
            id="c2",
            name="Item 2",
            description="Desc 2",
            regulation="HIPAA",
            category="data_protection",
        )
        self.tracker.add_item(item1)
        self.tracker.add_item(item2)
        results = self.tracker.list_items(regulation="GDPR")
        assert len(results) == 1
        assert results[0].id == "c1"

    def test_list_items_filter_by_owner(self) -> None:
        item1 = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
            owner="Alice",
        )
        item2 = ComplianceItem(
            id="c2",
            name="Item 2",
            description="Desc 2",
            regulation="GDPR",
            category="data_protection",
            owner="Bob",
        )
        self.tracker.add_item(item1)
        self.tracker.add_item(item2)
        results = self.tracker.list_items(owner="Alice")
        assert len(results) == 1
        assert results[0].id == "c1"

    def test_get_overdue_items(self) -> None:
        past = date.today() - timedelta(days=10)
        item1 = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
            due_date=past,
            status=ComplianceStatus.PENDING,
        )
        item2 = ComplianceItem(
            id="c2",
            name="Item 2",
            description="Desc 2",
            regulation="GDPR",
            category="data_protection",
            due_date=past,
            status=ComplianceStatus.COMPLIANT,
        )
        self.tracker.add_item(item1)
        self.tracker.add_item(item2)
        overdue = self.tracker.get_overdue_items()
        assert len(overdue) == 1
        assert overdue[0].id == "c1"

    def test_get_status_summary(self) -> None:
        item1 = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
            status=ComplianceStatus.COMPLIANT,
        )
        item2 = ComplianceItem(
            id="c2",
            name="Item 2",
            description="Desc 2",
            regulation="GDPR",
            category="data_protection",
            status=ComplianceStatus.NON_COMPLIANT,
        )
        item3 = ComplianceItem(
            id="c3",
            name="Item 3",
            description="Desc 3",
            regulation="GDPR",
            category="data_protection",
            status=ComplianceStatus.COMPLIANT,
        )
        self.tracker.add_item(item1)
        self.tracker.add_item(item2)
        self.tracker.add_item(item3)
        summary = self.tracker.get_status_summary()
        assert summary["compliant"] == 2
        assert summary["non_compliant"] == 1

    def test_get_compliance_rate(self) -> None:
        item1 = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
            status=ComplianceStatus.COMPLIANT,
        )
        item2 = ComplianceItem(
            id="c2",
            name="Item 2",
            description="Desc 2",
            regulation="GDPR",
            category="data_protection",
            status=ComplianceStatus.NON_COMPLIANT,
        )
        self.tracker.add_item(item1)
        self.tracker.add_item(item2)
        assert self.tracker.get_compliance_rate() == 50.0

    def test_get_compliance_rate_empty(self) -> None:
        assert self.tracker.get_compliance_rate() == 0.0

    def test_get_items_by_category(self) -> None:
        item1 = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
        )
        item2 = ComplianceItem(
            id="c2",
            name="Item 2",
            description="Desc 2",
            regulation="GDPR",
            category="access_control",
        )
        item3 = ComplianceItem(
            id="c3",
            name="Item 3",
            description="Desc 3",
            regulation="GDPR",
            category="data_protection",
        )
        self.tracker.add_item(item1)
        self.tracker.add_item(item2)
        self.tracker.add_item(item3)
        grouped = self.tracker.get_items_by_category()
        assert len(grouped["data_protection"]) == 2
        assert len(grouped["access_control"]) == 1

    def test_get_items_by_regulation(self) -> None:
        item1 = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
        )
        item2 = ComplianceItem(
            id="c2",
            name="Item 2",
            description="Desc 2",
            regulation="HIPAA",
            category="data_protection",
        )
        self.tracker.add_item(item1)
        self.tracker.add_item(item2)
        grouped = self.tracker.get_items_by_regulation()
        assert len(grouped["GDPR"]) == 1
        assert len(grouped["HIPAA"]) == 1

    def test_to_dict(self) -> None:
        item = ComplianceItem(
            id="c1",
            name="Item 1",
            description="Desc 1",
            regulation="GDPR",
            category="data_protection",
            status=ComplianceStatus.COMPLIANT,
        )
        self.tracker.add_item(item)
        data = self.tracker.to_dict()
        assert "items" in data
        assert "summary" in data
        assert "compliance_rate" in data
        assert data["items"]["c1"]["name"] == "Item 1"


# ============================================================================
# Policy Management Tests
# ============================================================================


class TestPolicyManager:
    """Tests for PolicyManager."""

    def setup_method(self) -> None:
        self.manager = PolicyManager()

    def test_create_policy(self) -> None:
        policy = self.manager.create_policy(
            policy_id="p1",
            title="Data Retention Policy",
            version="1.0",
            content="All data must be retained for 7 years",
            category="data_governance",
            author="Alice",
        )
        assert policy.id == "p1"
        assert policy.status == "draft"
        assert len(self.manager) == 1

    def test_get_policy(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Data Retention Policy",
            version="1.0",
            content="All data must be retained for 7 years",
            category="data_governance",
        )
        found = self.manager.get_policy("p1")
        assert found is not None
        assert found.title == "Data Retention Policy"

    def test_get_policy_not_found(self) -> None:
        assert self.manager.get_policy("nonexistent") is None

    def test_update_policy(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Data Retention Policy",
            version="1.0",
            content="All data must be retained for 7 years",
            category="data_governance",
        )
        updated = self.manager.update_policy("p1", title="Updated Title")
        assert updated is not None
        assert updated.title == "Updated Title"

    def test_update_policy_not_found(self) -> None:
        assert self.manager.update_policy("nonexistent", title="New") is None

    def test_approve_policy(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Data Retention Policy",
            version="1.0",
            content="All data must be retained for 7 years",
            category="data_governance",
        )
        approved = self.manager.approve_policy("p1", approver="Bob")
        assert approved is not None
        assert approved.status == "active"
        assert approved.approver == "Bob"
        assert approved.effective_date is not None

    def test_approve_policy_not_found(self) -> None:
        assert self.manager.approve_policy("nonexistent", approver="Bob") is None

    def test_deprecate_policy(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Data Retention Policy",
            version="1.0",
            content="All data must be retained for 7 years",
            category="data_governance",
        )
        self.manager.approve_policy("p1", approver="Bob")
        deprecated = self.manager.deprecate_policy("p1")
        assert deprecated is not None
        assert deprecated.status == "deprecated"

    def test_archive_policy(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Data Retention Policy",
            version="1.0",
            content="All data must be retained for 7 years",
            category="data_governance",
        )
        archived = self.manager.archive_policy("p1")
        assert archived is not None
        assert archived.status == "archived"

    def test_remove_policy(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Data Retention Policy",
            version="1.0",
            content="All data must be retained for 7 years",
            category="data_governance",
        )
        assert self.manager.remove_policy("p1") is True
        assert len(self.manager) == 0

    def test_remove_policy_not_found(self) -> None:
        assert self.manager.remove_policy("nonexistent") is False

    def test_list_policies_no_filter(self) -> None:
        for i in range(3):
            self.manager.create_policy(
                policy_id=f"p{i}",
                title=f"Policy {i}",
                version="1.0",
                content=f"Content {i}",
                category="data_governance",
            )
        assert len(self.manager.list_policies()) == 3

    def test_list_policies_filter_by_status(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Policy 1",
            version="1.0",
            content="Content 1",
            category="data_governance",
        )
        self.manager.create_policy(
            policy_id="p2",
            title="Policy 2",
            version="1.0",
            content="Content 2",
            category="data_governance",
        )
        self.manager.approve_policy("p1", approver="Bob")
        results = self.manager.list_policies(status="active")
        assert len(results) == 1
        assert results[0].id == "p1"

    def test_list_policies_filter_by_category(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Policy 1",
            version="1.0",
            content="Content 1",
            category="data_governance",
        )
        self.manager.create_policy(
            policy_id="p2",
            title="Policy 2",
            version="1.0",
            content="Content 2",
            category="security",
        )
        results = self.manager.list_policies(category="data_governance")
        assert len(results) == 1
        assert results[0].id == "p1"

    def test_list_policies_filter_by_tag(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Policy 1",
            version="1.0",
            content="Content 1",
            category="data_governance",
            tags=["gdpr", "data"],
        )
        self.manager.create_policy(
            policy_id="p2",
            title="Policy 2",
            version="1.0",
            content="Content 2",
            category="data_governance",
            tags=["hipaa"],
        )
        results = self.manager.list_policies(tag="gdpr")
        assert len(results) == 1
        assert results[0].id == "p1"

    def test_get_policies_by_category(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Policy 1",
            version="1.0",
            content="Content 1",
            category="data_governance",
        )
        self.manager.create_policy(
            policy_id="p2",
            title="Policy 2",
            version="1.0",
            content="Content 2",
            category="security",
        )
        self.manager.create_policy(
            policy_id="p3",
            title="Policy 3",
            version="1.0",
            content="Content 3",
            category="data_governance",
        )
        grouped = self.manager.get_policies_by_category()
        assert len(grouped["data_governance"]) == 2
        assert len(grouped["security"]) == 1

    def test_get_policies_by_regulation(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Policy 1",
            version="1.0",
            content="Content 1",
            category="data_governance",
            related_regulations=["GDPR"],
        )
        self.manager.create_policy(
            policy_id="p2",
            title="Policy 2",
            version="1.0",
            content="Content 2",
            category="data_governance",
            related_regulations=["HIPAA"],
        )
        results = self.manager.get_policies_by_regulation("GDPR")
        assert len(results) == 1
        assert results[0].id == "p1"

    def test_get_policies_needing_review(self) -> None:
        past = date.today() - timedelta(days=10)
        self.manager.create_policy(
            policy_id="p1",
            title="Policy 1",
            version="1.0",
            content="Content 1",
            category="data_governance",
            review_date=past,
        )
        self.manager.approve_policy("p1", approver="Bob")
        self.manager.create_policy(
            policy_id="p2",
            title="Policy 2",
            version="1.0",
            content="Content 2",
            category="data_governance",
            review_date=date.today() + timedelta(days=30),
        )
        self.manager.approve_policy("p2", approver="Bob")
        results = self.manager.get_policies_needing_review()
        assert len(results) == 1
        assert results[0].id == "p1"

    def test_search_policies(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Data Retention Policy",
            version="1.0",
            content="All data must be retained for 7 years",
            category="data_governance",
        )
        self.manager.create_policy(
            policy_id="p2",
            title="Access Control Policy",
            version="1.0",
            content="Only authorized users can access systems",
            category="security",
        )
        results = self.manager.search_policies("retention")
        assert len(results) == 1
        assert results[0].id == "p1"

    def test_to_dict(self) -> None:
        self.manager.create_policy(
            policy_id="p1",
            title="Policy 1",
            version="1.0",
            content="Content 1",
            category="data_governance",
        )
        data = self.manager.to_dict()
        assert "policies" in data
        assert "total" in data
        assert data["total"] == 1


# ============================================================================
# Risk Assessment Tests
# ============================================================================


class TestRiskAssessor:
    """Tests for RiskAssessor."""

    def setup_method(self) -> None:
        self.assessor = RiskAssessor()

    def test_create_risk(self) -> None:
        risk = self.assessor.create_risk(
            risk_id="r1",
            name="Data Breach",
            description="Unauthorized access to customer data",
            category="security",
            likelihood=4,
            impact=5,
        )
        assert risk.id == "r1"
        assert risk.risk_level == RiskLevel.CRITICAL
        assert risk.risk_score == 20
        assert len(self.assessor) == 1

    def test_create_risk_clamps_values(self) -> None:
        risk = self.assessor.create_risk(
            risk_id="r1",
            name="Low Risk",
            description="Test",
            category="test",
            likelihood=10,
            impact=10,
        )
        assert risk.likelihood == 5
        assert risk.impact == 5

    def test_get_risk(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Data Breach",
            description="Unauthorized access to customer data",
            category="security",
        )
        found = self.assessor.get_risk("r1")
        assert found is not None
        assert found.name == "Data Breach"

    def test_get_risk_not_found(self) -> None:
        assert self.assessor.get_risk("nonexistent") is None

    def test_update_risk(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Data Breach",
            description="Unauthorized access to customer data",
            category="security",
            likelihood=2,
            impact=2,
        )
        updated = self.assessor.update_risk("r1", likelihood=5, impact=5)
        assert updated is not None
        assert updated.risk_level == RiskLevel.CRITICAL
        assert updated.risk_score == 25

    def test_update_risk_not_found(self) -> None:
        assert self.assessor.update_risk("nonexistent", name="New") is None

    def test_add_mitigation(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Data Breach",
            description="Unauthorized access to customer data",
            category="security",
        )
        updated = self.assessor.add_mitigation("r1", "Implement MFA")
        assert updated is not None
        assert "Implement MFA" in updated.mitigations

    def test_add_mitigation_not_found(self) -> None:
        assert self.assessor.add_mitigation("nonexistent", "MFA") is None

    def test_remove_mitigation(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Data Breach",
            description="Unauthorized access to customer data",
            category="security",
            mitigations=["MFA", "Encryption"],
        )
        updated = self.assessor.remove_mitigation("r1", 0)
        assert updated is not None
        assert len(updated.mitigations) == 1
        assert updated.mitigations[0] == "Encryption"

    def test_remove_mitigation_invalid_index(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Data Breach",
            description="Unauthorized access to customer data",
            category="security",
            mitigations=["MFA"],
        )
        updated = self.assessor.remove_mitigation("r1", 5)
        assert updated is not None
        assert len(updated.mitigations) == 1

    def test_update_status(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Data Breach",
            description="Unauthorized access to customer data",
            category="security",
        )
        updated = self.assessor.update_status("r1", "mitigated")
        assert updated is not None
        assert updated.status == "mitigated"

    def test_remove_risk(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Data Breach",
            description="Unauthorized access to customer data",
            category="security",
        )
        assert self.assessor.remove_risk("r1") is True
        assert len(self.assessor) == 0

    def test_remove_risk_not_found(self) -> None:
        assert self.assessor.remove_risk("nonexistent") is False

    def test_list_risks_no_filter(self) -> None:
        for i in range(3):
            self.assessor.create_risk(
                risk_id=f"r{i}",
                name=f"Risk {i}",
                description=f"Description {i}",
                category="security",
            )
        assert len(self.assessor.list_risks()) == 3

    def test_list_risks_filter_by_level(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Critical Risk",
            description="Test",
            category="security",
            likelihood=5,
            impact=5,
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Low Risk",
            description="Test",
            category="security",
            likelihood=1,
            impact=1,
        )
        results = self.assessor.list_risks(risk_level=RiskLevel.CRITICAL)
        assert len(results) == 1
        assert results[0].id == "r1"

    def test_list_risks_filter_by_category(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Risk 1",
            description="Test",
            category="security",
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Risk 2",
            description="Test",
            category="operational",
        )
        results = self.assessor.list_risks(category="security")
        assert len(results) == 1
        assert results[0].id == "r1"

    def test_list_risks_filter_by_status(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Risk 1",
            description="Test",
            category="security",
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Risk 2",
            description="Test",
            category="security",
        )
        self.assessor.update_status("r1", "mitigated")
        results = self.assessor.list_risks(status="open")
        assert len(results) == 1
        assert results[0].id == "r2"

    def test_list_risks_filter_by_owner(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Risk 1",
            description="Test",
            category="security",
            owner="Alice",
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Risk 2",
            description="Test",
            category="security",
            owner="Bob",
        )
        results = self.assessor.list_risks(owner="Alice")
        assert len(results) == 1
        assert results[0].id == "r1"

    def test_get_risks_by_level(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Critical Risk",
            description="Test",
            category="security",
            likelihood=5,
            impact=5,
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Low Risk",
            description="Test",
            category="security",
            likelihood=1,
            impact=1,
        )
        grouped = self.assessor.get_risks_by_level()
        assert len(grouped["critical"]) == 1
        assert len(grouped["negligible"]) == 1

    def test_get_risks_by_category(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Risk 1",
            description="Test",
            category="security",
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Risk 2",
            description="Test",
            category="operational",
        )
        self.assessor.create_risk(
            risk_id="r3",
            name="Risk 3",
            description="Test",
            category="security",
        )
        grouped = self.assessor.get_risks_by_category()
        assert len(grouped["security"]) == 2
        assert len(grouped["operational"]) == 1

    def test_get_open_risks(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Risk 1",
            description="Test",
            category="security",
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Risk 2",
            description="Test",
            category="security",
        )
        self.assessor.update_status("r1", "mitigated")
        open_risks = self.assessor.get_open_risks()
        assert len(open_risks) == 1
        assert open_risks[0].id == "r2"

    def test_get_critical_risks(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Critical Risk",
            description="Test",
            category="security",
            likelihood=5,
            impact=5,
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Low Risk",
            description="Test",
            category="security",
            likelihood=1,
            impact=1,
        )
        critical = self.assessor.get_critical_risks()
        assert len(critical) == 1
        assert critical[0].id == "r1"

    def test_get_overdue_reviews(self) -> None:
        past = date.today() - timedelta(days=10)
        self.assessor.create_risk(
            risk_id="r1",
            name="Risk 1",
            description="Test",
            category="security",
            review_date=past,
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Risk 2",
            description="Test",
            category="security",
            review_date=date.today() + timedelta(days=30),
        )
        overdue = self.assessor.get_overdue_reviews()
        assert len(overdue) == 1
        assert overdue[0].id == "r1"

    def test_get_risk_matrix(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Risk 1",
            description="Test",
            category="security",
            likelihood=3,
            impact=4,
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Risk 2",
            description="Test",
            category="security",
            likelihood=3,
            impact=4,
        )
        matrix = self.assessor.get_risk_matrix()
        assert matrix["3"]["4"] == 2

    def test_get_average_risk_score(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Risk 1",
            description="Test",
            category="security",
            likelihood=2,
            impact=3,
        )
        self.assessor.create_risk(
            risk_id="r2",
            name="Risk 2",
            description="Test",
            category="security",
            likelihood=4,
            impact=5,
        )
        # Scores: 6 and 20, average = 13
        assert self.assessor.get_average_risk_score() == 13.0

    def test_get_average_risk_score_empty(self) -> None:
        assert self.assessor.get_average_risk_score() == 0.0

    def test_to_dict(self) -> None:
        self.assessor.create_risk(
            risk_id="r1",
            name="Risk 1",
            description="Test",
            category="security",
        )
        data = self.assessor.to_dict()
        assert "risks" in data
        assert "by_level" in data
        assert "average_score" in data


# ============================================================================
# Audit Management Tests
# ============================================================================


class TestAuditManager:
    """Tests for AuditManager."""

    def setup_method(self) -> None:
        self.manager = AuditManager()

    def test_create_audit(self) -> None:
        audit = self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
            lead_auditor="Alice",
        )
        assert audit.id == "a1"
        assert audit.status == AuditStatus.PLANNED
        assert len(self.manager) == 1

    def test_get_audit(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        found = self.manager.get_audit("a1")
        assert found is not None
        assert found.name == "Q1 Security Audit"

    def test_get_audit_not_found(self) -> None:
        assert self.manager.get_audit("nonexistent") is None

    def test_update_audit(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        updated = self.manager.update_audit("a1", name="Updated Audit")
        assert updated is not None
        assert updated.name == "Updated Audit"

    def test_start_audit(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        started = self.manager.start_audit("a1")
        assert started is not None
        assert started.status == AuditStatus.IN_PROGRESS
        assert started.start_date is not None

    def test_complete_audit(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.start_audit("a1")
        completed = self.manager.complete_audit("a1")
        assert completed is not None
        assert completed.status == AuditStatus.COMPLETED
        assert completed.end_date is not None

    def test_cancel_audit(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        cancelled = self.manager.cancel_audit("a1")
        assert cancelled is not None
        assert cancelled.status == AuditStatus.CANCELLED

    def test_add_finding(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        finding = self.manager.add_finding(
            audit_id="a1",
            finding_id="f1",
            title="Weak Passwords",
            description="Users have weak passwords",
            severity=FindingSeverity.MAJOR,
            recommendation="Enforce strong password policy",
        )
        assert finding is not None
        assert finding.id == "f1"
        assert finding.status == "open"

    def test_add_finding_audit_not_found(self) -> None:
        result = self.manager.add_finding(
            audit_id="nonexistent",
            finding_id="f1",
            title="Test",
            description="Test",
            severity=FindingSeverity.MINOR,
        )
        assert result is None

    def test_get_finding(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f1",
            title="Weak Passwords",
            description="Users have weak passwords",
            severity=FindingSeverity.MAJOR,
        )
        found = self.manager.get_finding("a1", "f1")
        assert found is not None
        assert found.title == "Weak Passwords"

    def test_get_finding_not_found(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        assert self.manager.get_finding("a1", "nonexistent") is None

    def test_update_finding_status(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f1",
            title="Weak Passwords",
            description="Users have weak passwords",
            severity=FindingSeverity.MAJOR,
        )
        updated = self.manager.update_finding_status("a1", "f1", "resolved")
        assert updated is not None
        assert updated.status == "resolved"
        assert updated.resolved_at is not None

    def test_update_finding_status_not_found(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        assert self.manager.update_finding_status("a1", "nonexistent", "resolved") is None

    def test_remove_finding(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f1",
            title="Weak Passwords",
            description="Users have weak passwords",
            severity=FindingSeverity.MAJOR,
        )
        assert self.manager.remove_finding("a1", "f1") is True
        audit = self.manager.get_audit("a1")
        assert audit is not None
        assert audit.finding_count == 0

    def test_remove_finding_not_found(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        assert self.manager.remove_finding("a1", "nonexistent") is False

    def test_remove_audit(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Q1 Security Audit",
            audit_type="internal",
            scope="All systems",
        )
        assert self.manager.remove_audit("a1") is True
        assert len(self.manager) == 0

    def test_remove_audit_not_found(self) -> None:
        assert self.manager.remove_audit("nonexistent") is False

    def test_list_audits_no_filter(self) -> None:
        for i in range(3):
            self.manager.create_audit(
                audit_id=f"a{i}",
                name=f"Audit {i}",
                audit_type="internal",
                scope="All systems",
            )
        assert len(self.manager.list_audits()) == 3

    def test_list_audits_filter_by_status(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Audit 1",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.create_audit(
            audit_id="a2",
            name="Audit 2",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.start_audit("a1")
        results = self.manager.list_audits(status=AuditStatus.IN_PROGRESS)
        assert len(results) == 1
        assert results[0].id == "a1"

    def test_list_audits_filter_by_type(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Audit 1",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.create_audit(
            audit_id="a2",
            name="Audit 2",
            audit_type="external",
            scope="All systems",
        )
        results = self.manager.list_audits(audit_type="internal")
        assert len(results) == 1
        assert results[0].id == "a1"

    def test_list_audits_filter_by_lead_auditor(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Audit 1",
            audit_type="internal",
            scope="All systems",
            lead_auditor="Alice",
        )
        self.manager.create_audit(
            audit_id="a2",
            name="Audit 2",
            audit_type="internal",
            scope="All systems",
            lead_auditor="Bob",
        )
        results = self.manager.list_audits(lead_auditor="Alice")
        assert len(results) == 1
        assert results[0].id == "a1"

    def test_get_audits_by_type(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Audit 1",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.create_audit(
            audit_id="a2",
            name="Audit 2",
            audit_type="external",
            scope="All systems",
        )
        self.manager.create_audit(
            audit_id="a3",
            name="Audit 3",
            audit_type="internal",
            scope="All systems",
        )
        grouped = self.manager.get_audits_by_type()
        assert len(grouped["internal"]) == 2
        assert len(grouped["external"]) == 1

    def test_get_open_findings(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Audit 1",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f1",
            title="Finding 1",
            description="Test",
            severity=FindingSeverity.MAJOR,
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f2",
            title="Finding 2",
            description="Test",
            severity=FindingSeverity.MINOR,
        )
        self.manager.update_finding_status("a1", "f1", "resolved")
        open_findings = self.manager.get_open_findings()
        assert len(open_findings) == 1
        assert open_findings[0][1].id == "f2"

    def test_get_overdue_findings(self) -> None:
        past = date.today() - timedelta(days=10)
        self.manager.create_audit(
            audit_id="a1",
            name="Audit 1",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f1",
            title="Finding 1",
            description="Test",
            severity=FindingSeverity.MAJOR,
            due_date=past,
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f2",
            title="Finding 2",
            description="Test",
            severity=FindingSeverity.MINOR,
            due_date=date.today() + timedelta(days=30),
        )
        overdue = self.manager.get_overdue_findings()
        assert len(overdue) == 1
        assert overdue[0][1].id == "f1"

    def test_get_finding_summary(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Audit 1",
            audit_type="internal",
            scope="All systems",
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f1",
            title="Finding 1",
            description="Test",
            severity=FindingSeverity.CRITICAL,
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f2",
            title="Finding 2",
            description="Test",
            severity=FindingSeverity.MAJOR,
        )
        self.manager.add_finding(
            audit_id="a1",
            finding_id="f3",
            title="Finding 3",
            description="Test",
            severity=FindingSeverity.MAJOR,
        )
        summary = self.manager.get_finding_summary()
        assert summary["critical"] == 1
        assert summary["major"] == 2

    def test_to_dict(self) -> None:
        self.manager.create_audit(
            audit_id="a1",
            name="Audit 1",
            audit_type="internal",
            scope="All systems",
        )
        data = self.manager.to_dict()
        assert "audits" in data
        assert "finding_summary" in data


# ============================================================================
# Regulatory Reporting Tests
# ============================================================================


class TestRegulatoryReporter:
    """Tests for RegulatoryReporter."""

    def setup_method(self) -> None:
        self.reporter = RegulatoryReporter()

    def test_create_report(self) -> None:
        report = self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        assert report.id == "rr1"
        assert report.status == "draft"
        assert len(self.reporter) == 1

    def test_get_report(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        found = self.reporter.get_report("rr1")
        assert found is not None
        assert found.name == "GDPR Annual Report"

    def test_get_report_not_found(self) -> None:
        assert self.reporter.get_report("nonexistent") is None

    def test_update_report(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        updated = self.reporter.update_report("rr1", name="Updated Report")
        assert updated is not None
        assert updated.name == "Updated Report"

    def test_update_report_not_found(self) -> None:
        assert self.reporter.update_report("nonexistent", name="New") is None

    def test_submit_report(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        submitted = self.reporter.submit_report(
            "rr1", submitted_by="Alice", reference_number="REF-001"
        )
        assert submitted is not None
        assert submitted.status == "submitted"
        assert submitted.submission_date is not None
        assert submitted.submitted_by == "Alice"
        assert submitted.reference_number == "REF-001"

    def test_submit_report_not_found(self) -> None:
        result = self.reporter.submit_report("nonexistent", submitted_by="Alice")
        assert result is None

    def test_accept_report(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        self.reporter.submit_report("rr1", submitted_by="Alice")
        accepted = self.reporter.accept_report("rr1")
        assert accepted is not None
        assert accepted.status == "accepted"

    def test_reject_report(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        self.reporter.submit_report("rr1", submitted_by="Alice")
        rejected = self.reporter.reject_report("rr1", notes="Incomplete data")
        assert rejected is not None
        assert rejected.status == "rejected"
        assert "Incomplete data" in rejected.notes

    def test_add_attachment(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        updated = self.reporter.add_attachment("rr1", "report.pdf")
        assert updated is not None
        assert "report.pdf" in updated.attachments

    def test_add_attachment_not_found(self) -> None:
        assert self.reporter.add_attachment("nonexistent", "report.pdf") is None

    def test_remove_attachment(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
            attachments=["file1.pdf", "file2.pdf"],
        )
        updated = self.reporter.remove_attachment("rr1", 0)
        assert updated is not None
        assert len(updated.attachments) == 1
        assert updated.attachments[0] == "file2.pdf"

    def test_remove_attachment_invalid_index(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
            attachments=["file1.pdf"],
        )
        updated = self.reporter.remove_attachment("rr1", 5)
        assert updated is not None
        assert len(updated.attachments) == 1

    def test_remove_report(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="GDPR Annual Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        assert self.reporter.remove_report("rr1") is True
        assert len(self.reporter) == 0

    def test_remove_report_not_found(self) -> None:
        assert self.reporter.remove_report("nonexistent") is False

    def test_list_reports_no_filter(self) -> None:
        for i in range(3):
            self.reporter.create_report(
                report_id=f"rr{i}",
                name=f"Report {i}",
                regulation="GDPR",
                reporting_period=f"2024-Q{i+1}",
            )
        assert len(self.reporter.list_reports()) == 3

    def test_list_reports_filter_by_status(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="Report 1",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        self.reporter.create_report(
            report_id="rr2",
            name="Report 2",
            regulation="GDPR",
            reporting_period="2024-Q2",
        )
        self.reporter.submit_report("rr1", submitted_by="Alice")
        results = self.reporter.list_reports(status="submitted")
        assert len(results) == 1
        assert results[0].id == "rr1"

    def test_list_reports_filter_by_regulation(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="Report 1",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        self.reporter.create_report(
            report_id="rr2",
            name="Report 2",
            regulation="HIPAA",
            reporting_period="2024-Q1",
        )
        results = self.reporter.list_reports(regulation="GDPR")
        assert len(results) == 1
        assert results[0].id == "rr1"

    def test_list_reports_filter_by_period(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="Report 1",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        self.reporter.create_report(
            report_id="rr2",
            name="Report 2",
            regulation="GDPR",
            reporting_period="2024-Q2",
        )
        results = self.reporter.list_reports(reporting_period="2024-Q1")
        assert len(results) == 1
        assert results[0].id == "rr1"

    def test_get_reports_by_regulation(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="Report 1",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        self.reporter.create_report(
            report_id="rr2",
            name="Report 2",
            regulation="HIPAA",
            reporting_period="2024-Q1",
        )
        self.reporter.create_report(
            report_id="rr3",
            name="Report 3",
            regulation="GDPR",
            reporting_period="2024-Q2",
        )
        grouped = self.reporter.get_reports_by_regulation()
        assert len(grouped["GDPR"]) == 2
        assert len(grouped["HIPAA"]) == 1

    def test_get_reports_by_status(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="Report 1",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        self.reporter.create_report(
            report_id="rr2",
            name="Report 2",
            regulation="GDPR",
            reporting_period="2024-Q2",
        )
        self.reporter.submit_report("rr1", submitted_by="Alice")
        grouped = self.reporter.get_reports_by_status()
        assert len(grouped["draft"]) == 1
        assert len(grouped["submitted"]) == 1

    def test_get_overdue_reports(self) -> None:
        past = date.today() - timedelta(days=10)
        self.reporter.create_report(
            report_id="rr1",
            name="Report 1",
            regulation="GDPR",
            reporting_period="2024-Q1",
            due_date=past,
        )
        self.reporter.create_report(
            report_id="rr2",
            name="Report 2",
            regulation="GDPR",
            reporting_period="2024-Q2",
            due_date=past,
        )
        self.reporter.submit_report("rr1", submitted_by="Alice")
        overdue = self.reporter.get_overdue_reports()
        assert len(overdue) == 1
        assert overdue[0].id == "rr2"

    def test_get_upcoming_deadlines(self) -> None:
        soon = date.today() + timedelta(days=15)
        later = date.today() + timedelta(days=60)
        self.reporter.create_report(
            report_id="rr1",
            name="Report 1",
            regulation="GDPR",
            reporting_period="2024-Q1",
            due_date=soon,
        )
        self.reporter.create_report(
            report_id="rr2",
            name="Report 2",
            regulation="GDPR",
            reporting_period="2024-Q2",
            due_date=later,
        )
        upcoming = self.reporter.get_upcoming_deadlines(days=30)
        assert len(upcoming) == 1
        assert upcoming[0].id == "rr1"

    def test_get_submission_rate(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="Report 1",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        self.reporter.create_report(
            report_id="rr2",
            name="Report 2",
            regulation="GDPR",
            reporting_period="2024-Q2",
        )
        self.reporter.submit_report("rr1", submitted_by="Alice")
        assert self.reporter.get_submission_rate() == 50.0

    def test_get_submission_rate_empty(self) -> None:
        assert self.reporter.get_submission_rate() == 0.0

    def test_to_dict(self) -> None:
        self.reporter.create_report(
            report_id="rr1",
            name="Report 1",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        data = self.reporter.to_dict()
        assert "reports" in data
        assert "by_status" in data
        assert "submission_rate" in data


# ============================================================================
# Model Tests
# ============================================================================


class TestModels:
    """Tests for data models."""

    def test_compliance_item_to_dict(self) -> None:
        item = ComplianceItem(
            id="c1",
            name="Test",
            description="Test description",
            regulation="GDPR",
            category="data_protection",
            status=ComplianceStatus.COMPLIANT,
        )
        data = item.to_dict()
        assert data["id"] == "c1"
        assert data["status"] == "compliant"

    def test_policy_to_dict(self) -> None:
        policy = Policy(
            id="p1",
            title="Test Policy",
            version="1.0",
            content="Test content",
            category="test",
        )
        data = policy.to_dict()
        assert data["id"] == "p1"
        assert data["title"] == "Test Policy"

    def test_risk_assessment_to_dict(self) -> None:
        risk = RiskAssessment(
            id="r1",
            name="Test Risk",
            description="Test description",
            category="test",
            likelihood=3,
            impact=4,
        )
        data = risk.to_dict()
        assert data["id"] == "r1"
        assert data["risk_score"] == 12
        assert data["risk_level"] == "high"

    def test_audit_to_dict(self) -> None:
        audit = Audit(
            id="a1",
            name="Test Audit",
            audit_type="internal",
            scope="Test scope",
        )
        data = audit.to_dict()
        assert data["id"] == "a1"
        assert data["finding_count"] == 0

    def test_audit_finding_to_dict(self) -> None:
        finding = AuditFinding(
            id="f1",
            title="Test Finding",
            description="Test description",
            severity=FindingSeverity.MAJOR,
        )
        data = finding.to_dict()
        assert data["id"] == "f1"
        assert data["severity"] == "major"

    def test_regulatory_report_to_dict(self) -> None:
        report = RegulatoryReport(
            id="rr1",
            name="Test Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
        )
        data = report.to_dict()
        assert data["id"] == "rr1"
        assert data["is_overdue"] is False

    def test_regulatory_report_is_overdue(self) -> None:
        past = date.today() - timedelta(days=10)
        report = RegulatoryReport(
            id="rr1",
            name="Test Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
            due_date=past,
        )
        assert report.is_overdue is True

    def test_regulatory_report_not_overdue_when_submitted(self) -> None:
        past = date.today() - timedelta(days=10)
        report = RegulatoryReport(
            id="rr1",
            name="Test Report",
            regulation="GDPR",
            reporting_period="2024-Q1",
            due_date=past,
            status="submitted",
        )
        assert report.is_overdue is False

    def test_risk_level_calculation(self) -> None:
        # Critical: 5*5=25
        risk = RiskAssessment(
            id="r1",
            name="Test",
            description="Test",
            category="test",
            likelihood=5,
            impact=5,
        )
        assert risk.risk_level == RiskLevel.CRITICAL

        # High: 4*3=12
        risk2 = RiskAssessment(
            id="r2",
            name="Test",
            description="Test",
            category="test",
            likelihood=4,
            impact=3,
        )
        assert risk2.risk_level == RiskLevel.HIGH

        # Medium: 2*3=6
        risk3 = RiskAssessment(
            id="r3",
            name="Test",
            description="Test",
            category="test",
            likelihood=2,
            impact=3,
        )
        assert risk3.risk_level == RiskLevel.MEDIUM

        # Low: 1*2=2
        risk4 = RiskAssessment(
            id="r4",
            name="Test",
            description="Test",
            category="test",
            likelihood=1,
            impact=2,
        )
        assert risk4.risk_level == RiskLevel.LOW

        # Negligible: 1*1=1
        risk5 = RiskAssessment(
            id="r5",
            name="Test",
            description="Test",
            category="test",
            likelihood=1,
            impact=1,
        )
        assert risk5.risk_level == RiskLevel.NEGLIGIBLE
