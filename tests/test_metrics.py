"""Tests for the metrics system."""

import time
import unittest

from apex_os_bp.metrics import Counter, Gauge, Histogram, Timer, MetricAggregation


class TestCounter(unittest.TestCase):
    """Tests for Counter metric."""

    def test_initial_value_is_zero(self):
        c = Counter("requests_total")
        self.assertEqual(c.get(), 0.0)

    def test_inc_default(self):
        c = Counter("requests_total")
        c.inc()
        self.assertEqual(c.get(), 1.0)

    def test_inc_custom_amount(self):
        c = Counter("requests_total")
        c.inc(5.0)
        self.assertEqual(c.get(), 5.0)

    def test_inc_returns_new_value(self):
        c = Counter("requests_total")
        result = c.inc(3.0)
        self.assertEqual(result, 3.0)
        self.assertEqual(c.get(), 3.0)

    def test_dec(self):
        c = Counter("requests_total")
        c.inc(10.0)
        c.dec(3.0)
        self.assertEqual(c.get(), 7.0)

    def test_set(self):
        c = Counter("requests_total")
        c.set(42.0)
        self.assertEqual(c.get(), 42.0)

    def test_reset(self):
        c = Counter("requests_total")
        c.inc(100.0)
        c.reset()
        self.assertEqual(c.get(), 0.0)

    def test_labels(self):
        c = Counter("requests_total", labels={"method": "GET", "status": "200"})
        self.assertEqual(c.labels(), {"method": "GET", "status": "200"})

    def test_to_dict(self):
        c = Counter("requests_total", description="Total requests", labels={"env": "prod"})
        c.inc(5.0)
        d = c.to_dict()
        self.assertEqual(d["name"], "requests_total")
        self.assertEqual(d["description"], "Total requests")
        self.assertEqual(d["labels"], {"env": "prod"})
        self.assertEqual(d["value"], 5.0)
        self.assertEqual(d["type"], "counter")

    def test_negative_values_allowed(self):
        c = Counter("requests_total")
        c.inc(5.0)
        c.dec(10.0)
        self.assertEqual(c.get(), -5.0)

    def test_multiple_increments(self):
        c = Counter("requests_total")
        for _ in range(100):
            c.inc()
        self.assertEqual(c.get(), 100.0)


class TestGauge(unittest.TestCase):
    """Tests for Gauge metric."""

    def test_initial_value_is_zero(self):
        g = Gauge("memory_usage_bytes")
        self.assertEqual(g.get(), 0.0)

    def test_inc(self):
        g = Gauge("memory_usage_bytes")
        g.inc(1024.0)
        self.assertEqual(g.get(), 1024.0)

    def test_dec(self):
        g = Gauge("memory_usage_bytes")
        g.inc(2048.0)
        g.dec(512.0)
        self.assertEqual(g.get(), 1536.0)

    def test_set(self):
        g = Gauge("memory_usage_bytes")
        g.set(4096.0)
        self.assertEqual(g.get(), 4096.0)

    def test_negative_values(self):
        g = Gauge("temperature_celsius")
        g.set(-10.0)
        self.assertEqual(g.get(), -10.0)

    def test_inc_returns_new_value(self):
        g = Gauge("memory_usage_bytes")
        result = g.inc(100.0)
        self.assertEqual(result, 100.0)

    def test_labels(self):
        g = Gauge("memory_usage_bytes", labels={"host": "server-01"})
        self.assertEqual(g.labels(), {"host": "server-01"})

    def test_to_dict(self):
        g = Gauge("memory_usage_bytes", description="Memory in bytes", labels={"host": "server-01"})
        g.set(2048.0)
        d = g.to_dict()
        self.assertEqual(d["name"], "memory_usage_bytes")
        self.assertEqual(d["description"], "Memory in bytes")
        self.assertEqual(d["labels"], {"host": "server-01"})
        self.assertEqual(d["value"], 2048.0)
        self.assertEqual(d["type"], "gauge")

    def test_fluctuating_values(self):
        g = Gauge("queue_depth")
        g.inc(10.0)
        g.inc(5.0)
        g.dec(3.0)
        g.inc(2.0)
        self.assertEqual(g.get(), 14.0)


