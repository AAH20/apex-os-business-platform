"""Collaborative filtering recommendation engine.

Supports user-based and item-based collaborative filtering using
cosine similarity, plus matrix factorization via truncated SVD.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from typing import Any


class CollaborativeFilter:
    """Collaborative filtering recommender.

    Parameters
    ----------
    n_factors : int
        Number of latent factors for matrix factorization.
    k_neighbors : int
        Number of nearest neighbors for user/item-based CF.
    method : str
        One of ``"user"``, ``"item"``, or ``"svd"``.
    """

    def __init__(self, n_factors: int = 15, k_neighbors: int = 20, method: str = "svd"):
        if method not in ("user", "item", "svd"):
            raise ValueError(f"Unknown method: {method}")
        self.n_factors = n_factors
        self.k_neighbors = k_neighbors
        self.method = method
        self.user_ids: list[str] = []
        self.item_ids: list[str] = []
        self.user_index: dict[str, int] = {}
        self.item_index: dict[str, int] = {}
        self.ratings_matrix: np.ndarray | None = None
        self.user_factors: np.ndarray | None = None
        self.item_factors: np.ndarray | None = None
        self.user_mean: np.ndarray | None = None
        self.global_mean: float = 0.0
        self._user_sim: np.ndarray | None = None
        self._item_sim: np.ndarray | None = None

    # ------------------------------------------------------------------ #
    #  Training
    # ------------------------------------------------------------------ #

    def fit(self, interactions: list[dict[str, Any]]) -> "CollaborativeFilter":
        """Build the model from a list of interaction dicts.

        Each dict must contain ``user_id``, ``item_id``, and ``rating``.
        """
        if not interactions:
            raise ValueError("interactions list is empty")

        users = sorted({i["user_id"] for i in interactions})
        items = sorted({i["item_id"] for i in interactions})
        self.user_ids = users
        self.item_ids = items
        self.user_index = {u: idx for idx, u in enumerate(users)}
        self.item_index = {it: idx for idx, it in enumerate(items)}

        n_users, n_items = len(users), len(items)
        mat = np.zeros((n_users, n_items), dtype=np.float64)
        for inter in interactions:
            u = self.user_index[inter["user_id"]]
            it = self.item_index[inter["item_id"]]
            mat[u, it] = inter["rating"]

        self.ratings_matrix = mat
        self.global_mean = float(mat[mat > 0].mean()) if (mat > 0).any() else 0.0

        # User mean for mean-centering
        self.user_mean = np.zeros(n_users, dtype=np.float64)
        for u in range(n_users):
            rated = mat[u][mat[u] > 0]
            self.user_mean[u] = rated.mean() if rated.size else self.global_mean

        if self.method == "svd":
            self._fit_svd(mat)
        elif self.method == "user":
            self._fit_user_sim(mat)
        elif self.method == "item":
            self._fit_item_sim(mat)

        return self

    def _fit_svd(self, mat: np.ndarray) -> None:
        """Truncated SVD on the mean-centered rating matrix."""
        centered = mat.copy()
        for u in range(centered.shape[0]):
            mask = centered[u] > 0
            centered[u][mask] -= self.user_mean[u]
        sparse = csr_matrix(centered)
        k = min(self.n_factors, min(sparse.shape) - 1)
        if k < 1:
            self.user_factors = np.zeros((mat.shape[0], 1))
            self.item_factors = np.zeros((mat.shape[1], 1))
            return
        u_svd, s, vt = svds(sparse, k=k)
        self.user_factors = u_svd @ np.diag(np.sqrt(s))
        self.item_factors = vt.T @ np.diag(np.sqrt(s))

    def _fit_user_sim(self, mat: np.ndarray) -> None:
        """Precompute user-user cosine similarity."""
        self._user_sim = self._cosine_similarity(mat)

    def _fit_item_sim(self, mat: np.ndarray) -> None:
        """Precompute item-item cosine similarity."""
        self._item_sim = self._cosine_similarity(mat.T)

    @staticmethod
    def _cosine_similarity(matrix: np.ndarray) -> np.ndarray:
        """Row-wise cosine similarity."""
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalised = matrix / norms
        return normalised @ normalised.T

    # ------------------------------------------------------------------ #
    #  Prediction
    # ------------------------------------------------------------------ #

    def predict(self, user_id: str, item_id: str) -> float:
        """Predict a rating for a user-item pair."""
        if user_id not in self.user_index or item_id not in self.item_index:
            return self.global_mean

        u = self.user_index[user_id]
        it = self.item_index[item_id]

        if self.method == "svd":
            return self._predict_svd(u, it)
        if self.method == "user":
            return self._predict_user(u, it)
        return self._predict_item(u, it)

    def _predict_svd(self, u: int, it: int) -> float:
        if self.user_factors is None or self.item_factors is None:
            return self.global_mean
        pred = self.user_mean[u] + self.user_factors[u] @ self.item_factors[it]
        return float(np.clip(pred, 1.0, 5.0))

    def _predict_user(self, u: int, it: int) -> float:
        sims = self._user_sim[u]
        rated_by_others = self.ratings_matrix[:, it] > 0
        if not rated_by_others.any():
            return self.user_mean[u]
        neighbor_idx = np.where(rated_by_others)[0]
        neighbor_sims = sims[neighbor_idx]
        top_k = neighbor_idx[np.argsort(neighbor_sims)[-self.k_neighbors:]]
        top_sims = sims[top_k]
        if top_sims.sum() == 0:
            return self.user_mean[u]
        ratings = self.ratings_matrix[top_k, it]
        return float(np.dot(top_sims, ratings) / np.abs(top_sims).sum())

    def _predict_item(self, u: int, it: int) -> float:
        sims = self._item_sim[it]
        rated_by_user = self.ratings_matrix[u] > 0
        if not rated_by_user.any():
            return self.user_mean[u]
        neighbor_idx = np.where(rated_by_user)[0]
        neighbor_sims = sims[neighbor_idx]
        top_k = neighbor_idx[np.argsort(neighbor_sims)[-self.k_neighbors:]]
        top_sims = sims[top_k]
        if top_sims.sum() == 0:
            return self.user_mean[u]
        ratings = self.ratings_matrix[u, top_k]
        return float(np.dot(top_sims, ratings) / np.abs(top_sims).sum())

    # ------------------------------------------------------------------ #
    #  Recommendation
    # ------------------------------------------------------------------ #

    def recommend(self, user_id: str, n: int = 10, exclude_seen: bool = True) -> list[dict[str, Any]]:
        """Return top-N item recommendations for a user."""
        if user_id not in self.user_index:
            return []
        u = self.user_index[user_id]
        scores: list[tuple[str, float]] = []
        for item_id in self.item_ids:
            if exclude_seen and self.ratings_matrix[u, self.item_index[item_id]] > 0:
                continue
            score = self.predict(user_id, item_id)
            scores.append((item_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [{"item_id": iid, "score": round(s, 4)} for iid, s in scores[:n]]

    def similar_items(self, item_id: str, n: int = 10) -> list[dict[str, Any]]:
        """Return items most similar to the given item."""
        if item_id not in self.item_index:
            return []
        it = self.item_index[item_id]
        if self.method == "item" and self._item_sim is not None:
            sims = self._item_sim[it]
        elif self.ratings_matrix is not None:
            target = self.ratings_matrix[:, it]
            sims = self._cosine_similarity(self.ratings_matrix.T)[it]
        else:
            return []
        ranked = np.argsort(sims)[::-1]
        results = []
        for idx in ranked:
            if self.item_ids[idx] == item_id:
                continue
            results.append({"item_id": self.item_ids[idx], "score": round(float(sims[idx]), 4)})
            if len(results) >= n:
                break
        return results

    def similar_users(self, user_id: str, n: int = 10) -> list[dict[str, Any]]:
        """Return users most similar to the given user."""
        if user_id not in self.user_index:
            return []
        u = self.user_index[user_id]
        if self._user_sim is not None:
            sims = self._user_sim[u]
        elif self.ratings_matrix is not None:
            sims = self._cosine_similarity(self.ratings_matrix)[u]
        else:
            return []
        ranked = np.argsort(sims)[::-1]
        results = []
        for idx in ranked:
            if self.user_ids[idx] == user_id:
                continue
            results.append({"user_id": self.user_ids[idx], "score": round(float(sims[idx]), 4)})
            if len(results) >= n:
                break
        return results
