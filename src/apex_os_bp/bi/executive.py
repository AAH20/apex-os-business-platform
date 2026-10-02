"""Executive dashboard module."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from apex_os_bp.bi.kpi import KPITracker, KPIStatus
from apex_os_bp.bi.benchmarking import BenchmarkEngine
from apex_os_bp.bi.predictive import PredictiveEngine


@dataclass
class ExecutiveSummary:
    """Executive summary data structure."""
    title: str
    period: str
    overall_health: str
    key_metrics: List[Dict] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "period": self.period,
            "overall_health": self.overall_health,
            "key_metrics": self.key_metrics,
            "highlights": self.highlights,
            "concerns": self.concerns,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class ExecutiveDashboard:
    """Executive dashboard for C-suite reporting."""

    def __init__(self, kpi_tracker: Optional[KPITracker] = None,
                 benchmark_engine: Optional[BenchmarkEngine] = None,
                 predictive_engine: Optional[PredictiveEngine] = None):
        self.kpi_tracker = kpi_tracker or KPITracker()
        self.benchmark_engine = benchmark_engine or BenchmarkEngine()
        self.predictive_engine = predictive_engine or PredictiveEngine()
        self._dashboards: Dict[str, Dict] = {}

    def create_dashboard(self, name: str, kpi_names: Optional[List[str]] = None,
                         period: str = "current") -> Dict:
        """Create an executive dashboard."""
        if kpi_names:
            kpis = []
            for kname in kpi_names:
                latest = self.kpi_tracker.get_latest(kname)
                if latest:
                    kpis.append(latest)
        else:
            kpis = self.kpi_tracker.get_all()

        dashboard = {
            "name": name,
            "period": period,
            "kpi_count": len(kpis),
            "kpis": [k.to_dict() for k in kpis],
            "summary": self.kpi_tracker.get_summary(),
        }
        self._dashboards[name] = dashboard
        return dashboard

    def generate_executive_summary(self, title: str = "Executive Summary",
                                   period: str = "Current Period") -> ExecutiveSummary:
        """Generate executive summary from tracked KPIs."""
        summary = self.kpi_tracker.get_summary()
        kpis = self.kpi_tracker.get_all()

        # Determine overall health
        overall_achievement = summary.get("overall_achievement", 0)
        if overall_achievement >= 100:
            health = "excellent"
        elif overall_achievement >= 80:
            health = "good"
        elif overall_achievement >= 60:
            health = "fair"
        else:
            health = "poor"

        # Key metrics
        key_metrics = []
        for kpi in kpis[:10]:  # Top 10
            key_metrics.append({
                "name": kpi.name,
                "value": kpi.value,
                "target": kpi.target,
                "achievement_rate": kpi.achievement_rate,
                "status": kpi.status.value,
                "unit": kpi.unit,
            })

        # Highlights (exceeding or on track)
        highlights = []
        for kpi in kpis:
            if kpi.status in (KPIStatus.EXCEEDING, KPIStatus.ON_TRACK):
                highlights.append(
                    f"{kpi.name}: {kpi.achievement_rate:.1f}% of target ({kpi.value}/{kpi.target} {kpi.unit})"
                )

        # Concerns (warning or critical)
        concerns = []
        for kpi in kpis:
            if kpi.status in (KPIStatus.WARNING, KPIStatus.CRITICAL):
                concerns.append(
                    f"{kpi.name}: {kpi.achievement_rate:.1f}% of target ({kpi.value}/{kpi.target} {kpi.unit})"
                )

        # Recommendations
        recommendations = self._generate_recommendations(kpis, summary)

        return ExecutiveSummary(
            title=title,
            period=period,
            overall_health=health,
            key_metrics=key_metrics,
            highlights=highlights,
            concerns=concerns,
            recommendations=recommendations,
            metadata={
                "total_kpis": len(kpis),
                "overall_achievement": overall_achievement,
            },
        )

    def _generate_recommendations(self, kpis: list, summary: Dict) -> List[str]:
        """Generate recommendations based on KPI analysis."""
        recommendations = []

        critical_count = summary.get("by_status", {}).get("critical", 0)
        warning_count = summary.get("by_status", {}).get("warning", 0)

        if critical_count > 0:
            recommendations.append(
                f"Address {critical_count} critical KPI(s) immediately"
            )
        if warning_count > 0:
            recommendations.append(
                f"Review {warning_count} KPI(s) showing warning signs"
            )

        # Check for declining trends
        for kpi in kpis:
            trend = self.kpi_tracker.get_trend(kpi.name)
            if len(trend) >= 3:
                recent = [t["value"] for t in trend[-3:]]
                if all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
                    recommendations.append(
                        f"Investigate declining trend in {kpi.name}"
                    )

        if not recommendations:
            recommendations.append("Continue current strategies - all KPIs on track")

        return recommendations

    def get_dashboard(self, name: str) -> Optional[Dict]:
        """Get dashboard by name."""
        return self._dashboards.get(name)

    def get_all_dashboards(self) -> Dict[str, Dict]:
        """Get all dashboards."""
        return self._dashboards.copy()

    def generate_board_report(self, period: str = "Q4 2024") -> Dict:
        """Generate board-ready report."""
        summary = self.generate_executive_summary(
            title="Board Report",
            period=period,
        )

        benchmark_summary = self.benchmark_engine.get_summary()

        return {
            "executive_summary": summary.to_dict(),
            "benchmark_summary": benchmark_summary,
            "scorecard": self.kpi_tracker.get_scorecard(),
            "generated_at": period,
        }

    def generate_trend_report(self, metric_names: List[str],
                              periods: int = 6) -> Dict:
        """Generate trend report for specified metrics."""
        trends = {}
        for name in metric_names:
            trend_data = self.kpi_tracker.get_trend(name, periods=periods)
            if trend_data:
                values = [t["value"] for t in trend_data]
                trend_analysis = self.predictive_engine.detect_trend(values)
                trends[name] = {
                    "data": trend_data,
                    "analysis": trend_analysis,
                }
        return {
            "trends": trends,
            "periods_analyzed": periods,
        }

    def clear(self) -> None:
        """Clear all dashboards."""
        self._dashboards.clear()
