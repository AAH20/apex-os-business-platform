"""A/B testing component for APEX-OS ML Platform."""

from __future__ import annotations

import hashlib
import math
import random
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ABTestConfig:
    """Configuration for an A/B test."""

    test_name: str
    control_model_id: str
    treatment_model_id: str
    traffic_split: float = 0.5  # Fraction of traffic to treatment
    confidence_level: float = 0.95
    min_sample_size: int = 100
    max_sample_size: int = 100000
    random_seed: int = 42

    def __post_init__(self):
        if not 0 < self.traffic_split < 1:
            raise ValueError("traffic_split must be between 0 and 1")
        if not 0 < self.confidence_level < 1:
            raise ValueError("confidence_level must be between 0 and 1")


@dataclass
class ABTestResult:
    """Results of an A/B test."""

    test_name: str
    control_model_id: str
    treatment_model_id: str
    control_size: int
    treatment_size: int
    control_mean: float
    treatment_mean: float
    control_std: float
    treatment_std: float
    difference: float
    relative_difference: float
    z_score: float
    p_value: float
    confidence_interval: Tuple[float, float]
    is_significant: bool
    winner: str  # "control", "treatment", "inconclusive"
    test_duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "control_model_id": self.control_model_id,
            "treatment_model_id": self.treatment_model_id,
            "control_size": self.control_size,
            "treatment_size": self.treatment_size,
            "control_mean": self.control_mean,
            "treatment_mean": self.treatment_mean,
            "control_std": self.control_std,
            "treatment_std": self.treatment_std,
            "difference": self.difference,
            "relative_difference": self.relative_difference,
            "z_score": self.z_score,
            "p_value": self.p_value,
            "confidence_interval": list(self.confidence_interval),
            "is_significant": self.is_significant,
            "winner": self.winner,
            "test_duration_seconds": self.test_duration_seconds,
        }


