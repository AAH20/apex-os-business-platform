"""Project management data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class ProjectStatus(Enum):
    """Project status."""

    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """Task status."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Task priority."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ResourceType(Enum):
    """Resource type."""

    HUMAN = "human"
    EQUIPMENT = "equipment"
    MATERIAL = "material"
    BUDGET = "budget"


@dataclass
class Project:
    """Project data structure."""

    id: str
    name: str
    description: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: ProjectStatus = ProjectStatus.PLANNING
    budget: float = 0.0
    metadata: Dict = field(default_factory=dict)
    task_ids: List[str] = field(default_factory=list)
    resource_ids: List[str] = field(default_factory=list)

    def duration_days(self) -> Optional[int]:
        """Calculate project duration in days."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    def is_overdue(self) -> bool:
        """Check if project is overdue."""
        if self.end_date and self.status != ProjectStatus.COMPLETED:
            return date.today() > self.end_date
        return False

    def progress_percentage(self, tasks: List[Task]) -> float:
        """Calculate project progress based on tasks."""
        if not tasks:
            return 0.0
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        return (completed / len(tasks)) * 100


@dataclass
class Task:
    """Task data structure."""

    id: str
    project_id: str
    name: str
    description: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: int = 1
    dependencies: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    priority: Priority = Priority.MEDIUM
    completion_percentage: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if self.end_date and self.status != TaskStatus.COMPLETED:
            return date.today() > self.end_date
        return False

    def is_blocked(self, tasks: Dict[str, Task]) -> bool:
        """Check if task is blocked by incomplete dependencies."""
        for dep_id in self.dependencies:
            dep = tasks.get(dep_id)
            if dep and dep.status != TaskStatus.COMPLETED:
                return True
        return False

    def can_start(self, tasks: Dict[str, Task]) -> bool:
        """Check if task can start (all dependencies completed)."""
        return not self.is_blocked(tasks)

    def remaining_days(self) -> Optional[int]:
        """Calculate remaining days."""
        if self.end_date:
            return (self.end_date - date.today()).days
        return None


@dataclass
class Resource:
    """Resource data structure."""

    id: str
    name: str
    type: ResourceType
    capacity: float = 1.0
    cost_rate: float = 0.0
    unit: str = "hour"
    metadata: Dict = field(default_factory=dict)
    assigned_tasks: List[str] = field(default_factory=list)

    def utilization_percentage(self, allocated_hours: float) -> float:
        """Calculate utilization percentage."""
        if self.capacity <= 0:
            return 0.0
        return min(100.0, (allocated_hours / self.capacity) * 100)

    def is_overallocated(self, allocated_hours: float) -> bool:
        """Check if resource is overallocated."""
        return allocated_hours > self.capacity


@dataclass
class TimeEntry:
    """Time entry data structure."""

    id: str
    task_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    hours: float = 0.0
    description: str = ""
    billable: bool = True
    metadata: Dict = field(default_factory=dict)

    def duration(self) -> Optional[timedelta]:
        """Calculate duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    def is_running(self) -> bool:
        """Check if time entry is still running."""
        return self.end_time is None


@dataclass
class GanttTask:
    """Gantt chart task representation."""

    task_id: str
    name: str
    start_date: date
    end_date: date
    duration_days: int
    progress_percentage: float
    dependencies: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    priority: Priority = Priority.MEDIUM
    is_milestone: bool = False
    parent_id: Optional[str] = None


@dataclass
class GanttChart:
    """Gantt chart data structure."""

    id: str
    project_id: str
    name: str
    tasks: List[GanttTask] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime = field(default_factory=datetime.now)

    def total_duration_days(self) -> int:
        """Calculate total duration in days."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return 0

    def tasks_by_date(self) -> Dict[date, List[GanttTask]]:
        """Group tasks by start date."""
        result: Dict[date, List[GanttTask]] = {}
        for task in self.tasks:
            if task.start_date not in result:
                result[task.start_date] = []
            result[task.start_date].append(task)
        return result

    def critical_path(self, task_dependencies: Dict[str, List[str]]) -> List[str]:
        """Calculate critical path using topological sort."""
        # Build adjacency list and in-degree
        in_degree: Dict[str, int] = {t.task_id: 0 for t in self.tasks}
        adj: Dict[str, List[str]] = {t.task_id: [] for t in self.tasks}

        for task in self.tasks:
            for dep_id in task_dependencies.get(task.task_id, []):
                if dep_id in adj:
                    adj[dep_id].append(task.task_id)
                    in_degree[task.task_id] += 1

        # Kahn's algorithm
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        path: List[str] = []

        while queue:
            # Sort by priority (higher first) then by start date
            queue.sort(
                key=lambda tid: (
                    -next(
                        (
                            t.priority.value
                            for t in self.tasks
                            if t.task_id == tid
                        ),
                        0,
                    ),
                    next(
                        (
                            t.start_date
                            for t in self.tasks
                            if t.task_id == tid
                        ),
                        date.max,
                    ),
                )
            )
            current = queue.pop(0)
            path.append(current)
            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return path
