"""Comprehensive tests for APEX-OS ML Platform."""

import math
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.ml.ab_testing import ABTest, ABTestConfig, ABTestManager, ABTestResult
from apex_os_bp.ml.feature_store import Feature, FeatureGroup, FeatureStore
from apex_os_bp.ml.monitoring import Alert, Metric, ModelMonitor, MonitoringRule
from apex_os_bp.ml.serving import ModelServer, Prediction, ServingConfig
from apex_os_bp.ml.training import ModelTrainer, TrainingConfig, TrainingResult


class TestModelTrainer(unittest.TestCase):
    """Tests for the ModelTrainer component."""

    def setUp(self):
        self.config = TrainingConfig(
            model_name="test_model",
            model_type="linear",
            learning_rate=0.1,
            epochs=200,
            batch_size=16,
            validation_split=0.2,
            random_seed=42,
        )
        self.trainer = ModelTrainer(self.config)

    def test_train_linear_model(self):
        """Test training a simple linear model."""
        X = [[1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0], [8.0], [9.0], [10.0]]
        y = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0]

        result = self.trainer.train(X, y, feature_names=["x"])

        self.assertIsInstance(result, TrainingResult)
        self.assertEqual(result.model_name, "test_model")
        self.assertEqual(result.model_type, "linear")
        self.assertEqual(len(result.weights), 1)
        self.assertGreater(result.epochs_run, 0)
        self.assertLess(result.training_loss, 10.0)
        self.assertIn("train_mse", result.metrics)
        self.assertIn("train_r2", result.metrics)

    def test_train_logistic_model(self):
        """Test training a logistic regression model."""
        config = TrainingConfig(
            model_name="logistic_model",
            model_type="logistic",
            learning_rate=0.5,
            epochs=100,
            random_seed=42,
        )
        trainer = ModelTrainer(config)

        X = [[0.0], [1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0], [8.0], [9.0]]
        y = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]

        result = trainer.train(X, y)

        self.assertEqual(result.model_type, "logistic")
        # Predictions should be between 0 and 1
        predictions = trainer.predict(result.model_id, [[0.0], [9.0]])
        for p in predictions:
            self.assertGreaterEqual(p, 0.0)
            self.assertLessEqual(p, 1.0)

    def test_predict_after_training(self):
        """Test making predictions after training."""
        X = [[1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0]]
        y = [3.0, 5.0, 7.0, 9.0]

        result = self.trainer.train(X, y)
        predictions = self.trainer.predict(result.model_id, [[5.0, 6.0]])

        self.assertEqual(len(predictions), 1)
        self.assertIsInstance(predictions[0], float)

    def test_invalid_model_type(self):
        """Test that invalid model type raises error."""
        with self.assertRaises(ValueError):
            TrainingConfig(model_name="bad", model_type="neural_network")

    def test_empty_training_data(self):
        """Test that empty training data raises error."""
        with self.assertRaises(ValueError):
            self.trainer.train([], [])

    def test_mismatched_data(self):
        """Test that mismatched X and y raises error."""
        with self.assertRaises(ValueError):
            self.trainer.train([[1.0], [2.0]], [1.0])

    def test_get_model(self):
        """Test retrieving a trained model."""
        X = [[1.0], [2.0], [3.0]]
        y = [1.0, 2.0, 3.0]
        result = self.trainer.train(X, y)

        model = self.trainer.get_model(result.model_id)
        self.assertEqual(model.model_id, result.model_id)

    def test_get_nonexistent_model(self):
        """Test that getting a nonexistent model raises error."""
        with self.assertRaises(KeyError):
            self.trainer.get_model("nonexistent_model_id")

    def test_list_models(self):
        """Test listing trained models."""
        X = [[1.0], [2.0], [3.0]]
        y = [1.0, 2.0, 3.0]
        result = self.trainer.train(X, y)

        models = self.trainer.list_models()
        self.assertIn(result.model_id, models)

    def test_training_result_to_dict(self):
        """Test TrainingResult serialization."""
        X = [[1.0], [2.0], [3.0]]
        y = [1.0, 2.0, 3.0]
        result = self.trainer.train(X, y)

        d = result.to_dict()
        self.assertIn("model_id", d)
        self.assertIn("weights", d)
        self.assertIn("metrics", d)
        self.assertIn("feature_importances", d)

    def test_feature_importances(self):
        """Test that feature importances are computed."""
        X = [[1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [4.0, 40.0]]
        y = [1.0, 2.0, 3.0, 4.0]
        result = self.trainer.train(X, y, feature_names=["a", "b"])

        self.assertIn("a", result.feature_importances)
        self.assertIn("b", result.feature_importances)
        # Importances should sum to ~1.0
        total = sum(result.feature_importances.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_early_stopping(self):
        """Test early stopping with patience."""
        config = TrainingConfig(
            model_name="early_stop",
            learning_rate=0.001,
            epochs=1000,
            early_stopping_patience=2,
            random_seed=42,
        )
        trainer = ModelTrainer(config)
        X = [[float(i)] for i in range(20)]
        y = [float(i) * 2 for i in range(20)]

        result = trainer.train(X, y)
        # Should stop before max epochs due to early stopping
        self.assertTrue(result.stopped_early or result.converged)

    def test_multifeature_training(self):
        """Test training with multiple features."""
        X = [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0], [3.0, 4.0, 5.0], [4.0, 5.0, 6.0]]
        y = [6.0, 9.0, 12.0, 15.0]
        result = self.trainer.train(X, y, feature_names=["a", "b", "c"])

        self.assertEqual(len(result.weights), 3)
        self.assertEqual(len(result.feature_importances), 3)


class TestModelServer(unittest.TestCase):
    """Tests for the ModelServer component."""

    def setUp(self):
        config = TrainingConfig(
            model_name="serve_model",
            learning_rate=0.1,
            epochs=50,
            random_seed=42,
        )
        self.trainer = ModelTrainer(config)
        X = [[1.0], [2.0], [3.0], [4.0], [5.0]]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        self.result = self.trainer.train(X, y)
        self.server = ModelServer(self.trainer)

    def test_deploy_model(self):
        """Test deploying a model."""
        serving_config = ServingConfig(
            model_id=self.result.model_id,
            model_name="serve_model",
        )
        self.server.deploy(serving_config)
        self.assertIn(self.result.model_id, self.server.list_deployed())

    def test_undeploy_model(self):
        """Test undeploying a model."""
        serving_config = ServingConfig(
            model_id=self.result.model_id,
            model_name="serve_model",
        )
        self.server.deploy(serving_config)
        self.server.undeploy(self.result.model_id)
        self.assertNotIn(self.result.model_id, self.server.list_deployed())

    def test_predict(self):
        """Test making a prediction."""
        serving_config = ServingConfig(
            model_id=self.result.model_id,
            model_name="serve_model",
        )
        self.server.deploy(serving_config)

        pred = self.server.predict(self.result.model_id, [3.0])
        self.assertIsInstance(pred, Prediction)
        self.assertEqual(pred.model_id, self.result.model_id)
        self.assertGreater(pred.latency_ms, 0)

    def test_predict_undeployed_model(self):
        """Test that predicting with undeployed model raises error."""
        with self.assertRaises(KeyError):
            self.server.predict("nonexistent_model", [1.0])

    def test_predict_batch(self):
        """Test batch prediction."""
        serving_config = ServingConfig(
            model_id=self.result.model_id,
            model_name="serve_model",
        )
        self.server.deploy(serving_config)

        predictions = self.server.predict_batch(
            self.result.model_id, [[1.0], [2.0], [3.0]]
        )
        self.assertEqual(len(predictions), 3)
        for p in predictions:
            self.assertIsInstance(p, Prediction)

    def test_caching(self):
        """Test prediction caching."""
        serving_config = ServingConfig(
            model_id=self.result.model_id,
            model_name="serve_model",
            enable_caching=True,
            cache_ttl_seconds=60.0,
        )
        self.server.deploy(serving_config)

        pred1 = self.server.predict(self.result.model_id, [3.0])
        pred2 = self.server.predict(self.result.model_id, [3.0])

        self.assertFalse(pred1.cached)
        self.assertTrue(pred2.cached)
        self.assertEqual(pred1.prediction, pred2.prediction)

    def test_clear_cache(self):
        """Test clearing the cache."""
        serving_config = ServingConfig(
            model_id=self.result.model_id,
            model_name="serve_model",
            enable_caching=True,
        )
        self.server.deploy(serving_config)

        self.server.predict(self.result.model_id, [3.0])
        self.server.clear_cache()

        stats = self.server.get_stats()
        self.assertEqual(stats["cache_size"], 0)

    def test_get_stats(self):
        """Test getting serving statistics."""
        serving_config = ServingConfig(
            model_id=self.result.model_id,
            model_name="serve_model",
        )
        self.server.deploy(serving_config)

        self.server.predict(self.result.model_id, [1.0])
        self.server.predict(self.result.model_id, [2.0])

        stats = self.server.get_stats()
        self.assertEqual(stats["total_requests"], 2)
        self.assertEqual(stats["total_errors"], 0)
        self.assertEqual(stats["deployed_models"], 1)

    def test_prediction_to_dict(self):
        """Test Prediction serialization."""
        serving_config = ServingConfig(
            model_id=self.result.model_id,
            model_name="serve_model",
        )
        self.server.deploy(serving_config)

        pred = self.server.predict(self.result.model_id, [3.0])
        d = pred.to_dict()
        self.assertIn("model_id", d)
        self.assertIn("prediction", d)
        self.assertIn("confidence", d)
        self.assertIn("latency_ms", d)

    def test_confidence_score(self):
        """Test that confidence is computed."""
        serving_config = ServingConfig(
            model_id=self.result.model_id,
            model_name="serve_model",
        )
        self.server.deploy(serving_config)

        pred = self.server.predict(self.result.model_id, [3.0])
        self.assertGreaterEqual(pred.confidence, 0.0)
        self.assertLessEqual(pred.confidence, 1.0)


class TestFeatureStore(unittest.TestCase):
    """Tests for the FeatureStore component."""

    def setUp(self):
        self.store = FeatureStore()

    def test_register_feature(self):
        """Test registering a feature."""
        feature = Feature(name="age", dtype="float", description="User age")
        self.store.register_feature(feature)

        retrieved = self.store.get_feature("age")
        self.assertEqual(retrieved.name, "age")
        self.assertEqual(retrieved.dtype, "float")

    def test_register_feature_group(self):
        """Test registering a feature group."""
        features = [
            Feature(name="age", dtype="float"),
            Feature(name="income", dtype="float"),
        ]
        group = FeatureGroup(name="user_features", features=features)
        self.store.register_feature_group(group)

        retrieved = self.store.get_feature_group("user_features")
        self.assertEqual(retrieved.name, "user_features")
        self.assertEqual(len(retrieved.features), 2)

    def test_put_get_online(self):
        """Test writing and reading from online store."""
        self.store.register_feature(Feature(name="age", dtype="float"))
        self.store.put_online("user_1", {"age": 25.0})

        result = self.store.get_online("user_1")
        self.assertEqual(result["age"], 25.0)

    def test_get_online_specific_features(self):
        """Test reading specific features from online store."""
        self.store.register_feature(Feature(name="age", dtype="float"))
        self.store.register_feature(Feature(name="income", dtype="float"))
        self.store.put_online("user_1", {"age": 25.0, "income": 50000.0})

        result = self.store.get_online("user_1", ["age"])
        self.assertEqual(result["age"], 25.0)
        self.assertNotIn("income", result)

    def test_put_get_offline(self):
        """Test writing and reading from offline store."""
        self.store.register_feature(Feature(name="age", dtype="float"))
        self.store.put_offline("user_1", {"age": 25.0})

        result = self.store.get_offline("user_1")
        self.assertEqual(result["age"], 25.0)

    def test_get_offline_batch(self):
        """Test batch reading from offline store."""
        self.store.register_feature(Feature(name="age", dtype="float"))
        self.store.put_offline("user_1", {"age": 25.0})
        self.store.put_offline("user_2", {"age": 30.0})

        result = self.store.get_offline_batch(["user_1", "user_2"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result["user_1"]["age"], 25.0)

    def test_delete_online(self):
        """Test deleting from online store."""
        self.store.register_feature(Feature(name="age", dtype="float"))
        self.store.put_online("user_1", {"age": 25.0})
        self.store.delete_online("user_1")

        result = self.store.get_online("user_1")
        self.assertEqual(result, {})

    def test_delete_offline(self):
        """Test deleting from offline store."""
        self.store.register_feature(Feature(name="age", dtype="float"))
        self.store.put_offline("user_1", {"age": 25.0})
        self.store.delete_offline("user_1")

        result = self.store.get_offline("user_1")
        self.assertEqual(result, {})

    def test_feature_validation(self):
        """Test feature value validation."""
        feature = Feature(name="age", dtype="float")
        self.assertTrue(feature.validate_value(25.0))
        self.assertTrue(feature.validate_value(25))
        self.assertFalse(feature.validate_value("25"))

        int_feature = Feature(name="count", dtype="int")
        self.assertTrue(int_feature.validate_value(5))
        self.assertFalse(int_feature.validate_value(5.0))
        self.assertFalse(int_feature.validate_value(True))

        str_feature = Feature(name="name", dtype="string")
        self.assertTrue(str_feature.validate_value("hello"))
        self.assertFalse(str_feature.validate_value(123))

        bool_feature = Feature(name="active", dtype="bool")
        self.assertTrue(bool_feature.validate_value(True))
        self.assertFalse(bool_feature.validate_value(1))

    def test_feature_group_validation(self):
        """Test feature group record validation."""
        features = [
            Feature(name="age", dtype="float"),
            Feature(name="name", dtype="string"),
        ]
        group = FeatureGroup(name="test_group", features=features)

        valid, errors = group.validate_record({"age": 25.0, "name": "Alice"})
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

        valid, errors = group.validate_record({"age": "not_a_number", "name": "Alice"})
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)

    def test_get_feature_vector(self):
        """Test getting a feature vector for model input."""
        self.store.register_feature(Feature(name="age", dtype="float", default_value=0.0))
        self.store.register_feature(Feature(name="income", dtype="float", default_value=0.0))
        self.store.put_online("user_1", {"age": 25.0})

        vector = self.store.get_feature_vector("user_1", ["age", "income"])
        self.assertEqual(len(vector), 2)
        self.assertEqual(vector[0], 25.0)
        self.assertEqual(vector[1], 0.0)  # default value

    def test_compute_feature_stats(self):
        """Test computing feature statistics."""
        self.store.register_feature(Feature(name="age", dtype="float"))
        self.store.put_offline("user_1", {"age": 20.0})
        self.store.put_offline("user_2", {"age": 30.0})
        self.store.put_offline("user_3", {"age": 40.0})

        stats = self.store.compute_feature_stats("age")
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["mean"], 30.0)
        self.assertEqual(stats["min"], 20.0)
        self.assertEqual(stats["max"], 40.0)

    def test_ttl_expiration(self):
        """Test TTL-based feature expiration."""
        feature = Feature(name="temp", dtype="float", ttl_seconds=0.01)
        self.store.register_feature(feature)
        self.store.put_online("user_1", {"temp": 42.0})

        # Should be available immediately
        result = self.store.get_online_with_ttl("user_1", ["temp"])
        self.assertIn("temp", result)

        # Wait for expiration
        time.sleep(0.02)
        result = self.store.get_online_with_ttl("user_1", ["temp"])
        self.assertNotIn("temp", result)

    def test_clear_store(self):
        """Test clearing all data."""
        self.store.register_feature(Feature(name="age", dtype="float"))
        self.store.put_online("user_1", {"age": 25.0})
        self.store.put_offline("user_1", {"age": 25.0})

        self.store.clear()
        self.assertEqual(self.store.get_online("user_1"), {})
        self.assertEqual(self.store.get_offline("user_1"), {})

    def test_list_features(self):
        """Test listing registered features."""
        self.store.register_feature(Feature(name="age", dtype="float"))
        self.store.register_feature(Feature(name="income", dtype="float"))

        features = self.store.list_features()
        self.assertIn("age", features)
        self.assertIn("income", features)

    def test_unregistered_feature_raises(self):
        """Test that using unregistered feature raises error."""
        with self.assertRaises(KeyError):
            self.store.put_online("user_1", {"unknown": 42.0})


