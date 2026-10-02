"""Cost optimization module."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class CostItem:
    """Represents a cost item."""

    resource: str
    quantity: float
    unit_cost: float

    def __post_init__(self):
        if self.quantity < 0:
            raise ValueError(f"Quantity for {self.resource} cannot be negative")
        if self.unit_cost < 0:
            raise ValueError(f"Unit cost for {self.resource} cannot be negative")


@dataclass
class CostOptimizationResult:
    """Result of cost optimization analysis."""

    current_cost: float
    optimized_cost: float
    savings: float
    savings_percent: float
    recommendations: List[str] = field(default_factory=list)


def calculate_total_cost(items: List[CostItem]) -> float:
    """Calculate total cost for a list of cost items.

    Args:
        items: List of cost items.

    Returns:
        Total cost.
    """
    return sum(item.quantity * item.unit_cost for item in items)


def optimize_costs(
    current_items: List[CostItem],
    demand_forecast: float,
    utilization_threshold: float = 0.8,
) -> CostOptimizationResult:
    """Optimize costs based on current allocation and demand forecast.

    Args:
        current_items: Current cost items.
        demand_forecast: Forecasted demand.
        utilization_threshold: Target utilization threshold.

    Returns:
        CostOptimizationResult with optimization recommendations.
    """
    if not current_items:
        raise ValueError("Current items cannot be empty")
    if demand_forecast < 0:
        raise ValueError("Demand forecast cannot be negative")

    current_cost = calculate_total_cost(current_items)
    total_quantity = sum(item.quantity for item in current_items)

    if total_quantity == 0:
        return CostOptimizationResult(
            current_cost=current_cost,
            optimized_cost=0.0,
            savings=current_cost,
            savings_percent=100.0,
            recommendations=["All resources are idle — consider decommissioning"],
        )

    current_util = demand_forecast / total_quantity if total_quantity > 0 else 0

    recommendations = []
    optimized_items = []

    if current_util < utilization_threshold:
        # Over-provisioned — recommend downsizing
        scale_factor = (
            demand_forecast / (total_quantity * utilization_threshold)
            if total_quantity * utilization_threshold > 0
            else 1.0
        )
        for item in current_items:
            new_qty = item.quantity * scale_factor
            optimized_items.append(
                CostItem(resource=item.resource, quantity=new_qty, unit_cost=item.unit_cost)
            )
        recommendations.append(
            f"Downsize resources by {(1 - scale_factor):.1%} to match demand forecast"
        )
    elif current_util > 0.95:
        # Under-provisioned — recommend upsizing
        scale_factor = (
            demand_forecast / (total_quantity * utilization_threshold)
            if total_quantity * utilization_threshold > 0
            else 1.0
        )
        for item in current_items:
            new_qty = item.quantity * scale_factor
            optimized_items.append(
                CostItem(resource=item.resource, quantity=new_qty, unit_cost=item.unit_cost)
            )
        recommendations.append(
            f"Upsize resources by {(scale_factor - 1):.1%} to meet demand forecast"
        )
    else:
        optimized_items = current_items
        recommendations.append("Current allocation is well-matched to demand")

    optimized_cost = calculate_total_cost(optimized_items)
    savings = current_cost - optimized_cost
    savings_percent = (savings / current_cost * 100) if current_cost > 0 else 0.0

    return CostOptimizationResult(
        current_cost=current_cost,
        optimized_cost=optimized_cost,
        savings=savings,
        savings_percent=savings_percent,
        recommendations=recommendations,
    )


def rightsizing_savings(
    current_items: List[CostItem], recommended_items: List[CostItem]
) -> float:
    """Calculate savings from rightsizing.

    Args:
        current_items: Current cost items.
        recommended_items: Recommended cost items after rightsizing.

    Returns:
        Savings amount (never negative).
    """
    current_cost = calculate_total_cost(current_items)
    recommended_cost = calculate_total_cost(recommended_items)
    return max(0.0, current_cost - recommended_cost)