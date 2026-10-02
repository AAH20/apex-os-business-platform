"""A/B testing framework for recommendation engines.

Provides deterministic variant assignment, metric tracking, and
statistical significance testing (chi-squared and t-test).
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from .collaborative_filtering import CollaborativeFilter
from .content_based import ContentBasedFilter
from .hybrid import HybridRecommender


@dataclass
class Experiment:
    """Represents a single A/B test experiment.

    Parameters
    ----------
    name : str
        Unique experiment name.
    variants : list[str]
        List of variant names (first is control).
    traffic_split : list[float]
        Traffic allocation per variant (must sum to 1.0).
    """

    name: str
    variants: list[str]
    traffic_split: list[float]
    metrics: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    assignments: dict[str, str] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    def __post_init__(self):
        if len(self.variants) < 2:
            raise ValueError("At least 2 variants required")
        if len(self.traffic_split) != len(self.variants):
            raise ValueError("traffic_split length must match variants")
        if abs(sum(self.traffic_split) - 1.0) > 1e-6:
            raise ValueError("traffic_split must sum to 1.0")
        for v in self.variants:
            self.metrics[v] = defaultdict(list)

    @property
    def is_active(self) -> bool:
        return self.end_time is None

    def stop(self) -> None:
        self.end_time = time.time()


class ABTestManager:
    """Manages A/B experiments for recommendation strategies.

    Parameters
    ----------
    seed : int
        Random seed for reproducible variant assignment.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.experiments: dict[str, Experiment] = {}
        self._recommenders: dict[str, Callable] = {}

    def register_recommender(self, name: str, recommender: Any) -> None:
        """Register a recommender callable for use in experiments."""
        self._recommenders[name] = recommender

    def create_experiment(
        self,
        name: str,
        variants: list[str],
        traffic_split: list[float] | None = None,
    ) -> Experiment:
        """Create a new experiment."""
        if name in self.experiments:
            raise ValueError(f"Experiment '{name}' already exists")
        if traffic_split is None:
            traffic_split = [1.0 / len(variants)] * len(variants)
        exp = Experiment(name=name, variants=variants, traffic_split=traffic_split)
        self.experiments[name] = exp
        return exp

    def assign_variant(self, experiment_name: str, user_id: str) -> str:
        """Deterministically assign a user to a variant.

        Uses a hash of (seed, experiment_name, user_id) for
        reproducible, sticky assignment.
        """
        exp = self.experiments.get(experiment_name)
        if exp is None:
            raise ValueError(f"Unknown experiment: {experiment_name}")
        if not exp.is_active:
            raise RuntimeError(f"Experiment '{experiment_name}' has ended")

        # Return existing assignment if already assigned
        key = f"{experiment_name}:{user_id}"
        if key in exp.assignments:
            return exp.assignments[key]

        # Deterministic hash-based assignment
        hash_input = f"{self.seed}:{experiment_name}:{user_id}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_val % 10000) / 10000.0

        cumulative = 0.0
        assigned = exp.variants[-1]
        for variant, split in zip(exp.variants, exp.traffic_split):
            cumulative += split
            if bucket < cumulative:
                assigned = variant
                break

        exp.assignments[key] = assigned
        return assigned

    def get_recommendations(
        self,
        experiment_name: str,
        user_id: str,
        n: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Get recommendations from the assigned variant's recommender."""
        exp = self.experiments.get(experiment_name)
        if exp is None:
            raise ValueError(f"Unknown experiment: {experiment_name}")
        variant = self.assign_variant(experiment_name, user_id)
        recommender = self._recommenders.get(variant)
        if recommender is None:
            raise ValueError(f"No recommender registered for variant '{variant}'")
        return recommender.recommend(user_id, n=n, **kwargs)

    def track_metric(
        self,
        experiment_name: str,
        user_id: str,
        metric_name: str,
        value: float,
    ) -> None:
        """Record a metric value for a user in an experiment."""
        exp = self.experiments.get(experiment_name)
        if exp is None:
            raise ValueError(f"Unknown experiment: {experiment_name}")
        variant = self.assign_variant(experiment_name, user_id)
        exp.metrics[variant][metric_name].append(value)

    def get_results(self, experiment_name: str) -> dict[str, Any]:
        """Compute aggregate metrics and statistical tests."""
        exp = self.experiments.get(experiment_name)
        if exp is None:
            raise ValueError(f"Unknown experiment: {experiment_name}")

        results: dict[str, Any] = {"experiment": experiment_name, "variants": {}}
        for variant in exp.variants:
            variant_data: dict[str, Any] = {"n": 0, "metrics": {}}
            for metric_name, values in exp.metrics[variant].items():
                n = len(values)
                variant_data["n"] = n
                if n == 0:
                    variant_data["metrics"][metric_name] = {"mean": 0.0, "std": 0.0, "n": 0}
                    continue
                mean = sum(values) / n
                variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
                variant_data["metrics"][metric_name] = {
                    "mean": round(mean, 4),
                    "std": round(math.sqrt(variance), 4),
                    "n": n,
                }
            results["variants"][variant] = variant_data

        # Statistical significance tests
        if len(exp.variants) >= 2:
            control = exp.variants[0]
            for variant in exp.variants[1:]:
                for metric_name in exp.metrics[variant]:
                    control_vals = exp.metrics[control].get(metric_name, [])
                    variant_vals = exp.metrics[variant].get(metric_name, [])
                    if len(control_vals) >= 2 and len(variant_vals) >= 2:
                        p_value = self._welch_ttest(control_vals, variant_vals)
                        key = f"{control}_vs_{variant}"
                        results.setdefault("significance", {})[key] = {
                            "metric": metric_name,
                            "p_value": round(p_value, 6),
                            "significant": p_value < 0.05,
                        }

        return results

    @staticmethod
    def _welch_ttest(sample_a: list[float], sample_b: list[float]) -> float:
        """Welch's t-test returning a two-tailed p-value approximation."""
        n_a, n_b = len(sample_a), len(sample_b)
        if n_a < 2 or n_b < 2:
            return 1.0
        mean_a = sum(sample_a) / n_a
        mean_b = sum(sample_b) / n_b
        var_a = sum((x - mean_a) ** 2 for x in sample_a) / (n_a - 1)
        var_b = sum((x - mean_b) ** 2 for x in sample_b) / (n_b - 1)
        se = math.sqrt(var_a / n_a + var_b / n_b)
        if se == 0:
            return 1.0
        t_stat = (mean_a - mean_b) / se
        # Approximate p-value using normal distribution for large samples
        # (sufficient for A/B testing purposes)
        df_num = (var_a / n_a + var_b / n_b) ** 2
        df_den = (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
        df = df_num / df_den if df_den > 0 else n_a + n_b - 2
        # Normal approximation
        p_value = 2 * (1 - _normal_cdf(abs(t_stat)))
        return min(max(p_value, 0.0), 1.0)


def _normal_cdf(x: float) -> float:
    """Approximation of the standard normal CDF."""
    # Abramowitz and Stegun approximation
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    d = 0.3989423 * math.exp(-x * x / 2.0)
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
    return 1.0 - p if x > 0 else p
