"""Email campaign management."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from apex_os_bp.marketing.models import (
    CampaignMetrics,
    CampaignStatus,
    EmailCampaign,
    EmailTemplate,
)


class EmailCampaignManager:
    """Manage email campaigns, templates, and performance tracking."""

    def __init__(self):
        self._campaigns: Dict[str, EmailCampaign] = {}
        self._templates: Dict[str, EmailTemplate] = {}

    def create_template(self, name: str, subject: str, body: str) -> EmailTemplate:
        """Create a new email template."""
        template = EmailTemplate(
            id=str(uuid.uuid4()),
            name=name,
            subject=subject,
            body=body,
        )
        self._templates[template.id] = template
        return template

    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)

    def create_campaign(
        self,
        name: str,
        subject: str,
        body: str,
        segments: Optional[List[str]] = None,
        template_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> EmailCampaign:
        """Create a new email campaign."""
        campaign = EmailCampaign(
            id=str(uuid.uuid4()),
            name=name,
            subject=subject,
            body=body,
            segments=segments or [],
            template_id=template_id,
            metadata=metadata or {},
        )
        self._campaigns[campaign.id] = campaign
        return campaign

    def get_campaign(self, campaign_id: str) -> Optional[EmailCampaign]:
        """Get campaign by ID."""
        return self._campaigns.get(campaign_id)

    def send_campaign(self, campaign_id: str, recipient_count: int = 100) -> CampaignMetrics:
        """Send campaign to recipients and return metrics."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")
        if campaign.status == CampaignStatus.SENT:
            raise ValueError(f"Campaign already sent: {campaign_id}")

        campaign.status = CampaignStatus.SENT
        campaign.sent_at = datetime.now()
        campaign.metrics.sent = recipient_count
        campaign.metrics.delivered = recipient_count
        return campaign.metrics

    def track_event(self, campaign_id: str, event_type: str) -> None:
        """Track a campaign event (open, click, conversion, bounce, unsubscribe)."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        metrics = campaign.metrics
        if event_type == "open":
            metrics.opened += 1
        elif event_type == "click":
            metrics.clicked += 1
        elif event_type == "conversion":
            metrics.converted += 1
        elif event_type == "bounce":
            metrics.bounced += 1
        elif event_type == "unsubscribe":
            metrics.unsubscribed += 1
        else:
            raise ValueError(f"Unknown event type: {event_type}")

    def get_campaign_report(self, campaign_id: str) -> Dict:
        """Generate a comprehensive campaign report."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        return {
            "campaign_id": campaign.id,
            "name": campaign.name,
            "status": campaign.status.value,
            "segments": campaign.segments,
            "metrics": campaign.metrics.to_dict(),
            "created_at": campaign.created_at.isoformat(),
            "sent_at": campaign.sent_at.isoformat() if campaign.sent_at else None,
        }

    def list_campaigns(self, status: Optional[CampaignStatus] = None) -> List[EmailCampaign]:
        """List all campaigns, optionally filtered by status."""
        campaigns = list(self._campaigns.values())
        if status:
            campaigns = [c for c in campaigns if c.status == status]
        return campaigns

    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign."""
        if campaign_id in self._campaigns:
            del self._campaigns[campaign_id]
            return True
        return False

    def get_aggregate_metrics(self) -> Dict:
        """Get aggregate metrics across all campaigns."""
        total = CampaignMetrics()
        for campaign in self._campaigns.values():
            total.sent += campaign.metrics.sent
            total.delivered += campaign.metrics.delivered
            total.opened += campaign.metrics.opened
            total.clicked += campaign.metrics.clicked
            total.converted += campaign.metrics.converted
            total.bounced += campaign.metrics.bounced
            total.unsubscribed += campaign.metrics.unsubscribed
        return total.to_dict()
