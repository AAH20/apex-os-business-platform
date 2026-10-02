"""Feature flag system for APEX-OS Business Platform.

Provides flag management, targeting rules, gradual rollout,
analytics, and dependency tracking.
"""

from .models import (
    Flag,
    FlagState,
    TargetingRule,
    RolloutConfig,
    RolloutStrategy,
    FlagAnalytics,
    FlagDependency,
)
from .manager import FeatureFlagManager
from .targeting import TargetingEngine
from .rollout import RolloutEngine
from .analytics import AnalyticsEngine
from .dependencies import DependencyEngine

__all__ = [
    "Flag",
    "FlagState",
    "TargetingRule",
    "RolloutConfig",
    "RolloutStrategy",
    "FlagAnalytics",
    "FlagDependency",
    "FeatureFlagManager",
    "TargetingEngine",
    "RolloutEngine",
    "AnalyticsEngine",
    "DependencyEngine",
]
