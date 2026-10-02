"""Tests for the APEX-OS monitoring system."""

import json
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from apex_os_bp.monitoring.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricRegistry,
    Timer,
)
from apex_os_bp.monitoring.logging_agg import (
    LogAggregator,
    LogEntry,
    LogLevel,
)
from apex_os_bp.monitoring.tracing import (
    Span,
    SpanContext,
    SpanKind,
    Tracer,
    TraceStatus,
)
from apex_os_bp.monitoring.alerting import (
    Alert,
    AlertManager,
    AlertRule,
    AlertSeverity,
    CallbackChannel,
    WebhookChannel,
)
from apex_os_bp.monitoring.dashboards import (
    Dashboard,
    DashboardManager,
    DataSource,
    Panel,
    PanelType,
)


class TestMetrics(unittest.TestCase):
    """Tests for metrics collection."""

    def test_counter_inc(self):
        counter = Counter("requests_total", "Total requests", ["method"])
        counter.inc(method="GET")
        counter.inc(method="GET")
        counter.inc(method="POST")
        self.assertEqual(counter.get(method="GET"), 2.0)
        self.assertEqual(counter.get(method="POST"), 1.0)

    def test_counter_reset(self):
        counter = Counter("test_counter")
        counter.inc(5)
        self.assertEqual(counter.get(), 5.0)
        counter.reset()
        self.assertEqual(counter.get(), 0.0)

    def test_counter_collect(self):
        counter = Counter("test_counter", labels=["env"])
        counter.inc(3, env="prod")
        values = counter.collect()
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].value, 3.0)
        self.assertEqual(values[0].labels["env"], "prod")

    def test_gauge_set_and_inc(self):
        gauge = Gauge("memory_usage")
        gauge.set(100.0)
        self.assertEqual(gauge.get(), 100.0)
        gauge.inc(50.0)
        self.assertEqual(gauge.get(), 150.0)
        gauge.dec(25.0)
        self.assertEqual(gauge.get(), 125.0)

    def test_gauge_labels(self):
        gauge = Gauge("cpu_usage", labels=["host"])
        gauge.set(75.0, host="server1")
        gauge.set(50.0, host="server2")
        self.assertEqual(gauge.get(host="server1"), 75.0)
        self.assertEqual(gauge.get(host="server2"), 50.0)

    def test_histogram_observe(self):
        hist = Histogram("request_duration")
        hist.observe(0.1)
        hist.observe(0.5)
        hist.observe(1.5)
        stats = hist.get_stats()
        self.assertEqual(stats["count"], 3)
        self.assertAlmostEqual(stats["sum"], 2.1, places=5)
        self.assertEqual(stats["min"], 0.1)
        self.assertEqual(stats["max"], 1.5)

    def test_histogram_buckets(self):
        hist = Histogram("request_duration", buckets=[0.1, 0.5, 1.0])
        hist.observe(0.05)
        hist.observe(0.3)
        hist.observe(0.7)
        hist.observe(2.0)
        counts = hist.get_bucket_counts()
        self.assertEqual(counts["0.1"], 1)
        self.assertEqual(counts["0.5"], 2)
        self.assertEqual(counts["1.0"], 3)
        self.assertEqual(counts["+Inf"], 4)

    def test_timer_context_manager(self):
        timer = Timer("operation_time")
        with timer.time():
            time.sleep(0.01)
        stats = timer.get_stats()
        self.assertEqual(stats["count"], 1)
        self.assertGreater(stats["sum"], 0.0)

    def test_timer_observe(self):
        timer = Timer("operation_time")
        timer.observe(0.5)
        timer.observe(1.5)
        stats = timer.get_stats()
        self.assertEqual(stats["count"], 2)
        self.assertAlmostEqual(stats["avg"], 1.0, places=5)

    def test_metric_registry(self):
        registry = MetricRegistry()
        counter = registry.register(Counter("test_counter"))
        gauge = registry.register(Gauge("test_gauge"))
        self.assertEqual(len(registry.names()), 2)
        self.assertIs(registry.get("test_counter"), counter)
        self.assertIs(registry.get("test_gauge"), gauge)

    def test_metric_registry_duplicate(self):
        registry = MetricRegistry()
        registry.register(Counter("test_counter"))
        with self.assertRaises(ValueError):
            registry.register(Counter("test_counter"))

    def test_metric_registry_collect_all(self):
        registry = MetricRegistry()
        counter = registry.register(Counter("test_counter", labels=["env"]))
        counter.inc(5, env="prod")
        values = registry.collect_all()
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].value, 5.0)

    def test_metric_registry_unregister(self):
        registry = MetricRegistry()
        registry.register(Counter("test_counter"))
        registry.unregister("test_counter")
        self.assertIsNone(registry.get("test_counter"))

    def test_metric_registry_clear(self):
        registry = MetricRegistry()
        registry.register(Counter("test_counter"))
        registry.register(Gauge("test_gauge"))
        registry.clear()
        self.assertEqual(len(registry.names()), 0)

    def test_counter_thread_safety(self):
        counter = Counter("test_counter")
        errors = []

        def increment():
            try:
                for _ in range(1000):
                    counter.inc()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(counter.get(), 10000.0)


