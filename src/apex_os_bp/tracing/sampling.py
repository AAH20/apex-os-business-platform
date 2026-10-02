"""Trace sampling strategies for APEX-OS Business Platform.

Sampling determines which traces are recorded and exported.
Multiple strategies are supported:
- AlwaysOn: sample everything
- AlwaysOff: sample nothing
- RateBased: sample at a fixed rate per second
- Probabilistic: sample based on a probability
- TailBased: sample based on trace characteristics after completion
"""
from __future__ import annotations

import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SamplingDecision:
    """Result of a sampling decision."""
    sampled: bool
    attributes: Dict[str, Any] = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


class SamplingStrategy(ABC):
    """Abstract base class for sampling strategies."""

    @abstractmethod
    def should_sample(self, trace_id: str, span_name: str, attributes: Optional[Dict[str, Any]] = None) -> SamplingDecision:
        """Determine if a span should be sampled."""
        pass


class AlwaysOnSampler(SamplingStrategy):
    """Samples all traces."""

    def should_sample(self, trace_id: str, span_name: str, attributes: Optional[Dict[str, Any]] = None) -> SamplingDecision:
        return SamplingDecision(sampled=True)


class AlwaysOffSampler(SamplingStrategy):
    """Samples no traces."""

    def should_sample(self, trace_id: str, span_name: str, attributes: Optional[Dict[str, Any]] = None) -> SamplingDecision:
        return SamplingDecision(sampled=False)


class RateBasedSampler(SamplingStrategy):
    """Samples at a fixed rate per second using token bucket.

    Args:
        samples_per_second: Maximum number of traces to sample per second.
    """

    def __init__(self, samples_per_second: float = 1.0):
        self._samples_per_second = samples_per_second
        self._tokens = samples_per_second
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def should_sample(self, trace_id: str, span_name: str, attributes: Optional[Dict[str, Any]] = None) -> SamplingDecision:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._samples_per_second, self._tokens + elapsed * self._samples_per_second)
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return SamplingDecision(sampled=True)
            return SamplingDecision(sampled=False)


class ProbabilisticSampler(SamplingStrategy):
    """Samples based on a fixed probability.

    Args:
        probability: Float between 0.0 and 1.0.
    """

    def __init__(self, probability: float = 0.1):
        if not 0.0 <= probability <= 1.0:
            raise ValueError(f"Probability must be between 0.0 and 1.0, got {probability}")
        self._probability = probability

    def should_sample(self, trace_id: str, span_name: str, attributes: Optional[Dict[str, Any]] = None) -> SamplingDecision:
        sampled = random.random() < self._probability
        return SamplingDecision(
            sampled=sampled,
            attributes={"sampling.probability": self._probability},
        )


class TailBasedSampler(SamplingStrategy):
    """Samples based on trace characteristics after completion.

    Can be configured to sample traces that:
    - Exceed a duration threshold
    - Contain errors
    - Match specific attribute values

    Args:
        duration_threshold_ms: Sample traces longer than this (None to disable).
        sample_errors: Whether to sample traces containing errors.
        attribute_rules: Dict of attribute key to value for matching.
    """

    def __init__(
        self,
        duration_threshold_ms: Optional[float] = None,
        sample_errors: bool = True,
        attribute_rules: Optional[Dict[str, Any]] = None,
    ):
        self._duration_threshold_ms = duration_threshold_ms
        self._sample_errors = sample_errors
        self._attribute_rules = attribute_rules or {}

    def should_sample(self, trace_id: str, span_name: str, attributes: Optional[Dict[str, Any]] = None) -> SamplingDecision:
        attrs = attributes or {}

        # Check error status
        if self._sample_errors and attrs.get("error") is True:
            return SamplingDecision(sampled=True, attributes={"sampling.reason": "error"})

        # Check attribute rules
        for key, expected_value in self._attribute_rules.items():
            if attrs.get(key) == expected_value:
                return SamplingDecision(
                    sampled=True,
                    attributes={"sampling.reason": f"attribute_match:{key}"},
                )

        return SamplingDecision(sampled=False)

    def should_sample_completed_trace(
        self,
        duration_ms: float,
        has_error: bool,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> SamplingDecision:
        """Evaluate sampling for a completed trace."""
        if self._sample_errors and has_error:
            return SamplingDecision(sampled=True, attributes={"sampling.reason": "error"})

        if self._duration_threshold_ms is not None and duration_ms >= self._duration_threshold_ms:
            return SamplingDecision(
                sampled=True,
                attributes={"sampling.reason": "duration_threshold"},
            )

        attrs = attributes or {}
        for key, expected_value in self._attribute_rules.items():
            if attrs.get(key) == expected_value:
                return SamplingDecision(
                    sampled=True,
                    attributes={"sampling.reason": f"attribute_match:{key}"},
                )

        return SamplingDecision(sampled=False)
