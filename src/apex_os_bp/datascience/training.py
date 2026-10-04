"""Model training with hyperparameter tuning."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import Model, ModelStatus


class BaseEstimator(ABC):
    """Minimal estimator interface."""

    @abstractmethod
    def fit(self, X: List[Dict[str, Any]], y: List[Any]) -> "BaseEstimator":
        ...

    @abstractmethod
    def predict(self, X: List[Dict[str, Any]]) -> List[Any]:
        ...

    def score(self, X: List[Dict[str, Any]], y: List[Any]) -> float:
        preds = self.predict(X)
        if not y:
            return 0.0
        correct = sum(1 for p, t in zip(preds, y) if p == t)
        return correct / len(y)


class LogisticRegressionStub(BaseEstimator):
    """Lightweight logistic-regression-like classifier for demonstration."""

    def __init__(self, lr: float = 0.1, epochs: int = 100, threshold: float = 0.5):
        self.lr = lr
        self.epochs = epochs
        self.threshold = threshold
        self.weights: Dict[str, float] = {}
        self.bias: float = 0.0
        self._fitted = False

    def _features(self, row: Dict[str, Any]) -> List[Tuple[str, float]]:
        return [(k, float(v)) for k, v in row.items() if isinstance(v, (int, float))]

    def fit(self, X: List[Dict[str, Any]], y: List[Any]) -> "LogisticRegressionStub":
        if not X:
            return self
        keys = set()
        for row in X:
            keys.update(k for k, _ in self._features(row))
        self.weights = {k: 0.0 for k in keys}
        self.bias = 0.0
        n = len(X)
        for _ in range(self.epochs):
            for row, target in zip(X, y):
                feats = dict(self._features(row))
                z = self.bias + sum(self.weights.get(k, 0.0) * v for k, v in feats.items())
                pred = 1.0 / (1.0 + pow(2.718281828, -max(-30.0, min(30.0, z))))
                err = float(target) - pred
                for k, v in feats.items():
                    self.weights[k] = self.weights.get(k, 0.0) + self.lr * err * v / n
                self.bias += self.lr * err / n
        self._fitted = True
        return self

    def predict(self, X: List[Dict[str, Any]]) -> List[Any]:
        preds: List[Any] = []
        for row in X:
            feats = dict(self._features(row))
            z = self.bias + sum(self.weights.get(k, 0.0) * v for k, v in feats.items())
            prob = 1.0 / (1.0 + pow(2.718281828, -max(-30.0, min(30.0, z))))
            preds.append(int(prob >= self.threshold))
        return preds


@dataclass
class TrainConfig:
    """Configuration for a training run."""

    estimator: BaseEstimator = field(default_factory=LogisticRegressionStub)
    test_size: float = 0.2
    random_seed: int = 42
    metrics: List[str] = field(default_factory=lambda: ["accuracy"])


class Trainer:
    """Train and evaluate models."""

    def __init__(self, config: Optional[TrainConfig] = None):
        self.config = config or TrainConfig()

    def _split(
        self, X: List[Dict[str, Any]], y: List[Any]
    ) -> Tuple[List[Dict[str, Any]], List[Any], List[Dict[str, Any]], List[Any]]:
        rng = random.Random(self.config.random_seed)
        indices = list(range(len(X)))
        rng.shuffle(indices)
        cut = int(len(indices) * (1 - self.config.test_size))
        train_idx, test_idx = indices[:cut], indices[cut:]
        X_train = [X[i] for i in train_idx]
        y_train = [y[i] for i in train_idx]
        X_test = [X[i] for i in test_idx]
        y_test = [y[i] for i in test_idx]
        return X_train, y_train, X_test, y_test

    def train(
        self,
        name: str,
        X: List[Dict[str, Any]],
        y: List[Any],
        feature_names: Optional[List[str]] = None,
    ) -> Model:
        X_train, y_train, X_test, y_test = self._split(X, y)
        est = self.config.estimator
        est.fit(X_train, y_train)
        acc = est.score(X_test, y_test)
        model = Model(
            name=name,
            model_type=type(est).__name__,
            status=ModelStatus.TRAINED,
            metrics={"accuracy": acc},
            params={
                "lr": getattr(est, "lr", None),
                "epochs": getattr(est, "epochs", None),
                "test_size": self.config.test_size,
            },
            feature_names=feature_names or [],
        )
        return model


class GridSearchTuner:
    """Grid-search hyperparameter tuning."""

    def __init__(self, param_grid: Dict[str, List[Any]], trainer: Optional[Trainer] = None):
        self.param_grid = param_grid
        self.trainer = trainer or Trainer()
        self.results: List[Dict[str, Any]] = []

    def _combinations(self) -> List[Dict[str, Any]]:
        keys = list(self.param_grid.keys())
        combos: List[Dict[str, Any]] = [{}]
        for key in keys:
            combos = [{**c, key: v} for c in combos for v in self.param_grid[key]]
        return combos

    def tune(
        self,
        name: str,
        X: List[Dict[str, Any]],
        y: List[Any],
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[Model, List[Dict[str, Any]]]:
        best_model: Optional[Model] = None
        best_score = -1.0
        self.results = []
        for combo in self._combinations():
            est = LogisticRegressionStub(**combo)
            cfg = TrainConfig(estimator=est)
            trainer = Trainer(cfg)
            model = trainer.train(f"{name}_trial", X, y, feature_names)
            score = model.metrics.get("accuracy", 0.0)
            self.results.append({"params": combo, "accuracy": score})
            if score > best_score:
                best_score = score
                best_model = model
        assert best_model is not None
        best_model.name = name
        return best_model, self.results
