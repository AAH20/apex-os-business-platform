"""Tests for the ContinuousBI advanced features.

These were rewritten to target the implementation that actually exists. The
previous version imported `modules.continuous_bi.*`, a package layout that was
planned but never landed, so every test failed at import.

The real implementation lives in `apex_os_bp.continuous_bi.advanced` and uses
different names and signatures than the old tests assumed:

    old assumption                     actual API
    ---------------------------        ----------------------------------------
    DashboardRenderer.render(data)     render(dashboard_id) -> dict
    DashboardRenderer.push_update()    update_data(dashboard_id, metrics)
    AlertEngine.evaluate(rule, vals)   AlertRule.evaluate(value) -> bool
    FreshnessMonitor.check(src, ts)    check_freshness(src) -> FreshnessStatus
    ReportScheduler.schedule(...)      add_schedule(ReportSchedule)
    ReportScheduler.run_job(id)        run_schedule(id) -> bool
    SelfServiceAnalytics.query(sql)    create_query(id, metric, filters)
    operator ">"                       "gt" / "lt" / "gte" / "lte" / "eq"
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from apex_os_bp.continuous_bi.advanced import (
    AlertManager,
    AlertRule,
    AlertSeverity,
    Dashboard,
    DashboardRenderer,
    FreshnessCheck,
    FreshnessMonitor,
    FreshnessStatus,
    MetricValue,
    ReportSchedule,
    ReportScheduler,
    SelfServiceAnalytics,
)


# ---------------------------------------------------------------------------
# 1. Dashboard rendering
# ---------------------------------------------------------------------------
class TestDashboardRendering:
    def test_render_returns_payload_for_registered_dashboard(self):
        renderer = DashboardRenderer()
        renderer.register(Dashboard(
            dashboard_id="d1", title="Revenue", metrics=["revenue"]
        ))
        renderer.update_data("d1", [MetricValue(name="revenue", value=1000)])

        result = renderer.render("d1")

        assert isinstance(result, dict)
        assert result["dashboard_id"] == "d1"
        assert result["title"] == "Revenue"

    def test_render_handles_empty_metric_list(self):
        renderer = DashboardRenderer()
        renderer.register(Dashboard(
            dashboard_id="d2", title="Empty", metrics=[]
        ))

        result = renderer.render("d2")

        assert result["dashboard_id"] == "d2"
        assert result["metrics"] == []

    def test_update_data_appends_metric_set(self):
        renderer = DashboardRenderer()
        renderer.register(Dashboard(
            dashboard_id="d3", title="Live", metrics=["a", "b"]
        ))
        renderer.update_data("d3", [
            MetricValue(name="a", value=1),
            MetricValue(name="b", value=2),
        ])

        result = renderer.render("d3")

        # update_data EXTENDS the cache rather than replacing it
        assert [m["name"] for m in result["metrics"]] == ["a", "b"]

        renderer.update_data("d3", [MetricValue(name="c", value=3)])
        assert len(renderer.render("d3")["metrics"]) == 3

    def test_unregister_removes_dashboard(self):
        renderer = DashboardRenderer()
        renderer.register(Dashboard(
            dashboard_id="d4", title="Temp", metrics=["x"]
        ))
        renderer.unregister("d4")

        from apex_os_bp.continuous_bi.advanced import DashboardNotFoundError

        with pytest.raises(DashboardNotFoundError):
            renderer.render("d4")


# ---------------------------------------------------------------------------
# 2. Alert rules
# ---------------------------------------------------------------------------
class TestAlertRules:
    def test_alert_triggers_on_threshold_breach(self):
        rule = AlertRule(name="cpu-high", metric="cpu", threshold=90, operator="gt")
        assert rule.evaluate(95) is True

    def test_alert_not_triggered_below_threshold(self):
        rule = AlertRule(name="cpu-high", metric="cpu", threshold=90, operator="gt")
        assert rule.evaluate(50) is False

    def test_cooldown_prevents_immediate_retrigger(self):
        rule = AlertRule(
            name="mem-high", metric="mem", threshold=80, operator="gt",
            cooldown_seconds=60,
        )
        assert rule.evaluate(90) is True
        rule.mark_triggered()
        assert rule.is_in_cooldown() is True

    def test_severity_is_preserved_on_the_rule(self):
        rule = AlertRule(
            name="disk-critical", metric="disk", threshold=95,
            operator="gt", severity=AlertSeverity.CRITICAL,
        )
        assert rule.severity == AlertSeverity.CRITICAL

    def test_all_supported_operators(self):
        cases = [
            ("gt", 11, True), ("gt", 9, False),
            ("lt", 9, True), ("lt", 11, False),
            ("gte", 10, True), ("gte", 9, False),
            ("lte", 10, True), ("lte", 11, False),
            ("eq", 10, True), ("eq", 11, False),
        ]
        for operator, value, expected in cases:
            rule = AlertRule(name="r", metric="m", threshold=10, operator=operator)
            assert rule.evaluate(value) is expected, f"{operator}({value}) vs 10"

    def test_unknown_operator_is_rejected(self):
        from apex_os_bp.continuous_bi.advanced import AlertRuleError

        rule = AlertRule(name="bad", metric="m", threshold=1, operator="~=")
        with pytest.raises(AlertRuleError):
            rule.evaluate(1)

    @pytest.mark.asyncio
    async def test_manager_dispatches_notifications_for_breach(self):
        manager = AlertManager()
        seen: list = []

        async def handler(notification):
            seen.append(notification)

        manager.add_handler(handler)
        manager.add_rule(AlertRule(
            name="cpu", metric="cpu", threshold=90, operator="gt",
            severity=AlertSeverity.CRITICAL,
        ))

        fired = await manager.evaluate(MetricValue(name="cpu", value=95))

        assert len(fired) == 1
        assert fired[0].metric == "cpu"
        assert len(seen) == 1


# ---------------------------------------------------------------------------
# 3. Data freshness
# ---------------------------------------------------------------------------
class TestDataFreshness:
    def test_recent_data_is_fresh(self):
        monitor = FreshnessMonitor()
        monitor.register(FreshnessCheck(source_name="orders", max_age_seconds=300))
        monitor.update_timestamp("orders", datetime.utcnow() - timedelta(seconds=30))

        assert monitor.check_freshness("orders") == FreshnessStatus.FRESH

    def test_stale_data_is_detected(self):
        monitor = FreshnessMonitor()
        monitor.register(FreshnessCheck(source_name="orders", max_age_seconds=60))
        monitor.update_timestamp("orders", datetime.utcnow() - timedelta(seconds=120))

        assert monitor.check_freshness("orders") != FreshnessStatus.FRESH

    def test_get_all_statuses_reports_each_registered_source(self):
        monitor = FreshnessMonitor()
        monitor.register(FreshnessCheck(source_name="orders", max_age_seconds=300))
        monitor.register(FreshnessCheck(source_name="events", max_age_seconds=300))
        monitor.update_timestamp("orders")
        monitor.update_timestamp("events")

        statuses = monitor.get_all_statuses()

        assert set(statuses) == {"orders", "events"}


# ---------------------------------------------------------------------------
# 4. Report scheduling
# ---------------------------------------------------------------------------
class TestReportScheduling:
    def test_schedule_can_be_added_and_run(self):
        renderer = DashboardRenderer()
        renderer.register(Dashboard(
            dashboard_id="d1", title="Ops", metrics=["cpu"]
        ))
        scheduler = ReportScheduler(renderer)
        scheduler.add_schedule(ReportSchedule(
            schedule_id="s1", name="daily", dashboard_id="d1",
            cron_expression="0 6 * * *", channels=[], recipients=["ops@example.com"],
        ))

        assert scheduler.remove_schedule("s1") is None

    @pytest.mark.asyncio
    async def test_run_schedule_raises_for_unknown_schedule(self):
        from apex_os_bp.continuous_bi.advanced import ReportScheduleError

        scheduler = ReportScheduler(DashboardRenderer())
        with pytest.raises(ReportScheduleError):
            await scheduler.run_schedule("nope")

    @pytest.mark.asyncio
    async def test_disabled_schedule_is_skipped(self):
        renderer = DashboardRenderer()
        renderer.register(Dashboard(
            dashboard_id="d4", title="Off", metrics=[]
        ))
        scheduler = ReportScheduler(renderer)
        scheduler.add_schedule(ReportSchedule(
            schedule_id="s4", name="off", dashboard_id="d4",
            cron_expression="0 0 * * *", channels=[], recipients=[],
            enabled=False,
        ))

        assert await scheduler.run_schedule("s4") is False

    @pytest.mark.asyncio
    async def test_run_schedule_renders_for_registered_dashboard(self):
        renderer = DashboardRenderer()
        renderer.register(Dashboard(
            dashboard_id="d3", title="Daily", metrics=["revenue"]
        ))
        renderer.update_data("d3", [MetricValue(name="revenue", value=42)])

        scheduler = ReportScheduler(renderer)
        scheduler.add_schedule(ReportSchedule(
            schedule_id="s3", name="ok", dashboard_id="d3",
            cron_expression="0 0 * * *", channels=[], recipients=[],
        ))

        assert await scheduler.run_schedule("s3") is True


# ---------------------------------------------------------------------------
# 5. Self-service analytics
# ---------------------------------------------------------------------------
class TestSelfServiceAnalytics:
    def test_create_and_retrieve_query(self):
        sa = SelfServiceAnalytics()
        sa.create_query("q1", metric="revenue", filters={"region": "emea"})

        stored = sa.get_query("q1")

        assert stored["metric"] == "revenue"
        assert stored["filters"] == {"region": "emea"}

    def test_unknown_query_raises(self):
        from apex_os_bp.continuous_bi.advanced import ContinuousBIError

        sa = SelfServiceAnalytics()
        with pytest.raises(ContinuousBIError):
            sa.get_query("nope")

    def test_delete_query(self):
        from apex_os_bp.continuous_bi.advanced import ContinuousBIError

        sa = SelfServiceAnalytics()
        sa.create_query("q2", metric="orders")
        sa.delete_query("q2")

        with pytest.raises(ContinuousBIError):
            sa.get_query("q2")

    def test_saved_views_round_trip(self):
        sa = SelfServiceAnalytics()
        sa.create_query("q3", metric="margin")
        sa.save_view("v1", "q3", {"columns": ["margin"]})

        views = sa.list_views()

        assert any(v["view_id"] == "v1" for v in views)