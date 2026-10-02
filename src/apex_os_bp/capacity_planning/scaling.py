"""Scaling recommendations module."""

from dataclasses import dataclass


@dataclass
class ScalingRecommendation:
    """A scaling recommendation."""

    action: str  # 'scale_up', 'scale_down', 'maintain'
    current_capacity: float
    recommended_capacity: float
    reason: str
    urgency: str  # 'low', 'medium', 'high'


def calculate_required_capacity(demand: float, target_utilization: float = 0.7) -> float:
    """Calculate required capacity to meet demand at target utilization.

    Args:
        demand: Expected demand.
        target_utilization: Target utilization rate (0-1).

    Returns:
        Required capacity.
    """
    if demand < 0:
        raise ValueError("Demand cannot be negative")
    if target_utilization <= 0 or target_utilization > 1:
        raise ValueError("Target utilization must be between 0 and 1")
    return demand / target_utilization


def recommend_scaling(
    current_capacity: float,
    forecasted_demand: float,
    target_utilization: float = 0.7,
    scale_up_threshold: float = 0.8,
    scale_down_threshold: float = 0.3,
) -> ScalingRecommendation:
    """Generate a scaling recommendation based on forecasted demand.

    Args:
        current_capacity: Current total capacity.
        forecasted_demand: Forecasted demand for the next period.
        target_utilization: Target utilization rate.
        scale_up_threshold: Utilization above which to recommend scaling up.
        scale_down_threshold: Utilization below which to recommend scaling down.

    Returns:
        ScalingRecommendation with action and details.
    """
    if current_capacity <= 0:
        raise ValueError("Current capacity must be positive")
    if forecasted_demand < 0:
        raise ValueError("Forecasted demand cannot be negative")

    required = calculate_required_capacity(forecasted_demand, target_utilization)
    current_util = forecasted_demand / current_capacity if current_capacity > 0 else 0

    if current_util >= scale_up_threshold:
        urgency = "high" if current_util >= 0.95 else "medium"
        return ScalingRecommendation(
            action="scale_up",
            current_capacity=current_capacity,
            recommended_capacity=required,
            reason=f"Projected utilization {current_util:.1%} exceeds scale-up threshold {scale_up_threshold:.1%}",
            urgency=urgency,
        )
    elif current_util <= scale_down_threshold:
        return ScalingRecommendation(
            action="scale_down",
            current_capacity=current_capacity,
            recommended_capacity=required,
            reason=f"Projected utilization {current_util:.1%} below scale-down threshold {scale_down_threshold:.1%}",
            urgency="low",
        )
    else:
        return ScalingRecommendation(
            action="maintain",
            current_capacity=current_capacity,
            recommended_capacity=current_capacity,
            reason=f"Projected utilization {current_util:.1%} within acceptable range",
            urgency="low",
        )