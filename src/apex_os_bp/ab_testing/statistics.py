"""Statistical analysis for A/B test results.

Provides conversion rate calculations, confidence intervals,
t-tests, chi-square tests, sample size estimation, and effect size.
Uses only the Python standard library (no external dependencies).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .models import Experiment, ExperimentResult


@dataclass
class StatisticalResult:
    """Container for statistical test results."""

    metric_name: str
    control_value: float
    treatment_value: float
    absolute_difference: float
    relative_uplift: float
    confidence_interval_low: float
    confidence_interval_high: float
    p_value: float
    is_significant: bool
    sample_size_control: int
    sample_size_treatment: int
    power: float = 0.0


@dataclass
class SampleSizeResult:
    """Container for sample size calculation results."""

    required_sample_size_per_variant: int
    total_required_sample_size: int
    baseline_rate: float
    minimum_detectable_effect: float
    alpha: float
    power: float


class StatisticalAnalyzer:
    """Performs statistical analysis on A/B test results.

    All methods use only the Python standard library. P-values are
    computed using the normal approximation (z-test) which is
    appropriate for large sample sizes typical in A/B testing.
    """

    # Z-scores for common confidence levels
    Z_SCORES = {
        0.90: 1.645,
        0.95: 1.960,
        0.99: 2.576,
    }

    def __init__(self, confidence_level: float = 0.95) -> None:
        if confidence_level not in self.Z_SCORES:
            raise ValueError(
                f"Unsupported confidence level: {confidence_level}. "
                f"Supported: {list(self.Z_SCORES.keys())}"
            )
        self.confidence_level = confidence_level
        self.z_score = self.Z_SCORES[confidence_level]

    # ------------------------------------------------------------------
    # Basic rate calculations
    # ------------------------------------------------------------------

    @staticmethod
    def conversion_rate(conversions: int, visitors: int) -> float:
        """Calculate conversion rate as a fraction (0-1)."""
        if visitors <= 0:
            return 0.0
        return conversions / visitors

    @staticmethod
    def uplift(control_rate: float, treatment_rate: float) -> float:
        """Calculate relative uplift: (treatment - control) / control.

        Returns:
            Relative uplift as a fraction. Returns 0.0 if control_rate is 0.
        """
        if control_rate <= 0:
            return 0.0
        return (treatment_rate - control_rate) / control_rate

    # ------------------------------------------------------------------
    # Confidence intervals
    # ------------------------------------------------------------------

    def confidence_interval(
        self,
        conversions: int,
        visitors: int,
    ) -> Tuple[float, float]:
        """Calculate the confidence interval for a proportion.

        Uses the normal approximation (Wald interval).

        Returns:
            Tuple of (lower_bound, upper_bound) as fractions (0-1).
        """
        if visitors <= 0:
            return (0.0, 0.0)

        p = conversions / visitors
        # Standard error for a proportion
        se = math.sqrt(p * (1 - p) / visitors)
        margin = self.z_score * se

        return (max(0.0, p - margin), min(1.0, p + margin))

    def confidence_interval_for_difference(
        self,
        control_conversions: int,
        control_visitors: int,
        treatment_conversions: int,
        treatment_visitors: int,
    ) -> Tuple[float, float]:
        """Calculate the confidence interval for the difference in proportions.

        Returns:
            Tuple of (lower_bound, upper_bound) for the difference
            (treatment_rate - control_rate).
        """
        if control_visitors <= 0 or treatment_visitors <= 0:
            return (0.0, 0.0)

        p_c = control_conversions / control_visitors
        p_t = treatment_conversions / treatment_visitors
        diff = p_t - p_c

        # Standard error of the difference
        var_c = p_c * (1 - p_c) / control_visitors
        var_t = p_t * (1 - p_t) / treatment_visitors
        se = math.sqrt(max(0.0, var_c + var_t))
        margin = self.z_score * se

        return (diff - margin, diff + margin)

    # ------------------------------------------------------------------
    # Hypothesis testing
    # ------------------------------------------------------------------

    def z_test_proportions(
        self,
        control_conversions: int,
        control_visitors: int,
        treatment_conversions: int,
        treatment_visitors: int,
    ) -> Tuple[float, float]:
        """Perform a two-proportion z-test.

        Returns:
            Tuple of (z_statistic, p_value).
        """
        if control_visitors <= 0 or treatment_visitors <= 0:
            return (0.0, 1.0)

        p_c = control_conversions / control_visitors
        p_t = treatment_conversions / treatment_visitors

        # Pooled proportion
        total_conversions = control_conversions + treatment_conversions
        total_visitors = control_visitors + treatment_visitors
        p_pooled = total_conversions / total_visitors

        # Standard error under null hypothesis
        se = math.sqrt(
            max(0.0, p_pooled * (1 - p_pooled) * (1 / control_visitors + 1 / treatment_visitors))
        )

        if se == 0:
            return (0.0, 1.0)

        z = (p_t - p_c) / se
        p_value = self._z_to_p_value(z)

        return (z, p_value)

    def chi_square_test(
        self,
        control_conversions: int,
        control_visitors: int,
        treatment_conversions: int,
        treatment_visitors: int,
    ) -> Tuple[float, float]:
        """Perform a chi-square test of independence on a 2x2 contingency table.

        Returns:
            Tuple of (chi2_statistic, p_value).
        """
        if control_visitors <= 0 or treatment_visitors <= 0:
            return (0.0, 1.0)

        # Build contingency table
        control_non_conversions = control_visitors - control_conversions
        treatment_non_conversions = treatment_visitors - treatment_conversions

        observed = [
            [control_conversions, control_non_conversions],
            [treatment_conversions, treatment_non_conversions],
        ]

        row_totals = [sum(row) for row in observed]
        col_totals = [
            observed[0][j] + observed[1][j] for j in range(2)
        ]
        grand_total = sum(row_totals)

        if grand_total == 0:
            return (0.0, 1.0)

        # Calculate chi-square statistic
        chi2 = 0.0
        for i in range(2):
            for j in range(2):
                expected = (row_totals[i] * col_totals[j]) / grand_total
                if expected > 0:
                    chi2 += ((observed[i][j] - expected) ** 2) / expected

        # 1 degree of freedom for 2x2 table
        p_value = self._chi2_to_p_value(chi2, df=1)

        return (chi2, p_value)

    # ------------------------------------------------------------------
    # Sample size calculation
    # ------------------------------------------------------------------

    def calculate_sample_size(
        self,
        baseline_rate: float,
        minimum_detectable_effect: float,
        alpha: float = 0.05,
        power: float = 0.8,
    ) -> SampleSizeResult:
        """Calculate required sample size per variant.

        Uses the standard formula for two-proportion comparison.

        Args:
            baseline_rate: Expected conversion rate for control (0-1).
            minimum_detectable_effect: Minimum relative effect to detect (0-1).
            alpha: Significance level (Type I error rate).
            power: Statistical power (1 - Type II error rate).

        Returns:
            SampleSizeResult with required sample sizes.
        """
        if not 0 < baseline_rate < 1:
            raise ValueError("Baseline rate must be between 0 and 1")
        if minimum_detectable_effect <= 0:
            raise ValueError("Minimum detectable effect must be positive")
        if not 0 < alpha < 1:
            raise ValueError("Alpha must be between 0 and 1")
        if not 0 < power < 1:
            raise ValueError("Power must be between 0 and 1")

        # Z-scores for alpha and power
        z_alpha = self._get_z_for_alpha(alpha)
        z_beta = self._get_z_for_alpha(1 - power)

        p1 = baseline_rate
        p2 = baseline_rate * (1 + minimum_detectable_effect)
        p2 = min(p2, 0.999)  # cap at 99.9%

        p_bar = (p1 + p2) / 2

        numerator = (
            z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
            + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        ) ** 2
        denominator = (p2 - p1) ** 2

        if denominator == 0:
            raise ValueError("Cannot compute sample size: effect size is zero")

        n = math.ceil(numerator / denominator)

        return SampleSizeResult(
            required_sample_size_per_variant=n,
            total_required_sample_size=n * 2,
            baseline_rate=baseline_rate,
            minimum_detectable_effect=minimum_detectable_effect,
            alpha=alpha,
            power=power,
        )

    # ------------------------------------------------------------------
    # Comprehensive analysis
    # ------------------------------------------------------------------

    def analyze_experiment(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
    ) -> Dict[str, StatisticalResult]:
        """Perform comprehensive statistical analysis on experiment results.

        Compares each treatment variant against the control variant.

        Args:
            experiment: The experiment definition.
            results: Aggregated results for all variants.

        Returns:
            Dict mapping treatment variant_id to StatisticalResult.
        """
        control = experiment.control_variant
        if control is None:
            raise ValueError("Experiment has no control variant")

        control_result = None
        treatment_results = []

        for r in results:
            if r.variant_id == control.id:
                control_result = r
            else:
                treatment_results.append(r)

        if control_result is None:
            raise ValueError("No results found for control variant")

        analysis: Dict[str, StatisticalResult] = {}

        for treatment in treatment_results:
            stat = self._compare_variants(
                control_result, treatment, experiment.confidence_level
            )
            analysis[treatment.variant_id] = stat

        return analysis

    def _compare_variants(
        self,
        control: ExperimentResult,
        treatment: ExperimentResult,
        confidence_level: float = 0.95,
    ) -> StatisticalResult:
        """Compare a treatment variant against control."""
        control_rate = control.conversion_rate
        treatment_rate = treatment.conversion_rate

        abs_diff = treatment_rate - control_rate
        rel_uplift = self.uplift(control_rate, treatment_rate)

        ci_low, ci_high = self.confidence_interval_for_difference(
            control.conversions,
            control.visitors,
            treatment.conversions,
            treatment.visitors,
        )

        _, p_value = self.z_test_proportions(
            control.conversions,
            control.visitors,
            treatment.conversions,
            treatment.visitors,
        )

        alpha = 1 - confidence_level
        is_significant = p_value < alpha

        return StatisticalResult(
            metric_name="conversion_rate",
            control_value=control_rate,
            treatment_value=treatment_rate,
            absolute_difference=abs_diff,
            relative_uplift=rel_uplift,
            confidence_interval_low=ci_low,
            confidence_interval_high=ci_high,
            p_value=p_value,
            is_significant=is_significant,
            sample_size_control=control.visitors,
            sample_size_treatment=treatment.visitors,
        )

    # ------------------------------------------------------------------
    # Power analysis
    # ------------------------------------------------------------------

    def calculate_power(
        self,
        baseline_rate: float,
        treatment_rate: float,
        sample_size_per_variant: int,
        alpha: float = 0.05,
    ) -> float:
        """Calculate statistical power for a given sample size.

        Returns:
            Power as a fraction (0-1).
        """
        if sample_size_per_variant <= 0:
            return 0.0

        z_alpha = self._get_z_for_alpha(alpha)

        p1 = baseline_rate
        p2 = treatment_rate
        p_bar = (p1 + p2) / 2

        # Standard error under alternative hypothesis
        se_alt = math.sqrt(
            p1 * (1 - p1) / sample_size_per_variant
            + p2 * (1 - p2) / sample_size_per_variant
        )

        if se_alt == 0:
            return 1.0

        # Standard error under null hypothesis
        se_null = math.sqrt(
            2 * p_bar * (1 - p_bar) / sample_size_per_variant
        )

        if se_null == 0:
            return 1.0

        z_beta = (abs(p2 - p1) - z_alpha * se_null) / se_alt
        return self._z_to_cdf(z_beta)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _z_to_p_value(z: float) -> float:
        """Convert a z-statistic to a two-tailed p-value.

        Uses the error function for the normal CDF.
        """
        cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
        # Two-tailed p-value: 2 * min(cdf, 1 - cdf)
        return 2 * min(cdf, 1 - cdf)

    @staticmethod
    def _z_to_cdf(z: float) -> float:
        """Convert a z-statistic to the standard normal CDF."""
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))

    @staticmethod
    def _chi2_to_p_value(chi2: float, df: int) -> float:
        """Approximate the chi-square p-value using the Wilson-Hilferty transform.

        This is a good approximation for df >= 1.
        """
        if chi2 <= 0:
            return 1.0

        # Wilson-Hilferty transformation
        z = ((chi2 / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
        cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
        return 1 - cdf

    @staticmethod
    def _get_z_for_alpha(alpha: float) -> float:
        """Get the z-score for a given alpha (one-tailed).

        Uses a rational approximation of the inverse normal CDF.
        """
        if not 0 < alpha < 1:
            raise ValueError("Alpha must be between 0 and 1")

        # Beasley-Springer-Moro algorithm approximation
        # For common values, use known z-scores
        known = {
            0.10: 1.282,
            0.05: 1.645,
            0.025: 1.960,
            0.01: 2.326,
            0.005: 2.576,
        }
        if alpha in known:
            return known[alpha]

        # Rational approximation for inverse normal CDF
        # (Abramowitz and Stegun approximation)
        if alpha < 0.5:
            t = math.sqrt(-2 * math.log(alpha))
            sign = 1
        else:
            t = math.sqrt(-2 * math.log(1 - alpha))
            sign = -1

        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308

        z = t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t)
        return sign * z

    @staticmethod
    def is_significant(p_value: float, alpha: float = 0.05) -> bool:
        """Check if a p-value is statistically significant."""
        return p_value < alpha
