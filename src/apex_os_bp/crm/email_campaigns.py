"""Email campaign integration for CRM.

Manages email campaigns: creation, audience targeting, send scheduling,
and engagement tracking (opens, clicks, bounces, unsubscribes).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class EmailCampaign:
    """Represents an email campaign."""

    name: str
    subject: str
    body_html: str
    body_text: str = ""
    segment_ids: list[str] = field(default_factory=list)
    status: CampaignStatus = CampaignStatus.DRAFT
    campaign_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    # Engagement tracking
    recipients_count: int = 0
    opens: int = 0
    clicks: int = 0
    bounces: int = 0
    unsubscribes: int = 0
    replies: int = 0

    @property
    def open_rate(self) -> float:
        if self.recipients_count == 0:
            return 0.0
        return round((self.opens / self.recipients_count) * 100, 2)

    @property
    def click_rate(self) -> float:
        if self.recipients_count == 0:
            return 0.0
        return round((self.clicks / self.recipients_count) * 100, 2)

    @property
    def bounce_rate(self) -> float:
        if self.recipients_count == 0:
            return 0.0
        return round((self.bounces / self.recipients_count) * 100, 2)

    @property
    def unsubscribe_rate(self) -> float:
        if self.recipients_count == 0:
            return 0.0
        return round((self.unsubscribes / self.recipients_count) * 100, 2)

    @property
    def click_to_open_rate(self) -> float:
        """Clicks as percentage of opens."""
        if self.opens == 0:
            return 0.0
        return round((self.clicks / self.opens) * 100, 2)

    @property
    def is_active(self) -> bool:
        return self.status in (
            CampaignStatus.SCHEDULED,
            CampaignStatus.SENDING,
            CampaignStatus.SENT,
        )

    def schedule(self, when: datetime) -> None:
        """Schedule the campaign for future sending."""
        if self.status not in (CampaignStatus.DRAFT, CampaignStatus.SCHEDULED):
            raise ValueError(
                f"Cannot schedule campaign in {self.status.value} status"
            )
        self.scheduled_at = when
        self.status = CampaignStatus.SCHEDULED

    def send(self, recipient_count: int) -> None:
        """Mark campaign as sent to N recipients."""
        if self.status == CampaignStatus.SENT:
            raise ValueError("Campaign already sent")
        self.recipients_count = recipient_count
        self.sent_at = datetime.utcnow()
        self.status = CampaignStatus.SENT

    def pause(self) -> None:
        if self.status not in (CampaignStatus.SENDING, CampaignStatus.SCHEDULED):
            raise ValueError(f"Cannot pause campaign in {self.status.value} status")
        self.status = CampaignStatus.PAUSED

    def cancel(self) -> None:
        if self.status == CampaignStatus.SENT:
            raise ValueError("Cannot cancel a sent campaign")
        self.status = CampaignStatus.CANCELLED

    def track_open(self) -> None:
        self.opens += 1

    def track_click(self) -> None:
        self.clicks += 1

    def track_bounce(self) -> None:
        self.bounces += 1

    def track_unsubscribe(self) -> None:
        self.unsubscribes += 1

    def track_reply(self) -> None:
        self.replies += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "subject": self.subject,
            "status": self.status.value,
            "segment_ids": self.segment_ids,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "recipients_count": self.recipients_count,
            "opens": self.opens,
            "clicks": self.clicks,
            "bounces": self.bounces,
            "unsubscribes": self.unsubscribes,
            "replies": self.replies,
            "open_rate": self.open_rate,
            "click_rate": self.click_rate,
            "bounce_rate": self.bounce_rate,
            "unsubscribe_rate": self.unsubscribe_rate,
            "click_to_open_rate": self.click_to_open_rate,
        }


class CampaignManager:
    """Manages a collection of email campaigns."""

    def __init__(self) -> None:
        self._campaigns: dict[str, EmailCampaign] = {}

    def create_campaign(
        self,
        name: str,
        subject: str,
        body_html: str,
        body_text: str = "",
        segment_ids: list[str] | None = None,
    ) -> EmailCampaign:
        campaign = EmailCampaign(
            name=name,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            segment_ids=segment_ids or [],
        )
        self._campaigns[campaign.campaign_id] = campaign
        return campaign

    def get_campaign(self, campaign_id: str) -> EmailCampaign | None:
        return self._campaigns.get(campaign_id)

    def list_campaigns(
        self, status: CampaignStatus | None = None
    ) -> list[EmailCampaign]:
        campaigns = list(self._campaigns.values())
        if status is not None:
            campaigns = [c for c in campaigns if c.status == status]
        return campaigns

    def delete_campaign(self, campaign_id: str) -> bool:
        if campaign_id in self._campaigns:
            del self._campaigns[campaign_id]
            return True
        return False

    def get_analytics_summary(self) -> dict[str, Any]:
        """Aggregate analytics across all campaigns."""
        campaigns = list(self._campaigns.values())
        if not campaigns:
            return {
                "total_campaigns": 0,
                "total_recipients": 0,
                "total_opens": 0,
                "total_clicks": 0,
                "total_bounces": 0,
                "total_unsubscribes": 0,
                "avg_open_rate": 0.0,
                "avg_click_rate": 0.0,
            }

        total_recipients = sum(c.recipients_count for c in campaigns)
        total_opens = sum(c.opens for c in campaigns)
        total_clicks = sum(c.clicks for c in campaigns)
        total_bounces = sum(c.bounces for c in campaigns)
        total_unsubs = sum(c.unsubscribes for c in campaigns)

        avg_open = (
            sum(c.open_rate for c in campaigns) / len(campaigns) if campaigns else 0.0
        )
        avg_click = (
            sum(c.click_rate for c in campaigns) / len(campaigns) if campaigns else 0.0
        )

        return {
            "total_campaigns": len(campaigns),
            "total_recipients": total_recipients,
            "total_opens": total_opens,
            "total_clicks": total_clicks,
            "total_bounces": total_bounces,
            "total_unsubscribes": total_unsubs,
            "avg_open_rate": round(avg_open, 2),
            "avg_click_rate": round(avg_click, 2),
        }

    def get_top_performing(self, limit: int = 5) -> list[EmailCampaign]:
        """Return top N campaigns by open rate."""
        sent = [c for c in self._campaigns.values()
                if c.status == CampaignStatus.SENT and c.recipients_count > 0]
        return sorted(sent, key=lambda c: c.open_rate, reverse=True)[:limit]

    def get_scheduled_campaigns(self) -> list[EmailCampaign]:
        """Return campaigns scheduled for future delivery."""
        return [
            c for c in self._campaigns.values()
            if c.status == CampaignStatus.SCHEDULED and c.scheduled_at is not None
        ]

    def get_due_campaigns(self, now: datetime | None = None) -> list[EmailCampaign]:
        """Return scheduled campaigns whose send time has arrived."""
        now = now or datetime.utcnow()
        return [
            c for c in self.get_scheduled_campaigns()
            if c.scheduled_at <= now
        ]
