"""CRM engine."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from apex_os_bp.crm.models import Contact, Deal, DealStage, Pipeline


class CRMEngine:
    """CRM engine with contact and deal management."""

    def __init__(self):
        self._contacts: Dict[str, Contact] = {}
        self._deals: Dict[str, Deal] = {}
        self._pipeline = Pipeline(name="Default Pipeline")

    def create_contact(self, name: str, email: str, **kwargs) -> Contact:
        """Create a new contact."""
        contact = Contact(id=str(uuid.uuid4()), name=name, email=email, **kwargs)
        self._contacts[contact.id] = contact
        return contact

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        """Get contact by ID."""
        return self._contacts.get(contact_id)

    def create_deal(self, title: str, value: float, **kwargs) -> Deal:
        """Create a new deal."""
        deal = Deal(id=str(uuid.uuid4()), title=title, value=value, stage=DealStage.LEAD, **kwargs)
        self._deals[deal.id] = deal
        self._pipeline.add_deal(deal)
        return deal

    def get_deal(self, deal_id: str) -> Optional[Deal]:
        """Get deal by ID."""
        return self._deals.get(deal_id)

    def link_deal_to_contact(self, deal_id: str, contact_id: str) -> None:
        """Link deal to contact."""
        deal = self._deals.get(deal_id)
        if not deal:
            raise ValueError(f"Deal not found: {deal_id}")
        deal.contact_id = contact_id

    def pipeline_report(self) -> Dict:
        """Generate pipeline report."""
        return {
            "total_deals": len(self._deals),
            "total_value": self._pipeline.total_value(),
            "deals_by_stage": {
                stage.value: len(deals)
                for stage, deals in self._pipeline.deals_by_stage().items()
            },
        }

    def get_contacts(self) -> List[Contact]:
        """Get all contacts."""
        return list(self._contacts.values())

    def get_deals(self) -> List[Deal]:
        """Get all deals."""
        return list(self._deals.values())
