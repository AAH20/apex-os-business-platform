"""Marketing automation data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class CampaignStatus(Enum):
    """Email campaign status."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"


class LeadStatus(Enum):
    """Lead status in the funnel."""

    NEW = "new"
    CONTACTED = "contacted"
    ENGAGED = "engaged"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


class TestStatus(Enum):
    """A/B test status."""

    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class EmailTemplate:
    """Email template data structure."""

    id: str
    name: str
    subject: str
    body: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CampaignMetrics:
    """Campaign performance metrics."""

    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    converted: int = 0
    bounced: int = 0
    unsubscribed: int = 0

    @property
    def open_rate(self) -> float:
        """Open rate as a ratio (0.0 to 1.0)."""
        return self.opened / self.delivered if self.delivered > 0 else 0.0

    @property
    def click_rate(self) -> float:
        """Click-through rate as a ratio (0.0 to 1.0)."""
        return self.clicked / self.delivered if self.delivered > 0 else 0.0

    @property
    def conversion_rate(self) -> float:
        """Conversion rate as a ratio (0.0 to 1.0)."""
        return self.converted / self.delivered if self.delivered > 0 else 0.0

    @property
    def bounce_rate(self) -> float:
        """Bounce rate as a ratio (0.0 to 1.0)."""
        return self.bounced / self.sent if self.sent > 0 else 0.0

    @property
    def unsubscribe_rate(self) -> float:
        """Unsubscribe rate as a ratio (0.0 to 1.0)."""
        return self.unsubscribed / self.delivered if self.delivered > 0 else 0.0

    @property
    def click_to_open_rate(self) -> float:
        """Click-to-open rate as a ratio (0.0 to 1.0)."""
        return self.clicked / self.opened if self.opened > 0 else 0.0

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "sent": self.sent,
            "delivered": self.delivered,
            "opened": self.opened,
            "clicked": self.clicked,
            "converted": self.converted,
            "bounced": self.bounced,
            "unsubscribed": self.unsubscribed,
            "open_rate": self.open_rate,
            "click_rate": self.click_rate,
            "conversion_rate": self.conversion_rate,
            "bounce_rate": self.bounce_rate,
            "unsubscribe_rate": self.unsubscribe_rate,
            "click_to_open_rate": self.click_to_open_rate,
        }


@dataclass
class EmailCampaign:
    """Email campaign data structure."""

    id: str
    name: str
    subject: str
    body: str
    status: CampaignStatus = CampaignStatus.DRAFT
    segments: List[str] = field(default_factory=list)
    template_id: Optional[str] = None
    metrics: CampaignMetrics = field(default_factory=CampaignMetrics)
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class Lead:
    """Lead data structure."""

    id: str
    name: str
    email: str
    score: float = 0.0
    status: LeadStatus = LeadStatus.NEW
    source: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class NurtureStep:
    """Nurture sequence step."""

    id: str
    sequence_id: str
    email_template: EmailTemplate
    delay_days: int = 0
    condition: Optional[str] = None
    order: int = 0


@dataclass
class NurtureSequence:
    """Nurture sequence data structure."""

    id: str
    name: str
    steps: List[NurtureStep] = field(default_factory=list)
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class LeadEnrollment:
    """Lead enrollment in a nurture sequence."""

    id: str
    lead_id: str
    sequence_id: str
    current_step: int = 0
    status: str = "active"
    enrolled_at: datetime = field(default_factory=datetime.now)
    last_sent_at: Optional[datetime] = None


@dataclass
class ABVariant:
    """A/B test variant."""

    id: str
    test_id: str
    name: str
    subject: str
    body: str
    metrics: CampaignMetrics = field(default_factory=CampaignMetrics)
    traffic_allocation: float = 0.5


@dataclass
class ABTest:
    """A/B test data structure."""

    id: str
    name: str
    variants: List[ABVariant] = field(default_factory=list)
    status: TestStatus = TestStatus.DRAFT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    winner_variant_id: Optional[str] = None
    confidence_level: float = 0.95
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ROIReport:
    """Campaign ROI report."""

    campaign_id: str
    campaign_name: str
    total_cost: float
    total_revenue: float
    roi: float
    roas: float
    cost_per_lead: float
    cost_per_acquisition: float
    leads_generated: int
    conversions: int
    generated_at: datetime = field(default_factory=datetime.now)
