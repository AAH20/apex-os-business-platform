"""Tests for Continuous BI core module."""

import time
import unittest

from apex_os_bp.continuous_bi.models import (
    Alert, AlertSeverity, Dashboard, Query, Widget, WidgetType,
)
from apex_os_bp.continuous_bi.query_engine import QueryCache, QueryEngine
from apex_os_bp.continuous_bi.streaming import (
    StreamEvent, StreamingETL, WindowOperator, WindowType,
)
from apex_os_bp.continuous_bi.visualization import ChartGenerator, ChartRenderer


class TestModels(unittest.TestCase):
    def test_query_creation(self):
        q = Query(id="q1", name="Test", sql="SELECT 1")
        self.assertEqual(q.id, "q1")
        self.assertEqual(q.ttl_seconds, 60)

    def test_widget_creation(self):
        w = Widget(id="w1", dashboard_id="d1", query_id="q1",
                   widget_type=WidgetType.LINE, title="Test")
        self.assertEqual(w.widget_type, WidgetType.LINE)

    def test_dashboard_creation(self):
        d = Dashboard(id="d1", name="Test")
        self.assertEqual(d.name, "Test")
        self.assertEqual(len(d.widgets), 0)

    def test_alert_creation(self):
        a = Alert(id="a1", name="Test", query_id="q1",
                  condition="x > 10", severity=AlertSeverity.WARNING)
        self.assertTrue(a.enabled)


class TestQueryEngine(unittest.TestCase):
    def test_cache_hit(self):
        engine = QueryEngine()
        call_count = 0

        def query():
            nonlocal call_count
            call_count += 1
            return 42

        r1 = engine.execute(query, "key1", ttl=60)
        r2 = engine.execute(query, "key1", ttl=60)
        self.assertEqual(r1, 42)
        self.assertEqual(r2, 42)
        self.assertEqual(call_count, 1)

    def test_cache_expiry(self):
        engine = QueryEngine()
        call_count = 0

        def query():
            nonlocal call_count
            call_count += 1
            return call_count

        r1 = engine.execute(query, "key2", ttl=0.01)
        time.sleep(0.02)
        r2 = engine.execute(query, "key2", ttl=0.01)
        self.assertNotEqual(r1, r2)

    def test_cache_invalidation(self):
        engine = QueryEngine()
        engine.execute(lambda: 42, "key3", ttl=60)
        engine.invalidate("key3")
        result = engine._cache.get("key3")
        self.assertIsNone(result)

    def test_cache_clear(self):
        cache = QueryCache()
        cache.put("a", 1, ttl=60)
        cache.clear()
        self.assertIsNone(cache.get("a"))


class TestStreaming(unittest.TestCase):
    def test_window_operator(self):
        op = WindowOperator(WindowType.TUMBLING, size_seconds=10)
        now = time.time()
        op.add_event(StreamEvent(timestamp=now, data={"value": 1}))
        op.add_event(StreamEvent(timestamp=now, data={"value": 2}))
        window = op.get_window()
        self.assertEqual(len(window.events), 2)

    def test_window_expiry(self):
        op = WindowOperator(WindowType.TUMBLING, size_seconds=0.05)
        op.add_event(StreamEvent(timestamp=time.time() - 1, data={"value": 1}))
        time.sleep(0.06)
        op.add_event(StreamEvent(timestamp=time.time(), data={"value": 2}))
        window = op.get_window()
        self.assertEqual(len(window.events), 1)

    def test_streaming_etl(self):
        etl = StreamingETL()
        op = WindowOperator(WindowType.TUMBLING, size_seconds=10)
        etl.add_operator("test", op)
        etl.process_event("test", StreamEvent(timestamp=time.time(), data={"x": 1}))
        window = op.get_window()
        self.assertEqual(len(window.events), 1)

    def test_aggregate(self):
        op = WindowOperator(WindowType.TUMBLING, size_seconds=10)
        now = time.time()
        op.add_event(StreamEvent(timestamp=now, data={"v": 10}))
        op.add_event(StreamEvent(timestamp=now, data={"v": 20}))
        result = op.aggregate(lambda events: sum(e.data["v"] for e in events))
        self.assertEqual(result, 30)


class TestVisualization(unittest.TestCase):
    def test_line_chart(self):
        data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}, {"x": 3, "y": 30}]
        svg = ChartGenerator.line_chart(data, "x", "y")
        self.assertIn("<svg", svg)
        self.assertIn("polyline", svg)

    def test_bar_chart(self):
        data = [{"x": "A", "y": 10}, {"x": "B", "y": 20}]
        svg = ChartGenerator.bar_chart(data, "x", "y")
        self.assertIn("<svg", svg)
        self.assertIn("rect", svg)

    def test_pie_chart(self):
        data = [{"label": "A", "value": 30}, {"label": "B", "value": 70}]
        svg = ChartGenerator.pie_chart(data, "label", "value")
        self.assertIn("<svg", svg)
        self.assertIn("path", svg)

    def test_empty_data(self):
        self.assertEqual(ChartGenerator.line_chart([], "x", "y"), "<svg></svg>")
        self.assertEqual(ChartGenerator.bar_chart([], "x", "y"), "<svg></svg>")
        self.assertEqual(ChartGenerator.pie_chart([], "l", "v"), "<svg></svg>")

    def test_renderer(self):
        renderer = ChartRenderer()
        data = [{"x": 1, "y": 10}]
        svg = renderer.render("line", data, x_key="x", y_key="y")
        self.assertIn("<svg", svg)
        svg = renderer.render("bar", data, x_key="x", y_key="y")
        self.assertIn("<svg", svg)
        svg = renderer.render("pie", [{"l": "A", "v": 1}], label_key="l", value_key="v")
        self.assertIn("<svg", svg)
        svg = renderer.render("unknown", data)
        self.assertEqual(svg, "<svg></svg>")


if __name__ == "__main__":
    unittest.main()