class ABTest:
    """Manages A/B tests between two model variants."""

    def __init__(self, config: ABTestConfig):
        self.config = config
        self._control_outcomes: List[float] = []
        self._treatment_outcomes: List[float] = []
        self._control_latencies: List[float] = []
        self._treatment_latencies: List[float] = []
        self._start_time = time.time()
        self._rng = random.Random(config.random_seed)
        self._is_active = True

    def assign_variant(self, entity_id: str) -> str:
        """Assign an entity to control or treatment.

        Uses consistent hashing for deterministic assignment.
        """
        hash_val = int(hashlib.sha256(entity_id.encode()).hexdigest(), 16)
        normalized = (hash_val % 10000) / 10000.0
        return "treatment" if normalized < self.config.traffic_split else "control"

    def record_outcome(
        self,
        variant: str,
        outcome: float,
        latency_ms: Optional[float] = None,
    ) -> None:
        """Record an outcome for a variant."""
        if not self._is_active:
            raise RuntimeError("Test is no longer active")
        if variant == "control":
            self._control_outcomes.append(outcome)
            if latency_ms is not None:
                self._control_latencies.append(latency_ms)
        elif variant == "treatment":
            self._treatment_outcomes.append(outcome)
            if latency_ms is not None:
                self._treatment_latencies.append(latency_ms)
        else:
            raise ValueError(f"Unknown variant: {variant}")

    def get_result(self) -> ABTestResult:
        """Compute and return the A/B test result."""
        control_size = len(self._control_outcomes)
        treatment_size = len(self._treatment_outcomes)

        if control_size == 0 or treatment_size == 0:
            return ABTestResult(
                test_name=self.config.test_name,
                control_model_id=self.config.control_model_id,
                treatment_model_id=self.config.treatment_model_id,
                control_size=control_size,
                treatment_size=treatment_size,
                control_mean=0.0,
                treatment_mean=0.0,
                control_std=0.0,
                treatment_std=0.0,
                difference=0.0,
                relative_difference=0.0,
                z_score=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                is_significant=False,
                winner="inconclusive",
                test_duration_seconds=time.time() - self._start_time,
            )

        control_mean = statistics.mean(self._control_outcomes)
        treatment_mean = statistics.mean(self._treatment_outcomes)
        control_std = statistics.stdev(self._control_outcomes) if control_size > 1 else 0.0
        treatment_std = statistics.stdev(self._treatment_outcomes) if treatment_size > 1 else 0.0

        difference = treatment_mean - control_mean
        relative_difference = (
            difference / control_mean if control_mean != 0 else 0.0
        )

        # Two-sample z-test
        se = self._compute_standard_error(
            control_std, control_size, treatment_std, treatment_size
        )

        if se == 0:
            z_score = 0.0
            p_value = 1.0
        else:
            z_score = difference / se
            p_value = self._compute_p_value(z_score)

        # Confidence interval
        z_critical = self._z_score_for_confidence(self.config.confidence_level)
        margin = z_critical * se
        ci_lower = difference - margin
        ci_upper = difference + margin

        is_significant = p_value < (1 - self.config.confidence_level)

        if is_significant:
            winner = "treatment" if difference > 0 else "control"
        else:
            winner = "inconclusive"

        return ABTestResult(
            test_name=self.config.test_name,
            control_model_id=self.config.control_model_id,
            treatment_model_id=self.config.treatment_model_id,
            control_size=control_size,
            treatment_size=treatment_size,
            control_mean=control_mean,
            treatment_mean=treatment_mean,
            control_std=control_std,
            treatment_std=treatment_std,
            difference=difference,
            relative_difference=relative_difference,
            z_score=z_score,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            is_significant=is_significant,
            winner=winner,
            test_duration_seconds=time.time() - self._start_time,
        )

    def should_stop(self) -> Tuple[bool, str]:
        """Determine if the test should stop early.

        Returns:
            (should_stop, reason)
        """
        control_size = len(self._control_outcomes)
        treatment_size = len(self._treatment_outcomes)

        if control_size < self.config.min_sample_size or treatment_size < self.config.min_sample_size:
            return False, "insufficient_samples"

        if control_size >= self.config.max_sample_size or treatment_size >= self.config.max_sample_size:
            return True, "max_samples_reached"

        # Check for statistical significance
        result = self.get_result()
        if result.is_significant and control_size >= self.config.min_sample_size:
            return True, "statistical_significance_reached"

        return False, "continue"

    def stop(self) -> None:
        """Stop the test."""
        self._is_active = False

    def get_variant_counts(self) -> Dict[str, int]:
        """Get the number of samples in each variant."""
        return {
            "control": len(self._control_outcomes),
            "treatment": len(self._treatment_outcomes),
        }

    def _compute_standard_error(
        self,
        std1: float,
        n1: int,
        std2: float,
        n2: int,
    ) -> float:
        """Compute standard error for two-sample z-test."""
        if n1 == 0 or n2 == 0:
            return 0.0
        var1 = std1 ** 2
        var2 = std2 ** 2
        return math.sqrt(var1 / n1 + var2 / n2)

    def _compute_p_value(self, z_score: float) -> float:
        """Compute two-tailed p-value from z-score."""
        # Using the error function for the normal CDF
        p = 2 * (1 - self._normal_cdf(abs(z_score)))
        return min(max(p, 0.0), 1.0)

    def _normal_cdf(self, x: float) -> float:
        """Approximate the standard normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _z_score_for_confidence(self, confidence: float) -> float:
        """Get the z-score for a given confidence level."""
        # Common z-scores
        z_table = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
            0.999: 3.291,
        }
        return z_table.get(confidence, 1.96)


class ABTestManager:
    """Manages multiple A/B tests."""

    def __init__(self):
        self._tests: Dict[str, ABTest] = {}

    def create_test(self, config: ABTestConfig) -> ABTest:
        """Create and register a new A/B test."""
        if config.test_name in self._tests:
            raise ValueError(f"Test {config.test_name} already exists")
        test = ABTest(config)
        self._tests[config.test_name] = test
        return test

    def get_test(self, test_name: str) -> ABTest:
        """Get a test by name."""
        if test_name not in self._tests:
            raise KeyError(f"Test {test_name} not found")
        return self._tests[test_name]

    def list_tests(self) -> List[str]:
        """List all test names."""
        return list(self._tests.keys())

    def end_test(self, test_name: str) -> ABTestResult:
        """End a test and return its results."""
        test = self.get_test(test_name)
        test.stop()
        return test.get_result()

    def remove_test(self, test_name: str) -> None:
        """Remove a test."""
        if test_name in self._tests:
            self._tests[test_name].stop()
            del self._tests[test_name]
