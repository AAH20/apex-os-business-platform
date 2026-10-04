"""Model serving component for APEX-OS ML Platform."""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .training import ModelTrainer


@dataclass
class ServingConfig:
    """Configuration for model serving."""

    model_id: str
    model_name: str
    version: str = "1.0.0"
    batch_timeout_ms: float = 10.0
    max_batch_size: int = 64
    enable_caching: bool = True
    cache_ttl_seconds: float = 60.0
    max_concurrent_requests: int = 100


@dataclass
class Prediction:
    """A single prediction result."""

    model_id: str
    model_name: str
    version: str
    input_hash: str
    prediction: float
    confidence: float
    latency_ms: float
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "version": self.version,
            "input_hash": self.input_hash,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
            "metadata": self.metadata,
        }


class ModelServer:
    """Serves trained models for real-time and batch inference."""

    def __init__(self, trainer: ModelTrainer):
        self._trainer = trainer
        self._deployed: Dict[str, ServingConfig] = {}
        self._cache: Dict[str, Tuple[Prediction, float]] = {}
        self._cache_lock = threading.Lock()
        self._semaphore = threading.Semaphore(100)
        self._request_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0
        self._lock = threading.Lock()

    def deploy(self, config: ServingConfig) -> None:
        """Deploy a model for serving."""
        # Verify model exists
        self._trainer.get_model(config.model_id)
        self._deployed[config.model_id] = config

    def undeploy(self, model_id: str) -> None:
        """Remove a model from serving."""
        if model_id in self._deployed:
            del self._deployed[model_id]
        # Clear cache for this model
        with self._cache_lock:
            keys_to_remove = [
                k for k in self._cache if k.startswith(f"{model_id}:")
            ]
            for k in keys_to_remove:
                del self._cache[k]

    def predict(self, model_id: str, features: List[float]) -> Prediction:
        """Make a single prediction."""
        if model_id not in self._deployed:
            raise KeyError(f"Model {model_id} is not deployed")

        config = self._deployed[model_id]
        input_hash = self._hash_input(features)

        # Check cache
        if config.enable_caching:
            cached = self._get_from_cache(model_id, input_hash, config.cache_ttl_seconds)
            if cached is not None:
                return cached

        start_time = time.time()

        with self._semaphore:
            try:
                predictions = self._trainer.predict(model_id, [features])
                raw_pred = predictions[0]

                # Compute confidence (distance from decision boundary for logistic)
                confidence = self._compute_confidence(raw_pred)

                latency_ms = (time.time() - start_time) * 1000.0

                prediction = Prediction(
                    model_id=model_id,
                    model_name=config.model_name,
                    version=config.version,
                    input_hash=input_hash,
                    prediction=raw_pred,
                    confidence=confidence,
                    latency_ms=latency_ms,
                    cached=False,
                )

                # Store in cache
                if config.enable_caching:
                    self._store_in_cache(model_id, input_hash, prediction, config.cache_ttl_seconds)

                # Update stats
                with self._lock:
                    self._request_count += 1
                    self._total_latency_ms += latency_ms

                return prediction
            except Exception as e:
                with self._lock:
                    self._error_count += 1
                raise

    def predict_batch(self, model_id: str, features_list: List[List[float]]) -> List[Prediction]:
        """Make batch predictions."""
        if not features_list:
            return []
        return [self.predict(model_id, f) for f in features_list]

    def get_stats(self) -> Dict[str, Any]:
        """Get serving statistics."""
        with self._lock:
            avg_latency = (
                self._total_latency_ms / self._request_count
                if self._request_count > 0
                else 0.0
            )
            return {
                "total_requests": self._request_count,
                "total_errors": self._error_count,
                "error_rate": (
                    self._error_count / self._request_count
                    if self._request_count > 0
                    else 0.0
                ),
                "average_latency_ms": avg_latency,
                "deployed_models": len(self._deployed),
                "cache_size": len(self._cache),
            }

    def clear_cache(self) -> None:
        """Clear the prediction cache."""
        with self._cache_lock:
            self._cache.clear()

    def list_deployed(self) -> List[str]:
        """List deployed model IDs."""
        return list(self._deployed.keys())

    def _hash_input(self, features: List[float]) -> str:
        """Hash input features for caching."""
        return hashlib.sha256(json.dumps(features).encode()).hexdigest()[:16]

    def _get_from_cache(
        self, model_id: str, input_hash: str, ttl: float
    ) -> Optional[Prediction]:
        """Get prediction from cache if not expired."""
        key = f"{model_id}:{input_hash}"
        with self._cache_lock:
            if key in self._cache:
                prediction, timestamp = self._cache[key]
                if time.time() - timestamp < ttl:
                    # Return a copy with cached=True
                    return Prediction(
                        model_id=prediction.model_id,
                        model_name=prediction.model_name,
                        version=prediction.version,
                        input_hash=prediction.input_hash,
                        prediction=prediction.prediction,
                        confidence=prediction.confidence,
                        latency_ms=0.0,
                        cached=True,
                        metadata=prediction.metadata,
                    )
                else:
                    del self._cache[key]
        return None

    def _store_in_cache(
        self, model_id: str, input_hash: str, prediction: Prediction, ttl: float
    ) -> None:
        """Store prediction in cache."""
        key = f"{model_id}:{input_hash}"
        with self._cache_lock:
            self._cache[key] = (prediction, time.time())

    def _compute_confidence(self, raw_prediction: float) -> float:
        """Compute confidence score for a prediction."""
        # For logistic: confidence is distance from 0.5
        # For linear: use a sigmoid-like transformation
        return abs(raw_prediction - 0.5) * 2.0 if 0 <= raw_prediction <= 1 else 1.0 / (
            1.0 + math.exp(-abs(raw_prediction))
        )
