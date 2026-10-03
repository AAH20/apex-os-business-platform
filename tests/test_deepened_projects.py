"""Tests for deepened project modules: Gantt, resources, time tracking, risk, portfolio."""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock


# ── Gantt ────────────────────────────────────────────────────────────────────

class TestGantt:
    def test_create_gantt_chart(self):
        from apex_os_bp.projects.deepened import GanttManager
        mgr = GanttManager()
        chart = mgr.create_chart("Project A", tasks=["T1", "T2"])
        assert chart["project"] == "Project A"
        assert len(chart["tasks"]) == 2

    def test_add_dependency(self):
        from apex_os_bp.projects.deepened import GanttManager
        mgr = GanttManager()
        mgr.create_chart("Project A", tasks=["T1", "T2"])
        result = mgr.add_dependency("T1", "T2")
        assert result["blocked"] == "T2"
        assert result["blocker"] == "T1"

    def test_critical_path(self):
        from apex_os_bp.projects.deepened import GanttManager
        mgr = GanttManager()
        mgr.create_chart("Project A", tasks=["T1", "T2", "T3"])
        mgr.add_dependency("T1", "T2")
        mgr.add_dependency("T2", "T3")
        path = mgr.critical_path()
        assert "T1" in path
        assert "T3" in path


# ── Resources ────────────────────────────────────────────────────────────────

class TestResources:
    def test_allocate_resource(self):
        from apex_os_bp.projects.deepened import ResourceManager
        mgr = ResourceManager()
        result = mgr.allocate("emp1", "Project A", hours=40)
        assert result["employee"] == "emp1"
        assert result["hours"] == 40

    def test_check_availability(self):
        from apex_os_bp.projects.deepened import ResourceManager
        mgr = ResourceManager()
        mgr.add_employee("emp1", capacity=40)
        mgr.allocate("emp1", "Project A", hours=30)
        assert mgr.check_availability("emp1") == 10

    def test_overallocation_detection(self):
        from apex_os_bp.projects.deepened import ResourceManager
        mgr = ResourceManager()
        mgr.add_employee("emp1", capacity=40)
        mgr.allocate("emp1", "Project A", hours=50)
        assert mgr.is_overallocated("emp1") is True


# ── Time Tracking ────────────────────────────────────────────────────────────

class TestTimeTracking:
    def test_log_hours(self):
        from apex_os_bp.projects.deepened import TimeTracker
        tracker = TimeTracker()
        entry = tracker.log("emp1", "T1", hours=5, date=date(2026, 10, 1))
        assert entry["employee"] == "emp1"
        assert entry["hours"] == 5

    def test_total_hours(self):
        from apex_os_bp.projects.deepened import TimeTracker
        tracker = TimeTracker()
        tracker.log("emp1", "T1", hours=5)
        tracker.log("emp1", "T2", hours=3)
        assert tracker.total_hours("emp1") == 8

    def test_timesheet_approval(self):
        from apex_os_bp.projects.deepened import TimeTracker
        tracker = TimeTracker()
        tracker.log("emp1", "T1", hours=5)
        result = tracker.submit_for_approval("emp1", week="2026-W40")
        assert result["status"] == "pending"


# ── Risk ─────────────────────────────────────────────────────────────────────

class TestRisk:
    def test_register_risk(self):
        from apex_os_bp.projects.deepened import RiskManager
        mgr = RiskManager()
        risk = mgr.register("R1", probability=0.3, impact=5)
        assert risk["id"] == "R1"
        assert risk["score"] == 1.5

    def test_mitigation_plan(self):
        from apex_os_bp.projects.deepened import RiskManager
        mgr = RiskManager()
        mgr.register("R1", probability=0.3, impact=5)
        plan = mgr.create_mitigation("R1", actions=["A1", "A2"])
        assert len(plan["actions"]) == 2

    def test_risk_matrix(self):
        from apex_os_bp.projects.deepened import RiskManager
        mgr = RiskManager()
        mgr.register("R1", probability=0.8, impact=5)
        mgr.register("R2", probability=0.2, impact=2)
        matrix = mgr.risk_matrix()
        assert len(matrix) == 2


# ── Portfolio ────────────────────────────────────────────────────────────────

class TestPortfolio:
    def test_add_project(self):
        from apex_os_bp.projects.deepened import PortfolioManager
        mgr = PortfolioManager()
        mgr.add_project("P1", budget=100000, status="active")
        assert "P1" in mgr.projects

    def test_portfolio_value(self):
        from apex_os_bp.projects.deepened import PortfolioManager
        mgr = PortfolioManager()
        mgr.add_project("P1", budget=100000)
        mgr.add_project("P2", budget=200000)
        assert mgr.total_value() == 300000

    def test_portfolio_health(self):
        from apex_os_bp.projects.deepened import PortfolioManager
        mgr = PortfolioManager()
        mgr.add_project("P1", budget=100000, status="on_track")
        mgr.add_project("P2", budget=200000, status="at_risk")
        health = mgr.health_summary()
        assert health["on_track"] == 1
        assert health["at_risk"] == 1
