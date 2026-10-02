"""Comprehensive tests for the recommendation engine."""

import math
import time
import unittest

from apex_os_bp.recommendations import (
    ABTestManager,
    CollaborativeFilter,
    ContentBasedFilter,
    HybridRecommender,
    RealTimeRecommender,
    RecommendationEngine,
)
from apex_os_bp.recommendations.ab_testing import Experiment


# --------------------------------------------------------------------- #
#  Test data helpers
# --------------------------------------------------------------------- #

def _sample_interactions():
    """Generate sample user-item interactions."""
    return [
        {"user_id": "u1", "item_id": "i1", "rating": 5.0},
        {"user_id": "u1", "item_id": "i2", "rating": 4.0},
        {"user_id": "u1", "item_id": "i3", "rating": 3.0},
        {"user_id": "u2", "item_id": "i1", "rating": 4.0},
        {"user_id": "u2", "item_id": "i2", "rating": 5.0},
        {"user_id": "u2", "item_id": "i4", "rating": 2.0},
        {"user_id": "u3", "item_id": "i2", "rating": 3.0},
        {"user_id": "u3", "item_id": "i3", "rating": 5.0},
        {"user_id": "u3", "item_id": "i5", "rating": 4.0},
        {"user_id": "u4", "item_id": "i1", "rating": 3.0},
        {"user_id": "u4", "item_id": "i4", "rating": 5.0},
        {"user_id": "u4", "item_id": "i5", "rating": 4.0},
        {"user_id": "u5", "item_id": "i3", "rating": 4.0},
        {"user_id": "u5", "item_id": "i4", "rating": 3.0},
        {"user_id": "u5", "item_id": "i5", "rating": 5.0},
    ]


def _sample_items():
    """Generate sample item metadata."""
    return [
        {"item_id": "i1", "features": {"title": "Action Movie", "category": "action", "genre": "thriller"}},
        {"item_id": "i2", "features": {"title": "Action Hero", "category": "action", "genre": "adventure"}},
        {"item_id": "i3", "features": {"title": "Comedy Show", "category": "comedy", "genre": "funny"}},
        {"item_id": "i4", "features": {"title": "Drama Series", "category": "drama", "genre": "emotional"}},
        {"item_id": "i5", "features": {"title": "Action Comedy", "category": "comedy", "genre": "action"}},
    ]


# --------------------------------------------------------------------- #
#  Collaborative Filtering Tests
# --------------------------------------------------------------------- #

class TestCollaborativeFiltering(unittest.TestCase):
    """Tests for collaborative filtering."""

    def setUp(self):
        self.interactions = _sample_interactions()
        self.cf_svd = CollaborativeFilter(method="svd", n_factors=2).fit(self.interactions)
        self.cf_user = CollaborativeFilter(method="user", k_neighbors=3).fit(self.interactions)
        self.cf_item = CollaborativeFilter(method="item", k_neighbors=3).fit(self.interactions)

    def test_fit_creates_indices(self):
        self.assertEqual(len(self.cf_svd.user_ids), 5)
        self.assertEqual(len(self.cf_svd.item_ids), 5)
        self.assertIn("u1", self.cf_svd.user_index)
        self.assertIn("i1", self.cf_svd.item_index)

    def test_fit_empty_raises(self):
        with self.assertRaises(ValueError):
            CollaborativeFilter().fit([])

    def test_invalid_method_raises(self):
        with self.assertRaises(ValueError):
            CollaborativeFilter(method="invalid")

    def test_predict_returns_float(self):
        score = self.cf_svd.predict("u1", "i1")
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 1.0)
        self.assertLessEqual(score, 5.0)

    def test_predict_unknown_user_returns_global_mean(self):
        score = self.cf_svd.predict("unknown_user", "i1")
        self.assertAlmostEqual(score, self.cf_svd.global_mean)

    def test_predict_unknown_item_returns_global_mean(self):
        score = self.cf_svd.predict("u1", "unknown_item")
        self.assertAlmostEqual(score, self.cf_svd.global_mean)

    def test_recommend_returns_list(self):
        recs = self.cf_svd.recommend("u1", n=3)
        self.assertIsInstance(recs, list)
        self.assertLessEqual(len(recs), 3)
        for rec in recs:
            self.assertIn("item_id", rec)
            self.assertIn("score", rec)

    def test_recommend_excludes_seen(self):
        recs = self.cf_svd.recommend("u1", n=10, exclude_seen=True)
        seen = {"i1", "i2", "i3"}  # u1 has rated these
        for rec in recs:
            self.assertNotIn(rec["item_id"], seen)

    def test_recommend_unknown_user_returns_empty(self):
        recs = self.cf_svd.recommend("unknown_user", n=5)
        self.assertEqual(recs, [])

    def test_recommend_sorted_descending(self):
        recs = self.cf_svd.recommend("u1", n=5)
        scores = [r["score"] for r in recs]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_similar_items(self):
        similar = self.cf_item.similar_items("i1", n=3)
        self.assertIsInstance(similar, list)
        self.assertLessEqual(len(similar), 3)
        for s in similar:
            self.assertIn("item_id", s)
            self.assertIn("score", s)
            self.assertNotEqual(s["item_id"], "i1")

    def test_similar_items_unknown_returns_empty(self):
        self.assertEqual(self.cf_item.similar_items("unknown"), [])

    def test_similar_users(self):
        similar = self.cf_user.similar_users("u1", n=3)
        self.assertIsInstance(similar, list)
        self.assertLessEqual(len(similar), 3)
        for s in similar:
            self.assertIn("user_id", s)
            self.assertNotEqual(s["user_id"], "u1")

    def test_similar_users_unknown_returns_empty(self):
        self.assertEqual(self.cf_user.similar_users("unknown"), [])

    def test_user_based_predict(self):
        score = self.cf_user.predict("u1", "i4")
        self.assertIsInstance(score, float)

    def test_item_based_predict(self):
        score = self.cf_item.predict("u1", "i4")
        self.assertIsInstance(score, float)

    def test_svd_factors_shape(self):
        self.assertEqual(self.cf_svd.user_factors.shape[0], 5)  # 5 users
        self.assertEqual(self.cf_svd.item_factors.shape[0], 5)  # 5 items


