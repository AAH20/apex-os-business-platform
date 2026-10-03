"""Advanced Data Science: model registry, A/B testing, drift detection, explainability, AutoML."""

import hashlib
import time
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import cross_val_score


class ModelRegistry:
    """Register, version, and retrieve ML models."""

    def __init__(self):
        self._models: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, model: Any, metadata: Optional[Dict] = None) -> str:
        version = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:8]
        self._models[name] = {
            "model": model, "version": version,
            "metadata": metadata or {}, "created_at": time.time(),
        }
        return version

    def get(self, name: str) -> Optional[Any]:
        entry = self._models.get(name)
        return entry["model"] if entry else None

    def get_version(self, name: str) -> Optional[str]:
        entry = self._models.get(name)
        return entry["version"] if entry else None

    def list_models(self) -> List[str]:
        return list(self._models.keys())

    def remove(self, name: str) -> bool:
        return self._models.pop(name, None) is not None


class ABTest:
    """A/B testing framework for model comparison."""

    @staticmethod
    def compare_models(model_a: Any, model_b: Any, X: np.ndarray, y: np.ndarray,
                       n_bootstrap: int = 1000) -> Dict[str, Any]:
        scores_a = cross_val_score(model_a, X, y, cv=5, scoring="accuracy")
        scores_b = cross_val_score(model_b, X, y, cv=5, scoring="accuracy")
        t_stat, p_value = stats.ttest_rel(scores_a, scores_b)
        rng = np.random.RandomState(42)
        diffs = [scores_a[rng.randint(0, len(scores_a), len(scores_a))].mean()
                 - scores_b[rng.randint(0, len(scores_b), len(scores_b))].mean()
                 for _ in range(n_bootstrap)]
        ci_lower, ci_upper = np.percentile(diffs, [2.5, 97.5])
        return {
            "model_a_mean": float(scores_a.mean()),
            "model_b_mean": float(scores_b.mean()),
            "t_statistic": float(t_stat), "p_value": float(p_value),
            "ci_lower": float(ci_lower), "ci_upper": float(ci_upper),
            "winner": "A" if scores_a.mean() > scores_b.mean() else "B",
            "significant": bool(p_value < 0.05),
        }


class DriftDetector:
    """Detect data drift between reference and current distributions."""

    @staticmethod
    def psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
        breakpoints = np.percentile(reference, np.linspace(0, 100, bins + 1))
        breakpoints[0], breakpoints[-1] = -np.inf, np.inf
        ref_counts = np.clip(np.histogram(reference, bins=breakpoints)[0] / len(reference), 1e-6, None)
        cur_counts = np.clip(np.histogram(current, bins=breakpoints)[0] / len(current), 1e-6, None)
        return float(np.sum((cur_counts - ref_counts) * np.log(cur_counts / ref_counts)))

    @staticmethod
    def ks_test(reference: np.ndarray, current: np.ndarray) -> Dict[str, float]:
        stat, p_value = stats.ks_2samp(reference, current)
        return {"statistic": float(stat), "p_value": float(p_value)}

    @classmethod
    def detect(cls, reference: np.ndarray, current: np.ndarray,
               threshold: float = 0.2) -> Dict[str, Any]:
        psi_val = cls.psi(reference, current)
        ks = cls.ks_test(reference, current)
        return {
            "psi": psi_val, "ks_statistic": ks["statistic"], "ks_p_value": ks["p_value"],
            "drift_detected": bool(psi_val > threshold or ks["p_value"] < 0.05),
            "severity": "high" if psi_val > 0.2 else "medium" if psi_val > 0.1 else "low",
        }


class Explainability:
    """Model explainability via permutation importance."""

    @staticmethod
    def permutation_importance(model: Any, X: np.ndarray, y: np.ndarray,
                               n_repeats: int = 10) -> Dict[str, float]:
        baseline = accuracy_score(y, model.predict(X))
        importances = {}
        for col in range(X.shape[1]):
            scores = []
            for r in range(n_repeats):
                X_perm = X.copy()
                rng = np.random.RandomState(42 + col * 100 + r)
                X_perm[:, col] = rng.permutation(X_perm[:, col])
                scores.append(baseline - accuracy_score(y, model.predict(X_perm)))
            importances[f"feature_{col}"] = float(np.mean(scores))
        return importances

    @staticmethod
    def feature_importance(model: Any, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        if hasattr(model, "feature_importances_"):
            return {f"feature_{i}": float(v) for i, v in enumerate(model.feature_importances_)}
        return Explainability.permutation_importance(model, X, y)


class AutoML:
    """Automated model selection via cross-validation."""

    MODELS = {
        "random_forest": RandomForestClassifier,
        "gradient_boosting": GradientBoostingClassifier,
        "logistic_regression": LogisticRegression,
    }

    @classmethod
    def auto_select(cls, X: np.ndarray, y: np.ndarray,
                    cv: int = 5, scoring: str = "accuracy") -> Dict[str, Any]:
        results = {}
        for name, model_cls in cls.MODELS.items():
            try:
                kwargs = {"max_iter": 1000} if name == "logistic_regression" else {"random_state": 42}
                scores = cross_val_score(model_cls(**kwargs), X, y, cv=cv, scoring=scoring)
                results[name] = {"mean_score": float(scores.mean()), "std_score": float(scores.std())}
            except Exception:
                continue
        if not results:
            raise ValueError("No models could be trained")
        best_name = max(results, key=lambda k: results[k]["mean_score"])
        kwargs = {"max_iter": 1000} if best_name == "logistic_regression" else {"random_state": 42}
        best_model = cls.MODELS[best_name](**kwargs)
        best_model.fit(X, y)
        return {
            "best_model": best_model, "best_name": best_name,
            "best_score": results[best_name]["mean_score"], "all_results": results,
        }
