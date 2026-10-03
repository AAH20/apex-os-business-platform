#!/usr/bin/env python3
"""CRM Demo: Lead creation, scoring, pipeline, segmentation, churn prediction."""

import random
import datetime
from dataclasses import dataclass, field
from typing import List, Dict

random.seed(42)


@dataclass
class Lead:
    id: int
    name: str
    email: str
    company: str
    source: str
    score: float = 0.0
    status: str = "new"
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)


@dataclass
class Customer:
    id: int
    name: str
    tenure_months: int
    monthly_spend: float
    support_tickets: int
    last_login_days: int
    churn_risk: float = 0.0


# ─── Demo 1: Lead Creation ───────────────────────────────────────────────────

def demo_lead_creation():
    print("=" * 60)
    print("DEMO 1: Lead Creation")
    print("=" * 60)
    sources = ["website", "referral", "social", "email", "event"]
    companies = ["Acme Corp", "Globex", "Initech", "Umbrella", "Stark Industries"]
    leads: List[Lead] = []
    for i in range(1, 6):
        lead = Lead(
            id=i,
            name=f"Lead {i}",
            email=f"lead{i}@example.com",
            company=random.choice(companies),
            source=random.choice(sources),
        )
        leads.append(lead)
        print(f"  Created: {lead.name} | {lead.company} | source={lead.source}")
    print(f"  Total leads created: {len(leads)}\n")
    return leads


# ─── Demo 2: Lead Scoring ───────────────────────────────────────────────────

def demo_lead_scoring(leads: List[Lead]):
    print("=" * 60)
    print("DEMO 2: Lead Scoring")
    print("=" * 60)
    for lead in leads:
        source_weight = {"website": 30, "referral": 50, "social": 20, "email": 35, "event": 40}
        base = source_weight.get(lead.source, 25)
        engagement = random.uniform(0, 30)
        fit = random.uniform(0, 20)
        lead.score = round(base + engagement + fit, 1)
        if lead.score >= 70:
            lead.status = "hot"
        elif lead.score >= 40:
            lead.status = "warm"
        else:
            lead.status = "cold"
        print(f"  {lead.name} ({lead.company}): score={lead.score} → {lead.status}")
    hot = [l for l in leads if l.status == "hot"]
    print(f"  Hot leads: {len(hot)}/{len(leads)}\n")
    return leads


# ─── Demo 3: Pipeline ───────────────────────────────────────────────────────

def demo_pipeline(leads: List[Lead]):
    print("=" * 60)
    print("DEMO 3: Pipeline Management")
    print("=" * 60)
    stages = ["new", "contacted", "qualified", "proposal", "won", "lost"]
    pipeline: Dict[str, List[str]] = {s: [] for s in stages}
    for lead in leads:
        if lead.status == "hot":
            stage = random.choice(["qualified", "proposal", "won"])
        elif lead.status == "warm":
            stage = random.choice(["contacted", "qualified"])
        else:
            stage = random.choice(["new", "contacted", "lost"])
        lead.status = stage
        pipeline[stage].append(lead.name)
    for stage, names in pipeline.items():
        print(f"  {stage:12s}: {', '.join(names) if names else '(empty)'}")
    won = len(pipeline["won"])
    total = len(leads)
    rate = (won / total * 100) if total else 0
    print(f"  Win rate: {rate:.0f}%\n")
    return pipeline


# ─── Demo 4: Segmentation ───────────────────────────────────────────────────

def demo_segmentation(leads: List[Lead]):
    print("=" * 60)
    print("DEMO 4: Segmentation")
    print("=" * 60)
    segments: Dict[str, List[str]] = {"enterprise": [], "smb": [], "startup": []}
    for lead in leads:
        if "Stark" in lead.company or "Umbrella" in lead.company:
            segments["enterprise"].append(lead.name)
        elif lead.score >= 50:
            segments["smb"].append(lead.name)
        else:
            segments["startup"].append(lead.name)
    for seg, names in segments.items():
        print(f"  {seg:12s}: {', '.join(names) if names else '(empty)'}")
    print(f"  Segments: {len(segments)}\n")
    return segments


# ─── Demo 5: Churn Prediction ───────────────────────────────────────────────

def demo_churn_prediction():
    print("=" * 60)
    print("DEMO 5: Churn Prediction")
    print("=" * 60)
    customers: List[Customer] = []
    for i in range(1, 6):
        c = Customer(
            id=i,
            name=f"Customer {i}",
            tenure_months=random.randint(3, 36),
            monthly_spend=round(random.uniform(50, 2000), 2),
            support_tickets=random.randint(0, 15),
            last_login_days=random.randint(0, 60),
        )
        recency_factor = c.last_login_days / 60 * 40
        ticket_factor = c.support_tickets / 15 * 30
        spend_factor = max(0, (500 - c.monthly_spend) / 500 * 20)
        tenure_factor = max(0, (12 - c.tenure_months) / 12 * 10)
        c.churn_risk = round(recency_factor + ticket_factor + spend_factor + tenure_factor, 1)
        customers.append(c)
        risk_label = "HIGH" if c.churn_risk >= 50 else "MEDIUM" if c.churn_risk >= 25 else "LOW"
        print(f"  {c.name}: churn_risk={c.churn_risk} → {risk_label}")
    high_risk = [c for c in customers if c.churn_risk >= 50]
    print(f"  High-risk customers: {len(high_risk)}/{len(customers)}\n")
    return customers


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 60)
    print("  APEX-OS CRM Demo Suite")
    print("█" * 60 + "\n")
    leads = demo_lead_creation()
    leads = demo_lead_scoring(leads)
    demo_pipeline(leads)
    demo_segmentation(leads)
    demo_churn_prediction()
    print("=" * 60)
    print("CRM Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
