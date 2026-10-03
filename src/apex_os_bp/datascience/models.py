"""Core data science models: Dataset, Feature, Model, Experiment."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModelStatus(str, Enum):
    """Lifecycle status of a model."""

    DRAFT = "draft"
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


@dataclass
class Dataset:
    """A named, versioned dataset with metadata."""

    name: str
    version: str = "1.0.0"
    rows: int = 0
    columns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint of dataset identity."""
        payload = f"{self.name}:{self.version}:{self.rows}:{','.join(self.columns)}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "rows": self.rows,
            "columns": len(self.columns),
            "fingerprint": self.fingerprint,
        }


@dataclass
class Feature:
    """A single feature definition with type and transformation info."""

    name: str
    dtype: str = "float"
    description: str = ""
    nullable: bool = False
    tags: List[str] = field(default_factory=list)
    stats: Dict[str, float] = field(default_factory=dict)

    def validate_value(self, value: Any) -> bool:
        """Check a raw value against this feature's dtype."""
        if value is None:
            return self.nullable
        try:
            if self.dtype == "int":
                int(value)
            elif self.dtype == "float":
                float(value)
            elif self.dtype == "bool":
                if not isinstance(value, (bool, int)):
                    return False
            elif self.dtype == "str":
                if not isinstance(value, str):
                    return False
            return True
        except (ValueError, TypeError):
            return False


@dataclass
class Model:
    """A trained (or trainable) model artifact."""

    name: str
    model_type: str = "sklearn"
    version: str = "0.1.0"
    status: ModelStatus = ModelStatus.DRAFT
    metrics: Dict[str, float] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    feature_names: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    artifact_path: Optional[str] = None

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "model_type": self.model_type,
            "status": self.status.value,
            "metrics": self.metrics,
            "params": self.params,
            "feature_names": self.feature_names,
            "artifact_path": self.artifact_path,
        }

    def save_manifest(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_manifest(), indent=2))


@dataclass
class Experiment:
    """A tracked experiment linking datasets, features, and models."""

    name: str
    dataset: Optional[Dataset] = None
    features: List[Feature] = field(default_factory=list)
    models: List[Model] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def add_model(self, model: Model) -> None:
        self.models.append(model)

    def best_model(self, metric: str = "accuracy") -> Optional[Model]:
        if not self.models:
            return None
        scored = [m for m in self.models if metric in m.metrics]
        if not scored:
            return None
        return max(scored, key=lambda m: m.metrics[metric])

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "n_features": len(self.features),
            "n_models": len(self.models),
            "best_model": self.best_model().name if self.best_model() else None,
        }
