"""APEX-OS Business Platform CRM module.

Provides lead scoring, email campaigns, contact deduplication,
sales forecasting, and customer segmentation.
"""

from .lead_scoring import LeadScoringEngine, LeadScore
from .email_campaigns import EmailCampaign, CampaignManager, CampaignStatus
from .deduplication import DeduplicationEngine, DuplicateGroup
from .forecasting import ForecastResult, SalesForecaster
from .segmentation import Segment, CustomerSegmentation

__all__ = [
    "LeadScoringEngine",
    "LeadScore",
    "EmailCampaign",
    "CampaignManager",
    "CampaignStatus",
    "DeduplicationEngine",
    "DuplicateGroup",
    "ForecastResult",
    "SalesForecaster",
    "Segment",
    "CustomerSegmentation",
]
