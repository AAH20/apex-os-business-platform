"""Comprehensive tests for the HR management system."""

from __future__ import annotations

import sys
import os
from datetime import date, timedelta

import pytest

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.hr.employees import (
    Department,
    Employee,
    EmployeeRepository,
    EmploymentStatus,
)
from apex_os_bp.hr.leave import (
    LeaveBalance,
    LeaveManager,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
)
from apex_os_bp.hr.payroll import (
    Deduction,
    PayFrequency,
    PayrollCalculator,
    Payslip,
)
from apex_os_bp.hr.performance import (
    Goal,
    GoalStatus,
    PerformanceReview,
    Rating,
    ReviewCycle,
    ReviewStatus,
)
from apex_os_bp.hr.recruitment import (
    Application,
    ApplicationStage,
    Candidate,
    JobPosting,
    RecruitmentManager,
)


# ═══════════════════════════════════════════════════════════════════════
#  Employee Records
# ═══════════════════════════════════════════════════════════════════════


class TestEmployee:
    def _make_employee(self, **kwargs):
        defaults = dict(
            id="E001",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            department_id="D001",
            job_title="Engineer",
            hire_date=date(2022, 1, 15),
            salary=75000.0,
        )
        defaults.update(kwargs)
        return Employee(**defaults)

    def test_create_employee(self):
        emp = self._make_employee()
        assert emp.id == "E001"
        assert emp.full_name == "Alice Smith"
        assert emp.status == EmploymentStatus.ACTIVE

    def test_full_name(self):
        emp = self._make_employee()
        assert emp.full_name == "Alice Smith"

    def test_tenure_years(self):
        emp = self._make_employee(hire_date=date(2020, 1, 1))
        assert emp.tenure_years > 5.0

    def test_invalid_email(self):
        with pytest.raises(ValueError, match="Invalid email"):
            self._make_employee(email="not-an-email")

    def test_negative_salary(self):
        with pytest.raises(ValueError, match="Salary cannot be negative"):
            self._make_employee(salary=-1000)

    def test_to_dict(self):
        emp = self._make_employee()
        d = emp.to_dict()
        assert d["id"] == "E001"
        assert d["full_name"] == "Alice Smith"
        assert d["email"] == "alice@example.com"
        assert "tenure_years" in d