# --------------------------------------------------------------------- #
#  Content-Based Filtering Tests
# --------------------------------------------------------------------- #

class TestContentBasedFiltering(unittest.TestCase):
    """Tests for content-based filtering."""

    def setUp(self):
        self.items = _sample_items()
        self.cb = ContentBasedFilter().fit(self.items)

    def test_fit_creates_item_ids(self):
        self.assertEqual(len(self.cb.item_ids), 5)
        self.assertIn("i1", self.cb.item_index)

    def test_fit_empty_raises(self):
        with self.assertRaises(ValueError):
            ContentBasedFilter().fit([])

    def test_vocabulary_built(self):
        self.assertGreater(len(self.cb.vocab), 0)
        self.assertGreater(len(self.cb.idf), 0)

    def test_tfidf_vectors_computed(self):
        self.assertEqual(len(self.cb.tfidf_vectors), 5)
        for iid, vec in self.cb.tfidf_vectors.items():
            self.assertIsInstance(vec, dict)
            # L2 norm should be ~1
            norm = math.sqrt(sum(v * v for v in vec.values()))
            self.assertAlmostEqual(norm, 1.0, places=5)

    def test_similar_items(self):
        similar = self.cb.similar_items("i1", n=3)
        self.assertIsInstance(similar, list)
        self.assertLessEqual(len(similar), 3)
        for s in similar:
            self.assertIn("item_id", s)
            self.assertIn("score", s)
            self.assertNotEqual(s["item_id"], "i1")

    def test_similar_items_unknown_returns_empty(self):
        self.assertEqual(self.cb.similar_items("unknown"), [])

    def test_update_user_profile(self):
        self.cb.update_user_profile("u1", ["i1", "i2"])
        self.assertIn("u1", self.cb._user_profiles)
        profile = self.cb._user_profiles["u1"]
        self.assertIsInstance(profile, dict)

    def test_recommend(self):
        self.cb.update_user_profile("u1", ["i1", "i2"])
        recs = self.cb.recommend("u1", n=3)
        self.assertIsInstance(recs, list)
        self.assertLessEqual(len(recs), 3)
        for rec in recs:
            self.assertIn("item_id", rec)
            self.assertIn("score", rec)

    def test_recommend_no_profile_returns_empty(self):
        recs = self.cb.recommend("unknown_user", n=5)
        self.assertEqual(recs, [])

    def test_recommend_excludes_items(self):
        self.cb.update_user_profile("u1", ["i1", "i2"])
        recs = self.cb.recommend("u1", n=5, exclude_items=["i3", "i4"])
        for rec in recs:
            self.assertNotIn(rec["item_id"], {"i3", "i4"})

    def test_recommend_for_items(self):
        recs = self.cb.recommend_for_items(["i1"], n=3)
        self.assertIsInstance(recs, list)
        self.assertLessEqual(len(recs), 3)
        for rec in recs:
            self.assertNotEqual(rec["item_id"], "i1")

    def test_recommend_for_items_empty_seeds(self):
        recs = self.cb.recommend_for_items([], n=3)
        self.assertEqual(recs, [])

    def test_cosine_similarity_identical(self):
        vec = {"a": 1.0, "b": 0.5}
        sim = ContentBasedFilter._cosine_sim(vec, vec)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_cosine_similarity_orthogonal(self):
        vec_a = {"a": 1.0}
        vec_b = {"b": 1.0}
        sim = ContentBasedFilter._cosine_sim(vec_a, vec_b)
        self.assertAlmostEqual(sim, 0.0, places=5)

    def test_cosine_similarity_empty(self):
        self.assertEqual(ContentBasedFilter._cosine_sim({}, {"a": 1.0}), 0.0)
        self.assertEqual(ContentBasedFilter._cosine_sim({"a": 1.0}, {}), 0.0)


