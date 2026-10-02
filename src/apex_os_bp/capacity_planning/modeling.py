"""Capacity modeling module."""

from dataclasses import dataclass, field
from typing import List, Dict
import datetime


@dataclass
class ResourceCapacity:
    """Represents a single resource's capacity."""

    name: str
    total: float
    used: float
    unit: str = "units"

    def __post_init__(self):
        if self.total <= 0:
            raise ValueError(f"Total capacity for {self.name} must be positive")
        if self.used < 0:
            raise ValueError(f"Used capacity for {self.name} cannot be negative")
        if self.used > self.total:
            raise ValueError(f"Used capacity for {self.name} cannot exceed total")


@dataclass
class CapacityReport:
    """Comprehensive capacity analysis report."""

    resources: List[ResourceCapacity]
    overall_utilization: float
    bottlenecks: List[str]
    headroom: Dict[str, float]
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())


def utilization_rate(used: float, total: float) -> float:
    """Calculate utilization rate as a ratio.

    Args:
        used: Currently used capacity.
        total: Total available capacity.

    Returns:
        Utilization rate between 0 and 1.
    """
    if total <= 0:
        raise ValueError("Total capacity must be positive")
    if used < 0:
        raise ValueError("Used capacity cannot be negative")
    return used / total


def headroom(total: float, used: float) -> float:
    """Calculate remaining headroom.

    Args:
        total: Total available capacity.
        used: Currently used capacity.

    Returns:
        Remaining headroom (never negative).
    """
    if total < 0:
        raise ValueError("Total capacity cannot be negative")
    if used < 0:
        raise ValueError("Used capacity cannot be negative")
    return max(0.0, total - used)


def analyze_capacity(
    resources: List[ResourceCapacity], bottleneck_threshold: float = 0.8
) -> CapacityReport:
    """Analyze capacity across all resources.

    Args:
        resources: List of resource capacities to analyze.
        bottleneck_threshold: Utilization rate above which a resource is
            considered a bottleneck.

    Returns:
        CapacityReport with analysis results.
    """
    if not resources:
        raise ValueError("Resources list cannot be empty")

    total_capacity = sum(r.total for r in resources)
    total_used = sum(r.used for r in resources)
    overall_util = total_used / total_capacity if total_capacity > 0 else 0.0

    bottlenecks = [
        r.name
        for r in resources
        if utilization_rate(r.used, r.total) >= bottleneck_threshold
    ]

    headroom_map = {r.name: headroom(r.total, r.used) for r in resources}

    return CapacityReport(
        resources=resources,
        overall_utilization=overall_util,
        bottlenecks=bottlenecks,
        headroom=headroom_map,
    )