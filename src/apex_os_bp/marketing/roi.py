"""Campaign ROI calculator."""
from __future__ import annotations

from typing import Dict, List

from apex_os_bp.marketing.models import ROIReport


class ROICalculator:
    """Calculate campaign ROI, ROAS, and related metrics."""

    def __init__(self):
        self._costs: Dict[str, float] = {}
        self._revenues: Dict[str, float] = {}
        self._campaign_names: Dict[str, str] = {}
        self._leads: Dict[str, int] = {}
        self._conversions: Dict[str, int] = {}

    def set_campaign_cost(self, campaign_id: str, cost: float) -> None:
        """Set the cost for a campaign."""
        if cost < 0:
            raise ValueError("Cost cannot be negative")
        self._costs[campaign_id] = cost

    def set_campaign_revenue(self, campaign_id: str, revenue: float) -> None:
        """Set the revenue for a campaign."""
        if revenue < 0:
            raise ValueError("Revenue cannot be negative")
        self._revenues[campaign_id] = revenue

    def set_campaign_name(self, campaign_id: str, name: str) -> None:
        """Set the campaign name."""
        self._campaign_names[campaign_id] = name

    def set_leads_generated(self, campaign_id: str, count: int) -> None:
        """Set the number of leads generated."""
        if count < 0:
            raise ValueError("Lead count cannot be negative")
        self._leads[campaign_id] = count

    def set_conversions(self, campaign_id: str, count: int) -> None:
        """Set the number of conversions."""
        if count < 0:
            raise ValueError("Conversion count cannot be negative")
        self._conversions[campaign_id] = count

    def calculate_roi(self, campaign_id: str) -> ROIReport:
        """Calculate ROI for a campaign."""
        cost = self._costs.get(campaign_id, 0.0)
        revenue = self._revenues.get(campaign_id, 0.0)
        leads = self._leads.get(campaign_id, 0)
        conversions = self._conversions.get(campaign_id, 0)
        name = self._campaign_names.get(campaign_id, "Unknown")

        roi = ((revenue - cost) / cost * 100) if cost > 0 else 0.0
        roas = (revenue / cost) if cost > 0 else 0.0
        cost_per_lead = (cost / leads) if leads > 0 else 0.0
        cost_per_acquisition = (cost / conversions) if conversions > 0 else 0.0

        return ROIReport(
            campaign_id=campaign_id,
            campaign_name=name,
            total_cost=cost,
            total_revenue=revenue,
            roi=roi,
            roas=roas,
            cost_per_lead=cost_per_lead,
            cost_per_acquisition=cost_per_acquisition,
            leads_generated=leads,
            conversions=conversions,
        )

    def get_roi_report(self, campaign_id: str) -> Dict:
        """Get a detailed ROI report for a campaign."""
        report = self.calculate_roi(campaign_id)
        return {
            "campaign_id": report.campaign_id,
            "campaign_name": report.campaign_name,
            "total_cost": report.total_cost,
            "total_revenue": report.total_revenue,
            "roi": report.roi,
            "roas": report.roas,
            "cost_per_lead": report.cost_per_lead,
            "cost_per_acquisition": report.cost_per_acquisition,
            "leads_generated": report.leads_generated,
            "conversions": report.conversions,
            "generated_at": report.generated_at.isoformat(),
        }

    def get_portfolio_roi(self) -> Dict:
        """Calculate ROI across all campaigns."""
        total_cost = sum(self._costs.values())
        total_revenue = sum(self._revenues.values())
        total_leads = sum(self._leads.values())
        total_conversions = sum(self._conversions.values())

        roi = ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0.0
        roas = (total_revenue / total_cost) if total_cost > 0 else 0.0
        cost_per_lead = (total_cost / total_leads) if total_leads > 0 else 0.0
        cost_per_acquisition = (
            (total_cost / total_conversions) if total_conversions > 0 else 0.0
        )

        return {
            "total_cost": total_cost,
            "total_revenue": total_revenue,
            "roi": roi,
            "roas": roas,
            "cost_per_lead": cost_per_lead,
            "cost_per_acquisition": cost_per_acquisition,
            "total_leads": total_leads,
            "total_conversions": total_conversions,
            "campaign_count": len(self._costs),
        }

    def compare_campaigns(self, campaign_ids: List[str]) -> Dict:
        """Compare ROI across multiple campaigns."""
        comparisons = []
        for cid in campaign_ids:
            if cid in self._costs:
                report = self.calculate_roi(cid)
                comparisons.append(
                    {
                        "campaign_id": cid,
                        "campaign_name": report.campaign_name,
                        "roi": report.roi,
                        "roas": report.roas,
                        "cost": report.total_cost,
                        "revenue": report.total_revenue,
                    }
                )

        comparisons.sort(key=lambda x: x["roi"], reverse=True)
        return {
            "comparisons": comparisons,
            "best_campaign": comparisons[0] if comparisons else None,
            "worst_campaign": comparisons[-1] if comparisons else None,
        }
