"""Comprehensive tests for the DataScience module."""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def sample_data():
    np.random.seed(42)
    X = np.random.randn(100, 5)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    return X, y


@pytest.fixture
def sample_df():
    np.random.seed(42)
    return pd.DataFrame({
        "a": np.random.randn(50), "b": np.random.randn(50),
        "c": np.random.choice(["x", "y", "z"], 50),
        "target": np.random.randint(0, 2, 50),
    })


# ── 1. Model Training ──────────────────────────────────────────────

class TestModelTraining:
    @pytest.mark.asyncio
    async def test_train_classifier(self, sample_data):
        from apex_os.datascience import ModelTrainer
        X, y = sample_data
        trainer = ModelTrainer(model_type="random_forest")
        model = await trainer.train(X, y)
        assert model is not None
        assert hasattr(model, "predict")

    @pytest.mark.asyncio
    async def test_train_with_validation_split(self, sample_data):
        from apex_os.datascience import ModelTrainer
        X, y = sample_data
        trainer = ModelTrainer(model_type="logistic_regression")
        result = await trainer.train(X, y, validation_split=0.2)
        assert "model" in result
        assert "metrics" in result

    @pytest.mark.asyncio
    async def test_train_invalid_data_raises(self):
        from apex_os.datascience import ModelTrainer
        trainer = ModelTrainer()
        with pytest.raises(ValueError):
            await trainer.train(np.array([]), np.array([]))

    @pytest.mark.asyncio
    async def test_train_unsupported_model_type(self, sample_data):
        from apex_os.datascience import ModelTrainer
        X, y = sample_data
        trainer = ModelTrainer(model_type="nonexistent_model")
        with pytest.raises(ValueError):
            await trainer.train(X, y)


# ── 2. Model Evaluation ───────────────────────────────────────────

class TestModelEvaluation:
    @pytest.mark.asyncio
    async def test_evaluate_returns_metrics(self, sample_data):
        from apex_os.datascience import ModelEvaluator
        X, y = sample_data
        evaluator = ModelEvaluator()
        metrics = await evaluator.evaluate(MagicMock(), X, y)
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics

    @pytest.mark.asyncio
    async def test_evaluate_binary_classification(self, sample_data):
        from apex_os.datascience import ModelEvaluator
        X, y = sample_data
        evaluator = ModelEvaluator()
        metrics = await evaluator.evaluate(MagicMock(), X, y, task="binary")
        assert 0.0 <= metrics["accuracy"] <= 1.0

    @pytest.mark.asyncio
    async def test_evaluate_regression(self):
        from apex_os.datascience import ModelEvaluator
        X = np.random.randn(80, 3)
        y = X @ np.array([1.5, -2.0, 0.5]) + np.random.randn(80) * 0.1
        evaluator = ModelEvaluator()
        metrics = await evaluator.evaluate(MagicMock(), X, y, task="regression")
        assert "mse" in metrics
        assert "r2" in metrics

    @pytest.mark.asyncio
    async def test_cross_validate(self, sample_data):
        from apex_os.datascience import ModelEvaluator
        X, y = sample_data
        evaluator = ModelEvaluator()
        scores = await evaluator.cross_validate(MagicMock(), X, y, cv=3)
        assert len(scores) == 3
        assert all(0.0 <= s <= 1.0 for s in scores)


# ── 3. Feature Engineering ─────────────────────────────────────────

