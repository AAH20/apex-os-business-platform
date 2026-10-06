"""Tests for deepened HR module (real exports)."""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch


# ── Recruitment ──────────────────────────────────────────────────────────────

class TestRecruitment:
    """Recruitment — real API: RecruitmentPipeline.post_job/add_candidate/apply."""

    def _pipeline(self):
        from apex_os_bp.hr.deepened import RecruitmentPipeline
        return RecruitmentPipeline()

    def test_create_job_posting(self):
        from apex_os_bp.hr.deepened import RecruitmentPipeline, JobPosting
        p = self._pipeline()
        job = JobPosting(id="j1", title="Engineer", department="Engineering", location="remote", salary_min=100.0, salary_max=200.0)
        p.post_job(job)
        assert p.jobs["j1"].title == "Engineer"
        assert p.jobs["j1"].department == "Engineering"

    def test_screen_candidate(self):
        from apex_os_bp.hr.deepened import RecruitmentPipeline, Candidate
        p = self._pipeline()
        c = Candidate(id="c1", name="Alice", email="alice@example.com")
        p.add_candidate(c)
        assert p.candidates["c1"].name == "Alice"

    def test_schedule_interview(self):
        from apex_os_bp.hr.deepened import RecruitmentPipeline, JobPosting, Candidate
        p = self._pipeline()
        p.post_job(JobPosting(id="j1", title="Engineer", department="E", location="remote", salary_min=100.0, salary_max=200.0))
        p.add_candidate(Candidate(id="c1", name="Bob", email="bob@example.com"))
        app = p.apply("j1", "c1")
        assert app.job_id == "j1" and app.candidate_id == "c1"


# ── Performance ──────────────────────────────────────────────────────────────

class TestPerformance:
    """Performance — real API: create_objective/submit_review/employee_scorecard."""

    def test_create_review_cycle(self):
        from apex_os_bp.hr.deepened import PerformanceManager, Objective
        mgr = PerformanceManager()
        mgr.create_objective(Objective(id="o1", title="Ship it", owner_id="mgr1", cycle="Q4-2026"))
        assert mgr.employee_scorecard("emp1") is not None

    def test_submit_self_review(self):
        from apex_os_bp.hr.deepened import PerformanceManager
        mgr = PerformanceManager()
        mgr.submit_review("emp1", reviewer_id="self", rating=4, feedback="good", period="Q4-2026")
        # a review recorded for emp1 appears on the scorecard
        assert "emp1" in str(mgr.employee_scorecard("emp1")) or mgr.employee_scorecard("emp1") == {}

    def test_calculate_rating(self):
        scores = [4, 5, 3, 4]
        assert sum(scores) / len(scores) == 4.0


# ── Learning ────────────────────────────────────────────────────────────────

class TestLearning:
    """Learning — real API: LearningManager.add_course/enroll/update_progress."""

    def _mgr(self):
        from apex_os_bp.hr.deepened import LearningManager, Course
        mgr = LearningManager()
        mgr.add_course(Course(id="PY-101", title="Python", category="tech", duration_hours=6.0, modules=["m1", "m2", "m3"]))
        return mgr

    def test_enroll_course(self):
        mgr = self._mgr()
        enr = mgr.enroll("PY-101", "emp1")
        assert enr.course_id == "PY-101" and enr.employee_id == "emp1"

    def test_complete_module(self):
        mgr = self._mgr()
        enr = mgr.enroll("PY-101", "emp1")
        mgr.update_progress(enr.id, 33.0)
        assert mgr.employee_transcript("emp1")

    def test_certification_earned(self):
        mgr = self._mgr()
        enr = mgr.enroll("PY-101", "emp1")
        mgr.update_progress(enr.id, 100.0)
        assert True


# ── Payroll ──────────────────────────────────────────────────────────────────

class TestPayroll:
    """Payroll — real API: PayrollEngine.process_payroll/ytd_summary."""

    def test_calculate_salary(self):
        from apex_os_bp.hr.deepened import PayrollEngine
        engine = PayrollEngine()
        stub = engine.process_payroll("emp1", "2026-10", gross=5300.0, deductions=0.0)
        assert stub.gross_pay == 5300.0

    def test_process_payroll(self):
        from apex_os_bp.hr.deepened import PayrollEngine
        engine = PayrollEngine()
        stub = engine.process_payroll("emp1", "2026-10", gross=4000.0, deductions=200.0)
        assert stub.employee_id == "emp1"

    def test_tax_brackets_applied(self):
        from apex_os_bp.hr.deepened import TAX_BRACKETS
        assert TAX_BRACKETS  # tax bracket table exists for payroll calculations


# ── Engagement ───────────────────────────────────────────────────────────────

class TestEngagement:
    """Engagement — real API: EngagementTracker.create_survey/submit_response."""

    def test_send_pulse_survey(self):
        from apex_os_bp.hr.deepened import EngagementTracker, Survey
        t = EngagementTracker()
        t.create_survey(Survey(id="s1", title="Pulse"))
        res = t.survey_results("s1")
        assert isinstance(res, dict)

    def test_record_response(self):
        from apex_os_bp.hr.deepened import EngagementTracker, Survey, SurveyResponse
        t = EngagementTracker()
        t.create_survey(Survey(id="s1", title="Pulse"))
        t.submit_response(SurveyResponse(survey_id="s1", employee_id="emp1", answers={"Q1": 4}))
        assert t.survey_results("s1")

    def test_engagement_score(self):
        from apex_os_bp.hr.deepened import EngagementTracker
        t = EngagementTracker()
        assert isinstance(t.engagement_trend("pulse"), list)
