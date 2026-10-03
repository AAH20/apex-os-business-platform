"""Advanced Data Science: training, evaluation, feature engineering, deployment, monitoring."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from scipy import stats
from sklearn.base import BaseEstimator
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

ArrayLike = Union[np.ndarray, List[List[float]]]


class TaskType(str, Enum):
    """Supported ML task types."""

    CLASSIFICATION = "classification"
    REGRESSION = "regression"


class DriftStatus(str, Enum):
    """Drift detection outcome."""

    NO_DRIFT = "no_drift"
    WARNING = "warning"
    DRIFT = "drift"


class DataScienceError(Exception):
    """Base exception for DataScience operations."""


class ModelTrainingError(DataScienceError):
    """Raised when model training fails."""


class DeploymentError(DataScienceError):
    """Raised when model deployment fails."""


@dataclass
class TrainingResult:
    """Result of a model training run."""

    model: BaseEstimator
    best_params: Dict[str, Any]
    cv_scores: List[float]
    feature_importances: Dict[str, float]
    metrics: Dict[str, float]
    training_time: float


@dataclass
class EvaluationResult:
    """Result of cross-validated model evaluation."""

    mean_score: float
    std_score: float
    fold_scores: List[float]
    metrics: Dict[str, float]


@dataclass
class DriftReport:
    """Drift detection report for a deployed model."""

    feature: str
    psi: float
    ks_statistic: float
    status: DriftStatus
    timestamp: float = field(default_factory=time.time)


class FeatureEngineer:
    """Automated feature engineering with autoML-style transformations.

    Generates polynomial features, interaction terms, and statistical
    aggregations to enrich raw datasets before model training.
    """

    def __init__(self, max_poly_degree: int = 2, include_interactions: bool = True) -> None:
        self.max_poly_degree = max_poly_degree
        self.include_interactions = include_interactions
        self._fitted = False
        self._feature_names: List[str] = []

    def fit_transform(self, X: np.ndarray, feature_names: Optional[List[str]] = None) -> np.ndarray:
        """Fit and transform input features with automated engineering.

        Args:
            X: Input feature matrix of shape (n_samples, n_features).
            feature_names: Optional list of feature names.

        Returns:
            Transformed feature matrix with engineered columns.

        Raises:
            ValueError: If input is empty or has invalid dimensions.
        """
        if X.size == 0:
            raise ValueError("Input feature matrix is empty")
        if X.ndim != 2:
            raise ValueError(f"Expected 2D array, got {X.ndim}D")

        n_features = X.shape[1]
        self._feature_names = feature_names or [f"f{i}" for i in range(n_features)]
        transformed: List[np.ndarray] = [X]

        if self.max_poly_degree >= 2:
            for degree in range(2, self.max_poly_degree + 1):
                transformed.append(np.power(X, degree))

        if self.include_interactions and n_features >= 2:
            interactions = []
            for i in range(n_features):
                for j in range(i + 1, n_features):
                    interactions.append((X[:, i] * X[:, j]).reshape(-1, 1))
            if interactions:
                transformed.append(np.hstack(interactions))

        self._fitted = True
        return np.hstack(transformed)

    def get_feature_names(self) -> List[str]:
        """Return names of engineered features."""
        if not self._fitted:
            raise DataScienceError("FeatureEngineer has not been fitted yet")
        return self._feature_names


class ModelTrainer:
    """Train ML models with automated hyperparameter tuning.

    Supports classification and regression tasks with grid-search
    cross-validation for optimal parameter selection.
    """

    _PARAM_GRIDS: Dict[str, Dict[str, List[Any]]] = {
        "random_forest": {
            "n_estimators": [50, 100, 200],
            "max_depth": [3, 5, 10, None],
            "min_samples_split": [2, 5, 10],
        },
        "gradient_boosting": {
            "n_estimators": [50, 100, 200],
            "learning_rate": [0.01, 0.1, 0.2],
            "max_depth": [3, 5, 7],
        },
        "logistic_regression": {
            "C": [0.01, 0.1, 1.0, 10.0],
            "penalty": ["l1", "l2"],
            "solver": ["liblinear"],
        },
    }

    def __init__(self, task_type: TaskType = TaskType.CLASSIFICATION, random_state: int = 42) -> None:
        self.task_type = task_type
        self.random_state = random_state

    def _get_estimator(self, model_name: str) -> BaseEstimator:
        """Get unscaled estimator by name."""
        if model_name == "random_forest":
            return RandomForestClassifier(random_state=self.random_state)
        if model_name == "gradient_boosting":
            return GradientBoostingClassifier(random_state=self.random_state)
        if model_name == "logistic_regression":
            return LogisticRegression(random_state=self.random_state, max_iter=1000)
        raise ValueError(f"Unknown model: {model_name}")

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model_name: str = "random_forest",
        cv_folds: int = 5,
        feature_names: Optional[List[str]] = None,
    ) -> TrainingResult:
        """Train a model with grid-search hyperparameter tuning.

        Args:
            X: Training feature matrix.
            y: Target vector.
            model_name: One of 'random_forest', 'gradient_boosting', 'logistic_regression'.
            cv_folds: Number of cross-validation folds.
            feature_names: Optional feature names for importance mapping.

        Returns:
            TrainingResult with tuned model and metrics.

        Raises:
            ModelTrainingError: If training fails.
        """
        start_time = time.time()
        try:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=self.random_state,
                stratify=y if self.task_type == TaskType.CLASSIFICATION else None,
            )
            pipeline = Pipeline([
                ("scaler", StandardScaler()),
                ("model", self._get_estimator(model_name)),
            ])
            param_grid = {f"model__{k}": v for k, v in self._PARAM_GRIDS[model_name].items()}
            grid_search = GridSearchCV(
                pipeline, param_grid, cv=cv_folds,
                scoring="accuracy" if self.task_type == TaskType.CLASSIFICATION else "neg_mean_squared_error",
                n_jobs=-1,
            )
            grid_search.fit(X_train, y_train)

            best_model = grid_search.best_estimator_
            y_pred = best_model.predict(X_val)
            metrics = self._compute_metrics(y_val, y_pred)
            importances = self._extract_importances(best_model, feature_names, X.shape[1])
            training_time = time.time() - start_time

            return TrainingResult(
                model=best_model,
                best_params=grid_search.best_params_,
                cv_scores=list(grid_search.cv_results_["mean_test_score"]),
                feature_importances=importances,
                metrics=metrics,
                training_time=training_time,
            )
        except Exception as exc:
            raise ModelTrainingError(f"Training failed: {exc}") from exc

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Compute task-appropriate evaluation metrics."""
        if self.task_type == TaskType.CLASSIFICATION:
            return {
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
                "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
                "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
            }
        return {
            "mse": float(mean_squared_error(y_true, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        }

    def _extract_importances(
        self, model: Pipeline, feature_names: Optional[List[str]], n_features: int
    ) -> Dict[str, float]:
        """Extract feature importances from the trained model."""
        names = feature_names or [f"f{i}" for i in range(n_features)]
        try:
            raw = model.named_steps["model"].feature_importances_
            return {name: float(val) for name, val in zip(names, raw[:n_features])}
        except (AttributeError, KeyError):
            return {name: 0.0 for name in names}


class ModelEvaluator:
    """Evaluate models using stratified cross-validation."""

    def __init__(self, task_type: TaskType = TaskType.CLASSIFICATION, n_splits: int = 5) -> None:
        self.task_type = task_type
        self.n_splits = n_splits

    def evaluate(self, model: BaseEstimator, X: np.ndarray, y: np.ndarray) -> EvaluationResult:
        """Run cross-validated evaluation of a model.

        Args:
            model: Fitted scikit-learn estimator.
            X: Feature matrix.
            y: Target vector.

        Returns:
            EvaluationResult with aggregate and per-fold scores.

        Raises:
            DataScienceError: If evaluation fails.
        """
        try:
            cv = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=42)
            scoring = "accuracy" if self.task_type == TaskType.CLASSIFICATION else "neg_mean_squared_error"
            scores = cross_val_score(model, X, y, cv=cv, scoring=scoring, n_jobs=-1)
            y_pred = model.predict(X)
            metrics = self._compute_metrics(y, y_pred)
            return EvaluationResult(
                mean_score=float(np.mean(scores)),
                std_score=float(np.std(scores)),
                fold_scores=list(scores),
                metrics=metrics,
            )
        except Exception as exc:
            raise DataScienceError(f"Evaluation failed: {exc}") from exc

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Compute evaluation metrics based on task type."""
        if self.task_type == TaskType.CLASSIFICATION:
            return {
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
                "roc_auc": float(roc_auc_score(y_true, y_pred)) if len(np.unique(y_true)) == 2 else 0.0,
            }
        return {"mse": float(mean_squared_error(y_true, y_pred))}


class ABTestDeployer:
    """Deploy models with A/B testing traffic splitting.

    Routes incoming prediction requests between a control (production)
    and candidate (new) model based on a configurable traffic split.
    """

    def __init__(
        self,
        control_model: BaseEstimator,
        candidate_model: BaseEstimator,
        traffic_split: float = 0.1,
    ) -> None:
        if not 0.0 <= traffic_split <= 1.0:
            raise ValueError("traffic_split must be between 0.0 and 1.0")
        self.control_model = control_model
        self.candidate_model = candidate_model
        self.traffic_split = traffic_split
        self._control_hash = self._model_hash(control_model)
        self._candidate_hash = self._model_hash(candidate_model)
        self._metrics: Dict[str, List[float]] = {"control": [], "candidate": []}

    @staticmethod
    def _model_hash(model: BaseEstimator) -> str:
        """Generate a deterministic hash for a model configuration."""
        params = json.dumps(model.get_params(), sort_keys=True, default=str)
        return hashlib.sha256(params.encode()).hexdigest()[:12]

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, str]:
        """Route prediction to control or candidate model.

        Args:
            X: Input feature matrix.

        Returns:
            Tuple of (predictions, variant_label).

        Raises:
            DeploymentError: If prediction fails.
        """
        try:
            if np.random.random() < self.traffic_split:
                return self.candidate_model.predict(X), "candidate"
            return self.control_model.predict(X), "control"
        except Exception as exc:
            raise DeploymentError(f"A/B prediction failed: {exc}") from exc

    def record_outcome(self, variant: str, score: float) -> None:
        """Record an outcome metric for A/B analysis."""
        if variant not in self._metrics:
            raise ValueError(f"Unknown variant: {variant}")
        self._metrics[variant].append(score)

    def get_results(self) -> Dict[str, Dict[str, float]]:
        """Return aggregated A/B test results."""
        results: Dict[str, Dict[str, float]] = {}
        for variant, scores in self._metrics.items():
            if scores:
                results[variant] = {
                    "count": float(len(scores)),
                    "mean": float(np.mean(scores)),
                    "std": float(np.std(scores)),
                }
            else:
                results[variant] = {"count": 0.0, "mean": 0.0, "std": 0.0}
        return results


class DriftMonitor:
    """Monitor deployed models for data and concept drift.

    Uses Population Stability Index (PSI) and Kolmogorov-Smirnov
    tests to detect distributional shifts in feature data.
    """

    def __init__(
        self,
        reference_data: np.ndarray,
        threshold_psi: float = 0.2,
        threshold_ks: float = 0.1,
    ) -> None:
        self.reference_data = reference_data
        self.threshold_psi = threshold_psi
        self.threshold_ks = threshold_ks
        self._reference_bins = self._compute_bins(reference_data)

    def _compute_bins(self, data: np.ndarray, n_bins: int = 10) -> List[np.ndarray]:
        """Compute quantile-based bin edges per feature."""
        bins = []
        for col in range(data.shape[1]):
            edges = np.quantile(data[:, col], np.linspace(0, 1, n_bins + 1))
            edges[0], edges[-1] = -np.inf, np.inf
            bins.append(np.unique(edges))
        return bins

    def _psi(self, expected: np.ndarray, actual: np.ndarray) -> float:
        """Calculate Population Stability Index between two distributions."""
        e_pct = np.histogram(expected, bins=self._reference_bins[0])[0] / len(expected)
        a_pct = np.histogram(actual, bins=self._reference_bins[0])[0] / len(actual)
        e_pct = np.clip(e_pct, 1e-6, None)
        a_pct = np.clip(a_pct, 1e-6, None)
        return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))

    def _ks_statistic(self, reference: np.ndarray, current: np.ndarray) -> float:
        """Compute two-sample Kolmogorov-Smirnov statistic."""
        result = stats.ks_2samp(reference, current)
        return float(result.statistic)

    def check_feature(
        self, feature_name: str, feature_index: int, current_data: np.ndarray
    ) -> DriftReport:
        """Check a single feature for drift against reference.

        Args:
            feature_name: Human-readable feature name.
            feature_index: Column index in the data matrix.
            current_data: Current production data for this feature.

        Returns:
            DriftReport with PSI, KS statistic, and drift status.
        """
        ref_col = self.reference_data[:, feature_index]
        cur_col = current_data[:, feature_index] if current_data.ndim > 1 else current_data
        psi = self._psi(ref_col, cur_col)
        ks = self._ks_statistic(ref_col, cur_col)

        if psi > self.threshold_psi or ks > self.threshold_ks:
            status = DriftStatus.DRIFT
        elif psi > self.threshold_psi * 0.5 or ks > self.threshold_ks * 0.5:
            status = DriftStatus.WARNING
        else:
            status = DriftStatus.NO_DRIFT

        return DriftReport(feature=feature_name, psi=psi, ks_statistic=ks, status=status)

    def check_all(
        self, current_data: np.ndarray, feature_names: Optional[List[str]] = None
    ) -> List[DriftReport]:
        """Check all features for drift.

        Args:
            current_data: Current production data matrix.
            feature_names: Optional feature names.

        Returns:
            List of DriftReport, one per feature.
        """
        n_features = current_data.shape[1]
        names = feature_names or [f"f{i}" for i in range(n_features)]
        return [self.check_feature(names[i], i, current_data) for i in range(n_features)]
