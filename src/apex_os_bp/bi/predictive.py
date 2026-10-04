"""Predictive analytics module."""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class ForecastResult:
    """Forecast result data structure."""
    method: str
    predictions: List[float]
    confidence_interval_lower: List[float] = field(default_factory=list)
    confidence_interval_upper: List[float] = field(default_factory=list)
    mape: float = 0.0  # Mean Absolute Percentage Error
    rmse: float = 0.0  # Root Mean Square Error
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "method": self.method,
            "predictions": self.predictions,
            "confidence_interval_lower": self.confidence_interval_lower,
            "confidence_interval_upper": self.confidence_interval_upper,
            "mape": self.mape,
            "rmse": self.rmse,
            "metadata": self.metadata,
        }


class PredictiveEngine:
    """Predictive analytics engine with multiple forecasting methods."""

    def __init__(self):
        self._models: Dict[str, Dict] = {}

    def moving_average(self, data: List[float], window: int = 3,
                       periods: int = 3) -> ForecastResult:
        """Simple moving average forecast."""
        if not data or window <= 0:
            return ForecastResult(method="moving_average", predictions=[])

        predictions = []
        lower_bounds = []
        upper_bounds = []

        for i in range(periods):
            if len(data) >= window:
                recent = data[-window:]
                avg = sum(recent) / len(recent)
            else:
                avg = sum(data) / len(data) if data else 0
            predictions.append(avg)

            # Simple confidence interval
            if len(recent) > 1:
                std = statistics.stdev(recent)
            else:
                std = 0
            lower_bounds.append(avg - 1.96 * std)
            upper_bounds.append(avg + 1.96 * std)

            data = data + [avg]  # Use prediction for next iteration

        # Calculate error metrics on historical fit
        mape, rmse = self._calculate_errors(data[:-periods] if periods > 0 else data, predictions)

        return ForecastResult(
            method="moving_average",
            predictions=predictions,
            confidence_interval_lower=lower_bounds,
            confidence_interval_upper=upper_bounds,
            mape=mape,
            rmse=rmse,
            metadata={"window": window, "periods": periods},
        )

    def exponential_smoothing(self, data: List[float], alpha: float = 0.3,
                              periods: int = 3) -> ForecastResult:
        """Exponential smoothing forecast."""
        if not data or alpha <= 0 or alpha > 1:
            return ForecastResult(method="exponential_smoothing", predictions=[])

        # Initialize with first value
        smoothed = data[0]
        for val in data[1:]:
            smoothed = alpha * val + (1 - alpha) * smoothed

        predictions = []
        lower_bounds = []
        upper_bounds = []

        for _ in range(periods):
            predictions.append(smoothed)
            # Confidence interval widens with forecast horizon
            std = statistics.stdev(data) if len(data) > 1 else 0
            margin = 1.96 * std * math.sqrt(len(predictions))
            lower_bounds.append(smoothed - margin)
            upper_bounds.append(smoothed + margin)

        mape, rmse = self._calculate_errors(data, [smoothed] * len(data))

        return ForecastResult(
            method="exponential_smoothing",
            predictions=predictions,
            confidence_interval_lower=lower_bounds,
            confidence_interval_upper=upper_bounds,
            mape=mape,
            rmse=rmse,
            metadata={"alpha": alpha, "periods": periods},
        )

    def linear_regression(self, data: List[float], periods: int = 3) -> ForecastResult:
        """Linear regression forecast."""
        if len(data) < 2:
            return ForecastResult(method="linear_regression", predictions=[])

        n = len(data)
        x_vals = list(range(n))
        x_mean = sum(x_vals) / n
        y_mean = sum(data) / n

        # Calculate slope and intercept
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, data))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        intercept = y_mean - slope * x_mean

        predictions = []
        lower_bounds = []
        upper_bounds = []

        for i in range(periods):
            x = n + i
            pred = slope * x + intercept
            predictions.append(pred)

            # Confidence interval
            residuals = [y - (slope * x + intercept) for x, y in zip(x_vals, data)]
            mse = sum(r ** 2 for r in residuals) / max(n - 2, 1)
            std_error = math.sqrt(mse)
            margin = 1.96 * std_error * math.sqrt(1 + 1/n + (x - x_mean)**2 / denominator if denominator > 0 else 1)
            lower_bounds.append(pred - margin)
            upper_bounds.append(pred + margin)

        # Calculate fit errors
        fitted = [slope * x + intercept for x in x_vals]
        mape, rmse = self._calculate_errors(data, fitted)

        return ForecastResult(
            method="linear_regression",
            predictions=predictions,
            confidence_interval_lower=lower_bounds,
            confidence_interval_upper=upper_bounds,
            mape=mape,
            rmse=rmse,
            metadata={"slope": slope, "intercept": intercept, "periods": periods},
        )

    def holt_winters(self, data: List[float], alpha: float = 0.3,
                     beta: float = 0.1, periods: int = 3) -> ForecastResult:
        """Holt's linear trend method (double exponential smoothing)."""
        if len(data) < 2:
            return ForecastResult(method="holt_winters", predictions=[])

        # Initialize
        level = data[0]
        trend = data[1] - data[0] if len(data) > 1 else 0

        for i in range(1, len(data)):
            prev_level = level
            level = alpha * data[i] + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend

        predictions = []
        lower_bounds = []
        upper_bounds = []

        for i in range(1, periods + 1):
            pred = level + i * trend
            predictions.append(pred)

            std = statistics.stdev(data) if len(data) > 1 else 0
            margin = 1.96 * std * math.sqrt(i)
            lower_bounds.append(pred - margin)
            upper_bounds.append(pred + margin)

        mape, rmse = self._calculate_errors(data, [level] * len(data))

        return ForecastResult(
            method="holt_winters",
            predictions=predictions,
            confidence_interval_lower=lower_bounds,
            confidence_interval_upper=upper_bounds,
            mape=mape,
            rmse=rmse,
            metadata={"alpha": alpha, "beta": beta, "periods": periods},
        )

    def ensemble_forecast(self, data: List[float], periods: int = 3) -> ForecastResult:
        """Ensemble forecast combining multiple methods."""
        if not data:
            return ForecastResult(method="ensemble", predictions=[])

        ma = self.moving_average(data, periods=periods)
        es = self.exponential_smoothing(data, periods=periods)
        lr = self.linear_regression(data, periods=periods)

        predictions = []
        lower_bounds = []
        upper_bounds = []

        for i in range(periods):
            vals = []
            if i < len(ma.predictions):
                vals.append(ma.predictions[i])
            if i < len(es.predictions):
                vals.append(es.predictions[i])
            if i < len(lr.predictions):
                vals.append(lr.predictions[i])

            avg = sum(vals) / len(vals) if vals else 0
            predictions.append(avg)

            if vals:
                std = statistics.stdev(vals) if len(vals) > 1 else 0
                lower_bounds.append(avg - 1.96 * std)
                upper_bounds.append(avg + 1.96 * std)
            else:
                lower_bounds.append(avg)
                upper_bounds.append(avg)

        mape = statistics.mean([ma.mape, es.mape, lr.mape]) if all([ma.mape, es.mape, lr.mape]) else 0
        rmse = statistics.mean([ma.rmse, es.rmse, lr.rmse]) if all([ma.rmse, es.rmse, lr.rmse]) else 0

        return ForecastResult(
            method="ensemble",
            predictions=predictions,
            confidence_interval_lower=lower_bounds,
            confidence_interval_upper=upper_bounds,
            mape=mape,
            rmse=rmse,
            metadata={"periods": periods, "methods": ["moving_average", "exponential_smoothing", "linear_regression"]},
        )

    def detect_trend(self, data: List[float]) -> Dict:
        """Detect trend in data."""
        if len(data) < 2:
            return {"trend": "insufficient_data", "slope": 0, "strength": 0}

        lr = self.linear_regression(data, periods=0)
        slope = lr.metadata.get("slope", 0)

        # Calculate R-squared
        n = len(data)
        x_vals = list(range(n))
        x_mean = sum(x_vals) / n
        y_mean = sum(data) / n
        ss_tot = sum((y - y_mean) ** 2 for y in data)
        ss_res = sum((y - (slope * x + lr.metadata.get("intercept", y_mean))) ** 2 for x, y in zip(x_vals, data))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Determine trend based on slope relative to data range
        data_range = max(data) - min(data) if len(data) > 0 else 0
        threshold = max(0.5, data_range * 0.1) if data_range > 0 else 0.5

        if slope > threshold:
            trend = "increasing"
        elif slope < -threshold:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "slope": slope,
            "r_squared": r_squared,
            "strength": abs(r_squared),
        }

    def detect_seasonality(self, data: List[float], period: int = 7) -> Dict:
        """Detect seasonality in data."""
        if len(data) < period * 2:
            return {"has_seasonality": False, "period": period, "strength": 0}

        # Calculate seasonal indices
        n_periods = len(data) // period
        seasonal_avg = []
        for i in range(period):
            vals = [data[i + j * period] for j in range(n_periods) if i + j * period < len(data)]
            seasonal_avg.append(sum(vals) / len(vals) if vals else 0)

        overall_avg = sum(data) / len(data)
        if overall_avg == 0:
            return {"has_seasonality": False, "period": period, "strength": 0}

        seasonal_indices = [s / overall_avg for s in seasonal_avg]
        variance = statistics.variance(seasonal_indices) if len(seasonal_indices) > 1 else 0

        return {
            "has_seasonality": variance > 0.01,
            "period": period,
            "strength": variance,
            "seasonal_indices": seasonal_indices,
        }

    def _calculate_errors(self, actual: List[float], predicted: List[float]) -> Tuple[float, float]:
        """Calculate MAPE and RMSE."""
        if not actual or not predicted or len(actual) != len(predicted):
            return 0.0, 0.0

        mape_vals = []
        rmse_vals = []
        for a, p in zip(actual, predicted):
            if a != 0:
                mape_vals.append(abs((a - p) / a) * 100)
            rmse_vals.append((a - p) ** 2)

        mape = sum(mape_vals) / len(mape_vals) if mape_vals else 0.0
        rmse = math.sqrt(sum(rmse_vals) / len(rmse_vals)) if rmse_vals else 0.0

        return mape, rmse
