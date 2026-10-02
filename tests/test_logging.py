"""Comprehensive tests for the APEX-OS logging system."""

from __future__ import annotations

import gzip
import io
import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from apex_os_bp.logging import (
    LogAggregator,
    LogAnalytics,
    LogEntry,
    LogLevel,
    LogRetention,
    LogSearch,
    RetentionPolicy,
    SearchQuery,
    StructuredLogger,
)


class TestLogEntry(unittest.TestCase):
    """Tests for LogEntry data class."""

    def test_create_basic_entry(self):
        entry = LogEntry("test message", level=LogLevel.INFO)
        self.assertEqual(entry.message, "test message")
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertIsNotNone(entry.timestamp)
        self.assertEqual(entry.source, "")
        self.assertEqual(entry.context, {})

    def test_to_dict(self):
        entry = LogEntry(
            "hello",
            level=LogLevel.ERROR,
            source="test",
            context={"key": "value"},
            trace_id="abc123",
        )
        data = entry.to_dict()
        self.assertEqual(data["message"], "hello")
        self.assertEqual(data["level"], "ERROR")
        self.assertEqual(data["level_value"], 40)
        self.assertEqual(data["source"], "test")
        self.assertEqual(data["context"], {"key": "value"})
        self.assertEqual(data["trace_id"], "abc123")
        self.assertIn("timestamp", data)

    def test_to_json_roundtrip(self):
        entry = LogEntry(
            "roundtrip",
            level=LogLevel.WARNING,
            source="svc",
            context={"n": 42},
        )
        json_str = entry.to_json()
        parsed = LogEntry.from_json(json_str)
        self.assertEqual(parsed.message, entry.message)
        self.assertEqual(parsed.level, entry.level)
        self.assertEqual(parsed.source, entry.source)
        self.assertEqual(parsed.context, entry.context)

    def test_from_dict(self):
        data = {
            "timestamp": "2025-01-15T10:30:00+00:00",
            "level": "DEBUG",
            "message": "dbg",
            "source": "mod",
            "context": {"a": 1},
        }
        entry = LogEntry.from_dict(data)
        self.assertEqual(entry.level, LogLevel.DEBUG)
        self.assertEqual(entry.message, "dbg")
        self.assertEqual(entry.source, "mod")

    def test_log_level_from_name(self):
        self.assertEqual(LogLevel.from_name("info"), LogLevel.INFO)
        self.assertEqual(LogLevel.from_name("ERROR"), LogLevel.ERROR)
        self.assertEqual(LogLevel.from_name("Critical"), LogLevel.CRITICAL)

    def test_log_level_from_value(self):
        self.assertEqual(LogLevel.from_value(10), LogLevel.DEBUG)
        self.assertEqual(LogLevel.from_value(50), LogLevel.CRITICAL)

    def test_invalid_level_name(self):
        with self.assertRaises(ValueError):
            LogLevel.from_name("INVALID")

    def test_entry_with_exception(self):
        exc = ValueError("bad value")
        entry = LogEntry("error occurred", level=LogLevel.ERROR, exception=exc)
        data = entry.to_dict()
        self.assertEqual(data["exception"]["type"], "ValueError")
        self.assertEqual(data["exception"]["message"], "bad value")


