"""Personalization analytics and reporting."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from apex_os_bp.personalization.ab_testing import ABTestManager
from apex_os_bp.personalization.behavior import BehaviorTracker
from apex_os_bp.personalization.profiles import ProfileStore


@dataclass
class EngagementScore:
    """Engagement score for a user.

    Attributes:
        user_id: The user identifier.
        score: Computed engagement score (0-100).
        factors: Breakdown of score components.
        computed_at: When the score was computed.
    """

    user_id: str
    score: float
    factors: dict[str, float] = field(default_factory=dict)
    computed_at: float = field(default_factory=time.time)


class PersonalizationAnalytics:
    """Computes analytics for the personalization system."""

    def __init__(
        self,
        profile_store: ProfileStore,
        behavior_tracker: BehaviorTracker,
        ab_test_manager: ABTestManager | None = None,
    ) -> None:
        self._profiles = profile_store
        self._behavior = behavior_tracker
        self._ab = ab_test_manager

    def compute_engagement_score(self, user_id: str) -> EngagementScore:
        """Compute an engagement score for a user.

        Score components:
        - event_count: Based on total events (max 30 points)
        - event_diversity: Based on unique event types (max 20 points)
        - recency: Based on time since last event (max 25 points)
        - session_count: Based on unique sessions (max 25 points)
        """
        events = self._behavior.get_user_events(user_id)
        if not events:
            return EngagementScore(user_id=user_id, score=0.0)

        event_count = len(events)
        event_count_score = min(event_count / 10.0, 1.0) * 30.0

        event_types = set(e.event_type for e in events)
        diversity_score = min(len(event_types) / 5.0, 1.0) * 20.0

        last_event = self._behavior.get_last_event(user_id)
        if last_event:
            hours_since = (time.time() - last_event.timestamp) / 3600.0
            recency_score = max(0.0, 25.0 - hours_since)
        else:
            recency_score = 0.0

        sessions = set(
            e.session_id for e in events if e.session_id is not None
        )
        session_score = min(len(sessions) / 5.0, 1.0) * 25.0

        total = event_count_score + diversity_score + recency_score + session_score
        total = min(max(total, 0.0), 100.0)

        return EngagementScore(
            user_id=user_id,
            score=round(total, 2),
            factors={
                "event_count": round(event_count_score, 2),
                "event_diversity": round(diversity_score, 2),
                "recency": round(recency_score, 2),
                "session_count": round(session_score, 2),
            },
        )

    def get_segment_distribution(self) -> dict[str, int]:
        """Get the distribution of users across segments."""
        distribution: dict[str, int] = {}
        for profile in self._profiles.list_all():
            for segment in profile.segments:
                distribution[segment] = distribution.get(segment, 0) + 1
        return distribution

    def get_top_preferences(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get the most common preference keys across all users."""
        pref_counts: dict[str, int] = {}
        for profile in self._profiles.list_all():
            for key in profile.preferences:
                pref_counts[key] = pref_counts.get(key, 0) + 1
        sorted_prefs = sorted(pref_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_prefs[:limit]

    def get_experiment_summary(
        self, experiment_id: str
    ) -> dict[str, Any] | None:
        """Get a summary of an A/B test experiment.

        Returns experiment info with per-variant conversion stats.
        """
        if self._ab is None:
            return None
        exp = self._ab.get_experiment(experiment_id)
        if exp is None:
            return None

        conversion_data = self._ab.get_conversion_data(experiment_id)
        variants_summary = []
        for v in exp.variants:
            stats = conversion_data.get(v.variant_id, {"count": 0, "total": 0, "mean": 0})
            variants_summary.append(
                {
                    "variant_id": v.variant_id,
                    "name": v.name,
                    "weight": v.weight,
                    "conversions": stats["count"],
                    "total_value": stats["total"],
                    "mean_value": stats["mean"],
                }
            )

        return {
            "experiment_id": exp.experiment_id,
            "name": exp.name,
            "status": exp.status,
            "variants": variants_summary,
        }

    def get_overall_metrics(self) -> dict[str, Any]:
        """Get overall personalization system metrics."""
        total_users = self._profiles.count()
        total_events = self._behavior.get_event_count()
        segment_dist = self.get_segment_distribution()

        event_types: dict[str, int] = {}
        for profile in self._profiles.list_all():
            user_events = self._behavior.get_user_events(profile.user_id)
            for e in user_events:
                event_types[e.event_type] = event_types.get(e.event_type, 0) + 1

        return {
            "total_users": total_users,
            "total_events": total_events,
            "segments": segment_dist,
            "event_types": event_types,
            "avg_events_per_user": (
                total_events / total_users if total_users > 0 else 0.0
            ),
        }
