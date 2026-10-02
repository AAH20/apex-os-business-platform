"""Anomaly detection for numeric time series.

Four detectors are provided:

- ``zscore`` — global z-score against the series mean/std.
- ``modified_zscore`` — robust z-score using median and MAD.
- ``iqr`` — Tukey fences (Q1 - k·IQR, Q3 + k·IQR).
- ``rolling_zscore`` — z-score against a trailing window (good for
  non-stationary series where the baseline drifts).

All detectors return a list of :class:`Anomaly` records.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

Number = (int, float)


@dataclass
class Anomaly:
    """A detected anomalous observation."""

    index: int
    value: float
    score: float
    method: str
    reason: str
    expected_low: Optional[float] = None
    expected_high: Optional[float] = None

    def to_dict(self) -> Dict:
        """Return a JSON-serialisable dict."""
        return {
            "index": self.index,
            "value": self.value,
            "score": self.score,
            "method": self.method,
            "reason": self.reason,
            "expected_low": self.expected_low,
            "expected_high": self.expected_high,
        }


def _validate_series(series: Sequence[Number]) -> List[float]:
    values = [float(v) for v in series]
    if not values:
        raise ValueError("series must not be empty")
    return values


def _mean_std(values: List[float]) -> tuple:
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var)


def _median(values: List[float]) -> float:
    return statistics.median(values)


def _mad(values: List[float], median: Optional[float] = None) -> float:
    """Median absolute deviation."""
    if median is None:
        median = _median(values)
    return _median([abs(v - median) for v in values])


def _quantile(sorted_values: List[float], q: float) -> float:
    """Linear-interpolation quantile (same method as numpy's default)."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    frac = pos - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def detect_zscore(
    series: Sequence[Number], threshold: float = 3.0
) -> List[Anomaly]:
    """Flag points whose |z-score| exceeds *threshold*."""
    values = _validate_series(series)
    if threshold <= 0:
        raise ValueError("threshold must be > 0")
    mean, std = _mean_std(values)
    anomalies: List[Anomaly] = []
    if std == 0:
        return anomalies
    for i, v in enumerate(values):
        z = (v - mean) / std
        if abs(z) > threshold:
            anomalies.append(
                Anomaly(
                    index=i,
                    value=v,
                    score=z,
                    method="zscore",
                    reason=f"z-score {z:.3f} exceeds ±{threshold}",
                    expected_low=mean - threshold * std,
                    expected_high=mean + threshold * std,
                )
            )
    return anomalies


def detect_modified_zscore(
    series: Sequence[Number], threshold: float = 3.5
) -> List[Anomaly]:
    """Robust z-score using median and MAD (Iglewicz & Hoaglin).

    The modified score is ``0.6745 * (x - median) / MAD``.
    """
    values = _validate_series(series)
    if threshold <= 0:
        raise ValueError("threshold must be > 0")
    med = _median(values)
    mad = _mad(values, med)
    anomalies: List[Anomaly] = []
    if mad == 0:
        return anomalies
    for i, v in enumerate(values):
        score = 0.6745 * (v - med) / mad
        if abs(score) > threshold:
            anomalies.append(
                Anomaly(
                    index=i,
                    value=v,
                    score=score,
                    method="modified_zscore",
                    reason=f"modified z-score {score:.3f} exceeds ±{threshold}",
                    expected_low=med - threshold * mad / 0.6745,
                    expected_high=med + threshold * mad / 0.6745,
                )
            )
    return anomalies


