"""Contract creation feature."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from .models import Contract, ContractParty, ContractStatus, ContractType


class ContractValidationError(Exception):
    """Raised when contract creation validation fails."""


@dataclass
class ContractDraft:
    """A draft contract before it is finalized."""
    title: str = ""
    contract_type: ContractType = ContractType.OTHER
    parties: list[ContractParty] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    value: float = 0.0
    currency: str = "USD"
    description: str = ""
    terms: list[str] = field(default_factory=list)
    clauses: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    auto_renew: bool = False
    renewal_notice_days: int = 30
    created_by: str = ""

    def validate(self) -> list[str]:
        """Validate the draft and return a list of error messages."""
        errors: list[str] = []
        if not self.title or len(self.title.strip()) < 3:
            errors.append("Title must be at least 3 characters long.")
        if not self.parties:
            errors.append("At least one party is required.")
        if self.start_date is None:
            errors.append("Start date is required.")
        if self.end_date is None:
            errors.append("End date is required.")
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            errors.append("End date must be after start date.")
        if self.value < 0:
            errors.append("Value cannot be negative.")
        if not self.currency or len(self.currency) != 3:
            errors.append("Currency must be a 3-letter code.")
        if self.renewal_notice_days < 0:
            errors.append("Renewal notice days cannot be negative.")
        return errors


class ContractCreator:
    """Creates and manages contract drafts."""

    def __init__(self) -> None:
        self._drafts: dict[str, ContractDraft] = {}

    def create_draft(
        self,
        title: str,
        contract_type: ContractType,
        parties: list[ContractParty],
        start_date: date,
        end_date: date,
        value: float = 0.0,
        currency: str = "USD",
        description: str = "",
        terms: Optional[list[str]] = None,
        clauses: Optional[dict[str, str]] = None,
        tags: Optional[list[str]] = None,
        auto_renew: bool = False,
        renewal_notice_days: int = 30,
        created_by: str = "",
    ) -> ContractDraft:
        """Create a new contract draft."""
        draft = ContractDraft(
            title=title,
            contract_type=contract_type,
            parties=list(parties),
            start_date=start_date,
            end_date=end_date,
            value=value,
            currency=currency,
            description=description,
            terms=list(terms) if terms else [],
            clauses=dict(clauses) if clauses else {},
            tags=list(tags) if tags else [],
            auto_renew=auto_renew,
            renewal_notice_days=renewal_notice_days,
            created_by=created_by,
        )
        draft_id = str(uuid.uuid4())
        self._drafts[draft_id] = draft
        return draft

    def get_draft(self, draft_id: str) -> Optional[ContractDraft]:
        """Retrieve a draft by ID."""
        return self._drafts.get(draft_id)

    def update_draft(self, draft_id: str, **kwargs: Any) -> ContractDraft:
        """Update draft fields."""
        draft = self._drafts.get(draft_id)
        if draft is None:
            raise ContractValidationError(f"Draft {draft_id} not found.")
        for key, value in kwargs.items():
            if hasattr(draft, key):
                setattr(draft, key, value)
        return draft

    def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft. Returns True if deleted."""
        if draft_id in self._drafts:
            del self._drafts[draft_id]
            return True
        return False

    def finalize(self, draft_id: str) -> Contract:
        """Convert a draft into a Contract."""
        draft = self._drafts.get(draft_id)
        if draft is None:
            raise ContractValidationError(f"Draft {draft_id} not found.")
        errors = draft.validate()
        if errors:
            raise ContractValidationError("; ".join(errors))
        contract = Contract(
            title=draft.title,
            contract_type=draft.contract_type,
            parties=draft.parties,
            start_date=draft.start_date,
            end_date=draft.end_date,
            value=draft.value,
            currency=draft.currency,
            status=ContractStatus.DRAFT,
            description=draft.description,
            terms=draft.terms,
            clauses=draft.clauses,
            tags=draft.tags,
            auto_renew=draft.auto_renew,
            renewal_notice_days=draft.renewal_notice_days,
            created_by=draft.created_by,
        )
        del self._drafts[draft_id]
        return contract

    def quick_create(
        self,
        title: str,
        contract_type: ContractType,
        parties: list[ContractParty],
        start_date: date,
        end_date: date,
        value: float = 0.0,
        currency: str = "USD",
        description: str = "",
        created_by: str = "",
    ) -> Contract:
        """Create a contract directly without a draft step."""
        draft = self.create_draft(
            title=title,
            contract_type=contract_type,
            parties=parties,
            start_date=start_date,
            end_date=end_date,
            value=value,
            currency=currency,
            description=description,
            created_by=created_by,
        )
        # Use a temporary ID for the draft
        temp_id = str(uuid.uuid4())
        self._drafts[temp_id] = draft
        return self.finalize(temp_id)
