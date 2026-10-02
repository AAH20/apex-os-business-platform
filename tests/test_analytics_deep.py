"""Tests for the deepened analytics module.

Covers forecasting, anomaly detection, cohort analysis, funnel
analysis, and the custom report builder.
"""
import json
import math

import pytest

from apex_os_bp.analytics.anomaly import (
    Anomaly,
    AnomalyDetector,
    detect_iqr,
    detect_modified_zscore,
    detect_rolling_zscore,
    detect_zscore,
)
from apex_os_bp.analytics.cohort import (
    Cohort,
    CohortAnalysis,
    CohortEvent,
)
from apex_os_bp.analytics.forecasting import (
    Forecast,
    forecast,
    forecast_from_metrics,
    linear_trend,
    moving_average,
    exponential_smoothing,
)
from apex_os_bp.analytics.funnel import (
    Funnel,
    FunnelEvent,
    FunnelStep,
    funnel_from_events,
)
from apex_os_bp.analytics.report_builder import (
    ReportBuilder,
    ReportMetric,
    ReportSection,
    aggregate,
)


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------


class TestMovingAverage:
    def test_basic(self):
        result = moving_average([1, 2, 3, 4, 5], window=3)
        assert result == pytest.approx([1.0, 1.5, 2.0, 3.0, 4.0])

    def test_window_one_returns_input(self):
        result = moving_average([10, 20, 30], window=1)
        assert result == pytest.approx([10.0, 20.0, 30.0])

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            moving_average([1, 2, 3], window=0)

    def test_empty_series(self):
        with pytest.raises(ValueError):
            moving_average([])


class TestExponentialSmoothing:
    def test_basic(self):
        result = exponential_smoothing([10, 20, 30], alpha=0.5)
        assert result[0] == pytest.approx(10.0)
        assert result[1] == pytest.approx(15.0)
        assert result[2] == pytest.approx(22.5)

    def test_alpha_one_returns_input(self):
        result = exponential_smoothing([1, 2, 3], alpha=1.0)
        assert result == pytest.approx([1.0, 2.0, 3.0])

    def test_invalid_alpha(self):
        with pytest.raises(ValueError):
            exponential_smoothing([1, 2, 3], alpha=0.0)
        with pytest.raises(ValueError):
            exponential_smoothing([1, 2, 3], alpha=1.5)


class TestLinearTrend:
    def test_perfect_line(self):
        slope, intercept = linear_trend([2, 4, 6, 8])
        assert slope == pytest.approx(2.0)
        assert intercept == pytest.approx(2.0)

    def test_single_point(self):
        slope, intercept = linear_trend([42])
        assert slope == pytest.approx(0.0)
        assert intercept == pytest.approx(42.0)


class TestForecast:
    def test_naive_method(self):
        result = forecast([10, 20, 30], steps=2, method="naive")
        assert result.method == "naive"
        assert len(result.points) == 2
        assert result.values == pytest.approx([30.0, 30.0])

    def test_sma_method(self):
        result = forecast([10, 20, 30], steps=2, method="sma", window=2)
        assert result.method == "sma"
        assert len(result.points) == 2
        # SMA of last 2 = 25
        assert result.values == pytest.approx([25.0, 25.0])

    def test_ema_method(self):
        result = forecast([10, 20, 30], steps=2, method="ema", alpha=0.5)
        assert result.method == "ema"
        assert len(result.points) == 2
        # EMA: 10, 15, 22.5
        assert result.values == pytest.approx([22.5, 22.5])

    def test_linear_method(self):
        result = forecast([2, 4, 6, 8], steps=2, method="linear")
        assert result.method == "linear"
        assert result.values == pytest.approx([10.0, 12.0])

    def test_auto_selects_linear_for_trending_series(self):
        result = forecast([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], steps=1, method="auto")
        assert result.method == "linear"

    def test_auto_selects_ema_for_flat_series(self):
        result = forecast([5, 5, 5, 5, 5, 5, 5, 5, 5, 5], steps=1, method="auto")
        assert result.method == "ema"

    def test_auto_selects_naive_for_short_series(self):
        result = forecast([1, 2], steps=1, method="auto")
        assert result.method == "naive"

    def test_confidence_interval_widens_for_linear(self):
        result = forecast([2, 4, 7, 8], steps=3, method="linear")
        widths = [p.upper - p.lower for p in result.points]
        assert widths[0] < widths[1] < widths[2]

    def test_invalid_method(self):
        with pytest.raises(ValueError):
            forecast([1, 2, 3], steps=1, method="bogus")

    def test_invalid_steps(self):
        with pytest.raises(ValueError):
            forecast([1, 2, 3], steps=0)

    def test_empty_series(self):
        with pytest.raises(ValueError):
            forecast([], steps=1)

    def test_forecast_summary(self):
        result = forecast([10, 20, 30], steps=2, method="naive")
        summary = result.summary()
        assert summary["method"] == "naive"
        assert summary["steps"] == 2
        assert summary["values"] == pytest.approx([30.0, 30.0])

    def test_forecast_point_structure(self):
        result = forecast([10, 20, 30], steps=1, method="naive")
        point = result.points[0]
        assert point.step == 1
        assert point.value == pytest.approx(30.0)
        assert point.lower <= point.value <= point.upper


