"""Model serving with batching support."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import Model, ModelStatus


class Predictor(ABC):
    """Interface for a servable predictor."""

    @abstractmethod
    def predict(self, features: Dict[str, Any]) -> Any:
        ...

    def predict_batch(self, rows: List[Dict[str, Any]]) -> List[Any]:
        return [self.predict(r) for r in rows]


class ThresholdPredictor(Predictor):
    """Simple threshold-based predictor for demonstration."""

    def __init__(self, weights: Dict[str, float], bias: float = 0.0, threshold: float = 0.5):
        self.weights = weights
        self.bias = bias
        self.threshold = threshold

    def predict(self, features: Dict[str, Any]) -> Any:
        z = self.bias + sum(
            self.weights.get(k, 0.0) * float(v)
            for k, v in features.items()
            if isinstance(v, (int, float))
        )
        prob = 1.0 / (1.0 + pow(2.718281828, -max(-30.0, min(30.0, z))))
        return int(prob >= self.threshold)


@dataclass
class PredictionResult:
    """Result of a single prediction."""

    value: Any
    latency_ms: float
    model_id: str
    model_version: str


@dataclass
class BatchResult:
    """Result of a batch prediction."""

    predictions: List[Any]
    latencies_ms: List[float]
    total_latency_ms: float
    model_id: str
    model_version: str


class ModelServer:
    """Serve a single model with request-level metrics."""

    def __init__(self, model: Model, predictor: Predictor):
        self.model = model
        self.predictor = predictor
        self._request_count = 0
        self._total_latency = 0.0

    @property
    def request_count(self) -> int:
        return self._request_count

    @property
    def avg_latency_ms(self) -> float:
        if self._request_count == 0:
            return 0.0
        return self._total_latency / self._request_count

    def predict(self, features: Dict[str, Any]) -> PredictionResult:
        start = time.perf_counter()
        value = self.predictor.predict(features)
        elapsed = (time.perf_counter() - start) * 1000.0
        self._request_count += 1
        self._total_latency += elapsed
        return PredictionResult(
            value=value,
            latency_ms=elapsed,
            model_id=self.model.id,
            model_version=self.model.version,
        )

    def health(self) -> Dict[str, Any]:
        return {
            "model_id": self.model.id,
            "model_name": self.model.name,
            "status": self.model.status.value,
            "request_count": self._request_count,
            "avg_latency_ms": self.avg_latency_ms,
        }


class BatchPredictor:
    """Efficient batch prediction with configurable batch size."""

    def __init__(self, server: ModelServer, batch_size: int = 32):
        self.server = server
        self.batch_size = batch_size

    def predict(self, rows: Iterable[Dict[str, Any]]) -> BatchResult:
        rows = list(rows)
        all_preds: List[Any] = []
        all_latencies: List[float] = []
        start = time.perf_counter()
        for i in range(0, len(rows), self.batch_size):
            chunk = rows[i : i + self.batch_size]
            for row in chunk:
                result = self.server.predict(row)
                all_preds.append(result.value)
                all_latencies.append(result.latency_ms)
        total = (time.perf_counter() - start) * 1000.0
        return BatchResult(
            predictions=all_preds,
            latencies_ms=all_latencies,
            total_latency_ms=total,
            model_id=self.server.model.id,
            model_version=self.server.model.version,
        )

    def predict_stream(
        self, rows: Iterable[Dict[str, Any]]
    ) -> Iterable[Tuple[Any, float]]:
        """Generator yielding (prediction, latency_ms) tuples."""
        for row in rows:
            result = self.server.predict(row)
            yield result.value, result.latency_ms