class TestEmployeeRepository:
    def setup_method(self):
        self.repo = EmployeeRepository()
        self.dept = Department(id="D001", name="Engineering")
        self.repo.add_department(self.dept)

    def test_add_and_get_employee(self):
        emp = Employee(
            id="E001",
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
            department_id="D001",
            job_title="Dev",
            hire_date=date(2023, 6, 1),
            salary=60000,
        )
        self.repo.add_employee(emp)
        fetched = self.repo.get_employee("E001")
        assert fetched is not None
        assert fetched.full_name == "Bob Jones"

    def test_duplicate_employee(self):
        emp = Employee(
            id="E001",
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
            department_id="D001",
            job_title="Dev",
            hire_date=date(2023, 6, 1),
            salary=60000,
        )
        self.repo.add_employee(emp)
        with pytest.raises(ValueError, match="already exists"):
            self.repo.add_employee(emp)

    def test_invalid_department(self):
        emp = Employee(
            id="E002",
            first_name="Charlie",
            last_name="Brown",
            email="charlie@example.com",
            department_id="D999",
            job_title="Dev",
            hire_date=date(2023, 6, 1),
            salary=60000,
        )
        with pytest.raises(ValueError, match="does not exist"):
            self.repo.add_employee(emp)

    def test_update_employee(self):
        emp = Employee(
            id="E001",
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
            department_id="D001",
            job_title="Dev",
            hire_date=date(2023, 6, 1),
            salary=60000,
        )
        self.repo.add_employee(emp)
        self.repo.update_employee("E001", salary=70000, job_title="Senior Dev")
        assert emp.salary == 70000
        assert emp.job_title == "Senior Dev"

    def test_remove_employee(self):
        emp = Employee(
            id="E001",
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
            department_id="D001",
            job_title="Dev",
            hire_date=date(2023, 6, 1),
            salary=60000,
        )
        self.repo.add_employee(emp)
        self.repo.remove_employee("E001")
        assert self.repo.get_employee("E001") is None

    def test_list_employees_by_department(self):
        for i in range(3):
            self.repo.add_employee(
                Employee(
                    id=f"E00{i}",
                    first_name=f"Emp{i}",
                    last_name="Test",
                    email=f"emp{i}@example.com",
                    department_id="D001",
                    job_title="Dev",
                    hire_date=date(2023, 1, 1),
                    salary=50000,
                )
            )
        self.repo.add_department(Department(id="D002", name="HR"))
        self.repo.add_employee(
            Employee(
                id="E100",
                first_name="HR",
                last_name="Person",
                email="hr@example.com",
                department_id="D002",
                job_title="Manager",
                hire_date=date(2023, 1, 1),
                salary=80000,
            )
        )
        result = self.repo.list_employees(department_id="D001")
        assert len(result) == 3

    def test_search(self):
        self.repo.add_employee(
            Employee(
                id="E001",
                first_name="Alice",
                last_name="Smith",
                email="alice@example.com",
                department_id="D001",
                job_title="Engineer",
                hire_date=date(2023, 1, 1),
                salary=70000,
            )
        )
        self.repo.add_employee(
            Employee(
                id="E002",
                first_name="Bob",
                last_name="Jones",
                email="bob@example.com",
                department_id="D001",
                job_title="Designer",
                hire_date=date(2023, 1, 1),
                salary=65000,
            )
        )
        results = self.repo.search("alice")
        assert len(results) == 1
        assert results[0].first_name == "Alice"

    def test_get_subordinates(self):
        self.repo.add_employee(
            Employee(
                id="M001",
                first_name="Manager",
                last_name="Person",
                email="mgr@example.com",
                department_id="D001",
                job_title="Manager",
                hire_date=date(2020, 1, 1),
                salary=100000,
            )
        )
        self.repo.add_employee(
            Employee(
                id="E001",
                first_name="Sub",
                last_name="Ordinate",
                email="sub@example.com",
                department_id="D001",
                job_title="Dev",
                hire_date=date(2023, 1, 1),
                salary=60000,
                manager_id="M001",
            )
        )
        subs = self.repo.get_subordinates("M001")
        assert len(subs) == 1
        assert subs[0].id == "E001"

    def test_count(self):
        assert self.repo.count() == 0
        self.repo.add_employee(
            Employee(
                id="E001",
                first_name="A",
                last_name="B",
                email="a@example.com",
                department_id="D001",
                job_title="Dev",
                hire_date=date(2023, 1, 1),
                salary=50000,
            )
        )
        assert self.repo.count() == 1


# ═══════════════════════════════════════════════════════════════════════
#  Leave Management
# ═══════════════════════════════════════════════════════════════════════


class TestLeaveBalance:
    def test_default_balances(self):
        bal = LeaveBalance(employee_id="E001", year=2026)
        assert bal.get_balance(LeaveType.ANNUAL) == 20.0
        assert bal.get_balance(LeaveType.SICK) == 10.0

    def test_deduct(self):
        bal = LeaveBalance(employee_id="E001", year=2026)
        bal.deduct(LeaveType.ANNUAL, 5)
        assert bal.get_balance(LeaveType.ANNUAL) == 15.0

    def test_insufficient_balance(self):
        bal = LeaveBalance(employee_id="E001", year=2026)
        with pytest.raises(ValueError, match="Insufficient"):
            bal.deduct(LeaveType.ANNUAL, 25)

    def test_add(self):
        bal = LeaveBalance(employee_id="E001", year=2026)
        bal.add(LeaveType.ANNUAL, 5)
        assert bal.get_balance(LeaveType.ANNUAL) == 25.0


