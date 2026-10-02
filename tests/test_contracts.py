"""Comprehensive tests for the contract management system."""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from apex_os_bp.contracts.models import (
    Contract,
    ContractParty,
    ContractStatus,
    ContractType,
)
from apex_os_bp.contracts.creation import (
    ContractCreator,
    ContractDraft,
    ContractValidationError,
)
from apex_os_bp.contracts.templates import (
    ContractTemplate,
    TemplateManager,
)
from apex_os_bp.contracts.approval import (
    ApprovalAction,
    ApprovalManager,
    ApprovalStep,
    ApprovalStepStatus,
    ApprovalWorkflow,
    ApprovalWorkflowBuilder,
)
from apex_os_bp.contracts.renewal import (
    RenewalManager,
    RenewalRecord,
    RenewalNotice,
    RenewalStatus,
)
from apex_os_bp.contracts.compliance import (
    ComplianceChecker,
    ComplianceReport,
    ComplianceRule,
    ComplianceSeverity,
    ComplianceStatus,
    ComplianceCheckResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_party(name: str, role: str, email: str = "") -> ContractParty:
    return ContractParty(
        name=name,
        role=role,
        contact_email=email or f"{name.lower().replace(' ', '.')}@example.com",
    )


def _make_contract(
    title: str = "Test Contract",
    contract_type: ContractType = ContractType.SERVICE,
    parties: list[ContractParty] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    value: float = 10000.0,
    status: ContractStatus = ContractStatus.DRAFT,
    auto_renew: bool = False,
    renewal_notice_days: int = 30,
    terms: list[str] | None = None,
    clauses: dict[str, str] | None = None,
) -> Contract:
    today = date.today()
    return Contract(
        title=title,
        contract_type=contract_type,
        parties=parties or [_make_party("Acme Corp", "client"), _make_party("Globex Inc", "vendor")],
        start_date=start_date or today,
        end_date=end_date or today + timedelta(days=365),
        value=value,
        status=status,
        auto_renew=auto_renew,
        renewal_notice_days=renewal_notice_days,
        terms=terms or [],
        clauses=clauses or {},
    )


# ===========================================================================
# CONTRACT CREATION TESTS
# ===========================================================================

class TestContractCreation(unittest.TestCase):
    """Tests for contract creation feature."""

    def setUp(self) -> None:
        self.creator = ContractCreator()

    def test_create_draft_basic(self) -> None:
        draft = self.creator.create_draft(
            title="Service Agreement",
            contract_type=ContractType.SERVICE,
            parties=[_make_party("Acme", "client")],
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
        )
        self.assertEqual(draft.title, "Service Agreement")
        self.assertEqual(draft.contract_type, ContractType.SERVICE)
        self.assertEqual(len(draft.parties), 1)

    def test_create_draft_with_all_fields(self) -> None:
        draft = self.creator.create_draft(
            title="Full Contract",
            contract_type=ContractType.SALES,
            parties=[_make_party("A", "client"), _make_party("B", "vendor")],
            start_date=date(2026, 1, 1),
            end_date=date(2027, 1, 1),
            value=50000.0,
            currency="EUR",
            description="A comprehensive sales agreement",
            terms=["Payment net 30", "Delivery FOB"],
            clauses={"termination": "30 days notice"},
            tags=["sales", "2026"],
            auto_renew=True,
            renewal_notice_days=60,
            created_by="user123",
        )
        self.assertEqual(draft.value, 50000.0)
        self.assertEqual(draft.currency, "EUR")
        self.assertEqual(len(draft.terms), 2)
        self.assertIn("termination", draft.clauses)
        self.assertTrue(draft.auto_renew)
        self.assertEqual(draft.renewal_notice_days, 60)
        self.assertEqual(draft.created_by, "user123")

    def test_draft_validation_valid(self) -> None:
        draft = ContractDraft(
            title="Valid Contract",
            contract_type=ContractType.SERVICE,
            parties=[_make_party("A", "client")],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            value=1000.0,
        )
        errors = draft.validate()
        self.assertEqual(errors, [])

    def test_draft_validation_short_title(self) -> None:
        draft = ContractDraft(title="AB")
        errors = draft.validate()
        self.assertTrue(any("Title" in e for e in errors))

    def test_draft_validation_no_parties(self) -> None:
        draft = ContractDraft(
            title="Valid Title",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        errors = draft.validate()
        self.assertTrue(any("party" in e.lower() for e in errors))

    def test_draft_validation_end_before_start(self) -> None:
        draft = ContractDraft(
            title="Valid Title",
            parties=[_make_party("A", "client")],
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1),
        )
        errors = draft.validate()
        self.assertTrue(any("End date" in e for e in errors))

    def test_draft_validation_negative_value(self) -> None:
        draft = ContractDraft(
            title="Valid Title",
            parties=[_make_party("A", "client")],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            value=-100,
        )
        errors = draft.validate()
        self.assertTrue(any("negative" in e.lower() for e in errors))

    def test_draft_validation_invalid_currency(self) -> None:
        draft = ContractDraft(
            title="Valid Title",
            parties=[_make_party("A", "client")],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            currency="US",
        )
        errors = draft.validate()
        self.assertTrue(any("Currency" in e for e in errors))

    def test_finalize_draft_success(self) -> None:
        draft = self.creator.create_draft(
            title="Finalizable Contract",
            contract_type=ContractType.SERVICE,
            parties=[_make_party("A", "client")],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        # Get the draft ID (only one in the manager)
        draft_id = list(self.creator._drafts.keys())[0]
        contract = self.creator.finalize(draft_id)
        self.assertIsInstance(contract, Contract)
        self.assertEqual(contract.title, "Finalizable Contract")
        self.assertEqual(contract.status, ContractStatus.DRAFT)

    def test_finalize_invalid_draft_raises(self) -> None:
        draft = self.creator.create_draft(
            title="AB",  # Too short
            contract_type=ContractType.SERVICE,
            parties=[_make_party("A", "client")],
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1),  # End before start
        )
        draft_id = list(self.creator._drafts.keys())[0]
        with self.assertRaises(ContractValidationError):
            self.creator.finalize(draft_id)

    def test_finalize_nonexistent_draft_raises(self) -> None:
        with self.assertRaises(ContractValidationError):
            self.creator.finalize("nonexistent-id")

    def test_quick_create(self) -> None:
        contract = self.creator.quick_create(
            title="Quick Contract",
            contract_type=ContractType.CONSULTING,
            parties=[_make_party("A", "client"), _make_party("B", "vendor")],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            value=25000.0,
            created_by="admin",
        )
        self.assertIsInstance(contract, Contract)
        self.assertEqual(contract.title, "Quick Contract")
        self.assertEqual(contract.status, ContractStatus.DRAFT)
        self.assertEqual(contract.created_by, "admin")

    def test_update_draft(self) -> None:
        draft = self.creator.create_draft(
            title="Original",
            contract_type=ContractType.SERVICE,
            parties=[_make_party("A", "client")],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        draft_id = list(self.creator._drafts.keys())[0]
        updated = self.creator.update_draft(draft_id, title="Updated", value=9999.0)
        self.assertEqual(updated.title, "Updated")
        self.assertEqual(updated.value, 9999.0)

    def test_delete_draft(self) -> None:
        self.creator.create_draft(
            title="To Delete",
            contract_type=ContractType.SERVICE,
            parties=[_make_party("A", "client")],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        draft_id = list(self.creator._drafts.keys())[0]
        result = self.creator.delete_draft(draft_id)
        self.assertTrue(result)
        self.assertIsNone(self.creator.get_draft(draft_id))

    def test_delete_nonexistent_draft(self) -> None:
        result = self.creator.delete_draft("nonexistent")
        self.assertFalse(result)


# ===========================================================================
# CONTRACT TEMPLATES TESTS
# ===========================================================================

class TestContractTemplates(unittest.TestCase):
    """Tests for contract templates feature."""

    def setUp(self) -> None:
        self.manager = TemplateManager()

    def test_create_template(self) -> None:
        template = self.manager.create_template(
            name="Standard NDA",
            contract_type=ContractType.NDA,
            description="Standard non-disclosure agreement",
            default_terms=["Confidentiality obligation", "Non-compete for 1 year"],
            default_clauses={"confidentiality": "Parties agree to keep information confidential"},
            default_duration_days=730,
            required_party_roles=["disclosing_party", "receiving_party"],
        )
        self.assertEqual(template.name, "Standard NDA")
        self.assertEqual(template.contract_type, ContractType.NDA)
        self.assertTrue(template.is_active)
        self.assertEqual(len(template.default_terms), 2)

    def test_get_template(self) -> None:
        template = self.manager.create_template(
            name="Test Template",
            contract_type=ContractType.SERVICE,
        )
        fetched = self.manager.get_template(template.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Test Template")

    def test_get_nonexistent_template(self) -> None:
        result = self.manager.get_template("nonexistent")
        self.assertIsNone(result)

    def test_get_templates_by_type(self) -> None:
        self.manager.create_template(name="NDA Template", contract_type=ContractType.NDA)
        self.manager.create_template(name="Service Template", contract_type=ContractType.SERVICE)
        self.manager.create_template(name="Another NDA", contract_type=ContractType.NDA)

        nda_templates = self.manager.get_templates_by_type(ContractType.NDA)
        self.assertEqual(len(nda_templates), 2)

    def test_list_templates_active_only(self) -> None:
        t1 = self.manager.create_template(name="Active", contract_type=ContractType.SERVICE)
        t2 = self.manager.create_template(name="Inactive", contract_type=ContractType.SERVICE)
        self.manager.deactivate_template(t2.id)

        active = self.manager.list_templates(include_inactive=False)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].name, "Active")

        all_templates = self.manager.list_templates(include_inactive=True)
        self.assertEqual(len(all_templates), 2)

    def test_update_template(self) -> None:
        template = self.manager.create_template(
            name="Original",
            contract_type=ContractType.SERVICE,
        )
        updated = self.manager.update_template(template.id, name="Updated", default_value=5000.0)
        self.assertEqual(updated.name, "Updated")
        self.assertEqual(updated.default_value, 5000.0)

    def test_delete_template(self) -> None:
        template = self.manager.create_template(
            name="To Delete",
            contract_type=ContractType.SERVICE,
        )
        result = self.manager.delete_template(template.id)
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_template(template.id))

    def test_deactivate_template(self) -> None:
        template = self.manager.create_template(
            name="To Deactivate",
            contract_type=ContractType.SERVICE,
        )
        deactivated = self.manager.deactivate_template(template.id)
        self.assertFalse(deactivated.is_active)

    def test_clone_template(self) -> None:
        original = self.manager.create_template(
            name="Original Template",
            contract_type=ContractType.SERVICE,
            default_terms=["Term 1", "Term 2"],
            default_clauses={"clause1": "Value 1"},
        )
        cloned = self.manager.clone_template(original.id, "Cloned Template")
        self.assertEqual(cloned.name, "Cloned Template")
        self.assertNotEqual(cloned.id, original.id)
        self.assertEqual(cloned.default_terms, original.default_terms)
        self.assertEqual(cloned.default_clauses, original.default_clauses)

    def test_apply_template(self) -> None:
        template = self.manager.create_template(
            name="Service Template",
            contract_type=ContractType.SERVICE,
            default_terms=["Payment net 30"],
            default_clauses={"liability": "Limited to contract value"},
            default_value=10000.0,
            default_currency="USD",
            default_duration_days=365,
            required_party_roles=["client", "vendor"],
        )
        result = self.manager.apply_template(
            template_id=template.id,
            title="New Service Contract",
            parties=[_make_party("Client A", "client"), _make_party("Vendor B", "vendor")],
            start_date=date(2026, 1, 1),
        )
        self.assertEqual(result["title"], "New Service Contract")
        self.assertEqual(result["value"], 10000.0)
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(result["end_date"], date(2027, 1, 1))
        self.assertIn("Payment net 30", result["terms"])

    def test_apply_template_with_overrides(self) -> None:
        template = self.manager.create_template(
            name="Template",
            contract_type=ContractType.SERVICE,
            default_value=1000.0,
            default_currency="USD",
        )
        result = self.manager.apply_template(
            template_id=template.id,
            title="Custom Contract",
            parties=[_make_party("A", "client")],
            start_date=date(2026, 1, 1),
            value=50000.0,
            currency="EUR",
            extra_terms=["Custom term"],
        )
        self.assertEqual(result["value"], 50000.0)
        self.assertEqual(result["currency"], "EUR")
        self.assertIn("Custom term", result["terms"])

    def test_apply_inactive_template_raises(self) -> None:
        template = self.manager.create_template(
            name="Inactive",
            contract_type=ContractType.SERVICE,
        )
        self.manager.deactivate_template(template.id)
        with self.assertRaises(ValueError):
            self.manager.apply_template(
                template_id=template.id,
                title="Test",
                parties=[_make_party("A", "client")],
                start_date=date(2026, 1, 1),
            )

    def test_validate_parties_against_template(self) -> None:
        template = self.manager.create_template(
            name="Template",
            contract_type=ContractType.SERVICE,
            required_party_roles=["client", "vendor"],
        )
        # Valid parties
        errors = self.manager.validate_parties_against_template(
            template.id,
            [_make_party("A", "client"), _make_party("B", "vendor")],
        )
        self.assertEqual(errors, [])

        # Missing role
        errors = self.manager.validate_parties_against_template(
            template.id,
            [_make_party("A", "client")],
        )
        self.assertTrue(len(errors) > 0)

    def test_template_to_dict(self) -> None:
        template = self.manager.create_template(
            name="Dict Test",
            contract_type=ContractType.SERVICE,
            default_terms=["Term 1"],
        )
        data = template.to_dict()
        self.assertEqual(data["name"], "Dict Test")
        self.assertEqual(data["contract_type"], "service")
        self.assertIn("id", data)

    def test_template_from_dict(self) -> None:
        data = {
            "id": "test-id",
            "name": "From Dict",
            "contract_type": "nda",
            "description": "Test",
            "default_terms": ["Term 1"],
            "default_clauses": {"c1": "v1"},
            "default_value": 5000.0,
            "default_currency": "EUR",
            "default_duration_days": 180,
            "default_auto_renew": True,
            "default_renewal_notice_days": 45,
            "required_party_roles": ["party_a"],
            "tags": ["tag1"],
            "is_active": True,
            "created_at": "2026-01-01",
        }
        template = ContractTemplate.from_dict(data)
        self.assertEqual(template.id, "test-id")
        self.assertEqual(template.name, "From Dict")
        self.assertEqual(template.contract_type, ContractType.NDA)
        self.assertEqual(template.default_value, 5000.0)


# ===========================================================================
# CONTRACT APPROVAL TESTS
# ===========================================================================

class TestContractApproval(unittest.TestCase):
    """Tests for contract approval workflow feature."""

    def setUp(self) -> None:
        self.manager = ApprovalManager()

    def _build_workflow(self, contract_id: str) -> ApprovalWorkflow:
        return (
            ApprovalWorkflowBuilder(contract_id)
            .add_step("user1", "Alice", "manager")
            .add_step("user2", "Bob", "legal")
            .add_step("user3", "Charlie", "finance")
            .build()
        )

    def test_create_workflow(self) -> None:
        workflow = self._build_workflow("contract-1")
        self.manager.create_workflow(workflow)
        fetched = self.manager.get_workflow(workflow.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(len(fetched.steps), 3)

    def test_workflow_progress(self) -> None:
        workflow = self._build_workflow("contract-1")
        self.manager.create_workflow(workflow)
        self.assertEqual(workflow.progress, 0.0)

        # Approve first step
        self.manager.approve(workflow.id, "user1")
        workflow = self.manager.get_workflow(workflow.id)
        self.assertAlmostEqual(workflow.progress, 1 / 3)

    def test_submit_for_approval(self) -> None:
        contract = _make_contract(status=ContractStatus.DRAFT)
        workflow = self._build_workflow(contract.id)
        result = self.manager.submit_for_approval(contract, workflow)
        self.assertEqual(result.status, ContractStatus.PENDING_APPROVAL)

    def test_submit_non_draft_raises(self) -> None:
        contract = _make_contract(status=ContractStatus.ACTIVE)
        workflow = self._build_workflow(contract.id)
        with self.assertRaises(ValueError):
            self.manager.submit_for_approval(contract, workflow)

    def test_approve_step(self) -> None:
        workflow = self._build_workflow("contract-1")
        self.manager.create_workflow(workflow)
        result = self.manager.approve(workflow.id, "user1", "Looks good")
        step = result.steps[0]
        self.assertEqual(step.status, ApprovalStepStatus.APPROVED)
        self.assertEqual(step.action, ApprovalAction.APPROVE)
        self.assertEqual(step.comments, "Looks good")
        self.assertEqual(result.current_step_index, 1)

    def test_approve_wrong_user_raises(self) -> None:
        workflow = self._build_workflow("contract-1")
        self.manager.create_workflow(workflow)
        with self.assertRaises(ValueError):
            self.manager.approve(workflow.id, "wrong_user")

    def test_reject_step(self) -> None:
        workflow = self._build_workflow("contract-1")
        self.manager.create_workflow(workflow)
        result = self.manager.reject(workflow.id, "user1", "Not acceptable")
        self.assertTrue(result.is_rejected)
        step = result.steps[0]
        self.assertEqual(step.status, ApprovalStepStatus.REJECTED)
        self.assertEqual(step.action, ApprovalAction.REJECT)

    def test_request_changes(self) -> None:
        workflow = self._build_workflow("contract-1")
        self.manager.create_workflow(workflow)
        # Approve first step
        self.manager.approve(workflow.id, "user1")
        # Request changes on second step
        result = self.manager.request_changes(workflow.id, "user2", "Please revise clause 3")
        self.assertEqual(result.current_step_index, 0)
        # All non-skipped steps should be reset to pending
        for step in result.steps:
            self.assertEqual(step.status, ApprovalStepStatus.PENDING)

    def test_delegate_step(self) -> None:
        workflow = self._build_workflow("contract-1")
        self.manager.create_workflow(workflow)
        result = self.manager.delegate(workflow.id, "user1", "user4", "Dave")
        # The step at index 0 is replaced with the new delegate
        step = result.steps[0]
        self.assertEqual(step.status, ApprovalStepStatus.PENDING)
        self.assertEqual(step.approver_id, "user4")
        self.assertEqual(step.approver_name, "Dave")

    def test_cancel_workflow(self) -> None:
        workflow = self._build_workflow("contract-1")
        self.manager.create_workflow(workflow)
        result = self.manager.cancel(workflow.id, "user1")
        self.assertTrue(result.is_rejected)

    def test_full_approval_flow(self) -> None:
        contract = _make_contract(status=ContractStatus.DRAFT)
        workflow = self._build_workflow(contract.id)
        self.manager.create_workflow(workflow)

        # Submit
        contract = self.manager.submit_for_approval(contract, workflow)
        self.assertEqual(contract.status, ContractStatus.PENDING_APPROVAL)

        # Approve all steps
        self.manager.approve(workflow.id, "user1")
        self.manager.approve(workflow.id, "user2")
        self.manager.approve(workflow.id, "user3")

        workflow = self.manager.get_workflow(workflow.id)
        self.assertTrue(workflow.is_complete)
        self.assertEqual(workflow.progress, 1.0)

        # Finalize
        contract = self.manager.finalize_approval(contract, workflow)
        self.assertEqual(contract.status, ContractStatus.APPROVED)
        self.assertIsNotNone(contract.approved_at)

    def test_finalize_rejected(self) -> None:
        contract = _make_contract(status=ContractStatus.DRAFT)
        workflow = self._build_workflow(contract.id)
        self.manager.create_workflow(workflow)
        contract = self.manager.submit_for_approval(contract, workflow)
        self.manager.reject(workflow.id, "user1", "Rejected")
        contract = self.manager.finalize_approval(contract, workflow)
        self.assertEqual(contract.status, ContractStatus.REJECTED)

    def test_activate_contract(self) -> None:
        contract = _make_contract(status=ContractStatus.APPROVED)
        result = self.manager.activate_contract(contract)
        self.assertEqual(result.status, ContractStatus.ACTIVE)

    def test_activate_non_approved_raises(self) -> None:
        contract = _make_contract(status=ContractStatus.DRAFT)
        with self.assertRaises(ValueError):
            self.manager.activate_contract(contract)

    def test_approve_completed_workflow_raises(self) -> None:
        workflow = self._build_workflow("contract-1")
        self.manager.create_workflow(workflow)
        self.manager.approve(workflow.id, "user1")
        self.manager.approve(workflow.id, "user2")
        self.manager.approve(workflow.id, "user3")
        with self.assertRaises(ValueError):
            self.manager.approve(workflow.id, "user1")

    def test_get_workflow_for_contract(self) -> None:
        workflow = self._build_workflow("contract-123")
        self.manager.create_workflow(workflow)
        found = self.manager.get_workflow_for_contract("contract-123")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, workflow.id)

    def test_approval_workflow_builder_add_steps(self) -> None:
        workflow = (
            ApprovalWorkflowBuilder("c1")
            .add_steps([
                ("u1", "Alice", "manager"),
                ("u2", "Bob", "legal"),
            ])
            .build()
        )
        self.assertEqual(len(workflow.steps), 2)
        self.assertEqual(workflow.steps[0].order, 0)
        self.assertEqual(workflow.steps[1].order, 1)

    def test_approval_step_to_dict(self) -> None:
        step = ApprovalStep(
            approver_id="u1",
            approver_name="Alice",
            role="manager",
            order=0,
        )
        data = step.to_dict()
        self.assertEqual(data["approver_id"], "u1")
        self.assertEqual(data["status"], "pending")

    def test_approval_workflow_to_dict(self) -> None:
        workflow = self._build_workflow("c1")
        data = workflow.to_dict()
        self.assertEqual(data["contract_id"], "c1")
        self.assertEqual(len(data["steps"]), 3)
        self.assertIn("is_complete", data)


# ===========================================================================
# CONTRACT RENEWAL TESTS
# ===========================================================================

class TestContractRenewal(unittest.TestCase):
    """Tests for contract renewal feature."""

    def setUp(self) -> None:
        self.manager = RenewalManager()

    def test_check_renewal_status_not_due(self) -> None:
        contract = _make_contract(
            end_date=date.today() + timedelta(days=180),
            renewal_notice_days=30,
        )
        status = self.manager.check_renewal_status(contract)
        self.assertEqual(status, RenewalStatus.NOT_DUE)

    def test_check_renewal_status_due_soon(self) -> None:
        contract = _make_contract(
            end_date=date.today() + timedelta(days=15),
            renewal_notice_days=30,
        )
        status = self.manager.check_renewal_status(contract)
        self.assertEqual(status, RenewalStatus.DUE_SOON)

    def test_check_renewal_status_overdue(self) -> None:
        contract = _make_contract(
            end_date=date.today() - timedelta(days=5),
            renewal_notice_days=30,
        )
        status = self.manager.check_renewal_status(contract)
        self.assertEqual(status, RenewalStatus.OVERDUE)

    def test_is_renewal_due_true(self) -> None:
        contract = _make_contract(
            end_date=date.today() + timedelta(days=10),
            renewal_notice_days=30,
        )
        self.assertTrue(self.manager.is_renewal_due(contract))

    def test_is_renewal_due_false(self) -> None:
        contract = _make_contract(
            end_date=date.today() + timedelta(days=90),
            renewal_notice_days=30,
        )
        self.assertFalse(self.manager.is_renewal_due(contract))

    def test_create_renewal_notice(self) -> None:
        contract = _make_contract(
            end_date=date.today() + timedelta(days=15),
            renewal_notice_days=30,
        )
        notice = self.manager.create_renewal_notice(
            contract,
            recipients=["admin@example.com"],
        )
        self.assertEqual(notice.contract_id, contract.id)
        self.assertEqual(notice.status, RenewalStatus.DUE_SOON)
        self.assertEqual(notice.days_remaining, 15)
        self.assertFalse(notice.sent)

    def test_send_renewal_notice(self) -> None:
        contract = _make_contract(
            end_date=date.today() + timedelta(days=15),
            renewal_notice_days=30,
        )
        notice = self.manager.create_renewal_notice(contract)
        sent_notice = self.manager.send_renewal_notice(notice.id)
        self.assertTrue(sent_notice.sent)
        self.assertIsNotNone(sent_notice.sent_at)

    def test_renew_contract(self) -> None:
        contract = _make_contract(
            status=ContractStatus.ACTIVE,
            end_date=date.today() + timedelta(days=10),
            value=10000.0,
        )
        renewed = self.manager.renew_contract(
            contract,
            new_duration_days=365,
            new_value=12000.0,
            renewed_by="admin",
            notes="Annual renewal",
        )
        self.assertEqual(renewed.status, ContractStatus.ACTIVE)
        self.assertEqual(renewed.parent_contract_id, contract.id)
        self.assertEqual(renewed.renewal_count, 1)
        self.assertEqual(renewed.value, 12000.0)
        self.assertEqual(renewed.end_date, contract.end_date + timedelta(days=365))
        # Original should be marked as renewed
        self.assertEqual(contract.status, ContractStatus.RENEWED)

    def test_renew_contract_default_duration(self) -> None:
        contract = _make_contract(
            status=ContractStatus.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        renewed = self.manager.renew_contract(contract)
        self.assertEqual(renewed.duration_days, contract.duration_days)

    def test_renew_non_active_contract_raises(self) -> None:
        contract = _make_contract(status=ContractStatus.DRAFT)
        with self.assertRaises(ValueError):
            self.manager.renew_contract(contract)

    def test_decline_renewal(self) -> None:
        contract = _make_contract(status=ContractStatus.ACTIVE)
        result = self.manager.decline_renewal(contract, "No longer needed")
        self.assertEqual(result.status, ContractStatus.EXPIRED)
        self.assertIn("No longer needed", result.termination_reason)

    def test_get_renewal_history(self) -> None:
        contract = _make_contract(status=ContractStatus.ACTIVE)
        renewed1 = self.manager.renew_contract(contract, renewed_by="user1")
        renewed2 = self.manager.renew_contract(renewed1, renewed_by="user2")

        history = self.manager.get_renewal_history(contract.id)
        self.assertEqual(len(history), 2)

    def test_list_notices_filter_by_contract(self) -> None:
        c1 = _make_contract(title="Contract 1", end_date=date.today() + timedelta(days=10))
        c2 = _make_contract(title="Contract 2", end_date=date.today() + timedelta(days=20))
        self.manager.create_renewal_notice(c1)
        self.manager.create_renewal_notice(c2)

        notices = self.manager.list_notices(contract_id=c1.id)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].contract_title, "Contract 1")

    def test_list_notices_filter_by_status(self) -> None:
        c1 = _make_contract(end_date=date.today() + timedelta(days=10))
        c2 = _make_contract(end_date=date.today() + timedelta(days=60))
        self.manager.create_renewal_notice(c1)
        self.manager.create_renewal_notice(c2)

        due_notices = self.manager.list_notices(status=RenewalStatus.DUE_SOON)
        self.assertEqual(len(due_notices), 1)

    def test_setup_auto_renewal(self) -> None:
        contract = _make_contract()
        result = self.manager.setup_auto_renewal(contract, notice_days=45)
        self.assertTrue(result.auto_renew)
        self.assertEqual(result.renewal_notice_days, 45)

    def test_cancel_auto_renewal(self) -> None:
        contract = _make_contract(auto_renew=True)
        result = self.manager.cancel_auto_renewal(contract)
        self.assertFalse(result.auto_renew)

    def test_get_renewal_forecast(self) -> None:
        contracts = [
            _make_contract(end_date=date.today() + timedelta(days=30), status=ContractStatus.ACTIVE),
            _make_contract(end_date=date.today() + timedelta(days=60), status=ContractStatus.ACTIVE),
            _make_contract(end_date=date.today() + timedelta(days=120), status=ContractStatus.ACTIVE),
            _make_contract(end_date=date.today() + timedelta(days=10), status=ContractStatus.DRAFT),
        ]
        forecast = self.manager.get_renewal_forecast(contracts, days_ahead=90)
        # Only active contracts within 90 days
        self.assertEqual(len(forecast), 2)
        self.assertEqual(forecast[0]["days_remaining"], 30)
        self.assertEqual(forecast[1]["days_remaining"], 60)

    def test_renewal_record_to_dict(self) -> None:
        record = RenewalRecord(
            original_contract_id="c1",
            new_contract_id="c2",
            renewal_date=date(2026, 1, 1),
            previous_end_date=date(2025, 12, 31),
            new_end_date=date(2026, 12, 31),
        )
        data = record.to_dict()
        self.assertEqual(data["original_contract_id"], "c1")
        self.assertEqual(data["new_contract_id"], "c2")

    def test_renewal_notice_to_dict(self) -> None:
        notice = RenewalNotice(
            contract_id="c1",
            contract_title="Test",
            expiry_date=date(2026, 12, 31),
            notice_date=date(2026, 12, 1),
            days_remaining=30,
            status=RenewalStatus.DUE_SOON,
        )
        data = notice.to_dict()
        self.assertEqual(data["contract_id"], "c1")
        self.assertEqual(data["status"], "due_soon")


