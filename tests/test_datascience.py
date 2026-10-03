"""Tests for the Data Science core module."""

from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.datascience.features import (
    FeaturePipeline,
    OneHotEncoder,
    StandardScaler,
)
from apex_os_bp.datascience.inference import (
    BatchPredictor,
    ModelServer,
    ThresholdPredictor,
)
from apex_os_bp.datascience.models import (
    Dataset,
    Experiment,
    Feature,
    Model,
    ModelStatus,
)
from apex_os_bp.datascience.training import (
    GridSearchTuner,
    LogisticRegressionStub,
    TrainConfig,
    Trainer,
)


def _sample_data(n: int = 100) -> tuple:
    """Generate simple linearly-separable data."""
    X = []
    y = []
    for i in range(n):
        a = float(i % 10)
        b = float((i * 3) % 7)
        X.append({"a": a, "b": b})
        y.append(1 if a + b > 8 else 0)
    return X, y


class TestDataset(unittest.TestCase):
    def test_fingerprint_deterministic(self):
        d1 = Dataset(name="sales", version="1.0", rows=100, columns=["a", "b"])
        d2 = Dataset(name="sales", version="1.0", rows=100, columns=["a", "b"])
        self.assertEqual(d1.fingerprint, d2.fingerprint)

    def test_fingerprint_changes_with_data(self):
        d1 = Dataset(name="sales", version="1.0", rows=100, columns=["a", "b"])
        d2 = Dataset(name="sales", version="1.0", rows=200, columns=["a", "b"])
        self.assertNotEqual(d1.fingerprint, d2.fingerprint)

    def test_summary(self):
        d = Dataset(name="test", rows=50, columns=["x", "y", "z"])
        s = d.summary()
        self.assertEqual(s["name"], "test")
        self.assertEqual(s["rows"], 50)
        self.assertEqual(s["columns"], 3)
        self.assertIn("fingerprint", s)


class TestFeature(unittest.TestCase):
    def test_validate_int(self):
        f = Feature(name="age", dtype="int")
        self.assertTrue(f.validate_value(42))
        self.assertFalse(f.validate_value("abc"))
        self.assertFalse(f.validate_value(None))

    def test_validate_nullable(self):
        f = Feature(name="score", dtype="float", nullable=True)
        self.assertTrue(f.validate_value(None))
        self.assertTrue(f.validate_value(3.14))

    def test_validate_str(self):
        f = Feature(name="label", dtype="str")
        self.assertTrue(f.validate_value("hello"))
        self.assertFalse(f.validate_value(123))


class TestModel(unittest.TestCase):
    def test_to_manifest(self):
        m = Model(
            name="clf",
            model_type="LogisticRegressionStub",
            metrics={"accuracy": 0.95},
            params={"lr": 0.1},
        )
        manifest = m.to_manifest()
        self.assertEqual(manifest["name"], "clf")
        self.assertEqual(manifest["status"], "draft")
        self.assertEqual(manifest["metrics"]["accuracy"], 0.95)

    def test_save_manifest(self):
        import tempfile

        m = Model(name="clf", metrics={"accuracy": 0.9})
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "manifest.json")
            m.save_manifest(path)
            self.assertTrue(os.path.exists(path))


class TestExperiment(unittest.TestCase):
    def test_add_and_best_model(self):
        exp = Experiment(name="exp1")
        m1 = Model(name="m1", metrics={"accuracy": 0.7})
        m2 = Model(name="m2", metrics={"accuracy": 0.9})
        exp.add_model(m1)
        exp.add_model(m2)
        self.assertEqual(len(exp.models), 2)
        self.assertEqual(exp.best_model().name, "m2")

    def test_best_model_empty(self):
        exp = Experiment(name="exp2")
        self.assertIsNone(exp.best_model())

    def test_summary(self):
        exp = Experiment(name="exp3", features=[Feature(name="f1")])
        exp.add_model(Model(name="m", metrics={"accuracy": 0.8}))
        s = exp.summary()
        self.assertEqual(s["n_features"], 1)
        self.assertEqual(s["n_models"], 1)
        self.assertEqual(s["best_model"], "m")


class TestStandardScaler(unittest.TestCase):
    def test_fit_transform(self):
        rows = [{"x": 1.0}, {"x": 2.0}, {"x": 3.0}]
        scaler = StandardScaler("x")
        out = scaler.fit_transform(rows)
        mean = sum(r["x"] for r in out) / len(out)
        self.assertAlmostEqual(mean, 0.0, places=5)

    def test_transform_new_value(self):
        rows = [{"x": 10.0}, {"x": 20.0}]
        scaler = StandardScaler("x")
        scaler.fit(rows)
        result = scaler.transform({"x": 15.0})
        self.assertAlmostEqual(result["x"], 0.0, places=5)


class TestOneHotEncoder(unittest.TestCase):
    def test_fit_transform(self):
        rows = [{"color": "red"}, {"color": "blue"}, {"color": "red"}]
        enc = OneHotEncoder("color")
        out = enc.fit_transform(rows)
        self.assertIn("color_red", out[0])
        self.assertEqual(out[0]["color_red"], 1.0)
        self.assertEqual(out[1]["color_blue"], 1.0)

    def test_unseen_category(self):
        rows = [{"color": "red"}]
        enc = OneHotEncoder("color")
        enc.fit(rows)
        out = enc.transform({"color": "green"})
        self.assertEqual(out["color_red"], 0.0)


