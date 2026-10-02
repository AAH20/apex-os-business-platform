"""Real-time analytics module for the IoT platform.

Provides aggregation, statistical analysis, anomaly detection,
and trend analysis over sensor readings.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from .data_ingestion import DataIngestion, SensorReading


class AggregationType(str, Enum):
    """Types of aggregation operations."""

    MIN = "min"
    MAX = "max"
    AVG = "avg"
    SUM = "sum"
    COUNT = "count"
    MEDIAN = "median"
    STDDEV = "stddev"
    VARIANCE = "variance"
    P95 = "p95"
    P99 = "p99"
    RANGE = "range"


class TimeWindow(str, Enum):
    """Predefined time windows for analytics."""

    LAST_MINUTE = "1m"
    LAST_5_MINUTES = "5m"
    LAST_15_MINUTES = "15m"
    LAST_30_MINUTES = "30m"
    LAST_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_12_HOURS = "12h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    ALL = "all"


@dataclass
class AnalyticsResult:
    """Result of an analytics computation.

    Attributes:
        device_id: Device that was analyzed.
        sensor_type: Sensor type analyzed.
        aggregation: Type of aggregation performed.
        value: Computed aggregate value.
        count: Number of readings used.
        window: Time window used.
        start_time: Start of analysis window.
        end_time: End of analysis window.
        additional_stats: Extra computed statistics.
    """

    device_id: str
    sensor_type: str
    aggregation: AggregationType
    value: float
    count: int
    window: TimeWindow
    start_time: datetime | None = None
    end_time: datetime | None = None
    additional_stats: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to a dictionary."""
        return {
            "device_id": self.device_id,
            "sensor_type": self.sensor_type,
            "aggregation": self.aggregation.value,
            "value": self.value,
            "count": self.count,
            "window": self.window.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "additional_stats": dict(self.additional_stats),
        }


