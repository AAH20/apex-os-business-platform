"""Feature engineering pipeline with composable transformers."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import Feature


class Transformer(ABC):
    """Base class for all feature transformers."""

    @abstractmethod
    def fit(self, rows: Iterable[Dict[str, Any]]) -> "Transformer":
        ...

    @abstractmethod
    def transform(self, row: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def fit_transform(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = list(rows)
        self.fit(rows)
        return [self.transform(r) for r in rows]


class StandardScaler(Transformer):
    """Z-score normalisation for a numeric column."""

    def __init__(self, column: str):
        self.column = column
        self.mean: float = 0.0
        self.std: float = 1.0
        self._fitted = False

    def fit(self, rows: Iterable[Dict[str, Any]]) -> "StandardScaler":
        vals = [float(r[self.column]) for r in rows if r.get(self.column) is not None]
        if not vals:
            return self
        self.mean = sum(vals) / len(vals)
        var = sum((v - self.mean) ** 2 for v in vals) / max(len(vals), 1)
        self.std = math.sqrt(var) or 1.0
        self._fitted = True
        return self

    def transform(self, row: Dict[str, Any]) -> Dict[str, Any]:
        val = row.get(self.column)
        if val is None:
            return {self.column: None}
        return {self.column: (float(val) - self.mean) / self.std}


class OneHotEncoder(Transformer):
    """One-hot encode a categorical column."""

    def __init__(self, column: str, max_categories: int = 50):
        self.column = column
        self.max_categories = max_categories
        self.categories: List[str] = []
        self._fitted = False

    def fit(self, rows: Iterable[Dict[str, Any]]) -> "OneHotEncoder":
        counts = Counter(str(r.get(self.column, "")) for r in rows)
        self.categories = [c for c, _ in counts.most_common(self.max_categories)]
        self._fitted = True
        return self

    def transform(self, row: Dict[str, Any]) -> Dict[str, Any]:
        val = str(row.get(self.column, ""))
        out: Dict[str, Any] = {}
        for cat in self.categories:
            out[f"{self.column}_{cat}"] = 1.0 if val == cat else 0.0
        return out


class FeaturePipeline:
    """Ordered chain of transformers producing a feature vector."""

    def __init__(self, features: Optional[List[Feature]] = None):
        self.features = features or []
        self.transformers: List[Transformer] = []
        self._fitted = False

    def add(self, transformer: Transformer) -> "FeaturePipeline":
        self.transformers.append(transformer)
        return self

    def fit(self, rows: Iterable[Dict[str, Any]]) -> "FeaturePipeline":
        rows = list(rows)
        for t in self.transformers:
            t.fit(rows)
        self._fitted = True
        return self

    def transform(self, row: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for t in self.transformers:
            out.update(t.transform(row))
        return out

    def transform_many(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.transform(r) for r in rows]

    def fit_transform(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = list(rows)
        self.fit(rows)
        return self.transform_many(rows)

    def feature_names(self) -> List[str]:
        names: List[str] = []
        for t in self.transformers:
            if isinstance(t, StandardScaler):
                names.append(t.column)
            elif isinstance(t, OneHotEncoder):
                names.extend(f"{t.column}_{c}" for c in t.categories)
        return names
