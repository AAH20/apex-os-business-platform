"""Analytics engine."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Metric:
    """Metric data structure."""
    name: str
    value: float
    unit: str
    tags: List[str] = field(default_factory=list)
    timestamp: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class Dashboard:
    """Dashboard data structure."""
    name: str
    metrics: List[Metric] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def add_metric(self, metric: Metric) -> None:
        """Add metric to dashboard."""
        self.metrics.append(metric)

    def summary(self) -> Dict:
        """Generate dashboard summary."""
        return {
            "name": self.name,
            "total_metrics": len(self.metrics),
            "metrics": [{"name": m.name, "value": m.value, "unit": m.unit} for m in self.metrics],
        }


class AnalyticsEngine:
    """Analytics engine with metric tracking and dashboards."""

    def __init__(self):
        self._metrics: Dict[str, List[Metric]] = {}
        self._dashboards: Dict[str, Dashboard] = {}

    def track(self, name: str, value: float, unit: str, **kwargs) -> Metric:
        """Track a metric."""
        metric = Metric(name=name, value=value, unit=unit, **kwargs)
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(metric)
        return metric

    def get_metric(self, name: str) -> Optional[float]:
        """Get latest value for metric."""
        if name in self._metrics and self._metrics[name]:
            return self._metrics[name][-1].value
        return None

    def time_series(self, name: str) -> List[Metric]:
        """Get time series for metric."""
        return self._metrics.get(name, [])

    def create_dashboard(self, name: str, **kwargs) -> Dashboard:
        """Create a new dashboard."""
        dashboard = Dashboard(name=name, **kwargs)
        self._dashboards[name] = dashboard
        return dashboard

    def get_dashboard(self, name: str) -> Optional[Dashboard]:
        """Get dashboard by name."""
        return self._dashboards.get(name)

    def add_metric_to_dashboard(self, dashboard_name: str, metric: Metric) -> None:
        """Add metric to dashboard."""
        dashboard = self._dashboards.get(dashboard_name)
        if not dashboard:
            raise ValueError(f"Dashboard not found: {dashboard_name}")
        dashboard.add_metric(metric)

    def report(self) -> Dict:
        """Generate analytics report."""
        return {
            name: self.get_metric(name)
            for name in self._metrics
        }
