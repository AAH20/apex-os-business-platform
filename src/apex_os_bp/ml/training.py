"""Model training component for APEX-OS ML Platform."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class TrainingConfig:
    """Configuration for model training."""

    model_name: str
    model_type: str = "linear"  # linear, logistic, decision_tree
    learning_rate: float = 0.01
    epochs: int = 100
    batch_size: int = 32
    validation_split: float = 0.2
    random_seed: int = 42
    early_stopping_patience: int = 10
    l2_regularization: float = 0.001
    verbose: bool = False

    def __post_init__(self):
        if self.model_type not in {"linear", "logistic", "decision_tree"}:
            raise ValueError(
                f"Unsupported model type: {self.model_type}. "
                f"Supported: linear, logistic, decision_tree"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_type": self.model_type,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "validation_split": self.validation_split,
            "random_seed": self.random_seed,
            "early_stopping_patience": self.early_stopping_patience,
            "l2_regularization": self.l2_regularization,
            "verbose": self.verbose,
        }


@dataclass
class TrainingResult:
    """Result of a model training run."""

    model_id: str
    model_name: str
    model_type: str
    weights: List[float]
    bias: float
    training_loss: float
    validation_loss: float
    epochs_run: int
    training_time_seconds: float
    metrics: Dict[str, float] = field(default_factory=dict)
    feature_importances: Dict[str, float] = field(default_factory=dict)
    converged: bool = False
    stopped_early: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "weights": self.weights,
            "bias": self.bias,
            "training_loss": self.training_loss,
            "validation_loss": self.validation_loss,
            "epochs_run": self.epochs_run,
            "training_time_seconds": self.training_time_seconds,
            "metrics": self.metrics,
            "feature_importances": self.feature_importances,
            "converged": self.converged,
            "stopped_early": self.stopped_early,
        }


class ModelTrainer:
    """Trains ML models with support for linear, logistic, and decision tree models."""

    SUPPORTED_MODEL_TYPES = {"linear", "logistic", "decision_tree"}

    def __init__(self, config: TrainingConfig):
        if config.model_type not in self.SUPPORTED_MODEL_TYPES:
            raise ValueError(
                f"Unsupported model type: {config.model_type}. "
                f"Supported: {self.SUPPORTED_MODEL_TYPES}"
            )
        self.config = config
        self._models: Dict[str, TrainingResult] = {}
        self._rng = random.Random(config.random_seed)

    def train(
        self,
        X: List[List[float]],
        y: List[float],
        feature_names: Optional[List[str]] = None,
    ) -> TrainingResult:
        """Train a model on the given data.

        Args:
            X: Feature matrix (n_samples x n_features).
            y: Target vector (n_samples,).
            feature_names: Optional names for features.

        Returns:
            TrainingResult with trained model parameters and metrics.
        """
        if not X or not y:
            raise ValueError("Training data must not be empty")
        if len(X) != len(y):
            raise ValueError("X and y must have the same number of samples")
        if len(X[0]) == 0:
            raise ValueError("Features must have at least one dimension")

        n_features = len(X[0])
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(n_features)]
        if len(feature_names) != n_features:
            raise ValueError("feature_names length must match number of features")

        start_time = time.time()

        # Split data
        indices = list(range(len(X)))
        self._rng.shuffle(indices)
        split_idx = int(len(indices) * (1 - self.config.validation_split))
        train_idx = indices[:split_idx]
        val_idx = indices[split_idx:]

        X_train = [X[i] for i in train_idx]
        y_train = [y[i] for i in train_idx]
        X_val = [X[i] for i in val_idx]
        y_val = [y[i] for i in val_idx]

        # Initialize weights
        weights = [self._rng.gauss(0, 0.1) for _ in range(n_features)]
        bias = 0.0

        best_val_loss = float("inf")
        best_weights = list(weights)
        best_bias = bias
        patience_counter = 0
        stopped_early = False
        converged = False

        for epoch in range(self.config.epochs):
            # Shuffle training data each epoch
            train_order = list(range(len(X_train)))
            self._rng.shuffle(train_order)

            epoch_loss = 0.0
            n_batches = 0

            for batch_start in range(0, len(train_order), self.config.batch_size):
                batch_indices = train_order[
                    batch_start : batch_start + self.config.batch_size
                ]
                batch_X = [X_train[i] for i in batch_indices]
                batch_y = [y_train[i] for i in batch_indices]

                # Compute gradients
                grad_w = [0.0] * n_features
                grad_b = 0.0

                for xi, yi in zip(batch_X, batch_y):
                    pred = self._predict_single(xi, weights, bias)
                    error = pred - yi
                    for j in range(n_features):
                        grad_w[j] += error * xi[j]
                    grad_b += error

                batch_size = len(batch_indices)
                for j in range(n_features):
                    grad_w[j] = grad_w[j] / batch_size + (
                        self.config.l2_regularization * weights[j]
                    )
                grad_b /= batch_size

                # Gradient clipping to prevent explosion
                max_grad_norm = 10.0
                grad_norm = math.sqrt(sum(g * g for g in grad_w) + grad_b * grad_b)
                if grad_norm > max_grad_norm:
                    scale = max_grad_norm / grad_norm
                    grad_w = [g * scale for g in grad_w]
                    grad_b *= scale

                # Update weights
                for j in range(n_features):
                    weights[j] -= self.config.learning_rate * grad_w[j]
                bias -= self.config.learning_rate * grad_b

                # Batch loss
                batch_loss = 0.0
                for xi, yi in zip(batch_X, batch_y):
                    pred = self._predict_single(xi, weights, bias)
                    batch_loss += (pred - yi) ** 2
                epoch_loss += batch_loss / batch_size
                n_batches += 1

            # Validation loss
            val_loss = 0.0
            if X_val:
                for xi, yi in zip(X_val, y_val):
                    pred = self._predict_single(xi, weights, bias)
                    val_loss += (pred - yi) ** 2
                val_loss /= len(X_val)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_weights = list(weights)
                best_bias = bias
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= self.config.early_stopping_patience:
                stopped_early = True
                break

            if epoch_loss / n_batches < 1e-6:
                converged = True
                break

        training_time = time.time() - start_time

        # Compute final metrics using best weights
        train_predictions = [self._predict_single(xi, best_weights, best_bias) for xi in X_train]
        val_predictions = [self._predict_single(xi, best_weights, best_bias) for xi in X_val]

        metrics = self._compute_metrics(y_train, train_predictions, y_val, val_predictions)

        # Compute actual training loss on full training set with best weights
        if X_train:
            final_train_loss = sum(
                (self._predict_single(xi, best_weights, best_bias) - yi) ** 2
                for xi, yi in zip(X_train, y_train)
            ) / len(X_train)
        else:
            final_train_loss = 0.0

        # Feature importances (based on weight magnitude)
        total_abs = sum(abs(w) for w in best_weights) or 1.0
        feature_importances = {
            name: abs(w) / total_abs for name, w in zip(feature_names, best_weights)
        }

        model_id = self._generate_model_id(self.config.model_name, best_weights, best_bias)

        result = TrainingResult(
            model_id=model_id,
            model_name=self.config.model_name,
            model_type=self.config.model_type,
            weights=best_weights,
            bias=best_bias,
            training_loss=final_train_loss,
            validation_loss=best_val_loss,
            epochs_run=epoch + 1,
            training_time_seconds=training_time,
            metrics=metrics,
            feature_importances=feature_importances,
            converged=converged,
            stopped_early=stopped_early,
        )

        self._models[model_id] = result
        return result

    def predict(self, model_id: str, X: List[List[float]]) -> List[float]:
        """Make predictions using a trained model."""
        if model_id not in self._models:
            raise KeyError(f"Model {model_id} not found")
        model = self._models[model_id]
        return [self._predict_single(xi, model.weights, model.bias) for xi in X]

    def get_model(self, model_id: str) -> TrainingResult:
        """Retrieve a trained model by ID."""
        if model_id not in self._models:
            raise KeyError(f"Model {model_id} not found")
        return self._models[model_id]

    def list_models(self) -> List[str]:
        """List all trained model IDs."""
        return list(self._models.keys())

    def _predict_single(self, x: List[float], weights: List[float], bias: float) -> float:
        """Make a prediction for a single sample."""
        raw = sum(w * xi for w, xi in zip(weights, x)) + bias
        if self.config.model_type == "logistic":
            return 1.0 / (1.0 + math.exp(-raw))
        return raw

    def _compute_metrics(
        self,
        y_train: List[float],
        train_preds: List[float],
        y_val: List[float],
        val_preds: List[float],
    ) -> Dict[str, float]:
        """Compute regression/classification metrics."""
        metrics: Dict[str, float] = {}

        if y_train:
            metrics["train_mse"] = sum(
                (p - a) ** 2 for p, a in zip(train_preds, y_train)
            ) / len(y_train)
            metrics["train_mae"] = sum(
                abs(p - a) for p, a in zip(train_preds, y_train)
            ) / len(y_train)
            metrics["train_rmse"] = math.sqrt(metrics["train_mse"])

            # R-squared
            mean_y = sum(y_train) / len(y_train)
            ss_tot = sum((yi - mean_y) ** 2 for yi in y_train)
            ss_res = sum((p - a) ** 2 for p, a in zip(train_preds, y_train))
            metrics["train_r2"] = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        if y_val:
            metrics["val_mse"] = sum(
                (p - a) ** 2 for p, a in zip(val_preds, y_val)
            ) / len(y_val)
            metrics["val_mae"] = sum(
                abs(p - a) for p, a in zip(val_preds, y_val)
            ) / len(y_val)
            metrics["val_rmse"] = math.sqrt(metrics["val_mse"])

        return metrics

    def _generate_model_id(self, name: str, weights: List[float], bias: float) -> str:
        """Generate a unique model ID based on name and parameters."""
        content = f"{name}:{json.dumps(weights)}:{bias}"
        return f"model_{hashlib.sha256(content.encode()).hexdigest()[:16]}"
