"""Marketing automation module."""
from apex_os_bp.marketing.models import (
    ABTest,
    ABVariant,
    CampaignMetrics,
    CampaignStatus,
    EmailCampaign,
    EmailTemplate,
    Lead,
    LeadEnrollment,
    LeadStatus,
    NurtureSequence,
    NurtureStep,
    ROIReport,
    TestStatus,
)
from apex_os_bp.marketing.email_campaigns import EmailCampaignManager
from apex_os_bp.marketing.lead_nurturing import LeadNurturingEngine
from apex_os_bp.marketing.ab_testing import ABTestingEngine
from apex_os_bp.marketing.analytics import MarketingAnalytics
from apex_os_bp.marketing.roi import ROICalculator

__all__ = [
    "ABTest",
    "ABVariant",
    "ABTestingEngine",
    "CampaignMetrics",
    "CampaignStatus",
    "EmailCampaign",
    "EmailCampaignManager",
    "EmailTemplate",
    "Lead",
    "LeadEnrollment",
    "LeadNurturingEngine",
    "LeadStatus",
    "MarketingAnalytics",
    "NurtureSequence",
    "NurtureStep",
    "ROICalculator",
    "ROIReport",
    "TestStatus",
]