class TestHistogram(unittest.TestCase):
    """Tests for Histogram metric."""

    def test_initial_state(self):
        h = Histogram("request_duration_seconds")
        self.assertEqual(h.get_count(), 0)
        self.assertEqual(h.get_sum(), 0.0)
        self.assertEqual(h.get_mean(), 0.0)

    def test_observe_single(self):
        h = Histogram("request_duration_seconds")
        h.observe(0.5)
        self.assertEqual(h.get_count(), 1)
        self.assertEqual(h.get_sum(), 0.5)

    def test_observe_multiple(self):
        h = Histogram("request_duration_seconds")
        h.observe(0.1)
        h.observe(0.5)
        h.observe(1.0)
        self.assertEqual(h.get_count(), 3)
        self.assertAlmostEqual(h.get_sum(), 1.6)

    def test_observe_many(self):
        h = Histogram("request_duration_seconds")
        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        h.observe_many(values)
        self.assertEqual(h.get_count(), 5)
        self.assertAlmostEqual(h.get_sum(), 1.5)

    def test_min_max(self):
        h = Histogram("request_duration_seconds")
        h.observe(0.5)
        h.observe(2.0)
        h.observe(0.1)
        self.assertEqual(h.get_min(), 0.1)
        self.assertEqual(h.get_max(), 2.0)

    def test_mean(self):
        h = Histogram("request_duration_seconds")
        h.observe(1.0)
        h.observe(2.0)
        h.observe(3.0)
        self.assertAlmostEqual(h.get_mean(), 2.0)

    def test_custom_buckets(self):
        h = Histogram("request_duration_seconds", buckets=[0.1, 0.5, 1.0, float("inf")])
        h.observe(0.05)
        h.observe(0.3)
        h.observe(0.7)
        h.observe(2.0)
        counts = h.get_bucket_counts()
        self.assertEqual(counts[0.1], 1)
        self.assertEqual(counts[0.5], 2)
        self.assertEqual(counts[1.0], 3)
        self.assertEqual(counts[float("inf")], 4)

    def test_default_buckets(self):
        h = Histogram("request_duration_seconds")
        buckets = h.get_buckets()
        self.assertIn(0.005, buckets)
        self.assertIn(1.0, buckets)
        self.assertIn(10.0, buckets)
        self.assertIn(float("inf"), buckets)

    def test_percentile(self):
        h = Histogram("request_duration_seconds", buckets=[10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, float("inf")])
        for i in range(1, 101):
            h.observe(float(i))
        p50 = h.get_percentile(50)
        self.assertGreaterEqual(p50, 50.0)
        self.assertLessEqual(p50, 60.0)

    def test_percentile_100(self):
        h = Histogram("request_duration_seconds")
        h.observe(5.0)
        h.observe(10.0)
        self.assertEqual(h.get_percentile(100), 10.0)

    def test_percentile_empty(self):
        h = Histogram("request_duration_seconds")
        self.assertEqual(h.get_percentile(50), 0.0)

    def test_percentile_invalid(self):
        h = Histogram("request_duration_seconds")
        with self.assertRaises(ValueError):
            h.get_percentile(0)
        with self.assertRaises(ValueError):
            h.get_percentile(101)

    def test_reset(self):
        h = Histogram("request_duration_seconds")
        h.observe(1.0)
        h.observe(2.0)
        h.reset()
        self.assertEqual(h.get_count(), 0)
        self.assertEqual(h.get_sum(), 0.0)
        self.assertEqual(h.get_mean(), 0.0)

    def test_labels(self):
        h = Histogram("request_duration_seconds", labels={"endpoint": "/api/v1"})
        self.assertEqual(h.labels(), {"endpoint": "/api/v1"})

    def test_to_dict(self):
        h = Histogram("request_duration_seconds", description="Duration in seconds")
        h.observe(0.5)
        d = h.to_dict()
        self.assertEqual(d["name"], "request_duration_seconds")
        self.assertEqual(d["type"], "histogram")
        self.assertEqual(d["count"], 1)
        self.assertAlmostEqual(d["sum"], 0.5)
        self.assertIn("buckets", d)
        self.assertIn("bucket_counts", d)

    def test_bucket_counts_cumulative(self):
        h = Histogram("request_duration_seconds", buckets=[1.0, 2.0, float("inf")])
        h.observe(0.5)
        h.observe(1.5)
        h.observe(3.0)
        counts = h.get_bucket_counts()
        self.assertEqual(counts[1.0], 1)
        self.assertEqual(counts[2.0], 2)
        self.assertEqual(counts[float("inf")], 3)


