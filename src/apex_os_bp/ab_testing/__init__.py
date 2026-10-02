"""A/B Testing System for APEX-OS Business Platform.

Provides experiment management, traffic splitting, statistical analysis,
experiment reporting, and auto-optimization capabilities.
"""

from .models import (
    ExperimentStatus,
    MetricType,
    Variant,
    Experiment,
    ExperimentResult,
    Assignment,
)
from .experiment import (
    ExperimentManager,
    ExperimentValidationError,
    ExperimentNotFoundError,
)
from .traffic_splitter import TrafficSplitter
from .statistics import StatisticalAnalyzer, StatisticalResult
from .reporting import ReportGenerator, ExperimentReport
from .auto_optimization import AutoOptimizer, OptimizationAction

__all__ = [
    "ExperimentStatus",
    "MetricType",
    "Variant",
    "Experiment",
    "ExperimentResult",
    "Assignment",
    "ExperimentManager",
    "ExperimentValidationError",
    "ExperimentNotFoundError",
    "TrafficSplitter",
    "StatisticalAnalyzer",
    "StatisticalResult",
    "ReportGenerator",
    "ExperimentReport",
    "AutoOptimizer",
    "OptimizationAction",
]