class TestModelMonitor(unittest.TestCase):
    """Tests for the ModelMonitor component."""

    def setUp(self):
        self.monitor = ModelMonitor()

    def test_record_metric(self):
        """Test recording a metric."""
        self.monitor.record_metric("accuracy", 0.95)
        metrics = self.monitor.get_metrics("accuracy")
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].value, 0.95)

    def test_record_prediction(self):
        """Test recording a prediction event."""
        self.monitor.record_prediction("model_1", 0.8, actual=1.0, latency_ms=5.0)

        pred_metrics = self.monitor.get_metrics("prediction_value")
        self.assertEqual(len(pred_metrics), 1)

        error_metrics = self.monitor.get_metrics("prediction_error")
        self.assertEqual(len(error_metrics), 1)
        self.assertAlmostEqual(error_metrics[0].value, 0.2)

        latency_metrics = self.monitor.get_metrics("prediction_latency_ms")
        self.assertEqual(len(latency_metrics), 1)

    def test_add_rule(self):
        """Test adding a monitoring rule."""
        rule = MonitoringRule(
            metric_name="accuracy",
            threshold=0.8,
            comparison="lt",
            severity="warning",
        )
        self.monitor.add_rule(rule)

        # This should trigger the alert
        self.monitor.record_metric("accuracy", 0.7)
        alerts = self.monitor.get_alerts()
        self.assertGreater(len(alerts), 0)

    def test_remove_rule(self):
        """Test removing a monitoring rule."""
        rule = MonitoringRule(
            metric_name="accuracy",
            threshold=0.8,
            comparison="lt",
        )
        self.monitor.add_rule(rule)
        self.monitor.remove_rule("accuracy")

        self.monitor.record_metric("accuracy", 0.5)
        alerts = self.monitor.get_alerts()
        self.assertEqual(len(alerts), 0)

    def test_get_metric_stats(self):
        """Test getting metric statistics."""
        for i in range(10):
            self.monitor.record_metric("latency", float(i))

        stats = self.monitor.get_metric_stats("latency")
        self.assertEqual(stats["count"], 10)
        self.assertEqual(stats["min"], 0.0)
        self.assertEqual(stats["max"], 9.0)
        self.assertIn("mean", stats)
        self.assertIn("p95", stats)

    def test_get_alerts_filtered(self):
        """Test filtering alerts."""
        rule = MonitoringRule(
            metric_name="error_rate",
            threshold=0.5,
            comparison="gt",
            severity="critical",
        )
        self.monitor.add_rule(rule)
        self.monitor.record_metric("error_rate", 0.8)

        critical_alerts = self.monitor.get_alerts(severity="critical")
        self.assertGreater(len(critical_alerts), 0)

        warning_alerts = self.monitor.get_alerts(severity="warning")
        self.assertEqual(len(warning_alerts), 0)

    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        rule = MonitoringRule(
            metric_name="error_rate",
            threshold=0.5,
            comparison="gt",
        )
        self.monitor.add_rule(rule)
        self.monitor.record_metric("error_rate", 0.8)

        alerts = self.monitor.get_alerts()
        alert_id = alerts[0].alert_id

        result = self.monitor.acknowledge_alert(alert_id)
        self.assertTrue(result)

        # Check acknowledged filter
        unack = self.monitor.get_alerts(acknowledged=False)
        ack = self.monitor.get_alerts(acknowledged=True)
        self.assertEqual(len(unack), 0)
        self.assertEqual(len(ack), 1)

    def test_detect_drift(self):
        """Test data drift detection."""
        now = time.time()
        # Reference window: old data with mean ~50
        for i in range(100):
            self.monitor.record_metric(
                "score", 50.0 + (i % 10) - 5, labels={"window": "ref"}
            )

        # Current window: shifted data with mean ~70
        for i in range(100):
            self.monitor.record_metric(
                "score", 70.0 + (i % 10) - 5, labels={"window": "cur"}
            )

        # Manually set timestamps for testing
        ref_start = now - 200
        ref_end = now - 100
        cur_start = now - 50
        cur_end = now

        # Re-record with proper timestamps
        self.monitor.clear()
        for i in range(100):
            m = Metric(name="score", value=50.0 + (i % 10) - 5, timestamp=ref_start + i)
            self.monitor._metrics.setdefault("score", []).append(m)
        for i in range(100):
            m = Metric(name="score", value=70.0 + (i % 10) - 5, timestamp=cur_start + i)
            self.monitor._metrics.setdefault("score", []).append(m)

        result = self.monitor.detect_drift(
            "score",
            (ref_start, ref_end),
            (cur_start, cur_end),
            threshold_std=2.0,
        )

        self.assertTrue(result["drift_detected"])
        self.assertGreater(abs(result["z_score"]), 2.0)

    def test_get_model_health(self):
        """Test getting model health summary."""
        self.monitor.record_prediction("model_1", 0.9, actual=1.0, latency_ms=10.0)
        self.monitor.record_prediction("model_1", 0.8, actual=1.0, latency_ms=15.0)

        health = self.monitor.get_model_health("model_1")
        self.assertEqual(health["model_id"], "model_1")
        self.assertEqual(health["total_predictions"], 2)
        self.assertEqual(health["status"], "healthy")

    def test_clear_monitor(self):
        """Test clearing all monitoring data."""
        self.monitor.record_metric("accuracy", 0.9)
        self.monitor.clear()

        metrics = self.monitor.get_metrics("accuracy")
        self.assertEqual(len(metrics), 0)

    def test_metric_to_dict(self):
        """Test Metric serialization."""
        metric = Metric(name="test", value=1.0, timestamp=123.0, labels={"a": "b"})
        d = metric.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["value"], 1.0)
        self.assertEqual(d["labels"]["a"], "b")

    def test_alert_to_dict(self):
        """Test Alert serialization."""
        alert = Alert(
            alert_id="a1",
            metric_name="accuracy",
            severity="warning",
            message="Test alert",
            threshold=0.8,
            observed_value=0.7,
            timestamp=123.0,
        )
        d = alert.to_dict()
        self.assertEqual(d["alert_id"], "a1")
        self.assertEqual(d["severity"], "warning")


