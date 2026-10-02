"""APEX-OS Capacity Planning System."""

from .forecasting import forecast_demand, ForecastResult
from .modeling import (
    ResourceCapacity,
    CapacityReport,
    utilization_rate,
    headroom,
    analyze_capacity,
)
from .scaling import (
    ScalingRecommendation,
    recommend_scaling,
    calculate_required_capacity,
)
from .cost_optimization import (
    CostItem,
    CostOptimizationResult,
    calculate_total_cost,
    optimize_costs,
    rightsizing_savings,
)
from .alerts import (
    AlertSeverity,
    CapacityAlert,
    check_capacity_alerts,
    format_alert,
)

__all__ = [
    "forecast_demand",
    "ForecastResult",
    "ResourceCapacity",
    "CapacityReport",
    "utilization_rate",
    "headroom",
    "analyze_capacity",
    "ScalingRecommendation",
    "recommend_scaling",
    "calculate_required_capacity",
    "CostItem",
    "CostOptimizationResult",
    "calculate_total_cost",
    "optimize_costs",
    "rightsizing_savings",
    "AlertSeverity",
    "CapacityAlert",
    "check_capacity_alerts",
    "format_alert",
]