def detect_iqr(
    series: Sequence[Number], factor: float = 1.5
) -> List[Anomaly]:
    """Tukey fence outlier detection.

    Points outside ``[Q1 - factor·IQR, Q3 + factor·IQR]`` are anomalies.
    """
    values = _validate_series(series)
    if factor <= 0:
        raise ValueError("factor must be > 0")
    ordered = sorted(values)
    q1 = _quantile(ordered, 0.25)
    q3 = _quantile(ordered, 0.75)
    iqr = q3 - q1
    low = q1 - factor * iqr
    high = q3 + factor * iqr
    anomalies: List[Anomaly] = []
    for i, v in enumerate(values):
        if v < low or v > high:
            score = (v - q1) / iqr if iqr > 0 else 0.0
            anomalies.append(
                Anomaly(
                    index=i,
                    value=v,
                    score=score,
                    method="iqr",
                    reason=f"value {v} outside [{low:.4f}, {high:.4f}]",
                    expected_low=low,
                    expected_high=high,
                )
            )
    return anomalies


def detect_rolling_zscore(
    series: Sequence[Number],
    window: int = 7,
    threshold: float = 3.0,
    min_periods: Optional[int] = None,
) -> List[Anomaly]:
    """Z-score against a trailing rolling mean/std.

    Useful when the series has a trend or seasonality so a global
    baseline is inappropriate. The first ``window - 1`` points are
    scored against an expanding window instead.
    """
    values = _validate_series(series)
    if window < 2:
        raise ValueError("window must be >= 2")
    if threshold <= 0:
        raise ValueError("threshold must be > 0")
    min_periods = min_periods or max(2, window // 2)
    anomalies: List[Anomaly] = []
    for i, v in enumerate(values):
        lo = max(0, i - window)
        history = values[lo:i]
        if len(history) < min_periods:
            continue
        mean, std = _mean_std(history)
        if std == 0:
            continue
        z = (v - mean) / std
        if abs(z) > threshold:
            anomalies.append(
                Anomaly(
                    index=i,
                    value=v,
                    score=z,
                    method="rolling_zscore",
                    reason=f"rolling z-score {z:.3f} exceeds ±{threshold}",
                    expected_low=mean - threshold * std,
                    expected_high=mean + threshold * std,
                )
            )
    return anomalies


class AnomalyDetector:
    """Unified anomaly-detection interface.

    Example
    -------
    >>> det = AnomalyDetector(method="iqr", factor=1.5)
    >>> anomalies = det.detect([10, 11, 12, 13, 100])
    """

    _METHODS = {
        "zscore": detect_zscore,
        "modified_zscore": detect_modified_zscore,
        "iqr": detect_iqr,
        "rolling_zscore": detect_rolling_zscore,
    }

    def __init__(
        self,
        method: str = "zscore",
        threshold: float = 3.0,
        window: int = 7,
        factor: float = 1.5,
    ):
        if method not in self._METHODS:
            raise ValueError(f"method must be one of {sorted(self._METHODS)}")
        self.method = method
        self.threshold = threshold
        self.window = window
        self.factor = factor

    def detect(self, series: Sequence[Number]) -> List[Anomaly]:
        """Detect anomalies in *series* using the configured method."""
        fn = self._METHODS[self.method]
        if self.method == "iqr":
            return fn(series, factor=self.factor)
        if self.method == "rolling_zscore":
            return fn(series, window=self.window, threshold=self.threshold)
        return fn(series, threshold=self.threshold)

    def detect_from_metrics(self, metrics: Sequence) -> List[Anomaly]:
        """Detect anomalies from Metric-like objects (ordered by timestamp)."""
        items = list(metrics)
        if not items:
            raise ValueError("metrics must not be empty")

        def sort_key(m):
            ts = getattr(m, "timestamp", None)
            return ts if ts is not None else ""

        items.sort(key=sort_key)
        series = [float(getattr(m, "value", m)) for m in items]
        return self.detect(series)

    def summary(self, series: Sequence[Number]) -> Dict:
        """Return a summary dict with count and details of anomalies."""
        anomalies = self.detect(series)
        return {
            "method": self.method,
            "threshold": self.threshold,
            "series_length": len(series),
            "anomaly_count": len(anomalies),
            "anomaly_rate": len(anomalies) / len(series) if series else 0.0,
            "anomalies": [a.to_dict() for a in anomalies],
        }
