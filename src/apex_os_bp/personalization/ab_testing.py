"""A/B testing framework for personalization."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Variant:
    """A single variant in an A/B test.

    Attributes:
        variant_id: Unique identifier for the variant.
        name: Human-readable name.
        weight: Traffic allocation weight (0.0 to 1.0).
        configuration: Variant-specific configuration data.
    """

    variant_id: str
    name: str
    weight: float = 0.5
    configuration: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize variant to dictionary."""
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "weight": self.weight,
            "configuration": dict(self.configuration),
        }


@dataclass
class Experiment:
    """An A/B test experiment.

    Attributes:
        experiment_id: Unique identifier for the experiment.
        name: Human-readable experiment name.
        variants: List of variants in the experiment.
        status: Experiment status ('draft', 'running', 'paused', 'completed').
        start_time: When the experiment started.
        end_time: When the experiment ended (None if still running).
        metadata: Additional experiment metadata.
    """

    experiment_id: str
    name: str
    variants: list[Variant] = field(default_factory=list)
    status: str = "draft"
    start_time: float | None = None
    end_time: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_variant(self, variant_id: str) -> Variant | None:
        """Get a variant by ID."""
        for v in self.variants:
            if v.variant_id == variant_id:
                return v
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize experiment to dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "variants": [v.to_dict() for v in self.variants],
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metadata": dict(self.metadata),
        }


class ABTestManager:
    """Manages A/B test experiments and variant assignments."""

    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}
        self._assignments: dict[str, dict[str, str]] = {}
        self._conversions: dict[str, dict[str, list[float]]] = {}

    def create_experiment(
        self,
        experiment_id: str,
        name: str,
        variants: list[Variant],
        metadata: dict[str, Any] | None = None,
    ) -> Experiment:
        """Create a new experiment."""
        if experiment_id in self._experiments:
            raise ValueError(f"Experiment already exists: {experiment_id}")
        exp = Experiment(
            experiment_id=experiment_id,
            name=name,
            variants=variants,
            metadata=metadata or {},
        )
        self._experiments[experiment_id] = exp
        self._assignments[experiment_id] = {}
        self._conversions[experiment_id] = {
            v.variant_id: [] for v in variants
        }
        return exp

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Get an experiment by ID."""
        return self._experiments.get(experiment_id)

    def start_experiment(self, experiment_id: str) -> None:
        """Start an experiment."""
        exp = self._experiments.get(experiment_id)
        if exp is None:
            raise KeyError(f"Experiment not found: {experiment_id}")
        exp.status = "running"
        exp.start_time = time.time()

    def pause_experiment(self, experiment_id: str) -> None:
        """Pause a running experiment."""
        exp = self._experiments.get(experiment_id)
        if exp is None:
            raise KeyError(f"Experiment not found: {experiment_id}")
        exp.status = "paused"

    def complete_experiment(self, experiment_id: str) -> None:
        """Complete an experiment."""
        exp = self._experiments.get(experiment_id)
        if exp is None:
            raise KeyError(f"Experiment not found: {experiment_id}")
        exp.status = "completed"
        exp.end_time = time.time()

    def assign_variant(self, experiment_id: str, user_id: str) -> str | None:
        """Assign a user to a variant using consistent hashing.

        Returns the assigned variant ID or None if experiment not found.
        """
        exp = self._experiments.get(experiment_id)
        if exp is None or exp.status != "running":
            return None

        if user_id in self._assignments.get(experiment_id, {}):
            return self._assignments[experiment_id][user_id]

        variant_id = self._hash_assign(user_id, exp)
        if experiment_id not in self._assignments:
            self._assignments[experiment_id] = {}
        self._assignments[experiment_id][user_id] = variant_id
        return variant_id

    def get_assignment(self, experiment_id: str, user_id: str) -> str | None:
        """Get the variant assigned to a user."""
        return self._assignments.get(experiment_id, {}).get(user_id)

    def track_conversion(
        self, experiment_id: str, variant_id: str, value: float = 1.0
    ) -> None:
        """Track a conversion event for a variant."""
        if experiment_id in self._conversions:
            if variant_id in self._conversions[experiment_id]:
                self._conversions[experiment_id][variant_id].append(value)

    def get_conversion_data(
        self, experiment_id: str
    ) -> dict[str, dict[str, float | int]]:
        """Get conversion statistics for an experiment.

        Returns per-variant: {count, total, mean}.
        """
        result: dict[str, dict[str, float | int]] = {}
        conversions = self._conversions.get(experiment_id, {})
        for variant_id, values in conversions.items():
            count = len(values)
            total = sum(values)
            mean = total / count if count > 0 else 0.0
            result[variant_id] = {"count": count, "total": total, "mean": mean}
        return result

    def _hash_assign(self, user_id: str, exp: Experiment) -> str:
        """Deterministically assign a user to a variant using hashing."""
        hash_input = f"{exp.experiment_id}:{user_id}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_val % 10000) / 10000.0

        cumulative = 0.0
        for variant in exp.variants:
            cumulative += variant.weight
            if bucket < cumulative:
                return variant.variant_id
        return exp.variants[-1].variant_id if exp.variants else ""

    def list_experiments(self) -> list[Experiment]:
        """Return all experiments."""
        return list(self._experiments.values())

    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete an experiment. Returns True if deleted."""
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            self._assignments.pop(experiment_id, None)
            self._conversions.pop(experiment_id, None)
            return True
        return False
