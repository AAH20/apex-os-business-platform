"""Experiment reporting: generate human-readable and machine-readable reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Experiment, ExperimentResult, ExperimentStatus
from .statistics import StatisticalAnalyzer, StatisticalResult


@dataclass
class VariantReport:
    """Report data for a single variant."""

    variant_id: str
    variant_name: str
    is_control: bool
    visitors: int
    conversions: int
    conversion_rate: float
    revenue: float
    revenue_per_visitor: float
    clicks: int
    click_rate: float
    confidence_interval_low: float
    confidence_interval_high: float


@dataclass
class ComparisonReport:
    """Report data for a treatment vs control comparison."""

    treatment_variant_id: str
    treatment_variant_name: str
    control_variant_id: str
    control_variant_name: str
    absolute_difference: float
    relative_uplift: float
    p_value: float
    is_significant: bool
    confidence_interval_low: float
    confidence_interval_high: float
    recommendation: str


@dataclass
class ExperimentReport:
    """Complete experiment report."""

    experiment_id: str
    experiment_name: str
    experiment_status: str
    primary_metric: str
    generated_at: str
    total_visitors: int
    total_conversions: int
    overall_conversion_rate: float
    variants: List[VariantReport]
    comparisons: List[ComparisonReport]
    summary: str
    recommendations: List[str]
    is_ready_for_decision: bool
    winner_variant_id: Optional[str] = None
    winner_variant_name: Optional[str] = None


class ReportGenerator:
    """Generates comprehensive A/B test reports."""

    def __init__(self, confidence_level: float = 0.95) -> None:
        self.analyzer = StatisticalAnalyzer(confidence_level=confidence_level)

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_report(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
    ) -> ExperimentReport:
        """Generate a complete experiment report.

        Args:
            experiment: The experiment definition.
            results: Aggregated results for all variants.

        Returns:
            An ExperimentReport with full analysis.
        """
        control = experiment.control_variant
        if control is None:
            raise ValueError("Experiment has no control variant")

        # Build variant reports
        variant_reports = self._build_variant_reports(experiment, results)

        # Build comparison reports
        comparison_reports = self._build_comparison_reports(
            experiment, results
        )

        # Determine if experiment is ready for decision
        is_ready = self._is_ready_for_decision(experiment, results)

        # Determine winner
        winner_id, winner_name = self._determine_winner(
            experiment, results, comparison_reports
        )

        # Generate summary and recommendations
        summary = self._generate_summary(
            experiment, results, comparison_reports, is_ready
        )
        recommendations = self._generate_recommendations(
            experiment, results, comparison_reports, is_ready
        )

        total_visitors = sum(r.visitors for r in results)
        total_conversions = sum(r.conversions for r in results)
        overall_rate = (
            total_conversions / total_visitors if total_visitors > 0 else 0.0
        )

        return ExperimentReport(
            experiment_id=experiment.id,
            experiment_name=experiment.name,
            experiment_status=experiment.status.value,
            primary_metric=experiment.primary_metric.value,
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_visitors=total_visitors,
            total_conversions=total_conversions,
            overall_conversion_rate=overall_rate,
            variants=variant_reports,
            comparisons=comparison_reports,
            summary=summary,
            recommendations=recommendations,
            is_ready_for_decision=is_ready,
            winner_variant_id=winner_id,
            winner_variant_name=winner_name,
        )

    def _build_variant_reports(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
    ) -> List[VariantReport]:
        """Build per-variant report data."""
        reports = []
        for result in results:
            variant = experiment.get_variant(result.variant_id)
            ci_low, ci_high = self.analyzer.confidence_interval(
                result.conversions, result.visitors
            )

            reports.append(VariantReport(
                variant_id=result.variant_id,
                variant_name=result.variant_name,
                is_control=variant.is_control if variant else False,
                visitors=result.visitors,
                conversions=result.conversions,
                conversion_rate=result.conversion_rate,
                revenue=result.revenue,
                revenue_per_visitor=result.revenue_per_visitor,
                clicks=result.clicks,
                click_rate=result.click_rate,
                confidence_interval_low=ci_low,
                confidence_interval_high=ci_high,
            ))
        return reports

    def _build_comparison_reports(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
    ) -> List[ComparisonReport]:
        """Build treatment vs control comparison reports."""
        control = experiment.control_variant
        if control is None:
            return []

        control_result = None
        for r in results:
            if r.variant_id == control.id:
                control_result = r
                break

        if control_result is None:
            return []

        comparisons = []
        for result in results:
            if result.variant_id == control.id:
                continue

            stat = self.analyzer._compare_variants(
                control_result, result, experiment.confidence_level
            )

            recommendation = self._comparison_recommendation(stat)

            comparisons.append(ComparisonReport(
                treatment_variant_id=result.variant_id,
                treatment_variant_name=result.variant_name,
                control_variant_id=control.id,
                control_variant_name=control.name,
                absolute_difference=stat.absolute_difference,
                relative_uplift=stat.relative_uplift,
                p_value=stat.p_value,
                is_significant=stat.is_significant,
                confidence_interval_low=stat.confidence_interval_low,
                confidence_interval_high=stat.confidence_interval_high,
                recommendation=recommendation,
            ))

        return comparisons

    def _comparison_recommendation(self, stat: StatisticalResult) -> str:
        """Generate a recommendation string for a comparison."""
        if not stat.is_significant:
            if stat.sample_size_control < 100 or stat.sample_size_treatment < 100:
                return "INSUFFICIENT_DATA: Collect more data before making a decision"
            return "NO_SIGNIFICANT_DIFFERENCE: No statistically significant difference detected"

        if stat.relative_uplift > 0:
            return (
                f"POSITIVE: Treatment shows {stat.relative_uplift:.1%} uplift "
                f"over control (p={stat.p_value:.4f})"
            )
        else:
            return (
                f"NEGATIVE: Treatment shows {abs(stat.relative_uplift):.1%} decrease "
                f"vs control (p={stat.p_value:.4f})"
            )

    def _is_ready_for_decision(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
    ) -> bool:
        """Check if the experiment has enough data for a decision."""
        for r in results:
            if r.visitors < experiment.min_sample_size:
                return False
        return True

    def _determine_winner(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
        comparisons: List[ComparisonReport],
    ) -> tuple[Optional[str], Optional[str]]:
        """Determine the winning variant, if any."""
        if not self._is_ready_for_decision(experiment, results):
            return (None, None)

        best_comparison = None
        for comp in comparisons:
            if comp.is_significant and comp.relative_uplift > 0:
                if best_comparison is None or comp.relative_uplift > best_comparison.relative_uplift:
                    best_comparison = comp

        if best_comparison:
            return (best_comparison.treatment_variant_id, best_comparison.treatment_variant_name)

        return (None, None)

    def _generate_summary(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
        comparisons: List[ComparisonReport],
        is_ready: bool,
    ) -> str:
        """Generate a human-readable summary."""
        total_visitors = sum(r.visitors for r in results)
        total_conversions = sum(r.conversions for r in results)

        lines = [
            f"Experiment: {experiment.name}",
            f"Status: {experiment.status.value}",
            f"Total visitors: {total_visitors:,}",
            f"Total conversions: {total_conversions:,}",
            f"Overall conversion rate: {total_conversions / total_visitors:.2%}" if total_visitors > 0 else "Overall conversion rate: N/A",
            "",
        ]

        if not is_ready:
            lines.append("⚠ Experiment is not ready for decision (insufficient sample size)")
            lines.append(f"   Minimum sample size per variant: {experiment.min_sample_size}")
            lines.append("")

        if comparisons:
            lines.append("Comparisons:")
            for comp in comparisons:
                sig_marker = "✓" if comp.is_significant else "✗"
                lines.append(
                    f"  {sig_marker} {comp.treatment_variant_name} vs {comp.control_variant_name}: "
                    f"{comp.relative_uplift:+.2%} uplift (p={comp.p_value:.4f})"
                )
            lines.append("")

        return "\n".join(lines)

    def _generate_recommendations(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
        comparisons: List[ComparisonReport],
        is_ready: bool,
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if not is_ready:
            recommendations.append(
                f"Continue collecting data. Minimum sample size: "
                f"{experiment.min_sample_size} per variant."
            )
            return recommendations

        significant_positive = [
            c for c in comparisons if c.is_significant and c.relative_uplift > 0
        ]
        significant_negative = [
            c for c in comparisons if c.is_significant and c.relative_uplift < 0
        ]

        if significant_positive:
            best = max(significant_positive, key=lambda c: c.relative_uplift)
            recommendations.append(
                f"Promote variant '{best.treatment_variant_name}' — "
                f"shows {best.relative_uplift:.1%} significant uplift over control."
            )
        elif significant_negative:
            recommendations.append(
                "Keep the control variant — all treatments show significant negative impact."
            )
        else:
            recommendations.append(
                "No significant difference detected. Consider: "
                "(1) running the experiment longer, "
                "(2) increasing traffic allocation, or "
                "(3) testing a larger effect."
            )

        return recommendations

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_json(self, report: ExperimentReport) -> str:
        """Export report as a JSON string."""
        return json.dumps(asdict(report), indent=2, default=str)

    def export_markdown(self, report: ExperimentReport) -> str:
        """Export report as a Markdown string."""
        lines = [
            f"# A/B Test Report: {report.experiment_name}",
            "",
            f"**Status:** {report.experiment_status}",
            f"**Generated:** {report.generated_at}",
            f"**Primary Metric:** {report.primary_metric}",
            "",
            "## Summary",
            "",
            report.summary,
            "",
            "## Variant Results",
            "",
            "| Variant | Visitors | Conversions | Conv. Rate | Revenue | Rev/Visitor | 95% CI |",
            "|---------|----------|-------------|------------|---------|------------|--------|",
        ]

        for v in report.variants:
            control_marker = " (control)" if v.is_control else ""
            ci_str = f"[{v.confidence_interval_low:.2%}, {v.confidence_interval_high:.2%}]"
            lines.append(
                f"| {v.variant_name}{control_marker} | {v.visitors:,} | {v.conversions:,} | "
                f"{v.conversion_rate:.2%} | ${v.revenue:,.2f} | ${v.revenue_per_visitor:.4f} | {ci_str} |"
            )

        lines.extend([
            "",
            "## Comparisons",
            "",
            "| Treatment | Uplift | P-Value | Significant | 95% CI | Recommendation |",
            "|-----------|--------|---------|-------------|--------|----------------|",
        ])

        for c in report.comparisons:
            sig = "Yes" if c.is_significant else "No"
            ci_str = f"[{c.confidence_interval_low:.2%}, {c.confidence_interval_high:.2%}]"
            lines.append(
                f"| {c.treatment_variant_name} | {c.relative_uplift:+.2%} | "
                f"{c.p_value:.4f} | {sig} | {ci_str} | {c.recommendation} |"
            )

        lines.extend([
            "",
            "## Recommendations",
            "",
        ])

        for rec in report.recommendations:
            lines.append(f"- {rec}")

        if report.winner_variant_name:
            lines.extend([
                "",
                f"**Winner:** {report.winner_variant_name}",
            ])

        lines.append("")
        return "\n".join(lines)

    def export_csv(self, report: ExperimentReport) -> str:
        """Export variant results as CSV."""
        lines = [
            "variant_id,variant_name,is_control,visitors,conversions,"
            "conversion_rate,revenue,revenue_per_visitor,clicks,click_rate,"
            "ci_low,ci_high"
        ]

        for v in report.variants:
            lines.append(
                f"{v.variant_id},{v.variant_name},{v.is_control},"
                f"{v.visitors},{v.conversions},{v.conversion_rate:.6f},"
                f"{v.revenue:.2f},{v.revenue_per_visitor:.6f},"
                f"{v.clicks},{v.click_rate:.6f},"
                f"{v.confidence_interval_low:.6f},{v.confidence_interval_high:.6f}"
            )

        return "\n".join(lines)