class TestForecastFromMetrics:
    def test_orders_by_timestamp(self):
        class M:
            def __init__(self, value, timestamp):
                self.value = value
                self.timestamp = timestamp

        metrics = [M(30, "2026-01-03"), M(10, "2026-01-01"), M(20, "2026-01-02")]
        result = forecast_from_metrics(metrics, steps=1, method="naive")
        assert result.values == pytest.approx([30.0])

    def test_empty_metrics(self):
        with pytest.raises(ValueError):
            forecast_from_metrics([], steps=1)


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


class TestDetectZScore:
    def test_detects_outlier(self):
        series = [10, 11, 12, 11, 10, 11, 100]
        anomalies = detect_zscore(series, threshold=2.0)
        assert len(anomalies) >= 1
        assert any(a.index == 6 for a in anomalies)

    def test_no_anomalies_in_uniform_series(self):
        series = [5, 5, 5, 5, 5]
        assert detect_zscore(series) == []

    def test_invalid_threshold(self):
        with pytest.raises(ValueError):
            detect_zscore([1, 2, 3], threshold=0)

    def test_empty_series(self):
        with pytest.raises(ValueError):
            detect_zscore([])

    def test_anomaly_fields(self):
        series = [10, 11, 12, 11, 10, 11, 100]
        anomalies = detect_zscore(series, threshold=2.0)
        a = anomalies[0]
        assert isinstance(a, Anomaly)
        assert a.method == "zscore"
        assert a.expected_low is not None
        assert a.expected_high is not None


class TestDetectModifiedZScore:
    def test_detects_outlier(self):
        series = [10, 11, 12, 11, 10, 11, 100]
        anomalies = detect_modified_zscore(series, threshold=3.0)
        assert len(anomalies) >= 1
        assert any(a.index == 6 for a in anomalies)

    def test_robust_to_median(self):
        # Median-based: adding one extreme value shouldn't shift the center
        series = [10, 11, 12, 11, 10, 11, 100]
        anomalies = detect_modified_zscore(series, threshold=3.5)
        assert len(anomalies) >= 1

    def test_no_anomalies_in_uniform_series(self):
        assert detect_modified_zscore([5, 5, 5, 5, 5]) == []


class TestDetectIQR:
    def test_detects_outlier(self):
        series = [10, 11, 12, 11, 10, 11, 100]
        anomalies = detect_iqr(series, factor=1.5)
        assert len(anomalies) >= 1
        assert any(a.index == 6 for a in anomalies)

    def test_no_anomalies_in_tight_series(self):
        series = [10, 11, 12, 11, 10, 11]
        assert detect_iqr(series) == []

    def test_invalid_factor(self):
        with pytest.raises(ValueError):
            detect_iqr([1, 2, 3], factor=0)


class TestDetectRollingZScore:
    def test_detects_outlier(self):
        series = [10, 11, 12, 11, 10, 11, 100]
        anomalies = detect_rolling_zscore(series, window=5, threshold=2.0)
        assert len(anomalies) >= 1
        assert any(a.index == 6 for a in anomalies)

    def test_skips_insufficient_history(self):
        series = [10, 100]
        anomalies = detect_rolling_zscore(series, window=5, min_periods=2)
        # Only index 1 has enough history
        assert all(a.index >= 1 for a in anomalies)

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            detect_rolling_zscore([1, 2, 3], window=1)


