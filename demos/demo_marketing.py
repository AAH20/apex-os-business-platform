#!/usr/bin/env python3
"""APEX-OS Marketing Demo — campaign, leads, email, engagement, reporting."""
from __future__ import annotations
import json, random, uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class Campaign:
    name: str; subject: str; body: str; segment: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "draft"
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "subject": self.subject,
                "segment": self.segment, "status": self.status,
                "created_at": self.created_at.isoformat()}

@dataclass
class Lead:
    name: str; email: str; company: str; score: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tags: list[str] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "email": self.email,
                "company": self.company, "score": self.score, "tags": self.tags}

@dataclass
class Engagement:
    lead_id: str; campaign_id: str; event: str
    timestamp: datetime = field(default_factory=datetime.now)
    def to_dict(self) -> dict[str, Any]:
        return {"lead_id": self.lead_id, "campaign_id": self.campaign_id,
                "event": self.event, "timestamp": self.timestamp.isoformat()}

def _step(n: int, title: str) -> None:
    print(f"\n{'=' * 60}\n  Step {n}: {title}\n{'=' * 60}")

def _json(label: str, data: Any) -> None:
    print(f"\n{label}:\n{json.dumps(data, indent=2, default=str)}")

def demo_create_campaign() -> Campaign:
    _step(1, "Create Campaign")
    c = Campaign("Q4 Product Launch", "🚀 Introducing ApexOS 2.0 — Now Available",
                 "Hi {name},\n\nWe're excited to announce ApexOS 2.0 with 10x faster processing.\n\n— The ApexOS Team",
                 "enterprise")
    c.status = "active"
    _json("Campaign created", c.to_dict())
    return c

def demo_add_leads() -> list[Lead]:
    _step(2, "Add Leads")
    leads = [
        Lead("Alice Chen", "alice@acme.io", "Acme Corp", 85, tags=["enterprise", "warm"]),
        Lead("Bob Martinez", "bob@globex.com", "Globex", 62, tags=["mid-market"]),
        Lead("Carol Singh", "carol@initech.dev", "Initech", 91, tags=["enterprise", "hot"]),
        Lead("David Kim", "david@umbrella.co", "Umbrella Co", 45, tags=["smb"]),
        Lead("Eva Novak", "eva@stark.io", "Stark Industries", 78, tags=["enterprise", "warm"]),
    ]
    for l in leads:
        print(f"  ✓ Added: {l.name} <{l.email}> (score: {l.score})")
    _json(f"{len(leads)} leads in CRM", [l.to_dict() for l in leads])
    return leads

def demo_send_email(campaign: Campaign, leads: list[Lead]) -> list[Engagement]:
    _step(3, "Send Email")
    engagements: list[Engagement] = []
    for lead in leads:
        event = "bounced" if random.random() < 0.05 else "sent"
        engagements.append(Engagement(lead.id, campaign.id, event))
        icon = "✗" if event == "bounced" else "✓"
        print(f"  {icon} To {lead.name} <{lead.email}> — {event}")
    sent = sum(1 for e in engagements if e.event == "sent")
    bounced = sum(1 for e in engagements if e.event == "bounced")
    print(f"\n  Sent: {sent} | Bounced: {bounced}")
    return engagements

def demo_track_engagement(campaign: Campaign, leads: list[Lead], engagements: list[Engagement]) -> list[Engagement]:
    _step(4, "Track Engagement")
    lead_map = {l.id: l for l in leads}
    for eng in engagements:
        if eng.event != "sent":
            continue
        lead = lead_map[eng.lead_id]
        if random.random() < 0.7:
            engagements.append(Engagement(lead.id, campaign.id, "opened"))
            print(f"  👁  {lead.name} opened")
        if random.random() < 0.4:
            engagements.append(Engagement(lead.id, campaign.id, "clicked"))
            lead.score = min(100, lead.score + 10)
            print(f"  🖱  {lead.name} clicked (score → {lead.score})")
    return engagements

def demo_generate_report(campaign: Campaign, leads: list[Lead], engagements: list[Engagement]) -> dict[str, Any]:
    _step(5, "Generate Report")
    sent = sum(1 for e in engagements if e.event == "sent")
    opened = sum(1 for e in engagements if e.event == "opened")
    clicked = sum(1 for e in engagements if e.event == "clicked")
    bounced = sum(1 for e in engagements if e.event == "bounced")
    total = len(leads)
    report = {
        "campaign": campaign.name, "campaign_id": campaign.id,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_leads": total, "emails_sent": sent, "emails_bounced": bounced,
            "opens": opened, "clicks": clicked,
            "open_rate": f"{(opened / sent * 100):.1f}%" if sent else "0%",
            "click_rate": f"{(clicked / sent * 100):.1f}%" if sent else "0%",
            "bounce_rate": f"{(bounced / total * 100):.1f}%" if total else "0%",
        },
        "top_leads": sorted([l.to_dict() for l in leads], key=lambda x: x["score"], reverse=True)[:3],
    }
    _json("Campaign Report", report)
    return report

def main() -> None:
    print("🎯 APEX-OS Marketing Demo")
    print(f"   Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    campaign = demo_create_campaign()
    leads = demo_add_leads()
    engagements = demo_send_email(campaign, leads)
    engagements = demo_track_engagement(campaign, leads, engagements)
    demo_generate_report(campaign, leads, engagements)
    print(f"\n{'=' * 60}\n  ✅ Demo complete — all 5 steps executed\n{'=' * 60}\n")

if __name__ == "__main__":
    main()