class TestTimer(unittest.TestCase):
    """Tests for Timer metric."""

    def test_observe_manual(self):
        t = Timer("request_duration_seconds")
        t.observe(0.5)
        self.assertEqual(t.get_count(), 1)
        self.assertAlmostEqual(t.get_sum(), 0.5)

    def test_start_stop(self):
        t = Timer("request_duration_seconds")
        t.start()
        time.sleep(0.01)
        elapsed = t.stop()
        self.assertGreater(elapsed, 0.0)
        self.assertEqual(t.get_count(), 1)

    def test_start_stop_with_tag(self):
        t = Timer("request_duration_seconds")
        t.start("db_query")
        time.sleep(0.005)
        elapsed = t.stop("db_query")
        self.assertGreater(elapsed, 0.0)

    def test_stop_invalid_tag(self):
        t = Timer("request_duration_seconds")
        with self.assertRaises(KeyError):
            t.stop("nonexistent")

    def test_context_manager(self):
        t = Timer("request_duration_seconds")
        with t.time():
            time.sleep(0.01)
        self.assertEqual(t.get_count(), 1)
        self.assertGreater(t.get_sum(), 0.0)

    def test_context_manager_with_tag(self):
        t = Timer("request_duration_seconds")
        with t.time("my_tag"):
            time.sleep(0.005)
        self.assertEqual(t.get_count(), 1)

    def test_context_manager_exception_still_records(self):
        t = Timer("request_duration_seconds")
        try:
            with t.time():
                time.sleep(0.005)
                raise RuntimeError("test error")
        except RuntimeError:
            pass
        self.assertEqual(t.get_count(), 1)

    def test_get_histogram(self):
        t = Timer("request_duration_seconds")
        t.observe(1.0)
        h = t.get_histogram()
        self.assertIsInstance(h, Histogram)
        self.assertEqual(h.get_count(), 1)

    def test_mean(self):
        t = Timer("request_duration_seconds")
        t.observe(1.0)
        t.observe(3.0)
        self.assertAlmostEqual(t.get_mean(), 2.0)

    def test_min_max(self):
        t = Timer("request_duration_seconds")
        t.observe(0.5)
        t.observe(2.0)
        t.observe(1.0)
        self.assertEqual(t.get_min(), 0.5)
        self.assertEqual(t.get_max(), 2.0)

    def test_percentile(self):
        t = Timer("request_duration_seconds")
        for i in range(1, 21):
            t.observe(float(i) * 0.1)
        p50 = t.get_percentile(50)
        self.assertGreater(p50, 0.0)

    def test_reset(self):
        t = Timer("request_duration_seconds")
        t.observe(1.0)
        t.observe(2.0)
        t.reset()
        self.assertEqual(t.get_count(), 0)
        self.assertEqual(t.get_sum(), 0.0)

    def test_labels(self):
        t = Timer("request_duration_seconds", labels={"endpoint": "/api"})
        self.assertEqual(t.labels(), {"endpoint": "/api"})

    def test_to_dict(self):
        t = Timer("request_duration_seconds", description="Request duration")
        t.observe(0.5)
        d = t.to_dict()
        self.assertEqual(d["name"], "request_duration_seconds")
        self.assertEqual(d["type"], "timer")
        self.assertEqual(d["count"], 1)
        self.assertAlmostEqual(d["sum"], 0.5)

    def test_multiple_observations(self):
        t = Timer("request_duration_seconds")
        for _ in range(10):
            t.observe(0.1)
        self.assertEqual(t.get_count(), 10)
        self.assertAlmostEqual(t.get_sum(), 1.0)


