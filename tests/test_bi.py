"""Tests for business intelligence module."""
import math
import pytest
from apex_os_bp.bi.kpi import KPITracker, KPI, KPIStatus
from apex_os_bp.bi.visualization import DataVisualizer, ChartType, ChartConfig, DataPoint, ChartSeries
from apex_os_bp.bi.predictive import PredictiveEngine, ForecastResult
from apex_os_bp.bi.benchmarking import BenchmarkEngine, BenchmarkResult, ComparisonType
from apex_os_bp.bi.executive import ExecutiveDashboard, ExecutiveSummary


class TestKPI:
    """Test KPI data structure."""

    def test_kpi_creation(self):
        """KPI can be created with basic fields."""
        kpi = KPI(name="revenue", value=1000.0, target=1200.0, unit="USD")
        assert kpi.name == "revenue"
        assert kpi.value == 1000.0
        assert kpi.target == 1200.0
        assert kpi.unit == "USD"
        assert kpi.id is not None

    def test_kpi_achievement_rate(self):
        """KPI achievement rate is calculated correctly."""
        kpi = KPI(name="revenue", value=900.0, target=1000.0, unit="USD")
        assert kpi.achievement_rate == 90.0

    def test_kpi_variance(self):
        """KPI variance is calculated correctly."""
        kpi = KPI(name="revenue", value=900.0, target=1000.0, unit="USD")
        assert kpi.variance == -100.0
        assert kpi.variance_percent == -10.0

    def test_kpi_status_critical(self):
        """KPI status is critical when achievement < 50%."""
        kpi = KPI(name="revenue", value=400.0, target=1000.0, unit="USD")
        assert kpi.status == KPIStatus.CRITICAL

    def test_kpi_status_warning(self):
        """KPI status is warning when achievement < 80%."""
        kpi = KPI(name="revenue", value=700.0, target=1000.0, unit="USD")
        assert kpi.status == KPIStatus.WARNING

    def test_kpi_status_on_track(self):
        """KPI status is on_track when achievement < 110%."""
        kpi = KPI(name="revenue", value=900.0, target=1000.0, unit="USD")
        assert kpi.status == KPIStatus.ON_TRACK

    def test_kpi_status_exceeding(self):
        """KPI status is exceeding when achievement >= 110%."""
        kpi = KPI(name="revenue", value=1200.0, target=1000.0, unit="USD")
        assert kpi.status == KPIStatus.EXCEEDING

    def test_kpi_to_dict(self):
        """KPI can be converted to dictionary."""
        kpi = KPI(name="revenue", value=1000.0, target=1200.0, unit="USD", category="sales")
        d = kpi.to_dict()
        assert d["name"] == "revenue"
        assert d["value"] == 1000.0
        assert d["target"] == 1200.0
        assert d["category"] == "sales"
        assert "achievement_rate" in d
        assert "status" in d

    def test_kpi_zero_target(self):
        """KPI handles zero target gracefully."""
        kpi = KPI(name="revenue", value=100.0, target=0.0, unit="USD")
        assert kpi.achievement_rate == 0.0
        assert kpi.variance_percent == 0.0


