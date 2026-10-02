"""Tests for the disaster recovery system."""

from __future__ import annotations

import time

import pytest

from apex_os_bp.disaster_recovery import (
    DRAlert,
    DRAlertSeverity,
    DRHealthReport,
    DRHealthStatus,
    DRMonitor,
    DRPlan,
    DRPlanner,
    DRTestRunner,
    DRTestResult,
    DRTestType,
    FailoverManager,
    FailoverResult,
    FailoverState,
    RecoveryTier,
    ReplicationLink,
    ReplicationManager,
    ReplicationStatus,
    ReplicationType,
)


# ---------------------------------------------------------------------------
# DR Planning tests
# ---------------------------------------------------------------------------


class TestDRPlanner:
    def test_create_plan_with_defaults(self):
        planner = DRPlanner()
        plan = planner.create_plan(
            name="test-plan",
            tier=RecoveryTier.TIER_1,
            primary_region="us-east-1",
            secondary_region="us-west-2",
            services=["api", "db"],
        )
        assert plan.name == "test-plan"
        assert plan.tier == RecoveryTier.TIER_1
        assert plan.rpo_seconds == 300
        assert plan.rto_seconds == 900
        assert plan.primary_region == "us-east-1"
        assert plan.secondary_region == "us-west-2"
        assert "api" in plan.services

    def test_create_plan_with_custom_rpo_rto(self):
        planner = DRPlanner()
        plan = planner.create_plan(
            name="custom-plan",
            tier=RecoveryTier.TIER_2,
            primary_region="eu-west-1",
            secondary_region="eu-central-1",
            rpo_seconds=600,
            rto_seconds=1800,
        )
        assert plan.rpo_seconds == 600
        assert plan.rto_seconds == 1800

    def test_get_plan(self):
        planner = DRPlanner()
        planner.create_plan(
            name="p1",
            tier=RecoveryTier.TIER_0,
            primary_region="a",
            secondary_region="b",
        )
        plan = planner.get_plan("p1")
        assert plan is not None
        assert plan.name == "p1"

    def test_get_plan_not_found(self):
        planner = DRPlanner()
        assert planner.get_plan("nonexistent") is None

    def test_list_plans(self):
        planner = DRPlanner()
        planner.create_plan(
            name="p1",
            tier=RecoveryTier.TIER_0,
            primary_region="a",
            secondary_region="b",
        )
        planner.create_plan(
            name="p2",
            tier=RecoveryTier.TIER_1,
            primary_region="c",
            secondary_region="d",
        )
        assert len(planner.list_plans()) == 2

    def test_plans_by_tier(self):
        planner = DRPlanner()
        planner.create_plan(
            name="p1",
            tier=RecoveryTier.TIER_0,
            primary_region="a",
            secondary_region="b",
        )
        planner.create_plan(
            name="p2",
            tier=RecoveryTier.TIER_1,
            primary_region="c",
            secondary_region="d",
        )
        tier0 = planner.plans_by_tier(RecoveryTier.TIER_0)
        assert len(tier0) == 1
        assert tier0[0].name == "p1"

    def test_untested_plans(self):
        planner = DRPlanner()
        planner.create_plan(
            name="p1",
            tier=RecoveryTier.TIER_0,
            primary_region="a",
            secondary_region="b",
        )
        untested = planner.untested_plans()
        assert len(untested) == 1

    def test_mark_tested(self):
        planner = DRPlanner()
        planner.create_plan(
            name="p1",
            tier=RecoveryTier.TIER_0,
            primary_region="a",
            secondary_region="b",
        )
        now = time.time()
        planner.mark_tested("p1", timestamp=now)
        plan = planner.get_plan("p1")
        assert plan.last_tested == now
        assert len(planner.untested_plans()) == 0

    def test_remove_plan(self):
        planner = DRPlanner()
        planner.create_plan(
            name="p1",
            tier=RecoveryTier.TIER_0,
            primary_region="a",
            secondary_region="b",
        )
        assert planner.remove_plan("p1") is True
        assert planner.get_plan("p1") is None
        assert planner.remove_plan("p1") is False

    def test_validate_plan_valid(self):
        planner = DRPlanner()
        plan = DRPlan(
            name="valid",
            tier=RecoveryTier.TIER_1,
            rpo_seconds=300,
            rto_seconds=900,
            primary_region="a",
            secondary_region="b",
            services=["api"],
        )
        assert planner.validate_plan(plan) == []

    def test_validate_plan_invalid(self):
        planner = DRPlanner()
        plan = DRPlan(
            name="",
            tier=RecoveryTier.TIER_1,
            rpo_seconds=-1,
            rto_seconds=0,
            primary_region="a",
            secondary_region="a",
        )
        issues = planner.validate_plan(plan)
        assert len(issues) > 0

    def test_plan_compliance(self):
        plan = DRPlan(
            name="p",
            tier=RecoveryTier.TIER_1,
            rpo_seconds=300,
            rto_seconds=900,
            primary_region="a",
            secondary_region="b",
        )
        assert plan.is_compliant(200, 800) is True
        assert plan.is_compliant(400, 800) is False
        assert plan.is_compliant(200, 1000) is False

    def test_plan_to_dict(self):
        plan = DRPlan(
            name="p",
            tier=RecoveryTier.TIER_1,
            rpo_seconds=300,
            rto_seconds=900,
            primary_region="a",
            secondary_region="b",
            services=["api"],
        )
        d = plan.to_dict()
        assert d["name"] == "p"
        assert d["tier"] == "tier_1"
        assert d["services"] == ["api"]


