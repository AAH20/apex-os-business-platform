"""Sales forecasting for CRM.

Projects future revenue from historical deal data using moving averages,
linear regression, and weighted trend analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class ForecastResult:
    """Result of a sales forecast."""

    period: str
    predicted_revenue: float
    confidence_low: float
    confidence_high: float
    confidence_level: float  # e.g. 0.90 for 90%
    method: str
    historical_average: float
    trend_direction: str  # "up", "down", "flat"
    trend_slope: float
    factors: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "predicted_revenue": self.predicted_revenue,
            "confidence_low": self.confidence_low,
            "confidence_high": self.confidence_high,
            "confidence_level": self.confidence_level,
            "method": self.method,
            "historical_average": self.historical_average,
            "trend_direction": self.trend_direction,
            "trend_slope": self.trend_slope,
            "factors": self.factors,
        }


class SalesForecaster:
    """Forecasts sales revenue from historical data.

    Each data point is a dict with:
        date: str (ISO format) or datetime
        revenue: float
        deals_closed: int (optional)
        pipeline_value: float (optional)
    """

    def __init__(self, confidence_level: float = 0.90):
        if not 0 < confidence_level < 1:
            raise ValueError("confidence_level must be between 0 and 1")
        self.confidence_level = confidence_level

    @staticmethod
    def _parse_date(d: str | datetime) -> datetime:
        if isinstance(d, datetime):
            return d
        return datetime.fromisoformat(d)

    @staticmethod
    def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
        """Simple linear regression. Returns (slope, intercept)."""
        n = len(xs)
        if n < 2:
            return 0.0, ys[0] if ys else 0.0
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs)
        if den == 0:
            return 0.0, mean_y
        slope = num / den
        intercept = mean_y - slope * mean_x
        return slope, intercept

    def _compute_confidence_interval(
        self, values: list[float], prediction: float
    ) -> tuple[float, float]:
        """Compute confidence interval using standard error."""
        n = len(values)
        if n < 2:
            return prediction * 0.8, prediction * 1.2

        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        std_dev = variance ** 0.5

        # Z-score for confidence level (approximation)
        z_map = {0.80: 1.28, 0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_map.get(self.confidence_level, 1.645)

        margin = z * std_dev / (n ** 0.5)
        return round(max(0, prediction - margin), 2), round(prediction + margin, 2)

    def forecast(
        self,
        historical_data: list[dict],
        periods: int = 3,
        period_days: int = 30,
    ) -> list[ForecastResult]:
        """Forecast revenue for future periods.

        Args:
            historical_data: List of dicts with 'date' and 'revenue' keys.
            periods: Number of future periods to forecast.
            period_days: Days per period (default 30 = monthly).

        Returns:
            List of ForecastResult, one per future period.
        """
        if not historical_data:
            return []

        # Sort by date
        sorted_data = sorted(
            historical_data,
            key=lambda d: self._parse_date(d["date"]),
        )

        revenues = [float(d["revenue"]) for d in sorted_data]
        n = len(revenues)

        if n == 0:
            return []

        # Compute trend via linear regression on index
        xs = list(range(n))
        slope, intercept = self._linear_regression(xs, revenues)

        # Determine trend direction
        if slope > 0.01 * (sum(revenues) / n):
            trend_dir = "up"
        elif slope < -0.01 * (sum(revenues) / n):
            trend_dir = "down"
        else:
            trend_dir = "flat"

        # Moving average (last 3 periods or all if fewer)
        window = min(3, n)
        moving_avg = sum(revenues[-window:]) / window

        # Weighted average (recent periods weighted more)
        weights = list(range(1, n + 1))
        weighted_avg = sum(
            r * w for r, w in zip(revenues, weights)
        ) / sum(weights)

        hist_avg = sum(revenues) / n

        results: list[ForecastResult] = []
        last_date = self._parse_date(sorted_data[-1]["date"])

        for i in range(1, periods + 1):
            # Combine linear regression projection with moving average
            lr_projection = intercept + slope * (n - 1 + i)
            # Blend: 60% regression, 25% moving avg, 15% weighted avg
            prediction = (
                0.60 * lr_projection
                + 0.25 * moving_avg
                + 0.15 * weighted_avg
            )
            prediction = max(0.0, round(prediction, 2))

            low, high = self._compute_confidence_interval(revenues, prediction)

            future_date = last_date + timedelta(days=period_days * i)
            period_label = future_date.strftime("%Y-%m")

            results.append(ForecastResult(
                period=period_label,
                predicted_revenue=prediction,
                confidence_low=low,
                confidence_high=high,
                confidence_level=self.confidence_level,
                method="blended_regression_moving_avg",
                historical_average=round(hist_avg, 2),
                trend_direction=trend_dir,
                trend_slope=round(slope, 4),
                factors={
                    "moving_average": round(moving_avg, 2),
                    "weighted_average": round(weighted_avg, 2),
                    "regression_projection": round(lr_projection, 2),
                    "data_points": n,
                },
            ))

        return results

    def forecast_from_pipeline(
        self,
        pipeline: list[dict],
        periods: int = 3,
    ) -> list[ForecastResult]:
        """Forecast based on pipeline deals.

        Each pipeline dict:
            stage: str (e.g. "prospecting", "qualification", "proposal", "negotiation", "closed_won")
            value: float
            probability: float (0-1)
            expected_close_date: str (ISO format)
        """
        if not pipeline:
            return []

        # Group by stage and compute weighted value
        stage_values: dict[str, list[float]] = {}
        for deal in pipeline:
            stage = deal.get("stage", "unknown")
            value = float(deal.get("value", 0))
            prob = float(deal.get("probability", 0.5))
            weighted = value * prob
            stage_values.setdefault(stage, []).append(weighted)

        # Create synthetic historical data from pipeline stages
        # Use stage progression as proxy for time series
        stage_order = [
            "prospecting", "qualification", "proposal",
            "negotiation", "closed_won",
        ]
        synthetic: list[dict] = []
        base_date = datetime.utcnow() - timedelta(days=90)

        for i, stage in enumerate(stage_order):
            values = stage_values.get(stage, [0.0])
            synthetic.append({
                "date": (base_date + timedelta(days=30 * i)).isoformat(),
                "revenue": sum(values),
            })

        return self.forecast(synthetic, periods=periods)

    def get_summary(self, forecast: list[ForecastResult]) -> dict[str, Any]:
        """Summarize a forecast into key metrics."""
        if not forecast:
            return {
                "total_predicted": 0.0,
                "avg_predicted": 0.0,
                "trend": "flat",
                "confidence_range": (0.0, 0.0),
            }

        total = sum(f.predicted_revenue for f in forecast)
        avg = total / len(forecast)
        low = sum(f.confidence_low for f in forecast)
        high = sum(f.confidence_high for f in forecast)

        return {
            "total_predicted": round(total, 2),
            "avg_predicted": round(avg, 2),
            "trend": forecast[0].trend_direction if forecast else "flat",
            "confidence_range": (round(low, 2), round(high, 2)),
            "periods": len(forecast),
        }
