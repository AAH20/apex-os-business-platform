"""Resource demand forecasting module."""

from dataclasses import dataclass, field
from typing import List, Literal
import statistics


@dataclass
class ForecastResult:
    """Result of a demand forecast."""

    values: List[float]
    method: str
    confidence_lower: List[float] = field(default_factory=list)
    confidence_upper: List[float] = field(default_factory=list)


def _linear_regression(data: List[float]) -> tuple:
    """Compute slope and intercept for linear regression."""
    n = len(data)
    if n < 2:
        return 0.0, data[0] if data else 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(data) / n
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(data))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0, y_mean
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept


def _compute_std_residuals(data: List[float], slope: float, intercept: float) -> float:
    """Compute standard deviation of residuals for confidence intervals."""
    n = len(data)
    if n < 3:
        return 0.0
    residuals = [data[i] - (slope * i + intercept) for i in range(n)]
    return statistics.stdev(residuals) if len(residuals) > 1 else 0.0


def _linear_forecast(data: List[float], periods: int) -> ForecastResult:
    """Forecast using linear regression."""
    slope, intercept = _linear_regression(data)
    n = len(data)
    std = _compute_std_residuals(data, slope, intercept)

    values = [slope * (n + i) + intercept for i in range(periods)]
    confidence_lower = [v - 1.96 * std for v in values]
    confidence_upper = [v + 1.96 * std for v in values]

    return ForecastResult(
        values=values,
        method="linear",
        confidence_lower=confidence_lower,
        confidence_upper=confidence_upper,
    )


def _moving_average_forecast(data: List[float], periods: int, window: int = 3) -> ForecastResult:
    """Forecast using moving average."""
    if window > len(data):
        window = len(data)

    values = []
    extended = list(data)
    for _ in range(periods):
        recent = extended[-window:] if len(extended) >= window else extended[:]
        avg = sum(recent) / len(recent)
        values.append(avg)
        extended.append(avg)

    std = statistics.stdev(data) if len(data) > 1 else 0.0
    confidence_lower = [v - 1.96 * std for v in values]
    confidence_upper = [v + 1.96 * std for v in values]

    return ForecastResult(
        values=values,
        method="moving_average",
        confidence_lower=confidence_lower,
        confidence_upper=confidence_upper,
    )


def _exponential_smoothing_forecast(
    data: List[float], periods: int, alpha: float = 0.3
) -> ForecastResult:
    """Forecast using exponential smoothing."""
    if not 0 < alpha <= 1:
        raise ValueError("Alpha must be between 0 and 1")

    smoothed = data[0]
    for value in data[1:]:
        smoothed = alpha * value + (1 - alpha) * smoothed

    values = [smoothed] * periods

    std = statistics.stdev(data) if len(data) > 1 else 0.0
    confidence_lower = [v - 1.96 * std for v in values]
    confidence_upper = [v + 1.96 * std for v in values]

    return ForecastResult(
        values=values,
        method="exponential_smoothing",
        confidence_lower=confidence_lower,
        confidence_upper=confidence_upper,
    )


def forecast_demand(
    historical_data: List[float],
    periods: int,
    method: Literal["linear", "moving_average", "exponential_smoothing"] = "linear",
) -> ForecastResult:
    """Forecast future resource demand.

    Args:
        historical_data: List of historical demand values.
        periods: Number of future periods to forecast.
        method: Forecasting method to use.

    Returns:
        ForecastResult with predicted values and confidence intervals.
    """
    if not historical_data:
        raise ValueError("Historical data cannot be empty")
    if periods <= 0:
        raise ValueError("Periods must be positive")

    if method == "linear":
        return _linear_forecast(historical_data, periods)
    elif method == "moving_average":
        return _moving_average_forecast(historical_data, periods)
    elif method == "exponential_smoothing":
        return _exponential_smoothing_forecast(historical_data, periods)
    else:
        raise ValueError(f"Unknown forecasting method: {method}")