# ===========================================================================
# CONTRACT COMPLIANCE TESTS
# ===========================================================================

class TestContractCompliance(unittest.TestCase):
    """Tests for contract compliance feature."""

    def setUp(self) -> None:
        self.checker = ComplianceChecker()

    def test_add_and_get_rule(self) -> None:
        rule = ComplianceRule(
            name="Test Rule",
            description="A test rule",
            severity=ComplianceSeverity.WARNING,
            check_function=lambda c: True,
        )
        self.checker.add_rule(rule)
        fetched = self.checker.get_rule(rule.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Test Rule")

    def test_remove_rule(self) -> None:
        rule = ComplianceRule(
            name="Removable",
            description="Will be removed",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        )
        self.checker.add_rule(rule)
        result = self.checker.remove_rule(rule.id)
        self.assertTrue(result)
        self.assertIsNone(self.checker.get_rule(rule.id))

    def test_remove_nonexistent_rule(self) -> None:
        result = self.checker.remove_rule("nonexistent")
        self.assertFalse(result)

    def test_list_rules_active_only(self) -> None:
        r1 = ComplianceRule(
            name="Active",
            description="Active rule",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        )
        r2 = ComplianceRule(
            name="Inactive",
            description="Inactive rule",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
            is_active=False,
        )
        self.checker.add_rule(r1)
        self.checker.add_rule(r2)

        active = self.checker.list_rules(active_only=True)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].name, "Active")

    def test_list_rules_filter_by_severity(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Warning Rule",
            description="Warning",
            severity=ComplianceSeverity.WARNING,
            check_function=lambda c: True,
        ))
        self.checker.add_rule(ComplianceRule(
            name="Critical Rule",
            description="Critical",
            severity=ComplianceSeverity.CRITICAL,
            check_function=lambda c: True,
        ))

        warnings = self.checker.list_rules(severity=ComplianceSeverity.WARNING)
        self.assertEqual(len(warnings), 1)

    def test_list_rules_filter_by_type(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="NDA Rule",
            description="NDA only",
            severity=ComplianceSeverity.VIOLATION,
            check_function=lambda c: True,
            applicable_types=[ContractType.NDA],
        ))
        self.checker.add_rule(ComplianceRule(
            name="All Rule",
            description="All types",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        ))

        nda_rules = self.checker.list_rules(contract_type=ContractType.NDA)
        self.assertEqual(len(nda_rules), 2)

        service_rules = self.checker.list_rules(contract_type=ContractType.SERVICE)
        self.assertEqual(len(service_rules), 1)

    def test_check_contract_compliant(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Always Pass",
            description="Always passes",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        ))
        contract = _make_contract()
        report = self.checker.check_contract(contract)
        self.assertEqual(report.overall_status, ComplianceStatus.COMPLIANT)
        self.assertEqual(report.compliance_score, 100.0)

    def test_check_contract_non_compliant(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Always Fail",
            description="Always fails",
            severity=ComplianceSeverity.VIOLATION,
            check_function=lambda c: False,
        ))
        contract = _make_contract()
        report = self.checker.check_contract(contract)
        self.assertEqual(report.overall_status, ComplianceStatus.NON_COMPLIANT)
        self.assertEqual(report.compliance_score, 0.0)

    def test_check_contract_with_specific_rules(self) -> None:
        r1 = ComplianceRule(
            name="Pass",
            description="Passes",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        )
        r2 = ComplianceRule(
            name="Fail",
            description="Fails",
            severity=ComplianceSeverity.WARNING,
            check_function=lambda c: False,
        )
        self.checker.add_rule(r1)
        self.checker.add_rule(r2)

        contract = _make_contract()
        report = self.checker.check_contract(contract, rule_ids=[r1.id])
        self.assertEqual(report.overall_status, ComplianceStatus.COMPLIANT)
        self.assertEqual(len(report.results), 1)

    def test_compliance_report_counts(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Pass",
            description="Passes",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        ))
        self.checker.add_rule(ComplianceRule(
            name="Fail",
            description="Fails",
            severity=ComplianceSeverity.WARNING,
            check_function=lambda c: False,
        ))
        contract = _make_contract()
        report = self.checker.check_contract(contract)
        self.assertEqual(report.passed_count, 1)
        self.assertEqual(report.failed_count, 1)
        self.assertEqual(report.compliance_score, 50.0)

    def test_get_report(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Rule",
            description="Test",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        ))
        contract = _make_contract()
        report = self.checker.check_contract(contract)
        fetched = self.checker.get_report(report.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, report.id)

    def test_list_reports_filter_by_contract(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Rule",
            description="Test",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        ))
        c1 = _make_contract(title="C1")
        c2 = _make_contract(title="C2")
        self.checker.check_contract(c1)
        self.checker.check_contract(c2)

        reports = self.checker.list_reports(contract_id=c1.id)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].contract_title, "C1")

    def test_list_reports_filter_by_status(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Fail Rule",
            description="Fails",
            severity=ComplianceSeverity.VIOLATION,
            check_function=lambda c: False,
        ))
        c1 = _make_contract()
        self.checker.check_contract(c1)

        non_compliant = self.checker.list_reports(status=ComplianceStatus.NON_COMPLIANT)
        self.assertEqual(len(non_compliant), 1)

    def test_get_contract_compliance_history(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Rule",
            description="Test",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        ))
        contract = _make_contract()
        self.checker.check_contract(contract)
        self.checker.check_contract(contract)

        history = self.checker.get_contract_compliance_history(contract.id)
        self.assertEqual(len(history), 2)

    def test_create_builtin_rules(self) -> None:
        rules = self.checker.create_builtin_rules()
        self.assertTrue(len(rules) >= 5)
        # Verify some key rules exist
        rule_names = {r.name for r in rules}
        self.assertIn("minimum_parties", rule_names)
        self.assertIn("positive_value", rule_names)
        self.assertIn("nda_confidentiality_clause", rule_names)

    def test_builtin_rule_minimum_parties(self) -> None:
        rules = self.checker.create_builtin_rules()
        rule = next(r for r in rules if r.name == "minimum_parties")

        # Contract with 2 parties should pass
        contract = _make_contract()
        self.assertTrue(rule.evaluate(contract))

        # Contract with 1 party should fail
        contract.parties = [_make_party("Only One", "client")]
        self.assertFalse(rule.evaluate(contract))

    def test_builtin_rule_positive_value(self) -> None:
        rules = self.checker.create_builtin_rules()
        rule = next(r for r in rules if r.name == "positive_value")

        contract = _make_contract(value=100.0)
        self.assertTrue(rule.evaluate(contract))

        contract.value = 0.0
        self.assertFalse(rule.evaluate(contract))

    def test_builtin_rule_nda_confidentiality(self) -> None:
        rules = self.checker.create_builtin_rules()
        rule = next(r for r in rules if r.name == "nda_confidentiality_clause")

        # NDA with confidentiality clause
        contract = _make_contract(
            contract_type=ContractType.NDA,
            clauses={"confidentiality": "Secret stuff"},
        )
        self.assertTrue(rule.evaluate(contract))

        # NDA without confidentiality clause
        contract.clauses = {}
        self.assertFalse(rule.evaluate(contract))

    def test_builtin_rule_end_date_future(self) -> None:
        rules = self.checker.create_builtin_rules()
        rule = next(r for r in rules if r.name == "end_date_future")

        contract = _make_contract(end_date=date.today() + timedelta(days=30))
        self.assertTrue(rule.evaluate(contract))

        contract.end_date = date.today() - timedelta(days=1)
        self.assertFalse(rule.evaluate(contract))

    def test_builtin_rule_high_value_approval(self) -> None:
        rules = self.checker.create_builtin_rules()
        rule = next(r for r in rules if r.name == "high_value_approval")

        # High value but approved
        contract = _make_contract(value=200000.0, status=ContractStatus.APPROVED)
        self.assertTrue(rule.evaluate(contract))

        # High value and draft (not approved)
        contract.status = ContractStatus.DRAFT
        self.assertFalse(rule.evaluate(contract))

        # Low value and draft (should pass)
        contract.value = 50000.0
        self.assertTrue(rule.evaluate(contract))

    def test_builtin_rule_max_duration(self) -> None:
        rules = self.checker.create_builtin_rules()
        rule = next(r for r in rules if r.name == "max_duration")

        contract = _make_contract(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.assertTrue(rule.evaluate(contract))

        contract.end_date = date(2031, 1, 1)  # 5+ years
        self.assertFalse(rule.evaluate(contract))

    def test_compliance_summary(self) -> None:
        self.checker.create_builtin_rules()
        contracts = [
            _make_contract(title="C1", value=100.0, status=ContractStatus.ACTIVE),
            _make_contract(title="C2", value=200.0, status=ContractStatus.ACTIVE),
        ]
        summary = self.checker.get_compliance_summary(contracts)
        self.assertEqual(summary["total_contracts"], 2)
        self.assertIn("average_score", summary)
        self.assertIn("compliant", summary)

    def test_compliance_summary_empty(self) -> None:
        summary = self.checker.get_compliance_summary([])
        self.assertEqual(summary["total_contracts"], 0)
        self.assertEqual(summary["average_score"], 0.0)

    def test_compliance_check_result_to_dict(self) -> None:
        result = ComplianceCheckResult(
            rule_id="r1",
            rule_name="Test Rule",
            severity=ComplianceSeverity.WARNING,
            passed=False,
            message="Failed",
        )
        data = result.to_dict()
        self.assertEqual(data["rule_id"], "r1")
        self.assertFalse(data["passed"])

    def test_compliance_report_to_dict(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Rule",
            description="Test",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        ))
        contract = _make_contract()
        report = self.checker.check_contract(contract)
        data = report.to_dict()
        self.assertEqual(data["contract_id"], contract.id)
        self.assertEqual(data["overall_status"], "compliant")
        self.assertIn("results", data)

    def test_rule_evaluate_with_non_applicable_type(self) -> None:
        rule = ComplianceRule(
            name="NDA Only",
            description="Only for NDAs",
            severity=ComplianceSeverity.VIOLATION,
            check_function=lambda c: False,  # Would fail if evaluated
            applicable_types=[ContractType.NDA],
        )
        # Service contract should pass (rule doesn't apply)
        contract = _make_contract(contract_type=ContractType.SERVICE)
        self.assertTrue(rule.evaluate(contract))

    def test_contract_stores_compliance_checks(self) -> None:
        self.checker.add_rule(ComplianceRule(
            name="Rule",
            description="Test",
            severity=ComplianceSeverity.INFO,
            check_function=lambda c: True,
        ))
        contract = _make_contract()
        self.assertEqual(len(contract.compliance_checks), 0)
        self.checker.check_contract(contract)
        self.assertEqual(len(contract.compliance_checks), 1)
        self.checker.check_contract(contract)
        self.assertEqual(len(contract.compliance_checks), 2)


