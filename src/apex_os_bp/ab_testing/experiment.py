"""Experiment management: CRUD operations and lifecycle control."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Experiment, ExperimentStatus, MetricType, Variant


class ExperimentValidationError(Exception):
    """Raised when experiment validation fails."""


class ExperimentNotFoundError(Exception):
    """Raised when an experiment is not found."""


class ExperimentManager:
    """Manages the full lifecycle of A/B test experiments."""

    def __init__(self) -> None:
        self._experiments: Dict[str, Experiment] = {}
        self._name_index: Dict[str, str] = {}  # name -> id

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        name: str,
        description: str = "",
        variants: Optional[List[Variant]] = None,
        primary_metric: MetricType = MetricType.CONVERSION,
        secondary_metrics: Optional[List[MetricType]] = None,
        min_sample_size: int = 100,
        confidence_level: float = 0.95,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Experiment:
        """Create a new experiment in DRAFT status.

        Args:
            name: Unique experiment name.
            description: Human-readable description.
            variants: List of variants (at least 2 required).
            primary_metric: The main metric for evaluation.
            secondary_metrics: Additional metrics to track.
            min_sample_size: Minimum visitors per variant before results
                are considered reliable.
            confidence_level: Statistical confidence level (0-1).
            metadata: Arbitrary key-value metadata.

        Returns:
            The newly created Experiment.

        Raises:
            ExperimentValidationError: If validation fails.
        """
        if not name or not name.strip():
            raise ExperimentValidationError("Experiment name is required")

        if name in self._name_index:
            raise ExperimentValidationError(
                f"Experiment with name '{name}' already exists"
            )

        if variants is None:
            variants = [
                Variant(name="control", traffic_allocation=50.0, is_control=True),
                Variant(name="treatment", traffic_allocation=50.0),
            ]

        if len(variants) < 2:
            raise ExperimentValidationError(
                "At least 2 variants are required for an A/B test"
            )

        # Validate traffic allocation sums to ~100%
        total = sum(v.traffic_allocation for v in variants)
        if abs(total - 100.0) > 0.01:
            raise ExperimentValidationError(
                f"Variant traffic allocations must sum to 100%, got {total}%"
            )

        # Ensure exactly one control
        control_count = sum(1 for v in variants if v.is_control)
        if control_count == 0:
            variants[0].is_control = True
        elif control_count > 1:
            raise ExperimentValidationError(
                "Exactly one variant must be marked as control"
            )

        # Ensure unique variant names
        names = [v.name for v in variants]
        if len(names) != len(set(names)):
            raise ExperimentValidationError("Variant names must be unique")

        experiment = Experiment(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            status=ExperimentStatus.DRAFT,
            variants=variants,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics or [],
            min_sample_size=min_sample_size,
            confidence_level=confidence_level,
            metadata=metadata or {},
        )

        self._experiments[experiment.id] = experiment
        self._name_index[experiment.name] = experiment.id
        return experiment

    def get_experiment(self, experiment_id: str) -> Experiment:
        """Retrieve an experiment by ID.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
        """
        if experiment_id not in self._experiments:
            raise ExperimentNotFoundError(
                f"Experiment '{experiment_id}' not found"
            )
        return self._experiments[experiment_id]

    def get_experiment_by_name(self, name: str) -> Experiment:
        """Retrieve an experiment by name.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
        """
        if name not in self._name_index:
            raise ExperimentNotFoundError(f"Experiment '{name}' not found")
        return self._experiments[self._name_index[name]]

    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
    ) -> List[Experiment]:
        """List all experiments, optionally filtered by status."""
        experiments = list(self._experiments.values())
        if status is not None:
            experiments = [e for e in experiments if e.status == status]
        return experiments

    def update_experiment(
        self,
        experiment_id: str,
        **kwargs: Any,
    ) -> Experiment:
        """Update experiment fields.

        Only DRAFT experiments can be modified. Running experiments
        must be paused first.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
            ExperimentValidationError: If the experiment is not in DRAFT.
        """
        exp = self.get_experiment(experiment_id)

        if exp.status != ExperimentStatus.DRAFT:
            raise ExperimentValidationError(
                f"Cannot update experiment in {exp.status.value} status. "
                "Only DRAFT experiments can be modified."
            )

        allowed_fields = {
            "name", "description", "primary_metric",
            "secondary_metrics", "min_sample_size",
            "confidence_level", "metadata",
        }

        old_name = exp.name
        for key, value in kwargs.items():
            if key not in allowed_fields:
                raise ExperimentValidationError(
                    f"Cannot update field '{key}'"
                )
            setattr(exp, key, value)

        # Update name index if name changed
        if "name" in kwargs and kwargs["name"] != old_name:
            if kwargs["name"] in self._name_index:
                raise ExperimentValidationError(
                    f"Experiment name '{kwargs['name']}' already in use"
                )
            del self._name_index[old_name]
            self._name_index[exp.name] = exp.id

        exp.updated_at = datetime.now(timezone.utc)
        return exp

    def delete_experiment(self, experiment_id: str) -> None:
        """Delete an experiment permanently.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
        """
        exp = self.get_experiment(experiment_id)
        del self._experiments[experiment_id]
        del self._name_index[exp.name]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_experiment(self, experiment_id: str) -> Experiment:
        """Transition an experiment from DRAFT/PAUSED to RUNNING.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
            ExperimentValidationError: If the experiment cannot be started.
        """
        exp = self.get_experiment(experiment_id)

        if exp.status == ExperimentStatus.RUNNING:
            raise ExperimentValidationError("Experiment is already running")
        if exp.status in (ExperimentStatus.COMPLETED, ExperimentStatus.ARCHIVED):
            raise ExperimentValidationError(
                f"Cannot start experiment in {exp.status.value} status"
            )
        if not exp.validate_traffic_allocation():
            raise ExperimentValidationError(
                "Traffic allocations must sum to 100% before starting"
            )

        exp.status = ExperimentStatus.RUNNING
        exp.start_time = datetime.now(timezone.utc)
        exp.updated_at = datetime.now(timezone.utc)
        return exp

    def pause_experiment(self, experiment_id: str) -> Experiment:
        """Pause a running experiment.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
            ExperimentValidationError: If the experiment is not running.
        """
        exp = self.get_experiment(experiment_id)

        if exp.status != ExperimentStatus.RUNNING:
            raise ExperimentValidationError(
                f"Cannot pause experiment in {exp.status.value} status"
            )

        exp.status = ExperimentStatus.PAUSED
        exp.updated_at = datetime.now(timezone.utc)
        return exp

    def resume_experiment(self, experiment_id: str) -> Experiment:
        """Resume a paused experiment.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
            ExperimentValidationError: If the experiment is not paused.
        """
        exp = self.get_experiment(experiment_id)

        if exp.status != ExperimentStatus.PAUSED:
            raise ExperimentValidationError(
                f"Cannot resume experiment in {exp.status.value} status"
            )

        exp.status = ExperimentStatus.RUNNING
        exp.updated_at = datetime.now(timezone.utc)
        return exp

    def complete_experiment(self, experiment_id: str) -> Experiment:
        """Mark an experiment as completed.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
        """
        exp = self.get_experiment(experiment_id)

        if exp.status == ExperimentStatus.ARCHIVED:
            raise ExperimentValidationError("Experiment is already archived")

        exp.status = ExperimentStatus.COMPLETED
        exp.end_time = datetime.now(timezone.utc)
        exp.updated_at = datetime.now(timezone.utc)
        return exp

    def archive_experiment(self, experiment_id: str) -> Experiment:
        """Archive an experiment (soft-delete).

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
        """
        exp = self.get_experiment(experiment_id)
        exp.status = ExperimentStatus.ARCHIVED
        exp.updated_at = datetime.now(timezone.utc)
        return exp

    # ------------------------------------------------------------------
    # Variant management
    # ------------------------------------------------------------------

    def add_variant(
        self,
        experiment_id: str,
        name: str,
        traffic_allocation: float,
        config: Optional[Dict[str, Any]] = None,
        is_control: bool = False,
    ) -> Experiment:
        """Add a variant to a DRAFT experiment.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
            ExperimentValidationError: If validation fails.
        """
        exp = self.get_experiment(experiment_id)

        if exp.status != ExperimentStatus.DRAFT:
            raise ExperimentValidationError(
                "Variants can only be added to DRAFT experiments"
            )

        new_total = exp.total_traffic_allocation + traffic_allocation
        if new_total > 100.0 + 0.01:
            raise ExperimentValidationError(
                f"Total traffic allocation would exceed 100% (would be {new_total}%)"
            )

        variant = Variant(
            name=name,
            traffic_allocation=traffic_allocation,
            config=config or {},
            is_control=is_control,
        )
        exp.variants.append(variant)
        exp.updated_at = datetime.now(timezone.utc)
        return exp

    def remove_variant(self, experiment_id: str, variant_id: str) -> Experiment:
        """Remove a variant from a DRAFT experiment.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
            ExperimentValidationError: If validation fails.
        """
        exp = self.get_experiment(experiment_id)

        if exp.status != ExperimentStatus.DRAFT:
            raise ExperimentValidationError(
                "Variants can only be removed from DRAFT experiments"
            )

        if len(exp.variants) <= 2:
            raise ExperimentValidationError(
                "Cannot remove variant: at least 2 variants required"
            )

        target = exp.get_variant(variant_id)
        if target is None:
            raise ExperimentValidationError(
                f"Variant '{variant_id}' not found in experiment"
            )

        exp.variants = [v for v in exp.variants if v.id != variant_id]
        exp.updated_at = datetime.now(timezone.utc)
        return exp

    def update_variant_traffic(
        self,
        experiment_id: str,
        variant_id: str,
        new_allocation: float,
    ) -> Experiment:
        """Update a variant's traffic allocation in a DRAFT experiment.

        Raises:
            ExperimentNotFoundError: If the experiment does not exist.
            ExperimentValidationError: If validation fails.
        """
        exp = self.get_experiment(experiment_id)

        if exp.status != ExperimentStatus.DRAFT:
            raise ExperimentValidationError(
                "Traffic can only be updated on DRAFT experiments"
            )

        variant = exp.get_variant(variant_id)
        if variant is None:
            raise ExperimentValidationError(
                f"Variant '{variant_id}' not found in experiment"
            )

        old_allocation = variant.traffic_allocation
        new_total = exp.total_traffic_allocation - old_allocation + new_allocation

        if abs(new_total - 100.0) > 0.01:
            raise ExperimentValidationError(
                f"Total traffic allocation must remain 100% (would be {new_total}%)"
            )

        variant.traffic_allocation = new_allocation
        exp.updated_at = datetime.now(timezone.utc)
        return exp

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def clone_experiment(
        self,
        experiment_id: str,
        new_name: str,
    ) -> Experiment:
        """Clone an existing experiment (as DRAFT) with a new name.

        Raises:
            ExperimentNotFoundError: If the source experiment does not exist.
            ExperimentValidationError: If the new name is already in use.
        """
        source = self.get_experiment(experiment_id)

        if new_name in self._name_index:
            raise ExperimentValidationError(
                f"Experiment name '{new_name}' already in use"
            )

        cloned_variants = [
            Variant(
                name=v.name,
                traffic_allocation=v.traffic_allocation,
                config=copy.deepcopy(v.config),
                is_control=v.is_control,
            )
            for v in source.variants
        ]

        return self.create_experiment(
            name=new_name,
            description=source.description,
            variants=cloned_variants,
            primary_metric=source.primary_metric,
            secondary_metrics=list(source.secondary_metrics),
            min_sample_size=source.min_sample_size,
            confidence_level=source.confidence_level,
            metadata=copy.deepcopy(source.metadata),
        )

    def get_experiment_count(self) -> int:
        """Return the total number of experiments."""
        return len(self._experiments)

    def clear_all(self) -> None:
        """Remove all experiments (useful for testing)."""
        self._experiments.clear()
        self._name_index.clear()
