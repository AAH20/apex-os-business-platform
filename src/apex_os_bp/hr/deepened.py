"""Deepened HR module: Recruitment, Performance, Learning, Payroll, Engagement."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional

# ── Recruitment Pipeline (ATS) ──────────────────────────────────────────────

class ApplicationStatus(str, Enum):
    APPLIED = "applied"; SCREENING = "screening"; INTERVIEW = "interview"
    OFFER = "offer"; HIRED = "hired"; REJECTED = "rejected"

@dataclass
class JobPosting:
    id: str; title: str; department: str; location: str
    salary_min: float; salary_max: float
    description: str = ""; posted_date: date = field(default_factory=date.today)
    is_active: bool = True

@dataclass
class Candidate:
    id: str; name: str; email: str; phone: str = ""; resume_url: str = ""
    skills: list[str] = field(default_factory=list)

@dataclass
class Application:
    id: str; job_id: str; candidate_id: str
    status: ApplicationStatus = ApplicationStatus.APPLIED
    applied_date: date = field(default_factory=date.today)
    stage_history: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def advance(self, new_status: ApplicationStatus, note: str = "") -> None:
        self.stage_history.append({
            "from": self.status.value, "to": new_status.value,
            "date": datetime.now().isoformat(), "note": note})
        self.status = new_status
        if note: self.notes.append(note)

class RecruitmentPipeline:
    def __init__(self) -> None:
        self.jobs: dict[str, JobPosting] = {}
        self.candidates: dict[str, Candidate] = {}
        self.applications: dict[str, Application] = {}

    def post_job(self, job: JobPosting) -> None: self.jobs[job.id] = job
    def add_candidate(self, c: Candidate) -> None: self.candidates[c.id] = c

    def apply(self, job_id: str, candidate_id: str) -> Application:
        app_id = f"app-{len(self.applications) + 1:04d}"
        app = Application(id=app_id, job_id=job_id, candidate_id=candidate_id)
        self.applications[app_id] = app
        return app

    def pipeline_summary(self, job_id: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for app in self.applications.values():
            if app.job_id == job_id:
                counts[app.status.value] = counts.get(app.status.value, 0) + 1
        return counts

# ── Performance Management (OKRs) ───────────────────────────────────────────

@dataclass
class KeyResult:
    id: str; description: str; target: float; current: float = 0.0; unit: str = ""

    @property
    def progress_pct(self) -> float:
        return min(100.0, (self.current / self.target * 100)) if self.target else 0.0

@dataclass
class Objective:
    id: str; title: str; owner_id: str; cycle: str
    key_results: list[KeyResult] = field(default_factory=list); weight: float = 1.0

    @property
    def overall_progress(self) -> float:
        if not self.key_results: return 0.0
        return sum(kr.progress_pct for kr in self.key_results) / len(self.key_results)

class PerformanceManager:
    def __init__(self) -> None:
        self.objectives: dict[str, Objective] = {}; self.reviews: list[dict] = []

    def create_objective(self, obj: Objective) -> None: self.objectives[obj.id] = obj

    def update_kr_progress(self, obj_id: str, kr_id: str, value: float) -> None:
        obj = self.objectives.get(obj_id)
        if not obj: raise KeyError(f"Objective {obj_id} not found")
        for kr in obj.key_results:
            if kr.id == kr_id: kr.current = value; return
        raise KeyError(f"KeyResult {kr_id} not found in {obj_id}")

    def submit_review(self, employee_id: str, reviewer_id: str,
                      rating: int, feedback: str, period: str) -> None:
        self.reviews.append({
            "employee_id": employee_id, "reviewer_id": reviewer_id,
            "rating": max(1, min(5, rating)), "feedback": feedback,
            "period": period, "submitted": datetime.now().isoformat()})

    def employee_scorecard(self, employee_id: str) -> dict:
        objs = [o for o in self.objectives.values() if o.owner_id == employee_id]
        avg = sum(o.overall_progress for o in objs) / len(objs) if objs else 0.0
        return {"employee_id": employee_id, "objective_count": len(objs),
                "average_progress": round(avg, 1),
                "objectives": [{"id": o.id, "title": o.title,
                                "progress": round(o.overall_progress, 1)} for o in objs]}

# ── Learning Management ──────────────────────────────────────────────────────

@dataclass
class Course:
    id: str; title: str; category: str; duration_hours: float
    modules: list[str] = field(default_factory=list); passing_score: float = 70.0

@dataclass
class Enrollment:
    id: str; course_id: str; employee_id: str
    progress_pct: float = 0.0; completed: bool = False; score: Optional[float] = None
    enrolled_date: date = field(default_factory=date.today)
    completed_date: Optional[date] = None

class LearningManager:
    def __init__(self) -> None:
        self.courses: dict[str, Course] = {}; self.enrollments: dict[str, Enrollment] = {}

    def add_course(self, course: Course) -> None: self.courses[course.id] = course

    def enroll(self, course_id: str, employee_id: str) -> Enrollment:
        enr_id = f"enr-{len(self.enrollments) + 1:04d}"
        enr = Enrollment(id=enr_id, course_id=course_id, employee_id=employee_id)
        self.enrollments[enr_id] = enr
        return enr

    def update_progress(self, enr_id: str, pct: float, score: Optional[float] = None) -> None:
        enr = self.enrollments.get(enr_id)
        if not enr: raise KeyError(f"Enrollment {enr_id} not found")
        enr.progress_pct = min(100.0, pct)
        if score is not None: enr.score = score
        course = self.courses.get(enr.course_id)
        if course and enr.progress_pct >= 100.0 and enr.score is not None:
            if enr.score >= course.passing_score:
                enr.completed = True; enr.completed_date = date.today()

    def employee_transcript(self, employee_id: str) -> list[dict]:
        return [{"course": self.courses[e.course_id].title, "progress": e.progress_pct,
                 "completed": e.completed, "score": e.score}
                for e in self.enrollments.values() if e.employee_id == employee_id]

# ── Payroll with Tax Calculation ─────────────────────────────────────────────

TAX_BRACKETS = [(0, 12_000, 0.10), (12_000, 45_000, 0.20),
                (45_000, 100_000, 0.30), (100_000, float("inf"), 0.40)]

def calculate_tax(gross: float) -> float:
    tax, remaining = 0.0, gross
    for low, high, rate in TAX_BRACKETS:
        taxable = min(remaining, high - low)
        if taxable <= 0: break
        tax += taxable * rate; remaining -= taxable
    return round(tax, 2)

@dataclass
class PayStub:
    employee_id: str; period: str; gross_pay: float; tax: float
    deductions: float; net_pay: float
    pay_date: date = field(default_factory=date.today)

class PayrollEngine:
    def __init__(self) -> None: self.stubs: list[PayStub] = []

    def process_payroll(self, employee_id: str, period: str,
                        gross: float, deductions: float = 0.0) -> PayStub:
        tax = calculate_tax(gross)
        stub = PayStub(employee_id=employee_id, period=period, gross_pay=gross,
                        tax=tax, deductions=deductions,
                        net_pay=round(gross - tax - deductions, 2))
        self.stubs.append(stub)
        return stub

    def ytd_summary(self, employee_id: str) -> dict:
        emp = [s for s in self.stubs if s.employee_id == employee_id]
        return {"employee_id": employee_id,
                "total_gross": round(sum(s.gross_pay for s in emp), 2),
                "total_tax": round(sum(s.tax for s in emp), 2),
                "total_deductions": round(sum(s.deductions for s in emp), 2),
                "total_net": round(sum(s.net_pay for s in emp), 2),
                "pay_periods": len(emp)}

# ── Employee Engagement (Surveys) ────────────────────────────────────────────

@dataclass
class SurveyQuestion:
    id: str; text: str; category: str; scale: int = 5

@dataclass
class Survey:
    id: str; title: str
    questions: list[SurveyQuestion] = field(default_factory=list)
    is_anonymous: bool = True
    start_date: date = field(default_factory=date.today)
    end_date: Optional[date] = None

@dataclass
class SurveyResponse:
    survey_id: str; employee_id: str; answers: dict[str, int]
    submitted_at: datetime = field(default_factory=datetime.now)

class EngagementTracker:
    def __init__(self) -> None:
        self.surveys: dict[str, Survey] = {}; self.responses: list[SurveyResponse] = []

    def create_survey(self, survey: Survey) -> None: self.surveys[survey.id] = survey
    def submit_response(self, response: SurveyResponse) -> None: self.responses.append(response)

    def survey_results(self, survey_id: str) -> dict:
        survey = self.surveys.get(survey_id)
        if not survey: raise KeyError(f"Survey {survey_id} not found")
        relevant = [r for r in self.responses if r.survey_id == survey_id]
        if not relevant: return {"survey_id": survey_id, "response_count": 0, "averages": {}}
        by_cat: dict[str, list[int]] = {}
        for r in relevant:
            for q in survey.questions:
                if q.id in r.answers:
                    by_cat.setdefault(q.category, []).append(r.answers[q.id])
        avgs = {c: round(sum(v) / len(v), 2) for c, v in by_cat.items()}
        overall = round(sum(avgs.values()) / len(avgs), 2) if avgs else 0.0
        return {"survey_id": survey_id, "title": survey.title,
                "response_count": len(relevant), "category_averages": avgs,
                "overall_score": overall}

    def engagement_trend(self, category: str) -> list[dict]:
        trend = []
        for survey in self.surveys.values():
            result = self.survey_results(survey.id)
            if category in result.get("category_averages", {}):
                trend.append({"survey": survey.title,
                              "date": survey.start_date.isoformat(),
                              "score": result["category_averages"][category]})
        return trend