class TestABTesting(unittest.TestCase):
    """Tests for the A/B testing component."""

    def setUp(self):
        self.config = ABTestConfig(
            test_name="test_ab",
            control_model_id="model_a",
            treatment_model_id="model_b",
            traffic_split=0.5,
            confidence_level=0.95,
            min_sample_size=10,
            random_seed=42,
        )

    def test_assign_variant(self):
        """Test variant assignment."""
        test = ABTest(self.config)
        variant = test.assign_variant("user_1")
        self.assertIn(variant, ["control", "treatment"])

    def test_assign_variant_deterministic(self):
        """Test that variant assignment is deterministic."""
        test = ABTest(self.config)
        v1 = test.assign_variant("user_1")
        v2 = test.assign_variant("user_1")
        self.assertEqual(v1, v2)

    def test_record_outcome(self):
        """Test recording outcomes."""
        test = ABTest(self.config)
        test.record_outcome("control", 0.8)
        test.record_outcome("treatment", 0.9)

        counts = test.get_variant_counts()
        self.assertEqual(counts["control"], 1)
        self.assertEqual(counts["treatment"], 1)

    def test_record_outcome_with_latency(self):
        """Test recording outcomes with latency."""
        test = ABTest(self.config)
        test.record_outcome("control", 0.8, latency_ms=10.0)
        test.record_outcome("treatment", 0.9, latency_ms=15.0)

        counts = test.get_variant_counts()
        self.assertEqual(counts["control"], 1)

    def test_invalid_variant(self):
        """Test that invalid variant raises error."""
        test = ABTest(self.config)
        with self.assertRaises(ValueError):
            test.record_outcome("invalid", 0.5)

    def test_get_result(self):
        """Test getting A/B test results."""
        test = ABTest(self.config)
        # Control: mean ~0.7
        for i in range(50):
            test.record_outcome("control", 0.7 + (i % 5) * 0.01)
        # Treatment: mean ~0.9
        for i in range(50):
            test.record_outcome("treatment", 0.9 + (i % 5) * 0.01)

        result = test.get_result()
        self.assertIsInstance(result, ABTestResult)
        self.assertEqual(result.control_size, 50)
        self.assertEqual(result.treatment_size, 50)
        self.assertGreater(result.difference, 0)
        self.assertIn(result.winner, ["control", "treatment", "inconclusive"])

    def test_result_to_dict(self):
        """Test ABTestResult serialization."""
        test = ABTest(self.config)
        for i in range(20):
            test.record_outcome("control", 0.7)
            test.record_outcome("treatment", 0.9)

        result = test.get_result()
        d = result.to_dict()
        self.assertIn("test_name", d)
        self.assertIn("control_mean", d)
        self.assertIn("treatment_mean", d)
        self.assertIn("p_value", d)
        self.assertIn("winner", d)

    def test_should_stop_insufficient_samples(self):
        """Test that test doesn't stop with insufficient samples."""
        test = ABTest(self.config)
        test.record_outcome("control", 0.7)
        test.record_outcome("treatment", 0.9)

        should_stop, reason = test.should_stop()
        self.assertFalse(should_stop)
        self.assertEqual(reason, "insufficient_samples")

    def test_should_stop_max_samples(self):
        """Test that test stops at max samples."""
        config = ABTestConfig(
            test_name="max_test",
            control_model_id="a",
            treatment_model_id="b",
            min_sample_size=5,
            max_sample_size=10,
        )
        test = ABTest(config)
        for i in range(10):
            test.record_outcome("control", 0.7)
            test.record_outcome("treatment", 0.9)

        should_stop, reason = test.should_stop()
        self.assertTrue(should_stop)
        self.assertEqual(reason, "max_samples_reached")

    def test_stop_test(self):
        """Test stopping a test."""
        test = ABTest(self.config)
        test.stop()

        with self.assertRaises(RuntimeError):
            test.record_outcome("control", 0.5)

    def test_invalid_traffic_split(self):
        """Test that invalid traffic split raises error."""
        with self.assertRaises(ValueError):
            ABTestConfig(
                test_name="bad",
                control_model_id="a",
                treatment_model_id="b",
                traffic_split=1.5,
            )

    def test_invalid_confidence_level(self):
        """Test that invalid confidence level raises error."""
        with self.assertRaises(ValueError):
            ABTestConfig(
                test_name="bad",
                control_model_id="a",
                treatment_model_id="b",
                confidence_level=1.5,
            )


