#!/usr/bin/env python3
"""APEX-OS CRM Demo — lead creation, scoring, opportunity, forecasting, segmentation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List

random.seed(42)


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class Lead:
    id: str
    name: str
    email: str
    company: str
    source: str
    score: int = 0
    status: str = "new"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Opportunity:
    id: str
    lead_id: str
    name: str
    stage: str
    amount: float
    probability: float
    close_date: datetime


@dataclass
class Customer:
    id: str
    name: str
    segment: str = ""
    lifetime_value: float = 0.0
    total_orders: int = 0


# ── 1. Create lead ──────────────────────────────────────────────────────────

def create_lead() -> Lead:
    """Create a new lead from a simulated form submission."""
    lead = Lead(
        id=f"LEAD-{random.randint(1000, 9999)}",
        name="Sarah Chen",
        email="sarah.chen@acme.io",
        company="Acme Corp",
        source="webinar",
    )
    print(f"[1] Lead created: {lead.id} — {lead.name} <{lead.email}> @ {lead.company}")
    print(f"    Source: {lead.source} | Status: {lead.status}")
    return lead


# ── 2. Score lead ───────────────────────────────────────────────────────────

def score_lead(lead: Lead) -> Lead:
    """Score a lead based on firmographic and behavioural signals."""
    source_weights = {"webinar": 30, "referral": 25, "ads": 15, "organic": 10}
    company_size_bonus = 20  # simulated: 500+ employees
    engagement_bonus = random.randint(0, 25)

    lead.score = (
        source_weights.get(lead.source, 10)
        + company_size_bonus
        + engagement_bonus
    )
    lead.status = "qualified" if lead.score >= 60 else "nurture"
    print(f"[2] Lead scored: {lead.score}/100 → status: {lead.status.upper()}")
    return lead


# ── 3. Create opportunity ───────────────────────────────────────────────────

def create_opportunity(lead: Lead) -> Opportunity:
    """Convert a qualified lead into a sales opportunity."""
    opp = Opportunity(
        id=f"OPP-{random.randint(1000, 9999)}",
        lead_id=lead.id,
        name=f"{lead.company} — Enterprise Plan",
        stage="discovery",
        amount=round(random.uniform(20_000, 150_000), 2),
        probability=0.25,
        close_date=datetime.now() + timedelta(days=45),
    )
    print(f"[3] Opportunity created: {opp.id} — {opp.name}")
    print(f"    Stage: {opp.stage} | Amount: ${opp.amount:,.2f} | Prob: {opp.probability:.0%}")
    return opp


# ── 4. Forecast revenue ─────────────────────────────────────────────────────

def forecast_revenue(opportunities: List[Opportunity]) -> Dict[str, float]:
    """Generate a revenue forecast from a pipeline of opportunities."""
    weighted = sum(o.amount * o.probability for o in opportunities)
    best_case = sum(o.amount for o in opportunities)
    pipeline = sum(o.amount for o in opportunities)

    forecast = {
        "pipeline": round(pipeline, 2),
        "weighted": round(weighted, 2),
        "best_case": round(best_case, 2),
    }
    print(f"[4] Revenue forecast:")
    print(f"    Pipeline:  ${forecast['pipeline']:>12,.2f}")
    print(f"    Weighted:  ${forecast['weighted']:>12,.2f}")
    print(f"    Best case: ${forecast['best_case']:>12,.2f}")
    return forecast


# ── 5. Segment customers ────────────────────────────────────────────────────

def segment_customers(customers: List[Customer]) -> Dict[str, List[Customer]]:
    """Segment customers by lifetime value tiers."""
    for c in customers:
        if c.lifetime_value >= 100_000:
            c.segment = "enterprise"
        elif c.lifetime_value >= 25_000:
            c.segment = "mid-market"
        else:
            c.segment = "smb"

    segments: Dict[str, List[Customer]] = {}
    for c in customers:
        segments.setdefault(c.segment, []).append(c)

    print(f"[5] Customer segmentation ({len(customers)} customers):")
    for tier in ("enterprise", "mid-market", "smb"):
        members = segments.get(tier, [])
        total_ltv = sum(c.lifetime_value for c in members)
        print(f"    {tier:>12}: {len(members):>3} customers | LTV ${total_ltv:>12,.2f}")
    return segments


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  APEX-OS CRM Demo")
    print("=" * 60)

    # 1. Create lead
    lead = create_lead()
    print()

    # 2. Score lead
    lead = score_lead(lead)
    print()

    # 3. Create opportunity
    opp = create_opportunity(lead)
    print()

    # 4. Forecast revenue (simulate a small pipeline)
    extra_opps = [
        Opportunity(
            id=f"OPP-{random.randint(1000, 9999)}",
            lead_id="LEAD-0000",
            name=f"Deal {i}",
            stage=random.choice(["discovery", "proposal", "negotiation"]),
            amount=round(random.uniform(10_000, 200_000), 2),
            probability=random.choice([0.1, 0.25, 0.5, 0.75]),
            close_date=datetime.now() + timedelta(days=random.randint(14, 90)),
        )
        for i in range(4)
    ]
    forecast_revenue([opp] + extra_opps)
    print()

    # 5. Segment customers
    customers = [
        Customer(id=f"CUST-{i}", name=f"Customer {i}", lifetime_value=random.uniform(5_000, 250_000))
        for i in range(12)
    ]
    segment_customers(customers)
    print()
    print("=" * 60)
    print("  Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
