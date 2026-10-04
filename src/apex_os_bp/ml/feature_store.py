"""Feature store component for APEX-OS ML Platform."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Feature:
    """Definition of a single feature."""

    name: str
    dtype: str  # "float", "int", "string", "bool"
    description: str = ""
    default_value: Any = None
    tags: List[str] = field(default_factory=list)
    ttl_seconds: Optional[float] = None

    def validate_value(self, value: Any) -> bool:
        """Validate that a value matches the feature's dtype."""
        if value is None:
            return self.default_value is not None
        if self.dtype == "float":
            return isinstance(value, (int, float))
        if self.dtype == "int":
            return isinstance(value, int) and not isinstance(value, bool)
        if self.dtype == "string":
            return isinstance(value, str)
        if self.dtype == "bool":
            return isinstance(value, bool)
        return False


@dataclass
class FeatureGroup:
    """A group of related features."""

    name: str
    features: List[Feature]
    description: str = ""
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)

    def get_feature_names(self) -> List[str]:
        return [f.name for f in self.features]

    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a record against this feature group."""
        errors = []
        for feature in self.features:
            if feature.name not in record:
                if feature.default_value is not None:
                    continue
                errors.append(f"Missing required feature: {feature.name}")
            elif not feature.validate_value(record[feature.name]):
                errors.append(
                    f"Invalid type for feature {feature.name}: expected {feature.dtype}"
                )
        return len(errors) == 0, errors


class FeatureStore:
    """Online and offline feature store for ML features."""

    def __init__(self):
        self._features: Dict[str, Feature] = {}
        self._groups: Dict[str, FeatureGroup] = {}
        self._online_store: Dict[str, Dict[str, Tuple[Any, float]]] = {}
        self._offline_store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register_feature(self, feature: Feature) -> None:
        """Register a feature definition."""
        with self._lock:
            self._features[feature.name] = feature

    def register_feature_group(self, group: FeatureGroup) -> None:
        """Register a feature group."""
        with self._lock:
            self._groups[group.name] = group
            for feature in group.features:
                self._features[feature.name] = feature

    def get_feature(self, name: str) -> Feature:
        """Get a feature definition by name."""
        if name not in self._features:
            raise KeyError(f"Feature {name} not found")
        return self._features[name]

    def get_feature_group(self, name: str) -> FeatureGroup:
        """Get a feature group by name."""
        if name not in self._groups:
            raise KeyError(f"Feature group {name} not found")
        return self._groups[name]

    def list_features(self) -> List[str]:
        """List all registered feature names."""
        return list(self._features.keys())

    def list_feature_groups(self) -> List[str]:
        """List all registered feature group names."""
        return list(self._groups.keys())

    def put_online(
        self,
        entity_id: str,
        features: Dict[str, Any],
        group_name: Optional[str] = None,
    ) -> None:
        """Write features to the online store.

        Args:
            entity_id: Unique entity identifier (e.g., user_id).
            features: Feature values keyed by feature name.
            group_name: Optional group to validate against.
        """
        if group_name:
            group = self.get_feature_group(group_name)
            valid, errors = group.validate_record(features)
            if not valid:
                raise ValueError(f"Validation failed: {'; '.join(errors)}")

        with self._lock:
            if entity_id not in self._online_store:
                self._online_store[entity_id] = {}
            for name, value in features.items():
                if name not in self._features:
                    raise KeyError(f"Feature {name} not registered")
                self._online_store[entity_id][name] = (value, time.time())

    def get_online(
        self,
        entity_id: str,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Read features from the online store.

        Args:
            entity_id: Entity identifier.
            feature_names: Optional list of features to retrieve. If None, returns all.

        Returns:
            Dictionary of feature values.
        """
        with self._lock:
            if entity_id not in self._online_store:
                return {}
            entity_features = self._online_store[entity_id]
            if feature_names is None:
                return {k: v[0] for k, v in entity_features.items()}
            result = {}
            for name in feature_names:
                if name in entity_features:
                    result[name] = entity_features[name][0]
            return result

    def get_online_with_ttl(
        self,
        entity_id: str,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Read features from online store, respecting TTL."""
        with self._lock:
            if entity_id not in self._online_store:
                return {}
            entity_features = self._online_store[entity_id]
            current_time = time.time()
            result = {}
            names = feature_names if feature_names else list(entity_features.keys())
            for name in names:
                if name in entity_features:
                    value, timestamp = entity_features[name]
                    feature_def = self._features.get(name)
                    if feature_def and feature_def.ttl_seconds:
                        if current_time - timestamp > feature_def.ttl_seconds:
                            continue  # Expired
                    result[name] = value
            return result

    def put_offline(
        self,
        entity_id: str,
        features: Dict[str, Any],
        group_name: Optional[str] = None,
    ) -> None:
        """Write features to the offline store (for training)."""
        if group_name:
            group = self.get_feature_group(group_name)
            valid, errors = group.validate_record(features)
            if not valid:
                raise ValueError(f"Validation failed: {'; '.join(errors)}")

        with self._lock:
            self._offline_store[entity_id] = dict(features)

    def get_offline(self, entity_id: str) -> Dict[str, Any]:
        """Read features from the offline store."""
        with self._lock:
            return dict(self._offline_store.get(entity_id, {}))

    def get_offline_batch(self, entity_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Read features for multiple entities from offline store."""
        with self._lock:
            return {
                eid: dict(self._offline_store[eid])
                for eid in entity_ids
                if eid in self._offline_store
            }

    def delete_online(self, entity_id: str, feature_names: Optional[List[str]] = None) -> None:
        """Delete features from the online store."""
        with self._lock:
            if entity_id in self._online_store:
                if feature_names is None:
                    del self._online_store[entity_id]
                else:
                    for name in feature_names:
                        self._online_store[entity_id].pop(name, None)

    def delete_offline(self, entity_id: str) -> None:
        """Delete features from the offline store."""
        with self._lock:
            self._offline_store.pop(entity_id, None)

    def get_feature_vector(
        self,
        entity_id: str,
        feature_names: List[str],
        fill_missing: bool = True,
    ) -> List[float]:
        """Get a feature vector for model input.

        Args:
            entity_id: Entity identifier.
            feature_names: Ordered list of feature names.
            fill_missing: If True, fill missing features with default values.

        Returns:
            List of feature values in the specified order.
        """
        online_features = self.get_online(entity_id)
        vector = []
        for name in feature_names:
            if name in online_features:
                vector.append(float(online_features[name]))
            elif fill_missing and name in self._features:
                default = self._features[name].default_value
                vector.append(float(default) if default is not None else 0.0)
            else:
                vector.append(0.0)
        return vector

    def compute_feature_stats(self, feature_name: str) -> Dict[str, Any]:
        """Compute statistics for a feature across all entities in offline store."""
        with self._lock:
            values = []
            for entity_features in self._offline_store.values():
                if feature_name in entity_features:
                    val = entity_features[feature_name]
                    if isinstance(val, (int, float)):
                        values.append(float(val))

            if not values:
                return {"count": 0}

            values.sort()
            n = len(values)
            mean = sum(values) / n
            variance = sum((v - mean) ** 2 for v in values) / n
            return {
                "count": n,
                "mean": mean,
                "std": variance ** 0.5,
                "min": values[0],
                "max": values[-1],
                "median": values[n // 2] if n % 2 == 1 else (values[n // 2 - 1] + values[n // 2]) / 2,
                "p25": values[n // 4],
                "p75": values[3 * n // 4],
            }

    def clear(self) -> None:
        """Clear all stored data."""
        with self._lock:
            self._online_store.clear()
            self._offline_store.clear()
