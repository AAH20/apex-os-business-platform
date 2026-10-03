"""Deepened ML module: training, evaluation, deployment, feature engineering, monitoring."""
from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# 1. Model Training with Hyperparameter Tuning
# ---------------------------------------------------------------------------

class TuningStrategy(Enum):
    GRID = "grid"
    RANDOM = "random"
    BAYESIAN = "bayesian"


@dataclass
class HyperparameterSpace:
    """Defines searchable hyperparameter ranges."""
    params: Dict[str, List[Any]] = field(default_factory=dict)

    def sample(self, strategy: TuningStrategy, rng: np.random.Generator) -> Dict[str, Any]:
        if strategy == TuningStrategy.GRID:
            return {k: v[0] for k, v in self.params.items()}
        return {k: rng.choice(v) for k, v in self.params.items()}


@dataclass
class TrainingResult:
    model_id: str
    params: Dict[str, Any]
    metrics: Dict[str, float]
    feature_importance: Dict[str, float] = field(default_factory=dict)
    trained_at: float = field(default_factory=time.time)


class ModelTrainer:
    """Trains models with hyperparameter tuning."""

    def __init__(self, model_factory: Callable, space: HyperparameterSpace,
                 strategy: TuningStrategy = TuningStrategy.RANDOM, n_trials: int = 10):
        self._factory = model_factory
        self._space = space
        self._strategy = strategy
        self._n_trials = n_trials
        self._results: List[TrainingResult] = []

    def fit(self, X: np.ndarray, y: np.ndarray,
            eval_fn: Optional[Callable] = None) -> TrainingResult:
        rng = np.random.default_rng(42)
        best_score = -np.inf
        best_result = None
        for i in range(self._n_trials):
            params = self._space.sample(self._strategy, rng)
            model = self._factory(**params)
            model.fit(X, y)
            metrics = eval_fn(model, X, y) if eval_fn else {"score": float(model.score(X, y))}
            score = metrics.get("score", 0.0)
            result = TrainingResult(
                model_id=hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12],
                params=params, metrics=metrics,
                feature_importance=self._extract_importance(model),
            )
            self._results.append(result)
            if score > best_score:
                best_score, best_result = score, result
        return best_result

    def _extract_importance(self, model: Any) -> Dict[str, float]:
        if hasattr(model, "feature_importances_"):
            return {f"f{i}": float(v) for i, v in enumerate(model.feature_importances_)}
        return {}

    @property
    def best(self) -> Optional[TrainingResult]:
        return max(self._results, key=lambda r: r.metrics.get("score", 0)) if self._results else None


# ---------------------------------------------------------------------------
# 2. Model Evaluation with Cross-Validation
# ---------------------------------------------------------------------------

@dataclass
class CVResult:
    fold_scores: List[float]
    mean: float
    std: float
    confidence_interval: Tuple[float, float]


class CrossValidator:
    """K-fold cross-validation evaluator."""

    def __init__(self, n_splits: int = 5, shuffle: bool = True, random_state: int = 42):
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.random_state = random_state

    def evaluate(self, model_factory: Callable, X: np.ndarray, y: np.ndarray,
                 metric: Optional[Callable] = None) -> CVResult:
        n = len(y)
        indices = np.arange(n)
        if self.shuffle:
            np.random.default_rng(self.random_state).shuffle(indices)
        folds = np.array_split(indices, self.n_splits)
        scores: List[float] = []
        for i in range(self.n_splits):
            test_idx = folds[i]
            train_idx = np.concatenate([folds[j] for j in range(self.n_splits) if j != i])
            model = model_factory()
            model.fit(X[train_idx], y[train_idx])
            pred = model.predict(X[test_idx])
            score = metric(y[test_idx], pred) if metric else float(np.mean(pred == y[test_idx]))
            scores.append(score)
        arr = np.array(scores)
        ci = (float(arr.mean() - 1.96 * arr.std() / np.sqrt(len(arr))),
              float(arr.mean() + 1.96 * arr.std() / np.sqrt(len(arr))))
        return CVResult(fold_scores=scores, mean=float(arr.mean()), std=float(arr.std()), confidence_interval=ci)


# ---------------------------------------------------------------------------
# 3. Model Deployment with A/B Testing
# ---------------------------------------------------------------------------

class DeploymentStatus(Enum):
    CANARY = "canary"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"


