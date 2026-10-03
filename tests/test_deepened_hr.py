"""Tests for deepened HR modules: recruitment, performance, learning, payroll, engagement."""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch


# ── Recruitment ──────────────────────────────────────────────────────────────

class TestRecruitment:
    def test_create_job_posting(self):
        from apex_os_bp.hr.deepened import RecruitmentManager
        mgr = RecruitmentManager()
        job = mgr.create_job(title="Engineer", dept="Engineering", openings=2)
        assert job["title"] == "Engineer"
        assert job["dept"] == "Engineering"
        assert job["openings"] == 2
        assert job["status"] == "open"

    def test_screen_candidate(self):
        from apex_os_bp.hr.deepened import RecruitmentManager
        mgr = RecruitmentManager()
        result = mgr.screen_candidate("Alice", score=85)
        assert result["candidate"] == "Alice"
        assert result["passed"] is True

    def test_schedule_interview(self):
        from apex_os_bp.hr.deepened import RecruitmentManager
        mgr = RecruitmentManager()
        slot = mgr.schedule_interview("Bob", date=date(2026, 10, 10))
        assert slot["candidate"] == "Bob"
        assert slot["scheduled"] is True


# ── Performance ──────────────────────────────────────────────────────────────

class TestPerformance:
    def test_create_review_cycle(self):
        from apex_os_bp.hr.deepened import PerformanceManager
        mgr = PerformanceManager()
        cycle = mgr.create_review_cycle("Q4-2026", reviewers=["mgr1", "mgr2"])
        assert cycle["name"] == "Q4-2026"
        assert len(cycle["reviewers"]) == 2

    def test_submit_self_review(self):
        from apex_os_bp.hr.deepened import PerformanceManager
        mgr = PerformanceManager()
        mgr.create_review_cycle("Q4-2026", reviewers=["mgr1"])
        result = mgr.submit_self_review("emp1", goals_met=4, total_goals=5)
        assert result["score"] == 0.8

    def test_calculate_rating(self):
        from apex_os_bp.hr.deepened import PerformanceManager
        mgr = PerformanceManager()
        rating = mgr.calculate_rating(scores=[4, 5, 3, 4])
        assert rating == 4.0


# ── Learning ─────────────────────────────────────────────────────────────────

class TestLearning:
    def test_enroll_course(self):
        from apex_os_bp.hr.deepened import LearningManager
        mgr = LearningManager()
        enrollment = mgr.enroll("emp1", course_id="PY-101")
        assert enrollment["employee"] == "emp1"
        assert enrollment["course"] == "PY-101"
        assert enrollment["progress"] == 0.0

    def test_complete_module(self):
        from apex_os_bp.hr.deepened import LearningManager
        mgr = LearningManager()
        mgr.enroll("emp1", course_id="PY-101")
        result = mgr.complete_module("emp1", "PY-101", module=1)
        assert result["completed"] is True

    def test_certification_earned(self):
        from apex_os_bp.hr.deepened import LearningManager
        mgr = LearningManager()
        mgr.enroll("emp1", course_id="PY-101")
        for i in range(1, 4):
            mgr.complete_module("emp1", "PY-101", module=i)
        cert = mgr.issue_certification("emp1", "PY-101")
        assert cert["certified"] is True


# ── Payroll ──────────────────────────────────────────────────────────────────

class TestPayroll:
    def test_calculate_salary(self):
        from apex_os_bp.hr.deepened import PayrollManager
        mgr = PayrollManager()
        result = mgr.calculate_salary(base=5000, bonus=500, deductions=200)
        assert result["net"] == 5300

    def test_process_payroll(self):
        from apex_os_bp.hr.deepened import PayrollManager
        mgr = PayrollManager()
        mgr.add_employee("emp1", base=4000)
        result = mgr.process_payroll("emp1")
        assert result["employee"] == "emp1"
        assert result["paid"] is True

    def test_tax_calculation(self):
        from apex_os_bp.hr.deepened import PayrollManager
        mgr = PayrollManager()
        tax = mgr.calculate_tax(income=60000, brackets=[(50000, 0.2), (float("inf"), 0.3)])
        assert tax == 7000.0


# ── Engagement ───────────────────────────────────────────────────────────────

class TestEngagement:
    def test_send_pulse_survey(self):
        from apex_os_bp.hr.deepened import EngagementManager
        mgr = EngagementManager()
        survey = mgr.send_pulse_survey(["emp1", "emp2"], questions=["Q1", "Q2"])
        assert len(survey["recipients"]) == 2
        assert len(survey["questions"]) == 2

    def test_record_response(self):
        from apex_os_bp.hr.deepened import EngagementManager
        mgr = EngagementManager()
        mgr.send_pulse_survey(["emp1"], questions=["Q1"])
        result = mgr.record_response("emp1", "Q1", score=4)
        assert result["score"] == 4

    def test_engagement_score(self):
        from apex_os_bp.hr.deepened import EngagementManager
        mgr = EngagementManager()
        mgr.send_pulse_survey(["emp1", "emp2"], questions=["Q1"])
        mgr.record_response("emp1", "Q1", score=5)
        mgr.record_response("emp2", "Q1", score=3)
        score = mgr.engagement_score()
        assert score == 4.0
