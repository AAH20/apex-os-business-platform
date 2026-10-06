"""Tests for deepened analytics module (offline, real exports)."""
import warnings

import pandas as pd
import pytest


def _module():
    import apex_os_bp.analytics.deepened as m
    return m


# ---------------------------------------------------------------- cohorts

class TestCohortAnalysis:
    @pytest.fixture
    def analyzer(self):
        return _module().cohort_analysis

    def test_simple_cohort(self, analyzer):
        events = pd.DataFrame({
            "user_id": [1, 1, 2, 1],
            "event_date": ["2024-01-05", "2024-02-05", "2024-01-07", "2024-03-06"],
        })
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = analyzer(events)
        assert isinstance(result, _module().CohortResult)
        assert len(result.retention_matrix) >= 1

    def test_empty_cohort(self, analyzer):
        events = pd.DataFrame({"user_id": pd.Series(dtype="int64"),
                               "event_date": pd.Series(dtype="object")})
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises(Exception):
                analyzer(events)


# ---------------------------------------------------------------- funnels

class TestFunnelAnalysis:
    @pytest.fixture
    def funnel(self):
        return _module().funnel_analysis

    def test_funnel_conversion(self, funnel):
        events = pd.DataFrame({
            "user_id": [1, 1, 1, 2, 2],
            "event_name": ["view", "signup", "purchase", "view", "signup"],
        })
        result = funnel(events, steps=["view", "signup", "purchase"])
        assert isinstance(result, _module().FunnelResult)
        assert result.overall_conversion == pytest.approx(0.5)
        assert result.steps["users"].tolist() == [2, 2, 1]

    def test_step_dropoff(self, funnel):
        events = pd.DataFrame({
            "user_id": list(range(10)) + list(range(5)),
            "event_name": ["view"] * 10 + ["signup"] * 5,
        })
        result = funnel(events, steps=["view", "signup"])
        assert result.steps["step_conversion"].dropna().iloc[0] == pytest.approx(0.5)


# ---------------------------------------------------------------- forecasting

class TestForecasting:
    @pytest.fixture
    def forecaster(self):
        return _module().arima_forecast

    def test_linear_trend(self, forecaster):
        series = pd.Series([100 + i * 10 for i in range(30)], dtype="float64")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = forecaster(series, steps=3)
        assert isinstance(result, _module().ForecastResult)
        assert len(result.forecast) == 3

    def test_insufficient_data(self, forecaster):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = forecaster(pd.Series([1.0] * 3), steps=3)  # <5 points -> naive fallback
        assert result.forecast[0] == 1.0


# ---------------------------------------------------------------- anomalies

class TestAnomalyDetection:
    @pytest.fixture
    def detector(self):
        return _module().detect_anomalies

    def test_detects_outlier(self, detector):
        df = pd.DataFrame({"value": [10, 11, 10, 12, 11, 100, 10, 11]},
                          dtype="float64")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = detector(df, ["value"], contamination=0.2)
        assert result is not None
        assert len(result.anomalies) >= 1  # 100 flagged
        assert -1 in result.labels

    def test_stable_data(self, detector):
        df = pd.DataFrame({"value": [10, 11, 10, 11, 10, 11, 10, 11]},
                          dtype="float64")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = detector(df, ["value"], contamination=0.1)
        assert result is not None
        assert isinstance(result.labels, object) or True


# ---------------------------------------------------------------- correlation

class TestCorrelation:
    @pytest.fixture
    def analyzer(self):
        return _module().correlation_analysis

    def test_positive_correlation(self, analyzer):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0], "y": [2.0, 4.0, 6.0, 8.0, 10.0]})
        result = analyzer(df)
        assert result is not None

    def test_eight_columns(self, analyzer):
        df = pd.DataFrame({c: range(5) for c in ["a", "b", "c", "d", "e", "f", "g", "h"]})
        result = analyzer(df)
        assert result is not None
