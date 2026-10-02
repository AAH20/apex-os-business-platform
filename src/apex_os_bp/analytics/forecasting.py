"""Time-series forecasting.

Pure-Python implementations of common forecasting methods:
- Naive (last value)
- Simple moving average (SMA)
- Exponential smoothing (EMA / Holt)
- Linear trend (least-squares extrapolation)

Each method returns a :class:`Forecast` with point predictions and
approximate confidence intervals derived from residual spread.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

Number = (int, float)


@dataclass
class ForecastPoint:
    """A single forecast point with confidence bounds."""

    step: int
    value: float
    lower: float
    upper: float
    timestamp: Optional[str] = None


@dataclass
class Forecast:
    """Forecast result container."""

    method: str
    points: List[ForecastPoint] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    @property
    def values(self) -> List[float]:
        """Return just the predicted values."""
        return [p.value for p in self.points]

    @property
    def mean(self) -> float:
        """Mean of predicted values."""
        if not self.points:
            return 0.0
        return sum(p.value for p in self.points) / len(self.points)

    def summary(self) -> Dict:
        """Return a JSON-serialisable summary."""
        return {
            "method": self.method,
            "steps": len(self.points),
            "values": self.values,
            "mean": self.mean,
            "metadata": self.metadata,
        }


def _validate_series(series: Sequence[Number]) -> List[float]:
    """Coerce and validate a numeric series."""
    values = [float(v) for v in series]
    if not values:
        raise ValueError("series must not be empty")
    return values


def _residual_std(history: List[float], fitted: List[float]) -> float:
    """Standard deviation of residuals (history minus fitted)."""
    if len(history) < 2:
        return 0.0
    n = min(len(history), len(fitted))
    if n < 2:
        return 0.0
    residuals = [history[i] - fitted[i] for i in range(n)]
    mean_r = sum(residuals) / n
    var = sum((r - mean_r) ** 2 for r in residuals) / (n - 1)
    return math.sqrt(var)


def moving_average(series: Sequence[Number], window: int = 3) -> List[float]:
    """Simple moving average smoothing.

    Returns a list the same length as *series*; the first ``window - 1``
    entries use the expanding mean of available data.
    """
    values = _validate_series(series)
    if window < 1:
        raise ValueError("window must be >= 1")
    out: List[float] = []
    for i in range(len(values)):
        lo = max(0, i - window + 1)
        chunk = values[lo : i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def exponential_smoothing(series: Sequence[Number], alpha: float = 0.3) -> List[float]:
    """Single exponential smoothing.

    ``alpha`` in (0, 1]; higher values weight recent observations more.
    """
    values = _validate_series(series)
    if not 0.0 < alpha <= 1.0:
        raise ValueError("alpha must be in (0, 1]")
    out: List[float] = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def linear_trend(series: Sequence[Number]) -> Tuple[float, float]:
    """Least-squares fit ``y = slope * x + intercept``.

    Returns ``(slope, intercept)`` over x = 0..n-1.
    """
    values = _validate_series(series)
    n = len(values)
    if n < 2:
        return 0.0, values[0]
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((xs[i] - mean_x) * (values[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return 0.0, mean_y
    slope = num / den
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _naive_forecast(values: List[float], steps: int, z: float) -> List[ForecastPoint]:
    last = values[-1]
    std = _residual_std(values, values[:-1] + [values[-1]])
    return [
        ForecastPoint(
            step=i + 1,
            value=last,
            lower=last - z * std,
            upper=last + z * std,
        )
        for i in range(steps)
    ]


def _sma_forecast(
    values: List[float], steps: int, window: int, z: float
) -> List[ForecastPoint]:
    smoothed = moving_average(values, window)
    forecast_val = smoothed[-1]
    std = _residual_std(values, smoothed)
    return [
        ForecastPoint(
            step=i + 1,
            value=forecast_val,
            lower=forecast_val - z * std,
            upper=forecast_val + z * std,
        )
        for i in range(steps)
    ]


def _ema_forecast(
    values: List[float], steps: int, alpha: float, z: float
) -> List[ForecastPoint]:
    smoothed = exponential_smoothing(values, alpha)
    forecast_val = smoothed[-1]
    std = _residual_std(values, smoothed)
    return [
        ForecastPoint(
            step=i + 1,
            value=forecast_val,
            lower=forecast_val - z * std,
            upper=forecast_val + z * std,
        )
        for i in range(steps)
    ]


def _linear_forecast(
    values: List[float], steps: int, z: float
) -> List[ForecastPoint]:
    slope, intercept = linear_trend(values)
    n = len(values)
    fitted = [slope * i + intercept for i in range(n)]
    std = _residual_std(values, fitted)
    # Widen the interval as we extrapolate further from the data.
    return [
        ForecastPoint(
            step=i + 1,
            value=slope * (n + i) + intercept,
            lower=slope * (n + i) + intercept - z * math.sqrt(1 + i) * std,
            upper=slope * (n + i) + intercept + z * math.sqrt(1 + i) * std,
        )
        for i in range(steps)
    ]


def forecast(
    series: Sequence[Number],
    steps: int = 1,
    method: str = "auto",
    alpha: float = 0.3,
    window: int = 3,
    confidence: float = 1.96,
) -> Forecast:
    """Forecast *steps* points ahead.

    Parameters
    ----------
    series:
        Historical observations, oldest first.
    steps:
        Number of future points to predict.
    method:
        One of ``"auto"``, ``"naive"``, ``"sma"``, ``"ema"``, ``"linear"``.
        ``"auto"`` picks ``"linear"`` for series with >= 5 points and a
        non-zero slope, ``"ema"`` for series with >= 3 points, else
        ``"naive"``.
    alpha:
        Smoothing factor for EMA.
    window:
        Window size for SMA.
    confidence:
        Z-score multiplier for the confidence interval (1.96 ≈ 95%).
    """
    values = _validate_series(series)
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if confidence <= 0:
        raise ValueError("confidence must be > 0")

    method = method.lower()
    valid = {"auto", "naive", "sma", "ema", "linear"}
    if method not in valid:
        raise ValueError(f"method must be one of {sorted(valid)}")

    if method == "auto":
        if len(values) >= 5:
            slope, _ = linear_trend(values)
            method = "linear" if abs(slope) > 1e-12 else "ema"
        elif len(values) >= 3:
            method = "ema"
        else:
            method = "naive"

    builders = {
        "naive": lambda: _naive_forecast(values, steps, confidence),
        "sma": lambda: _sma_forecast(values, steps, window, confidence),
        "ema": lambda: _ema_forecast(values, steps, alpha, confidence),
        "linear": lambda: _linear_forecast(values, steps, confidence),
    }
    points = builders[method]()

    return Forecast(
        method=method,
        points=points,
        metadata={
            "history_length": len(values),
            "alpha": alpha if method == "ema" else None,
            "window": window if method == "sma" else None,
            "confidence_z": confidence,
        },
    )


def forecast_from_metrics(metrics: Sequence, steps: int = 1, **kwargs) -> Forecast:
    """Convenience wrapper: forecast from a sequence of Metric-like objects.

    Each item must expose a numeric ``value`` attribute (or be a plain
    number). Items are ordered by their ``timestamp`` when available.
    """
    items = list(metrics)
    if not items:
        raise ValueError("metrics must not be empty")

    def sort_key(m):
        ts = getattr(m, "timestamp", None)
        return ts if ts is not None else ""

    items.sort(key=sort_key)
    series = [float(getattr(m, "value", m)) for m in items]
    return forecast(series, steps=steps, **kwargs)
