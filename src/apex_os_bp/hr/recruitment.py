"""Recruitment: job postings, candidates, applications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class ApplicationStage(str, Enum):
    """Pipeline stages for a job application."""

    APPLIED = "applied"
    SCREENING = "screening"
    PHONE_INTERVIEW = "phone_interview"
    TECHNICAL_INTERVIEW = "technical_interview"
    ONSITE = "onsite"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"


@dataclass
class JobPosting:
    """An open job position."""

    id: str
    title: str
    department_id: str
    description: str
    requirements: list[str] = field(default_factory=list)
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    location: Optional[str] = None
    is_active: bool = True
    posted_date: date = field(default_factory=date.today)
    closing_date: Optional[date] = None

    def __post_init__(self) -> None:
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min cannot exceed salary_max")

    def close(self) -> None:
        self.is_active = False

    def reopen(self) -> None:
        self.is_active = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "department_id": self.department_id,
            "description": self.description,
            "requirements": self.requirements,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "location": self.location,
            "is_active": self.is_active,
            "posted_date": self.posted_date.isoformat(),
            "closing_date": self.closing_date.isoformat() if self.closing_date else None,
        }


@dataclass
class Candidate:
    """A job candidate."""

    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    years_experience: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.first_name or not self.last_name:
            raise ValueError("First and last name are required")
        if "@" not in self.email:
            raise ValueError("Invalid email address")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class Application:
    """A candidate's application to a job posting."""

    id: str
    job_id: str
    candidate_id: str
    stage: ApplicationStage = ApplicationStage.APPLIED
    applied_date: date = field(default_factory=date.today)
    notes: list[str] = field(default_factory=list)
    rating: Optional[int] = None  # 1–5 recruiter rating

    def __post_init__(self) -> None:
        if self.rating is not None and not 1 <= self.rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

    def advance(self) -> None:
        """Move to the next pipeline stage."""
        order = [
            ApplicationStage.APPLIED,
            ApplicationStage.SCREENING,
            ApplicationStage.PHONE_INTERVIEW,
            ApplicationStage.TECHNICAL_INTERVIEW,
            ApplicationStage.ONSITE,
            ApplicationStage.OFFER,
            ApplicationStage.HIRED,
        ]
        if self.stage == ApplicationStage.REJECTED:
            raise ValueError("Cannot advance a rejected application")
        if self.stage == ApplicationStage.HIRED:
            raise ValueError("Application already at final stage")
        idx = order.index(self.stage)
        self.stage = order[idx + 1]

    def reject(self, reason: Optional[str] = None) -> None:
        self.stage = ApplicationStage.REJECTED
        if reason:
            self.notes.append(f"Rejected: {reason}")

    def add_note(self, note: str) -> None:
        self.notes.append(note)

    def set_rating(self, rating: int) -> None:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        self.rating = rating


class RecruitmentManager:
    """Manages job postings, candidates, and applications."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobPosting] = {}
        self._candidates: dict[str, Candidate] = {}
        self._applications: dict[str, Application] = {}

    # ── Job postings ─────────────────────────────────────────────────

    def post_job(self, job: JobPosting) -> JobPosting:
        if job.id in self._jobs:
            raise ValueError(f"Job posting {job.id} already exists")
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobPosting]:
        return self._jobs.get(job_id)

    def list_jobs(self, active_only: bool = False, department_id: Optional[str] = None) -> list[JobPosting]:
        results = list(self._jobs.values())
        if active_only:
            results = [j for j in results if j.is_active]
        if department_id:
            results = [j for j in results if j.department_id == department_id]
        return results

    def close_job(self, job_id: str) -> JobPosting:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"Job posting {job_id} not found")
        job.close()
        return job

    # ── Candidates ──────────────────────────────────────────────────

    def add_candidate(self, candidate: Candidate) -> Candidate:
        if candidate.id in self._candidates:
            raise ValueError(f"Candidate {candidate.id} already exists")
        self._candidates[candidate.id] = candidate
        return candidate

    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        return self._candidates.get(candidate_id)

    def search_candidates(self, skill: Optional[str] = None) -> list[Candidate]:
        results = list(self._candidates.values())
        if skill:
            s = skill.lower()
            results = [c for c in results if any(s in sk.lower() for sk in c.skills)]
        return results

    # ── Applications ────────────────────────────────────────────────

    def apply(self, application: Application) -> Application:
        if application.id in self._applications:
            raise ValueError(f"Application {application.id} already exists")
        if application.job_id not in self._jobs:
            raise ValueError(f"Job posting {application.job_id} does not exist")
        if application.candidate_id not in self._candidates:
            raise ValueError(f"Candidate {application.candidate_id} does not exist")
        self._applications[application.id] = application
        return application

    def get_application(self, app_id: str) -> Optional[Application]:
        return self._applications.get(app_id)

    def list_applications(
        self,
        job_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        stage: Optional[ApplicationStage] = None,
    ) -> list[Application]:
        results = list(self._applications.values())
        if job_id:
            results = [a for a in results if a.job_id == job_id]
        if candidate_id:
            results = [a for a in results if a.candidate_id == candidate_id]
        if stage:
            results = [a for a in results if a.stage == stage]
        return results

    def advance_application(self, app_id: str) -> Application:
        app = self._applications.get(app_id)
        if app is None:
            raise KeyError(f"Application {app_id} not found")
        app.advance()
        return app

    def reject_application(self, app_id: str, reason: Optional[str] = None) -> Application:
        app = self._applications.get(app_id)
        if app is None:
            raise KeyError(f"Application {app_id} not found")
        app.reject(reason)
        return app

    def pipeline_summary(self, job_id: str) -> dict[str, int]:
        """Count applications per stage for a job."""
        apps = self.list_applications(job_id=job_id)
        summary: dict[str, int] = {}
        for stage in ApplicationStage:
            summary[stage.value] = sum(1 for a in apps if a.stage == stage)
        return summary