class TestAnomalyDetector:
    def test_zscore_method(self):
        det = AnomalyDetector(method="zscore", threshold=2.0)
        anomalies = det.detect([10, 11, 12, 11, 10, 11, 100])
        assert len(anomalies) >= 1

    def test_iqr_method(self):
        det = AnomalyDetector(method="iqr", factor=1.5)
        anomalies = det.detect([10, 11, 12, 11, 10, 11, 100])
        assert len(anomalies) >= 1

    def test_rolling_method(self):
        det = AnomalyDetector(method="rolling_zscore", window=5, threshold=2.0)
        anomalies = det.detect([10, 11, 12, 11, 10, 11, 100])
        assert len(anomalies) >= 1

    def test_invalid_method(self):
        with pytest.raises(ValueError):
            AnomalyDetector(method="bogus")

    def test_detect_from_metrics(self):
        class M:
            def __init__(self, value, timestamp):
                self.value = value
                self.timestamp = timestamp

        metrics = [
            M(10, "2026-01-01"),
            M(11, "2026-01-02"),
            M(12, "2026-01-03"),
            M(100, "2026-01-04"),
        ]
        det = AnomalyDetector(method="zscore", threshold=1.0)
        anomalies = det.detect_from_metrics(metrics)
        assert len(anomalies) >= 1

    def test_summary(self):
        det = AnomalyDetector(method="zscore", threshold=2.0)
        summary = det.summary([10, 11, 12, 11, 10, 11, 100])
        assert summary["method"] == "zscore"
        assert summary["series_length"] == 7
        assert summary["anomaly_count"] >= 1
        assert "anomalies" in summary


# ---------------------------------------------------------------------------
# Cohort analysis
# ---------------------------------------------------------------------------


class TestCohortEvent:
    def test_period_month(self):
        ev = CohortEvent(user_id="u1", timestamp="2026-03-15T10:00:00")
        assert ev.period("month") == "2026-03"

    def test_period_day(self):
        ev = CohortEvent(user_id="u1", timestamp="2026-03-15T10:00:00")
        assert ev.period("day") == "2026-03-15"

    def test_period_quarter(self):
        ev = CohortEvent(user_id="u1", timestamp="2026-05-15T10:00:00")
        assert ev.period("quarter") == "2026-Q2"

    def test_period_year(self):
        ev = CohortEvent(user_id="u1", timestamp="2026-05-15T10:00:00")
        assert ev.period("year") == "2026"

    def test_invalid_period(self):
        ev = CohortEvent(user_id="u1", timestamp="2026-03-15T10:00:00")
        with pytest.raises(ValueError):
            ev.period("bogus")


class TestCohortAnalysis:
    def _make_events(self):
        """Two cohorts: Jan (3 users) and Feb (2 users).

        Jan cohort: u1 active in Jan+Feb+Mar, u2 active in Jan+Feb, u3 active in Jan only.
        Feb cohort: u4 active in Feb+Mar, u5 active in Feb only.
        """
        return [
            CohortEvent("u1", "2026-01-05"),
            CohortEvent("u1", "2026-02-10"),
            CohortEvent("u1", "2026-03-15"),
            CohortEvent("u2", "2026-01-06"),
            CohortEvent("u2", "2026-02-11"),
            CohortEvent("u3", "2026-01-07"),
            CohortEvent("u4", "2026-02-05"),
            CohortEvent("u4", "2026-03-10"),
            CohortEvent("u5", "2026-02-06"),
        ]

    def test_cohort_sizes(self):
        ca = CohortAnalysis(self._make_events())
        cohorts = {c.key: c for c in ca.cohorts}
        assert cohorts["2026-01"].size == 3
        assert cohorts["2026-02"].size == 2

    def test_retention_matrix(self):
        ca = CohortAnalysis(self._make_events())
        matrix = ca.retention_matrix()
        assert matrix["granularity"] == "month"
        assert matrix["periods"] == 3
        cohorts = {c["key"]: c for c in matrix["cohorts"]}
        # Jan cohort: 3/3, 2/3, 1/3
        assert cohorts["2026-01"]["retention"] == pytest.approx(
            [1.0, 2 / 3, 1 / 3]
        )
        # Feb cohort: 2/2, 1/2, 0/2
        assert cohorts["2026-02"]["retention"] == pytest.approx([1.0, 0.5, 0.0])

    def test_average_retention(self):
        ca = CohortAnalysis(self._make_events())
        avg = ca.average_retention()
        # Period 0: (1.0 + 1.0) / 2 = 1.0
        # Period 1: (2/3 + 0.5) / 2 = 7/12
        # Period 2: (1/3 + 0) / 2 = 1/6
        assert avg[0] == pytest.approx(1.0)
        assert avg[1] == pytest.approx(7 / 12)
        assert avg[2] == pytest.approx(1 / 6)

    def test_summary(self):
        ca = CohortAnalysis(self._make_events())
        summary = ca.summary()
        assert summary["cohort_count"] == 2
        assert summary["total_users"] == 5
        assert "average_retention" in summary
        assert "matrix" in summary

    def test_empty_events(self):
        ca = CohortAnalysis([])
        assert ca.cohorts == []
        assert ca.retention_matrix()["cohorts"] == []

    def test_invalid_granularity(self):
        with pytest.raises(ValueError):
            CohortAnalysis([], granularity="bogus")

    def test_cohort_to_dict(self):
        c = Cohort(key="2026-01", size=10, retention=[1.0, 0.5])
        d = c.to_dict()
        assert d["key"] == "2026-01"
        assert d["size"] == 10
        assert d["retention"] == [1.0, 0.5]
        assert d["average_retention"] == pytest.approx(0.75)

    def test_cohort_average_retention_empty(self):
        c = Cohort(key="2026-01", size=0, retention=[])
        assert c.average_retention == 0.0