class TestLogAggregation(unittest.TestCase):
    """Tests for log aggregation."""

    def test_log_entry_creation(self):
        entry = LogEntry(
            message="Test log",
            level=LogLevel.INFO,
            source="test_module",
            trace_id="abc123",
            span_id="def456",
            attributes={"key": "value"},
        )
        self.assertEqual(entry.message, "Test log")
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.trace_id, "abc123")
        self.assertEqual(entry.attributes["key"], "value")

    def test_log_entry_to_dict(self):
        entry = LogEntry(message="Test", level=LogLevel.ERROR)
        d = entry.to_dict()
        self.assertEqual(d["message"], "Test")
        self.assertEqual(d["level"], "error")
        self.assertIn("timestamp", d)

    def test_log_entry_to_json(self):
        entry = LogEntry(message="Test", level=LogLevel.WARNING)
        j = entry.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["message"], "Test")
        self.assertEqual(parsed["level"], "warning")

    def test_log_entry_from_dict(self):
        data = {
            "message": "Test",
            "level": "info",
            "source": "test",
            "trace_id": "abc",
            "span_id": "def",
            "attributes": {"k": "v"},
        }
        entry = LogEntry.from_dict(data)
        self.assertEqual(entry.message, "Test")
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.trace_id, "abc")

    def test_log_level_comparison(self):
        self.assertTrue(LogLevel.ERROR > LogLevel.WARNING)
        self.assertTrue(LogLevel.WARNING >= LogLevel.WARNING)
        self.assertTrue(LogLevel.INFO < LogLevel.ERROR)
        self.assertTrue(LogLevel.CRITICAL > LogLevel.INFO)

    def test_log_aggregator_log(self):
        agg = LogAggregator(min_level=LogLevel.INFO)
        entry = agg.log("Test message", level=LogLevel.INFO, source="test")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.message, "Test message")

    def test_log_aggregator_min_level(self):
        agg = LogAggregator(min_level=LogLevel.WARNING)
        entry = agg.log("Debug message", level=LogLevel.DEBUG)
        self.assertIsNone(entry)
        entry = agg.log("Warning message", level=LogLevel.WARNING)
        self.assertIsNotNone(entry)

    def test_log_aggregator_flush(self):
        agg = LogAggregator(batch_size=3)
        handler = MagicMock()
        agg.add_handler(handler)
        agg.log("msg1", level=LogLevel.INFO)
        agg.log("msg2", level=LogLevel.INFO)
        agg.log("msg3", level=LogLevel.INFO)
        handler.assert_called_once()
        batch = handler.call_args[0][0]
        self.assertEqual(len(batch), 3)

    def test_log_aggregator_filter(self):
        agg = LogAggregator()
        agg.add_filter(lambda e: "block" not in e.message.lower())
        entry1 = agg.log("Good message", level=LogLevel.INFO)
        entry2 = agg.log("Blocked message", level=LogLevel.INFO)
        self.assertIsNotNone(entry1)
        self.assertIsNone(entry2)

    def test_log_aggregator_search(self):
        agg = LogAggregator()
        agg.log("Error in module A", level=LogLevel.ERROR, source="module_a")
        agg.log("Info in module B", level=LogLevel.INFO, source="module_b")
        agg.log("Error in module C", level=LogLevel.ERROR, source="module_c")

        results = agg.search("Error", level=LogLevel.ERROR)
        self.assertEqual(len(results), 2)

        results = agg.search("module_b")
        self.assertEqual(len(results), 1)

    def test_log_aggregator_get_recent(self):
        agg = LogAggregator()
        for i in range(10):
            agg.log(f"Message {i}", level=LogLevel.INFO)
        recent = agg.get_recent(count=5)
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[-1].message, "Message 9")

    def test_log_aggregator_stats(self):
        agg = LogAggregator()
        agg.log("Test", level=LogLevel.INFO)
        stats = agg.get_stats()
        self.assertEqual(stats["total_aggregated"], 1)
        self.assertEqual(stats["buffered"], 1)

    def test_log_aggregator_clear(self):
        agg = LogAggregator()
        agg.log("Test", level=LogLevel.INFO)
        agg.clear()
        stats = agg.get_stats()
        self.assertEqual(stats["total_aggregated"], 0)
        self.assertEqual(stats["buffered"], 0)

    def test_log_aggregator_on_flush(self):
        agg = LogAggregator(batch_size=2)
        callback = MagicMock()
        agg.on_flush(callback)
        agg.log("msg1", level=LogLevel.INFO)
        agg.log("msg2", level=LogLevel.INFO)
        callback.assert_called_once()

    def test_log_aggregator_remove_handler(self):
        agg = LogAggregator()
        handler = MagicMock()
        agg.add_handler(handler)
        agg.remove_handler(handler)
        agg.log("Test", level=LogLevel.INFO)
        agg.flush()
        handler.assert_not_called()