class TestStructuredLogger(unittest.TestCase):
    """Tests for StructuredLogger."""

    def test_create_logger(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        self.assertEqual(logger.name, "test")
        logger.close()

    def test_info_logging(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        entry = logger.info("hello world")
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.message, "hello world")

        output = stream.getvalue()
        self.assertIn("hello world", output)
        self.assertIn('"level": "INFO"', output)
        logger.close()

    def test_debug_below_threshold(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", level=LogLevel.WARNING, outputs=[stream])
        entry = logger.debug("should not appear")
        self.assertEqual(stream.getvalue(), "")
        logger.close()

    def test_error_logging(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        logger.error("something broke")
        output = stream.getvalue()
        self.assertIn("something broke", output)
        self.assertIn('"level": "ERROR"', output)
        logger.close()

    def test_critical_logging(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        logger.critical("system failure")
        self.assertIn("system failure", stream.getvalue())
        logger.close()

    def test_exception_logging(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        try:
            raise RuntimeError("test error")
        except RuntimeError as e:
            logger.exception("caught error", exc=e)

        output = stream.getvalue()
        self.assertIn("caught error", output)
        self.assertIn("RuntimeError", output)
        logger.close()

    def test_context_in_log_entry(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        logger.info("with context", context={"user_id": 123, "action": "login"})
        output = stream.getvalue()
        self.assertIn("user_id", output)
        self.assertIn("123", output)
        logger.close()

    def test_default_context(self):
        stream = io.StringIO()
        logger = StructuredLogger(
            "test", outputs=[stream], default_context={"app": "apex-os"}
        )
        logger.info("msg")
        output = stream.getvalue()
        self.assertIn("apex-os", output)
        logger.close()

    def test_bind_creates_child_logger(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        child = logger.bind(request_id="req-1")
        child.info("child message")
        output = stream.getvalue()
        self.assertIn("req-1", output)
        self.assertIn("child message", output)
        logger.close()

    def test_get_entries(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        logger.info("one")
        logger.info("two")
        entries = logger.get_entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].message, "one")
        self.assertEqual(entries[1].message, "two")
        logger.close()

    def test_clear_entries(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        logger.info("one")
        logger.clear()
        self.assertEqual(len(logger.get_entries()), 0)
        logger.close()

    def test_file_output(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            tmppath = f.name
        try:
            logger = StructuredLogger("test", outputs=[tmppath])
            logger.info("file test")
            logger.close()
            with open(tmppath) as f:
                content = f.read()
            self.assertIn("file test", content)
        finally:
            os.unlink(tmppath)

    def test_multiple_outputs(self):
        s1 = io.StringIO()
        s2 = io.StringIO()
        logger = StructuredLogger("test", outputs=[s1, s2])
        logger.info("broadcast")
        self.assertIn("broadcast", s1.getvalue())
        self.assertIn("broadcast", s2.getvalue())
        logger.close()

    def test_context_manager(self):
        stream = io.StringIO()
        with StructuredLogger("test", outputs=[stream]) as logger:
            logger.info("inside context")
        self.assertIn("inside context", stream.getvalue())

    def test_trace_id(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        logger.info("traced", trace_id="trace-xyz")
        output = stream.getvalue()
        self.assertIn("trace-xyz", output)
        logger.close()

    def test_warning_level(self):
        stream = io.StringIO()
        logger = StructuredLogger("test", outputs=[stream])
        logger.warning("warn msg")
        self.assertIn('"level": "WARNING"', stream.getvalue())
        logger.close()


class TestLogAggregator(unittest.TestCase):
    """Tests for LogAggregator."""

    def test_add_entry(self):
        agg = LogAggregator()
        entry = LogEntry("test", level=LogLevel.INFO)
        agg.add_entry(entry, source="svc1")
        self.assertEqual(agg.get_buffer_size(), 1)
        self.assertEqual(agg.get_total_aggregated(), 1)

    def test_add_entries(self):
        agg = LogAggregator()
        entries = [LogEntry(f"msg-{i}") for i in range(5)]
        count = agg.add_entries(entries, source="batch")
        self.assertEqual(count, 5)
        self.assertEqual(agg.get_buffer_size(), 5)

    def test_source_counts(self):
        agg = LogAggregator()
        agg.add_entry(LogEntry("a"), source="svc1")
        agg.add_entry(LogEntry("b"), source="svc1")
        agg.add_entry(LogEntry("c"), source="svc2")
        counts = agg.get_source_counts()
        self.assertEqual(counts["svc1"], 2)
        self.assertEqual(counts["svc2"], 1)

    def test_flush(self):
        agg = LogAggregator()
        agg.add_entry(LogEntry("one"))
        agg.add_entry(LogEntry("two"))
        flushed = agg.flush()
        self.assertEqual(len(flushed), 2)
        self.assertEqual(agg.get_buffer_size(), 0)

    def test_flush_callback(self):
        agg = LogAggregator()
        received = []
        agg.on_flush(lambda entries: received.append(len(entries)))
        agg.add_entry(LogEntry("x"))
        agg.flush()
        self.assertEqual(received, [1])

    def test_max_buffer_auto_flush(self):
        agg = LogAggregator(max_buffer_size=3)
        received = []
        agg.on_flush(lambda entries: received.append(len(entries)))
        for i in range(5):
            agg.add_entry(LogEntry(f"msg-{i}"))
        # Should have auto-flushed at 3, leaving 2 in buffer
        self.assertEqual(agg.get_buffer_size(), 2)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], 3)

    def test_merge_aggregators(self):
        agg1 = LogAggregator()
        agg2 = LogAggregator()
        agg1.add_entry(LogEntry("a"), source="s1")
        agg2.add_entry(LogEntry("b"), source="s2")
        agg1.merge(agg2)
        self.assertEqual(agg1.get_buffer_size(), 2)
        self.assertEqual(agg2.get_buffer_size(), 0)
        self.assertEqual(agg1.get_total_aggregated(), 2)

    def test_get_entries_filtered(self):
        agg = LogAggregator()
        now = datetime.now(timezone.utc)
        agg.add_entry(LogEntry("info", level=LogLevel.INFO))
        agg.add_entry(LogEntry("error", level=LogLevel.ERROR))
        entries = agg.get_entries(level=LogLevel.ERROR)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].message, "error")

    def test_merge_sorted(self):
        agg = LogAggregator()
        now = datetime.now(timezone.utc)
        e1 = LogEntry("a", timestamp=now)
        e2 = LogEntry("b", timestamp=now + timedelta(seconds=1))
        e3 = LogEntry("c", timestamp=now + timedelta(seconds=2))
        result = agg.merge_sorted([[e1, e3], [e2]])
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].message, "a")
        self.assertEqual(result[1].message, "b")
        self.assertEqual(result[2].message, "c")

    def test_clear(self):
        agg = LogAggregator()
        agg.add_entry(LogEntry("x"))
        agg.clear()
        self.assertEqual(agg.get_buffer_size(), 0)
        self.assertEqual(agg.get_total_aggregated(), 0)

    def test_aggregation_stats(self):
        from apex_os_bp.logging.aggregation import AggregationStats

        agg = LogAggregator()
        agg.add_entry(LogEntry("info", level=LogLevel.INFO))
        agg.add_entry(LogEntry("error", level=LogLevel.ERROR))
        agg.add_entry(LogEntry("error2", level=LogLevel.ERROR))
        stats = AggregationStats().compute(agg.get_entries())
        self.assertEqual(stats.total_entries, 3)
        self.assertEqual(stats.entries_by_level["ERROR"], 2)
        self.assertAlmostEqual(stats.error_rate, 2 / 3)
        self.assertIsNotNone(stats.time_range)


class TestLogSearch(unittest.TestCase):
    """Tests for LogSearch."""

    def _make_entries(self):
        now = datetime.now(timezone.utc)
        return [
            LogEntry("user login", level=LogLevel.INFO, source="auth", trace_id="t1",
                     context={"user_id": 1}, timestamp=now - timedelta(minutes=5)),
            LogEntry("user logout", level=LogLevel.INFO, source="auth", trace_id="t1",
                     context={"user_id": 1}, timestamp=now - timedelta(minutes=4)),
            LogEntry("db connection failed", level=LogLevel.ERROR, source="db",
                     context={"host": "db1"}, timestamp=now - timedelta(minutes=3)),
            LogEntry("cache miss", level=LogLevel.WARNING, source="cache",
                     context={"key": "session"}, timestamp=now - timedelta(minutes=2)),
            LogEntry("payment processed", level=LogLevel.INFO, source="payment",
                     context={"amount": 99.99}, timestamp=now - timedelta(minutes=1)),
        ]

    def test_add_and_count(self):
        search = LogSearch()
        search.add_entries(self._make_entries())
        self.assertEqual(search.count(), 5)

    def test_search_by_text(self):
        search = LogSearch(self._make_entries())
        results = search.find_by_text("login")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].message, "user login")

    def test_search_by_level(self):
        search = LogSearch(self._make_entries())
        results = search.find_by_level(LogLevel.ERROR)
        self.assertEqual(len(results), 1)
        self.assertIn("db connection", results[0].message)

    def test_search_by_trace(self):
        search = LogSearch(self._make_entries())
        results = search.find_by_trace("t1")
        self.assertEqual(len(results), 2)

    def test_search_by_time_range(self):
        search = LogSearch(self._make_entries())
        now = datetime.now(timezone.utc)
        results = search.find_by_time_range(
            now - timedelta(minutes=4, seconds=30), now
        )
        self.assertEqual(len(results), 4)

    def test_find_errors(self):
        search = LogSearch(self._make_entries())
        errors = search.find_errors()
        self.assertEqual(len(errors), 1)

    def test_search_query_builder(self):
        search = LogSearch(self._make_entries())
        query = (
            SearchQuery()
            .with_text("user")
            .with_level(LogLevel.INFO)
            .with_pagination(limit=10)
        )
        result = search.search(query)
        self.assertEqual(result.total, 2)
        self.assertEqual(result.count, 2)

    def test_search_with_context_filter(self):
        search = LogSearch(self._make_entries())
        query = SearchQuery().with_context(user_id=1)
        result = search.search(query)
        self.assertEqual(result.total, 2)

    def test_search_with_regex(self):
        search = LogSearch(self._make_entries())
        query = SearchQuery().with_regex(r"db.*failed")
        result = search.search(query)
        self.assertEqual(result.total, 1)

    def test_search_pagination(self):
        search = LogSearch(self._make_entries())
        query = SearchQuery().with_pagination(limit=2, offset=0)
        result = search.search(query)
        self.assertEqual(result.total, 5)
        self.assertEqual(result.count, 2)

        query2 = SearchQuery().with_pagination(limit=2, offset=2)
        result2 = search.search(query2)
        self.assertEqual(result2.count, 2)

    def test_search_result_to_dict(self):
        search = LogSearch(self._make_entries())
        query = SearchQuery().with_level(LogLevel.INFO)
        result = search.search(query)
        data = result.to_dict()
        self.assertIn("total", data)
        self.assertIn("count", data)
        self.assertIn("entries", data)

    def test_clear(self):
        search = LogSearch(self._make_entries())
        search.clear()
        self.assertEqual(search.count(), 0)

    def test_case_insensitive_search(self):
        search = LogSearch(self._make_entries())
        results = search.find_by_text("LOGIN")
        self.assertEqual(len(results), 1)

    def test_case_sensitive_search(self):
        search = LogSearch(self._make_entries())
        results = search.find_by_text("LOGIN", case_sensitive=True)
        self.assertEqual(len(results), 0)


class TestLogAnalytics(unittest.TestCase):
    """Tests for LogAnalytics."""

    def _make_entries(self):
        now = datetime.now(timezone.utc)
        return [
            LogEntry("info 1", level=LogLevel.INFO, source="web",
                     context={"duration_ms": 100}, timestamp=now - timedelta(minutes=10)),
            LogEntry("info 2", level=LogLevel.INFO, source="web",
                     context={"duration_ms": 200}, timestamp=now - timedelta(minutes=9)),
            LogEntry("error 1", level=LogLevel.ERROR, source="db",
                     context={"duration_ms": 500}, timestamp=now - timedelta(minutes=8)),
            LogEntry("warn 1", level=LogLevel.WARNING, source="cache",
                     context={"duration_ms": 50}, timestamp=now - timedelta(minutes=7)),
            LogEntry("error 2", level=LogLevel.ERROR, source="db",
                     context={"duration_ms": 600}, timestamp=now - timedelta(minutes=6)),
            LogEntry("info 3", level=LogLevel.INFO, source="web",
                     context={"duration_ms": 150}, timestamp=now - timedelta(minutes=5)),
        ]

    def test_compute_metrics(self):
        analytics = LogAnalytics(self._make_entries())
        metrics = analytics.compute_metrics()
        self.assertEqual(metrics.total_entries, 6)
        self.assertEqual(metrics.entries_by_level["INFO"], 3)
        self.assertEqual(metrics.entries_by_level["ERROR"], 2)
        self.assertEqual(metrics.entries_by_level["WARNING"], 1)
        self.assertEqual(metrics.error_count, 2)
        self.assertAlmostEqual(metrics.error_rate, 2 / 6)

    def test_top_errors(self):
        analytics = LogAnalytics(self._make_entries())
        top = analytics.top_errors()
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0][1], 1)  # each error appears once

    def test_top_messages(self):
        analytics = LogAnalytics(self._make_entries())
        metrics = analytics.compute_metrics()
        self.assertTrue(len(metrics.top_messages) > 0)

    def test_error_trend(self):
        analytics = LogAnalytics(self._make_entries())
        trend = analytics.error_trend(bucket_minutes=5)
        self.assertIsInstance(trend, list)
        self.assertTrue(len(trend) > 0)

    def test_latency_analysis(self):
        analytics = LogAnalytics(self._make_entries())
        stats = analytics.latency_analysis("duration_ms")
        self.assertEqual(stats["count"], 6)
        self.assertEqual(stats["min"], 50)
        self.assertEqual(stats["max"], 600)
        self.assertIn("mean", stats)
        self.assertIn("p95", stats)
        self.assertIn("p99", stats)

    def test_latency_analysis_empty(self):
        analytics = LogAnalytics()
        stats = analytics.latency_analysis("duration_ms")
        self.assertEqual(stats, {})

    def test_source_breakdown(self):
        analytics = LogAnalytics(self._make_entries())
        breakdown = analytics.source_breakdown()
        self.assertIn("web", breakdown)
        self.assertIn("db", breakdown)
        self.assertEqual(breakdown["web"]["total"], 3)
        self.assertEqual(breakdown["db"]["errors"], 2)

    def test_hourly_distribution(self):
        analytics = LogAnalytics(self._make_entries())
        dist = analytics.hourly_distribution()
        self.assertIsInstance(dist, dict)
        self.assertTrue(len(dist) > 0)

    def test_detect_anomalies(self):
        now = datetime.now(timezone.utc)
        entries = [LogEntry(f"msg-{i}", timestamp=now) for i in range(100)]
        entries.append(LogEntry("spike", timestamp=now))
        analytics = LogAnalytics(entries)
        anomalies = analytics.detect_anomalies(threshold_std=1.0)
        self.assertIsInstance(anomalies, list)

    def test_summary(self):
        analytics = LogAnalytics(self._make_entries())
        summary = analytics.summary()
        self.assertIn("metrics", summary)
        self.assertIn("top_errors", summary)
        self.assertIn("source_breakdown", summary)
        self.assertIn("anomalies", summary)

    def test_empty_metrics(self):
        analytics = LogAnalytics()
        metrics = analytics.compute_metrics()
        self.assertEqual(metrics.total_entries, 0)
        self.assertEqual(metrics.error_rate, 0.0)

    def test_clear(self):
        analytics = LogAnalytics(self._make_entries())
        analytics.clear()
        self.assertEqual(analytics.compute_metrics().total_entries, 0)

    def test_add_entries(self):
        analytics = LogAnalytics()
        analytics.add_entries(self._make_entries()[:3])
        self.assertEqual(analytics.compute_metrics().total_entries, 3)
        analytics.add_entries(self._make_entries()[3:])
        self.assertEqual(analytics.compute_metrics().total_entries, 6)


