"""Benchmarking module."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ComparisonType(Enum):
    """Types of benchmark comparisons."""
    INTERNAL = "internal"
    INDUSTRY = "industry"
    COMPETITOR = "competitor"
    HISTORICAL = "historical"
    TARGET = "target"


@dataclass
class BenchmarkResult:
    """Benchmark comparison result."""
    metric_name: str
    entity_value: float
    benchmark_value: float
    comparison_type: ComparisonType
    unit: str = ""
    percentile: float = 0.0
    gap: float = 0.0
    gap_percent: float = 0.0
    status: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "entity_value": self.entity_value,
            "benchmark_value": self.benchmark_value,
            "comparison_type": self.comparison_type.value,
            "unit": self.unit,
            "percentile": self.percentile,
            "gap": self.gap,
            "gap_percent": self.gap_percent,
            "status": self.status,
            "metadata": self.metadata,
        }


class BenchmarkEngine:
    """Benchmarking and comparison engine."""

    def __init__(self):
        self._benchmarks: Dict[str, Dict] = {}
        self._results: List[BenchmarkResult] = []

    def add_benchmark(self, name: str, value: float, category: str = "industry",
                      unit: str = "", metadata: Optional[Dict] = None) -> None:
        """Add a benchmark value."""
        self._benchmarks[name] = {
            "value": value,
            "category": category,
            "unit": unit,
            "metadata": metadata or {},
        }

    def compare(self, metric_name: str, entity_value: float,
                benchmark_value: float, comparison_type: ComparisonType = ComparisonType.INDUSTRY,
                unit: str = "") -> BenchmarkResult:
        """Compare entity value against benchmark."""
        gap = entity_value - benchmark_value
        gap_percent = (gap / benchmark_value * 100) if benchmark_value != 0 else 0

        # Determine status
        if gap_percent >= 10:
            status = "leading"
        elif gap_percent >= -5:
            status = "competitive"
        elif gap_percent >= -20:
            status = "lagging"
        else:
            status = "critical"

        # Calculate percentile (simplified)
        percentile = 50 + gap_percent / 2
        percentile = max(0, min(100, percentile))

        result = BenchmarkResult(
            metric_name=metric_name,
            entity_value=entity_value,
            benchmark_value=benchmark_value,
            comparison_type=comparison_type,
            unit=unit,
            percentile=percentile,
            gap=gap,
            gap_percent=gap_percent,
            status=status,
        )
        self._results.append(result)
        return result

    def compare_to_benchmark(self, metric_name: str, entity_value: float,
                             comparison_type: ComparisonType = ComparisonType.INDUSTRY) -> Optional[BenchmarkResult]:
        """Compare entity value to a stored benchmark."""
        if metric_name not in self._benchmarks:
            return None
        bench = self._benchmarks[metric_name]
        return self.compare(
            metric_name=metric_name,
            entity_value=entity_value,
            benchmark_value=bench["value"],
            comparison_type=comparison_type,
            unit=bench.get("unit", ""),
        )

    def percentile_rank(self, values: List[float], entity_value: float) -> float:
        """Calculate percentile rank of entity value within a distribution."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        count_below = sum(1 for v in sorted_vals if v < entity_value)
        count_equal = sum(1 for v in sorted_vals if v == entity_value)
        return (count_below + 0.5 * count_equal) / len(sorted_vals) * 100

    def compare_to_distribution(self, metric_name: str, entity_value: float,
                                distribution: List[float], unit: str = "") -> BenchmarkResult:
        """Compare entity value to a distribution of values."""
        if not distribution:
            return BenchmarkResult(
                metric_name=metric_name,
                entity_value=entity_value,
                benchmark_value=0,
                comparison_type=ComparisonType.INDUSTRY,
                unit=unit,
            )

        median = statistics.median(distribution)
        percentile = self.percentile_rank(distribution, entity_value)
        gap = entity_value - median
        gap_percent = (gap / median * 100) if median != 0 else 0

        if percentile >= 75:
            status = "leading"
        elif percentile >= 50:
            status = "competitive"
        elif percentile >= 25:
            status = "lagging"
        else:
            status = "critical"

        result = BenchmarkResult(
            metric_name=metric_name,
            entity_value=entity_value,
            benchmark_value=median,
            comparison_type=ComparisonType.INDUSTRY,
            unit=unit,
            percentile=percentile,
            gap=gap,
            gap_percent=gap_percent,
            status=status,
            metadata={"distribution_size": len(distribution)},
        )
        self._results.append(result)
        return result

    def get_results(self) -> List[BenchmarkResult]:
        """Get all benchmark results."""
        return self._results.copy()

    def get_results_by_status(self, status: str) -> List[BenchmarkResult]:
        """Get results filtered by status."""
        return [r for r in self._results if r.status == status]

    def get_summary(self) -> Dict:
        """Get benchmark summary."""
        if not self._results:
            return {
                "total_comparisons": 0,
                "leading": 0,
                "competitive": 0,
                "lagging": 0,
                "critical": 0,
                "average_percentile": 0.0,
            }

        by_status = {"leading": 0, "competitive": 0, "lagging": 0, "critical": 0}
        for r in self._results:
            by_status[r.status] = by_status.get(r.status, 0) + 1

        avg_percentile = sum(r.percentile for r in self._results) / len(self._results)

        return {
            "total_comparisons": len(self._results),
            **by_status,
            "average_percentile": avg_percentile,
        }

    def get_gap_analysis(self) -> List[Dict]:
        """Get gap analysis for all comparisons."""
        return [
            {
                "metric": r.metric_name,
                "gap": r.gap,
                "gap_percent": r.gap_percent,
                "status": r.status,
                "direction": "positive" if r.gap >= 0 else "negative",
            }
            for r in self._results
        ]

    def clear(self) -> None:
        """Clear all benchmarks and results."""
        self._benchmarks.clear()
        self._results.clear()