class TestABTestManager(unittest.TestCase):
    """Tests for the ABTestManager component."""

    def setUp(self):
        self.manager = ABTestManager()

    def test_create_test(self):
        """Test creating a test."""
        config = ABTestConfig(
            test_name="managed_test",
            control_model_id="a",
            treatment_model_id="b",
        )
        test = self.manager.create_test(config)
        self.assertIsInstance(test, ABTest)
        self.assertIn("managed_test", self.manager.list_tests())

    def test_create_duplicate_test(self):
        """Test that creating duplicate test raises error."""
        config = ABTestConfig(
            test_name="dup_test",
            control_model_id="a",
            treatment_model_id="b",
        )
        self.manager.create_test(config)
        with self.assertRaises(ValueError):
            self.manager.create_test(config)

    def test_get_test(self):
        """Test getting a test by name."""
        config = ABTestConfig(
            test_name="get_test",
            control_model_id="a",
            treatment_model_id="b",
        )
        self.manager.create_test(config)

        test = self.manager.get_test("get_test")
        self.assertIsInstance(test, ABTest)

    def test_get_nonexistent_test(self):
        """Test that getting nonexistent test raises error."""
        with self.assertRaises(KeyError):
            self.manager.get_test("nonexistent")

    def test_end_test(self):
        """Test ending a test."""
        config = ABTestConfig(
            test_name="end_test",
            control_model_id="a",
            treatment_model_id="b",
        )
        test = self.manager.create_test(config)
        for i in range(20):
            test.record_outcome("control", 0.7)
            test.record_outcome("treatment", 0.9)

        result = self.manager.end_test("end_test")
        self.assertIsInstance(result, ABTestResult)

    def test_remove_test(self):
        """Test removing a test."""
        config = ABTestConfig(
            test_name="remove_test",
            control_model_id="a",
            treatment_model_id="b",
        )
        self.manager.create_test(config)
        self.manager.remove_test("remove_test")

        self.assertNotIn("remove_test", self.manager.list_tests())


