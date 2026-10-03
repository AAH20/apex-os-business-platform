"""Deepened projects module: Gantt, resources, time tracking, risk, portfolio."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional


# ── Gantt chart with dependencies ──────────────────────────────────────────

class TaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


@dataclass
class GanttTask:
    id: str
    name: str
    start: date
    duration_days: int
    status: TaskStatus = TaskStatus.NOT_STARTED
    progress_pct: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    assignee: Optional[str] = None

    @property
    def end(self) -> date:
        return self.start + timedelta(days=self.duration_days)

    def is_blocked(self, tasks: dict[str, "GanttTask"]) -> bool:
        return any(tasks[d].status != TaskStatus.DONE for d in self.dependencies if d in tasks)

    def critical_path(self, tasks: dict[str, "GanttTask"]) -> list[str]:
        chain = [self.id]
        for dep_id in self.dependencies:
            if dep_id in tasks:
                chain = tasks[dep_id].critical_path(tasks) + chain
        return chain


@dataclass
class GanttChart:
    tasks: dict[str, GanttTask] = field(default_factory=dict)

    def add(self, task: GanttTask) -> None:
        self.tasks[task.id] = task

    def ready_tasks(self) -> list[GanttTask]:
        return [t for t in self.tasks.values()
                if t.status == TaskStatus.NOT_STARTED and not t.is_blocked(self.tasks)]

    def timeline(self) -> list[dict]:
        return sorted(
            [{"id": t.id, "name": t.name, "start": t.start.isoformat(),
              "end": t.end.isoformat(), "status": t.status.value,
              "progress": t.progress_pct, "deps": t.dependencies}
             for t in self.tasks.values()],
            key=lambda x: x["start"],
        )


# ── Resource allocation with capacity planning ─────────────────────────────

@dataclass
class Resource:
    id: str
    name: str
    role: str
    capacity_hours_per_week: float = 40.0
    allocated_hours: float = 0.0

    @property
    def available_hours(self) -> float:
        return max(0.0, self.capacity_hours_per_week - self.allocated_hours)

    @property
    def utilization_pct(self) -> float:
        return (self.allocated_hours / self.capacity_hours_per_week * 100
                if self.capacity_hours_per_week else 0.0)


@dataclass
class Allocation:
    resource_id: str
    project_id: str
    hours: float
    week_start: date


@dataclass
class CapacityPlanner:
    resources: dict[str, Resource] = field(default_factory=dict)
    allocations: list[Allocation] = field(default_factory=list)

    def add_resource(self, r: Resource) -> None:
        self.resources[r.id] = r

    def allocate(self, a: Allocation) -> bool:
        r = self.resources.get(a.resource_id)
        if not r or r.available_hours < a.hours:
            return False
        r.allocated_hours += a.hours
        self.allocations.append(a)
        return True

    def overallocated(self) -> list[Resource]:
        return [r for r in self.resources.values() if r.allocated_hours > r.capacity_hours_per_week]

    def utilization_report(self) -> list[dict]:
        return [{"id": r.id, "name": r.name, "utilization_pct": round(r.utilization_pct, 1),
                 "available_hrs": r.available_hours} for r in self.resources.values()]


# ── Time tracking with timesheets ──────────────────────────────────────────

@dataclass
class TimeEntry:
    id: str
    user_id: str
    project_id: str
    task_id: Optional[str]
    date: date
    hours: float
    billable: bool = True
    description: str = ""


@dataclass
class Timesheet:
    user_id: str
    week_start: date
    entries: list[TimeEntry] = field(default_factory=list)
    submitted: bool = False
    approved: bool = False

    @property
    def total_hours(self) -> float:
        return sum(e.hours for e in self.entries)

    @property
    def billable_hours(self) -> float:
        return sum(e.hours for e in self.entries if e.billable)

    def submit(self) -> None:
        self.submitted = True

    def approve(self) -> None:
        if self.submitted:
            self.approved = True


@dataclass
class TimeTracker:
    timesheets: dict[str, list[Timesheet]] = field(default_factory=dict)

    def log(self, entry: TimeEntry) -> None:
        key = entry.user_id
        if key not in self.timesheets:
            self.timesheets[key] = []
        ws = next((t for t in self.timesheets[key]
                   if t.week_start <= entry.date < t.week_start + timedelta(days=7)), None)
        if ws is None:
            ws = Timesheet(user_id=entry.user_id, week_start=entry.date)
            self.timesheets[key].append(ws)
        ws.entries.append(entry)

    def weekly_summary(self, user_id: str, week_start: date) -> dict:
        ws = next((t for t in self.timesheets.get(user_id, []) if t.week_start == week_start), None)
        if not ws:
            return {"total": 0.0, "billable": 0.0, "entries": 0}
        return {"total": ws.total_hours, "billable": ws.billable_hours, "entries": len(ws.entries)}


# ── Risk management with mitigation ────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Risk:
    id: str
    project_id: str
    description: str
    probability: float  # 0.0–1.0
    impact: float       # 0.0–1.0
    level: RiskLevel = RiskLevel.LOW
    mitigation: str = ""
    owner: Optional[str] = None
    status: str = "open"  # open, mitigated, realized, closed

    @property
    def score(self) -> float:
        return self.probability * self.impact

    def classify(self) -> RiskLevel:
        s = self.score
        if s >= 0.5:
            return RiskLevel.CRITICAL
        if s >= 0.25:
            return RiskLevel.HIGH
        if s >= 0.1:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


@dataclass
class RiskRegister:
    risks: dict[str, Risk] = field(default_factory=dict)

    def add(self, risk: Risk) -> None:
        risk.level = risk.classify()
        self.risks[risk.id] = risk

    def by_project(self, project_id: str) -> list[Risk]:
        return [r for r in self.risks.values() if r.project_id == project_id]

    def open_risks(self) -> list[Risk]:
        return [r for r in self.risks.values() if r.status == "open"]

    def top_risks(self, n: int = 5) -> list[Risk]:
        return sorted(self.open_risks(), key=lambda r: r.score, reverse=True)[:n]

    def mitigate(self, risk_id: str, plan: str) -> bool:
        r = self.risks.get(risk_id)
        if not r:
            return False
        r.mitigation = plan
        r.status = "mitigated"
        return True


# ── Project portfolio with prioritization ──────────────────────────────────

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PortfolioProject:
    id: str
    name: str
    priority: Priority = Priority.MEDIUM
    budget: float = 0.0
    spent: float = 0.0
    expected_value: float = 0.0
    risk_score: float = 0.0
    status: str = "active"  # active, on_hold, cancelled, completed

    @property
    def roi(self) -> float:
        return (self.expected_value - self.spent) / self.spent if self.spent > 0 else 0.0

    @property
    def budget_variance(self) -> float:
        return self.budget - self.spent

    def priority_score(self) -> float:
        weights = {Priority.LOW: 1, Priority.MEDIUM: 2, Priority.HIGH: 3, Priority.CRITICAL: 4}
        return weights[self.priority] * 0.4 + self.roi * 0.3 - self.risk_score * 0.3


@dataclass
class Portfolio:
    projects: dict[str, PortfolioProject] = field(default_factory=dict)

    def add(self, p: PortfolioProject) -> None:
        self.projects[p.id] = p

    def ranked(self) -> list[PortfolioProject]:
        return sorted(self.projects.values(), key=lambda p: p.priority_score(), reverse=True)

    def total_budget(self) -> float:
        return sum(p.budget for p in self.projects.values())

    def total_spent(self) -> float:
        return sum(p.spent for p in self.projects.values())

    def by_priority(self, priority: Priority) -> list[PortfolioProject]:
        return [p for p in self.projects.values() if p.priority == priority]

    def summary(self) -> dict:
        return {
            "project_count": len(self.projects),
            "total_budget": self.total_budget(),
            "total_spent": self.total_spent(),
            "variance": self.total_budget() - self.total_spent(),
            "top_priority": [p.id for p in self.ranked()[:3]],
        }
