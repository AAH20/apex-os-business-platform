"""Log analytics — metrics, trends, and insights from log data."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .structured import LogEntry, LogLevel


class LogMetrics:
    """Computed metrics from log analysis."""

    def __init__(self):
        self.total_entries: int = 0
        self.entries_by_level: Dict[str, int] = {}
        self.entries_by_source: Dict[str, int] = {}
        self.entries_by_hour: Dict[str, int] = {}
        self.error_count: int = 0
        self.error_rate: float = 0.0
        self.warning_rate: float = 0.0
        self.top_messages: List[Tuple[str, int]] = []
        self.top_sources: List[Tuple[str, int]] = []
        self.avg_entries_per_minute: float = 0.0
        self.peak_entries_per_minute: int = 0
        self.time_range: Optional[Tuple[datetime, datetime]] = None
        self.error_trend: List[Dict[str, Any]] = []
        self.latency_stats: Dict[str, float] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entries": self.total_entries,
            "entries_by_level": self.entries_by_level,
            "entries_by_source": self.entries_by_source,
            "entries_by_hour": self.entries_by_hour,
            "error_count": self.error_count,
            "error_rate": self.error_rate,
            "warning_rate": self.warning_rate,
            "top_messages": self.top_messages,
            "top_sources": self.top_sources,
            "avg_entries_per_minute": self.avg_entries_per_minute,
            "peak_entries_per_minute": self.peak_entries_per_minute,
            "time_range": (
                [self.time_range[0].isoformat(), self.time_range[1].isoformat()]
                if self.time_range
                else None
            ),
            "error_trend": self.error_trend,
            "latency_stats": self.latency_stats,
        }


class LogAnalytics:
    """Analytics engine for log data."""

    def __init__(self, entries: Optional[Iterable[LogEntry]] = None):
        self._entries: List[LogEntry] = list(entries) if entries else []

    def add_entries(self, entries: Iterable[LogEntry]) -> None:
        """Add entries for analysis."""
        self._entries.extend(entries)

    def compute_metrics(self) -> LogMetrics:
        """Compute comprehensive metrics from all entries."""
        metrics = LogMetrics()
        if not self._entries:
            return metrics

        metrics.total_entries = len(self._entries)

        timestamps = []
        level_counter: Counter = Counter()
        source_counter: Counter = Counter()
        message_counter: Counter = Counter()
        hour_counter: Counter = Counter()
        minute_counter: Counter = Counter()
        error_count = 0
        warning_count = 0

        for entry in self._entries:
            level_counter[entry.level.name] += 1
            source_counter[entry.source] += 1
            message_counter[entry.message] += 1
            hour_key = entry.timestamp.strftime("%Y-%m-%dT%H")
            hour_counter[hour_key] += 1
            minute_key = entry.timestamp.strftime("%Y-%m-%dT%H:%M")
            minute_counter[minute_key] += 1
            timestamps.append(entry.timestamp)

            if entry.level.value >= LogLevel.ERROR.value:
                error_count += 1
            if entry.level.value >= LogLevel.WARNING.value:
                warning_count += 1

        metrics.entries_by_level = dict(level_counter)
        metrics.entries_by_source = dict(source_counter)
        metrics.entries_by_hour = dict(hour_counter)
        metrics.error_count = error_count
        metrics.error_rate = error_count / metrics.total_entries
        metrics.warning_rate = warning_count / metrics.total_entries
        metrics.top_messages = message_counter.most_common(10)
        metrics.top_sources = source_counter.most_common(10)

        if timestamps:
            metrics.time_range = (min(timestamps), max(timestamps))
            duration_minutes = (
                (max(timestamps) - min(timestamps)).total_seconds() / 60.0
            )
            if duration_minutes > 0:
                metrics.avg_entries_per_minute = metrics.total_entries / duration_minutes
            metrics.peak_entries_per_minute = max(minute_counter.values()) if minute_counter else 0

        return metrics

    def error_trend(
        self, bucket_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """Compute error counts over time buckets."""
        if not self._entries:
            return []

        buckets: Dict[str, Dict[str, Any]] = {}
        for entry in self._entries:
            bucket_ts = entry.timestamp.replace(
                second=0,
                microsecond=0,
                minute=(entry.timestamp.minute // bucket_minutes) * bucket_minutes,
            )
            key = bucket_ts.isoformat()
            if key not in buckets:
                buckets[key] = {"timestamp": key, "total": 0, "errors": 0}
            buckets[key]["total"] += 1
            if entry.level.value >= LogLevel.ERROR.value:
                buckets[key]["errors"] += 1

        result = []
        for key in sorted(buckets.keys()):
            b = buckets[key]
            b["error_rate"] = b["errors"] / b["total"] if b["total"] else 0.0
            result.append(b)
        return result

    def top_errors(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get the most frequent error messages."""
        error_messages = Counter()
        for entry in self._entries:
            if entry.level.value >= LogLevel.ERROR.value:
                error_messages[entry.message] += 1
        return error_messages.most_common(n)

    def latency_analysis(self, context_key: str = "duration_ms") -> Dict[str, float]:
        """Analyze latency from context fields containing timing data."""
        latencies: List[float] = []
        for entry in self._entries:
            val = entry.context.get(context_key)
            if val is not None:
                try:
                    latencies.append(float(val))
                except (ValueError, TypeError):
                    pass

        if not latencies:
            return {}

        latencies.sort()
        return {
            "count": len(latencies),
            "min": latencies[0],
            "max": latencies[-1],
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": _percentile(latencies, 95),
            "p99": _percentile(latencies, 99),
            "stddev": statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
        }

    def source_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Break down entries by source with level distribution."""
        breakdown: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "levels": defaultdict(int), "errors": 0}
        )
        for entry in self._entries:
            src = entry.source or "unknown"
            breakdown[src]["total"] += 1
            breakdown[src]["levels"][entry.level.name] += 1
            if entry.level.value >= LogLevel.ERROR.value:
                breakdown[src]["errors"] += 1

        result = {}
        for src, data in breakdown.items():
            result[src] = {
                "total": data["total"],
                "levels": dict(data["levels"]),
                "errors": data["errors"],
                "error_rate": data["errors"] / data["total"] if data["total"] else 0.0,
            }
        return result

    def hourly_distribution(self) -> Dict[str, int]:
        """Get entry counts grouped by hour."""
        hour_counter: Counter = Counter()
        for entry in self._entries:
            hour_key = entry.timestamp.strftime("%Y-%m-%dT%H:00")
            hour_counter[hour_key] += 1
        return dict(sorted(hour_counter.items()))

    def detect_anomalies(
        self, threshold_std: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect anomalous spikes in log volume per minute."""
        if not self._entries:
            return []

        minute_counter: Counter = Counter()
        for entry in self._entries:
            minute_key = entry.timestamp.strftime("%Y-%m-%dT%H:%M")
            minute_counter[minute_key] += 1

        counts = list(minute_counter.values())
        if len(counts) < 3:
            return []

        mean = statistics.mean(counts)
        stddev = statistics.stdev(counts) if len(counts) > 1 else 0.0

        anomalies = []
        for minute, count in minute_counter.items():
            if stddev > 0 and count > mean + threshold_std * stddev:
                anomalies.append({
                    "minute": minute,
                    "count": count,
                    "expected": mean,
                    "deviation": (count - mean) / stddev,
                })

        anomalies.sort(key=lambda x: x["deviation"], reverse=True)
        return anomalies

    def summary(self) -> Dict[str, Any]:
        """Generate a high-level summary of log data."""
        metrics = self.compute_metrics()
        return {
            "metrics": metrics.to_dict(),
            "top_errors": self.top_errors(5),
            "source_breakdown": self.source_breakdown(),
            "anomalies": self.detect_anomalies(),
        }

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()


def _percentile(sorted_data: List[float], pct: float) -> float:
    """Compute percentile from sorted data."""
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])