class TestLogRetention(unittest.TestCase):
    """Tests for LogRetention."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_dir = Path(self.tmpdir) / "logs"
        self.log_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_log_file(self, name: str, content: str = "test log\n") -> Path:
        fpath = self.log_dir / name
        fpath.write_text(content)
        return fpath

    def test_scan_files(self):
        self._create_log_file("app.log")
        self._create_log_file("error.log")
        self._create_log_file("old.log.1")
        retention = LogRetention(self.log_dir)
        files = retention.scan_files()
        self.assertEqual(len(files), 3)

    def test_get_file_age_days(self):
        fpath = self._create_log_file("test.log")
        retention = LogRetention(self.log_dir)
        age = retention.get_file_age_days(fpath)
        self.assertAlmostEqual(age, 0.0, places=1)

    def test_get_total_size(self):
        self._create_log_file("a.log", "hello")
        self._create_log_file("b.log", "world!")
        retention = LogRetention(self.log_dir)
        self.assertEqual(retention.get_total_size(), 11)

    def test_archive_file(self):
        fpath = self._create_log_file("app.log", "log content")
        policy = RetentionPolicy(compress_archives=False)
        retention = LogRetention(self.log_dir, policy=policy)
        dest = retention.archive_file(fpath)
        self.assertTrue(dest.exists())
        self.assertEqual(dest.read_text(), "log content")

    def test_archive_compress(self):
        fpath = self._create_log_file("app.log", "compress me")
        policy = RetentionPolicy(compress_archives=True)
        retention = LogRetention(self.log_dir, policy=policy)
        dest = retention.archive_file(fpath)
        self.assertTrue(str(dest).endswith(".gz"))
        with gzip.open(dest, "rt") as f:
            self.assertEqual(f.read(), "compress me")

    def test_compress_file(self):
        fpath = self._create_log_file("test.log", "data")
        retention = LogRetention(self.log_dir)
        compressed = retention.compress_file(fpath)
        self.assertFalse(fpath.exists())
        self.assertTrue(compressed.exists())
        with gzip.open(compressed, "rt") as f:
            self.assertEqual(f.read(), "data")

    def test_delete_file(self):
        fpath = self._create_log_file("delete.log", "bye")
        retention = LogRetention(self.log_dir)
        freed = retention.delete_file(fpath)
        self.assertEqual(freed, 3)
        self.assertFalse(fpath.exists())

    def test_cleanup_dry_run(self):
        fpath = self._create_log_file("app.log")
        # Make file old
        old_time = time.time() - (40 * 86400)  # 40 days ago
        os.utime(fpath, (old_time, old_time))

        policy = RetentionPolicy(max_age_days=30)
        retention = LogRetention(self.log_dir, policy=policy)
        report = retention.cleanup(dry_run=True)
        self.assertEqual(report.files_deleted, 1)
        self.assertTrue(fpath.exists())  # dry run doesn't delete

    def test_cleanup_actual(self):
        fpath = self._create_log_file("app.log")
        old_time = time.time() - (40 * 86400)
        os.utime(fpath, (old_time, old_time))

        policy = RetentionPolicy(max_age_days=30)
        retention = LogRetention(self.log_dir, policy=policy)
        report = retention.cleanup(dry_run=False)
        self.assertEqual(report.files_deleted, 1)
        self.assertFalse(fpath.exists())
        self.assertGreater(report.bytes_freed, 0)

    def test_cleanup_archive(self):
        fpath = self._create_log_file("app.log", "archive me")
        old_time = time.time() - (10 * 86400)  # 10 days ago
        os.utime(fpath, (old_time, old_time))

        policy = RetentionPolicy(
            max_age_days=30,
            archive_after_days=7,
            compress_archives=True,
        )
        retention = LogRetention(self.log_dir, policy=policy)
        report = retention.cleanup(dry_run=False)
        self.assertEqual(report.files_archived, 1)
        self.assertEqual(report.files_compressed, 1)

    def test_max_files_enforcement(self):
        for i in range(10):
            self._create_log_file(f"app-{i}.log", f"log {i}")

        policy = RetentionPolicy(max_files=5, max_age_days=365)
        retention = LogRetention(self.log_dir, policy=policy)
        report = retention.cleanup(dry_run=False)
        self.assertEqual(report.files_deleted, 5)
        self.assertEqual(len(retention.scan_files()), 5)

    def test_prune_entries(self):
        now = datetime.now(timezone.utc)
        entries = [
            LogEntry(f"msg-{i}", timestamp=now - timedelta(hours=i))
            for i in range(10)
        ]
        retention = LogRetention(self.log_dir)
        pruned = retention.prune_entries(entries, max_age=timedelta(hours=5), keep_minimum=0)
        self.assertTrue(len(pruned) < 10)

    def test_prune_keeps_minimum(self):
        now = datetime.now(timezone.utc)
        entries = [
            LogEntry(f"msg-{i}", timestamp=now - timedelta(hours=i))
            for i in range(5)
        ]
        retention = LogRetention(self.log_dir)
        pruned = retention.prune_entries(
            entries, max_age=timedelta(hours=1), keep_minimum=3
        )
        self.assertEqual(len(pruned), 3)

    def test_rotate_file(self):
        fpath = self._create_log_file("rotate.log", "x" * 2000)
        retention = LogRetention(self.log_dir)
        rotated = retention.rotate_file(fpath, max_size=1000)
        self.assertIsNotNone(rotated)
        self.assertFalse(fpath.exists())
        self.assertTrue(rotated.exists())

    def test_rotate_no_rotation_needed(self):
        fpath = self._create_log_file("small.log", "tiny")
        retention = LogRetention(self.log_dir)
        result = retention.rotate_file(fpath, max_size=10000)
        self.assertIsNone(result)
        self.assertTrue(fpath.exists())

    def test_retention_summary(self):
        self._create_log_file("a.log", "hello")
        self._create_log_file("b.log", "world")
        retention = LogRetention(self.log_dir)
        summary = retention.get_retention_summary()
        self.assertEqual(summary["total_files"], 2)
        self.assertEqual(summary["total_size_bytes"], 10)
        self.assertIn("policy", summary)

    def test_retention_policy_should_archive(self):
        policy = RetentionPolicy(archive_after_days=7)
        old = datetime.now(timezone.utc) - timedelta(days=10)
        self.assertTrue(policy.should_archive(old))

    def test_retention_policy_should_delete(self):
        policy = RetentionPolicy(max_age_days=30)
        old = datetime.now(timezone.utc) - timedelta(days=40)
        self.assertTrue(policy.should_delete(old))

    def test_retention_policy_size_check(self):
        policy = RetentionPolicy(max_size_bytes=1000)
        self.assertTrue(policy.is_within_size(500))
        self.assertFalse(policy.is_within_size(1500))

    def test_cleanup_by_level(self):
        entries = [
            LogEntry("info", level=LogLevel.INFO),
            LogEntry("error", level=LogLevel.ERROR),
            LogEntry("debug", level=LogLevel.DEBUG),
        ]
        retention = LogRetention(self.log_dir)
        filtered = retention.cleanup_by_level(entries, LogLevel.ERROR)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].level, LogLevel.ERROR)

    def test_pre_cleanup_hook(self):
        fpath = self._create_log_file("hook.log")
        old_time = time.time() - (40 * 86400)
        os.utime(fpath, (old_time, old_time))

        hook_calls = []
        policy = RetentionPolicy(max_age_days=30)
        retention = LogRetention(self.log_dir, policy=policy)
        retention.on_pre_cleanup(lambda p: hook_calls.append(str(p)))
        retention.cleanup()
        self.assertEqual(len(hook_calls), 1)

    def test_post_cleanup_hook(self):
        self._create_log_file("hook.log")
        hook_calls = []
        retention = LogRetention(self.log_dir)
        retention.on_post_cleanup(lambda r: hook_calls.append(r))
        retention.cleanup()
        self.assertEqual(len(hook_calls), 1)

    def test_report_to_dict(self):
        from apex_os_bp.logging.retention import RetentionReport

        report = RetentionReport(
            files_archived=2,
            files_deleted=3,
            bytes_freed=1000,
        )
        data = report.to_dict()
        self.assertEqual(data["files_archived"], 2)
        self.assertEqual(data["files_deleted"], 3)
        self.assertEqual(data["bytes_freed"], 1000)
        self.assertIn("errors", data)
        self.assertIn("archived_files", data)


class TestIntegration(unittest.TestCase):
    """Integration tests across all logging components."""

    def test_full_pipeline(self):
        """Test logging -> aggregation -> search -> analytics."""
        stream = io.StringIO()
        logger = StructuredLogger("integration", outputs=[stream])

        # Generate logs
        logger.info("server started", context={"port": 8080})
        logger.info("request received", context={"method": "GET", "path": "/api"})
        logger.error("db timeout", context={"host": "db1", "duration_ms": 5000})
        logger.warning("high memory", context={"usage_pct": 85})
        logger.info("request completed", context={"status": 200, "duration_ms": 150})

        entries = logger.get_entries()
        self.assertEqual(len(entries), 5)

        # Aggregate
        agg = LogAggregator()
        agg.add_entries(entries, source="integration")
        self.assertEqual(agg.get_buffer_size(), 5)

        # Search
        search = LogSearch(agg.get_entries())
        errors = search.find_errors()
        self.assertEqual(len(errors), 1)

        # Analytics
        analytics = LogAnalytics(agg.get_entries())
        metrics = analytics.compute_metrics()
        self.assertEqual(metrics.total_entries, 5)
        self.assertEqual(metrics.error_count, 1)

        logger.close()

    def test_structured_to_search_to_analytics(self):
        """Test JSON roundtrip through all components."""
        entry = LogEntry(
            "test",
            level=LogLevel.INFO,
            source="test",
            context={"key": "value"},
        )
        json_str = entry.to_json()
        parsed = LogEntry.from_json(json_str)

        search = LogSearch([parsed])
        results = search.find_by_text("test")
        self.assertEqual(len(results), 1)

        analytics = LogAnalytics(results)
        metrics = analytics.compute_metrics()
        self.assertEqual(metrics.total_entries, 1)

    def test_logger_to_file_to_retention(self):
        """Test writing logs to file and applying retention."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "app.log"
            logger = StructuredLogger("filetest", outputs=[log_file])
            logger.info("retention test")
            logger.close()

            self.assertTrue(log_file.exists())

            retention = LogRetention(Path(tmpdir))
            files = retention.scan_files()
            self.assertEqual(len(files), 1)


if __name__ == "__main__":
    unittest.main()
