"""Data models for the A/B testing system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ExperimentStatus(str, Enum):
    """Lifecycle status of an experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MetricType(str, Enum):
    """Supported metric types for experiment evaluation."""

    CONVERSION = "conversion"
    REVENUE = "revenue"
    CLICK = "click"
    CUSTOM = "custom"


@dataclass
class Variant:
    """A single variant (treatment or control) within an experiment."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    traffic_allocation: float = 50.0  # percentage 0-100
    config: Dict[str, Any] = field(default_factory=dict)
    is_control: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Variant name cannot be empty")
        if not 0 <= self.traffic_allocation <= 100:
            raise ValueError(
                f"Traffic allocation must be between 0 and 100, got {self.traffic_allocation}"
            )


@dataclass
class Experiment:
    """An A/B test experiment definition."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    variants: List[Variant] = field(default_factory=list)
    primary_metric: MetricType = MetricType.CONVERSION
    secondary_metrics: List[MetricType] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    min_sample_size: int = 100
    confidence_level: float = 0.95

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Experiment name cannot be empty")
        if len(self.variants) < 2:
            raise ValueError("Experiment must have at least 2 variants")
        if not 0 < self.confidence_level < 1:
            raise ValueError("Confidence level must be between 0 and 1")

    @property
    def control_variant(self) -> Optional[Variant]:
        """Return the control variant, or None if not set."""
        for v in self.variants:
            if v.is_control:
                return v
        return self.variants[0] if self.variants else None

    @property
    def treatment_variants(self) -> List[Variant]:
        """Return all non-control variants."""
        control = self.control_variant
        return [v for v in self.variants if v.id != control.id] if control else []

    @property
    def total_traffic_allocation(self) -> float:
        """Sum of all variant traffic allocations."""
        return sum(v.traffic_allocation for v in self.variants)

    def validate_traffic_allocation(self, tolerance: float = 0.01) -> bool:
        """Check that traffic allocations sum to ~100%."""
        return abs(self.total_traffic_allocation - 100.0) <= tolerance

    def get_variant(self, variant_id: str) -> Optional[Variant]:
        """Look up a variant by ID."""
        for v in self.variants:
            if v.id == variant_id:
                return v
        return None


@dataclass
class ExperimentResult:
    """Aggregated results for a single variant in an experiment."""

    experiment_id: str = ""
    variant_id: str = ""
    variant_name: str = ""
    visitors: int = 0
    conversions: int = 0
    revenue: float = 0.0
    clicks: int = 0
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def conversion_rate(self) -> float:
        """Conversion rate as a fraction (0-1)."""
        if self.visitors == 0:
            return 0.0
        return self.conversions / self.visitors

    @property
    def revenue_per_visitor(self) -> float:
        """Average revenue per visitor."""
        if self.visitors == 0:
            return 0.0
        return self.revenue / self.visitors

    @property
    def click_rate(self) -> float:
        """Click-through rate as a fraction (0-1)."""
        if self.visitors == 0:
            return 0.0
        return self.clicks / self.visitors


@dataclass
class Assignment:
    """A traffic assignment of a user to a variant."""

    experiment_id: str = ""
    user_id: str = ""
    variant_id: str = ""
    variant_name: str = ""
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bucket: int = 0  # hash bucket 0-9999
