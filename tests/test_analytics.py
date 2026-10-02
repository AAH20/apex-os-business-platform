"""Tests for analytics module."""
import pytest
from apex_os_bp.analytics.engine import AnalyticsEngine, Metric, Dashboard


class TestMetric:
    """Test metric data structure."""

    def test_metric_creation(self):
        """Metric can be created."""
        metric = Metric(name="revenue", value=1000.0, unit="USD")
        assert metric.name == "revenue"
        assert metric.value == 1000.0
        assert metric.unit == "USD"

    def test_metric_with_tags(self):
        """Metric supports tags."""
        metric = Metric(name="revenue", value=1000.0, unit="USD", tags=["monthly", "sales"])
        assert "monthly" in metric.tags


class TestDashboard:
    """Test dashboard functionality."""

    def test_dashboard_creation(self):
        """Dashboard can be created."""
        dashboard = Dashboard(name="Sales Dashboard")
        assert dashboard.name == "Sales Dashboard"
        assert len(dashboard.metrics) == 0

    def test_add_metric(self):
        """Metric can be added to dashboard."""
        dashboard = Dashboard(name="Sales Dashboard")
        metric = Metric(name="revenue", value=1000.0, unit="USD")
        dashboard.add_metric(metric)
        assert len(dashboard.metrics) == 1

    def test_dashboard_summary(self):
        """Dashboard generates summary."""
        dashboard = Dashboard(name="Sales Dashboard")
        dashboard.add_metric(Metric(name="revenue", value=1000.0, unit="USD"))
        dashboard.add_metric(Metric(name="deals", value=10.0, unit="count"))
        summary = dashboard.summary()
        assert summary["total_metrics"] == 2


class TestAnalyticsEngine:
    """Test analytics engine."""

    def test_track_metric(self):
        """Metric can be tracked."""
        engine = AnalyticsEngine()
        engine.track("revenue", 1000.0, "USD")
        assert engine.get_metric("revenue") == 1000.0

    def test_track_multiple_metrics(self):
        """Multiple metrics can be tracked."""
        engine = AnalyticsEngine()
        engine.track("revenue", 1000.0, "USD")
        engine.track("deals", 10.0, "count")
        assert engine.get_metric("revenue") == 1000.0
        assert engine.get_metric("deals") == 10.0

    def test_create_dashboard(self):
        """Dashboard can be created."""
        engine = AnalyticsEngine()
        dashboard = engine.create_dashboard("Sales Dashboard")
        assert dashboard.name == "Sales Dashboard"

    def test_add_metric_to_dashboard(self):
        """Metric can be added to dashboard."""
        engine = AnalyticsEngine()
        dashboard = engine.create_dashboard("Sales Dashboard")
        engine.add_metric_to_dashboard(dashboard.name, Metric(name="revenue", value=1000.0, unit="USD"))
        assert len(dashboard.metrics) == 1

    def test_report(self):
        """Report can be generated."""
        engine = AnalyticsEngine()
        engine.track("revenue", 1000.0, "USD")
        engine.track("deals", 10.0, "count")
        report = engine.report()
        assert "revenue" in report
        assert "deals" in report

    def test_time_series(self):
        """Time series data can be tracked."""
        engine = AnalyticsEngine()
        engine.track("revenue", 1000.0, "USD", timestamp="2026-01-01")
        engine.track("revenue", 2000.0, "USD", timestamp="2026-01-02")
        series = engine.time_series("revenue")
        assert len(series) == 2