# --------------------------------------------------------------------- #
#  Hybrid Recommendation Tests
# --------------------------------------------------------------------- #

class TestHybridRecommendations(unittest.TestCase):
    """Tests for hybrid recommendation engine."""

    def setUp(self):
        self.interactions = _sample_interactions()
        self.items = _sample_items()
        self.hybrid = HybridRecommender().fit(self.interactions, self.items)

    def test_fit_creates_submodels(self):
        self.assertIsNotNone(self.hybrid.cf)
        self.assertIsNotNone(self.hybrid.cb)

    def test_invalid_strategy_raises(self):
        with self.assertRaises(ValueError):
            HybridRecommender(strategy="invalid")

    def test_negative_weights_raise(self):
        with self.assertRaises(ValueError):
            HybridRecommender(cf_weight=-0.5, cb_weight=0.5)

    def test_zero_total_weights_raise(self):
        with self.assertRaises(ValueError):
            HybridRecommender(cf_weight=0.0, cb_weight=0.0)

    def test_recommend_returns_list(self):
        recs = self.hybrid.recommend("u1", n=3)
        self.assertIsInstance(recs, list)
        self.assertLessEqual(len(recs), 3)

    def test_recommend_excludes_items(self):
        recs = self.hybrid.recommend("u1", n=5, exclude_items=["i4", "i5"])
        for rec in recs:
            self.assertNotIn(rec["item_id"], {"i4", "i5"})

    def test_recommend_before_fit_raises(self):
        hybrid = HybridRecommender()
        with self.assertRaises(RuntimeError):
            hybrid.recommend("u1", n=3)

    def test_weighted_strategy(self):
        hybrid = HybridRecommender(strategy="weighted", cf_weight=0.7, cb_weight=0.3)
        hybrid.fit(self.interactions, self.items)
        recs = hybrid.recommend("u1", n=3)
        self.assertIsInstance(recs, list)
        self.assertLessEqual(len(recs), 3)

    def test_switching_strategy(self):
        hybrid = HybridRecommender(strategy="switching")
        hybrid.fit(self.interactions, self.items)
        recs = hybrid.recommend("u1", n=3)
        self.assertIsInstance(recs, list)

    def test_feature_strategy(self):
        hybrid = HybridRecommender(strategy="feature")
        hybrid.fit(self.interactions, self.items)
        recs = hybrid.recommend("u1", n=3)
        self.assertIsInstance(recs, list)

    def test_normalize_scores(self):
        scores = [{"item_id": "a", "score": 10.0}, {"item_id": "b", "score": 20.0}]
        norm = self.hybrid._normalize_scores(scores)
        self.assertAlmostEqual(norm["a"], 0.0)
        self.assertAlmostEqual(norm["b"], 1.0)

    def test_normalize_scores_empty(self):
        self.assertEqual(self.hybrid._normalize_scores([]), {})

    def test_normalize_scores_same_values(self):
        scores = [{"item_id": "a", "score": 5.0}, {"item_id": "b", "score": 5.0}]
        norm = self.hybrid._normalize_scores(scores)
        self.assertAlmostEqual(norm["a"], 0.5)
        self.assertAlmostEqual(norm["b"], 0.5)


# --------------------------------------------------------------------- #
#  Real-Time Recommendation Tests
# --------------------------------------------------------------------- #

