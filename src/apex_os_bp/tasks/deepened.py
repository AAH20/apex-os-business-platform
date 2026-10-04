"""Deepened tasks module: subtasks, dependencies, templates, automation, analytics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any


class TaskState(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class Recurrence(Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class TriggerType(Enum):
    STATUS_CHANGE = "status_change"
    ASSIGNED_TO = "assigned_to"
    DUE_DATE_REACHED = "due_date_reached"
    TASK_CREATED = "task_created"


@dataclass
class Subtask:
    id: str
    title: str
    state: TaskState = TaskState.TODO
    effort: int = 1
    created_at: datetime = field(default_factory=datetime.now)

    def complete(self) -> None:
        self.state = TaskState.DONE


@dataclass
class Task:
    id: str
    title: str
    state: TaskState = TaskState.TODO
    effort: int = 1
    duration_days: int = 1
    assignee: str | None = None
    due_date: date | None = None
    created_at: datetime = field(default_factory=datetime.now)
    subtasks: list[Subtask] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    template_id: str | None = None
    recurrence: Recurrence = Recurrence.NONE
    automation_triggers: list[dict[str, Any]] = field(default_factory=list)

    def add_subtask(self, title: str, effort: int = 1) -> Subtask:
        st = Subtask(id=str(uuid.uuid4())[:8], title=title, effort=effort)
        self.subtasks.append(st)
        return st

    def subtask_progress(self) -> float:
        if not self.subtasks:
            return 1.0 if self.state == TaskState.DONE else 0.0
        return sum(1 for s in self.subtasks if s.state == TaskState.DONE) / len(self.subtasks)

    def effective_effort(self) -> int:
        return sum(s.effort for s in self.subtasks) if self.subtasks else self.effort


class DependencyGraph:
    """Manages task dependencies and computes critical paths."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    def depends_on(self, task_id: str, dep_ids: list[str]) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].dependencies.extend(dep_ids)

    def _topo_sort(self) -> list[str]:
        visited: set[str] = set()
        order: list[str] = []

        def visit(tid: str) -> None:
            if tid in visited:
                return
            visited.add(tid)
            for dep in self._tasks.get(tid, Task(id="", title="")).dependencies:
                visit(dep)
            order.append(tid)

        for tid in self._tasks:
            visit(tid)
        return order

    def critical_path(self) -> list[str]:
        """Return task IDs on the critical path (longest duration chain)."""
        order = self._topo_sort()
        dist: dict[str, int] = {}
        pred: dict[str, str | None] = {}
        for tid in order:
            task = self._tasks[tid]
            best, best_pred = 0, None
            for dep in task.dependencies:
                if dist.get(dep, 0) > best:
                    best, best_pred = dist[dep], dep
            dist[tid] = best + task.duration_days
            pred[tid] = best_pred
        if not dist:
            return []
        end = max(dist, key=lambda k: dist[k])
        path: list[str] = []
        cur: str | None = end
        while cur is not None:
            path.append(cur)
            cur = pred[cur]
        return list(reversed(path))

    def blocked_tasks(self) -> list[str]:
        """Return IDs of tasks whose dependencies are not all done."""
        blocked = []
        for tid, task in self._tasks.items():
            if task.state == TaskState.DONE:
                continue
            for dep in task.dependencies:
                dep_task = self._tasks.get(dep)
                if dep_task and dep_task.state != TaskState.DONE:
                    blocked.append(tid)
                    break
        return blocked


@dataclass
class TaskTemplate:
    id: str
    name: str
    title_pattern: str
    default_effort: int = 1
    default_duration: int = 1
    recurrence: Recurrence = Recurrence.NONE
    subtask_specs: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def instantiate(self, **kwargs: Any) -> Task:
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=self.title_pattern.format(**kwargs),
            effort=self.default_effort,
            duration_days=self.default_duration,
            template_id=self.id,
            recurrence=self.recurrence,
        )
        for spec in self.subtask_specs:
            task.add_subtask(spec["title"], spec.get("effort", 1))
        return task


class TemplateRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, TaskTemplate] = {}

    def register(self, template: TaskTemplate) -> None:
        self._templates[template.id] = template

    def get(self, template_id: str) -> TaskTemplate | None:
        return self._templates.get(template_id)

    def list_all(self) -> list[TaskTemplate]:
        return list(self._templates.values())

    def create_recurring(self, template_id: str, start: date, count: int, **kwargs: Any) -> list[Task]:
        tmpl = self._templates.get(template_id)
        if not tmpl:
            return []
        tasks = []
        for i in range(count):
            t = tmpl.instantiate(**kwargs)
            if tmpl.recurrence == Recurrence.DAILY:
                t.due_date = start + timedelta(days=i)
            elif tmpl.recurrence == Recurrence.WEEKLY:
                t.due_date = start + timedelta(weeks=i)
            elif tmpl.recurrence == Recurrence.MONTHLY:
                t.due_date = date(start.year, start.month + i, start.day)
            elif tmpl.recurrence == Recurrence.YEARLY:
                t.due_date = date(start.year + i, start.month, start.day)
            tasks.append(t)
        return tasks


class AutomationEngine:
    """Evaluates trigger conditions and executes actions."""

    def __init__(self) -> None:
        self._rules: list[dict[str, Any]] = []

    def add_rule(
        self,
        trigger: TriggerType,
        condition: dict[str, Any],
        action: str,
        action_params: dict[str, Any] | None = None
    ) -> None:
        self._rules.append({"trigger": trigger, "condition": condition,
                           "action": action, "action_params": action_params or {}})

    def evaluate(self, task: Task, event: TriggerType, context: dict[str, Any] | None = None) -> list[str]:
        fired = []
        ctx = context or {}
        for rule in self._rules:
            if rule["trigger"] != event:
                continue
            if self._matches(rule["condition"], task, ctx):
                fired.append(rule["action"])
                self._execute(rule["action"], rule["action_params"], task, ctx)
        return fired

    def _matches(self, condition: dict[str, Any], task: Task, ctx: dict[str, Any]) -> bool:
        for key, val in condition.items():
            if key == "state" and task.state.value != val:
                return False
            if key == "assignee" and task.assignee != val:
                return False
            if key == "overdue" and not (task.due_date and task.due_date < date.today()):
                return False
            if key == "subtask_progress_below" and task.subtask_progress() >= val:
                return False
        return True

    def _execute(self, action: str, params: dict[str, Any], task: Task, ctx: dict[str, Any]) -> None:
        if action == "notify":
            ctx.setdefault("notifications", []).append(f"Task '{task.title}' triggered: {params.get('message', '')}")
        elif action == "escalate":
            ctx.setdefault("escalations", []).append(task.id)
        elif action == "auto_assign":
            task.assignee = params.get("assignee")


@dataclass
class BurndownPoint:
    date: date
    total_effort: int
    remaining_effort: int
    ideal_effort: int


class TaskAnalytics:
    """Burndown charts and velocity metrics."""

    def __init__(self, tasks: list[Task]) -> None:
        self.tasks = tasks

    def total_effort(self) -> int:
        return sum(t.effective_effort() for t in self.tasks)

    def remaining_effort(self) -> int:
        return sum(t.effective_effort() for t in self.tasks if t.state != TaskState.DONE)

    def burndown(self, start: date, end: date) -> list[BurndownPoint]:
        total = self.total_effort()
        days = (end - start).days + 1
        if days <= 0:
            return []
        daily_ideal = total / days
        points = []
        for i in range(days):
            d = start + timedelta(days=i)
            remaining = sum(t.effective_effort()
                            for t in self.tasks if t.state != TaskState.DONE and t.created_at.date() <= d)
            ideal = max(0, total - daily_ideal * (i + 1))
            points.append(BurndownPoint(d, total, remaining, int(ideal)))
        return points

    def velocity(self, completed_tasks: list[Task], period_days: int = 7) -> float:
        if period_days <= 0:
            return 0.0
        return sum(t.effective_effort() for t in completed_tasks) / period_days

    def completion_rate(self) -> float:
        if not self.tasks:
            return 0.0
        return sum(1 for t in self.tasks if t.state == TaskState.DONE) / len(self.tasks)

    def summary(self) -> dict[str, Any]:
        return {
            "total_tasks": len(self.tasks),
            "total_effort": self.total_effort(),
            "remaining_effort": self.remaining_effort(),
            "completion_rate": round(self.completion_rate(), 2),
            "done": sum(1 for t in self.tasks if t.state == TaskState.DONE),
            "in_progress": sum(1 for t in self.tasks if t.state == TaskState.IN_PROGRESS),
            "blocked": sum(1 for t in self.tasks if t.state == TaskState.BLOCKED),
        }