@dataclass
class Deployment:
    deployment_id: str
    model_id: str
    variant: str
    traffic_pct: float
    status: DeploymentStatus
    metrics: Dict[str, float] = field(default_factory=dict)


class ABTestDeployer:
    """Deploys models with A/B traffic splitting and automatic rollback."""

    def __init__(self, canary_pct: float = 0.1, promotion_threshold: float = 0.02):
        self._canary_pct = canary_pct
        self._promotion_threshold = promotion_threshold
        self._deployments: Dict[str, Deployment] = {}
        self._traffic_log: Dict[str, List[bool]] = defaultdict(list)

    def deploy(self, model_id: str, variant: str = "treatment") -> Deployment:
        dep = Deployment(
            deployment_id=hashlib.sha256(f"{model_id}:{variant}".encode()).hexdigest()[:10],
            model_id=model_id, variant=variant,
            traffic_pct=self._canary_pct, status=DeploymentStatus.CANARY,
        )
        self._deployments[dep.deployment_id] = dep
        return dep

    def route(self, user_id: str) -> Optional[str]:
        for dep in self._deployments.values():
            if dep.status == DeploymentStatus.ACTIVE:
                return dep.model_id
        for dep in self._deployments.values():
            if dep.status == DeploymentStatus.CANARY:
                bucket = int(hashlib.sha256(user_id.encode()).hexdigest(), 16) % 100
                if bucket < dep.traffic_pct * 100:
                    return dep.model_id
        return None

    def record_outcome(self, deployment_id: str, success: bool) -> None:
        self._traffic_log[deployment_id].append(success)

    def evaluate_and_promote(self, deployment_id: str) -> DeploymentStatus:
        dep = self._deployments.get(deployment_id)
        if not dep:
            raise ValueError(f"Unknown deployment: {deployment_id}")
        outcomes = self._traffic_log.get(deployment_id, [])
        if len(outcomes) < 100:
            return dep.status
        treatment_rate = np.mean(outcomes)
        control_rate = 0.95
        if treatment_rate >= control_rate + self._promotion_threshold:
            dep.status = DeploymentStatus.ACTIVE
            dep.traffic_pct = 1.0
        elif treatment_rate < control_rate - self._promotion_threshold:
            dep.status = DeploymentStatus.ROLLED_BACK
            dep.traffic_pct = 0.0
        dep.metrics = {"success_rate": float(treatment_rate), "n_samples": len(outcomes)}
        return dep.status


# ---------------------------------------------------------------------------
# 4. Feature Engineering with AutoML
# ---------------------------------------------------------------------------

@dataclass
class FeatureTransform:
    name: str
    fn: Callable[[np.ndarray], np.ndarray]
    input_dim: int
    output_dim: int


