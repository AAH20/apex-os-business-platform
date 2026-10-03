"""Tests for deepened analytics module."""
import pytest
from datetime import date, timedelta
from decimal import Decimal


class TestCohortAnalysis:
    @pytest.fixture
    def analyzer(self):
        from apex_os_bp.analytics.deepened import CohortAnalyzer
        return CohortAnalyzer()

    def test_cohort_retention(self, analyzer):
        users = [
            {"id": 1, "signup": date(2024, 1, 1), "active_dates": [date(2024, 1, 1), date(2024, 2, 1)]},
            {"id": 2, "signup": date(2024, 1, 1), "active_dates": [date(2024, 1, 1)]},
        ]
        result = analyzer.analyze(users, period="monthly")
        assert result["2024-01"]["size"] == 2
        assert result["2024-01"]["retention"][0] == 1.0

    def test_empty_cohort(self, analyzer):
        result = analyzer.analyze([], period="monthly")
        assert result == {}

    def test_multiple_cohorts(self, analyzer):
        users = [
            {"id": 1, "signup": date(2024, 1, 1), "active_dates": [date(2024, 1, 1)]},
            {"id": 2, "signup": date(2024, 2, 1), "active_dates": [date(2024, 2, 1)]},
        ]
        result = analyzer.analyze(users, period="monthly")
        assert "2024-01" in result
        assert "2024-02" in result


class TestFunnelAnalysis:
    @pytest.fixture
    def funnel(self):
        from apex_os_bp.analytics.deepened import FunnelAnalyzer
        return FunnelAnalyzer()

    def test_funnel_conversion(self, funnel):
        events = [
            {"user": 1, "step": "view"},
            {"user": 1, "step": "signup"},
            {"user": 1, "step": "purchase"},
            {"user": 2, "step": "view"},
            {"user": 2, "step": "signup"},
        ]
        result = funnel.analyze(events, ["view", "signup", "purchase"])
        assert result["steps"]["view"] == 2
        assert result["steps"]["purchase"] == 1
        assert result["overall_conversion"] == 0.5

    def test_step_dropoff(self, funnel):
        events = [{"user": i, "step": "view"} for i in range(10)]
        events += [{"user": i, "step": "signup"} for i in range(5)]
        result = funnel.analyze(events, ["view", "signup"])
        assert result["dropoff"]["view_to_signup"] == 0.5

    def test_empty_funnel(self, funnel):
        result = funnel.analyze([], ["view", "signup"])
        assert result["overall_conversion"] == 0


class TestForecasting:
    @pytest.fixture
    def forecaster(self):
        from apex_os_bp.analytics.deepened import Forecaster
        return Forecaster()

    def test_linear_trend(self, forecaster):
        data = [{"date": date(2024, 1, i + 1), "value": 100 + i * 10} for i in range(10)]
        result = forecaster.forecast(data, periods=3)
        assert len(result) == 3
        assert result[-1]["value"] > result[0]["value"]

    def test_forecast_confidence_interval(self, forecaster):
        data = [{"date": date(2024, 1, i + 1), "value": 100} for i in range(5)]
        result = forecaster.forecast(data, periods=1)
        assert "lower" in result[0]
        assert "upper" in result[0]

    def test_insufficient_data(self, forecaster):
        with pytest.raises(ValueError):
            forecaster.forecast([], periods=3)


class TestAnomalyDetection:
    @pytest.fixture
    def detector(self):
        from apex_os_bp.analytics.deepened import AnomalyDetector
        return AnomalyDetector(threshold=2.0)

    def test_detects_outlier(self, detector):
        data = [10, 11, 10, 12, 11, 100, 10, 11]
        anomalies = detector.detect(data)
        assert 5 in anomalies  # index of 100

    def test_no_anomalies_in_stable_data(self, detector):
        data = [10, 11, 10, 11, 10, 11, 10, 11]
        assert detector.detect(data) == []

    def test_custom_threshold(self):
        from apex_os_bp.analytics.deepened import AnomalyDetector
        detector = AnomalyDetector(threshold=1.0)
        data = [10, 11, 10, 15]
        assert len(detector.detect(data)) > 0


class TestCorrelation:
    @pytest.fixture
    def analyzer(self):
        from apex_os_bp.analytics.deepened import CorrelationAnalyzer
        return CorrelationAnalyzer()

    def test_positive_correlation(self, analyzer):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        result = analyzer.pearson(x, y)
        assert result == pytest.approx(1.0)

    def test_negative_correlation(self, analyzer):
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        result = analyzer.pearson(x, y)
        assert result == pytest.approx(-1.0)

    def test_no_correlation(self, analyzer):
        x = [1, 2, 3]
        y = [3, 1, 2]
        result = analyzer.pearson(x, y)
        assert abs(result) < 0.5

    def test_unequal_length_raises(self, analyzer):
        with pytest.raises(ValueError):
            analyzer.pearson([1, 2], [1])
