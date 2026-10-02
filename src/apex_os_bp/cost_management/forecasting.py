"""Cost forecasting engine."""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.cost_management.models import (
    CostCategory,
    CostEntry,
    ForecastMethod,
    ForecastResult,
)


class CostForecaster:
    """Forecasts future costs using various methods."""

    def __init__(self):
        self._results: Dict[str, ForecastResult] = {}

    def add_result(self, result: ForecastResult) -> ForecastResult:
        """Add a forecast result."""
        self._results[result.id] = result
        return result

    def get_result(self, result_id: str) -> Optional[ForecastResult]:
        """Get a forecast result by ID."""
        return self._results.get(result_id)

    def get_all_results(self) -> List[ForecastResult]:
        """Get all forecast results."""
        return list(self._results.values())

    def forecast(
        self,
        entries: List[CostEntry],
        periods: int = 12,
        period_days: int = 30,
        method: ForecastMethod = ForecastMethod.MOVING_AVERAGE,
        category: Optional[CostCategory] = None,
        department_id: Optional[str] = None,
        alpha: float = 0.3,
    ) -> ForecastResult:
        """Generate a cost forecast."""
        # Filter entries
        filtered = entries
        if category:
            filtered = [e for e in filtered if e.category == category]
        if department_id:
            filtered = [e for e in filtered if e.department_id == department_id]

        # Group costs by period
        period_costs = self._group_by_period(filtered, period_days)

        if not period_costs:
            # No data, return zero forecast
            return self._create_result(
                method, [0.0] * periods, [0.0] * periods, [0.0] * periods,
                category, department_id,
            )

        if method == ForecastMethod.MOVING_AVERAGE:
            forecast = self._moving_average(period_costs, periods)
        elif method == ForecastMethod.EXPONENTIAL_SMOOTHING:
            forecast = self._exponential_smoothing(period_costs, periods, alpha)
        elif method == ForecastMethod.LINEAR_REGRESSION:
            forecast = self._linear_regression(period_costs, periods)
        elif method == ForecastMethod.SEASONAL:
            forecast = self._seasonal(period_costs, periods)
        else:
            raise ValueError(f"Unknown forecast method: {method}")

        # Compute confidence intervals
        std_dev = self._compute_std_dev(period_costs)
        lower = [max(0.0, f - 1.96 * std_dev) for f in forecast]
        upper = [f + 1.96 * std_dev for f in forecast]

        return self._create_result(
            method, forecast, lower, upper, category, department_id,
        )

    def _group_by_period(
        self,
        entries: List[CostEntry],
        period_days: int,
    ) -> List[float]:
        """Group entry costs into time periods."""
        if not entries:
            return []

        # Sort by date
        sorted_entries = sorted(entries, key=lambda e: e.incurred_date)
        start_date = sorted_entries[0].incurred_date
        end_date = sorted_entries[-1].incurred_date

        num_periods = max(1, int((end_date - start_date).days / period_days) + 1)
        costs = [0.0] * num_periods

        for entry in sorted_entries:
            period_idx = int((entry.incurred_date - start_date).days / period_days)
            period_idx = min(period_idx, num_periods - 1)
            costs[period_idx] += entry.amount

        return costs

    def _moving_average(self, data: List[float], periods: int) -> List[float]:
        """Simple moving average forecast."""
        if not data:
            return [0.0] * periods
        window = min(3, len(data))
        avg = sum(data[-window:]) / window
        return [avg] * periods

    def _exponential_smoothing(
        self,
        data: List[float],
        periods: int,
        alpha: float,
    ) -> List[float]:
        """Exponential smoothing forecast."""
        if not data:
            return [0.0] * periods
        smoothed = data[0]
        for value in data[1:]:
            smoothed = alpha * value + (1 - alpha) * smoothed
        return [smoothed] * periods

    def _linear_regression(self, data: List[float], periods: int) -> List[float]:
        """Linear regression forecast."""
        if not data:
            return [0.0] * periods
        n = len(data)
        if n < 2:
            return [data[0]] * periods

        # Compute regression coefficients
        x_mean = (n - 1) / 2.0
        y_mean = sum(data) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(data))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return [y_mean] * periods

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # Forecast future values
        forecast = []
        for i in range(periods):
            x = n + i
            value = intercept + slope * x
            forecast.append(max(0.0, value))

        return forecast

    def _seasonal(self, data: List[float], periods: int) -> List[float]:
        """Seasonal forecast using simple seasonal decomposition."""
        if not data:
            return [0.0] * periods
        # Use a simple seasonal pattern (e.g., 12 periods for monthly seasonality)
        season_length = min(12, len(data))
        if season_length < 2:
            return [sum(data) / len(data)] * periods

        # Compute seasonal indices
        seasonal_avg = []
        for i in range(season_length):
            values = [data[j] for j in range(i, len(data), season_length)]
            seasonal_avg.append(sum(values) / len(values) if values else 0.0)

        overall_avg = sum(data) / len(data)
        if overall_avg == 0:
            return [0.0] * periods

        seasonal_indices = [avg / overall_avg for avg in seasonal_avg]

        # Forecast using seasonal pattern
        forecast = []
        for i in range(periods):
            season_idx = (len(data) + i) % season_length
            forecast.append(overall_avg * seasonal_indices[season_idx])

        return forecast

    def _compute_std_dev(self, data: List[float]) -> float:
        """Compute standard deviation of data."""
        if len(data) < 2:
            return 0.0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / (len(data) - 1)
        return math.sqrt(variance)

    def _create_result(
        self,
        method: ForecastMethod,
        forecast: List[float],
        lower: List[float],
        upper: List[float],
        category: Optional[CostCategory],
        department_id: Optional[str],
    ) -> ForecastResult:
        """Create and store a forecast result."""
        result = ForecastResult.create(
            method=method,
            forecast_periods=forecast,
            confidence_interval_lower=lower,
            confidence_interval_upper=upper,
            category=category,
            department_id=department_id,
        )
        self._results[result.id] = result
        return result

    def forecast_by_category(
        self,
        entries: List[CostEntry],
        periods: int = 12,
        method: ForecastMethod = ForecastMethod.MOVING_AVERAGE,
    ) -> Dict[CostCategory, ForecastResult]:
        """Generate forecasts for each category."""
        categories = set(e.category for e in entries)
        results = {}
        for category in categories:
            results[category] = self.forecast(
                entries, periods=periods, method=method, category=category
            )
        return results

    def forecast_by_department(
        self,
        entries: List[CostEntry],
        periods: int = 12,
        method: ForecastMethod = ForecastMethod.MOVING_AVERAGE,
    ) -> Dict[str, ForecastResult]:
        """Generate forecasts for each department."""
        departments = set(
            e.department_id for e in entries if e.department_id is not None
        )
        results = {}
        for dept_id in departments:
            results[dept_id] = self.forecast(
                entries, periods=periods, method=method, department_id=dept_id
            )
        return results

    def get_total_forecast(self) -> float:
        """Get total forecasted cost across all results."""
        return sum(r.total_forecast for r in self._results.values())

    def clear(self) -> None:
        """Clear all forecast results."""
        self._results.clear()
