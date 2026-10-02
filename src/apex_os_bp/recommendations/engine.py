"""Unified recommendation engine facade.

Provides a single entry point that orchestrates collaborative
filtering, content-based filtering, hybrid recommendations,
real-time recommendations, and A/B testing.
"""

from __future__ import annotations

from typing import Any

from .ab_testing import ABTestManager
from .collaborative_filtering import CollaborativeFilter
from .content_based import ContentBasedFilter
from .hybrid import HybridRecommender
from .real_time import RealTimeRecommender


class RecommendationEngine:
    """Unified recommendation engine for APEX-OS Business Platform.

    Usage
    -----
    >>> engine = RecommendationEngine()
    >>> engine.fit(interactions, items)
    >>> recs = engine.recommend("user_1", n=5)
    >>> rt_recs = engine.recommend_real_time("user_1", n=5)
    >>> ab_recs = engine.recommend_ab("exp_name", "user_1", n=5)
    """

    def __init__(self):
        self.cf: CollaborativeFilter | None = None
        self.cb: ContentBasedFilter | None = None
        self.hybrid: HybridRecommender | None = None
        self.real_time: RealTimeRecommender | None = None
        self.ab_manager = ABTestManager()
        self._interactions: list[dict[str, Any]] = []
        self._items: list[dict[str, Any]] = []

    def fit(
        self,
        interactions: list[dict[str, Any]],
        items: list[dict[str, Any]],
    ) -> "RecommendationEngine":
        """Train all recommendation models."""
        self._interactions = list(interactions)
        self._items = list(items)

        self.cf = CollaborativeFilter(method="svd").fit(interactions)
        self.cb = ContentBasedFilter().fit(items)
        self.hybrid = HybridRecommender().fit(interactions, items)
        self.real_time = RealTimeRecommender().fit(interactions, items)

        # Register recommenders for A/B testing
        self.ab_manager.register_recommender("cf", self.cf)
        self.ab_manager.register_recommender("cb", self.cb)
        self.ab_manager.register_recommender("hybrid", self.hybrid)
        self.ab_manager.register_recommender("real_time", self.real_time)

        return self

    def recommend(self, user_id: str, n: int = 10, method: str = "hybrid") -> list[dict[str, Any]]:
        """Get recommendations using the specified method."""
        if method == "collaborative":
            if self.cf is None:
                raise RuntimeError("Engine not fitted")
            return self.cf.recommend(user_id, n=n)
        if method == "content":
            if self.cb is None:
                raise RuntimeError("Engine not fitted")
            return self.cb.recommend(user_id, n=n)
        if method == "hybrid":
            if self.hybrid is None:
                raise RuntimeError("Engine not fitted")
            return self.hybrid.recommend(user_id, n=n)
        raise ValueError(f"Unknown method: {method}")

    def recommend_real_time(
        self,
        user_id: str,
        n: int = 10,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get real-time recommendations."""
        if self.real_time is None:
            raise RuntimeError("Engine not fitted")
        return self.real_time.recommend(user_id, n=n, context=context)

    def recommend_ab(
        self,
        experiment_name: str,
        user_id: str,
        n: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recommendations via A/B test assignment."""
        return self.ab_manager.get_recommendations(experiment_name, user_id, n=n)

    def create_ab_experiment(
        self,
        name: str,
        variants: list[str],
        traffic_split: list[float] | None = None,
    ):
        """Create an A/B experiment."""
        return self.ab_manager.create_experiment(name, variants, traffic_split)

    def track_ab_metric(
        self,
        experiment_name: str,
        user_id: str,
        metric_name: str,
        value: float,
    ) -> None:
        """Track a metric for an A/B experiment."""
        self.ab_manager.track_metric(experiment_name, user_id, metric_name, value)

    def get_ab_results(self, experiment_name: str) -> dict[str, Any]:
        """Get A/B experiment results."""
        return self.ab_manager.get_results(experiment_name)

    def add_interaction(self, interaction: dict[str, Any]) -> None:
        """Add a real-time interaction."""
        self._interactions.append(interaction)
        if self.real_time is not None:
            self.real_time.add_interaction(interaction)

    def get_trending(self, n: int = 10) -> list[dict[str, Any]]:
        """Get trending items."""
        if self.real_time is None:
            raise RuntimeError("Engine not fitted")
        return self.real_time.get_trending(n=n)
