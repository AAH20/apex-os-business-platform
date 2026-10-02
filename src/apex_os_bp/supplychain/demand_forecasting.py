"""Demand forecasting module.

Provides multiple forecasting methods for predicting future
demand based on historical data.
"""

from __future__ import annotations

import math
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional


class ForecastingMethod(str, Enum):
    """Available forecasting methods."""

    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    LINEAR_REGRESSION = "linear_regression"
    SEASONAL_NAIVE = "seasonal_naive"
    WEIGHTED_MOVING_AVERAGE = "weighted_moving_average"


@dataclass
class DemandForecast:
    """Represents a demand forecast for a product.

    Attributes:
        product_sku: Product stock-keeping unit.
        method: Forecasting method used.
        historical_data: Historical demand quantities.
        forecast_periods: Number of periods to forecast.
        alpha: Smoothing factor (for exponential smoothing).
        seasonality_period: Seasonality period (for seasonal methods).
        weights: Weights for weighted moving average.
        id: Unique identifier.
        created_at: Creation timestamp.
    """

    product_sku: str
    method: ForecastingMethod = ForecastingMethod.MOVING_AVERAGE
    historical_data: list[float] = field(default_factory=list)
    forecast_periods: int = 1
    alpha: float = 0.3
    seasonality_period: int = 1
    weights: list[float] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        if not self.product_sku:
            raise ValueError("Product SKU cannot be empty")
        if self.forecast_periods <= 0:
            raise ValueError("Forecast periods must be positive")
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError("Alpha must be between 0.0 and 1.0")
        if self.seasonality_period <= 0:
            raise ValueError("Seasonality period must be positive")
        if any(d < 0 for d in self.historical_data):
            raise ValueError("Historical data cannot contain negative values")

    @property
    def data_count(self) -> int:
        """Number of historical data points."""
        return len(self.historical_data)

    @property
    def mean_demand(self) -> float:
        """Mean of historical demand."""
        if not self.historical_data:
            return 0.0
        return statistics.mean(self.historical_data)

    @property
    def std_deviation(self) -> float:
        """Standard deviation of historical demand."""
        if len(self.historical_data) < 2:
            return 0.0
        return statistics.stdev(self.historical_data)

    @property
    def trend(self) -> float:
        """Simple trend (slope) of historical data."""
        if len(self.historical_data) < 2:
            return 0.0
        n = len(self.historical_data)
        x_mean = (n - 1) / 2
        y_mean = self.mean_demand
        numerator = sum(
            (i - x_mean) * (y - y_mean) for i, y in enumerate(self.historical_data)
        )
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator

    def to_dict(self) -> dict:
        """Serialize forecast configuration to dictionary."""
        return {
            "id": self.id,
            "product_sku": self.product_sku,
            "method": self.method.value,
            "historical_data": self.historical_data,
            "forecast_periods": self.forecast_periods,
            "alpha": self.alpha,
            "seasonality_period": self.seasonality_period,
            "weights": self.weights,
            "data_count": self.data_count,
            "mean_demand": self.mean_demand,
            "std_deviation": self.std_deviation,
            "trend": self.trend,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ForecastResult:
    """Result of a demand forecast.

    Attributes:
        product_sku: Product stock-keeping unit.
        method: Forecasting method used.
        forecast_values: Forecasted demand values.
        confidence_lower: Lower confidence bound.
        confidence_upper: Upper confidence bound.
        mae: Mean absolute error (if backtested).
        rmse: Root mean squared error (if backtested).
        mape: Mean absolute percentage error (if backtested).
        forecast_dates: Dates for each forecast period.
        id: Unique identifier.
    """

    product_sku: str
    method: ForecastingMethod
    forecast_values: list[float]
    confidence_lower: list[float] = field(default_factory=list)
    confidence_upper: list[float] = field(default_factory=list)
    mae: float = 0.0
    rmse: float = 0.0
    mape: float = 0.0
    forecast_dates: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if not self.product_sku:
            raise ValueError("Product SKU cannot be empty")
        if any(v < 0 for v in self.forecast_values):
            raise ValueError("Forecast values cannot be negative")

    @property
    def total_forecast(self) -> float:
        """Sum of all forecast values."""
        return sum(self.forecast_values)

    @property
    def average_forecast(self) -> float:
        """Average forecast value."""
        if not self.forecast_values:
            return 0.0
        return statistics.mean(self.forecast_values)

    @property
    def max_forecast(self) -> float:
        """Maximum forecast value."""
        if not self.forecast_values:
            return 0.0
        return max(self.forecast_values)

    @property
    def min_forecast(self) -> float:
        """Minimum forecast value."""
        if not self.forecast_values:
            return 0.0
        return min(self.forecast_values)

    def to_dict(self) -> dict:
        """Serialize forecast result to dictionary."""
        return {
            "id": self.id,
            "product_sku": self.product_sku,
            "method": self.method.value,
            "forecast_values": self.forecast_values,
            "confidence_lower": self.confidence_lower,
            "confidence_upper": self.confidence_upper,
            "total_forecast": self.total_forecast,
            "average_forecast": self.average_forecast,
            "max_forecast": self.max_forecast,
            "min_forecast": self.min_forecast,
            "mae": self.mae,
            "rmse": self.rmse,
            "mape": self.mape,
            "forecast_dates": self.forecast_dates,
        }


class DemandForecaster:
    """Generates demand forecasts using various methods."""

    def __init__(self) -> None:
        self._forecasts: dict[str, DemandForecast] = {}
        self._results: dict[str, list[ForecastResult]] = {}

    def create_forecast(
        self,
        product_sku: str,
        historical_data: list[float],
        method: ForecastingMethod = ForecastingMethod.MOVING_AVERAGE,
        forecast_periods: int = 1,
        alpha: float = 0.3,
        seasonality_period: int = 1,
        weights: Optional[list[float]] = None,
    ) -> DemandForecast:
        """Create a new demand forecast configuration."""
        forecast = DemandForecast(
            product_sku=product_sku,
            method=method,
            historical_data=historical_data,
            forecast_periods=forecast_periods,
            alpha=alpha,
            seasonality_period=seasonality_period,
            weights=weights or [],
        )
        self._forecasts[forecast.id] = forecast
        return forecast

    def get_forecast(self, forecast_id: str) -> Optional[DemandForecast]:
        """Retrieve a forecast configuration by ID."""
        return self._forecasts.get(forecast_id)

    def remove_forecast(self, forecast_id: str) -> bool:
        """Remove a forecast by ID. Returns True if removed."""
        if forecast_id in self._forecasts:
            del self._forecasts[forecast_id]
            return True
        return False

    def list_forecasts(
        self, product_sku: Optional[str] = None
    ) -> list[DemandForecast]:
        """List forecast configurations with optional filtering."""
        results = list(self._forecasts.values())
        if product_sku is not None:
            results = [f for f in results if f.product_sku == product_sku]
        return results

    # ── Forecasting methods ────────────────────────────────────────

    def _moving_average(self, data: list[float], periods: int) -> list[float]:
        """Simple moving average forecast."""
        if not data:
            return [0.0] * periods
        window = min(3, len(data))
        avg = statistics.mean(data[-window:])
        return [avg] * periods

    def _weighted_moving_average(
        self, data: list[float], periods: int, weights: list[float]
    ) -> list[float]:
        """Weighted moving average forecast."""
        if not data:
            return [0.0] * periods
        if not weights:
            weights = list(range(1, len(data) + 1))
        # Use only the last N data points where N = len(weights)
        n = min(len(weights), len(data))
        recent = data[-n:]
        w = weights[-n:]
        weighted_sum = sum(d * wt for d, wt in zip(recent, w))
        weight_total = sum(w)
        if weight_total == 0:
            return [0.0] * periods
        return [weighted_sum / weight_total] * periods

    def _exponential_smoothing(
        self, data: list[float], periods: int, alpha: float
    ) -> list[float]:
        """Exponential smoothing forecast."""
        if not data:
            return [0.0] * periods
        smoothed = data[0]
        for value in data[1:]:
            smoothed = alpha * value + (1 - alpha) * smoothed
        return [smoothed] * periods

    def _linear_regression(self, data: list[float], periods: int) -> list[float]:
        """Linear regression forecast."""
        if not data:
            return [0.0] * periods
        n = len(data)
        if n < 2:
            return [data[0]] * periods
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(data)
        numerator = sum(
            (i - x_mean) * (y - y_mean) for i, y in enumerate(data)
        )
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return [y_mean] * periods
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        forecasts = []
        for p in range(1, periods + 1):
            value = intercept + slope * (n - 1 + p)
            forecasts.append(max(0.0, value))
        return forecasts

    def _seasonal_naive(
        self, data: list[float], periods: int, seasonality_period: int
    ) -> list[float]:
        """Seasonal naive forecast."""
        if not data:
            return [0.0] * periods
        if seasonality_period <= 0 or seasonality_period > len(data):
            seasonality_period = 1
        forecasts = []
        for p in range(1, periods + 1):
            idx = len(data) - seasonality_period + ((p - 1) % seasonality_period)
            idx = max(0, min(idx, len(data) - 1))
            forecasts.append(data[idx])
        return forecasts

    # ── Confidence intervals ───────────────────────────────────────

    def _calculate_confidence_intervals(
        self,
        forecast_values: list[float],
        historical_data: list[float],
        confidence_level: float = 0.95,
    ) -> tuple[list[float], list[float]]:
        """Calculate confidence intervals for forecast values."""
        if not historical_data or len(historical_data) < 2:
            return (
                [0.0] * len(forecast_values),
                [f * 2 for f in forecast_values],
            )
        std_dev = statistics.stdev(historical_data)
        # Z-score for confidence level (approximation)
        z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_scores.get(confidence_level, 1.96)
        margin = z * std_dev
        lower = [max(0.0, f - margin) for f in forecast_values]
        upper = [f + margin for f in forecast_values]
        return lower, upper

    # ── Backtesting metrics ────────────────────────────────────────

    def _calculate_metrics(
        self, actual: list[float], predicted: list[float]
    ) -> tuple[float, float, float]:
        """Calculate MAE, RMSE, and MAPE."""
        if not actual or not predicted or len(actual) != len(predicted):
            return 0.0, 0.0, 0.0
        n = len(actual)
        mae = sum(abs(a - p) for a, p in zip(actual, predicted)) / n
        rmse = math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / n)
        mape_values = [
            abs((a - p) / a) * 100 for a, p in zip(actual, predicted) if a != 0
        ]
        mape = statistics.mean(mape_values) if mape_values else 0.0
        return mae, rmse, mape

    # ── Main forecast method ──────────────────────────────────────

    def generate_forecast(self, forecast_id: str) -> ForecastResult:
        """Generate a forecast result from a configuration."""
        forecast_config = self._forecasts.get(forecast_id)
        if not forecast_config:
            raise ValueError(f"Forecast {forecast_id} not found")

        data = forecast_config.historical_data
        periods = forecast_config.forecast_periods
        method = forecast_config.method

        # Generate forecast values based on method
        if method == ForecastingMethod.MOVING_AVERAGE:
            values = self._moving_average(data, periods)
        elif method == ForecastingMethod.WEIGHTED_MOVING_AVERAGE:
            values = self._weighted_moving_average(
                data, periods, forecast_config.weights
            )
        elif method == ForecastingMethod.EXPONENTIAL_SMOOTHING:
            values = self._exponential_smoothing(data, periods, forecast_config.alpha)
        elif method == ForecastingMethod.LINEAR_REGRESSION:
            values = self._linear_regression(data, periods)
        elif method == ForecastingMethod.SEASONAL_NAIVE:
            values = self._seasonal_naive(
                data, periods, forecast_config.seasonality_period
            )
        else:
            values = self._moving_average(data, periods)

        # Calculate confidence intervals
        lower, upper = self._calculate_confidence_intervals(values, data)

        # Calculate forecast dates
        forecast_dates = []
        start_date = date.today()
        for i in range(1, periods + 1):
            forecast_dates.append((start_date + timedelta(days=i)).isoformat())

        # Backtest: use last 3 periods as test set if enough data
        mae, rmse, mape = 0.0, 0.0, 0.0
        if len(data) >= 4:
            test_size = min(3, len(data) // 2)
            train = data[:-test_size]
            test = data[-test_size:]
            if method == ForecastingMethod.MOVING_AVERAGE:
                pred = self._moving_average(train, test_size)
            elif method == ForecastingMethod.EXPONENTIAL_SMOOTHING:
                pred = self._exponential_smoothing(train, test_size, forecast_config.alpha)
            elif method == ForecastingMethod.LINEAR_REGRESSION:
                pred = self._linear_regression(train, test_size)
            else:
                pred = self._moving_average(train, test_size)
            mae, rmse, mape = self._calculate_metrics(test, pred)

        result = ForecastResult(
            product_sku=forecast_config.product_sku,
            method=method,
            forecast_values=values,
            confidence_lower=lower,
            confidence_upper=upper,
            mae=mae,
            rmse=rmse,
            mape=mape,
            forecast_dates=forecast_dates,
        )

        # Store result
        if forecast_config.product_sku not in self._results:
            self._results[forecast_config.product_sku] = []
        self._results[forecast_config.product_sku].append(result)

        return result

    def get_results(self, product_sku: str) -> list[ForecastResult]:
        """Get all forecast results for a product."""
        return self._results.get(product_sku, [])

    def compare_methods(
        self,
        product_sku: str,
        historical_data: list[float],
        forecast_periods: int = 1,
    ) -> dict[str, ForecastResult]:
        """Run all forecasting methods and return comparison."""
        results = {}
        for method in ForecastingMethod:
            forecast = self.create_forecast(
                product_sku=product_sku,
                historical_data=historical_data,
                method=method,
                forecast_periods=forecast_periods,
            )
            result = self.generate_forecast(forecast.id)
            results[method.value] = result
        return results

    def get_best_method(
        self,
        product_sku: str,
        historical_data: list[float],
        forecast_periods: int = 1,
    ) -> tuple[str, ForecastResult]:
        """Find the best forecasting method based on MAPE."""
        comparisons = self.compare_methods(
            product_sku, historical_data, forecast_periods
        )
        best_method = min(comparisons, key=lambda m: comparisons[m].mape)
        return best_method, comparisons[best_method]

    def count_forecasts(self) -> int:
        """Return total number of forecast configurations."""
        return len(self._forecasts)

    def clear(self) -> None:
        """Remove all forecasts and results."""
        self._forecasts.clear()
        self._results.clear()