class TestTracing(unittest.TestCase):
    """Tests for distributed tracing."""

    def test_span_creation(self):
        span = Span(
            name="test-span",
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id="span-parent",
            kind=SpanKind.SERVER,
        )
        self.assertEqual(span.name, "test-span")
        self.assertEqual(span.trace_id, "trace-123")
        self.assertEqual(span.span_id, "span-456")
        self.assertEqual(span.parent_span_id, "span-parent")
        self.assertEqual(span.kind, SpanKind.SERVER)

    def test_span_attributes(self):
        span = Span(name="test", trace_id="t", span_id="s")
        span.set_attribute("key", "value")
        self.assertEqual(span.attributes["key"], "value")
        span.set_attributes({"a": 1, "b": 2})
        self.assertEqual(span.attributes["a"], 1)
        self.assertEqual(span.attributes["b"], 2)

    def test_span_events(self):
        span = Span(name="test", trace_id="t", span_id="s")
        span.add_event("test_event", {"key": "value"})
        self.assertEqual(len(span.events), 1)
        self.assertEqual(span.events[0].name, "test_event")
        self.assertEqual(span.events[0].attributes["key"], "value")

    def test_span_status(self):
        span = Span(name="test", trace_id="t", span_id="s")
        span.set_status(TraceStatus.ERROR, "Something went wrong")
        self.assertEqual(span.status, TraceStatus.ERROR)
        self.assertEqual(span.attributes["status.description"], "Something went wrong")

    def test_span_record_exception(self):
        span = Span(name="test", trace_id="t", span_id="s")
        try:
            raise ValueError("test error")
        except ValueError as e:
            span.record_exception(e)
        self.assertEqual(span.status, TraceStatus.ERROR)
        self.assertEqual(len(span.events), 1)
        self.assertEqual(span.events[0].name, "exception")

    def test_span_duration(self):
        span = Span(name="test", trace_id="t", span_id="s")
        self.assertIsNone(span.duration)
        span.end()
        self.assertIsNotNone(span.duration)
        self.assertGreaterEqual(span.duration, 0.0)

    def test_span_context(self):
        span = Span(name="test", trace_id="t", span_id="s")
        ctx = span.get_context()
        self.assertEqual(ctx.trace_id, "t")
        self.assertEqual(ctx.span_id, "s")

    def test_span_context_headers(self):
        ctx = SpanContext(trace_id="t", span_id="s")
        headers = ctx.to_headers()
        self.assertEqual(headers["X-Trace-ID"], "t")
        self.assertEqual(headers["X-Span-ID"], "s")

    def test_span_context_from_headers(self):
        headers = {"X-Trace-ID": "t", "X-Span-ID": "s", "X-Trace-Flags": "1"}
        ctx = SpanContext.from_headers(headers)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.trace_id, "t")
        self.assertEqual(ctx.span_id, "s")

    def test_span_context_from_headers_missing(self):
        headers = {"X-Trace-ID": "t"}
        ctx = SpanContext.from_headers(headers)
        self.assertIsNone(ctx)

    def test_tracer_start_span(self):
        tracer = Tracer("test-service")
        span = tracer.start_span("test-operation", kind=SpanKind.SERVER)
        self.assertEqual(span.name, "test-operation")
        self.assertEqual(span.kind, SpanKind.SERVER)
        self.assertEqual(span.attributes["service.name"], "test-service")

    def test_tracer_start_span_with_parent(self):
        tracer = Tracer("test-service")
        parent_ctx = SpanContext(trace_id="parent-trace", span_id="parent-span")
        span = tracer.start_span("child-operation", parent_context=parent_ctx)
        self.assertEqual(span.trace_id, "parent-trace")
        self.assertEqual(span.parent_span_id, "parent-span")

    def test_tracer_end_span(self):
        tracer = Tracer("test-service")
        exporter = MagicMock()
        tracer.add_exporter(exporter)
        span = tracer.start_span("test-operation")
        tracer.end_span(span)
        exporter.assert_called_once_with(span)

    def test_tracer_get_trace(self):
        tracer = Tracer("test-service")
        span1 = tracer.start_span("op1")
        span2 = tracer.start_span("op2", parent_context=span1.get_context())
        trace = tracer.get_trace(span1.trace_id)
        self.assertEqual(len(trace), 2)

    def test_tracer_inject_extract(self):
        tracer = Tracer("test-service")
        span = tracer.start_span("test-op")
        headers = {}
        tracer.inject_context(span.get_context(), headers)
        self.assertIn("X-Trace-ID", headers)

        ctx = tracer.extract_context(headers)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.trace_id, span.trace_id)

    def test_tracer_clear(self):
        tracer = Tracer("test-service")
        tracer.start_span("test-op")
        tracer.clear()
        self.assertEqual(len(tracer.get_traces()), 0)

    def test_span_context_manager(self):
        tracer = Tracer("test-service")
        with tracer.start_span("test-op") as span:
            self.assertIsNotNone(span)
            span.set_attribute("key", "value")
        self.assertIsNotNone(span.end_time)

    def test_span_context_manager_exception(self):
        tracer = Tracer("test-service")
        with self.assertRaises(ValueError):
            with tracer.start_span("test-op") as span:
                raise ValueError("test")
        self.assertEqual(span.status, TraceStatus.ERROR)


