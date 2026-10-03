"""Comprehensive tests for ContinuousBI module."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# 1. Real-time Dashboard Rendering
# ---------------------------------------------------------------------------
class TestDashboardRendering:
    @pytest.mark.asyncio
    async def test_dashboard_renders_with_valid_data(self):
        from modules.continuous_bi.dashboard import DashboardRenderer
        renderer = DashboardRenderer()
        data = {"metrics": [{"name": "revenue", "value": 1000}]}
        result = await renderer.render(data)
        assert result.status == "ok"
        assert "revenue" in result.html

    @pytest.mark.asyncio
    async def test_dashboard_handles_empty_metrics(self):
        from modules.continuous_bi.dashboard import DashboardRenderer
        renderer = DashboardRenderer()
        result = await renderer.render({"metrics": []})
        assert result.status == "ok"
        assert result.html is not None

    @pytest.mark.asyncio
    async def test_dashboard_realtime_update(self):
        from modules.continuous_bi.dashboard import DashboardRenderer
        renderer = DashboardRenderer()
        await renderer.render({"metrics": []})
        update = await renderer.push_update({"metrics": [{"name": "x", "value": 1}]})
        assert update.broadcast is True

    @pytest.mark.asyncio
    async def test_dashboard_widget_filter(self):
        from modules.continuous_bi.dashboard import DashboardRenderer
        renderer = DashboardRenderer()
        data = {"metrics": [{"name": "a", "value": 1}, {"name": "b", "value": 2}]}
        result = await renderer.render(data, widget_filter=["a"])
        assert "a" in result.html
        assert "b" not in result.html


# ---------------------------------------------------------------------------
# 2. Alert Rules
# ---------------------------------------------------------------------------
class TestAlertRules:
    @pytest.mark.asyncio
    async def test_alert_triggers_on_threshold_breach(self):
        from modules.continuous_bi.alerts import AlertEngine
        engine = AlertEngine()
        rule = {"metric": "cpu", "threshold": 90, "op": ">"}
        triggered = await engine.evaluate(rule, {"cpu": 95})
        assert triggered is True

    @pytest.mark.asyncio
    async def test_alert_not_triggered_below_threshold(self):
        from modules.continuous_bi.alerts import AlertEngine
        engine = AlertEngine()
        rule = {"metric": "cpu", "threshold": 90, "op": ">"}
        triggered = await engine.evaluate(rule, {"cpu": 50})
        assert triggered is False

    @pytest.mark.asyncio
    async def test_alert_cooldown_prevents_spam(self):
        from modules.continuous_bi.alerts import AlertEngine
        engine = AlertEngine(cooldown_seconds=60)
        rule = {"metric": "mem", "threshold": 80, "op": ">"}
        first = await engine.evaluate(rule, {"mem": 90})
        second = await engine.evaluate(rule, {"mem": 95})
        assert first is True
        assert second is False

    @pytest.mark.asyncio
    async def test_alert_severity_levels(self):
        from modules.continuous_bi.alerts import AlertEngine
        engine = AlertEngine()
        rule = {"metric": "disk", "threshold": 95, "op": ">", "severity": "critical"}
        alert = await engine.evaluate(rule, {"disk": 99})
        assert alert.severity == "critical"


# ---------------------------------------------------------------------------
# 3. Data Freshness Monitoring
# ---------------------------------------------------------------------------
class TestDataFreshness:
    @pytest.mark.asyncio
    async def test_fresh_data_passes_check(self):
        from modules.continuous_bi.freshness import FreshnessMonitor
        monitor = FreshnessMonitor(max_age_seconds=300)
        timestamp = datetime.utcnow() - timedelta(seconds=30)
        result = await monitor.check("orders", timestamp)
        assert result.is_fresh is True

    @pytest.mark.asyncio
    async def test_stale_data_fails_check(self):
        from modules.continuous_bi.freshness import FreshnessMonitor
        monitor = FreshnessMonitor(max_age_seconds=60)
        timestamp = datetime.utcnow() - timedelta(seconds=120)
        result = await monitor.check("orders", timestamp)
        assert result.is_fresh is False

    @pytest.mark.asyncio
    async def test_freshness_triggers_alert_on_stale(self):
        from modules.continuous_bi.freshness import FreshnessMonitor
        monitor = FreshnessMonitor(max_age_seconds=60)
        timestamp = datetime.utcnow() - timedelta(seconds=300)
        result = await monitor.check("events", timestamp)
        assert result.alert_triggered is True

    @pytest.mark.asyncio
    async def test_freshness_age_calculation(self):
        from modules.continuous_bi.freshness import FreshnessMonitor
        monitor = FreshnessMonitor(max_age_seconds=300)
        ts = datetime.utcnow() - timedelta(seconds=150)
        result = await monitor.check("metrics", ts)
        assert 140 <= result.age_seconds <= 160


# ---------------------------------------------------------------------------
# 4. Report Scheduling
# ---------------------------------------------------------------------------
class TestReportScheduling:
    @pytest.mark.asyncio
    async def test_schedule_daily_report(self):
        from modules.continuous_bi.scheduler import ReportScheduler
        scheduler = ReportScheduler()
        job = await scheduler.schedule(name="daily", cron="0 6 * * *")
        assert job.id is not None
        assert job.cron == "0 6 * * *"

    @pytest.mark.asyncio
    async def test_scheduled_report_executes(self):
        from modules.continuous_bi.scheduler import ReportScheduler
        scheduler = ReportScheduler()
        job = await scheduler.schedule(name="hourly", cron="0 * * * *")
        with patch.object(scheduler, "_execute", new=AsyncMock(return_value=True)):
            result = await scheduler.run_job(job.id)
            assert result is True

    @pytest.mark.asyncio
    async def test_schedule_invalid_cron_raises(self):
        from modules.continuous_bi.scheduler import ReportScheduler
        scheduler = ReportScheduler()
        with pytest.raises(ValueError):
            await scheduler.schedule(name="bad", cron="not-a-cron")

    @pytest.mark.asyncio
    async def test_list_scheduled_reports(self):
        from modules.continuous_bi.scheduler import ReportScheduler
        scheduler = ReportScheduler()
        await scheduler.schedule(name="r1", cron="0 0 * * *")
        await scheduler.schedule(name="r2", cron="0 12 * * *")
        jobs = await scheduler.list_jobs()
        assert len(jobs) == 2


# ---------------------------------------------------------------------------
# 5. Self-Service Analytics
# ---------------------------------------------------------------------------
class TestSelfServiceAnalytics:
    @pytest.mark.asyncio
    async def test_ad_hoc_query_returns_results(self):
        from modules.continuous_bi.self_service import SelfServiceAnalytics
        sa = SelfServiceAnalytics()
        with patch.object(sa, "_fetch", new=AsyncMock(return_value=[{"x": 1}])):
            result = await sa.query("SELECT * FROM events LIMIT 1")
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_query_with_filters(self):
        from modules.continuous_bi.self_service import SelfServiceAnalytics
        sa = SelfServiceAnalytics()
        with patch.object(sa, "_fetch", new=AsyncMock(return_value=[])):
            result = await sa.query("SELECT * FROM t", filters={"date": "2026-10-03"})
            assert result == []

    @pytest.mark.asyncio
    async def test_saved_query_retrieval(self):
        from modules.continuous_bi.self_service import SelfServiceAnalytics
        sa = SelfServiceAnalytics()
        await sa.save_query("q1", "SELECT 1")
        q = await sa.get_query("q1")
        assert q.sql == "SELECT 1"

    @pytest.mark.asyncio
    async def test_query_timeout_handling(self):
        from modules.continuous_bi.self_service import SelfServiceAnalytics
        sa = SelfServiceAnalytics(timeout_ms=100)
        with patch.object(sa, "_fetch", new=AsyncMock(side_effect=asyncio.TimeoutError)):
            with pytest.raises(asyncio.TimeoutError):
                await sa.query("SELECT pg_sleep(10)")