# ---------------------------------------------------------------------------
# Failover tests
# ---------------------------------------------------------------------------


class TestFailoverManager:
    def test_initial_state(self):
        fm = FailoverManager()
        assert fm.state == FailoverState.IDLE
        assert fm.history == []

    def test_failover_success(self):
        fm = FailoverManager()
        result = fm.failover("us-east-1", "us-west-2", services=["api"])
        assert result.success is True
        assert result.state == FailoverState.FAILOVER_COMPLETE
        assert result.source_region == "us-east-1"
        assert result.target_region == "us-west-2"
        assert result.duration_seconds is not None
        assert fm.state == FailoverState.FAILOVER_COMPLETE

    def test_failover_dry_run(self):
        fm = FailoverManager()
        result = fm.failover("us-east-1", "us-west-2", dry_run=True)
        assert result.success is True
        assert result.metadata.get("dry_run") is True

    def test_failover_unhealthy_service(self):
        fm = FailoverManager()
        fm.register_health_check("api", lambda: False)
        result = fm.failover("us-east-1", "us-west-2", services=["api"])
        assert result.success is False
        assert result.state == FailoverState.FAILED
        assert result.error is not None

    def test_failover_healthy_service(self):
        fm = FailoverManager()
        fm.register_health_check("api", lambda: True)
        result = fm.failover("us-east-1", "us-west-2", services=["api"])
        assert result.success is True

    def test_failback(self):
        fm = FailoverManager()
        result = fm.failback("us-west-2", "us-east-1", services=["api"])
        assert result.success is True
        assert result.state == FailoverState.FAILBACK_COMPLETE
        assert result.metadata.get("direction") == "failback"

    def test_failback_dry_run(self):
        fm = FailoverManager()
        result = fm.failback("us-west-2", "us-east-1", dry_run=True)
        assert result.success is True
        assert result.metadata.get("dry_run") is True

    def test_pre_failover_hook(self):
        fm = FailoverManager()
        calls = []
        fm.register_pre_failover_hook(lambda src, tgt: calls.append((src, tgt)))
        fm.failover("a", "b")
        assert calls == [("a", "b")]

    def test_post_failover_hook(self):
        fm = FailoverManager()
        results = []
        fm.register_post_failover_hook(lambda r: results.append(r))
        fm.failover("a", "b")
        assert len(results) == 1
        assert results[0].success is True

    def test_last_result(self):
        fm = FailoverManager()
        assert fm.last_result() is None
        fm.failover("a", "b")
        assert fm.last_result() is not None

    def test_reset(self):
        fm = FailoverManager()
        fm.failover("a", "b")
        fm.reset()
        assert fm.state == FailoverState.IDLE
        assert fm.history == []

    def test_result_to_dict(self):
        result = FailoverResult(
            success=True,
            source_region="a",
            target_region="b",
            state=FailoverState.FAILOVER_COMPLETE,
            started_at=1000.0,
            completed_at=1005.0,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["duration_seconds"] == 5.0


# ---------------------------------------------------------------------------
# Replication tests
# ---------------------------------------------------------------------------


class TestReplicationManager:
    def test_register_link(self):
        rm = ReplicationManager()
        link = rm.register_link("us-east-1", "us-west-2", "postgres")
        assert link.source_region == "us-east-1"
        assert link.target_region == "us-west-2"
        assert link.data_source == "postgres"
        assert link.status == ReplicationStatus.UNKNOWN

    def test_get_link(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        link = rm.get_link("a", "b", "db1")
        assert link is not None
        assert link.data_source == "db1"

    def test_get_link_not_found(self):
        rm = ReplicationManager()
        assert rm.get_link("x", "y", "z") is None

    def test_list_links(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        rm.register_link("a", "b", "db2")
        assert len(rm.list_links()) == 2

    def test_links_for_region(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        rm.register_link("b", "c", "db2")
        rm.register_link("x", "y", "db3")
        links = rm.links_for_region("b")
        assert len(links) == 2

    def test_update_lag_healthy(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        status = rm.update_lag("a", "b", "db1", lag_seconds=5.0)
        assert status == ReplicationStatus.HEALTHY

    def test_update_lag_lagging(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        status = rm.update_lag("a", "b", "db1", lag_seconds=60.0)
        assert status == ReplicationStatus.LAGGING

    def test_update_lag_degraded(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        status = rm.update_lag("a", "b", "db1", lag_seconds=600.0)
        assert status == ReplicationStatus.DEGRADED

    def test_update_lag_broken(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        status = rm.update_lag("a", "b", "db1", lag_seconds=7200.0)
        assert status == ReplicationStatus.BROKEN

    def test_update_lag_not_found(self):
        rm = ReplicationManager()
        with pytest.raises(ValueError):
            rm.update_lag("x", "y", "z", lag_seconds=0)

    def test_synchronous_replication_healthy(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1", replication_type=ReplicationType.SYNCHRONOUS)
        status = rm.update_lag("a", "b", "db1", lag_seconds=0)
        assert status == ReplicationStatus.HEALTHY

    def test_synchronous_replication_degraded(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1", replication_type=ReplicationType.SYNCHRONOUS)
        status = rm.update_lag("a", "b", "db1", lag_seconds=1.0)
        assert status == ReplicationStatus.DEGRADED

    def test_healthy_links(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        rm.register_link("a", "b", "db2")
        rm.update_lag("a", "b", "db1", lag_seconds=5.0)
        rm.update_lag("a", "b", "db2", lag_seconds=600.0)
        healthy = rm.healthy_links()
        assert len(healthy) == 1

    def test_unhealthy_links(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        rm.register_link("a", "b", "db2")
        rm.update_lag("a", "b", "db1", lag_seconds=5.0)
        rm.update_lag("a", "b", "db2", lag_seconds=600.0)
        unhealthy = rm.unhealthy_links()
        assert len(unhealthy) == 1

    def test_remove_link(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        assert rm.remove_link("a", "b", "db1") is True
        assert rm.get_link("a", "b", "db1") is None
        assert rm.remove_link("a", "b", "db1") is False

    def test_summary(self):
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        rm.register_link("a", "b", "db2")
        rm.update_lag("a", "b", "db1", lag_seconds=5.0)
        rm.update_lag("a", "b", "db2", lag_seconds=600.0)
        summary = rm.summary()
        assert summary["total_links"] == 2
        assert summary["healthy"] == 1
        assert summary["degraded"] == 1

    def test_link_to_dict(self):
        link = ReplicationLink(
            source_region="a",
            target_region="b",
            data_source="db1",
            replication_type=ReplicationType.ASYNCHRONOUS,
            lag_seconds=10.0,
        )
        d = link.to_dict()
        assert d["source_region"] == "a"
        assert d["replication_type"] == "asynchronous"
        assert d["lag_seconds"] == 10.0


# ---------------------------------------------------------------------------
# DR Testing tests
# ---------------------------------------------------------------------------


class TestDRTestRunner:
    def test_initial_state(self):
        runner = DRTestRunner()
        assert runner.last_result() is None
        assert runner.summary()["total_tests"] == 0

    def test_run_test_no_handler(self):
        runner = DRTestRunner()
        result = runner.run_test(DRTestType.FAILOVER, "plan1")
        assert result.success is False
        assert "No handler" in result.error

    def test_run_test_with_handler(self):
        runner = DRTestRunner()

        def handler(plan_name: str, **kwargs):
            return DRTestResult(
                test_type=DRTestType.FAILOVER,
                plan_name=plan_name,
                success=True,
                started_at=time.time(),
                completed_at=time.time(),
            )

        runner.register_handler(DRTestType.FAILOVER, handler)
        result = runner.run_test(DRTestType.FAILOVER, "plan1")
        assert result.success is True

    def test_run_failover_test(self):
        runner = DRTestRunner()

        def failover_fn(source_region, target_region, services, dry_run):
            return FailoverResult(
                success=True,
                source_region=source_region,
                target_region=target_region,
                state=FailoverState.FAILOVER_COMPLETE,
                started_at=time.time(),
                completed_at=time.time(),
                services_affected=services,
                metadata={"dry_run": dry_run},
            )

        result = runner.run_failover_test(
            "plan1", "a", "b", services=["api"], failover_fn=failover_fn
        )
        assert result.success is True
        assert result.test_type == DRTestType.FAILOVER
        assert result.rto_achieved is not None

    def test_run_failover_test_no_fn(self):
        runner = DRTestRunner()
        result = runner.run_failover_test("plan1", "a", "b")
        assert result.success is False
        assert "failover_fn is required" in result.error

    def test_run_data_integrity_test(self):
        runner = DRTestRunner()

        def check_fn(data_source):
            return True, "All records verified"

        result = runner.run_data_integrity_test(
            "plan1", "db1", check_fn=check_fn
        )
        assert result.success is True
        assert result.test_type == DRTestType.DATA_INTEGRITY

    def test_run_data_integrity_test_failure(self):
        runner = DRTestRunner()

        def check_fn(data_source):
            return False, "Checksum mismatch"

        result = runner.run_data_integrity_test(
            "plan1", "db1", check_fn=check_fn
        )
        assert result.success is False

    def test_run_replication_lag_test(self):
        runner = DRTestRunner()

        def get_lag_fn(src, tgt, ds):
            return 50.0

        result = runner.run_replication_lag_test(
            "plan1", "a", "b", "db1", max_lag_seconds=100.0, get_lag_fn=get_lag_fn
        )
        assert result.success is True
        assert result.rpo_achieved == 50.0

    def test_run_replication_lag_test_exceeded(self):
        runner = DRTestRunner()

        def get_lag_fn(src, tgt, ds):
            return 500.0

        result = runner.run_replication_lag_test(
            "plan1", "a", "b", "db1", max_lag_seconds=100.0, get_lag_fn=get_lag_fn
        )
        assert result.success is False

    def test_results_for_plan(self):
        runner = DRTestRunner()

        def handler(plan_name: str, **kwargs):
            return DRTestResult(
                test_type=DRTestType.FAILOVER,
                plan_name=plan_name,
                success=True,
                started_at=time.time(),
                completed_at=time.time(),
            )

        runner.register_handler(DRTestType.FAILOVER, handler)
        runner.run_test(DRTestType.FAILOVER, "plan1")
        runner.run_test(DRTestType.FAILOVER, "plan2")
        results = runner.results_for_plan("plan1")
        assert len(results) == 1

    def test_results_for_type(self):
        runner = DRTestRunner()

        def handler(plan_name: str, **kwargs):
            return DRTestResult(
                test_type=DRTestType.FAILOVER,
                plan_name=plan_name,
                success=True,
                started_at=time.time(),
                completed_at=time.time(),
            )

        runner.register_handler(DRTestType.FAILOVER, handler)
        runner.run_test(DRTestType.FAILOVER, "plan1")
        results = runner.results_for_type(DRTestType.FAILOVER)
        assert len(results) == 1

    def test_summary(self):
        runner = DRTestRunner()

        def handler(plan_name: str, **kwargs):
            return DRTestResult(
                test_type=DRTestType.FAILOVER,
                plan_name=plan_name,
                success=True,
                started_at=time.time(),
                completed_at=time.time(),
            )

        runner.register_handler(DRTestType.FAILOVER, handler)
        runner.run_test(DRTestType.FAILOVER, "plan1")
        runner.run_test(DRTestType.FAILOVER, "plan2")
        summary = runner.summary()
        assert summary["total_tests"] == 2
        assert summary["passed"] == 2
        assert summary["pass_rate"] == 1.0

    def test_clear_history(self):
        runner = DRTestRunner()

        def handler(plan_name: str, **kwargs):
            return DRTestResult(
                test_type=DRTestType.FAILOVER,
                plan_name=plan_name,
                success=True,
                started_at=time.time(),
                completed_at=time.time(),
            )

        runner.register_handler(DRTestType.FAILOVER, handler)
        runner.run_test(DRTestType.FAILOVER, "plan1")
        runner.clear_history()
        assert runner.summary()["total_tests"] == 0

    def test_result_to_dict(self):
        result = DRTestResult(
            test_type=DRTestType.FAILOVER,
            plan_name="p1",
            success=True,
            started_at=1000.0,
            completed_at=1005.0,
            rto_achieved=5.0,
        )
        d = result.to_dict()
        assert d["test_type"] == "failover"
        assert d["duration_seconds"] == 5.0
        assert d["rto_achieved"] == 5.0


# ---------------------------------------------------------------------------
# DR Monitoring tests
# ---------------------------------------------------------------------------


class TestDRMonitor:
    def test_initial_state(self):
        monitor = DRMonitor()
        assert monitor.active_alerts() == []

    def test_raise_alert(self):
        monitor = DRMonitor()
        alert = monitor.raise_alert(
            DRAlertSeverity.WARNING, "test", "Test alert"
        )
        assert alert.severity == DRAlertSeverity.WARNING
        assert alert.source == "test"
        assert alert.message == "Test alert"
        assert alert.acknowledged is False

    def test_acknowledge_alert(self):
        monitor = DRMonitor()
        alert = monitor.raise_alert(DRAlertSeverity.INFO, "test", "msg")
        assert monitor.acknowledge_alert(alert.alert_id) is True
        assert monitor.active_alerts() == []

    def test_acknowledge_nonexistent(self):
        monitor = DRMonitor()
        assert monitor.acknowledge_alert("nonexistent") is False

    def test_active_alerts_filter_by_severity(self):
        monitor = DRMonitor()
        monitor.raise_alert(DRAlertSeverity.WARNING, "a", "msg1")
        monitor.raise_alert(DRAlertSeverity.CRITICAL, "b", "msg2")
        warnings = monitor.active_alerts(severity=DRAlertSeverity.WARNING)
        assert len(warnings) == 1

    def test_alerts_for_source(self):
        monitor = DRMonitor()
        monitor.raise_alert(DRAlertSeverity.INFO, "repl", "msg1")
        monitor.raise_alert(DRAlertSeverity.INFO, "other", "msg2")
        alerts = monitor.alerts_for_source("repl")
        assert len(alerts) == 1

    def test_clear_alerts(self):
        monitor = DRMonitor()
        monitor.raise_alert(DRAlertSeverity.INFO, "a", "msg")
        monitor.clear_alerts()
        assert monitor.active_alerts() == []

    def test_alert_handler_called(self):
        monitor = DRMonitor()
        alerts = []
        monitor.register_alert_handler(lambda a: alerts.append(a))
        monitor.raise_alert(DRAlertSeverity.WARNING, "test", "msg")
        assert len(alerts) == 1

    def test_check_replication_health_healthy(self):
        monitor = DRMonitor()
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        rm.update_lag("a", "b", "db1", lag_seconds=5.0)
        status = monitor.check_replication_health(rm)
        assert status == DRHealthStatus.HEALTHY

    def test_check_replication_health_critical(self):
        monitor = DRMonitor()
        rm = ReplicationManager()
        rm.register_link("a", "b", "db1")
        rm.update_lag("a", "b", "db1", lag_seconds=7200.0)
        status = monitor.check_replication_health(rm)
        assert status == DRHealthStatus.CRITICAL

    def test_check_failover_readiness_ready(self):
        monitor = DRMonitor()
        rm = ReplicationManager()
        fm = FailoverManager()
        rm.register_link("a", "b", "db1")
        rm.update_lag("a", "b", "db1", lag_seconds=5.0)
        assert monitor.check_failover_readiness(fm, rm) is True

    def test_check_failover_readiness_not_ready(self):
        monitor = DRMonitor()
        rm = ReplicationManager()
        fm = FailoverManager()
        rm.register_link("a", "b", "db1")
        rm.update_lag("a", "b", "db1", lag_seconds=7200.0)
        assert monitor.check_failover_readiness(fm, rm) is False

    def test_check_plan_freshness_healthy(self):
        monitor = DRMonitor()
        status = monitor.check_plan_freshness([])
        assert status == DRHealthStatus.HEALTHY

    def test_check_plan_freshness_warning(self):
        monitor = DRMonitor()
        status = monitor.check_plan_freshness(["plan1", "plan2"])
        assert status == DRHealthStatus.WARNING

    def test_generate_health_report_healthy(self):
        monitor = DRMonitor()
        rm = ReplicationManager()
        fm = FailoverManager()
        rm.register_link("a", "b", "db1")
        rm.update_lag("a", "b", "db1", lag_seconds=5.0)
        report = monitor.generate_health_report(rm, fm, untested_plans=[])
        assert report.status == DRHealthStatus.HEALTHY
        assert report.failover_ready is True

    def test_generate_health_report_critical(self):
        monitor = DRMonitor()
        rm = ReplicationManager()
        fm = FailoverManager()
        rm.register_link("a", "b", "db1")
        rm.update_lag("a", "b", "db1", lag_seconds=7200.0)
        report = monitor.generate_health_report(rm, fm, untested_plans=[])
        assert report.status == DRHealthStatus.CRITICAL
        assert report.failover_ready is False

    def test_generate_health_report_with_untested(self):
        monitor = DRMonitor()
        rm = ReplicationManager()
        fm = FailoverManager()
        rm.register_link("a", "b", "db1")
        rm.update_lag("a", "b", "db1", lag_seconds=5.0)
        report = monitor.generate_health_report(rm, fm, untested_plans=["p1"])
        assert report.status == DRHealthStatus.WARNING
        assert "p1" in report.untested_plans

    def test_report_to_dict(self):
        report = DRHealthReport(
            status=DRHealthStatus.HEALTHY,
            timestamp=time.time(),
            failover_ready=True,
        )
        d = report.to_dict()
        assert d["status"] == "healthy"
        assert d["failover_ready"] is True

    def test_alert_to_dict(self):
        alert = DRAlert(
            alert_id="DR-000001",
            severity=DRAlertSeverity.WARNING,
            source="test",
            message="msg",
            timestamp=1000.0,
        )
        d = alert.to_dict()
        assert d["alert_id"] == "DR-000001"
        assert d["severity"] == "warning"
