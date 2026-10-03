"""Deepened marketing module: campaigns, email, social, attribution, ROI."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


# ── Campaign Management with A/B Testing ──────────────────────────────────────

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class ABVariant:
    name: str
    weight: float = 0.5
    conversions: int = 0
    impressions: int = 0

    @property
    def ctr(self) -> float:
        return self.conversions / self.impressions if self.impressions else 0.0


@dataclass
class Campaign:
    name: str
    budget: float
    start: datetime
    end: datetime
    status: CampaignStatus = CampaignStatus.DRAFT
    variants: list[ABVariant] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def add_variant(self, name: str, weight: float = 0.5) -> ABVariant:
        v = ABVariant(name=name, weight=weight)
        self.variants.append(v)
        return v

    def winner(self) -> ABVariant | None:
        if not self.variants:
            return None
        return max(self.variants, key=lambda v: v.ctr)

    def total_spend(self) -> float:
        return self.budget if self.status == CampaignStatus.ACTIVE else 0.0


# ── Email Marketing with Templates ───────────────────────────────────────────

@dataclass
class EmailTemplate:
    subject: str
    body: str
    variables: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def render(self, **ctx: Any) -> dict[str, str]:
        subject = self.subject
        body = self.body
        for key, val in ctx.items():
            token = f"{{{key}}}"
            subject = subject.replace(token, str(val))
            body = body.replace(token, str(val))
        return {"subject": subject, "body": body}


@dataclass
class EmailCampaign:
    template: EmailTemplate
    recipients: list[str] = field(default_factory=list)
    sent: int = 0
    opened: int = 0
    clicked: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def send(self) -> None:
        self.sent = len(self.recipients)

    @property
    def open_rate(self) -> float:
        return self.opened / self.sent if self.sent else 0.0

    @property
    def click_rate(self) -> float:
        return self.clicked / self.sent if self.sent else 0.0


# ── Social Media Scheduling ──────────────────────────────────────────────────

class Platform(str, Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


@dataclass
class ScheduledPost:
    content: str
    platform: Platform
    scheduled_at: datetime
    published: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def publish(self) -> None:
        self.published = True


@dataclass
class SocialScheduler:
    posts: list[ScheduledPost] = field(default_factory=list)

    def schedule(self, content: str, platform: Platform, when: datetime) -> ScheduledPost:
        post = ScheduledPost(content=content, platform=platform, scheduled_at=when)
        self.posts.append(post)
        return post

    def due_posts(self, now: datetime | None = None) -> list[ScheduledPost]:
        now = now or datetime.utcnow()
        return [p for p in self.posts if not p.scheduled_at <= now and not p.published]

    def publish_due(self, now: datetime | None = None) -> int:
        due = self.due_posts(now)
        for p in due:
            p.publish()
        return len(due)


# ── Multi-Touch Attribution ──────────────────────────────────────────────────

class TouchType(str, Enum):
    FIRST = "first"
    LAST = "last"
    LINEAR = "linear"
    TIME_DECAY = "time_decay"


@dataclass
class Touchpoint:
    channel: str
    timestamp: datetime
    campaign_id: str | None = None


@dataclass
class AttributionResult:
    channel: str
    credit: float


def attribute(
    touches: list[Touchpoint],
    revenue: float,
    model: TouchType = TouchType.LINEAR,
    half_life_days: float = 7.0,
) -> list[AttributionResult]:
    if not touches:
        return []
    touches = sorted(touches, key=lambda t: t.timestamp)
    n = len(touches)

    if model == TouchType.FIRST:
        weights = [1.0] + [0.0] * (n - 1)
    elif model == TouchType.LAST:
        weights = [0.0] * (n - 1) + [1.0]
    elif model == TouchType.LINEAR:
        weights = [1.0 / n] * n
    elif model == TouchType.TIME_DECAY:
        now = touches[-1].timestamp
        raw = [0.5 ** ((now - t.timestamp).total_seconds() / 86400 / half_life_days) for t in touches]
        total = sum(raw)
        weights = [r / total for r in raw]
    else:
        weights = [1.0 / n] * n

    channel_credit: dict[str, float] = {}
    for t, w in zip(touches, weights):
        channel_credit[t.channel] = channel_credit.get(t.channel, 0.0) + w * revenue

    return [AttributionResult(ch, round(cr, 2)) for ch, cr in channel_credit.items()]


# ── ROI & Cohort Analysis ────────────────────────────────────────────────────

@dataclass
class Cohort:
    label: str
    customers: int
    revenue: float
    cost: float

    @property
    def roi(self) -> float:
        return (self.revenue - self.cost) / self.cost if self.cost else 0.0

    @property
    def roas(self) -> float:
        return self.revenue / self.cost if self.cost else 0.0

    @property
    def ltv_cac_ratio(self) -> float:
        return self.revenue / self.customers if self.customers else 0.0


@dataclass
class ROICalculator:
    cohorts: list[Cohort] = field(default_factory=list)

    def add_cohort(self, label: str, customers: int, revenue: float, cost: float) -> Cohort:
        c = Cohort(label=label, customers=customers, revenue=revenue, cost=cost)
        self.cohorts.append(c)
        return c

    def blended_roi(self) -> float:
        total_rev = sum(c.revenue for c in self.cohorts)
        total_cost = sum(c.cost for c in self.cohorts)
        return (total_rev - total_cost) / total_cost if total_cost else 0.0

    def best_cohort(self) -> Cohort | None:
        if not self.cohorts:
            return None
        return max(self.cohorts, key=lambda c: c.roi)

    def cohort_table(self) -> list[dict[str, Any]]:
        return [
            {
                "label": c.label,
                "customers": c.customers,
                "revenue": c.revenue,
                "cost": c.cost,
                "roi": round(c.roi, 4),
                "roas": round(c.roas, 4),
                "ltv_cac": round(c.ltv_cac_ratio, 2),
            }
            for c in self.cohorts
        ]
