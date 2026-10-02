"""Marketing analytics and reporting."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.marketing.models import CampaignMetrics


class MarketingAnalytics:
    """Marketing analytics with event tracking and reporting."""

    def __init__(self):
        self._events: List[Dict] = []
        self._funnel_stages: Dict[str, int] = {}

    def track_event(
        self,
        event_type: str,
        campaign_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Track a marketing event."""
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "campaign_id": campaign_id,
            "lead_id": lead_id,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        self._events.append(event)
        return event

    def get_events(
        self,
        event_type: Optional[str] = None,
        campaign_id: Optional[str] = None,
        lead_id: Optional[str] = None,
    ) -> List[Dict]:
        """Get events with optional filters."""
        events = self._events
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        if campaign_id:
            events = [e for e in events if e["campaign_id"] == campaign_id]
        if lead_id:
            events = [e for e in events if e["lead_id"] == lead_id]
        return events

    def get_campaign_analytics(self, campaign_id: str) -> Dict:
        """Get analytics for a specific campaign."""
        events = self.get_events(campaign_id=campaign_id)
        metrics = CampaignMetrics()
        for event in events:
            if event["type"] == "open":
                metrics.opened += 1
            elif event["type"] == "click":
                metrics.clicked += 1
            elif event["type"] == "conversion":
                metrics.converted += 1
            elif event["type"] == "bounce":
                metrics.bounced += 1
            elif event["type"] == "unsubscribe":
                metrics.unsubscribed += 1

        return {
            "campaign_id": campaign_id,
            "total_events": len(events),
            "metrics": metrics.to_dict(),
        }

    def get_funnel_analysis(self, stages: List[str]) -> Dict:
        """Analyze conversion funnel across stages."""
        funnel = {}
        previous_count = None
        for stage in stages:
            count = self._funnel_stages.get(stage, 0)
            conversion_from_previous = None
            if previous_count is not None and previous_count > 0:
                conversion_from_previous = count / previous_count
            funnel[stage] = {
                "count": count,
                "conversion_from_previous": conversion_from_previous,
            }
            previous_count = count

        return {
            "stages": funnel,
            "overall_conversion": (
                funnel[stages[-1]]["count"] / funnel[stages[0]]["count"]
                if stages and funnel[stages[0]]["count"] > 0
                else 0.0
            ),
        }

    def set_funnel_stage(self, stage: str, count: int) -> None:
        """Set the count for a funnel stage."""
        self._funnel_stages[stage] = count

    def get_engagement_trends(self, days: int = 30) -> Dict:
        """Get engagement trends over time."""
        cutoff = datetime.now() - timedelta(days=days)
        recent_events = [
            e for e in self._events if datetime.fromisoformat(e["timestamp"]) >= cutoff
        ]

        daily_counts: Dict[str, Dict[str, int]] = {}
        for event in recent_events:
            day = event["timestamp"][:10]
            if day not in daily_counts:
                daily_counts[day] = {"opens": 0, "clicks": 0, "conversions": 0}
            if event["type"] == "open":
                daily_counts[day]["opens"] += 1
            elif event["type"] == "click":
                daily_counts[day]["clicks"] += 1
            elif event["type"] == "conversion":
                daily_counts[day]["conversions"] += 1

        return {
            "period_days": days,
            "daily": daily_counts,
            "total_events": len(recent_events),
        }

    def get_channel_performance(self) -> Dict:
        """Get performance by channel/source."""
        channel_metrics: Dict[str, Dict] = {}
        for event in self._events:
            channel = event.get("metadata", {}).get("channel", "unknown")
            if channel not in channel_metrics:
                channel_metrics[channel] = {
                    "opens": 0,
                    "clicks": 0,
                    "conversions": 0,
                    "total": 0,
                }
            channel_metrics[channel]["total"] += 1
            if event["type"] == "open":
                channel_metrics[channel]["opens"] += 1
            elif event["type"] == "click":
                channel_metrics[channel]["clicks"] += 1
            elif event["type"] == "conversion":
                channel_metrics[channel]["conversions"] += 1

        for channel, metrics in channel_metrics.items():
            total = metrics["total"]
            metrics["open_rate"] = metrics["opens"] / total if total > 0 else 0.0
            metrics["click_rate"] = metrics["clicks"] / total if total > 0 else 0.0
            metrics["conversion_rate"] = (
                metrics["conversions"] / total if total > 0 else 0.0
            )

        return channel_metrics

    def get_overview(self) -> Dict:
        """Get marketing analytics overview."""
        total_events = len(self._events)
        opens = len([e for e in self._events if e["type"] == "open"])
        clicks = len([e for e in self._events if e["type"] == "click"])
        conversions = len([e for e in self._events if e["type"] == "conversion"])

        return {
            "total_events": total_events,
            "total_opens": opens,
            "total_clicks": clicks,
            "total_conversions": conversions,
            "open_rate": opens / total_events if total_events > 0 else 0.0,
            "click_rate": clicks / total_events if total_events > 0 else 0.0,
            "conversion_rate": conversions / total_events if total_events > 0 else 0.0,
        }
