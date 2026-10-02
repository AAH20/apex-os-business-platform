"""Contract approval workflow feature."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .models import Contract, ContractStatus


class ApprovalAction(str, Enum):
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    CANCEL = "cancel"
    DELEGATE = "delegate"


class ApprovalStepStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"
    DELEGATED = "delegated"


@dataclass
class ApprovalStep:
    """A single step in an approval workflow."""
    approver_id: str
    approver_name: str
    role: str  # e.g., "manager", "legal", "finance", "executive"
    order: int = 0
    status: ApprovalStepStatus = ApprovalStepStatus.PENDING
    action: Optional[ApprovalAction] = None
    comments: str = ""
    action_at: Optional[datetime] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "role": self.role,
            "order": self.order,
            "status": self.status.value,
            "action": self.action.value if self.action else None,
            "comments": self.comments,
            "action_at": self.action_at.isoformat() if self.action_at else None,
        }


@dataclass
class ApprovalWorkflow:
    """An approval workflow for a contract."""
    contract_id: str
    steps: list[ApprovalStep] = field(default_factory=list)
    current_step_index: int = 0
    is_complete: bool = False
    is_rejected: bool = False
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def current_step(self) -> Optional[ApprovalStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status in (ApprovalStepStatus.APPROVED, ApprovalStepStatus.SKIPPED))
        return completed / len(self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "is_complete": self.is_complete,
            "is_rejected": self.is_rejected,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ApprovalWorkflowBuilder:
    """Builder for creating approval workflows."""

    def __init__(self, contract_id: str) -> None:
        self.contract_id = contract_id
        self._steps: list[ApprovalStep] = []

    def add_step(self, approver_id: str, approver_name: str, role: str) -> ApprovalWorkflowBuilder:
        """Add an approval step."""
        step = ApprovalStep(
            approver_id=approver_id,
            approver_name=approver_name,
            role=role,
            order=len(self._steps),
        )
        self._steps.append(step)
        return self

    def add_steps(self, steps: list[tuple[str, str, str]]) -> ApprovalWorkflowBuilder:
        """Add multiple steps at once. Each tuple is (approver_id, approver_name, role)."""
        for approver_id, approver_name, role in steps:
            self.add_step(approver_id, approver_name, role)
        return self

    def build(self) -> ApprovalWorkflow:
        """Build the workflow."""
        return ApprovalWorkflow(
            contract_id=self.contract_id,
            steps=self._steps,
        )


class ApprovalManager:
    """Manages contract approval workflows."""

    def __init__(self) -> None:
        self._workflows: dict[str, ApprovalWorkflow] = {}

    def create_workflow(self, workflow: ApprovalWorkflow) -> ApprovalWorkflow:
        """Register a workflow."""
        self._workflows[workflow.id] = workflow
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[ApprovalWorkflow]:
        """Retrieve a workflow by ID."""
        return self._workflows.get(workflow_id)

    def get_workflow_for_contract(self, contract_id: str) -> Optional[ApprovalWorkflow]:
        """Get the workflow associated with a contract."""
        for wf in self._workflows.values():
            if wf.contract_id == contract_id:
                return wf
        return None

    def submit_for_approval(self, contract: Contract, workflow: ApprovalWorkflow) -> Contract:
        """Submit a contract for approval."""
        if contract.status != ContractStatus.DRAFT:
            raise ValueError(f"Cannot submit contract with status {contract.status.value} for approval.")
        contract.status = ContractStatus.PENDING_APPROVAL
        contract.approval_history.append({
            "action": ApprovalAction.SUBMIT.value,
            "timestamp": datetime.utcnow().isoformat(),
            "workflow_id": workflow.id,
        })
        workflow.submitted_at = datetime.utcnow()
        self._workflows[workflow.id] = workflow
        return contract

    def approve(self, workflow_id: str, approver_id: str, comments: str = "") -> ApprovalWorkflow:
        """Approve the current step."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow {workflow_id} not found.")
        if workflow.is_complete or workflow.is_rejected:
            raise ValueError("Workflow is already complete or rejected.")

        step = workflow.current_step
        if step is None:
            raise ValueError("No current step in workflow.")
        if step.approver_id != approver_id:
            raise ValueError(f"User {approver_id} is not the current approver.")

        step.status = ApprovalStepStatus.APPROVED
        step.action = ApprovalAction.APPROVE
        step.comments = comments
        step.action_at = datetime.utcnow()

        if workflow.current_step_index < len(workflow.steps) - 1:
            workflow.current_step_index += 1
        else:
            workflow.is_complete = True
            workflow.completed_at = datetime.utcnow()

        return workflow

    def reject(self, workflow_id: str, approver_id: str, comments: str = "") -> ApprovalWorkflow:
        """Reject the current step."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow {workflow_id} not found.")
        if workflow.is_complete or workflow.is_rejected:
            raise ValueError("Workflow is already complete or rejected.")

        step = workflow.current_step
        if step is None:
            raise ValueError("No current step in workflow.")
        if step.approver_id != approver_id:
            raise ValueError(f"User {approver_id} is not the current approver.")

        step.status = ApprovalStepStatus.REJECTED
        step.action = ApprovalAction.REJECT
        step.comments = comments
        step.action_at = datetime.utcnow()
        workflow.is_rejected = True
        workflow.completed_at = datetime.utcnow()

        return workflow

    def request_changes(self, workflow_id: str, approver_id: str, comments: str) -> ApprovalWorkflow:
        """Request changes on the current step."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow {workflow_id} not found.")
        if workflow.is_complete or workflow.is_rejected:
            raise ValueError("Workflow is already complete or rejected.")

        step = workflow.current_step
        if step is None:
            raise ValueError("No current step in workflow.")
        if step.approver_id != approver_id:
            raise ValueError(f"User {approver_id} is not the current approver.")

        step.status = ApprovalStepStatus.PENDING
        step.action = ApprovalAction.REQUEST_CHANGES
        step.comments = comments
        step.action_at = datetime.utcnow()
        # Reset to first step for rework
        workflow.current_step_index = 0
        for s in workflow.steps:
            if s.status != ApprovalStepStatus.SKIPPED:
                s.status = ApprovalStepStatus.PENDING
                s.action = None
                s.action_at = None

        return workflow

    def cancel(self, workflow_id: str, requester_id: str) -> ApprovalWorkflow:
        """Cancel the workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow {workflow_id} not found.")
        if workflow.is_complete or workflow.is_rejected:
            raise ValueError("Workflow is already complete or rejected.")
        workflow.is_rejected = True
        workflow.completed_at = datetime.utcnow()
        return workflow

    def delegate(self, workflow_id: str, from_approver_id: str, to_approver_id: str, to_approver_name: str) -> ApprovalWorkflow:
        """Delegate the current step to another approver."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow {workflow_id} not found.")
        if workflow.is_complete or workflow.is_rejected:
            raise ValueError("Workflow is already complete or rejected.")

        step = workflow.current_step
        if step is None:
            raise ValueError("No current step in workflow.")
        if step.approver_id != from_approver_id:
            raise ValueError(f"User {from_approver_id} is not the current approver.")

        step.status = ApprovalStepStatus.DELEGATED
        step.action = ApprovalAction.DELEGATE
        step.action_at = datetime.utcnow()

        new_step = ApprovalStep(
            approver_id=to_approver_id,
            approver_name=to_approver_name,
            role=step.role,
            order=workflow.current_step_index,
        )
        workflow.steps[workflow.current_step_index] = new_step

        return workflow

    def finalize_approval(self, contract: Contract, workflow: ApprovalWorkflow) -> Contract:
        """Apply the final approval state to the contract."""
        if workflow.is_rejected:
            contract.status = ContractStatus.REJECTED
        elif workflow.is_complete:
            contract.status = ContractStatus.APPROVED
            contract.approved_at = datetime.utcnow()
            # Set approved_by from the last approver
            if workflow.steps:
                last_approver = workflow.steps[-1]
                contract.approved_by = last_approver.approver_id
        contract.approval_history.append({
            "action": "finalize",
            "workflow_id": workflow.id,
            "timestamp": datetime.utcnow().isoformat(),
            "result": contract.status.value,
        })
        return contract

    def activate_contract(self, contract: Contract) -> Contract:
        """Activate an approved contract."""
        if contract.status != ContractStatus.APPROVED:
            raise ValueError(f"Cannot activate contract with status {contract.status.value}.")
        contract.status = ContractStatus.ACTIVE
        return contract
