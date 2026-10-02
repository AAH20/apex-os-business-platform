"""CRM data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class DealStage(Enum):
    """Deal stages."""
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


@dataclass
class Contact:
    """Contact data structure."""
    id: str
    name: str
    email: str
    phone: str = ""
    company: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class Deal:
    """Deal data structure."""
    id: str
    title: str
    value: float
    stage: DealStage
    contact_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def advance_stage(self) -> None:
        """Advance deal to next stage."""
        stages = list(DealStage)
        current_idx = stages.index(self.stage)
        if current_idx < len(stages) - 1:
            self.stage = stages[current_idx + 1]


@dataclass
class Pipeline:
    """Sales pipeline."""
    name: str
    deals: List[Deal] = field(default_factory=list)

    def add_deal(self, deal: Deal) -> None:
        """Add deal to pipeline."""
        self.deals.append(deal)

    def total_value(self) -> float:
        """Calculate total pipeline value."""
        return sum(deal.value for deal in self.deals)

    def deals_by_stage(self) -> Dict[DealStage, List[Deal]]:
        """Group deals by stage."""
        result: Dict[DealStage, List[Deal]] = {}
        for deal in self.deals:
            if deal.stage not in result:
                result[deal.stage] = []
            result[deal.stage].append(deal)
        return result