class TestLeaveRequest:
    def test_create_request(self):
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
        )
        assert req.status == LeaveStatus.PENDING
        assert req.duration_days == 5

    def test_weekend_excluded(self):
        # June 6-7, 2026 is Sat-Sun
        req = LeaveRequest(
            id="L002",
            employee_id="E001",
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 7),
        )
        assert req.duration_days == 5  # Mon-Fri only

    def test_invalid_dates(self):
        with pytest.raises(ValueError, match="End date cannot be before start"):
            LeaveRequest(
                id="L003",
                employee_id="E001",
                leave_type=LeaveType.ANNUAL,
                start_date=date(2026, 6, 10),
                end_date=date(2026, 6, 1),
            )

    def test_approve(self):
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
        )
        req.approve("M001")
        assert req.status == LeaveStatus.APPROVED
        assert req.approver_id == "M001"

    def test_reject(self):
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
        )
        req.reject("M001")
        assert req.status == LeaveStatus.REJECTED

    def test_cancel(self):
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
        )
        req.cancel()
        assert req.status == LeaveStatus.CANCELLED

    def test_cancel_approved_raises(self):
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
        )
        req.approve("M001")
        with pytest.raises(ValueError, match="Cannot cancel"):
            req.cancel()


class TestLeaveManager:
    def setup_method(self):
        self.mgr = LeaveManager()

    def test_submit_and_approve(self):
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
        )
        self.mgr.submit_request(req)
        self.mgr.approve_request("L001", "M001")
        assert req.status == LeaveStatus.APPROVED
        bal = self.mgr.get_balance("E001", 2026)
        assert bal.get_balance(LeaveType.ANNUAL) == 15.0

    def test_submit_insufficient_balance(self):
        self.mgr.set_entitlement("E001", LeaveType.ANNUAL, 3, 2026)
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
        )
        with pytest.raises(ValueError, match="Insufficient"):
            self.mgr.submit_request(req)

    def test_unpaid_no_balance_check(self):
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.UNPAID,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
        )
        self.mgr.submit_request(req)
        self.mgr.approve_request("L001", "M001")
        assert req.status == LeaveStatus.APPROVED

    def test_reject_request(self):
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.SICK,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
        )
        self.mgr.submit_request(req)
        self.mgr.reject_request("L001", "M001")
        assert req.status == LeaveStatus.REJECTED

    def test_list_requests(self):
        for i in range(3):
            self.mgr.submit_request(
                LeaveRequest(
                    id=f"L00{i}",
                    employee_id="E001",
                    leave_type=LeaveType.ANNUAL,
                    start_date=date(2026, 6, 1 + i),
                    end_date=date(2026, 6, 2 + i),
                )
            )
        assert len(self.mgr.list_requests(employee_id="E001")) == 3
        assert len(self.mgr.get_pending_requests()) == 3

    def test_cancel_request(self):
        req = LeaveRequest(
            id="L001",
            employee_id="E001",
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
        )
        self.mgr.submit_request(req)
        self.mgr.cancel_request("L001")
        assert req.status == LeaveStatus.CANCELLED


# ═══════════════════════════════════════════════════════════════════════
#  Payroll
# ═══════════════════════════════════════════════════════════════════════


