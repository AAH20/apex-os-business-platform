"""Tests for search analytics and suggestions."""
import unittest
from apex_os_bp.search.analytics import SearchAnalyticsEngine
from apex_os_bp.search.suggestions import SearchSuggestionsEngine
from apex_os_bp.search.models import SearchableDocument


class TestSearchAnalytics(unittest.TestCase):
    def setUp(self):
        self.sa = SearchAnalyticsEngine()

    def test_record_search(self):
        e = self.sa.record_search("laptop", user_id="u1", result_count=5)
        self.assertEqual(e.query, "laptop")
        self.assertEqual(e.result_count, 5)

    def test_click_through_rate(self):
        self.sa.record_search("phone", user_id="u1", result_count=3)
        self.sa.record_search("tablet", user_id="u2", result_count=0)
        self.sa.record_click("phone", "r1", 0, user_id="u1")
        self.assertEqual(self.sa.get_click_through_rate(), 0.5)

    def test_top_queries(self):
        self.sa.record_search("laptop")
        self.sa.record_search("laptop")
        self.sa.record_search("phone")
        top = self.sa.get_top_queries(1)
        self.assertEqual(top[0], ("laptop", 2))

    def test_zero_result_queries(self):
        self.sa.record_search("xyz123", result_count=0)
        self.sa.record_search("xyz123", result_count=0)
        zero = self.sa.get_zero_result_queries()
        self.assertEqual(len(zero), 1)
        self.assertEqual(zero[0][0], "xyz123")

    def test_summary(self):
        self.sa.record_search("a", result_count=5, latency_ms=100)
        self.sa.record_search("b", result_count=3, latency_ms=200)
        s = self.sa.get_summary()
        self.assertEqual(s.total_searches, 2)
        self.assertEqual(s.unique_queries, 2)
        self.assertEqual(s.avg_latency_ms, 150.0)

    def test_user_history(self):
        self.sa.record_search("q1", user_id="u1")
        self.sa.record_search("q2", user_id="u1")
        history = self.sa.get_user_history("u1")
        self.assertEqual(len(history), 2)


class TestSearchSuggestions(unittest.TestCase):
    def setUp(self):
        self.ss = SearchSuggestionsEngine()
        self.ss.add_document(SearchableDocument(
            id="1", title="laptop computer",
            content="portable notebook pc", tags=["electronics"]
        ))
        self.ss.add_document(SearchableDocument(
            id="2", title="laptop bag",
            content="carry case for laptop", tags=["accessories"]
        ))

    def test_did_you_mean(self):
        results = self.ss.did_you_mean("laptp")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].type, "correction")

    def test_did_you_mean_empty(self):
        self.assertEqual(self.ss.did_you_mean(""), [])

    def test_related_searches(self):
        related = self.ss.related_searches("laptop")
        self.assertTrue(len(related) > 0)
        self.assertEqual(related[0].type, "related")

    def test_trending(self):
        self.ss.analytics.record_search("laptop")
        self.ss.analytics.record_search("laptop")
        trending = self.ss.trending_searches()
        self.assertTrue(len(trending) > 0)

    def test_get_suggestions(self):
        result = self.ss.get_suggestions("laptop")
        self.assertIn("corrections", result)
        self.assertIn("related", result)
        self.assertIn("trending", result)
        self.assertIn("completions", result)


if __name__ == "__main__":
    unittest.main()