class TestMetricAggregation(unittest.TestCase):
    """Tests for MetricAggregation."""

    def setUp(self):
        self.agg = MetricAggregation()

    def test_register_and_get(self):
        c = Counter("requests_total")
        self.agg.register(c)
        self.assertEqual(self.agg.get("requests_total"), c)

    def test_unregister(self):
        c = Counter("requests_total")
        self.agg.register(c)
        result = self.agg.unregister("requests_total")
        self.assertTrue(result)
        self.assertIsNone(self.agg.get("requests_total"))

    def test_unregister_nonexistent(self):
        result = self.agg.unregister("nonexistent")
        self.assertFalse(result)

    def test_get_all(self):
        c = Counter("requests_total")
        g = Gauge("memory_usage")
        self.agg.register(c)
        self.agg.register(g)
        all_metrics = self.agg.get_all()
        self.assertEqual(len(all_metrics), 2)
        self.assertIn("requests_total", all_metrics)
        self.assertIn("memory_usage", all_metrics)

    def test_get_by_type(self):
        c = Counter("requests_total")
        c2 = Counter("errors_total")
        g = Gauge("memory_usage")
        self.agg.register(c)
        self.agg.register(c2)
        self.agg.register(g)
        counters = self.agg.get_by_type("counter")
        self.assertEqual(len(counters), 2)
        gauges = self.agg.get_by_type("gauge")
        self.assertEqual(len(gauges), 1)

    def test_names(self):
        c = Counter("requests_total")
        g = Gauge("memory_usage")
        self.agg.register(c)
        self.agg.register(g)
        self.assertEqual(sorted(self.agg.names()), ["memory_usage", "requests_total"])

    def test_count(self):
        self.assertEqual(self.agg.count(), 0)
        self.agg.register(Counter("a"))
        self.agg.register(Gauge("b"))
        self.assertEqual(self.agg.count(), 2)

    def test_summary(self):
        c = Counter("requests_total")
        c.inc(5.0)
        self.agg.register(c)
        summary = self.agg.summary()
        self.assertIn("requests_total", summary)
        self.assertEqual(summary["requests_total"]["value"], 5.0)

    def test_aggregate_sum_counters(self):
        c1 = Counter("requests_total")
        c1.inc(10.0)
        c2 = Counter("errors_total")
        c2.inc(5.0)
        self.agg.register(c1)
        self.agg.register(c2)
        self.assertEqual(self.agg.aggregate_sum("counter"), 15.0)

    def test_aggregate_sum_gauges(self):
        g1 = Gauge("memory_usage")
        g1.set(100.0)
        g2 = Gauge("cpu_usage")
        g2.set(50.0)
        self.agg.register(g1)
        self.agg.register(g2)
        self.assertEqual(self.agg.aggregate_sum("gauge"), 150.0)

    def test_aggregate_sum_all_types(self):
        c = Counter("requests_total")
        c.inc(10.0)
        g = Gauge("memory_usage")
        g.set(100.0)
        self.agg.register(c)
        self.agg.register(g)
        self.assertEqual(self.agg.aggregate_sum(), 110.0)

    def test_aggregate_mean(self):
        c1 = Counter("a")
        c1.set(10.0)
        c2 = Counter("b")
        c2.set(20.0)
        self.agg.register(c1)
        self.agg.register(c2)
        self.assertEqual(self.agg.aggregate_mean("counter"), 15.0)

    def test_aggregate_max(self):
        c1 = Counter("a")
        c1.set(10.0)
        c2 = Counter("b")
        c2.set(50.0)
        self.agg.register(c1)
        self.agg.register(c2)
        self.assertEqual(self.agg.aggregate_max("counter"), 50.0)

    def test_aggregate_min(self):
        c1 = Counter("a")
        c1.set(10.0)
        c2 = Counter("b")
        c2.set(50.0)
        self.agg.register(c1)
        self.agg.register(c2)
        self.assertEqual(self.agg.aggregate_min("counter"), 10.0)

    def test_aggregate_empty(self):
        self.assertEqual(self.agg.aggregate_sum(), 0.0)
        self.assertEqual(self.agg.aggregate_mean(), 0.0)
        self.assertEqual(self.agg.aggregate_max(), 0.0)
        self.assertEqual(self.agg.aggregate_min(), 0.0)

    def test_filter_by_label(self):
        c1 = Counter("requests_total", labels={"env": "prod"})
        c2 = Counter("errors_total", labels={"env": "staging"})
        c3 = Counter("clicks_total", labels={"env": "prod"})
        self.agg.register(c1)
        self.agg.register(c2)
        self.agg.register(c3)
        prod_metrics = self.agg.filter_by_label("env", "prod")
        self.assertEqual(len(prod_metrics), 2)

    def test_filter_by_label_no_match(self):
        c = Counter("requests_total", labels={"env": "prod"})
        self.agg.register(c)
        result = self.agg.filter_by_label("env", "dev")
        self.assertEqual(len(result), 0)

    def test_reset_all(self):
        c = Counter("requests_total")
        c.inc(10.0)
        g = Gauge("memory_usage")
        g.set(100.0)
        self.agg.register(c)
        self.agg.register(g)
        self.agg.reset_all()
        self.assertEqual(c.get(), 0.0)
        self.assertEqual(g.get(), 0.0)

    def test_clear(self):
        c = Counter("requests_total")
        self.agg.register(c)
        self.agg.clear()
        self.assertEqual(self.agg.count(), 0)

    def test_aggregate_sum_histograms(self):
        h1 = Histogram("latency")
        h1.observe(1.0)
        h1.observe(2.0)
        h2 = Histogram("duration")
        h2.observe(3.0)
        self.agg.register(h1)
        self.agg.register(h2)
        self.assertEqual(self.agg.aggregate_sum("histogram"), 6.0)

    def test_aggregate_sum_timers(self):
        t1 = Timer("request_time")
        t1.observe(0.5)
        t2 = Timer("db_time")
        t2.observe(1.5)
        self.agg.register(t1)
        self.agg.register(t2)
        self.assertEqual(self.agg.aggregate_sum("timer"), 2.0)