class TestAlerting(unittest.TestCase):
    """Tests for the alerting system."""

    def test_alert_rule_evaluate(self):
        rule = AlertRule(
            name="high_cpu",
            description="CPU usage is high",
            severity=AlertSeverity.WARNING,
            metric_name="cpu_usage",
            threshold=80.0,
            comparison="gt",
        )
        self.assertTrue(rule.evaluate(90.0))
        self.assertFalse(rule.evaluate(70.0))

    def test_alert_rule_comparisons(self):
        rule_gt = AlertRule(name="t", description="t", severity=AlertSeverity.INFO, metric_name="m", threshold=10, comparison="gt")
        rule_lt = AlertRule(name="t", description="t", severity=AlertSeverity.INFO, metric_name="m", threshold=10, comparison="lt")
        rule_gte = AlertRule(name="t", description="t", severity=AlertSeverity.INFO, metric_name="m", threshold=10, comparison="gte")
        rule_lte = AlertRule(name="t", description="t", severity=AlertSeverity.INFO, metric_name="m", threshold=10, comparison="lte")
        rule_eq = AlertRule(name="t", description="t", severity=AlertSeverity.INFO, metric_name="m", threshold=10, comparison="eq")

        self.assertTrue(rule_gt.evaluate(11))
        self.assertFalse(rule_gt.evaluate(10))
        self.assertTrue(rule_lt.evaluate(9))
        self.assertFalse(rule_lt.evaluate(10))
        self.assertTrue(rule_gte.evaluate(10))
        self.assertTrue(rule_lte.evaluate(10))
        self.assertTrue(rule_eq.evaluate(10))

    def test_alert_rule_disabled(self):
        rule = AlertRule(
            name="test",
            description="test",
            severity=AlertSeverity.INFO,
            metric_name="m",
            threshold=10,
            comparison="gt",
            enabled=False,
        )
        self.assertFalse(rule.evaluate(100))

    def test_alert_manager_add_rule(self):
        mgr = AlertManager()
        rule = AlertRule(
            name="test",
            description="test",
            severity=AlertSeverity.INFO,
            metric_name="m",
            threshold=10,
            comparison="gt",
        )
        mgr.add_rule(rule)
        self.assertIs(mgr.get_rule("test"), rule)

    def test_alert_manager_evaluate(self):
        mgr = AlertManager()
        rule = AlertRule(
            name="high_cpu",
            description="CPU is high",
            severity=AlertSeverity.WARNING,
            metric_name="cpu_usage",
            threshold=80.0,
            comparison="gt",
        )
        mgr.add_rule(rule)
        alerts = mgr.evaluate("cpu_usage", 90.0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].rule_name, "high_cpu")
        self.assertEqual(alerts[0].severity, AlertSeverity.WARNING)

    def test_alert_manager_no_alert(self):
        mgr = AlertManager()
        rule = AlertRule(
            name="high_cpu",
            description="CPU is high",
            severity=AlertSeverity.WARNING,
            metric_name="cpu_usage",
            threshold=80.0,
            comparison="gt",
        )
        mgr.add_rule(rule)
        alerts = mgr.evaluate("cpu_usage", 50.0)
        self.assertEqual(len(alerts), 0)

    def test_alert_manager_cooldown(self):
        mgr = AlertManager()
        rule = AlertRule(
            name="test",
            description="test",
            severity=AlertSeverity.INFO,
            metric_name="m",
            threshold=10,
            comparison="gt",
            cooldown=60.0,
        )
        mgr.add_rule(rule)
        alerts1 = mgr.evaluate("m", 20.0)
        alerts2 = mgr.evaluate("m", 20.0)
        self.assertEqual(len(alerts1), 1)
        self.assertEqual(len(alerts2), 0)

    def test_alert_manager_duration(self):
        mgr = AlertManager()
        rule = AlertRule(
            name="test",
            description="test",
            severity=AlertSeverity.INFO,
            metric_name="m",
            threshold=10,
            comparison="gt",
            duration=1.0,
        )
        mgr.add_rule(rule)
        alerts1 = mgr.evaluate("m", 20.0)
        self.assertEqual(len(alerts1), 0)
        time.sleep(1.1)
        alerts2 = mgr.evaluate("m", 20.0)
        self.assertEqual(len(alerts2), 1)

    def test_alert_manager_channels(self):
        mgr = AlertManager()
        channel = CallbackChannel(lambda alert: None)
        mgr.add_channel(channel)
        rule = AlertRule(
            name="test",
            description="test",
            severity=AlertSeverity.INFO,
            metric_name="m",
            threshold=10,
            comparison="gt",
        )
        mgr.add_rule(rule)
        alerts = mgr.evaluate("m", 20.0)
        self.assertEqual(len(alerts), 1)

    def test_alert_manager_acknowledge(self):
        mgr = AlertManager()
        rule = AlertRule(
            name="test",
            description="test",
            severity=AlertSeverity.INFO,
            metric_name="m",
            threshold=10,
            comparison="gt",
        )
        mgr.add_rule(rule)
        mgr.evaluate("m", 20.0)
        count = mgr.acknowledge("test")
        self.assertEqual(count, 1)
        alerts = mgr.get_alerts(acknowledged=True)
        self.assertEqual(len(alerts), 1)

    def test_alert_manager_get_alerts_filter(self):
        mgr = AlertManager()
        rule1 = AlertRule(
            name="rule1",
            description="test",
            severity=AlertSeverity.WARNING,
            metric_name="m1",
            threshold=10,
            comparison="gt",
        )
        rule2 = AlertRule(
            name="rule2",
            description="test",
            severity=AlertSeverity.CRITICAL,
            metric_name="m2",
            threshold=10,
            comparison="gt",
        )
        mgr.add_rule(rule1)
        mgr.add_rule(rule2)
        mgr.evaluate("m1", 20.0)
        mgr.evaluate("m2", 20.0)

        warnings = mgr.get_alerts(severity=AlertSeverity.WARNING)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].rule_name, "rule1")

    def test_alert_manager_clear(self):
        mgr = AlertManager()
        rule = AlertRule(
            name="test",
            description="test",
            severity=AlertSeverity.INFO,
            metric_name="m",
            threshold=10,
            comparison="gt",
        )
        mgr.add_rule(rule)
        mgr.evaluate("m", 20.0)
        mgr.clear_alerts()
        self.assertEqual(len(mgr.get_alerts()), 0)

    def test_alert_manager_stats(self):
        mgr = AlertManager()
        rule = AlertRule(
            name="test",
            description="test",
            severity=AlertSeverity.INFO,
            metric_name="m",
            threshold=10,
            comparison="gt",
        )
        mgr.add_rule(rule)
        mgr.evaluate("m", 20.0)
        stats = mgr.get_stats()
        self.assertEqual(stats["rules"], 1)
        self.assertEqual(stats["total_alerts"], 1)

    def test_alert_manager_label_matching(self):
        mgr = AlertManager()
        rule = AlertRule(
            name="test",
            description="test",
            severity=AlertSeverity.INFO,
            metric_name="cpu_usage",
            threshold=80,
            comparison="gt",
            labels={"host": "server1"},
        )
        mgr.add_rule(rule)
        alerts = mgr.evaluate("cpu_usage", 90.0, labels={"host": "server1"})
        self.assertEqual(len(alerts), 1)
        alerts = mgr.evaluate("cpu_usage", 90.0, labels={"host": "server2"})
        self.assertEqual(len(alerts), 0)

    def test_webhook_channel(self):
        channel = WebhookChannel("http://example.com/webhook")
        alert = Alert(
            rule_name="test",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            value=90.0,
            threshold=80.0,
        )
        # Should not raise even if the request fails
        result = channel.send(alert)
        self.assertFalse(result)

    def test_alert_to_dict(self):
        alert = Alert(
            rule_name="test",
            severity=AlertSeverity.WARNING,
            message="Test",
            value=90.0,
            threshold=80.0,
            labels={"host": "server1"},
        )
        d = alert.to_dict()
        self.assertEqual(d["rule_name"], "test")
        self.assertEqual(d["severity"], "warning")
        self.assertEqual(d["value"], 90.0)


