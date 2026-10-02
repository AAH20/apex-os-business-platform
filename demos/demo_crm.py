#!/usr/bin/env python3
"""
APEX-OS Business Platform — CRM Demo
=====================================
Demonstrates a CRM lead-to-cash workflow.

Shows:
  • Lead capture and qualification
  • Opportunity management
  • Quote generation
  • Order creation and fulfillment
  • Invoice and payment tracking
  • Pipeline analytics

Usage:
    python demo_crm.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums and data model
# ---------------------------------------------------------------------------

class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"


class OpportunityStage(str, Enum):
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    FULFILLED = "fulfilled"
    INVOICED = "invoiced"
    PAID = "paid"


@dataclass
class Lead:
    """A potential customer in the sales funnel."""
    id: int
    name: str
    company: str
    email: str
    phone: str
    source: str
    status: LeadStatus = LeadStatus.NEW
    score: int = 0  # 0-100
    created_date: date = field(default_factory=date.today)


@dataclass
class Opportunity:
    """A qualified sales opportunity."""
    id: int
    lead_id: int
    name: str
    value: Decimal
    stage: OpportunityStage = OpportunityStage.PROSPECTING
    probability: float = 0.10
    expected_close: Optional[date] = None
    created_date: date = field(default_factory=date.today)


@dataclass
class Quote:
    """A formal price quote for an opportunity."""
    id: int
    opportunity_id: int
    items: List[Dict]  # list of {description, quantity, unit_price}
    discount_pct: float = 0.0
    valid_until: Optional[date] = None
    status: str = "draft"  # draft, sent, accepted, rejected

    @property
    def subtotal(self) -> Decimal:
        return sum(
            Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
            for item in self.items
        )

    @property
    def discount(self) -> Decimal:
        return self.subtotal * Decimal(str(self.discount_pct / 100))

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount


@dataclass
class Order:
    """A confirmed customer order."""
    id: int
    quote_id: int
    status: OrderStatus = OrderStatus.DRAFT
    order_date: date = field(default_factory=date.today)
    ship_date: Optional[date] = None


@dataclass
class Invoice:
    """An invoice for a fulfilled order."""
    id: int
    order_id: int
    amount: Decimal
    due_date: date
    paid: bool = False
    paid_date: Optional[date] = None


@dataclass
class CRM:
    """The CRM system — manages the full lead-to-cash pipeline."""
    leads: Dict[int, Lead] = field(default_factory=dict)
    opportunities: Dict[int, Opportunity] = field(default_factory=dict)
    quotes: Dict[int, Quote] = field(default_factory=dict)
    orders: Dict[int, Order] = field(default_factory=dict)
    invoices: Dict[int, Invoice] = field(default_factory=dict)
    _lead_seq: int = 0
    _opp_seq: int = 0
    _quote_seq: int = 0
    _order_seq: int = 0
    _invoice_seq: int = 0

    # --- Lead management ---
    def add_lead(self, name: str, company: str, email: str, phone: str, source: str) -> Lead:
        self._lead_seq += 1
        lead = Lead(id=self._lead_seq, name=name, company=company,
                    email=email, phone=phone, source=source)
        self.leads[lead.id] = lead
        return lead

    def qualify_lead(self, lead_id: int, score: int) -> None:
        lead = self.leads[lead_id]
        lead.score = score
        lead.status = LeadStatus.QUALIFIED if score >= 50 else LeadStatus.UNQUALIFIED

    def convert_lead(self, lead_id: int) -> None:
        self.leads[lead_id].status = LeadStatus.CONVERTED

    # --- Opportunity management ---
    def create_opportunity(self, lead_id: int, name: str, value: Decimal,
                           expected_close: date) -> Opportunity:
        self._opp_seq += 1
        opp = Opportunity(id=self._opp_seq, lead_id=lead_id, name=name,
                          value=value, expected_close=expected_close)
        self.opportunities[opp.id] = opp
        self.convert_lead(lead_id)
        return opp

    def advance_stage(self, opp_id: int) -> None:
        opp = self.opportunities[opp_id]
        stages = list(OpportunityStage)
        idx = stages.index(opp.stage)
        if idx < len(stages) - 1:
            opp.stage = stages[idx + 1]
            # Update probability based on stage
            prob_map = {
                OpportunityStage.PROSPECTING: 0.10,
                OpportunityStage.QUALIFICATION: 0.25,
                OpportunityStage.PROPOSAL: 0.50,
                OpportunityStage.NEGOTIATION: 0.75,
                OpportunityStage.CLOSED_WON: 1.00,
                OpportunityStage.CLOSED_LOST: 0.00,
            }
            opp.probability = prob_map[opp.stage]

    # --- Quote management ---
    def create_quote(self, opp_id: int, items: List[Dict],
                     discount_pct: float = 0.0, valid_days: int = 30) -> Quote:
        self._quote_seq += 1
        quote = Quote(
            id=self._quote_seq,
            opportunity_id=opp_id,
            items=items,
            discount_pct=discount_pct,
            valid_until=date.today() + timedelta(days=valid_days),
        )
        self.quotes[quote.id] = quote
        return quote

    def accept_quote(self, quote_id: int) -> None:
        self.quotes[quote_id].status = "accepted"
        opp = self.opportunities[self.quotes[quote_id].opportunity_id]
        opp.stage = OpportunityStage.CLOSED_WON
        opp.probability = 1.0

    # --- Order management ---
    def create_order(self, quote_id: int) -> Order:
        self._order_seq += 1
        order = Order(id=self._order_seq, quote_id=quote_id)
        self.orders[order.id] = order
        return order

    def fulfill_order(self, order_id: int) -> None:
        order = self.orders[order_id]
        order.status = OrderStatus.FULFILLED
        order.ship_date = date.today()

    # --- Invoice management ---
    def create_invoice(self, order_id: int, net_days: int = 30) -> Invoice:
        self._invoice_seq += 1
        order = self.orders[order_id]
        quote = self.quotes[order.quote_id]
        invoice = Invoice(
            id=self._invoice_seq,
            order_id=order_id,
            amount=quote.total,
            due_date=date.today() + timedelta(days=net_days),
        )
        self.invoices[invoice.id] = invoice
        order.status = OrderStatus.INVOICED
        return invoice

    def record_payment(self, invoice_id: int) -> None:
        invoice = self.invoices[invoice_id]
        invoice.paid = True
        invoice.paid_date = date.today()
        order = self.orders[invoice.order_id]
        order.status = OrderStatus.PAID

    # --- Analytics ---
    def pipeline_value(self) -> Decimal:
        """Total value of open opportunities."""
        return sum(
            opp.value for opp in self.opportunities.values()
            if opp.stage not in (OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST)
        )

    def weighted_pipeline(self) -> Decimal:
        """Probability-weighted pipeline value."""
        return sum(
            opp.value * Decimal(str(opp.probability))
            for opp in self.opportunities.values()
            if opp.stage not in (OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST)
        )

    def revenue(self) -> Decimal:
        """Total recognized revenue (paid invoices)."""
        return sum(
            inv.amount for inv in self.invoices.values() if inv.paid
        )

    def outstanding_receivables(self) -> Decimal:
        """Total unpaid invoice amounts."""
        return sum(
            inv.amount for inv in self.invoices.values() if not inv.paid
        )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def run_demo() -> None:
    """Run the CRM demonstration."""
    print("=" * 70)
    print("  APEX-OS Business Platform — CRM Demo")
    print("  Lead-to-Cash Workflow Demonstration")
    print("=" * 70)

    crm = CRM()

    # 1. Lead capture
    print("\n📥 STEP 1: Lead Capture")
    print("-" * 40)
    leads_data = [
        ("Alice Johnson", "TechCorp Inc.", "alice@techcorp.com", "555-0101", "Website"),
        ("Bob Smith", "DataFlow LLC", "bob@dataflow.io", "555-0102", "Referral"),
        ("Carol White", "CloudNine Systems", "carol@cloudnine.com", "555-0103", "Trade Show"),
        ("David Brown", "InnovateCo", "david@innovateco.com", "555-0104", "Website"),
        ("Eve Davis", "StartupXYZ", "eve@startupxyz.com", "555-0105", "Cold Call"),
    ]
    for name, company, email, phone, source in leads_data:
        lead = crm.add_lead(name, company, email, phone, source)
        print(f"  Lead #{lead.id}: {name} ({company}) — source: {source}")

    # 2. Lead qualification
    print("\n🔍 STEP 2: Lead Qualification")
    print("-" * 40)
    scores = {1: 85, 2: 72, 3: 45, 4: 91, 5: 30}
    for lead_id, score in scores.items():
        crm.qualify_lead(lead_id, score)
        lead = crm.leads[lead_id]
        status_icon = "✅" if lead.status == LeadStatus.QUALIFIED else "❌"
        print(f"  Lead #{lead_id}: {lead.name:<20} score={score:>3}  {status_icon} {lead.status.value}")

    # 3. Create opportunities for qualified leads
    print("\n💼 STEP 3: Opportunity Creation")
    print("-" * 40)
    opp_data = [
        (1, "TechCorp Platform License", Decimal("45000"), date(2026, 3, 15)),
        (2, "DataFlow Integration Project", Decimal("28000"), date(2026, 2, 28)),
        (4, "InnovateCo Annual Subscription", Decimal("60000"), date(2026, 4, 1)),
    ]
    for lead_id, name, value, close in opp_data:
        opp = crm.create_opportunity(lead_id, name, value, close)
        print(f"  Opp #{opp.id}: {name:<35} ${value:>10,.2f}  close: {close}")

    # 4. Advance pipeline stages
    print("\n🔄 STEP 4: Pipeline Progression")
    print("-" * 40)
    # Opp 1: advance to proposal
    crm.advance_stage(1)  # qualification
    crm.advance_stage(1)  # proposal
    opp1 = crm.opportunities[1]
    print(f"  Opp #1: {opp1.name:<35} stage={opp1.stage.value:<15} prob={opp1.probability:.0%}")

    # Opp 2: advance to negotiation
    crm.advance_stage(2)
    crm.advance_stage(2)
    crm.advance_stage(2)
    opp2 = crm.opportunities[2]
    print(f"  Opp #2: {opp2.name:<35} stage={opp2.stage.value:<15} prob={opp2.probability:.0%}")

    # Opp 3: still prospecting
    opp3 = crm.opportunities[3]
    print(f"  Opp #3: {opp3.name:<35} stage={opp3.stage.value:<15} prob={opp3.probability:.0%}")

    # 5. Generate quotes
    print("\n📝 STEP 5: Quote Generation")
    print("-" * 40)
    quote1 = crm.create_quote(1, [
        {"description": "Enterprise License (1 year)", "quantity": 1, "unit_price": 35000},
        {"description": "Implementation Services", "quantity": 1, "unit_price": 8000},
        {"description": "Training Package", "quantity": 1, "unit_price": 2000},
    ], discount_pct=5.0)
    print(f"  Quote #{quote1.id} for Opp #1:")
    for item in quote1.items:
        print(f"    {item['description']:<35} {item['quantity']} × ${item['unit_price']:>10,.2f}")
    print(f"    {'Subtotal:':<35} ${quote1.subtotal:>10,.2f}")
    print(f"    {'Discount (5%):':<35} -${quote1.discount:>10,.2f}")
    print(f"    {'Total:':<35} ${quote1.total:>10,.2f}")

    quote2 = crm.create_quote(2, [
        {"description": "Integration Development", "quantity": 1, "unit_price": 20000},
        {"description": "API Connectors (10)", "quantity": 10, "unit_price": 500},
        {"description": "Support (6 months)", "quantity": 1, "unit_price": 3000},
    ])
    print(f"\n  Quote #{quote2.id} for Opp #2:")
    for item in quote2.items:
        print(f"    {item['description']:<35} {item['quantity']} × ${item['unit_price']:>10,.2f}")
    print(f"    {'Subtotal:':<35} ${quote2.subtotal:>10,.2f}")
    print(f"    {'Total:':<35} ${quote2.total:>10,.2f}")

    # 6. Accept quotes and create orders
    print("\n📦 STEP 6: Order Creation")
    print("-" * 40)
    crm.accept_quote(1)
    order1 = crm.create_order(1)
    print(f"  Quote #1 accepted → Order #{order1.id} created")

    crm.accept_quote(2)
    order2 = crm.create_order(2)
    print(f"  Quote #2 accepted → Order #{order2.id} created")

    # 7. Fulfill orders
    print("\n🚚 STEP 7: Order Fulfillment")
    print("-" * 40)
    crm.fulfill_order(1)
    print(f"  Order #{order1.id} fulfilled on {order1.ship_date}")
    crm.fulfill_order(2)
    print(f"  Order #{order2.id} fulfilled on {order2.ship_date}")

    # 8. Generate invoices
    print("\n🧾 STEP 8: Invoice Generation")
    print("-" * 40)
    inv1 = crm.create_invoice(1, net_days=30)
    print(f"  Invoice #{inv1.id}: ${inv1.amount:>10,.2f}  due: {inv1.due_date}")
    inv2 = crm.create_invoice(2, net_days=15)
    print(f"  Invoice #{inv2.id}: ${inv2.amount:>10,.2f}  due: {inv2.due_date}")

    # 9. Record payments
    print("\n💰 STEP 9: Payment Collection")
    print("-" * 40)
    crm.record_payment(1)
    print(f"  Invoice #{inv1.id} paid on {inv1.paid_date} ✅")
    # Invoice 2 remains unpaid

    # 10. Pipeline analytics
    print("\n📊 STEP 10: Pipeline Analytics")
    print("-" * 40)
    print(f"  Open pipeline value:       ${crm.pipeline_value():>12,.2f}")
    print(f"  Weighted pipeline value:   ${crm.weighted_pipeline():>12,.2f}")
    print(f"  Recognized revenue:        ${crm.revenue():>12,.2f}")
    print(f"  Outstanding receivables:   ${crm.outstanding_receivables():>12,.2f}")

    # 11. Lead conversion summary
    print("\n📈 STEP 11: Lead Conversion Summary")
    print("-" * 40)
    total_leads = len(crm.leads)
    qualified = sum(1 for l in crm.leads.values()
                    if l.status in (LeadStatus.QUALIFIED, LeadStatus.CONVERTED))
    converted = sum(1 for l in crm.leads.values() if l.status == LeadStatus.CONVERTED)
    print(f"  Total leads:     {total_leads}")
    print(f"  Qualified:       {qualified} ({qualified/total_leads:.0%})")
    print(f"  Converted:       {converted} ({converted/total_leads:.0%})")

    print("\n" + "=" * 70)
    print("  CRM demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