class TestMetricsIntegration(unittest.TestCase):
    """Integration tests combining multiple metric types."""

    def test_full_workflow(self):
        """Test a realistic metrics workflow."""
        agg = MetricAggregation()

        # Register metrics
        requests = Counter("http_requests_total", labels={"service": "api"})
        errors = Counter("http_errors_total", labels={"service": "api"})
        latency = Histogram("http_request_duration_seconds", labels={"service": "api"})
        db_timer = Timer("db_query_duration_seconds", labels={"service": "db"})
        connections = Gauge("active_connections", labels={"service": "api"})

        agg.register(requests)
        agg.register(errors)
        agg.register(latency)
        agg.register(db_timer)
        agg.register(connections)

        # Simulate traffic
        for _ in range(100):
            requests.inc()
            latency.observe(0.05)

        for _ in range(5):
            errors.inc()

        connections.set(42.0)

        with db_timer.time():
            time.sleep(0.001)

        # Verify
        self.assertEqual(requests.get(), 100.0)
        self.assertEqual(errors.get(), 5.0)
        self.assertEqual(connections.get(), 42.0)
        self.assertEqual(latency.get_count(), 100)
        self.assertEqual(db_timer.get_count(), 1)

        # Verify aggregation
        self.assertEqual(agg.count(), 5)
        self.assertEqual(agg.aggregate_sum("counter"), 105.0)

        # Verify summary
        summary = agg.summary()
        self.assertEqual(len(summary), 5)
        self.assertIn("http_requests_total", summary)
        self.assertIn("db_query_duration_seconds", summary)

    def test_concurrent_access(self):
        """Test thread-safety with concurrent increments."""
        import threading

        c = Counter("requests_total")
        errors = []

        def worker():
            try:
                for _ in range(1000):
                    c.inc()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(c.get(), 10000.0)


if __name__ == "__main__":
    unittest.main()