# ---------------------------------------------------------------------------
# Funnel analysis
# ---------------------------------------------------------------------------


class TestFunnel:
    def _make_funnel(self):
        """Funnel: signup -> activate -> purchase.

        u1: all 3 steps
        u2: signup + activate
        u3: signup only
        u4: all 3 steps
        """
        f = Funnel(name="Onboarding", steps=["signup", "activate", "purchase"])
        f.add_event("u1", "signup")
        f.add_event("u1", "activate")
        f.add_event("u1", "purchase")
        f.add_event("u2", "signup")
        f.add_event("u2", "activate")
        f.add_event("u3", "signup")
        f.add_event("u4", "signup")
        f.add_event("u4", "activate")
        f.add_event("u4", "purchase")
        return f

    def test_step_counts(self):
        f = self._make_funnel()
        steps = f.computed_steps
        assert steps[0].count == 4  # signup
        assert steps[1].count == 3  # activate
        assert steps[2].count == 2  # purchase

    def test_conversion_from_previous(self):
        f = self._make_funnel()
        steps = f.computed_steps
        assert steps[0].conversion_from_previous == pytest.approx(1.0)
        assert steps[1].conversion_from_previous == pytest.approx(0.75)
        assert steps[2].conversion_from_previous == pytest.approx(2 / 3)

    def test_conversion_from_top(self):
        f = self._make_funnel()
        steps = f.computed_steps
        assert steps[0].conversion_from_top == pytest.approx(1.0)
        assert steps[1].conversion_from_top == pytest.approx(0.75)
        assert steps[2].conversion_from_top == pytest.approx(0.5)

    def test_dropoff(self):
        f = self._make_funnel()
        steps = f.computed_steps
        assert steps[1].dropoff_count == 1
        assert steps[2].dropoff_count == 1

    def test_overall_conversion(self):
        f = self._make_funnel()
        assert f.overall_conversion == pytest.approx(0.5)

    def test_biggest_dropoff(self):
        f = self._make_funnel()
        drop = f.biggest_dropoff
        assert drop is not None
        assert drop.name == "purchase"

    def test_summary(self):
        f = self._make_funnel()
        summary = f.summary()
        assert summary["name"] == "Onboarding"
        assert len(summary["steps"]) == 3
        assert summary["overall_conversion"] == pytest.approx(0.5)

    def test_empty_funnel(self):
        f = Funnel(name="Empty", steps=["a", "b"])
        assert f.overall_conversion == 0.0
        assert f.biggest_dropoff is None

    def test_invalid_step(self):
        f = Funnel(name="Test", steps=["a", "b"])
        with pytest.raises(ValueError):
            f.add_event("u1", "c")

    def test_empty_steps(self):
        with pytest.raises(ValueError):
            Funnel(name="Test", steps=[])

    def test_duplicate_steps(self):
        with pytest.raises(ValueError):
            Funnel(name="Test", steps=["a", "a"])

    def test_add_events_bulk(self):
        f = Funnel(name="Test", steps=["a", "b"])
        events = [
            FunnelEvent("u1", "a"),
            FunnelEvent("u1", "b"),
            FunnelEvent("u2", "a"),
        ]
        f.add_events(events)
        assert f.computed_steps[0].count == 2
        assert f.computed_steps[1].count == 1

    def test_funnel_from_events(self):
        events = [("u1", "a"), ("u1", "b"), ("u2", "a")]
        f = funnel_from_events("Test", ["a", "b"], events)
        assert f.computed_steps[0].count == 2
        assert f.computed_steps[1].count == 1

    def test_funnel_step_to_dict(self):
        s = FunnelStep(
            name="a",
            count=10,
            conversion_from_previous=1.0,
            conversion_from_top=1.0,
            dropoff_from_previous=0.0,
            dropoff_count=0,
        )
        d = s.to_dict()
        assert d["name"] == "a"
        assert d["count"] == 10


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


