"""Auto-optimization: automated decision-making and traffic adjustment.

Provides Bayesian analysis, automated winner promotion, traffic
rebalancing, and experiment recommendation engine.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import Experiment, ExperimentResult, ExperimentStatus, Variant
from .statistics import StatisticalAnalyzer, StatisticalResult


@dataclass
class OptimizationAction:
    """Represents an optimization action to be taken."""

    action_type: str  # "promote_winner", "adjust_traffic", "stop_experiment", "continue"
    reason: str
    confidence: float  # 0-1
    details: Dict[str, Any] = field(default_factory=dict)
    applied: bool = False


@dataclass
class BayesianResult:
    """Result of Bayesian analysis."""

    probability_treatment_better: float  # 0-1
    expected_loss_control: float
    expected_loss_treatment: float
    credible_interval_low: float
    credible_interval_high: float


class AutoOptimizer:
    """Automated optimization engine for A/B tests.

    Uses a combination of frequentist and Bayesian methods to make
    decisions about experiment outcomes and traffic allocation.
    """

    def __init__(
        self,
        confidence_level: float = 0.95,
        min_probability_threshold: float = 0.95,
        max_traffic_shift: float = 20.0,
    ) -> None:
        """
        Args:
            confidence_level: Statistical confidence level.
            min_probability_threshold: Minimum Bayesian probability
                required to auto-promote a winner (0-1).
            max_traffic_shift: Maximum traffic shift per optimization
                cycle in percentage points.
        """
        self.analyzer = StatisticalAnalyzer(confidence_level=confidence_level)
        self.min_probability_threshold = min_probability_threshold
        self.max_traffic_shift = max_traffic_shift

    # ------------------------------------------------------------------
    # Bayesian analysis
    # ------------------------------------------------------------------

    def bayesian_analysis(
        self,
        control_conversions: int,
        control_visitors: int,
        treatment_conversions: int,
        treatment_visitors: int,
        num_samples: int = 100_000,
    ) -> BayesianResult:
        """Perform Bayesian analysis using Beta-Binomial model.

        Uses Monte Carlo sampling to estimate the probability that
        the treatment is better than control.

        Args:
            control_conversions: Conversions in control.
            control_visitors: Visitors in control.
            treatment_conversions: Conversions in treatment.
            treatment_visitors: Visitors in treatment.
            num_samples: Number of Monte Carlo samples.

        Returns:
            BayesianResult with probability estimates and expected loss.
        """
        if control_visitors <= 0 or treatment_visitors <= 0:
            return BayesianResult(
                probability_treatment_better=0.5,
                expected_loss_control=0.0,
                expected_loss_treatment=0.0,
                credible_interval_low=0.0,
                credible_interval_high=0.0,
            )

        # Beta(1, 1) prior (uniform)
        alpha_control = 1 + control_conversions
        beta_control = 1 + (control_visitors - control_conversions)
        alpha_treatment = 1 + treatment_conversions
        beta_treatment = 1 + (treatment_visitors - treatment_conversions)

        # Monte Carlo sampling
        treatment_wins = 0
        loss_control_samples = []
        loss_treatment_samples = []
        diff_samples = []

        for _ in range(num_samples):
            # Sample from Beta distributions using gamma trick
            sample_control = self._sample_beta(alpha_control, beta_control)
            sample_treatment = self._sample_beta(alpha_treatment, beta_treatment)

            if sample_treatment > sample_control:
                treatment_wins += 1

            # Expected loss: how much we lose by choosing each variant
            loss_control = max(0, sample_treatment - sample_control)
            loss_treatment = max(0, sample_control - sample_treatment)

            loss_control_samples.append(loss_control)
            loss_treatment_samples.append(loss_treatment)
            diff_samples.append(sample_treatment - sample_control)

        prob_treatment_better = treatment_wins / num_samples
        expected_loss_control = sum(loss_control_samples) / num_samples
        expected_loss_treatment = sum(loss_treatment_samples) / num_samples

        # 95% credible interval for the difference
        diff_samples.sort()
        ci_low = diff_samples[int(0.025 * num_samples)]
        ci_high = diff_samples[int(0.975 * num_samples)]

        return BayesianResult(
            probability_treatment_better=prob_treatment_better,
            expected_loss_control=expected_loss_control,
            expected_loss_treatment=expected_loss_treatment,
            credible_interval_low=ci_low,
            credible_interval_high=ci_high,
        )

    @staticmethod
    def _sample_beta(alpha: float, beta: float) -> float:
        """Sample from a Beta distribution using the Gamma trick.

        Beta(a, b) = Gamma(a) / (Gamma(a) + Gamma(b))
        """
        # Clamp to positive values to avoid gammavariate errors
        alpha = max(alpha, 1e-10)
        beta = max(beta, 1e-10)
        # Use random.gammavariate for Gamma sampling
        x = random.gammavariate(alpha, 1.0)
        y = random.gammavariate(beta, 1.0)
        if x + y == 0:
            return 0.5
        return x / (x + y)

    # ------------------------------------------------------------------
    # Decision engine
    # ------------------------------------------------------------------

    def recommend_action(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
    ) -> OptimizationAction:
        """Recommend an optimization action based on experiment data.

        Args:
            experiment: The experiment definition.
            results: Aggregated results for all variants.

        Returns:
            OptimizationAction with recommendation.
        """
        control = experiment.control_variant
        if control is None:
            return OptimizationAction(
                action_type="continue",
                reason="No control variant defined",
                confidence=0.0,
            )

        control_result = None
        treatment_results = []
        for r in results:
            if r.variant_id == control.id:
                control_result = r
            else:
                treatment_results.append(r)

        if control_result is None or not treatment_results:
            return OptimizationAction(
                action_type="continue",
                reason="Insufficient variant data",
                confidence=0.0,
            )

        # Check minimum sample size
        for r in results:
            if r.visitors < experiment.min_sample_size:
                return OptimizationAction(
                    action_type="continue",
                    reason=(
                        f"Insufficient data: variant '{r.variant_name}' has "
                        f"{r.visitors} visitors (min: {experiment.min_sample_size})"
                    ),
                    confidence=0.0,
                )

        # Analyze each treatment variant
        best_treatment = None
        best_bayesian_prob = -1.0
        best_stat_result = None

        for treatment in treatment_results:
            bayesian = self.bayesian_analysis(
                control_result.conversions,
                control_result.visitors,
                treatment.conversions,
                treatment.visitors,
            )

            stat = self.analyzer._compare_variants(
                control_result, treatment, experiment.confidence_level
            )

            if bayesian.probability_treatment_better > best_bayesian_prob:
                best_bayesian_prob = bayesian.probability_treatment_better
                best_treatment = treatment
                best_stat_result = stat

        if best_treatment is None or best_stat_result is None:
            return OptimizationAction(
                action_type="continue",
                reason="No treatment variants to evaluate",
                confidence=0.0,
            )

        # Decision logic
        if best_bayesian_prob >= self.min_probability_threshold:
            if best_stat_result.relative_uplift > 0:
                return OptimizationAction(
                    action_type="promote_winner",
                    reason=(
                        f"Variant '{best_treatment.variant_name}' has "
                        f"{best_bayesian_prob:.1%} probability of being better "
                        f"with {best_stat_result.relative_uplift:.1%} uplift"
                    ),
                    confidence=best_bayesian_prob,
                    details={
                        "winner_variant_id": best_treatment.variant_id,
                        "winner_variant_name": best_treatment.variant_name,
                        "uplift": best_stat_result.relative_uplift,
                        "p_value": best_stat_result.p_value,
                    },
                )
            else:
                return OptimizationAction(
                    action_type="stop_experiment",
                    reason=(
                        f"Variant '{best_treatment.variant_name}' is significantly worse "
                        f"({best_stat_result.relative_uplift:.1%} vs control)"
                    ),
                    confidence=best_bayesian_prob,
                    details={
                        "loser_variant_id": best_treatment.variant_id,
                        "loser_variant_name": best_treatment.variant_name,
                        "uplift": best_stat_result.relative_uplift,
                    },
                )

        # Check for significant negative results (harm detection)
        for treatment in treatment_results:
            stat = self.analyzer._compare_variants(
                control_result, treatment, experiment.confidence_level
            )
            if stat.is_significant and stat.relative_uplift < -0.1:
                return OptimizationAction(
                    action_type="stop_experiment",
                    reason=(
                        f"Variant '{treatment.variant_name}' is significantly worse "
                        f"({stat.relative_uplift:.1%} vs control, p={stat.p_value:.4f})"
                    ),
                    confidence=1.0 - stat.p_value,
                    details={
                        "loser_variant_id": treatment.variant_id,
                        "loser_variant_name": treatment.variant_name,
                        "uplift": stat.relative_uplift,
                    },
                )

        # Check if all treatments are clearly worse
        all_worse = True
        for treatment in treatment_results:
            bayesian = self.bayesian_analysis(
                control_result.conversions,
                control_result.visitors,
                treatment.conversions,
                treatment.visitors,
            )
            if bayesian.probability_treatment_better > 0.1:
                all_worse = False
                break

        if all_worse:
            return OptimizationAction(
                action_type="stop_experiment",
                reason="All treatment variants are performing worse than control",
                confidence=0.9,
                details={"control_variant_name": control.name},
            )

        # Suggest traffic adjustment for promising variants
        if best_bayesian_prob > 0.7 and best_stat_result.relative_uplift > 0:
            variant = experiment.get_variant(best_treatment.variant_id)
            current_alloc = variant.traffic_allocation if variant else 50.0
            return OptimizationAction(
                action_type="adjust_traffic",
                reason=(
                    f"Variant '{best_treatment.variant_name}' shows promise "
                    f"({best_bayesian_prob:.1%} probability of winning)"
                ),
                confidence=best_bayesian_prob,
                details={
                    "variant_id": best_treatment.variant_id,
                    "variant_name": best_treatment.variant_name,
                    "current_allocation": current_alloc,
                    "recommended_allocation": min(
                        current_alloc + self.max_traffic_shift,
                        80.0,
                    ),
                },
            )

        return OptimizationAction(
            action_type="continue",
            reason=(
                f"Continue collecting data. Best variant '{best_treatment.variant_name}' "
                f"has {best_bayesian_prob:.1%} probability of winning"
            ),
            confidence=1.0 - best_bayesian_prob,
        )

    # ------------------------------------------------------------------
    # Auto-optimization
    # ------------------------------------------------------------------

    def auto_optimize(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
        apply: bool = False,
    ) -> OptimizationAction:
        """Analyze and optionally apply optimization.

        Args:
            experiment: The experiment definition.
            results: Aggregated results for all variants.
            apply: If True, apply the recommended action to the experiment.

        Returns:
            OptimizationAction with details of what was done.
        """
        action = self.recommend_action(experiment, results)

        if apply and not action.applied:
            if action.action_type != "continue":
                self._apply_action(experiment, action)
                action.applied = True

        return action

    def _apply_action(self, experiment: Experiment, action: OptimizationAction) -> None:
        """Apply an optimization action to an experiment."""
        if action.action_type == "promote_winner":
            winner_id = action.details.get("winner_variant_id")
            if winner_id:
                # Shift traffic to winner
                winner = experiment.get_variant(winner_id)
                if winner:
                    shift = min(self.max_traffic_shift, winner.traffic_allocation)
                    winner.traffic_allocation = min(
                        winner.traffic_allocation + shift, 90.0
                    )
                    # Reduce other variants proportionally
                    self._rebalance_traffic(experiment, winner_id)

        elif action.action_type == "stop_experiment":
            experiment.status = ExperimentStatus.COMPLETED

        elif action.action_type == "adjust_traffic":
            variant_id = action.details.get("variant_id")
            new_allocation = action.details.get("recommended_allocation")
            if variant_id and new_allocation:
                variant = experiment.get_variant(variant_id)
                if variant:
                    variant.traffic_allocation = new_allocation
                    self._rebalance_traffic(experiment, variant_id)

    def _rebalance_traffic(
        self,
        experiment: Experiment,
        priority_variant_id: str,
    ) -> None:
        """Rebalance traffic so total remains 100%.

        Reduces other variants proportionally to accommodate the
        priority variant's new allocation.
        """
        priority = experiment.get_variant(priority_variant_id)
        if priority is None:
            return

        others = [v for v in experiment.variants if v.id != priority_variant_id]
        if not others:
            return

        remaining = 100.0 - priority.traffic_allocation
        current_others_total = sum(v.traffic_allocation for v in others)

        if current_others_total > 0:
            for v in others:
                proportion = v.traffic_allocation / current_others_total
                v.traffic_allocation = round(remaining * proportion, 2)

    # ------------------------------------------------------------------
    # Multi-armed bandit (Thompson Sampling)
    # ------------------------------------------------------------------

    def thompson_sampling_assignment(
        self,
        experiment: Experiment,
        user_id: str,
    ) -> str:
        """Assign a user using Thompson Sampling.

        Thompson Sampling is a Bayesian approach to the multi-armed
        bandit problem. It naturally balances exploration and
        exploitation by sampling from the posterior distribution
        of each variant's conversion rate.

        Args:
            experiment: The experiment definition.
            user_id: Unique user identifier.

        Returns:
            The selected variant_id.
        """
        if not experiment.variants:
            raise ValueError("Experiment has no variants")

        best_variant = None
        best_sample = -1.0

        for variant in experiment.variants:
            # Get observed data for this variant
            conversions = variant.config.get("conversions", 0)
            visitors = variant.config.get("visitors", 0)

            # Beta(1 + conversions, 1 + visitors - conversions) posterior
            alpha = 1 + conversions
            beta = 1 + (visitors - conversions)

            sample = self._sample_beta(alpha, beta)

            if sample > best_sample:
                best_sample = sample
                best_variant = variant

        if best_variant is None:
            best_variant = experiment.variants[0]

        return best_variant.id

    # ------------------------------------------------------------------
    # Early stopping
    # ------------------------------------------------------------------

    def should_stop_early(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
    ) -> Tuple[bool, str]:
        """Determine if the experiment should be stopped early.

        Uses a combination of statistical significance and
        Bayesian probability to make the decision.

        Returns:
            Tuple of (should_stop, reason).
        """
        control = experiment.control_variant
        if control is None:
            return (False, "No control variant")

        control_result = None
        treatment_results = []
        for r in results:
            if r.variant_id == control.id:
                control_result = r
            else:
                treatment_results.append(r)

        if control_result is None or not treatment_results:
            return (False, "Insufficient data")

        for treatment in treatment_results:
            # Check for significant negative result (harm detection)
            stat = self.analyzer._compare_variants(
                control_result, treatment, experiment.confidence_level
            )

            if stat.is_significant and stat.relative_uplift < -0.1:
                return (
                    True,
                    f"Variant '{treatment.variant_name}' is significantly worse "
                    f"({stat.relative_uplift:.1%} vs control, p={stat.p_value:.4f}). "
                    "Stopping to prevent further harm.",
                )

            # Check for overwhelming positive result
            bayesian = self.bayesian_analysis(
                control_result.conversions,
                control_result.visitors,
                treatment.conversions,
                treatment.visitors,
            )

            if (
                bayesian.probability_treatment_better >= 0.99
                and stat.relative_uplift > 0
            ):
                return (
                    True,
                    f"Variant '{treatment.name}' has overwhelming evidence of "
                    f"superiority ({bayesian.probability_treatment_better:.1%} probability).",
                )

        return (False, "Continue experiment")

    # ------------------------------------------------------------------
    # Traffic optimization
    # ------------------------------------------------------------------

    def optimize_traffic_allocation(
        self,
        experiment: Experiment,
        results: List[ExperimentResult],
    ) -> Dict[str, float]:
        """Suggest optimized traffic allocations based on performance.

        Allocates more traffic to better-performing variants while
        maintaining minimum allocation for exploration.

        Returns:
            Dict mapping variant_id to recommended traffic allocation.
        """
        if not results:
            return {v.id: v.traffic_allocation for v in experiment.variants}

        # Calculate performance scores
        scores: Dict[str, float] = {}
        for r in results:
            if r.visitors > 0:
                # Use conversion rate as performance score
                scores[r.variant_id] = r.conversion_rate
            else:
                scores[r.variant_id] = 0.0

        total_score = sum(scores.values())
        if total_score == 0:
            return {v.id: v.traffic_allocation for v in experiment.variants}

        # Minimum 10% allocation for exploration
        min_allocation = 10.0
        num_variants = len(experiment.variants)
        reserved = min_allocation * num_variants
        distributable = 100.0 - reserved

        allocations: Dict[str, float] = {}
        for variant in experiment.variants:
            score = scores.get(variant.id, 0.0)
            proportion = score / total_score
            allocations[variant.id] = round(
                min_allocation + distributable * proportion, 2
            )

        # Normalize to exactly 100%
        total = sum(allocations.values())
        if total != 100.0:
            # Adjust the largest allocation
            max_id = max(allocations, key=lambda k: allocations[k])
            allocations[max_id] += round(100.0 - total, 2)

        return allocations
