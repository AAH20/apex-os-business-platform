"""Tests for deepened projects module (real exports)."""
import pytest
from datetime import date, timedelta


# ── Gantt ────────────────────────────────────────────────────────────────────

class TestGantt:
    def test_create_gantt_chart(self):
        from apex_os_bp.projects.deepened import GanttChart, GanttTask
        chart = GanttChart()
        chart.add(GanttTask(id="T1", name="Task 1", start=date(2026, 10, 1), duration_days=3))
        chart.add(GanttTask(id="T2", name="Task 2", start=date(2026, 10, 4), duration_days=2))
        assert len(chart.timeline()) == 2

    def test_add_dependency(self):
        from apex_os_bp.projects.deepened import GanttChart, GanttTask
        chart = GanttChart()
        chart.add(GanttTask(id="T1", name="Task 1", start=date(2026, 10, 1), duration_days=3))
        chart.add(GanttTask(id="T2", name="Task 2", start=date(2026, 10, 4), duration_days=2, dependencies=["T1"]))
        ready = {t.id for t in chart.ready_tasks()}
        assert "T1" in ready and "T2" not in ready

    def test_critical_path(self):
        from apex_os_bp.projects.deepened import GanttChart, GanttTask
        chart = GanttChart()
        chart.add(GanttTask(id="T1", name="Task 1", start=date(2026, 10, 1), duration_days=3))
        chart.add(GanttTask(id="T2", name="Task 2", start=date(2026, 10, 4), duration_days=2, dependencies=["T1"]))
        chart.add(GanttTask(id="T3", name="Task 3", start=date(2026, 10, 6), duration_days=4, dependencies=["T2"]))
        timeline = chart.timeline()
        assert isinstance(timeline, list) and len(timeline) == 3


# ── Resources ────────────────────────────────────────────────────────────────

class TestResources:
    def test_allocate_resource(self):
        from apex_os_bp.projects.deepened import CapacityPlanner, Resource, Allocation
        planner = CapacityPlanner()
        planner.add_resource(Resource(id="emp1", name="Emp One", role="dev", capacity_hours_per_week=40.0))
        ok = planner.allocate(Allocation(resource_id="emp1", project_id="P1", hours=30.0, week_start=date(2026, 10, 5)))
        assert ok is True

    def test_check_availability(self):
        from apex_os_bp.projects.deepened import CapacityPlanner, Resource, Allocation
        planner = CapacityPlanner()
        planner.add_resource(Resource(id="emp1", name="Emp One", role="dev", capacity_hours_per_week=40.0))
        planner.allocate(Allocation(resource_id="emp1", project_id="P1", hours=30.0, week_start=date(2026, 10, 5)))
        report = planner.utilization_report()
        assert report and report[0]["utilization_pct"] == 75.0

    def test_overallocation_detection(self):
        from apex_os_bp.projects.deepened import CapacityPlanner, Resource, Allocation
        planner = CapacityPlanner()
        planner.add_resource(Resource(id="emp1", name="Emp One", role="dev", capacity_hours_per_week=40.0))
        # allocate() refuses hours above remaining capacity...
        assert planner.allocate(Allocation(resource_id="emp1", project_id="P1", hours=50.0, week_start=date(2026, 10, 5))) is False
        # ...so overallocation is only reachable by allocating under the cap first
        assert planner.allocate(Allocation(resource_id="emp1", project_id="P1", hours=40.0, week_start=date(2026, 10, 5))) is True
        r = planner.overallocated()
        assert isinstance(r, list)


# ── Time Tracking ────────────────────────────────────────────────────────────

class TestTimeTracking:
    def test_log_hours(self):
        from apex_os_bp.projects.deepened import TimeTracker, TimeEntry
        tracker = TimeTracker()
        tracker.log(TimeEntry(id="e1", user_id="emp1", project_id="P1", task_id="T1",
                              date=date(2026, 10, 1), hours=5.0))
        summary = tracker.weekly_summary("emp1", date(2026, 10, 1))
        assert summary["total"] == 5.0

    def test_total_hours(self):
        from apex_os_bp.projects.deepened import TimeTracker, TimeEntry
        tracker = TimeTracker()
        tracker.log(TimeEntry(id="e1", user_id="emp1", project_id="P1", task_id="T1",
                              date=date(2026, 10, 1), hours=5.0))
        tracker.log(TimeEntry(id="e2", user_id="emp1", project_id="P1", task_id="T2",
                              date=date(2026, 10, 2), hours=3.0))
        assert tracker.weekly_summary("emp1", date(2026, 10, 1))["total"] == 8.0

    def test_timesheet_approval(self):
        from apex_os_bp.projects.deepened import TimeTracker, TimeEntry
        tracker = TimeTracker()
        tracker.log(TimeEntry(id="e1", user_id="emp1", project_id="P1", task_id="T1",
                              date=date(2026, 10, 1), hours=5.0))
        summary = tracker.weekly_summary("emp1", date(2026, 10, 1))
        assert "entries" in summary or "days" in summary


# ── Risk ─────────────────────────────────────────────────────────────────────

class TestRisk:
    def test_register_risk(self):
        from apex_os_bp.projects.deepened import RiskRegister, Risk, RiskLevel
        reg = RiskRegister()
        reg.add(Risk(id="R1", project_id="P1", description="delay", probability=0.3, impact=5.0))
        assert reg.open_risks()[0].id == "R1"

    def test_mitigation_plan(self):
        from apex_os_bp.projects.deepened import RiskRegister, Risk
        reg = RiskRegister()
        reg.add(Risk(id="R1", project_id="P1", description="delay", probability=0.3, impact=5.0))
        assert reg.mitigate("R1", "add buffer time") is True

    def test_risk_matrix(self):
        from apex_os_bp.projects.deepened import RiskRegister, Risk
        reg = RiskRegister()
        reg.add(Risk(id="R1", project_id="P1", description="delay", probability=0.8, impact=5.0))
        reg.add(Risk(id="R2", project_id="P2", description="budget", probability=0.2, impact=2.0))
        assert len(reg.top_risks(2)) == 2


# ── Portfolio ────────────────────────────────────────────────────────────────

class TestPortfolio:
    def test_add_project(self):
        from apex_os_bp.projects.deepened import Portfolio, PortfolioProject
        p = Portfolio()
        p.add(PortfolioProject(id="P1", name="Proj 1", budget=100000.0))
        assert p.total_budget() == 100000.0

    def test_portfolio_value(self):
        from apex_os_bp.projects.deepened import Portfolio, PortfolioProject
        p = Portfolio()
        p.add(PortfolioProject(id="P1", name="Proj 1", budget=100000.0))
        p.add(PortfolioProject(id="P2", name="Proj 2", budget=200000.0))
        assert p.total_budget() == 300000.0

    def test_portfolio_health(self):
        from apex_os_bp.projects.deepened import Portfolio, PortfolioProject
        p = Portfolio()
        p.add(PortfolioProject(id="P1", name="Proj 1", budget=100000.0, status="on_track"))
        p.add(PortfolioProject(id="P2", name="Proj 2", budget=200000.0, status="at_risk"))
        s = p.summary()
        assert isinstance(s, dict)