class TestPayrollCalculator:
    def setup_method(self):
        self.calc = PayrollCalculator()

    def test_income_tax_zero(self):
        assert self.calc.calculate_income_tax(10000) == 0.0

    def test_income_tax_basic(self):
        # £20,000: first 12570 at 0%, remaining 7430 at 20% = 1486
        tax = self.calc.calculate_income_tax(20000)
        assert tax == 1486.0

    def test_income_tax_higher(self):
        # £60,000: 0 + (50270-12570)*0.2 + (60000-50270)*0.4
        # = 0 + 7540 + 3892 = 11432
        tax = self.calc.calculate_income_tax(60000)
        assert tax == 11432.0

    def test_ni(self):
        assert self.calc.calculate_ni(3000) == 240.0

    def test_pension(self):
        assert self.calc.calculate_pension(3000) == 150.0

    def test_gross_monthly(self):
        gross = self.calc.gross_per_period(60000, PayFrequency.MONTHLY)
        assert gross == 5000.0

    def test_gross_weekly(self):
        gross = self.calc.gross_per_period(52000, PayFrequency.WEEKLY)
        assert gross == 1000.0

    def test_generate_payslip(self):
        slip = self.calc.generate_payslip(
            employee_id="E001",
            annual_salary=60000,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            frequency=PayFrequency.MONTHLY,
        )
        assert slip.gross_pay == 5000.0
        assert slip.net_pay < slip.gross_pay
        assert len(slip.deductions) >= 3  # tax + NI + pension

    def test_payslip_to_dict(self):
        slip = self.calc.generate_payslip(
            employee_id="E001",
            annual_salary=60000,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
        )
        d = slip.to_dict()
        assert d["employee_id"] == "E001"
        assert d["gross_pay"] == 5000.0
        assert "deductions" in d

    def test_ytd(self):
        for month in range(1, 4):
            self.calc.generate_payslip(
                employee_id="E001",
                annual_salary=60000,
                period_start=date(2026, month, 1),
                period_end=date(2026, month, 28),
            )
        assert self.calc.ytd_gross("E001") == 15000.0
        assert self.calc.ytd_net("E001") > 0
        assert self.calc.ytd_tax("E001") > 0

    def test_extra_deductions(self):
        slip = self.calc.generate_payslip(
            employee_id="E001",
            annual_salary=60000,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            extra_deductions=[Deduction(name="Union", amount=25.0)],
        )
        names = [d.name for d in slip.deductions]
        assert "Union" in names

    def test_invalid_period(self):
        with pytest.raises(ValueError, match="Period end cannot be before"):
            Payslip(
                employee_id="E001",
                period_start=date(2026, 6, 30),
                period_end=date(2026, 6, 1),
                gross_pay=1000,
            )


# ═══════════════════════════════════════════════════════════════════════
#  Performance Reviews
# ═══════════════════════════════════════════════════════════════════════


class TestGoal:
    def test_create_goal(self):
        goal = Goal(
            id="G001",
            employee_id="E001",
            title="Learn Rust",
            description="Complete Rust course",
            target_date=date(2026, 12, 31),
        )
        assert goal.status == GoalStatus.NOT_STARTED
        assert goal.progress == 0

    def test_update_progress(self):
        goal = Goal(
            id="G001",
            employee_id="E001",
            title="Learn Rust",
            description="Complete Rust course",
            target_date=date(2026, 12, 31),
        )
        goal.update_progress(50)
        assert goal.progress == 50
        assert goal.status == GoalStatus.IN_PROGRESS

    def test_complete_goal(self):
        goal = Goal(
            id="G001",
            employee_id="E001",
            title="Learn Rust",
            description="Complete Rust course",
            target_date=date(2026, 12, 31),
        )
        goal.complete()
        assert goal.progress == 100
        assert goal.status == GoalStatus.COMPLETED

    def test_invalid_progress(self):
        goal = Goal(
            id="G001",
            employee_id="E001",
            title="Learn Rust",
            description="Complete Rust course",
            target_date=date(2026, 12, 31),
        )
        with pytest.raises(ValueError, match="Progress must be between"):
            goal.update_progress(150)


class TestPerformanceReview:
    def _make_review(self):
        return PerformanceReview(
            id="R001",
            employee_id="E001",
            reviewer_id="M001",
            review_period_start=date(2026, 1, 1),
            review_period_end=date(2026, 6, 30),
        )

    def test_create_review(self):
        review = self._make_review()
        assert review.status == ReviewStatus.DRAFT
        assert review.overall_rating is None

    def test_self_review(self):
        review = self._make_review()
        review.submit_self_review(Rating.EXCEEDS_EXPECTATIONS, "Great work")
        assert review.self_rating == Rating.EXCEEDS_EXPECTATIONS
        assert review.status == ReviewStatus.SELF_REVIEW

    def test_manager_review(self):
        review = self._make_review()
        review.submit_manager_review(Rating.MEETS_EXPECTATIONS, "Good")
        assert review.manager_rating == Rating.MEETS_EXPECTATIONS

    def test_overall_rating(self):
        review = self._make_review()
        review.submit_self_review(Rating.OUTSTANDING, "Amazing")
        review.submit_manager_review(Rating.EXCEEDS_EXPECTATIONS, "Great")
        assert review.overall_rating == Rating.EXCEEDS_EXPECTATIONS  # avg of 5 and 4 → 4.5 → round to 4

    def test_complete_review(self):
        review = self._make_review()
        review.submit_self_review(Rating.MEETS_EXPECTATIONS, "OK")
        review.submit_manager_review(Rating.MEETS_EXPECTATIONS, "Fine")
        review.complete()
        assert review.status == ReviewStatus.COMPLETED

    def test_complete_without_ratings(self):
        review = self._make_review()
        with pytest.raises(ValueError, match="Both self and manager"):
            review.complete()

    def test_add_goal(self):
        review = self._make_review()
        goal = Goal(
            id="G001",
            employee_id="E001",
            title="Learn Rust",
            description="Complete Rust course",
            target_date=date(2026, 12, 31),
        )
        review.add_goal(goal)
        assert len(review.goals) == 1

    def test_to_dict(self):
        review = self._make_review()
        d = review.to_dict()
        assert d["id"] == "R001"
        assert d["status"] == "draft"


