"""Analytics engine — tracks flag evaluation metrics."""

from __future__ import annotations

from typing import Dict

from .models import FlagAnalytics


class AnalyticsEngine:
    """Manages analytics data for feature flags."""

    def get_hit_rate(self, analytics: FlagAnalytics) -> float:
        """Get the hit rate for a flag."""
        return analytics.hit_rate

    def get_summary(self, analytics: FlagAnalytics) -> Dict[str, object]:
        """Get a summary of analytics for a flag."""
        return {
            "flag_name": analytics.flag_name,
            "evaluations": analytics.evaluations,
            "hits": analytics.hits,
            "misses": analytics.misses,
            "hit_rate": analytics.hit_rate,
            "unique_users": len(analytics.unique_users),
            "last_evaluated_at": analytics.last_evaluated_at,
        }

    def get_daily_summary(self, analytics: FlagAnalytics) -> Dict[str, int]:
        """Get daily evaluation counts."""
        return dict(analytics.daily_counts)
