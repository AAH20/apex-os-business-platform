"""Tests for advanced Data Science features."""

import pytest
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification

from apex_os_bp.datascience.advanced import (
    ModelRegistry, ABTest, DriftDetector, Explainability, AutoML,
)


@pytest.fixture
def sample_data():
    return make_classification(n_samples=200, n_features=5, random_state=42)


class TestModelRegistry:
    def test_register_and_get(self):
        reg = ModelRegistry()
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        version = reg.register("rf", model, {"type": "classifier"})
        assert version is not None
        assert reg.get("rf") is model
        assert reg.get_version("rf") == version
        assert "rf" in reg.list_models()

    def test_remove(self):
        reg = ModelRegistry()
        reg.register("test", RandomForestClassifier())
        assert reg.remove("test") is True
        assert reg.get("test") is None


class TestABTest:
    def test_compare(self, sample_data):
        X, y = sample_data
        result = ABTest.compare_models(
            RandomForestClassifier(n_estimators=10, random_state=42),
            LogisticRegression(max_iter=1000), X, y, n_bootstrap=100,
        )
        assert "model_a_mean" in result
        assert "p_value" in result
        assert result["winner"] in ("A", "B")
        assert isinstance(result["significant"], bool)


class TestDriftDetector:
    def test_no_drift(self):
        rng = np.random.RandomState(42)
        result = DriftDetector.detect(rng.normal(0, 1, 1000), rng.normal(0, 1, 1000))
        assert result["drift_detected"] is False

    def test_drift_detected(self):
        rng = np.random.RandomState(42)
        result = DriftDetector.detect(rng.normal(0, 1, 1000), rng.normal(3, 1, 1000))
        assert result["drift_detected"] is True
        assert result["severity"] == "high"


class TestExplainability:
    def test_permutation_importance(self, sample_data):
        X, y = sample_data
        model = RandomForestClassifier(n_estimators=10, random_state=42).fit(X, y)
        importance = Explainability.permutation_importance(model, X, y, n_repeats=3)
        assert len(importance) == X.shape[1]
        assert all(v >= 0 for v in importance.values())

    def test_feature_importance_from_model(self, sample_data):
        X, y = sample_data
        model = RandomForestClassifier(n_estimators=10, random_state=42).fit(X, y)
        importance = Explainability.feature_importance(model, X, y)
        assert len(importance) == X.shape[1]


class TestAutoML:
    def test_auto_select(self, sample_data):
        X, y = sample_data
        result = AutoML.auto_select(X, y, cv=3)
        assert "best_model" in result
        assert result["best_name"] in AutoML.MODELS
        assert len(result["all_results"]) > 0