class TestIntegration(unittest.TestCase):
    """Integration tests across all ML components."""

    def test_full_ml_pipeline(self):
        """Test a complete ML pipeline from training to serving."""
        # 1. Train a model
        config = TrainingConfig(
            model_name="pipeline_model",
            learning_rate=0.1,
            epochs=50,
            random_seed=42,
        )
        trainer = ModelTrainer(config)
        X = [[float(i)] for i in range(1, 21)]
        y = [float(i) * 2 for i in range(1, 21)]
        result = trainer.train(X, y, feature_names=["x"])

        # 2. Deploy the model
        server = ModelServer(trainer)
        serving_config = ServingConfig(
            model_id=result.model_id,
            model_name="pipeline_model",
        )
        server.deploy(serving_config)

        # 3. Set up feature store
        store = FeatureStore()
        store.register_feature(Feature(name="x", dtype="float"))
        store.put_online("entity_1", {"x": 10.0})

        # 4. Get feature vector and predict
        features = store.get_feature_vector("entity_1", ["x"])
        pred = server.predict(result.model_id, features)

        self.assertIsInstance(pred, Prediction)
        self.assertGreater(pred.prediction, 0)

        # 5. Monitor the prediction
        monitor = ModelMonitor()
        monitor.record_prediction(
            result.model_id, pred.prediction, actual=20.0, latency_ms=pred.latency_ms
        )

        health = monitor.get_model_health(result.model_id)
        self.assertEqual(health["total_predictions"], 1)

    def test_ab_test_with_trained_models(self):
        """Test A/B testing with two trained models."""
        # Train two models
        config_a = TrainingConfig(model_name="model_a", learning_rate=0.1, epochs=30)
        config_b = TrainingConfig(model_name="model_b", learning_rate=0.2, epochs=30)
        trainer_a = ModelTrainer(config_a)
        trainer_b = ModelTrainer(config_b)

        X = [[float(i)] for i in range(1, 11)]
        y = [float(i) * 2 for i in range(1, 11)]

        result_a = trainer_a.train(X, y)
        result_b = trainer_b.train(X, y)

        # Create A/B test
        ab_config = ABTestConfig(
            test_name="model_comparison",
            control_model_id=result_a.model_id,
            treatment_model_id=result_b.model_id,
            min_sample_size=5,
        )
        test = ABTest(ab_config)

        # Simulate traffic
        for i in range(20):
            variant = test.assign_variant(f"user_{i}")
            if variant == "control":
                pred = trainer_a.predict(result_a.model_id, [[float(i)]])[0]
                test.record_outcome("control", pred)
            else:
                pred = trainer_b.predict(result_b.model_id, [[float(i)]])[0]
                test.record_outcome("treatment", pred)

        result = test.get_result()
        self.assertIsInstance(result, ABTestResult)
        self.assertGreater(result.control_size, 0)
        self.assertGreater(result.treatment_size, 0)


if __name__ == "__main__":
    unittest.main()