class TestDashboards(unittest.TestCase):
    """Tests for dashboards."""

    def test_data_source(self):
        ds = DataSource(
            name="prometheus",
            source_type="prometheus",
            url="http://localhost:9090",
            query="up",
        )
        self.assertEqual(ds.name, "prometheus")
        self.assertEqual(ds.source_type, "prometheus")
        d = ds.to_dict()
        self.assertEqual(d["name"], "prometheus")

    def test_panel_creation(self):
        panel = Panel(
            title="CPU Usage",
            panel_type=PanelType.GRAPH,
            data_source="prometheus",
            query="cpu_usage",
            unit="percent",
        )
        self.assertEqual(panel.title, "CPU Usage")
        self.assertEqual(panel.panel_type, PanelType.GRAPH)
        self.assertEqual(panel.unit, "percent")

    def test_panel_to_dict(self):
        panel = Panel(
            title="Test",
            panel_type=PanelType.STAT,
            grid_pos={"x": 0, "y": 0, "w": 6, "h": 4},
        )
        d = panel.to_dict()
        self.assertEqual(d["title"], "Test")
        self.assertEqual(d["type"], "stat")
        self.assertEqual(d["grid_pos"]["w"], 6)

    def test_panel_from_dict(self):
        data = {
            "title": "Test",
            "type": "graph",
            "data_source": "prometheus",
            "query": "up",
            "unit": "short",
            "thresholds": [],
            "targets": [],
            "grid_pos": {"x": 0, "y": 0, "w": 12, "h": 8},
            "legend": True,
            "description": "Test panel",
        }
        panel = Panel.from_dict(data)
        self.assertEqual(panel.title, "Test")
        self.assertEqual(panel.panel_type, PanelType.GRAPH)

    def test_dashboard_creation(self):
        dash = Dashboard(
            title="System Overview",
            description="Main system dashboard",
            refresh_interval=15.0,
            time_range="6h",
        )
        self.assertEqual(dash.title, "System Overview")
        self.assertEqual(dash.refresh_interval, 15.0)

    def test_dashboard_add_panel(self):
        dash = Dashboard(title="Test")
        panel = Panel(title="CPU", panel_type=PanelType.GRAPH)
        dash.add_panel(panel)
        self.assertEqual(len(dash.list_panels()), 1)
        self.assertIs(dash.get_panel("CPU"), panel)

    def test_dashboard_remove_panel(self):
        dash = Dashboard(title="Test")
        dash.add_panel(Panel(title="CPU", panel_type=PanelType.GRAPH))
        self.assertTrue(dash.remove_panel("CPU"))
        self.assertFalse(dash.remove_panel("NonExistent"))

    def test_dashboard_data_source(self):
        dash = Dashboard(title="Test")
        ds = DataSource(name="prom", source_type="prometheus", url="http://localhost:9090")
        dash.add_data_source(ds)
        self.assertIs(dash.get_data_source("prom"), ds)
        self.assertTrue(dash.remove_data_source("prom"))
        self.assertFalse(dash.remove_data_source("nonexistent"))

    def test_dashboard_to_dict(self):
        dash = Dashboard(title="Test", description="Test dash")
        dash.add_panel(Panel(title="Panel1", panel_type=PanelType.STAT))
        d = dash.to_dict()
        self.assertEqual(d["title"], "Test")
        self.assertEqual(len(d["panels"]), 1)

    def test_dashboard_to_json(self):
        dash = Dashboard(title="Test")
        dash.add_panel(Panel(title="Panel1", panel_type=PanelType.GRAPH))
        j = dash.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["title"], "Test")

    def test_dashboard_from_dict(self):
        data = {
            "title": "Test",
            "description": "Test dash",
            "refresh_interval": 30.0,
            "time_range": "1h",
            "tags": ["system"],
            "panels": [
                {
                    "title": "CPU",
                    "type": "graph",
                    "data_source": "prom",
                    "query": "cpu",
                    "unit": "percent",
                    "thresholds": [],
                    "targets": [],
                    "grid_pos": {"x": 0, "y": 0, "w": 12, "h": 8},
                    "legend": True,
                    "description": "",
                }
            ],
            "data_sources": {
                "prom": {
                    "name": "prom",
                    "type": "prometheus",
                    "url": "http://localhost:9090",
                    "query": "",
                    "refresh_interval": 30.0,
                    "headers": {},
                }
            },
        }
        dash = Dashboard.from_dict(data)
        self.assertEqual(dash.title, "Test")
        self.assertEqual(len(dash.list_panels()), 1)
        self.assertIsNotNone(dash.get_data_source("prom"))

    def test_dashboard_from_json(self):
        json_str = json.dumps({
            "title": "Test",
            "description": "",
            "refresh_interval": 30.0,
            "time_range": "1h",
            "tags": [],
            "panels": [],
            "data_sources": {},
        })
        dash = Dashboard.from_json(json_str)
        self.assertEqual(dash.title, "Test")

    def test_dashboard_manager_create(self):
        mgr = DashboardManager()
        dash = mgr.create_dashboard("System", description="System dash")
        self.assertIs(mgr.get_dashboard("System"), dash)

    def test_dashboard_manager_remove(self):
        mgr = DashboardManager()
        mgr.create_dashboard("Test")
        self.assertTrue(mgr.remove_dashboard("Test"))
        self.assertFalse(mgr.remove_dashboard("NonExistent"))

    def test_dashboard_manager_list(self):
        mgr = DashboardManager()
        mgr.create_dashboard("Dash1")
        mgr.create_dashboard("Dash2")
        titles = mgr.list_dashboard_titles()
        self.assertEqual(len(titles), 2)
        self.assertIn("Dash1", titles)
        self.assertIn("Dash2", titles)

    def test_dashboard_manager_to_json(self):
        mgr = DashboardManager()
        mgr.create_dashboard("Test")
        j = mgr.to_json()
        parsed = json.loads(j)
        self.assertIn("Test", parsed)


if __name__ == "__main__":
    unittest.main()
