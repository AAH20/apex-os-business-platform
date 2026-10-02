"""Hybrid recommendation engine.

Combines collaborative filtering and content-based filtering using
weighted score fusion, switching, or feature-augmentation strategies.
"""

from __future__ import annotations

from typing import Any

from .collaborative_filtering import CollaborativeFilter
from .content_based import ContentBasedFilter


class HybridRecommender:
    """Hybrid recommender that merges CF and content-based scores.

    Parameters
    ----------
    cf_weight : float
        Weight for collaborative filtering scores (0–1).
    cb_weight : float
        Weight for content-based scores (0–1).
    strategy : str
        One of ``"weighted"``, ``"switching"``, or ``"feature"``.
    """

    def __init__(
        self,
        cf_weight: float = 0.6,
        cb_weight: float = 0.4,
        strategy: str = "weighted",
    ):
        if strategy not in ("weighted", "switching", "feature"):
            raise ValueError(f"Unknown strategy: {strategy}")
        if cf_weight < 0 or cb_weight < 0:
            raise ValueError("Weights must be non-negative")
        total = cf_weight + cb_weight
        if total == 0:
            raise ValueError("At least one weight must be positive")
        self.cf_weight = cf_weight / total
        self.cb_weight = cb_weight / total
        self.strategy = strategy
        self.cf: CollaborativeFilter | None = None
        self.cb: ContentBasedFilter | None = None

    def fit(
        self,
        interactions: list[dict[str, Any]],
        items: list[dict[str, Any]],
    ) -> "HybridRecommender":
        """Train both sub-models."""
        self.cf = CollaborativeFilter(method="svd").fit(interactions)
        self.cb = ContentBasedFilter().fit(items)
        # Build user profiles from interactions
        user_likes: dict[str, list[str]] = {}
        for inter in interactions:
            uid = inter["user_id"]
            user_likes.setdefault(uid, []).append(inter["item_id"])
        for uid, liked in user_likes.items():
            self.cb.update_user_profile(uid, liked)
        return self

    def _normalize_scores(self, scores: list[dict[str, Any]]) -> dict[str, float]:
        """Min-max normalise a list of scored items to [0, 1]."""
        if not scores:
            return {}
        vals = [s["score"] for s in scores]
        lo, hi = min(vals), max(vals)
        rng = hi - lo
        if rng == 0:
            return {s["item_id"]: 0.5 for s in scores}
        return {s["item_id"]: (s["score"] - lo) / rng for s in scores}

    def recommend(
        self,
        user_id: str,
        n: int = 10,
        exclude_items: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate hybrid recommendations for a user."""
        if self.cf is None or self.cb is None:
            raise RuntimeError("Model not fitted. Call fit() first.")

        exclude = set(exclude_items or [])

        if self.strategy == "weighted":
            return self._weighted_recommend(user_id, n, exclude)
        if self.strategy == "switching":
            return self._switching_recommend(user_id, n, exclude)
        return self._feature_recommend(user_id, n, exclude)

    def _weighted_recommend(
        self, user_id: str, n: int, exclude: set[str]
    ) -> list[dict[str, Any]]:
        """Weighted score fusion."""
        cf_scores = self._normalize_scores(
            self.cf.recommend(user_id, n=len(self.cf.item_ids), exclude_seen=False)
        )
        cb_scores = self._normalize_scores(
            self.cb.recommend(user_id, n=len(self.cb.item_ids), exclude_items=[])
        )
        all_items = set(cf_scores) | set(cb_scores)
        combined: list[tuple[str, float]] = []
        for iid in all_items:
            if iid in exclude:
                continue
            score = self.cf_weight * cf_scores.get(iid, 0.0) + self.cb_weight * cb_scores.get(iid, 0.0)
            combined.append((iid, score))
        combined.sort(key=lambda x: x[1], reverse=True)
        return [{"item_id": iid, "score": round(s, 4)} for iid, s in combined[:n]]

    def _switching_recommend(
        self, user_id: str, n: int, exclude: set[str]
    ) -> list[dict[str, Any]]:
        """Switch between CF and CB based on user history density."""
        user_history = [
            i for i in self.cf.ratings_matrix[self.cf.user_index[user_id]] > 0
        ] if user_id in self.cf.user_index else []
        # If user has few ratings, rely more on content-based
        if len(user_history) < 5:
            primary, secondary = self.cb, self.cf
            primary_weight = 0.7
        else:
            primary, secondary = self.cf, self.cb
            primary_weight = 0.7

        primary_scores = self._normalize_scores(
            primary.recommend(user_id, n=len(primary.item_ids), exclude_seen=False)
            if isinstance(primary, CollaborativeFilter)
            else primary.recommend(user_id, n=len(primary.item_ids))
        )
        secondary_scores = self._normalize_scores(
            secondary.recommend(user_id, n=len(secondary.item_ids), exclude_seen=False)
            if isinstance(secondary, CollaborativeFilter)
            else secondary.recommend(user_id, n=len(secondary.item_ids))
        )
        all_items = set(primary_scores) | set(secondary_scores)
        combined: list[tuple[str, float]] = []
        for iid in all_items:
            if iid in exclude:
                continue
            score = (
                primary_weight * primary_scores.get(iid, 0.0)
                + (1 - primary_weight) * secondary_scores.get(iid, 0.0)
            )
            combined.append((iid, score))
        combined.sort(key=lambda x: x[1], reverse=True)
        return [{"item_id": iid, "score": round(s, 4)} for iid, s in combined[:n]]

    def _feature_recommend(
        self, user_id: str, n: int, exclude: set[str]
    ) -> list[dict[str, Any]]:
        """Feature augmentation: use CB scores as a tiebreaker for CF."""
        cf_scores = self._normalize_scores(
            self.cf.recommend(user_id, n=len(self.cf.item_ids), exclude_seen=False)
        )
        cb_scores = self._normalize_scores(
            self.cb.recommend(user_id, n=len(self.cb.item_ids), exclude_items=[])
        )
        all_items = set(cf_scores) | set(cb_scores)
        combined: list[tuple[str, float]] = []
        for iid in all_items:
            if iid in exclude:
                continue
            cf_s = cf_scores.get(iid, 0.0)
            cb_s = cb_scores.get(iid, 0.0)
            # CF is primary, CB breaks ties
            score = cf_s + 0.01 * cb_s
            combined.append((iid, score))
        combined.sort(key=lambda x: x[1], reverse=True)
        return [{"item_id": iid, "score": round(s, 4)} for iid, s in combined[:n]]