class TestReviewCycle:
    def test_create_cycle(self):
        cycle = ReviewCycle(
            id="C001",
            name="2026 H1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        assert cycle.completion_rate() == 0.0

    def test_completion_rate(self):
        cycle = ReviewCycle(
            id="C001",
            name="2026 H1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        for i in range(4):
            review = PerformanceReview(
                id=f"R00{i}",
                employee_id=f"E00{i}",
                reviewer_id="M001",
                review_period_start=date(2026, 1, 1),
                review_period_end=date(2026, 6, 30),
            )
            if i < 2:
                review.submit_self_review(Rating.MEETS_EXPECTATIONS, "OK")
                review.submit_manager_review(Rating.MEETS_EXPECTATIONS, "OK")
                review.complete()
            cycle.add_review(review)
        assert cycle.completion_rate() == 50.0

    def test_average_rating(self):
        cycle = ReviewCycle(
            id="C001",
            name="2026 H1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        for i, rating in enumerate([Rating.OUTSTANDING, Rating.EXCEEDS_EXPECTATIONS]):
            review = PerformanceReview(
                id=f"R00{i}",
                employee_id=f"E00{i}",
                reviewer_id="M001",
                review_period_start=date(2026, 1, 1),
                review_period_end=date(2026, 6, 30),
            )
            review.submit_self_review(rating, "Good")
            review.submit_manager_review(rating, "Good")
            review.complete()
            cycle.add_review(review)
        assert cycle.average_rating() == 4.5


# ═══════════════════════════════════════════════════════════════════════
#  Recruitment
# ═══════════════════════════════════════════════════════════════════════


class TestJobPosting:
    def test_create_job(self):
        job = JobPosting(
            id="J001",
            title="Senior Engineer",
            department_id="D001",
            description="Build things",
            requirements=["Python", "Rust"],
            salary_min=80000,
            salary_max=120000,
        )
        assert job.is_active is True

    def test_invalid_salary_range(self):
        with pytest.raises(ValueError, match="salary_min cannot exceed"):
            JobPosting(
                id="J001",
                title="Senior Engineer",
                department_id="D001",
                description="Build things",
                salary_min=120000,
                salary_max=80000,
            )

    def test_close_reopen(self):
        job = JobPosting(
            id="J001",
            title="Senior Engineer",
            department_id="D001",
            description="Build things",
        )
        job.close()
        assert job.is_active is False
        job.reopen()
        assert job.is_active is True


class TestCandidate:
    def test_create_candidate(self):
        cand = Candidate(
            id="C001",
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            skills=["Python", "Go"],
            years_experience=5,
        )
        assert cand.full_name == "Jane Doe"

    def test_invalid_email(self):
        with pytest.raises(ValueError, match="Invalid email"):
            Candidate(
                id="C001",
                first_name="Jane",
                last_name="Doe",
                email="not-an-email",
            )


class TestApplication:
    def test_create_application(self):
        app = Application(
            id="A001",
            job_id="J001",
            candidate_id="C001",
        )
        assert app.stage == ApplicationStage.APPLIED

    def test_advance(self):
        app = Application(
            id="A001",
            job_id="J001",
            candidate_id="C001",
        )
        app.advance()
        assert app.stage == ApplicationStage.SCREENING
        app.advance()
        assert app.stage == ApplicationStage.PHONE_INTERVIEW

    def test_reject(self):
        app = Application(
            id="A001",
            job_id="J001",
            candidate_id="C001",
        )
        app.reject("Not a fit")
        assert app.stage == ApplicationStage.REJECTED
        assert len(app.notes) == 1

    def test_advance_rejected_raises(self):
        app = Application(
            id="A001",
            job_id="J001",
            candidate_id="C001",
        )
        app.reject("Not a fit")
        with pytest.raises(ValueError, match="Cannot advance"):
            app.advance()

    def test_set_rating(self):
        app = Application(
            id="A001",
            job_id="J001",
            candidate_id="C001",
        )
        app.set_rating(4)
        assert app.rating == 4

    def test_invalid_rating(self):
        app = Application(
            id="A001",
            job_id="J001",
            candidate_id="C001",
        )
        with pytest.raises(ValueError, match="Rating must be between"):
            app.set_rating(6)


class TestRecruitmentManager:
    def setup_method(self):
        self.mgr = RecruitmentManager()
        self.job = JobPosting(
            id="J001",
            title="Senior Engineer",
            department_id="D001",
            description="Build things",
        )
        self.mgr.post_job(self.job)
        self.candidate = Candidate(
            id="C001",
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            skills=["Python", "Go"],
        )
        self.mgr.add_candidate(self.candidate)

    def test_post_and_get_job(self):
        fetched = self.mgr.get_job("J001")
        assert fetched is not None
        assert fetched.title == "Senior Engineer"

    def test_list_active_jobs(self):
        self.mgr.close_job("J001")
        assert len(self.mgr.list_jobs(active_only=True)) == 0
        assert len(self.mgr.list_jobs(active_only=False)) == 1

    def test_add_and_get_candidate(self):
        fetched = self.mgr.get_candidate("C001")
        assert fetched is not None
        assert fetched.full_name == "Jane Doe"

    def test_search_candidates_by_skill(self):
        self.mgr.add_candidate(
            Candidate(
                id="C002",
                first_name="John",
                last_name="Smith",
                email="john@example.com",
                skills=["JavaScript"],
            )
        )
        results = self.mgr.search_candidates(skill="Python")
        assert len(results) == 1
        assert results[0].id == "C001"

    def test_apply(self):
        app = Application(id="A001", job_id="J001", candidate_id="C001")
        self.mgr.apply(app)
        fetched = self.mgr.get_application("A001")
        assert fetched is not None
        assert fetched.stage == ApplicationStage.APPLIED

    def test_apply_invalid_job(self):
        app = Application(id="A001", job_id="J999", candidate_id="C001")
        with pytest.raises(ValueError, match="Job posting"):
            self.mgr.apply(app)

    def test_advance_application(self):
        app = Application(id="A001", job_id="J001", candidate_id="C001")
        self.mgr.apply(app)
        self.mgr.advance_application("A001")
        assert app.stage == ApplicationStage.SCREENING

    def test_reject_application(self):
        app = Application(id="A001", job_id="J001", candidate_id="C001")
        self.mgr.apply(app)
        self.mgr.reject_application("A001", "Not a fit")
        assert app.stage == ApplicationStage.REJECTED

    def test_pipeline_summary(self):
        for i in range(3):
            self.mgr.apply(
                Application(id=f"A00{i}", job_id="J001", candidate_id="C001")
            )
        self.mgr.advance_application("A000")
        summary = self.mgr.pipeline_summary("J001")
        assert summary["applied"] == 2
        assert summary["screening"] == 1

    def test_list_applications_filter(self):
        self.mgr.apply(Application(id="A001", job_id="J001", candidate_id="C001"))
        self.mgr.apply(Application(id="A002", job_id="J001", candidate_id="C001"))
        results = self.mgr.list_applications(job_id="J001", stage=ApplicationStage.APPLIED)
        assert len(results) == 2