class AutoMLFeatureEngineer:
    """Automated feature engineering with transform discovery."""

    def __init__(self, max_features: int = 50):
        self.max_features = max_features
        self.transforms: List[FeatureTransform] = []
        self._fitted = False

    def _candidate_transforms(self) -> List[FeatureTransform]:
        return [
            FeatureTransform("square", lambda x: x ** 2, 1, 1),
            FeatureTransform("sqrt", lambda x: np.sqrt(np.abs(x)), 1, 1),
            FeatureTransform("log1p", lambda x: np.log1p(np.abs(x)), 1, 1),
            FeatureTransform("sigmoid", lambda x: 1 / (1 + np.exp(-x)), 1, 1),
            FeatureTransform("interaction", lambda x: x[:, 0] * x[:, 1] if x.shape[1] >= 2 else x[:, 0], 2, 1),
            FeatureTransform("poly2", lambda x: np.hstack([x, x ** 2]), -1, -1),
        ]

    def fit_transform(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> np.ndarray:
        candidates = self._candidate_transforms()
        base_score = self._baseline_score(X, y) if y is not None else 0.0
        scored: List[Tuple[float, FeatureTransform]] = []
        for t in candidates:
            try:
                transformed = t.fn(X)
                if transformed.ndim == 1:
                    transformed = transformed.reshape(-1, 1)
                combined = np.hstack([X, transformed])
                score = self._baseline_score(combined, y) if y is not None else 0.0
                if score > base_score:
                    scored.append((score, t))
            except (ValueError, FloatingPointError):
                continue
        scored.sort(key=lambda s: s[0], reverse=True)
        selected = scored[: self.max_features]
        self.transforms = [t for _, t in selected]
        self._fitted = True
        if not self.transforms:
            return X
        return self.transform(X)

    def transform(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Must call fit_transform first")
        parts = [X]
        for t in self.transforms:
            out = t.fn(X)
            if out.ndim == 1:
                out = out.reshape(-1, 1)
            parts.append(out)
        return np.hstack(parts)

    def _baseline_score(self, X: np.ndarray, y: Optional[np.ndarray]) -> float:
        if y is None or X.shape[0] == 0:
            return 0.0
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.model_selection import cross_val_score
            model = LogisticRegression(max_iter=200)
            scores = cross_val_score(model, X, y, cv=3, scoring="accuracy")
            return float(scores.mean())
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# 5. Model Monitoring with Drift Detection
# ---------------------------------------------------------------------------

class DriftMethod(Enum):
    PSI = "psi"
    KS = "ks"
    WASSERSTEIN = "wasserstein"


@dataclass
class DriftReport:
    feature: str
    method: DriftMethod
    statistic: float
    p_value: float
    drifted: bool
    threshold: float


class ModelMonitor:
    """Monitors model inputs/outputs for data and concept drift."""

    def __init__(self, reference_data: np.ndarray, threshold: float = 0.05,
                 method: DriftMethod = DriftMethod.PSI):
        self.reference = reference_data
        self.threshold = threshold
        self.method = method
        self._prediction_log: List[np.ndarray] = []
        self._drift_history: List[DriftReport] = []

    def check_input_drift(self, current: np.ndarray) -> List[DriftReport]:
        reports: List[DriftReport] = []
        for col in range(min(self.reference.shape[1], current.shape[1])):
            ref_col = self.reference[:, col]
            cur_col = current[:, col]
            stat, pval = self._compute(ref_col, cur_col)
            report = DriftReport(
                feature=f"feature_{col}", method=self.method,
                statistic=float(stat), p_value=float(pval),
                drifted=bool(pval < self.threshold), threshold=self.threshold,
            )
            reports.append(report)
            self._drift_history.append(report)
        return reports

    def check_prediction_drift(self, predictions: np.ndarray) -> DriftReport:
        self._prediction_log.append(predictions)
        if len(self._prediction_log) < 2:
            return DriftReport("prediction", self.method, 0.0, 1.0, False, self.threshold)
        recent = np.concatenate(self._prediction_log[-10:])
        ref_pred = self._prediction_log[0]
        stat, pval = self._compute(ref_pred, recent)
        return DriftReport("prediction", self.method, float(stat), float(pval),
                           bool(pval < self.threshold), self.threshold)

    def _compute(self, ref: np.ndarray, cur: np.ndarray) -> Tuple[float, float]:
        if self.method == DriftMethod.PSI:
            return self._psi(ref, cur)
        elif self.method == DriftMethod.KS:
            return self._ks(ref, cur)
        else:
            return self._wasserstein(ref, cur)

    @staticmethod
    def _psi(ref: np.ndarray, cur: np.ndarray, bins: int = 10) -> Tuple[float, float]:
        edges = np.quantile(ref, np.linspace(0, 1, bins + 1))
        edges[0], edges[-1] = -np.inf, np.inf
        ref_pct = np.histogram(ref, bins=edges)[0] / len(ref)
        cur_pct = np.histogram(cur, bins=edges)[0] / len(cur)
        ref_pct = np.clip(ref_pct, 1e-6, None)
        cur_pct = np.clip(cur_pct, 1e-6, None)
        psi = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))
        return psi, float(np.exp(-psi))

    @staticmethod
    def _ks(ref: np.ndarray, cur: np.ndarray) -> Tuple[float, float]:
        from scipy import stats
        result = stats.ks_2samp(ref, cur)
        return float(result.statistic), float(result.pvalue)

    @staticmethod
    def _wasserstein(ref: np.ndarray, cur: np.ndarray) -> Tuple[float, float]:
        from scipy import stats
        result = stats.wasserstein_distance(ref, cur)
        return float(result), float(np.exp(-result))

    @property
    def drift_count(self) -> int:
        return sum(1 for r in self._drift_history if r.drifted)

    def summary(self) -> Dict[str, Any]:
        total = len(self._drift_history)
        drifted = self.drift_count
        return {
            "total_checks": total,
            "drifted_features": drifted,
            "drift_rate": drifted / total if total else 0.0,
            "last_check": self._drift_history[-1].__dict__ if self._drift_history else None,
        }
