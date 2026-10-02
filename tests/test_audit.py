"""Tests for the APEX-OS audit system."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apex_os_bp.audit import (
    AuditEvent,
    AuditSeverity,
    AuditStatus,
    AuditLogger,
    AuditTrail,
    AuditStore,
    InMemoryAuditStore,
    FileAuditStore,
    ComplianceFramework,
    ComplianceReport,
    ComplianceReporter,
    RetentionPolicy,
    DataRetentionManager,
    SearchQuery,
    AuditSearch,
)


class TestAuditLogging(unittest.TestCase):
    """Tests for audit logging (Feature 1)."""

    def setUp(self):
        self.store = InMemoryAuditStore()
        self.logger = AuditLogger(self.store)

    def test_log_basic_event(self):
        event = self.logger.log("user.login", actor="alice")
        self.assertEqual(event.action, "user.login")
        self.assertEqual(event.actor, "alice")
        self.assertEqual(event.severity, AuditSeverity.WARNING)
        self.assertEqual(event.status, AuditStatus.SUCCESS)
        self.assertIsNotNone(event.id)
        self.assertIsNotNone(event.timestamp)

    def test_log_with_metadata(self):
        event = self.logger.log(
            "file.access",
            actor="bob",
            resource="/data/secret.txt",
            resource_type="file",
            metadata={"file_size": 1024, "permission": "read"},
        )
        self.assertEqual(event.metadata["file_size"], 1024)
        self.assertEqual(event.resource, "/data/secret.txt")

    def test_log_with_severity_and_status(self):
        event = self.logger.log(
            "auth.failure",
            actor="eve",
            severity=AuditSeverity.WARNING,
            status=AuditStatus.FAILURE,
        )
        self.assertEqual(event.severity, AuditSeverity.WARNING)
        self.assertEqual(event.status, AuditStatus.FAILURE)

    def test_log_stores_event(self):
        self.logger.log("test.action", actor="tester")
        events = self.store.get_all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "test.action")

    def test_log_multiple_events(self):
        for i in range(5):
            self.logger.log(f"action.{i}", actor=f"user{i}")
        self.assertEqual(len(self.store.get_all()), 5)

    def test_context_manager_success(self):
        with self.logger.context("process.data", actor="worker"):
            pass
        events = self.store.get_all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "process.data")
        self.assertIsNotNone(events[0].duration_ms)

    def test_context_manager_failure(self):
        with self.assertRaises(ValueError):
            with self.logger.context("process.data", actor="worker"):
                raise ValueError("test error")
        events = self.store.get_all()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1].status, AuditStatus.FAILURE)
        self.assertEqual(events[1].severity, AuditSeverity.ERROR)

    def test_decorator_success(self):
        @self.logger.decorator("compute.heavy", actor="worker")
        def heavy_task():
            return 42

        result = heavy_task()
        self.assertEqual(result, 42)
        events = self.store.get_all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "compute.heavy")
        self.assertEqual(events[0].status, AuditStatus.SUCCESS)

    def test_decorator_failure(self):
        @self.logger.decorator("compute.heavy", actor="worker")
        def heavy_task():
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            heavy_task()
        events = self.store.get_all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].status, AuditStatus.FAILURE)

    def test_correlation_id(self):
        event = self.logger.log("action", actor="user", correlation_id="corr-123")
        self.assertEqual(event.correlation_id, "corr-123")

    def test_ip_and_user_agent(self):
        event = self.logger.log(
            "api.call",
            actor="service",
            ip_address="192.168.1.1",
            user_agent="test-agent/1.0",
        )
        self.assertEqual(event.ip_address, "192.168.1.1")
        self.assertEqual(event.user_agent, "test-agent/1.0")


class TestAuditTrail(unittest.TestCase):
    """Tests for audit trail (Feature 2)."""

    def setUp(self):
        self.store = InMemoryAuditStore()
        self.logger = AuditLogger(self.store)
        self.trail = AuditTrail(self.store)

    def test_get_events_chronological(self):
        self.logger.log("first", actor="a")
        self.logger.log("second", actor="b")
        self.logger.log("third", actor="c")
        events = self.trail.get_events()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].action, "first")
        self.assertEqual(events[2].action, "third")

    def test_get_by_correlation(self):
        self.logger.log("step1", actor="a", correlation_id="txn-1")
        self.logger.log("step2", actor="b", correlation_id="txn-1")
        self.logger.log("step3", actor="c", correlation_id="txn-2")
        events = self.trail.get_by_correlation("txn-1")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].action, "step1")
        self.assertEqual(events[1].action, "step2")

    def test_get_chain(self):
        e1 = self.logger.log("start", actor="a", correlation_id="chain-1")
        self.logger.log("middle", actor="b", correlation_id="chain-1")
        self.logger.log("end", actor="c", correlation_id="chain-1")
        chain = self.trail.get_chain(e1.id)
        self.assertEqual(len(chain), 3)

    def test_get_chain_single_event(self):
        e1 = self.logger.log("solo", actor="a")
        chain = self.trail.get_chain(e1.id)
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0].id, e1.id)

    def test_get_chain_not_found(self):
        chain = self.trail.get_chain("nonexistent-id")
        self.assertEqual(len(chain), 0)

    def test_get_timeline(self):
        self.logger.log("a1", actor="alice")
        self.logger.log("b1", actor="bob")
        self.logger.log("a2", actor="alice")
        timeline = self.trail.get_timeline(actor="alice")
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0].action, "a1")
        self.assertEqual(timeline[1].action, "a2")

    def test_summarize(self):
        self.logger.log("a", actor="alice", severity=AuditSeverity.INFO)
        self.logger.log(
            "b", actor="bob", severity=AuditSeverity.ERROR, status=AuditStatus.FAILURE
        )
        self.logger.log("c", actor="alice", correlation_id="corr-1")
        summary = self.trail.summarize()
        self.assertEqual(summary["total_events"], 3)
        self.assertEqual(summary["unique_actors"], 2)
        self.assertEqual(summary["unique_correlations"], 1)
        self.assertEqual(summary["by_severity"]["info"], 1)
        self.assertEqual(summary["by_severity"]["error"], 1)
        self.assertEqual(summary["by_status"]["success"], 2)
        self.assertEqual(summary["by_status"]["failure"], 1)


class TestComplianceReporting(unittest.TestCase):
    """Tests for compliance reporting (Feature 3)."""

    def setUp(self):
        self.store = InMemoryAuditStore()
        self.logger = AuditLogger(self.store)
        self.reporter = ComplianceReporter(self.store)

    def test_generate_soc2_report(self):
        self.logger.log("access.granted", actor="admin", resource="server1")
        self.logger.log("access.denied", actor="eve", status=AuditStatus.DENIED)
        report = self.reporter.generate(ComplianceFramework.SOC2)
        self.assertEqual(report.framework, ComplianceFramework.SOC2)
        self.assertGreater(len(report.findings), 0)
        self.assertIsInstance(report.passed, bool)
        self.assertGreaterEqual(report.pass_rate, 0.0)
        self.assertLessEqual(report.pass_rate, 1.0)

    def test_generate_gdpr_report(self):
        self.logger.log("data.access", actor="service", resource_type="personal_data")
        report = self.reporter.generate(ComplianceFramework.GDPR)
        self.assertEqual(report.framework, ComplianceFramework.GDPR)
        self.assertGreater(len(report.findings), 0)

    def test_generate_hipaa_report(self):
        self.logger.log("phi.access", actor="doctor", resource_type="phi")
        report = self.reporter.generate(ComplianceFramework.HIPAA)
        self.assertEqual(report.framework, ComplianceFramework.HIPAA)
        self.assertGreater(len(report.findings), 0)

    def test_generate_pci_dss_report(self):
        self.logger.log("payment.process", actor="gateway", resource_type="payment")
        report = self.reporter.generate(ComplianceFramework.PCI_DSS)
        self.assertEqual(report.framework, ComplianceFramework.PCI_DSS)
        self.assertGreater(len(report.findings), 0)

    def test_generate_iso27001_report(self):
        self.logger.log("security.scan", actor="scanner")
        report = self.reporter.generate(ComplianceFramework.ISO27001)
        self.assertEqual(report.framework, ComplianceFramework.ISO27001)
        self.assertGreater(len(report.findings), 0)

    def test_report_to_dict(self):
        self.logger.log("test", actor="tester")
        report = self.reporter.generate(ComplianceFramework.SOC2)
        d = report.to_dict()
        self.assertIn("framework", d)
        self.assertIn("generated_at", d)
        self.assertIn("passed", d)
        self.assertIn("pass_rate", d)
        self.assertIn("findings", d)
        self.assertIsInstance(d["findings"], list)

    def test_report_to_json(self):
        self.logger.log("test", actor="tester")
        report = self.reporter.generate(ComplianceFramework.SOC2)
        j = report.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["framework"], "soc2")

    def test_report_with_no_events(self):
        report = self.reporter.generate(ComplianceFramework.SOC2)
        self.assertEqual(report.total_events_analyzed, 0)
        self.assertIsInstance(report.passed, bool)

    def test_finding_structure(self):
        self.logger.log("test", actor="tester")
        report = self.reporter.generate(ComplianceFramework.SOC2)
        for finding in report.findings:
            self.assertIsNotNone(finding.control_id)
            self.assertIsNotNone(finding.description)
            self.assertIsNotNone(finding.severity)
            self.assertIsInstance(finding.passed, bool)


class TestDataRetention(unittest.TestCase):
    """Tests for data retention (Feature 4)."""

    def setUp(self):
        self.store = InMemoryAuditStore()
        self.logger = AuditLogger(self.store)
        self.manager = DataRetentionManager(self.store)

    def test_add_policy(self):
        policy = RetentionPolicy(name="short", retention_days=7)
        self.manager.add_policy(policy)
        self.assertEqual(self.manager.get_policy("short"), policy)

    def test_remove_policy(self):
        policy = RetentionPolicy(name="temp", retention_days=1)
        self.manager.add_policy(policy)
        self.assertTrue(self.manager.remove_policy("temp"))
        self.assertIsNone(self.manager.get_policy("temp"))

    def test_remove_nonexistent_policy(self):
        self.assertFalse(self.manager.remove_policy("nonexistent"))

    def test_list_policies(self):
        self.manager.add_policy(RetentionPolicy(name="p1", retention_days=30))
        self.manager.add_policy(RetentionPolicy(name="p2", retention_days=90))
        policies = self.manager.list_policies()
        self.assertEqual(len(policies), 2)

    def test_is_expired(self):
        policy = RetentionPolicy(name="test", retention_days=30)
        old_event = AuditEvent(
            timestamp=datetime.now(timezone.utc) - timedelta(days=31),
            action="old",
        )
        new_event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            action="new",
        )
        self.assertTrue(policy.is_expired(old_event))
        self.assertFalse(policy.is_expired(new_event))

    def test_policy_matches_severity(self):
        policy = RetentionPolicy(
            name="errors_only",
            retention_days=7,
            severity_filter={AuditSeverity.ERROR, AuditSeverity.CRITICAL},
        )
        error_event = AuditEvent(severity=AuditSeverity.ERROR)
        info_event = AuditEvent(severity=AuditSeverity.INFO)
        self.assertTrue(policy.matches(error_event))
        self.assertFalse(policy.matches(info_event))

    def test_policy_matches_resource_type(self):
        policy = RetentionPolicy(
            name="files_only",
            retention_days=7,
            resource_type_filter={"file", "document"},
        )
        file_event = AuditEvent(resource_type="file")
        db_event = AuditEvent(resource_type="database")
        self.assertTrue(policy.matches(file_event))
        self.assertFalse(policy.matches(db_event))

    def test_purge_expired(self):
        self.manager.add_policy(RetentionPolicy(name="short", retention_days=7))
        old_event = AuditEvent(
            timestamp=datetime.now(timezone.utc) - timedelta(days=30),
            action="old_action",
        )
        new_event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            action="new_action",
        )
        self.store.append(old_event)
        self.store.append(new_event)
        purged = self.manager.purge_expired()
        self.assertEqual(purged, 1)
        remaining = self.store.get_all()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].action, "new_action")

    def test_purge_with_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = str(Path(tmpdir) / "archive.jsonl")
            self.manager.add_policy(
                RetentionPolicy(
                    name="archive_policy",
                    retention_days=7,
                    archive_before_delete=True,
                    archive_path=archive_path,
                )
            )
            old_event = AuditEvent(
                timestamp=datetime.now(timezone.utc) - timedelta(days=30),
                action="archived_action",
            )
            self.store.append(old_event)
            purged = self.manager.purge_expired()
            self.assertEqual(purged, 1)
            self.assertTrue(Path(archive_path).exists())

    def test_get_retention_summary(self):
        self.manager.add_policy(
            RetentionPolicy(
                name="errors",
                retention_days=30,
                severity_filter={AuditSeverity.ERROR},
            )
        )
        self.logger.log("info_event", severity=AuditSeverity.INFO)
        self.logger.log("error_event", severity=AuditSeverity.ERROR)
        summary = self.manager.get_retention_summary()
        self.assertEqual(summary["errors"], 1)


class TestAuditSearch(unittest.TestCase):
    """Tests for audit search (Feature 5)."""

    def setUp(self):
        self.store = InMemoryAuditStore()
        self.logger = AuditLogger(self.store)
        self.search = AuditSearch(self.store)
        self.logger.log(
            "user.login", actor="alice", resource="app", severity=AuditSeverity.INFO
        )
        self.logger.log(
            "file.read", actor="bob", resource="/data/file.txt", resource_type="file"
        )
        self.logger.log(
            "user.login",
            actor="alice",
            resource="app",
            severity=AuditSeverity.WARNING,
            status=AuditStatus.FAILURE,
        )
        self.logger.log(
            "db.query",
            actor="charlie",
            resource="users_table",
            resource_type="database",
        )
        self.logger.log(
            "api.call",
            actor="alice",
            resource="/api/users",
            metadata={"method": "GET", "status_code": 200},
        )

    def test_search_by_actor(self):
        results = self.search.search(SearchQuery(actor="alice"))
        self.assertEqual(len(results), 3)

    def test_search_by_action(self):
        results = self.search.search(SearchQuery(action="user.login"))
        self.assertEqual(len(results), 2)

    def test_search_by_resource_type(self):
        results = self.search.search(SearchQuery(resource_type="file"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].action, "file.read")

    def test_search_by_severity(self):
        results = self.search.search(SearchQuery(severity=AuditSeverity.WARNING))
        self.assertEqual(len(results), 1)

    def test_search_by_status(self):
        results = self.search.search(SearchQuery(status=AuditStatus.FAILURE))
        self.assertEqual(len(results), 1)

    def test_search_by_time_range(self):
        now = datetime.now(timezone.utc)
        results = self.search.search(
            SearchQuery(
                start_time=now - timedelta(hours=1),
                end_time=now + timedelta(hours=1),
            )
        )
        self.assertEqual(len(results), 5)

    def test_search_by_metadata(self):
        results = self.search.search(
            SearchQuery(metadata_key="method", metadata_value="GET")
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].action, "api.call")

    def test_search_text(self):
        results = self.search.search(SearchQuery(text_search="alice"))
        self.assertEqual(len(results), 3)

    def test_search_with_limit(self):
        results = self.search.search(SearchQuery(limit=2))
        self.assertEqual(len(results), 2)

    def test_search_with_offset(self):
        results = self.search.search(SearchQuery(offset=3))
        self.assertEqual(len(results), 2)

    def test_search_with_limit_and_offset(self):
        results = self.search.search(SearchQuery(limit=2, offset=1))
        self.assertEqual(len(results), 2)

    def test_search_sort_by_actor(self):
        results = self.search.search(SearchQuery(sort_by="actor", sort_desc=False))
        self.assertEqual(results[0].actor, "alice")

    def test_search_sort_by_action(self):
        results = self.search.search(SearchQuery(sort_by="action", sort_desc=False))
        self.assertEqual(results[0].action, "api.call")

    def test_count(self):
        count = self.search.count(SearchQuery(actor="alice"))
        self.assertEqual(count, 3)

    def test_get_by_actor(self):
        results = self.search.get_by_actor("bob")
        self.assertEqual(len(results), 1)

    def test_get_by_action(self):
        results = self.search.get_by_action("db.query")
        self.assertEqual(len(results), 1)

    def test_get_by_time_range(self):
        now = datetime.now(timezone.utc)
        results = self.search.get_by_time_range(
            now - timedelta(hours=1), now + timedelta(hours=1)
        )
        self.assertEqual(len(results), 5)

    def test_get_by_severity(self):
        results = self.search.get_by_severity(AuditSeverity.INFO)
        self.assertEqual(len(results), 1)

    def test_get_by_status(self):
        results = self.search.get_by_status(AuditStatus.SUCCESS)
        self.assertEqual(len(results), 4)

    def test_full_text_search(self):
        results = self.search.full_text_search("alice")
        self.assertEqual(len(results), 3)

    def test_search_no_results(self):
        results = self.search.search(SearchQuery(actor="nonexistent"))
        self.assertEqual(len(results), 0)

    def test_search_combined_filters(self):
        results = self.search.search(
            SearchQuery(actor="alice", severity=AuditSeverity.INFO)
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].action, "user.login")


class TestFileAuditStore(unittest.TestCase):
    """Tests for file-based storage backend."""

    def test_file_store_append_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "audit.jsonl")
            store = FileAuditStore(path)
            event = AuditEvent(action="test", actor="tester")
            store.append(event)
            events = store.get_all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].action, "test")

    def test_file_store_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "audit.jsonl")
            store = FileAuditStore(path)
            store.append(AuditEvent(action="test"))
            store.clear()
            self.assertEqual(len(store.get_all()), 0)

    def test_file_store_nonexistent_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "nonexistent.jsonl")
            store = FileAuditStore(path)
            self.assertEqual(len(store.get_all()), 0)


class TestAuditEventModel(unittest.TestCase):
    """Tests for the AuditEvent data model."""

    def test_to_dict(self):
        event = AuditEvent(action="test", actor="tester")
        d = event.to_dict()
        self.assertEqual(d["action"], "test")
        self.assertEqual(d["actor"], "tester")
        self.assertEqual(d["severity"], "warning")
        self.assertEqual(d["status"], "success")
        self.assertIn("id", d)
        self.assertIn("timestamp", d)

    def test_from_dict(self):
        event = AuditEvent(
            action="test", actor="tester", severity=AuditSeverity.WARNING
        )
        d = event.to_dict()
        restored = AuditEvent.from_dict(d)
        self.assertEqual(restored.action, "test")
        self.assertEqual(restored.actor, "tester")
        self.assertEqual(restored.severity, AuditSeverity.WARNING)

    def test_roundtrip(self):
        event = AuditEvent(
            action="roundtrip",
            actor="tester",
            metadata={"key": "value"},
            severity=AuditSeverity.ERROR,
            status=AuditStatus.FAILURE,
            correlation_id="corr-123",
        )
        d = event.to_dict()
        restored = AuditEvent.from_dict(d)
        self.assertEqual(restored.action, event.action)
        self.assertEqual(restored.actor, event.actor)
        self.assertEqual(restored.metadata, event.metadata)
        self.assertEqual(restored.severity, event.severity)
        self.assertEqual(restored.status, event.status)
        self.assertEqual(restored.correlation_id, event.correlation_id)


if __name__ == "__main__":
    unittest.main()