class TestRealTimeRecommendations(unittest.TestCase):
    """Tests for real-time recommendation engine."""

    def setUp(self):
        self.interactions = _sample_interactions()
        self.items = _sample_items()
        self.rt = RealTimeRecommender().fit(self.interactions, self.items)

    def test_fit_creates_models(self):
        self.assertIsNotNone(self.rt.cf)
        self.assertIsNotNone(self.rt.cb)

    def test_add_interaction(self):
        initial_count = len(self.rt.interactions)
        self.rt.add_interaction({"user_id": "u6", "item_id": "i1", "rating": 4.0})
        self.assertEqual(len(self.rt.interactions), initial_count + 1)

    def test_recommend_returns_list(self):
        recs = self.rt.recommend("u1", n=3)
        self.assertIsInstance(recs, list)
        self.assertLessEqual(len(recs), 3)

    def test_recommend_with_context(self):
        recs = self.rt.recommend("u1", n=3, context={"session_items": ["i1"], "current_item": "i2"})
        self.assertIsInstance(recs, list)

    def test_recommend_excludes_seen(self):
        recs = self.rt.recommend("u1", n=10)
        # u1 has rated i1, i2, i3
        for rec in recs:
            self.assertNotIn(rec["item_id"], {"i1", "i2", "i3"})

    def test_get_trending(self):
        trending = self.rt.get_trending(n=3)
        self.assertIsInstance(trending, list)
        self.assertLessEqual(len(trending), 3)
        for t in trending:
            self.assertIn("item_id", t)
            self.assertIn("score", t)

    def test_recency_weight(self):
        now = time.time()
        w = self.rt._recency_weight(now, now)
        self.assertAlmostEqual(w, 1.0)
        w_old = self.rt._recency_weight(now - self.rt.decay_half_life, now)
        self.assertAlmostEqual(w_old, 0.5, places=5)

    def test_get_session_items(self):
        now = time.time()
        self.rt.user_sessions["u1"].append({"item_id": "i1", "timestamp": now, "rating": 5.0})
        session = self.rt._get_session_items("u1", now)
        self.assertIn("i1", session)

    def test_normalize(self):
        scores = [{"item_id": "a", "score": 5.0}, {"item_id": "b", "score": 15.0}]
        norm = self.rt._normalize(scores)
        self.assertAlmostEqual(norm["a"], 0.0)
        self.assertAlmostEqual(norm["b"], 1.0)

    def test_normalize_empty(self):
        self.assertEqual(self.rt._normalize([]), {})


# --------------------------------------------------------------------- #
#  A/B Testing Tests
# --------------------------------------------------------------------- #

