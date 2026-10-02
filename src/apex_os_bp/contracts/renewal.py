"""Contract renewal feature."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Optional

from .models import Contract, ContractParty, ContractStatus, ContractType


class RenewalStatus(str, Enum):
    NOT_DUE = "not_due"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"
    RENEWED = "renewed"
    DECLINED = "declined"


@dataclass
class RenewalRecord:
    """A record of a contract renewal."""
    original_contract_id: str
    new_contract_id: str
    renewal_date: date
    previous_end_date: date
    new_end_date: date
    renewed_by: str = ""
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "original_contract_id": self.original_contract_id,
            "new_contract_id": self.new_contract_id,
            "renewal_date": self.renewal_date.isoformat(),
            "previous_end_date": self.previous_end_date.isoformat(),
            "new_end_date": self.new_end_date.isoformat(),
            "renewed_by": self.renewed_by,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RenewalNotice:
    """A notice that a contract is due for renewal."""
    contract_id: str
    contract_title: str
    expiry_date: date
    notice_date: date
    days_remaining: int
    status: RenewalStatus
    recipients: list[str] = field(default_factory=list)
    sent: bool = False
    sent_at: Optional[datetime] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "contract_title": self.contract_title,
            "expiry_date": self.expiry_date.isoformat(),
            "notice_date": self.notice_date.isoformat(),
            "days_remaining": self.days_remaining,
            "status": self.status.value,
            "recipients": self.recipients,
            "sent": self.sent,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


class RenewalManager:
    """Manages contract renewals."""

    def __init__(self) -> None:
        self._renewal_records: dict[str, RenewalRecord] = {}
        self._notices: dict[str, RenewalNotice] = {}

    def check_renewal_status(self, contract: Contract, as_of: Optional[date] = None) -> RenewalStatus:
        """Check the renewal status of a contract."""
        if contract.status in (ContractStatus.RENEWED, ContractStatus.TERMINATED, ContractStatus.EXPIRED):
            return RenewalStatus.RENEWED if contract.status == ContractStatus.RENEWED else RenewalStatus.DECLINED

        today = as_of or date.today()
        days_remaining = (contract.end_date - today).days

        if days_remaining < 0:
            return RenewalStatus.OVERDUE
        elif days_remaining <= contract.renewal_notice_days:
            return RenewalStatus.DUE_SOON
        else:
            return RenewalStatus.NOT_DUE

    def is_renewal_due(self, contract: Contract, as_of: Optional[date] = None) -> bool:
        """Check if a contract is due for renewal."""
        status = self.check_renewal_status(contract, as_of)
        return status in (RenewalStatus.DUE_SOON, RenewalStatus.OVERDUE)

    def create_renewal_notice(
        self,
        contract: Contract,
        recipients: Optional[list[str]] = None,
        as_of: Optional[date] = None,
    ) -> RenewalNotice:
        """Create a renewal notice for a contract."""
        today = as_of or date.today()
        days_remaining = (contract.end_date - today).days
        status = self.check_renewal_status(contract, today)

        notice = RenewalNotice(
            contract_id=contract.id,
            contract_title=contract.title,
            expiry_date=contract.end_date,
            notice_date=today,
            days_remaining=days_remaining,
            status=status,
            recipients=recipients or [],
        )
        self._notices[notice.id] = notice
        return notice

    def send_renewal_notice(self, notice_id: str) -> RenewalNotice:
        """Mark a renewal notice as sent."""
        notice = self._notices.get(notice_id)
        if notice is None:
            raise ValueError(f"Notice {notice_id} not found.")
        notice.sent = True
        notice.sent_at = datetime.utcnow()
        return notice

    def renew_contract(
        self,
        contract: Contract,
        new_duration_days: Optional[int] = None,
        new_value: Optional[float] = None,
        renewed_by: str = "",
        notes: str = "",
        as_of: Optional[date] = None,
    ) -> Contract:
        """Renew a contract, creating a new contract based on the original."""
        if contract.status not in (ContractStatus.ACTIVE, ContractStatus.EXPIRED, ContractStatus.RENEWED):
            raise ValueError(f"Cannot renew contract with status {contract.status.value}.")

        today = as_of or date.today()
        duration = new_duration_days or contract.duration_days
        new_start = contract.end_date
        new_end = date.fromordinal(new_start.toordinal() + duration)

        renewed_contract = Contract(
            title=contract.title,
            contract_type=contract.contract_type,
            parties=[ContractParty(**vars(p)) for p in contract.parties],
            start_date=new_start,
            end_date=new_end,
            value=new_value if new_value is not None else contract.value,
            currency=contract.currency,
            status=ContractStatus.ACTIVE,
            description=contract.description,
            terms=list(contract.terms),
            clauses=dict(contract.clauses),
            tags=list(contract.tags),
            parent_contract_id=contract.id,
            renewal_count=contract.renewal_count + 1,
            auto_renew=contract.auto_renew,
            renewal_notice_days=contract.renewal_notice_days,
            created_by=renewed_by,
        )

        # Update original contract
        contract.status = ContractStatus.RENEWED
        contract.terminated_at = today
        contract.termination_reason = "Renewed"

        # Create renewal record
        record = RenewalRecord(
            original_contract_id=contract.id,
            new_contract_id=renewed_contract.id,
            renewal_date=today,
            previous_end_date=contract.end_date,
            new_end_date=new_end,
            renewed_by=renewed_by,
            notes=notes,
        )
        self._renewal_records[record.id] = record

        return renewed_contract

    def decline_renewal(self, contract: Contract, reason: str = "", as_of: Optional[date] = None) -> Contract:
        """Decline renewal of a contract."""
        today = as_of or date.today()
        contract.status = ContractStatus.EXPIRED
        contract.terminated_at = today
        contract.termination_reason = f"Renewal declined: {reason}" if reason else "Renewal declined"
        return contract

    def get_renewal_history(self, contract_id: str) -> list[RenewalRecord]:
        """Get the renewal history for a contract (including its children)."""
        records: list[RenewalRecord] = []
        to_process = [contract_id]
        visited: set[str] = set()

        while to_process:
            current_id = to_process.pop()
            if current_id in visited:
                continue
            visited.add(current_id)
            for record in self._renewal_records.values():
                if record.original_contract_id == current_id:
                    records.append(record)
                    to_process.append(record.new_contract_id)

        return sorted(records, key=lambda r: r.renewal_date)

    def get_notice(self, notice_id: str) -> Optional[RenewalNotice]:
        """Retrieve a renewal notice by ID."""
        return self._notices.get(notice_id)

    def list_notices(
        self,
        contract_id: Optional[str] = None,
        status: Optional[RenewalStatus] = None,
        sent: Optional[bool] = None,
    ) -> list[RenewalNotice]:
        """List renewal notices with optional filters."""
        notices = list(self._notices.values())
        if contract_id:
            notices = [n for n in notices if n.contract_id == contract_id]
        if status:
            notices = [n for n in notices if n.status == status]
        if sent is not None:
            notices = [n for n in notices if n.sent == sent]
        return notices

    def get_renewal_record(self, record_id: str) -> Optional[RenewalRecord]:
        """Retrieve a renewal record by ID."""
        return self._renewal_records.get(record_id)

    def list_renewal_records(self, contract_id: Optional[str] = None) -> list[RenewalRecord]:
        """List renewal records, optionally filtered by contract."""
        records = list(self._renewal_records.values())
        if contract_id:
            records = [r for r in records if r.original_contract_id == contract_id or r.new_contract_id == contract_id]
        return records

    def setup_auto_renewal(self, contract: Contract, notice_days: Optional[int] = None) -> Contract:
        """Enable auto-renewal for a contract."""
        contract.auto_renew = True
        if notice_days is not None:
            contract.renewal_notice_days = notice_days
        return contract

    def cancel_auto_renewal(self, contract: Contract) -> Contract:
        """Disable auto-renewal for a contract."""
        contract.auto_renew = False
        return contract

    def get_renewal_forecast(
        self,
        contracts: list[Contract],
        days_ahead: int = 90,
        as_of: Optional[date] = None,
    ) -> list[dict[str, Any]]:
        """Get a forecast of upcoming renewals."""
        today = as_of or date.today()
        forecast: list[dict[str, Any]] = []
        for contract in contracts:
            if contract.status not in (ContractStatus.ACTIVE, ContractStatus.RENEWED):
                continue
            days_remaining = (contract.end_date - today).days
            if 0 <= days_remaining <= days_ahead:
                forecast.append({
                    "contract_id": contract.id,
                    "title": contract.title,
                    "expiry_date": contract.end_date.isoformat(),
                    "days_remaining": days_remaining,
                    "value": contract.value,
                    "currency": contract.currency,
                    "auto_renew": contract.auto_renew,
                    "renewal_status": self.check_renewal_status(contract, today).value,
                })
        return sorted(forecast, key=lambda x: x["days_remaining"])
