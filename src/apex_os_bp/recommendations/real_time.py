"""Real-time recommendation engine.

Provides session-based recommendations, recency-weighted scoring,
and incremental model updates for low-latency serving.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from .collaborative_filtering import CollaborativeFilter
from .content_based import ContentBasedFilter


class RealTimeRecommender:
    """Real-time recommender with session awareness and recency decay.

    Parameters
    ----------
    decay_half_life : float
        Half-life in seconds for recency decay (default 3600 = 1 hour).
    session_window : float
        Session window in seconds (default 1800 = 30 minutes).
    """

    def __init__(self, decay_half_life: float = 3600.0, session_window: float = 1800.0):
        self.decay_half_life = decay_half_life
        self.session_window = session_window
        self.cf = CollaborativeFilter(method="item", k_neighbors=10)
        self.cb = ContentBasedFilter()
        self.interactions: list[dict[str, Any]] = []
        self.user_sessions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.item_popularity: dict[str, float] = defaultdict(float)
        self._last_update: float = 0.0

    def fit(
        self,
        interactions: list[dict[str, Any]],
        items: list[dict[str, Any]],
    ) -> "RealTimeRecommender":
        """Initial training on historical data."""
        self.interactions = list(interactions)
        self.cf.fit(interactions)
        self.cb.fit(items)
        for inter in interactions:
            uid = inter["user_id"]
            self.user_sessions[uid].append({
                "item_id": inter["item_id"],
                "timestamp": inter.get("timestamp", time.time()),
                "rating": inter["rating"],
            })
            self.item_popularity[inter["item_id"]] += inter["rating"]
        self._last_update = time.time()
        return self

    def add_interaction(self, interaction: dict[str, Any]) -> None:
        """Incrementally add a new interaction and update state."""
        self.interactions.append(interaction)
        uid = interaction["user_id"]
        ts = interaction.get("timestamp", time.time())
        self.user_sessions[uid].append({
            "item_id": interaction["item_id"],
            "timestamp": ts,
            "rating": interaction["rating"],
        })
        self.item_popularity[interaction["item_id"]] += interaction["rating"]
        self._last_update = time.time()

    def _recency_weight(self, timestamp: float, now: float) -> float:
        """Exponential decay weight based on age."""
        age = max(0.0, now - timestamp)
        return 0.5 ** (age / self.decay_half_life)

    def _get_session_items(self, user_id: str, now: float) -> list[str]:
        """Get items from the user's current session."""
        session = self.user_sessions.get(user_id, [])
        cutoff = now - self.session_window
        return [s["item_id"] for s in session if s["timestamp"] >= cutoff]

    def recommend(
        self,
        user_id: str,
        n: int = 10,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate real-time recommendations.

        Parameters
        ----------
        user_id : str
            Target user.
        n : int
            Number of recommendations.
        context : dict, optional
            May contain ``session_items`` (list of item IDs in the
            current session) and ``current_item`` (the item being
            viewed right now).
        """
        now = time.time()
        context = context or {}
        session_items = context.get("session_items", self._get_session_items(user_id, now))
        current_item = context.get("current_item")

        # Score candidates
        candidates: dict[str, float] = defaultdict(float)

        # 1. Session-based: items similar to current session items
        if session_items:
            session_recs = self.cb.recommend_for_items(
                session_items, n=len(self.cb.item_ids), exclude_items=session_items
            )
            for rec in session_recs:
                candidates[rec["item_id"]] += 0.4 * rec["score"]

        # 2. Current item similarity
        if current_item:
            similar = self.cb.similar_items(current_item, n=20)
            for rec in similar:
                candidates[rec["item_id"]] += 0.3 * rec["score"]

        # 3. Collaborative filtering scores
        cf_recs = self.cf.recommend(user_id, n=len(self.cf.item_ids), exclude_seen=False)
        cf_norm = self._normalize(cf_recs)
        for iid, score in cf_norm.items():
            candidates[iid] += 0.2 * score

        # 4. Popularity boost (recency-weighted)
        pop_norm = self._normalize(
            [{"item_id": k, "score": v} for k, v in self.item_popularity.items()]
        )
        for iid, score in pop_norm.items():
            candidates[iid] += 0.1 * score

        # Exclude already-seen items
        seen = set()
        if user_id in self.cf.user_index:
            u = self.cf.user_index[user_id]
            seen = {
                self.cf.item_ids[i]
                for i, r in enumerate(self.cf.ratings_matrix[u])
                if r > 0
            }
        seen.update(session_items)
        if current_item:
            seen.add(current_item)

        ranked = [(iid, score) for iid, score in candidates.items() if iid not in seen]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return [{"item_id": iid, "score": round(s, 4)} for iid, s in ranked[:n]]

    def get_trending(self, n: int = 10, window_seconds: float = 86400) -> list[dict[str, Any]]:
        """Get trending items based on recent interaction velocity."""
        now = time.time()
        cutoff = now - window_seconds
        recent: dict[str, float] = defaultdict(float)
        for inter in self.interactions:
            ts = inter.get("timestamp", 0)
            if ts >= cutoff:
                age = now - ts
                weight = 0.5 ** (age / self.decay_half_life)
                recent[inter["item_id"]] += inter["rating"] * weight
        ranked = sorted(recent.items(), key=lambda x: x[1], reverse=True)
        return [{"item_id": iid, "score": round(s, 4)} for iid, s in ranked[:n]]

    @staticmethod
    def _normalize(scores: list[dict[str, Any]]) -> dict[str, float]:
        """Min-max normalise scores to [0, 1]."""
        if not scores:
            return {}
        vals = [s["score"] for s in scores]
        lo, hi = min(vals), max(vals)
        rng = hi - lo
        if rng == 0:
            return {s["item_id"]: 0.5 for s in scores}
        return {s["item_id"]: (s["score"] - lo) / rng for s in scores}