class TestFeatureEngineering:
    @pytest.mark.asyncio
    async def test_create_features_from_df(self, sample_df):
        from apex_os.datascience import FeatureEngineer
        fe = FeatureEngineer()
        result = await fe.transform(sample_df, target_col="target")
        assert isinstance(result, pd.DataFrame)
        assert result.shape[0] == sample_df.shape[0]

    @pytest.mark.asyncio
    async def test_encode_categoricals(self, sample_df):
        from apex_os.datascience import FeatureEngineer
        fe = FeatureEngineer()
        result = await fe.encode_categoricals(sample_df)
        assert "c" not in result.columns
        assert any(c.startswith("c_") for c in result.columns)

    @pytest.mark.asyncio
    async def test_scale_features(self, sample_df):
        from apex_os.datascience import FeatureEngineer
        fe = FeatureEngineer()
        result = await fe.scale(sample_df[["a", "b"]])
        assert np.allclose(result.mean(), 0, atol=1e-7)
        assert np.allclose(result.std(), 1, atol=1e-7)

    @pytest.mark.asyncio
    async def test_handle_missing_values(self):
        from apex_os.datascience import FeatureEngineer
        df = pd.DataFrame({"a": [1, np.nan, 3], "b": [np.nan, 2, 3]})
        fe = FeatureEngineer()
        result = await fe.impute(df, strategy="mean")
        assert not result.isnull().any().any()

    @pytest.mark.asyncio
    async def test_select_features(self, sample_df):
        from apex_os.datascience import FeatureEngineer
        fe = FeatureEngineer()
        selected = await fe.select_k_best(sample_df.drop(columns=["target"]),
                                         sample_df["target"], k=2)
        assert selected.shape[1] == 2


# ── 4. Model Deployment ────────────────────────────────────────────

class TestModelDeployment:
    @pytest.mark.asyncio
    async def test_deploy_model(self):
        from apex_os.datascience import ModelDeployer
        deployer = ModelDeployer(backend="mock")
        deployment = await deployer.deploy(MagicMock(), name="test-model")
        assert deployment["status"] == "deployed"
        assert "endpoint" in deployment

    @pytest.mark.asyncio
    async def test_deploy_with_versioning(self):
        from apex_os.datascience import ModelDeployer
        deployer = ModelDeployer(backend="mock")
        d1 = await deployer.deploy(MagicMock(), name="m", version="1.0")
        d2 = await deployer.deploy(MagicMock(), name="m", version="2.0")
        assert d1["version"] != d2["version"]

    @pytest.mark.asyncio
    async def test_undeploy_model(self):
        from apex_os.datascience import ModelDeployer
        deployer = ModelDeployer(backend="mock")
        dep = await deployer.deploy(MagicMock(), name="to-remove")
        result = await deployer.undeploy(dep["id"])
        assert result is True

    @pytest.mark.asyncio
    async def test_deploy_invalid_backend_raises(self):
        from apex_os.datascience import ModelDeployer
        with pytest.raises(ValueError):
            ModelDeployer(backend="invalid_backend")


# ── 5. Model Monitoring ────────────────────────────────────────────

class TestModelMonitoring:
    @pytest.mark.asyncio
    async def test_log_prediction(self):
        from apex_os.datascience import ModelMonitor
        monitor = ModelMonitor()
        await monitor.log_prediction("model-1", input_data=[1, 2, 3],
                                     output=1, latency_ms=15.2)
        logs = await monitor.get_logs("model-1")
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_detect_drift(self):
        from apex_os.datascience import ModelMonitor
        monitor = ModelMonitor()
        baseline = np.random.randn(100, 3)
        current = np.random.randn(100, 3) + 2.0
        drift_score = await monitor.detect_drift(baseline, current)
        assert drift_score > 0.5

    @pytest.mark.asyncio
    async def test_performance_degradation_alert(self):
        from apex_os.datascience import ModelMonitor
        monitor = ModelMonitor(threshold=0.8)
        for acc in [0.95, 0.93, 0.88, 0.82, 0.75]:
            await monitor.record_metric("model-1", "accuracy", acc)
        alerts = await monitor.check_alerts("model-1")
        assert len(alerts) > 0

    @pytest.mark.asyncio
    async def test_get_model_health(self):
        from apex_os.datascience import ModelMonitor
        monitor = ModelMonitor()
        await monitor.record_metric("m1", "accuracy", 0.92)
        health = await monitor.get_health("m1")
        assert health["status"] in ("healthy", "degraded", "unhealthy")
