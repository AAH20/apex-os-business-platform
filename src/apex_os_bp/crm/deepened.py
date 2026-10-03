"""Deepened CRM: lead scoring, pipeline automation, email tracking, RFM segmentation, churn prediction."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# ── 1. Lead Scoring ──────────────────────────────────────────────────────────
class LeadScoreFactor(Enum):
    DEMOGRAPHIC = "demographic"; BEHAVIORAL = "behavioral"
    ENGAGEMENT = "engagement"; FIT = "fit"

@dataclass
class LeadScoreWeight:
    factor: LeadScoreFactor; weight: float; description: str = ""

@dataclass
class Lead:
    lead_id: str; name: str; email: str; company: str = ""; job_title: str = ""
    industry: str = ""; company_size: int = 0; website_visits: int = 0
    email_opens: int = 0; email_clicks: int = 0; form_submissions: int = 0
    demo_requested: bool = False; trial_started: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    custom_scores: dict[str, float] = field(default_factory=dict)

DEFAULT_LEAD_WEIGHTS = [
    LeadScoreWeight(LeadScoreFactor.DEMOGRAPHIC, 0.20, "Company size, industry, title fit"),
    LeadScoreWeight(LeadScoreFactor.BEHAVIORAL, 0.30, "Visits, forms, demo requests"),
    LeadScoreWeight(LeadScoreFactor.ENGAGEMENT, 0.35, "Email opens, clicks, trial"),
    LeadScoreWeight(LeadScoreFactor.FIT, 0.15, "Custom sales-team fit scores"),
]

def _raw_score(lead: Lead, factor: LeadScoreFactor) -> float:
    if factor == LeadScoreFactor.DEMOGRAPHIC:
        s = min(lead.company_size / 500, 1.0) * 0.4 if lead.company_size > 0 else 0
        return s + (0.3 if lead.industry else 0) + (0.3 if lead.job_title else 0)
    if factor == LeadScoreFactor.BEHAVIORAL:
        return (min(lead.website_visits / 20, 1.0) * 0.3 + min(lead.form_submissions / 5, 1.0) * 0.3
                + 0.2 * lead.demo_requested + 0.2 * lead.trial_started)
    if factor == LeadScoreFactor.ENGAGEMENT:
        return min(lead.email_opens / 10, 1.0) * 0.4 + min(lead.email_clicks / 5, 1.0) * 0.4 + 0.2 * lead.trial_started
    if factor == LeadScoreFactor.FIT:
        return sum(lead.custom_scores.values()) / len(lead.custom_scores) if lead.custom_scores else 0.0
    return 0.0

def score_lead(lead: Lead, weights: list[LeadScoreWeight] | None = None) -> dict[str, Any]:
    weights = weights or DEFAULT_LEAD_WEIGHTS
    tw = sum(w.weight for w in weights)
    if tw == 0:
        return {"score": 0, "grade": "F", "breakdown": {}}
    bd = {w.factor.value: round(min(max(_raw_score(lead, w.factor), 0), 1) * w.weight * 100, 2) for w in weights}
    score = round(min(max(sum(bd.values()), 0), 100), 1)
    return {"score": score, "grade": _grade(score), "breakdown": bd}

def _grade(s: float) -> str:
    return "A" if s >= 80 else "B" if s >= 60 else "C" if s >= 40 else "D" if s >= 20 else "F"

# ── 2. Sales Pipeline Automation ──────────────────────────────────────────────
class PipelineStage(Enum):
    NEW = "new"; CONTACTED = "contacted"; QUALIFIED = "qualified"
    PROPOSAL = "proposal"; NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"; CLOSED_LOST = "closed_lost"

STAGE_ORDER = [PipelineStage.NEW, PipelineStage.CONTACTED, PipelineStage.QUALIFIED,
               PipelineStage.PROPOSAL, PipelineStage.NEGOTIATION, PipelineStage.CLOSED_WON]
STAGE_PROBABILITY = {PipelineStage.NEW: 0.10, PipelineStage.CONTACTED: 0.25,
                     PipelineStage.QUALIFIED: 0.40, PipelineStage.PROPOSAL: 0.60,
                     PipelineStage.NEGOTIATION: 0.80, PipelineStage.CLOSED_WON: 1.00,
                     PipelineStage.CLOSED_LOST: 0.00}

@dataclass
class Deal:
    deal_id: str; title: str; value: float; stage: PipelineStage = PipelineStage.NEW
    lead_id: str = ""; created_at: datetime = field(default_factory=datetime.now)
    stage_history: list[dict[str, Any]] = field(default_factory=list)

@dataclass
class AutomationRule:
    rule_id: str; name: str; from_stage: PipelineStage; to_stage: PipelineStage
    condition: str; action: str; active: bool = True

def transition_deal(deal: Deal, to_stage: PipelineStage, reason: str = "") -> dict[str, Any]:
    if deal.stage in (PipelineStage.CLOSED_WON, PipelineStage.CLOSED_LOST):
        return {"success": False, "error": "Cannot transition from a closed stage"}
    ci = STAGE_ORDER.index(deal.stage) if deal.stage in STAGE_ORDER else -1
    ti = STAGE_ORDER.index(to_stage) if to_stage in STAGE_ORDER else -1
    if ti < ci and to_stage not in (PipelineStage.CLOSED_WON, PipelineStage.CLOSED_LOST):
        return {"success": False, "error": "Cannot move backward in pipeline"}
    old = deal.stage; deal.stage = to_stage
    deal.stage_history.append({"from": old.value, "to": to_stage.value,
                               "at": datetime.now().isoformat(), "reason": reason})
    return {"success": True, "deal_id": deal.deal_id, "from": old.value,
            "to": to_stage.value, "probability": STAGE_PROBABILITY[to_stage]}

def _eval_condition(deal: Deal, cond: str) -> bool:
    if cond == "always": return True
    if cond.startswith("value >"):
        try: return deal.value > float(cond.split(">")[1].strip())
        except (ValueError, IndexError): return False
    if cond.startswith("days_in_stage >"):
        try:
            t = int(cond.split(">")[1].strip())
            if deal.stage_history:
                return (datetime.now() - datetime.fromisoformat(deal.stage_history[-1]["at"])).days > t
        except (ValueError, IndexError): pass
    return False

def run_automation_rules(deal: Deal, rules: list[AutomationRule]) -> list[dict[str, Any]]:
    results = []
    for r in rules:
        if not r.active or r.from_stage != deal.stage: continue
        if _eval_condition(deal, r.condition):
            if r.action == "move":
                res = transition_deal(deal, r.to_stage, f"Automation: {r.name}")
                results.append({"rule": r.name, "action": "move", "result": res})
            elif r.action == "notify":
                results.append({"rule": r.name, "action": "notify", "deal_id": deal.deal_id})
            elif r.action == "escalate":
                results.append({"rule": r.name, "action": "escalate", "deal_id": deal.deal_id})
    return results

# ── 3. Email Campaign Tracking ───────────────────────────────────────────────
@dataclass
class EmailCampaign:
    campaign_id: str; name: str; subject: str; sent_count: int = 0
    open_count: int = 0; click_count: int = 0; bounce_count: int = 0
    unsubscribe_count: int = 0; created_at: datetime = field(default_factory=datetime.now)

def track_event(campaign: EmailCampaign, event_type: str) -> dict[str, Any]:
    counters = {"sent": "sent_count", "open": "open_count", "click": "click_count",
                "bounce": "bounce_count", "unsubscribe": "unsubscribe_count"}
    et = event_type.lower()
    if et not in counters:
        return {"success": False, "error": f"Unknown event type: {et}"}
    setattr(campaign, counters[et], getattr(campaign, counters[et]) + 1)
    return {"success": True, "campaign_id": campaign.campaign_id, "event": et}

def get_campaign_metrics(campaign: EmailCampaign) -> dict[str, Any]:
    s = campaign.sent_count
    if s == 0:
        return {"campaign_id": campaign.campaign_id, "sent": 0, "open_rate": 0.0,
                "click_rate": 0.0, "bounce_rate": 0.0, "unsubscribe_rate": 0.0}
    return {"campaign_id": campaign.campaign_id, "sent": s, "opens": campaign.open_count,
            "clicks": campaign.click_count, "bounces": campaign.bounce_count,
            "unsubscribes": campaign.unsubscribe_count,
            "open_rate": round(campaign.open_count / s * 100, 2),
            "click_rate": round(campaign.click_count / s * 100, 2),
            "bounce_rate": round(campaign.bounce_count / s * 100, 2),
            "unsubscribe_rate": round(campaign.unsubscribe_count / s * 100, 2)}

# ── 4. Customer Segmentation (RFM) ───────────────────────────────────────────
@dataclass
class CustomerTransaction:
    customer_id: str; amount: float; date: datetime

@dataclass
class RFMProfile:
    customer_id: str; recency_days: int; frequency: int; monetary: float
    r_score: int = 0; f_score: int = 0; m_score: int = 0; segment: str = ""

def compute_rfm(customer_id: str, transactions: list[CustomerTransaction],
               reference_date: datetime | None = None) -> RFMProfile:
    ref = reference_date or datetime.now()
    if not transactions:
        return RFMProfile(customer_id, 999, 0, 0.0)
    return RFMProfile(customer_id, (ref - max(t.date for t in transactions)).days,
                      len(transactions), sum(t.amount for t in transactions))

def _quintile(value: float, sorted_vals: list[float], reverse: bool = False) -> int:
    if not sorted_vals: return 1
    pos = sum(1 for v in sorted_vals if v >= value) if reverse else sum(1 for v in sorted_vals if v <= value)
    return min(5, max(1, math.ceil(pos / len(sorted_vals) * 5)))

def _classify(r: int, f: int, m: int) -> str:
    if r >= 4 and f >= 4 and m >= 4: return "champions"
    if r >= 3 and f >= 3 and m >= 3: return "loyal_customers"
    if r >= 4 and f <= 2: return "new_customers"
    if r <= 2 and f >= 3: return "at_risk"
    if r <= 2 and f <= 2 and m >= 3: return "hibernating"
    avg = (r + f + m) / 3
    if avg >= 3.5: return "potential_loyalists"
    if avg >= 2.5: return "need_attention"
    return "lost"

def score_rfm(profile: RFMProfile, all_profiles: list[RFMProfile]) -> RFMProfile:
    if not all_profiles:
        profile.r_score = profile.f_score = profile.m_score = 1; profile.segment = "unknown"; return profile
    profile.r_score = _quintile(profile.recency_days, sorted(p.recency_days for p in all_profiles), reverse=True)
    profile.f_score = _quintile(profile.frequency, sorted(p.frequency for p in all_profiles))
    profile.m_score = _quintile(profile.monetary, sorted(p.monetary for p in all_profiles))
    profile.segment = _classify(profile.r_score, profile.f_score, profile.m_score)
    return profile

# ── 5. Churn Prediction ──────────────────────────────────────────────────────
@dataclass
class ChurnSignals:
    customer_id: str; days_since_last_login: int = 0; days_since_last_purchase: int = 0
    support_tickets_30d: int = 0; nps_score: float = 0.0; feature_usage_score: float = 0.0
    contract_months_remaining: int = 0; payment_failures_90d: int = 0; engagement_trend: float = 0.0

@dataclass
class ChurnPrediction:
    customer_id: str; churn_probability: float; risk_level: str
    top_factors: list[str]; recommended_actions: list[str]

def predict_churn(s: ChurnSignals) -> ChurnPrediction:
    factors: list[tuple[str, float]] = []
    if s.days_since_last_login > 30:
        factors.append(("login_inactivity", min(s.days_since_last_login / 90, 1.0) * 0.15))
    if s.days_since_last_purchase > 60:
        factors.append(("purchase_inactivity", min(s.days_since_last_purchase / 180, 1.0) * 0.20))
    if s.support_tickets_30d > 3:
        factors.append(("high_support_load", min(s.support_tickets_30d / 10, 1.0) * 0.15))
    if 0 < s.nps_score < 6:
        factors.append(("low_nps", (6 - s.nps_score) / 6 * 0.15))
    if s.feature_usage_score < 0.3:
        factors.append(("low_feature_usage", (0.3 - s.feature_usage_score) / 0.3 * 0.15))
    if s.contract_months_remaining < 3:
        factors.append(("contract_expiring", (3 - s.contract_months_remaining) / 3 * 0.10))
    if s.payment_failures_90d > 0:
        factors.append(("payment_failures", min(s.payment_failures_90d / 3, 1.0) * 0.10))
    if s.engagement_trend < -0.3:
        factors.append(("declining_engagement", abs(s.engagement_trend) * 0.10))
    prob = round(min(max(sum(v for _, v in factors), 0.0), 1.0), 3)
    risk = "critical" if prob >= 0.7 else "high" if prob >= 0.5 else "medium" if prob >= 0.3 else "low"
    top = [n for n, _ in sorted(factors, key=lambda x: x[1], reverse=True)[:3]]
    return ChurnPrediction(s.customer_id, prob, risk, top, _actions(risk, top))

def _actions(risk: str, top: list[str]) -> list[str]:
    a: list[str] = []
    if risk in ("high", "critical"):
        a += ["Schedule executive outreach call", "Prepare retention offer"]
    if "login_inactivity" in top: a.append("Send re-engagement email sequence")
    if "low_nps" in top: a.append("Trigger customer success follow-up")
    if "contract_expiring" in top: a.append("Initiate renewal conversation")
    if "payment_failures" in top: a.append("Resolve billing issues")
    if "declining_engagement" in top: a.append("Offer product training session")
    return a or ["Monitor account health"]