# ===========================================================================
# INTEGRATION TESTS
# ===========================================================================

class TestContractIntegration(unittest.TestCase):
    """Integration tests across multiple contract features."""

    def test_full_contract_lifecycle(self) -> None:
        """Test the complete lifecycle: create -> template -> approve -> renew."""
        # 1. Create
        creator = ContractCreator()
        contract = creator.quick_create(
            title="Lifecycle Test",
            contract_type=ContractType.SERVICE,
            parties=[_make_party("Client", "client"), _make_party("Vendor", "vendor")],
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            value=50000.0,
        )
        self.assertEqual(contract.status, ContractStatus.DRAFT)

        # 2. Approve
        approval_mgr = ApprovalManager()
        workflow = (
            ApprovalWorkflowBuilder(contract.id)
            .add_step("mgr1", "Manager", "manager")
            .add_step("legal1", "Legal", "legal")
            .build()
        )
        approval_mgr.create_workflow(workflow)
        contract = approval_mgr.submit_for_approval(contract, workflow)
        approval_mgr.approve(workflow.id, "mgr1")
        approval_mgr.approve(workflow.id, "legal1")
        contract = approval_mgr.finalize_approval(contract, workflow)
        self.assertEqual(contract.status, ContractStatus.APPROVED)

        # 3. Activate
        contract = approval_mgr.activate_contract(contract)
        self.assertEqual(contract.status, ContractStatus.ACTIVE)

        # 4. Compliance check
        checker = ComplianceChecker()
        checker.create_builtin_rules()
        report = checker.check_contract(contract)
        self.assertIsNotNone(report)

        # 5. Renew
        renewal_mgr = RenewalManager()
        renewed = renewal_mgr.renew_contract(contract, renewed_by="admin")
        self.assertEqual(renewed.status, ContractStatus.ACTIVE)
        self.assertEqual(renewed.parent_contract_id, contract.id)
        self.assertEqual(renewed.renewal_count, 1)

    def test_template_to_contract_workflow(self) -> None:
        """Test using a template to create a contract and approve it."""
        template_mgr = TemplateManager()
        template = template_mgr.create_template(
            name="Standard Service",
            contract_type=ContractType.SERVICE,
            default_terms=["Payment net 30", "SLA 99.9%"],
            default_clauses={"termination": "30 days notice"},
            default_value=25000.0,
            default_duration_days=365,
            required_party_roles=["client", "vendor"],
        )

        params = template_mgr.apply_template(
            template_id=template.id,
            title="New Service Deal",
            parties=[_make_party("Acme", "client"), _make_party("Globex", "vendor")],
            start_date=date.today(),
        )

        creator = ContractCreator()
        contract = creator.quick_create(
            title=params["title"],
            contract_type=params["contract_type"],
            parties=params["parties"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            value=params["value"],
        )
        self.assertEqual(contract.value, 25000.0)
        # quick_create doesn't carry terms from template params; verify via draft path
        draft = creator.create_draft(
            title=params["title"],
            contract_type=params["contract_type"],
            parties=params["parties"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            value=params["value"],
            terms=params["terms"],
        )
        self.assertIn("Payment net 30", draft.terms)

    def test_compliance_blocks_approval(self) -> None:
        """Test that compliance checking can be integrated into approval."""
        checker = ComplianceChecker()
        checker.create_builtin_rules()

        # Create a contract that will fail compliance (no terms)
        contract = _make_contract(terms=[])
        report = checker.check_contract(contract)
        # Should have some non-compliance due to missing terms
        self.assertGreater(report.failed_count, 0)

    def test_renewal_with_compliance(self) -> None:
        """Test renewing a contract and checking compliance of the renewed contract."""
        checker = ComplianceChecker()
        checker.create_builtin_rules()
        renewal_mgr = RenewalManager()

        contract = _make_contract(
            status=ContractStatus.ACTIVE,
            end_date=date.today() + timedelta(days=5),
            terms=["Standard term"],
            clauses={"termination": "30 days"},
        )
        renewed = renewal_mgr.renew_contract(contract)
        report = checker.check_contract(renewed)
        self.assertIsNotNone(report)
        # Renewed contract should inherit terms and clauses
        self.assertIn("Standard term", renewed.terms)


if __name__ == "__main__":
    unittest.main()
