"""Core data models for the contract management system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional


class ContractStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    RENEWED = "renewed"
    REJECTED = "rejected"


class ContractType(str, Enum):
    SERVICE = "service"
    EMPLOYMENT = "employment"
    NDA = "nda"
    SALES = "sales"
    LEASE = "lease"
    LICENSING = "licensing"
    PARTNERSHIP = "partnership"
    MAINTENANCE = "maintenance"
    CONSULTING = "consulting"
    OTHER = "other"


@dataclass
class ContractParty:
    """A party involved in a contract."""
    name: str
    role: str  # e.g., "client", "vendor", "employee"
    contact_email: str = ""
    contact_phone: str = ""
    address: str = ""
    tax_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Contract:
    """Represents a business contract."""
    title: str
    contract_type: ContractType
    parties: list[ContractParty]
    start_date: date
    end_date: date
    value: float = 0.0
    currency: str = "USD"
    status: ContractStatus = ContractStatus.DRAFT
    description: str = ""
    terms: list[str] = field(default_factory=list)
    clauses: dict[str, str] = field(default_factory=dict)
    attachments: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    parent_contract_id: Optional[str] = None  # For renewals
    renewal_count: int = 0
    auto_renew: bool = False
    renewal_notice_days: int = 30
    approval_history: list[dict[str, Any]] = field(default_factory=list)
    compliance_checks: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    approved_by: str = ""
    approved_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    termination_reason: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def is_active(self) -> bool:
        return self.status == ContractStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        return date.today() > self.end_date

    @property
    def days_until_expiry(self) -> int:
        return (self.end_date - date.today()).days

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "contract_type": self.contract_type.value,
            "parties": [
                {
                    "name": p.name,
                    "role": p.role,
                    "contact_email": p.contact_email,
                    "contact_phone": p.contact_phone,
                    "address": p.address,
                    "tax_id": p.tax_id,
                    "metadata": p.metadata,
                }
                for p in self.parties
            ],
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "value": self.value,
            "currency": self.currency,
            "status": self.status.value,
            "description": self.description,
            "terms": self.terms,
            "clauses": self.clauses,
            "attachments": self.attachments,
            "tags": self.tags,
            "parent_contract_id": self.parent_contract_id,
            "renewal_count": self.renewal_count,
            "auto_renew": self.auto_renew,
            "renewal_notice_days": self.renewal_notice_days,
            "approval_history": self.approval_history,
            "compliance_checks": self.compliance_checks,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
            "termination_reason": self.termination_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Contract:
        parties = [ContractParty(**p) for p in data.get("parties", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data["title"],
            contract_type=ContractType(data["contract_type"]),
            parties=parties,
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(data["end_date"]),
            value=data.get("value", 0.0),
            currency=data.get("currency", "USD"),
            status=ContractStatus(data.get("status", "draft")),
            description=data.get("description", ""),
            terms=data.get("terms", []),
            clauses=data.get("clauses", {}),
            attachments=data.get("attachments", []),
            tags=data.get("tags", []),
            parent_contract_id=data.get("parent_contract_id"),
            renewal_count=data.get("renewal_count", 0),
            auto_renew=data.get("auto_renew", False),
            renewal_notice_days=data.get("renewal_notice_days", 30),
            approval_history=data.get("approval_history", []),
            compliance_checks=data.get("compliance_checks", []),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
            created_by=data.get("created_by", ""),
            approved_by=data.get("approved_by", ""),
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
            terminated_at=datetime.fromisoformat(data["terminated_at"]) if data.get("terminated_at") else None,
            termination_reason=data.get("termination_reason", ""),
        )