@dataclass
class AnomalyEvent:
    """Represents a detected anomaly.

    Attributes:
        device_id: Device that produced the anomalous reading.
        sensor_type: Sensor type.
        reading: The anomalous SensorReading.
        expected_range: Tuple of (low, high) expected values.
        severity: Severity score (0.0 to 1.0).
        detected_at: When the anomaly was detected.
        description: Human-readable description.
    """

    device_id: str
    sensor_type: str
    reading: SensorReading
    expected_range: tuple[float, float]
    severity: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize anomaly to a dictionary."""
        return {
            "device_id": self.device_id,
            "sensor_type": self.sensor_type,
            "reading": self.reading.to_dict(),
            "expected_range": list(self.expected_range),
            "severity": self.severity,
            "detected_at": self.detected_at.isoformat(),
            "description": self.description,
        }


class AnalyticsEngine:
    """Computes real-time analytics over IoT sensor data.

    Works with a DataIngestion instance to provide aggregation,
    anomaly detection, and trend analysis.
    """

    _WINDOW_DELTAS: dict[TimeWindow, timedelta | None] = {
        TimeWindow.LAST_MINUTE: timedelta(minutes=1),
        TimeWindow.LAST_5_MINUTES: timedelta(minutes=5),
        TimeWindow.LAST_15_MINUTES: timedelta(minutes=15),
        TimeWindow.LAST_30_MINUTES: timedelta(minutes=30),
        TimeWindow.LAST_HOUR: timedelta(hours=1),
        TimeWindow.LAST_6_HOURS: timedelta(hours=6),
        TimeWindow.LAST_12_HOURS: timedelta(hours=12),
        TimeWindow.LAST_24_HOURS: timedelta(hours=24),
        TimeWindow.LAST_7_DAYS: timedelta(days=7),
        TimeWindow.LAST_30_DAYS: timedelta(days=30),
        TimeWindow.ALL: None,
    }

    def __init__(self, ingestion: DataIngestion) -> None:
        """Initialize the analytics engine.

        Args:
            ingestion: DataIngestion instance to pull readings from.
        """
        self._ingestion = ingestion

    def aggregate(
        self,
        device_id: str,
        sensor_type: str,
        aggregation: AggregationType | str,
        window: TimeWindow | str = TimeWindow.ALL,
    ) -> AnalyticsResult:
        """Compute an aggregate statistic over readings.

        Args:
            device_id: Device to analyze.
            sensor_type: Sensor type to analyze.
            aggregation: Type of aggregation.
            window: Time window to consider.

        Returns:
            AnalyticsResult with the computed value.

        Raises:
            ValueError: If no readings match the criteria.
        """
        if isinstance(aggregation, str):
            aggregation = AggregationType(aggregation)
        if isinstance(window, str):
            window = TimeWindow(window)

        readings = self._get_window_readings(device_id, sensor_type, window)
        if not readings:
            raise ValueError(
                f"No readings found for device '{device_id}' "
                f"sensor '{sensor_type}' in window '{window.value}'"
            )

        values = [r.value for r in readings]
        computed = self._compute_aggregation(values, aggregation)

        # Compute additional stats
        additional = self._compute_additional_stats(values)

        start_time = min(r.timestamp for r in readings)
        end_time = max(r.timestamp for r in readings)

        return AnalyticsResult(
            device_id=device_id,
            sensor_type=sensor_type,
            aggregation=aggregation,
            value=computed,
            count=len(values),
            window=window,
            start_time=start_time,
            end_time=end_time,
            additional_stats=additional,
        )

    def detect_anomalies(
        self,
        device_id: str,
        sensor_type: str,
        window: TimeWindow | str = TimeWindow.LAST_24_HOURS,
        threshold_std: float = 2.0,
    ) -> list[AnomalyEvent]:
        """Detect anomalous readings using standard deviation.

        Args:
            device_id: Device to analyze.
            sensor_type: Sensor type to analyze.
            window: Time window for baseline.
            threshold_std: Number of standard deviations for anomaly threshold.

        Returns:
            List of detected AnomalyEvent objects.
        """
        if isinstance(window, str):
            window = TimeWindow(window)

        readings = self._get_window_readings(device_id, sensor_type, window)
        if len(readings) < 3:
            return []

        values = [r.value for r in readings]
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0

        if std == 0.0:
            return []

        low = mean - threshold_std * std
        high = mean + threshold_std * std

        anomalies: list[AnomalyEvent] = []
        for reading in readings:
            if reading.value < low or reading.value > high:
                deviation = abs(reading.value - mean) / std
                severity = min(1.0, deviation / (threshold_std * 2))
                anomalies.append(AnomalyEvent(
                    device_id=device_id,
                    sensor_type=sensor_type,
                    reading=reading,
                    expected_range=(low, high),
                    severity=severity,
                    description=(
                        f"Value {reading.value} outside expected range "
                        f"[{low:.2f}, {high:.2f}] ({deviation:.1f} std dev)"
                    ),
                ))

        return anomalies

    def compute_trend(
        self,
        device_id: str,
        sensor_type: str,
        window: TimeWindow | str = TimeWindow.LAST_24_HOURS,
    ) -> dict[str, Any]:
        """Compute trend direction and rate of change.

        Args:
            device_id: Device to analyze.
            sensor_type: Sensor type to analyze.
            window: Time window.

        Returns:
            Dictionary with trend info: direction, slope, change_percent.
        """
        if isinstance(window, str):
            window = TimeWindow(window)

        readings = self._get_window_readings(device_id, sensor_type, window)
        if len(readings) < 2:
            return {
                "direction": "insufficient_data",
                "slope": 0.0,
                "change_percent": 0.0,
                "data_points": len(readings),
            }

        # Sort by time ascending
        sorted_readings = sorted(readings, key=lambda r: r.timestamp)
        first_val = sorted_readings[0].value
        last_val = sorted_readings[-1].value

        # Simple linear regression for slope
        n = len(sorted_readings)
        times = [
            (r.timestamp - sorted_readings[0].timestamp).total_seconds()
            for r in sorted_readings
        ]
        values = [r.value for r in sorted_readings]

        sum_x = sum(times)
        sum_y = sum(values)
        sum_xy = sum(t * v for t, v in zip(times, values))
        sum_x2 = sum(t * t for t in times)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            slope = 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator

        if first_val != 0:
            change_pct = ((last_val - first_val) / abs(first_val)) * 100
        else:
            change_pct = 0.0 if last_val == 0 else float("inf")

        if abs(slope) < 1e-10:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        return {
            "direction": direction,
            "slope": slope,
            "change_percent": change_pct,
            "data_points": n,
            "first_value": first_val,
            "last_value": last_val,
        }

    def get_summary(
        self,
        device_id: str,
        sensor_type: str,
        window: TimeWindow | str = TimeWindow.ALL,
    ) -> dict[str, float]:
        """Get a summary of all statistics for a device/sensor.

        Args:
            device_id: Device to analyze.
            sensor_type: Sensor type.
            window: Time window.

        Returns:
            Dictionary with min, max, avg, count, stddev, etc.
        """
        if isinstance(window, str):
            window = TimeWindow(window)

        readings = self._get_window_readings(device_id, sensor_type, window)
        if not readings:
            return {"count": 0.0}

        values = [r.value for r in readings]
        return self._compute_additional_stats(values)

    def compare_devices(
        self,
        device_ids: list[str],
        sensor_type: str,
        aggregation: AggregationType | str = AggregationType.AVG,
        window: TimeWindow | str = TimeWindow.LAST_24_HOURS,
    ) -> dict[str, AnalyticsResult]:
        """Compare the same metric across multiple devices.

        Args:
            device_ids: List of device IDs to compare.
            sensor_type: Sensor type to compare.
            aggregation: Aggregation to compute.
            window: Time window.

        Returns:
            Dictionary mapping device_id to AnalyticsResult.
        """
        results: dict[str, AnalyticsResult] = {}
        for dev_id in device_ids:
            try:
                results[dev_id] = self.aggregate(dev_id, sensor_type, aggregation, window)
            except ValueError:
                # No data for this device
                continue
        return results

    def _get_window_readings(
        self,
        device_id: str,
        sensor_type: str,
        window: TimeWindow,
    ) -> list[SensorReading]:
        """Get readings filtered by time window."""
        delta = self._WINDOW_DELTAS.get(window)
        if delta is None:
            return self._ingestion.get_readings(device_id=device_id, sensor_type=sensor_type)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - delta
        return self._ingestion.get_readings(
            device_id=device_id,
            sensor_type=sensor_type,
            start_time=start_time,
            end_time=end_time,
        )

    def _compute_aggregation(self, values: list[float], agg: AggregationType) -> float:
        """Compute a single aggregation over a list of values."""
        if not values:
            raise ValueError("Cannot aggregate empty list")

        if agg == AggregationType.MIN:
            return min(values)
        if agg == AggregationType.MAX:
            return max(values)
        if agg == AggregationType.AVG:
            return statistics.mean(values)
        if agg == AggregationType.SUM:
            return sum(values)
        if agg == AggregationType.COUNT:
            return float(len(values))
        if agg == AggregationType.MEDIAN:
            return statistics.median(values)
        if agg == AggregationType.STDDEV:
            return statistics.stdev(values) if len(values) > 1 else 0.0
        if agg == AggregationType.VARIANCE:
            return statistics.variance(values) if len(values) > 1 else 0.0
        if agg == AggregationType.P95:
            return self._percentile(values, 95)
        if agg == AggregationType.P99:
            return self._percentile(values, 99)
        if agg == AggregationType.RANGE:
            return max(values) - min(values)
        raise ValueError(f"Unknown aggregation type: {agg}")

    def _compute_additional_stats(self, values: list[float]) -> dict[str, float]:
        """Compute a full set of statistics."""
        if not values:
            return {"count": 0.0}

        stats: dict[str, float] = {
            "count": float(len(values)),
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "sum": sum(values),
        }
        if len(values) > 1:
            stats["stddev"] = statistics.stdev(values)
            stats["variance"] = statistics.variance(values)
        else:
            stats["stddev"] = 0.0
            stats["variance"] = 0.0
        stats["median"] = statistics.median(values)
        stats["range"] = max(values) - min(values)
        stats["p95"] = self._percentile(values, 95)
        stats["p99"] = self._percentile(values, 99)
        return stats

    @staticmethod
    def _percentile(values: list[float], p: float) -> float:
        """Compute the p-th percentile using linear interpolation."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        k = (p / 100) * (n - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        d0 = sorted_vals[f] * (c - k)
        d1 = sorted_vals[c] * (k - f)
        return d0 + d1