class TestAggregate:
    def test_sum(self):
        assert aggregate([1, 2, 3], "sum") == 6.0

    def test_avg(self):
        assert aggregate([1, 2, 3], "avg") == 2.0

    def test_mean_alias(self):
        assert aggregate([1, 2, 3], "mean") == 2.0

    def test_min(self):
        assert aggregate([3, 1, 2], "min") == 1.0

    def test_max(self):
        assert aggregate([3, 1, 2], "max") == 3.0

    def test_count(self):
        assert aggregate([3, 1, 2], "count") == 3.0

    def test_median_odd(self):
        assert aggregate([3, 1, 2], "median") == 2.0

    def test_median_even(self):
        assert aggregate([4, 1, 3, 2], "median") == 2.5

    def test_std(self):
        result = aggregate([2, 4, 4, 4, 5, 5, 7, 9], "std")
        assert result == pytest.approx(2.138, rel=1e-2)

    def test_empty_series(self):
        with pytest.raises(ValueError):
            aggregate([], "sum")

    def test_unknown_func(self):
        with pytest.raises(ValueError):
            aggregate([1, 2, 3], "bogus")


class TestReportBuilder:
    def test_add_section_and_metric(self):
        rb = ReportBuilder(title="Test Report")
        sec = rb.add_section("Revenue")
        sec.add("total", 1000, unit="USD")
        report = rb.build()
        assert report["title"] == "Test Report"
        assert report["section_count"] == 1
        assert report["metric_count"] == 1

    def test_add_metric_by_index(self):
        rb = ReportBuilder(title="Test")
        rb.add_section("S1")
        rb.add_metric(0, "m1", 42)
        report = rb.build()
        assert report["sections"][0]["metrics"][0]["value"] == 42

    def test_add_metric_by_title(self):
        rb = ReportBuilder(title="Test")
        rb.add_section("Sales")
        rb.add_metric("Sales", "m1", 42)
        report = rb.build()
        assert report["sections"][0]["metrics"][0]["value"] == 42

    def test_add_computed(self):
        rb = ReportBuilder(title="Test")
        rb.add_section("Live")
        rb.add_computed("Live", "total", lambda: 999)
        report = rb.build()
        assert report["sections"][0]["metrics"][0]["value"] == 999

    def test_add_aggregation(self):
        rb = ReportBuilder(title="Test")
        rb.add_section("Stats")
        rb.add_aggregation("Stats", "avg", [10, 20, 30], "avg")
        report = rb.build()
        assert report["sections"][0]["metrics"][0]["value"] == pytest.approx(20.0)

    def test_section_not_found(self):
        rb = ReportBuilder(title="Test")
        with pytest.raises(KeyError):
            rb.add_metric("Nonexistent", "m", 1)

    def test_section_index_out_of_range(self):
        rb = ReportBuilder(title="Test")
        with pytest.raises(IndexError):
            rb.add_metric(5, "m", 1)

    def test_to_json(self):
        rb = ReportBuilder(title="Test")
        sec = rb.add_section("S1")
        sec.add("m1", 42)
        data = json.loads(rb.to_json())
        assert data["title"] == "Test"
        assert data["sections"][0]["metrics"][0]["value"] == 42

    def test_to_markdown(self):
        rb = ReportBuilder(title="My Report", description="A test report")
        sec = rb.add_section("Revenue", description="Monthly revenue")
        sec.add("total", 1000, unit="USD", description="Total revenue")
        md = rb.to_markdown()
        assert "# My Report" in md
        assert "## Revenue" in md
        assert "total" in md
        assert "1000" in md

    def test_chaining(self):
        rb = ReportBuilder(title="Test")
        rb.add_section("A").add("m1", 1).add("m2", 2)
        rb.add_section("B").add("m3", 3)
        report = rb.build()
        assert report["metric_count"] == 3

    def test_report_metric_to_dict(self):
        m = ReportMetric(name="m", value=1, unit="USD", description="desc", tags=["t1"])
        d = m.to_dict()
        assert d["name"] == "m"
        assert d["value"] == 1
        assert d["unit"] == "USD"
        assert d["description"] == "desc"
        assert d["tags"] == ["t1"]

    def test_report_section_to_dict(self):
        s = ReportSection(title="S", description="desc")
        s.add("m", 1)
        d = s.to_dict()
        assert d["title"] == "S"
        assert d["description"] == "desc"
        assert len(d["metrics"]) == 1

    def test_empty_report(self):
        rb = ReportBuilder(title="Empty")
        report = rb.build()
        assert report["section_count"] == 0
        assert report["metric_count"] == 0