class TestABTesting(unittest.TestCase):
    """Tests for A/B testing framework."""

    def setUp(self):
        self.interactions = _sample_interactions()
        self.items = _sample_items()
        self.ab = ABTestManager(seed=42)
        self.cf = CollaborativeFilter().fit(self.interactions)
        self.cb = ContentBasedFilter().fit(self.items)
        self.ab.register_recommender("cf", self.cf)
        self.ab.register_recommender("cb", self.cb)

    def test_create_experiment(self):
        exp = self.ab.create_experiment("test_exp", ["control", "variant_a"])
        self.assertEqual(exp.name, "test_exp")
        self.assertEqual(len(exp.variants), 2)
        self.assertTrue(exp.is_active)

    def test_create_duplicate_raises(self):
        self.ab.create_experiment("test_exp", ["control", "variant_a"])
        with self.assertRaises(ValueError):
            self.ab.create_experiment("test_exp", ["control", "variant_a"])

    def test_experiment_requires_two_variants(self):
        with self.assertRaises(ValueError):
            Experiment(name="bad", variants=["only_one"], traffic_split=[1.0])

    def test_experiment_traffic_split_must_match(self):
        with self.assertRaises(ValueError):
            Experiment(name="bad", variants=["a", "b"], traffic_split=[1.0])

    def test_experiment_traffic_split_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            Experiment(name="bad", variants=["a", "b"], traffic_split=[0.3, 0.3])

    def test_assign_variant_deterministic(self):
        self.ab.create_experiment("test_exp", ["control", "variant_a"])
        v1 = self.ab.assign_variant("test_exp", "user_1")
        v2 = self.ab.assign_variant("test_exp", "user_1")
        self.assertEqual(v1, v2)

    def test_assign_variant_sticky(self):
        self.ab.create_experiment("test_exp", ["control", "variant_a"])
        v1 = self.ab.assign_variant("test_exp", "user_1")
        v2 = self.ab.assign_variant("test_exp", "user_1")
        self.assertEqual(v1, v2)

    def test_assign_variant_unknown_experiment(self):
        with self.assertRaises(ValueError):
            self.ab.assign_variant("unknown", "user_1")

    def test_assign_variant_after_stop(self):
        exp = self.ab.create_experiment("test_exp", ["control", "variant_a"])
        exp.stop()
        with self.assertRaises(RuntimeError):
            self.ab.assign_variant("test_exp", "user_1")

    def test_get_recommendations(self):
        self.ab.create_experiment("test_exp", ["cf", "cb"])
        recs = self.ab.get_recommendations("test_exp", "u1", n=3)
        self.assertIsInstance(recs, list)
        self.assertLessEqual(len(recs), 3)

    def test_get_recommendations_unknown_variant(self):
        self.ab.create_experiment("test_exp", ["cf", "unknown_variant"])
        with self.assertRaises(ValueError):
            self.ab.get_recommendations("test_exp", "u1", n=3)

    def test_track_metric(self):
        self.ab.create_experiment("test_exp", ["cf", "cb"])
        self.ab.track_metric("test_exp", "u1", "ctr", 1.0)
        self.ab.track_metric("test_exp", "u1", "ctr", 0.0)
        exp = self.ab.experiments["test_exp"]
        self.assertEqual(len(exp.metrics["cf"]["ctr"]) + len(exp.metrics["cb"]["ctr"]), 2)

    def test_get_results(self):
        self.ab.create_experiment("test_exp", ["cf", "cb"])
        self.ab.track_metric("test_exp", "u1", "ctr", 1.0)
        self.ab.track_metric("test_exp", "u2", "ctr", 0.0)
        results = self.ab.get_results("test_exp")
        self.assertIn("variants", results)
        self.assertIn("cf", results["variants"])
        self.assertIn("cb", results["variants"])

    def test_get_results_unknown_experiment(self):
        with self.assertRaises(ValueError):
            self.ab.get_results("unknown")

    def test_welch_ttest_identical(self):
        p = ABTestManager._welch_ttest([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        self.assertGreater(p, 0.05)

    def test_welch_ttest_different(self):
        p = ABTestManager._welch_ttest([1.0, 1.1, 0.9], [5.0, 5.1, 4.9])
        self.assertLess(p, 0.05)

    def test_welch_ttest_small_samples(self):
        p = ABTestManager._welch_ttest([1.0], [2.0])
        self.assertEqual(p, 1.0)

    def test_normal_cdf(self):
        from apex_os_bp.recommendations.ab_testing import _normal_cdf
        self.assertAlmostEqual(_normal_cdf(0.0), 0.5, places=5)
        self.assertGreater(_normal_cdf(1.0), 0.8)
        self.assertLess(_normal_cdf(-1.0), 0.2)

    def test_traffic_split_custom(self):
        exp = self.ab.create_experiment(
            "test_exp", ["a", "b", "c"], traffic_split=[0.5, 0.3, 0.2]
        )
        self.assertEqual(exp.traffic_split, [0.5, 0.3, 0.2])


# --------------------------------------------------------------------- #
#  Unified Engine Tests
# --------------------------------------------------------------------- #

class TestRecommendationEngine(unittest.TestCase):
    """Tests for the unified recommendation engine."""

    def setUp(self):
        self.interactions = _sample_interactions()
        self.items = _sample_items()
        self.engine = RecommendationEngine()
        self.engine.fit(self.interactions, self.items)

    def test_fit_creates_all_models(self):
        self.assertIsNotNone(self.engine.cf)
        self.assertIsNotNone(self.engine.cb)
        self.assertIsNotNone(self.engine.hybrid)
        self.assertIsNotNone(self.engine.real_time)

    def test_recommend_collaborative(self):
        recs = self.engine.recommend("u1", n=3, method="collaborative")
        self.assertIsInstance(recs, list)
        self.assertLessEqual(len(recs), 3)

    def test_recommend_content(self):
        recs = self.engine.recommend("u1", n=3, method="content")
        self.assertIsInstance(recs, list)

    def test_recommend_hybrid(self):
        recs = self.engine.recommend("u1", n=3, method="hybrid")
        self.assertIsInstance(recs, list)

    def test_recommend_invalid_method(self):
        with self.assertRaises(ValueError):
            self.engine.recommend("u1", n=3, method="invalid")

    def test_recommend_before_fit_raises(self):
        engine = RecommendationEngine()
        with self.assertRaises(RuntimeError):
            engine.recommend("u1", n=3)

    def test_recommend_real_time(self):
        recs = self.engine.recommend_real_time("u1", n=3)
        self.assertIsInstance(recs, list)

    def test_recommend_real_time_with_context(self):
        recs = self.engine.recommend_real_time(
            "u1", n=3, context={"session_items": ["i1"], "current_item": "i2"}
        )
        self.assertIsInstance(recs, list)

    def test_create_ab_experiment(self):
        exp = self.engine.create_ab_experiment("test_exp", ["cf", "cb"])
        self.assertEqual(exp.name, "test_exp")

    def test_recommend_ab(self):
        self.engine.create_ab_experiment("test_exp", ["cf", "cb"])
        recs = self.engine.recommend_ab("test_exp", "u1", n=3)
        self.assertIsInstance(recs, list)

    def test_track_ab_metric(self):
        self.engine.create_ab_experiment("test_exp", ["cf", "cb"])
        self.engine.track_ab_metric("test_exp", "u1", "ctr", 1.0)
        results = self.engine.get_ab_results("test_exp")
        self.assertIn("variants", results)

    def test_add_interaction(self):
        initial = len(self.engine._interactions)
        self.engine.add_interaction({"user_id": "u6", "item_id": "i1", "rating": 4.0})
        self.assertEqual(len(self.engine._interactions), initial + 1)

    def test_get_trending(self):
        trending = self.engine.get_trending(n=3)
        self.assertIsInstance(trending, list)
        self.assertLessEqual(len(trending), 3)

    def test_get_trending_before_fit_raises(self):
        engine = RecommendationEngine()
        with self.assertRaises(RuntimeError):
            engine.get_trending(n=3)


# --------------------------------------------------------------------- #
#  Integration Tests
# --------------------------------------------------------------------- #

class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""

    def test_full_pipeline(self):
        """Test the complete recommendation pipeline."""
        interactions = _sample_interactions()
        items = _sample_items()

        engine = RecommendationEngine()
        engine.fit(interactions, items)

        # Get recommendations from each method
        cf_recs = engine.recommend("u1", n=3, method="collaborative")
        cb_recs = engine.recommend("u1", n=3, method="content")
        hybrid_recs = engine.recommend("u1", n=3, method="hybrid")
        rt_recs = engine.recommend_real_time("u1", n=3)

        self.assertIsInstance(cf_recs, list)
        self.assertIsInstance(cb_recs, list)
        self.assertIsInstance(hybrid_recs, list)
        self.assertIsInstance(rt_recs, list)

        # A/B testing
        engine.create_ab_experiment("full_test", ["cf", "cb", "hybrid"])
        ab_recs = engine.recommend_ab("full_test", "u1", n=3)
        self.assertIsInstance(ab_recs, list)

        # Track metrics
        engine.track_ab_metric("full_test", "u1", "ctr", 1.0)
        engine.track_ab_metric("full_test", "u2", "ctr", 0.0)
        results = engine.get_ab_results("full_test")
        self.assertIn("variants", results)

        # Real-time update
        engine.add_interaction({"user_id": "u1", "item_id": "i4", "rating": 5.0})
        new_recs = engine.recommend_real_time("u1", n=3)
        self.assertIsInstance(new_recs, list)

        # Trending
        trending = engine.get_trending(n=3)
        self.assertIsInstance(trending, list)

    def test_cold_start_user(self):
        """Test recommendations for a user not in training data."""
        interactions = _sample_interactions()
        items = _sample_items()

        engine = RecommendationEngine()
        engine.fit(interactions, items)

        # Unknown user should still get real-time recs (popularity-based)
        recs = engine.recommend_real_time("unknown_user", n=3)
        self.assertIsInstance(recs, list)

    def test_single_item_single_user(self):
        """Test edge case with minimal data."""
        interactions = [{"user_id": "u1", "item_id": "i1", "rating": 5.0}]
        items = [{"item_id": "i1", "features": {"title": "Test", "category": "test"}}]

        cf = CollaborativeFilter(method="svd", n_factors=1).fit(interactions)
        recs = cf.recommend("u1", n=1)
        # Only one item exists and it's seen, so no recs
        self.assertEqual(recs, [])


if __name__ == "__main__":
    unittest.main()