class TestKPITracker:
    """Test KPI tracker functionality."""

    def test_track_kpi(self):
        """KPI can be tracked."""
        tracker = KPITracker()
        kpi = tracker.track("revenue", 1000.0, 1200.0, "USD")
        assert kpi.name == "revenue"
        assert kpi.value == 1000.0

    def test_get_kpi_by_id(self):
        """KPI can be retrieved by ID."""
        tracker = KPITracker()
        kpi = tracker.track("revenue", 1000.0, 1200.0, "USD")
        retrieved = tracker.get(kpi.id)
        assert retrieved is not None
        assert retrieved.id == kpi.id

    def test_get_kpi_by_name(self):
        """KPIs can be retrieved by name."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD")
        tracker.track("revenue", 1100.0, 1200.0, "USD")
        results = tracker.get_by_name("revenue")
        assert len(results) == 2

    def test_get_latest(self):
        """Latest KPI can be retrieved."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD")
        tracker.track("revenue", 1100.0, 1200.0, "USD")
        latest = tracker.get_latest("revenue")
        assert latest is not None
        assert latest.value == 1100.0

    def test_get_all(self):
        """All KPIs can be retrieved."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD")
        tracker.track("deals", 50.0, 60.0, "count")
        all_kpis = tracker.get_all()
        assert len(all_kpis) == 2

    def test_get_by_category(self):
        """KPIs can be filtered by category."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD", category="sales")
        tracker.track("deals", 50.0, 60.0, "count", category="sales")
        tracker.track("satisfaction", 4.5, 4.0, "rating", category="customer")
        sales_kpis = tracker.get_by_category("sales")
        assert len(sales_kpis) == 2

    def test_get_by_status(self):
        """KPIs can be filtered by status."""
        tracker = KPITracker()
        tracker.track("revenue", 1200.0, 1000.0, "USD")  # exceeding
        tracker.track("deals", 400.0, 1000.0, "count")  # critical
        exceeding = tracker.get_by_status(KPIStatus.EXCEEDING)
        critical = tracker.get_by_status(KPIStatus.CRITICAL)
        assert len(exceeding) == 1
        assert len(critical) == 1

    def test_get_categories(self):
        """All categories can be retrieved."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD", category="sales")
        tracker.track("satisfaction", 4.5, 4.0, "rating", category="customer")
        categories = tracker.get_categories()
        assert "sales" in categories
        assert "customer" in categories

    def test_get_trend(self):
        """Trend data can be retrieved."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD")
        tracker.track("revenue", 1100.0, 1200.0, "USD")
        tracker.track("revenue", 1050.0, 1200.0, "USD")
        trend = tracker.get_trend("revenue")
        assert len(trend) == 3
        assert trend[0]["value"] == 1000.0
        assert trend[-1]["value"] == 1050.0

    def test_get_summary(self):
        """Summary can be generated."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD", category="sales")
        tracker.track("deals", 50.0, 60.0, "count", category="sales")
        summary = tracker.get_summary()
        assert summary["total"] == 2
        assert "by_status" in summary
        assert "by_category" in summary
        assert "overall_achievement" in summary

    def test_get_scorecard(self):
        """Balanced scorecard can be generated."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD", category="financial")
        tracker.track("satisfaction", 4.5, 4.0, "rating", category="customer")
        scorecard = tracker.get_scorecard()
        assert "financial" in scorecard
        assert "customer" in scorecard
        assert scorecard["financial"]["kpi_count"] == 1

    def test_clear(self):
        """All KPIs can be cleared."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD")
        tracker.clear()
        assert len(tracker.get_all()) == 0


class TestDataVisualizer:
    """Test data visualization functionality."""

    def test_create_line_chart(self):
        """Line chart can be created."""
        viz = DataVisualizer()
        series = [ChartSeries(name="Revenue", data=[DataPoint("Jan", 100), DataPoint("Feb", 120)])]
        chart = viz.create_line_chart(series, ChartConfig(title="Revenue Trend"))
        assert chart["type"] == "line"
        assert chart["config"]["title"] == "Revenue Trend"
        assert len(chart["series"]) == 1

    def test_create_bar_chart(self):
        """Bar chart can be created."""
        viz = DataVisualizer()
        series = [ChartSeries(name="Sales", data=[DataPoint("Q1", 500), DataPoint("Q2", 600)])]
        chart = viz.create_bar_chart(series, ChartConfig(title="Quarterly Sales"))
        assert chart["type"] == "bar"
        assert chart["config"]["title"] == "Quarterly Sales"

    def test_create_pie_chart(self):
        """Pie chart can be created."""
        viz = DataVisualizer()
        data = [DataPoint("A", 30), DataPoint("B", 50), DataPoint("C", 20)]
        chart = viz.create_pie_chart(data, ChartConfig(title="Market Share"))
        assert chart["type"] == "pie"
        assert len(chart["data"]) == 3
        assert chart["data"][0]["percentage"] == 30.0

    def test_create_gauge_chart(self):
        """Gauge chart can be created."""
        viz = DataVisualizer()
        chart = viz.create_gauge_chart(75.0, 0.0, 100.0, title="Performance", unit="%")
        assert chart["type"] == "gauge"
        assert chart["value"] == 75.0
        assert chart["percentage"] == 75.0

    def test_create_heatmap(self):
        """Heatmap can be created."""
        viz = DataVisualizer()
        data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        chart = viz.create_heatmap(data, ["A", "B", "C"], ["X", "Y", "Z"], title="Correlation")
        assert chart["type"] == "heatmap"
        assert len(chart["data"]) == 3

    def test_create_table(self):
        """Table can be created."""
        viz = DataVisualizer()
        chart = viz.create_table(["Name", "Value"], [["A", 1], ["B", 2]], title="Data")
        assert chart["type"] == "table"
        assert chart["headers"] == ["Name", "Value"]
        assert len(chart["rows"]) == 2

    def test_create_scatter_plot(self):
        """Scatter plot can be created."""
        viz = DataVisualizer()
        series = [ChartSeries(name="Data", data=[DataPoint("1", 10), DataPoint("2", 20)])]
        chart = viz.create_scatter_plot(series, ChartConfig(title="Scatter"))
        assert chart["type"] == "scatter"

    def test_create_area_chart(self):
        """Area chart can be created."""
        viz = DataVisualizer()
        series = [ChartSeries(name="Trend", data=[DataPoint("Jan", 100), DataPoint("Feb", 150)])]
        chart = viz.create_area_chart(series, ChartConfig(title="Area"))
        assert chart["type"] == "area"

    def test_get_chart(self):
        """Chart can be retrieved by ID."""
        viz = DataVisualizer()
        series = [ChartSeries(name="Test", data=[DataPoint("A", 1)])]
        chart = viz.create_line_chart(series)
        # Get the first chart key
        chart_id = list(viz.get_all_charts().keys())[0]
        retrieved = viz.get_chart(chart_id)
        assert retrieved is not None

    def test_clear_charts(self):
        """All charts can be cleared."""
        viz = DataVisualizer()
        series = [ChartSeries(name="Test", data=[DataPoint("A", 1)])]
        viz.create_line_chart(series)
        viz.clear()
        assert len(viz.get_all_charts()) == 0

    def test_generate_ascii_bar(self):
        """ASCII bar chart can be generated."""
        data = [DataPoint("A", 50), DataPoint("B", 100), DataPoint("C", 75)]
        result = DataVisualizer.generate_ascii_bar(data, width=20)
        assert "A" in result
        assert "B" in result
        assert "█" in result

    def test_generate_ascii_line(self):
        """ASCII line chart can be generated."""
        data = [DataPoint("1", 10), DataPoint("2", 20), DataPoint("3", 15)]
        result = DataVisualizer.generate_ascii_line(data, height=5, width=10)
        assert "*" in result


class TestPredictiveEngine:
    """Test predictive analytics functionality."""

    def test_moving_average(self):
        """Moving average forecast works."""
        engine = PredictiveEngine()
        data = [100, 110, 120, 130, 140]
        result = engine.moving_average(data, window=3, periods=2)
        assert result.method == "moving_average"
        assert len(result.predictions) == 2
        assert all(p > 0 for p in result.predictions)

    def test_moving_average_empty(self):
        """Moving average handles empty data."""
        engine = PredictiveEngine()
        result = engine.moving_average([], periods=2)
        assert result.predictions == []

    def test_exponential_smoothing(self):
        """Exponential smoothing forecast works."""
        engine = PredictiveEngine()
        data = [100, 110, 120, 130, 140]
        result = engine.exponential_smoothing(data, alpha=0.3, periods=2)
        assert result.method == "exponential_smoothing"
        assert len(result.predictions) == 2

    def test_exponential_smoothing_empty(self):
        """Exponential smoothing handles empty data."""
        engine = PredictiveEngine()
        result = engine.exponential_smoothing([], periods=2)
        assert result.predictions == []

    def test_linear_regression(self):
        """Linear regression forecast works."""
        engine = PredictiveEngine()
        data = [100, 110, 120, 130, 140]
        result = engine.linear_regression(data, periods=2)
        assert result.method == "linear_regression"
        assert len(result.predictions) == 2
        assert "slope" in result.metadata
        assert "intercept" in result.metadata

    def test_linear_regression_insufficient_data(self):
        """Linear regression handles insufficient data."""
        engine = PredictiveEngine()
        result = engine.linear_regression([100], periods=2)
        assert result.predictions == []

    def test_holt_winters(self):
        """Holt-Winters forecast works."""
        engine = PredictiveEngine()
        data = [100, 110, 120, 130, 140, 150, 160]
        result = engine.holt_winters(data, alpha=0.3, beta=0.1, periods=2)
        assert result.method == "holt_winters"
        assert len(result.predictions) == 2

    def test_ensemble_forecast(self):
        """Ensemble forecast combines methods."""
        engine = PredictiveEngine()
        data = [100, 110, 120, 130, 140]
        result = engine.ensemble_forecast(data, periods=3)
        assert result.method == "ensemble"
        assert len(result.predictions) == 3
        assert "methods" in result.metadata

    def test_detect_trend_increasing(self):
        """Increasing trend is detected."""
        engine = PredictiveEngine()
        data = [100, 110, 120, 130, 140, 150]
        result = engine.detect_trend(data)
        assert result["trend"] == "increasing"
        assert result["slope"] > 0

    def test_detect_trend_decreasing(self):
        """Decreasing trend is detected."""
        engine = PredictiveEngine()
        data = [150, 140, 130, 120, 110, 100]
        result = engine.detect_trend(data)
        assert result["trend"] == "decreasing"
        assert result["slope"] < 0

    def test_detect_trend_stable(self):
        """Stable trend is detected."""
        engine = PredictiveEngine()
        data = [100, 101, 99, 100, 100, 101]
        result = engine.detect_trend(data)
        assert result["trend"] == "stable"

    def test_detect_trend_insufficient(self):
        """Insufficient data is handled."""
        engine = PredictiveEngine()
        result = engine.detect_trend([100])
        assert result["trend"] == "insufficient_data"

    def test_detect_seasonality(self):
        """Seasonality detection works."""
        engine = PredictiveEngine()
        data = [100, 120, 140, 100, 120, 140, 100, 120, 140, 100, 120, 140]
        result = engine.detect_seasonality(data, period=3)
        assert "has_seasonality" in result
        assert "seasonal_indices" in result

    def test_detect_seasonality_insufficient(self):
        """Seasonality handles insufficient data."""
        engine = PredictiveEngine()
        result = engine.detect_seasonality([100, 110], period=7)
        assert result["has_seasonality"] is False

    def test_forecast_confidence_intervals(self):
        """Forecast includes confidence intervals."""
        engine = PredictiveEngine()
        data = [100, 110, 120, 130, 140]
        result = engine.linear_regression(data, periods=3)
        assert len(result.confidence_interval_lower) == 3
        assert len(result.confidence_interval_upper) == 3
        assert all(l <= u for l, u in zip(result.confidence_interval_lower, result.confidence_interval_upper))

    def test_forecast_error_metrics(self):
        """Forecast includes error metrics."""
        engine = PredictiveEngine()
        data = [100, 110, 120, 130, 140]
        result = engine.linear_regression(data, periods=2)
        assert result.mape >= 0
        assert result.rmse >= 0


class TestBenchmarkEngine:
    """Test benchmarking functionality."""

    def test_add_benchmark(self):
        """Benchmark can be added."""
        engine = BenchmarkEngine()
        engine.add_benchmark("industry_avg_revenue", 50000.0, category="industry", unit="USD")
        assert "industry_avg_revenue" in engine._benchmarks

    def test_compare(self):
        """Comparison can be made."""
        engine = BenchmarkEngine()
        result = engine.compare("revenue", 60000.0, 50000.0, ComparisonType.INDUSTRY, "USD")
        assert result.entity_value == 60000.0
        assert result.benchmark_value == 50000.0
        assert result.gap == 10000.0
        assert result.gap_percent == 20.0

    def test_compare_leading(self):
        """Leading status is assigned correctly."""
        engine = BenchmarkEngine()
        result = engine.compare("revenue", 60000.0, 50000.0)
        assert result.status == "leading"

    def test_compare_competitive(self):
        """Competitive status is assigned correctly."""
        engine = BenchmarkEngine()
        result = engine.compare("revenue", 52000.0, 50000.0)
        assert result.status == "competitive"

    def test_compare_lagging(self):
        """Lagging status is assigned correctly."""
        engine = BenchmarkEngine()
        result = engine.compare("revenue", 45000.0, 50000.0)
        assert result.status == "lagging"

    def test_compare_critical(self):
        """Critical status is assigned correctly."""
        engine = BenchmarkEngine()
        result = engine.compare("revenue", 30000.0, 50000.0)
        assert result.status == "critical"

    def test_compare_to_benchmark(self):
        """Comparison to stored benchmark works."""
        engine = BenchmarkEngine()
        engine.add_benchmark("avg_revenue", 50000.0, unit="USD")
        result = engine.compare_to_benchmark("avg_revenue", 60000.0)
        assert result is not None
        assert result.gap == 10000.0

    def test_compare_to_benchmark_missing(self):
        """Missing benchmark returns None."""
        engine = BenchmarkEngine()
        result = engine.compare_to_benchmark("nonexistent", 60000.0)
        assert result is None

    def test_percentile_rank(self):
        """Percentile rank is calculated correctly."""
        engine = BenchmarkEngine()
        values = [10, 20, 30, 40, 50]
        rank = engine.percentile_rank(values, 30)
        assert rank == 50.0

    def test_compare_to_distribution(self):
        """Comparison to distribution works."""
        engine = BenchmarkEngine()
        distribution = [40000, 45000, 50000, 55000, 60000]
        result = engine.compare_to_distribution("revenue", 55000.0, distribution, "USD")
        assert result.entity_value == 55000.0
        assert result.percentile > 50

    def test_get_results(self):
        """All results can be retrieved."""
        engine = BenchmarkEngine()
        engine.compare("revenue", 60000.0, 50000.0)
        engine.compare("deals", 100.0, 80.0)
        results = engine.get_results()
        assert len(results) == 2

    def test_get_results_by_status(self):
        """Results can be filtered by status."""
        engine = BenchmarkEngine()
        engine.compare("revenue", 60000.0, 50000.0)  # leading
        engine.compare("deals", 30000.0, 50000.0)  # critical
        leading = engine.get_results_by_status("leading")
        critical = engine.get_results_by_status("critical")
        assert len(leading) == 1
        assert len(critical) == 1

    def test_get_summary(self):
        """Summary can be generated."""
        engine = BenchmarkEngine()
        engine.compare("revenue", 60000.0, 50000.0)
        engine.compare("deals", 100.0, 80.0)
        summary = engine.get_summary()
        assert summary["total_comparisons"] == 2
        assert "leading" in summary
        assert "average_percentile" in summary

    def test_get_gap_analysis(self):
        """Gap analysis can be generated."""
        engine = BenchmarkEngine()
        engine.compare("revenue", 60000.0, 50000.0)
        gaps = engine.get_gap_analysis()
        assert len(gaps) == 1
        assert gaps[0]["metric"] == "revenue"
        assert gaps[0]["direction"] == "positive"

    def test_clear(self):
        """All benchmarks and results can be cleared."""
        engine = BenchmarkEngine()
        engine.add_benchmark("test", 100.0)
        engine.compare("test", 120.0, 100.0)
        engine.clear()
        assert len(engine.get_results()) == 0


class TestExecutiveDashboard:
    """Test executive dashboard functionality."""

    def test_create_dashboard(self):
        """Dashboard can be created."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 1000.0, 1200.0, "USD")
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        result = dashboard.create_dashboard("Test Dashboard")
        assert result["name"] == "Test Dashboard"
        assert result["kpi_count"] == 1

    def test_create_dashboard_with_kpi_names(self):
        """Dashboard can be created with specific KPI names."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 1000.0, 1200.0, "USD")
        kpi_tracker.track("deals", 50.0, 60.0, "count")
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        result = dashboard.create_dashboard("Sales", kpi_names=["revenue"])
        assert result["kpi_count"] == 1

    def test_generate_executive_summary(self):
        """Executive summary can be generated."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 1000.0, 1200.0, "USD")
        kpi_tracker.track("deals", 50.0, 60.0, "count")
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        summary = dashboard.generate_executive_summary()
        assert summary.title == "Executive Summary"
        assert summary.overall_health in ["excellent", "good", "fair", "poor"]
        assert len(summary.key_metrics) == 2

    def test_executive_summary_health_excellent(self):
        """Excellent health is assigned when achievement >= 100%."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 1200.0, 1000.0, "USD")
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        summary = dashboard.generate_executive_summary()
        assert summary.overall_health == "excellent"

    def test_executive_summary_health_poor(self):
        """Poor health is assigned when achievement < 60%."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 500.0, 1000.0, "USD")
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        summary = dashboard.generate_executive_summary()
        assert summary.overall_health == "poor"

    def test_executive_summary_highlights(self):
        """Highlights are generated for exceeding/on-track KPIs."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 1200.0, 1000.0, "USD")  # exceeding
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        summary = dashboard.generate_executive_summary()
        assert len(summary.highlights) > 0

    def test_executive_summary_concerns(self):
        """Concerns are generated for warning/critical KPIs."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 400.0, 1000.0, "USD")  # critical
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        summary = dashboard.generate_executive_summary()
        assert len(summary.concerns) > 0

    def test_executive_summary_recommendations(self):
        """Recommendations are generated."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 1000.0, 1200.0, "USD")
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        summary = dashboard.generate_executive_summary()
        assert len(summary.recommendations) > 0

    def test_get_dashboard(self):
        """Dashboard can be retrieved by name."""
        kpi_tracker = KPITracker()
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        dashboard.create_dashboard("Test")
        result = dashboard.get_dashboard("Test")
        assert result is not None
        assert result["name"] == "Test"

    def test_get_all_dashboards(self):
        """All dashboards can be retrieved."""
        kpi_tracker = KPITracker()
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        dashboard.create_dashboard("Dash1")
        dashboard.create_dashboard("Dash2")
        all_dash = dashboard.get_all_dashboards()
        assert len(all_dash) == 2

    def test_generate_board_report(self):
        """Board report can be generated."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 1000.0, 1200.0, "USD")
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        report = dashboard.generate_board_report()
        assert "executive_summary" in report
        assert "benchmark_summary" in report
        assert "scorecard" in report

    def test_generate_trend_report(self):
        """Trend report can be generated."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 1000.0, 1200.0, "USD")
        kpi_tracker.track("revenue", 1100.0, 1200.0, "USD")
        kpi_tracker.track("revenue", 1050.0, 1200.0, "USD")
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        report = dashboard.generate_trend_report(["revenue"])
        assert "trends" in report
        assert "revenue" in report["trends"]

    def test_clear_dashboards(self):
        """All dashboards can be cleared."""
        kpi_tracker = KPITracker()
        dashboard = ExecutiveDashboard(kpi_tracker=kpi_tracker)
        dashboard.create_dashboard("Test")
        dashboard.clear()
        assert len(dashboard.get_all_dashboards()) == 0

    def test_executive_summary_to_dict(self):
        """Executive summary can be converted to dictionary."""
        summary = ExecutiveSummary(
            title="Test",
            period="Q1",
            overall_health="good",
            key_metrics=[{"name": "revenue", "value": 100}],
            highlights=["Good performance"],
            concerns=["None"],
            recommendations=["Continue"],
        )
        d = summary.to_dict()
        assert d["title"] == "Test"
        assert d["overall_health"] == "good"
        assert len(d["key_metrics"]) == 1


class TestIntegration:
    """Integration tests for BI system."""

    def test_full_kpi_workflow(self):
        """Full KPI tracking workflow works."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD", category="sales")
        tracker.track("revenue", 1100.0, 1200.0, "USD", category="sales")
        tracker.track("satisfaction", 4.5, 4.0, "rating", category="customer")

        summary = tracker.get_summary()
        assert summary["total"] == 3

        scorecard = tracker.get_scorecard()
        assert "sales" in scorecard
        assert "customer" in scorecard

    def test_full_benchmark_workflow(self):
        """Full benchmarking workflow works."""
        engine = BenchmarkEngine()
        engine.add_benchmark("industry_revenue", 50000.0, unit="USD")
        result = engine.compare_to_benchmark("industry_revenue", 60000.0)
        assert result is not None
        assert result.status == "leading"

        summary = engine.get_summary()
        assert summary["total_comparisons"] == 1

    def test_full_predictive_workflow(self):
        """Full predictive analytics workflow works."""
        engine = PredictiveEngine()
        data = [100, 110, 120, 130, 140, 150, 160]

        ma = engine.moving_average(data, periods=3)
        assert len(ma.predictions) == 3

        es = engine.exponential_smoothing(data, periods=3)
        assert len(es.predictions) == 3

        lr = engine.linear_regression(data, periods=3)
        assert len(lr.predictions) == 3

        trend = engine.detect_trend(data)
        assert trend["trend"] == "increasing"

    def test_full_executive_dashboard_workflow(self):
        """Full executive dashboard workflow works."""
        kpi_tracker = KPITracker()
        kpi_tracker.track("revenue", 1000.0, 1200.0, "USD", category="financial")
        kpi_tracker.track("satisfaction", 4.5, 4.0, "rating", category="customer")

        benchmark_engine = BenchmarkEngine()
        benchmark_engine.compare("revenue", 1000.0, 900.0)

        dashboard = ExecutiveDashboard(
            kpi_tracker=kpi_tracker,
            benchmark_engine=benchmark_engine,
        )

        dash = dashboard.create_dashboard("Executive")
        assert dash["kpi_count"] == 2

        summary = dashboard.generate_executive_summary()
        assert summary.overall_health in ["excellent", "good", "fair", "poor"]

        report = dashboard.generate_board_report()
        assert "executive_summary" in report
        assert "benchmark_summary" in report

    def test_kpi_with_visualization(self):
        """KPI data can be visualized."""
        tracker = KPITracker()
        tracker.track("revenue", 1000.0, 1200.0, "USD")
        tracker.track("revenue", 1100.0, 1200.0, "USD")
        tracker.track("revenue", 1050.0, 1200.0, "USD")

        trend = tracker.get_trend("revenue")
        data_points = [DataPoint(label=t["timestamp"][:10], value=t["value"]) for t in trend]

        viz = DataVisualizer()
        chart = viz.create_line_chart(
            [ChartSeries(name="Revenue", data=data_points)],
            ChartConfig(title="Revenue Trend"),
        )
        assert chart["type"] == "line"
        assert len(chart["series"][0]["data"]) == 3

    def test_predictive_with_kpi(self):
        """Predictive analytics works with KPI data."""
        tracker = KPITracker()
        for i, val in enumerate([100, 110, 120, 130, 140]):
            tracker.track("revenue", float(val), 150.0, "USD")

        trend = tracker.get_trend("revenue")
        values = [t["value"] for t in trend]

        engine = PredictiveEngine()
        forecast = engine.linear_regression(values, periods=3)
        assert len(forecast.predictions) == 3
        assert all(p > 0 for p in forecast.predictions)