class TestFeaturePipeline(unittest.TestCase):
    def test_pipeline_fit_transform(self):
        rows = [
            {"num": 1.0, "cat": "a"},
            {"num": 2.0, "cat": "b"},
            {"num": 3.0, "cat": "a"},
        ]
        pipe = FeaturePipeline()
        pipe.add(StandardScaler("num")).add(OneHotEncoder("cat"))
        out = pipe.fit_transform(rows)
        self.assertEqual(len(out), 3)
        self.assertIn("num", out[0])
        self.assertIn("cat_a", out[0])

    def test_feature_names(self):
        pipe = FeaturePipeline()
        pipe.add(StandardScaler("num")).add(OneHotEncoder("cat"))
        pipe.fit([{"num": 1.0, "cat": "x"}])
        names = pipe.feature_names()
        self.assertIn("num", names)
        self.assertIn("cat_x", names)


class TestLogisticRegressionStub(unittest.TestCase):
    def test_fit_predict(self):
        X, y = _sample_data(50)
        clf = LogisticRegressionStub(lr=0.5, epochs=200)
        clf.fit(X, y)
        preds = clf.predict(X[:5])
        self.assertEqual(len(preds), 5)
        self.assertTrue(all(p in (0, 1) for p in preds))

    def test_score(self):
        X, y = _sample_data(50)
        clf = LogisticRegressionStub(lr=0.5, epochs=200)
        clf.fit(X, y)
        acc = clf.score(X, y)
        self.assertGreater(acc, 0.5)


class TestTrainer(unittest.TestCase):
    def test_train_returns_model(self):
        X, y = _sample_data(80)
        trainer = Trainer()
        model = trainer.train("test_model", X, y, feature_names=["a", "b"])
        self.assertEqual(model.name, "test_model")
        self.assertEqual(model.status, ModelStatus.TRAINED)
        self.assertIn("accuracy", model.metrics)
        self.assertGreaterEqual(model.metrics["accuracy"], 0.0)
        self.assertLessEqual(model.metrics["accuracy"], 1.0)

    def test_train_config(self):
        X, y = _sample_data(40)
        cfg = TrainConfig(estimator=LogisticRegressionStub(lr=0.2, epochs=50))
        trainer = Trainer(cfg)
        model = trainer.train("cfg_model", X, y)
        self.assertEqual(model.params["lr"], 0.2)


class TestGridSearchTuner(unittest.TestCase):
    def test_tune_returns_best(self):
        X, y = _sample_data(60)
        grid = {"lr": [0.1, 0.5], "epochs": [50, 100]}
        tuner = GridSearchTuner(grid)
        best, results = tuner.tune("tuned", X, y)
        self.assertEqual(len(results), 4)
        self.assertEqual(best.name, "tuned")
        self.assertIn("accuracy", best.metrics)

    def test_results_recorded(self):
        X, y = _sample_data(40)
        grid = {"lr": [0.1], "epochs": [10]}
        tuner = GridSearchTuner(grid)
        _, results = tuner.tune("t", X, y)
        self.assertEqual(len(results), 1)
        self.assertIn("params", results[0])


class TestThresholdPredictor(unittest.TestCase):
    def test_predict(self):
        pred = ThresholdPredictor(weights={"a": 1.0, "b": 1.0}, bias=-5.0)
        self.assertEqual(pred.predict({"a": 3.0, "b": 3.0}), 1)
        self.assertEqual(pred.predict({"a": 1.0, "b": 1.0}), 0)

    def test_predict_batch(self):
        pred = ThresholdPredictor(weights={"a": 1.0}, bias=0.0)
        rows = [{"a": 1.0}, {"a": -1.0}]
        out = pred.predict_batch(rows)
        self.assertEqual(len(out), 2)


class TestModelServer(unittest.TestCase):
    def test_predict(self):
        model = Model(name="srv", version="1.0", status=ModelStatus.DEPLOYED)
        pred = ThresholdPredictor(weights={"a": 1.0}, bias=0.0)
        server = ModelServer(model, pred)
        result = server.predict({"a": 1.0})
        self.assertEqual(result.value, 1)
        self.assertEqual(result.model_id, model.id)
        self.assertGreaterEqual(result.latency_ms, 0.0)

    def test_request_count(self):
        model = Model(name="srv")
        pred = ThresholdPredictor(weights={"a": 1.0}, bias=0.0)
        server = ModelServer(model, pred)
        server.predict({"a": 1.0})
        server.predict({"a": 2.0})
        self.assertEqual(server.request_count, 2)

    def test_health(self):
        model = Model(name="srv", status=ModelStatus.DEPLOYED)
        pred = ThresholdPredictor(weights={}, bias=0.0)
        server = ModelServer(model, pred)
        h = server.health()
        self.assertEqual(h["model_name"], "srv")
        self.assertEqual(h["status"], "deployed")


class TestBatchPredictor(unittest.TestCase):
    def test_predict(self):
        model = Model(name="batch", version="1.0")
        pred = ThresholdPredictor(weights={"a": 1.0}, bias=0.0)
        server = ModelServer(model, pred)
        batch = BatchPredictor(server, batch_size=4)
        rows = [{"a": float(i)} for i in range(10)]
        result = batch.predict(rows)
        self.assertEqual(len(result.predictions), 10)
        self.assertEqual(len(result.latencies_ms), 10)
        self.assertGreaterEqual(result.total_latency_ms, 0.0)

    def test_predict_stream(self):
        model = Model(name="stream")
        pred = ThresholdPredictor(weights={"a": 1.0}, bias=0.0)
        server = ModelServer(model, pred)
        batch = BatchPredictor(server)
        rows = [{"a": 1.0}, {"a": 2.0}]
        results = list(batch.predict_stream(rows))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], 1)


if __name__ == "__main__":
    unittest.main()
