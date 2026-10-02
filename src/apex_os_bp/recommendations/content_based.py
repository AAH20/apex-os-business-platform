"""Content-based filtering recommendation engine.

Uses TF-IDF vectorisation over item textual features and cosine
similarity to recommend items similar to those a user has liked.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any


class ContentBasedFilter:
    """Content-based recommender using TF-IDF and cosine similarity.

    Parameters
    ----------
    max_features : int
        Maximum vocabulary size for the TF-IDF vectoriser.
    """

    def __init__(self, max_features: int = 5000):
        self.max_features = max_features
        self.item_ids: list[str] = []
        self.item_features: dict[str, dict[str, Any]] = {}
        self.item_tokens: dict[str, list[str]] = {}
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.tfidf_vectors: dict[str, dict[str, float]] = {}
        self._user_profiles: dict[str, dict[str, float]] = {}

    # ------------------------------------------------------------------ #
    #  Tokenisation & TF-IDF
    # ------------------------------------------------------------------ #

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase alphanumeric tokenisation."""
        return re.findall(r"[a-z0-9]+", text.lower())

    def _build_vocabulary(self) -> None:
        """Build vocabulary and IDF from all item documents."""
        doc_freq: Counter[str] = Counter()
        total_docs = len(self.item_tokens)
        for tokens in self.item_tokens.values():
            unique = set(tokens)
            for term in unique:
                doc_freq[term] += 1

        # Keep top-N by document frequency
        most_common = doc_freq.most_common(self.max_features)
        self.vocab = {term: idx for idx, (term, _) in enumerate(most_common)}
        self.idf = {
            term: math.log((1 + total_docs) / (1 + df)) + 1
            for term, df in most_common
        }

    def _compute_tfidf(self, tokens: list[str]) -> dict[str, float]:
        """Compute normalised TF-IDF vector for a token list."""
        tf: Counter[str] = Counter(tokens)
        total = len(tokens) if tokens else 1
        vec: dict[str, float] = {}
        for term, count in tf.items():
            if term in self.vocab:
                tf_val = count / total
                vec[term] = tf_val * self.idf.get(term, 0.0)
        # L2 normalise
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            vec = {k: v / norm for k, v in vec.items()}
        return vec

    # ------------------------------------------------------------------ #
    #  Training
    # ------------------------------------------------------------------ #

    def fit(self, items: list[dict[str, Any]]) -> "ContentBasedFilter":
        """Build the content model from item metadata.

        Each item dict must contain ``item_id`` and ``features`` (a
        dict with string values that will be concatenated and
        tokenised, e.g. ``{"title": "...", "category": "..."}``).
        """
        if not items:
            raise ValueError("items list is empty")

        self.item_ids = [item["item_id"] for item in items]
        self.item_index = {item["item_id"]: idx for idx, item in enumerate(items)}
        self.item_features = {item["item_id"]: item.get("features", {}) for item in items}

        for item in items:
            iid = item["item_id"]
            features = item.get("features", {})
            text = " ".join(str(v) for v in features.values())
            self.item_tokens[iid] = self._tokenize(text)

        self._build_vocabulary()
        for iid, tokens in self.item_tokens.items():
            self.tfidf_vectors[iid] = self._compute_tfidf(tokens)

        return self

    # ------------------------------------------------------------------ #
    #  User profiles
    # ------------------------------------------------------------------ #

    def update_user_profile(self, user_id: str, liked_items: list[str]) -> None:
        """Build a user profile vector from items the user liked."""
        profile: dict[str, float] = defaultdict(float)
        count = 0
        for iid in liked_items:
            if iid not in self.tfidf_vectors:
                continue
            for term, weight in self.tfidf_vectors[iid].items():
                profile[term] += weight
            count += 1
        if count > 0:
            profile = {k: v / count for k, v in profile.items()}
        self._user_profiles[user_id] = dict(profile)

    # ------------------------------------------------------------------ #
    #  Similarity
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cosine_sim(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
        """Cosine similarity between two sparse vectors."""
        if not vec_a or not vec_b:
            return 0.0
        common = set(vec_a) & set(vec_b)
        dot = sum(vec_a[t] * vec_b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def similar_items(self, item_id: str, n: int = 10) -> list[dict[str, Any]]:
        """Return items most similar by content."""
        if item_id not in self.tfidf_vectors:
            return []
        target_vec = self.tfidf_vectors[item_id]
        scores: list[tuple[str, float]] = []
        for iid, vec in self.tfidf_vectors.items():
            if iid == item_id:
                continue
            sim = self._cosine_sim(target_vec, vec)
            scores.append((iid, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [{"item_id": iid, "score": round(s, 4)} for iid, s in scores[:n]]

    # ------------------------------------------------------------------ #
    #  Recommendation
    # ------------------------------------------------------------------ #

    def recommend(
        self,
        user_id: str,
        n: int = 10,
        exclude_items: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Recommend items based on the user's content profile."""
        if user_id not in self._user_profiles:
            return []
        profile = self._user_profiles[user_id]
        exclude = set(exclude_items or [])
        scores: list[tuple[str, float]] = []
        for iid, vec in self.tfidf_vectors.items():
            if iid in exclude:
                continue
            sim = self._cosine_sim(profile, vec)
            scores.append((iid, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [{"item_id": iid, "score": round(s, 4)} for iid, s in scores[:n]]

    def recommend_for_items(
        self,
        seed_items: list[str],
        n: int = 10,
        exclude_items: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Recommend items similar to a set of seed items."""
        exclude = set(exclude_items or [])
        exclude.update(seed_items)
        combined: dict[str, float] = defaultdict(float)
        count = 0
        for iid in seed_items:
            if iid not in self.tfidf_vectors:
                continue
            for term, weight in self.tfidf_vectors[iid].items():
                combined[term] += weight
            count += 1
        if count == 0:
            return []
        profile = {k: v / count for k, v in combined.items()}
        scores: list[tuple[str, float]] = []
        for iid, vec in self.tfidf_vectors.items():
            if iid in exclude:
                continue
            sim = self._cosine_sim(profile, vec)
            scores.append((iid, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [{"item_id": iid, "score": round(s, 4)} for iid, s in scores[:n]]
