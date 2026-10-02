"""Project management engine."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from apex_os_bp.projects.models import (
    GanttChart,
    GanttTask,
    Priority,
    Project,
    ProjectStatus,
    Resource,
    ResourceType,
    Task,
    TaskStatus,
    TimeEntry,
)


class ProjectEngine:
    """Project engine with project, task, Gantt, resource, and time tracking."""

    def __init__(self):
        self._projects: Dict[str, Project] = {}
        self._tasks: Dict[str, Task] = {}
        self._resources: Dict[str, Resource] = {}
        self._time_entries: Dict[str, TimeEntry] = {}
        self._gantt_charts: Dict[str, GanttChart] = {}

    # ── Project Management ──────────────────────────────────────────

    def create_project(
        self,
        name: str,
        description: str = "",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        budget: float = 0.0,
        **kwargs,
    ) -> Project:
        """Create a new project."""
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            **kwargs,
        )
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        return self._projects.get(project_id)

    def update_project(self, project_id: str, **kwargs) -> Optional[Project]:
        """Update project fields."""
        project = self._projects.get(project_id)
        if not project:
            return None
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        return project

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its tasks."""
        if project_id not in self._projects:
            return False
        # Delete associated tasks
        project = self._projects[project_id]
        for task_id in list(project.task_ids):
            self.delete_task(task_id)
        del self._projects[project_id]
        return True

    def list_projects(
        self, status: Optional[ProjectStatus] = None
    ) -> List[Project]:
        """List all projects, optionally filtered by status."""
        projects = list(self._projects.values())
        if status:
            projects = [p for p in projects if p.status == status]
        return projects

    def get_project_tasks(self, project_id: str) -> List[Task]:
        """Get all tasks for a project."""
        project = self._projects.get(project_id)
        if not project:
            return []
        return [self._tasks[tid] for tid in project.task_ids if tid in self._tasks]

    def project_progress(self, project_id: str) -> float:
        """Calculate project progress percentage."""
        tasks = self.get_project_tasks(project_id)
        project = self._projects.get(project_id)
        if not project:
            return 0.0
        return project.progress_percentage(tasks)

    def project_summary(self, project_id: str) -> Dict:
        """Generate project summary."""
        project = self._projects.get(project_id)
        if not project:
            return {}
        tasks = self.get_project_tasks(project_id)
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        in_progress_tasks = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
        blocked_tasks = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)
        overdue_tasks = sum(1 for t in tasks if t.is_overdue())

        total_hours = sum(
            entry.hours
            for entry in self._time_entries.values()
            if entry.task_id in project.task_ids
        )

        return {
            "project_id": project.id,
            "name": project.name,
            "status": project.status.value,
            "progress_percentage": project.progress_percentage(tasks),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "blocked_tasks": blocked_tasks,
            "overdue_tasks": overdue_tasks,
            "total_hours_logged": total_hours,
            "budget": project.budget,
            "is_overdue": project.is_overdue(),
            "duration_days": project.duration_days(),
        }

    # ── Task Management ─────────────────────────────────────────────

    def create_task(
        self,
        project_id: str,
        name: str,
        description: str = "",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        duration_days: int = 1,
        dependencies: Optional[List[str]] = None,
        assigned_to: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        **kwargs,
    ) -> Task:
        """Create a new task in a project."""
        if project_id not in self._projects:
            raise ValueError(f"Project not found: {project_id}")

        task = Task(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
            dependencies=dependencies or [],
            assigned_to=assigned_to,
            priority=priority,
            **kwargs,
        )
        self._tasks[task.id] = task
        self._projects[project_id].task_ids.append(task.id)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Update task fields."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        # Remove from project
        project = self._projects.get(task.project_id)
        if project and task_id in project.task_ids:
            project.task_ids.remove(task_id)
        # Remove from resource assignments
        for resource in self._resources.values():
            if task_id in resource.assigned_tasks:
                resource.assigned_tasks.remove(task_id)
        # Remove associated time entries
        for entry_id in list(self._time_entries.keys()):
            if self._time_entries[entry_id].task_id == task_id:
                del self._time_entries[entry_id]
        del self._tasks[task_id]
        return True

    def list_tasks(
        self,
        project_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[str] = None,
    ) -> List[Task]:
        """List tasks with optional filters."""
        tasks = list(self._tasks.values())
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        return tasks

    def add_task_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """Add a dependency to a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
        return True

    def remove_task_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """Remove a dependency from a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        if depends_on_id in task.dependencies:
            task.dependencies.remove(depends_on_id)
        return True

    def start_task(self, task_id: str) -> Optional[Task]:
        """Start a task (set status to in_progress)."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        if task.is_blocked(self._tasks):
            raise ValueError(f"Task {task_id} is blocked by incomplete dependencies")
        task.status = TaskStatus.IN_PROGRESS
        return task

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Complete a task."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = TaskStatus.COMPLETED
        task.completion_percentage = 100.0
        return task

    def block_task(self, task_id: str) -> Optional[Task]:
        """Block a task."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = TaskStatus.BLOCKED
        return task

    def set_task_progress(self, task_id: str, percentage: float) -> Optional[Task]:
        """Set task completion percentage."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.completion_percentage = max(0.0, min(100.0, percentage))
        if task.completion_percentage >= 100.0:
            task.status = TaskStatus.COMPLETED
        elif task.completion_percentage > 0.0:
            task.status = TaskStatus.IN_PROGRESS
        return task

    def get_critical_path(self, project_id: str) -> List[str]:
        """Get critical path for a project."""
        tasks = self.get_project_tasks(project_id)
        if not tasks:
            return []
        task_deps = {t.id: t.dependencies for t in tasks}
        gantt = self.generate_gantt_chart(project_id)
        return gantt.critical_path(task_deps)

    # ── Gantt Chart ────────────────────────────────────────────────

    def generate_gantt_chart(
        self, project_id: str, name: Optional[str] = None
    ) -> GanttChart:
        """Generate a Gantt chart for a project."""
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        tasks = self.get_project_tasks(project_id)
        gantt_tasks: List[GanttTask] = []

        for task in tasks:
            task_start = task.start_date or project.start_date or date.today()
            task_end = task.end_date or (task_start + timedelta(days=task.duration_days))
            gantt_task = GanttTask(
                task_id=task.id,
                name=task.name,
                start_date=task_start,
                end_date=task_end,
                duration_days=(task_end - task_start).days,
                progress_percentage=task.completion_percentage,
                dependencies=task.dependencies,
                assigned_to=task.assigned_to,
                status=task.status,
                priority=task.priority,
            )
            gantt_tasks.append(gantt_task)

        # Determine chart date range
        all_dates = []
        for gt in gantt_tasks:
            all_dates.extend([gt.start_date, gt.end_date])
        chart_start = min(all_dates) if all_dates else project.start_date or date.today()
        chart_end = max(all_dates) if all_dates else project.end_date or date.today()

        chart = GanttChart(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name or f"{project.name} Gantt Chart",
            tasks=gantt_tasks,
            start_date=chart_start,
            end_date=chart_end,
        )
        self._gantt_charts[chart.id] = chart
        return chart

    def get_gantt_chart(self, chart_id: str) -> Optional[GanttChart]:
        """Get Gantt chart by ID."""
        return self._gantt_charts.get(chart_id)

    def update_gantt_task(
        self, chart_id: str, task_id: str, **kwargs
    ) -> Optional[GanttTask]:
        """Update a task in a Gantt chart."""
        chart = self._gantt_charts.get(chart_id)
        if not chart:
            return None
        for gt in chart.tasks:
            if gt.task_id == task_id:
                for key, value in kwargs.items():
                    if hasattr(gt, key):
                        setattr(gt, key, value)
                return gt
        return None

    def gantt_chart_summary(self, chart_id: str) -> Dict:
        """Generate Gantt chart summary."""
        chart = self._gantt_charts.get(chart_id)
        if not chart:
            return {}
        total_tasks = len(chart.tasks)
        completed = sum(1 for t in chart.tasks if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in chart.tasks if t.status == TaskStatus.IN_PROGRESS)
        not_started = sum(1 for t in chart.tasks if t.status == TaskStatus.NOT_STARTED)
        blocked = sum(1 for t in chart.tasks if t.status == TaskStatus.BLOCKED)
        avg_progress = (
            sum(t.progress_percentage for t in chart.tasks) / total_tasks
            if total_tasks > 0
            else 0.0
        )
        return {
            "chart_id": chart.id,
            "project_id": chart.project_id,
            "name": chart.name,
            "total_tasks": total_tasks,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "blocked": blocked,
            "average_progress": avg_progress,
            "total_duration_days": chart.total_duration_days(),
            "start_date": chart.start_date.isoformat() if chart.start_date else None,
            "end_date": chart.end_date.isoformat() if chart.end_date else None,
        }

    # ── Resource Allocation ────────────────────────────────────────

    def create_resource(
        self,
        name: str,
        type: ResourceType,
        capacity: float = 1.0,
        cost_rate: float = 0.0,
        unit: str = "hour",
        **kwargs,
    ) -> Resource:
        """Create a new resource."""
        resource = Resource(
            id=str(uuid.uuid4()),
            name=name,
            type=type,
            capacity=capacity,
            cost_rate=cost_rate,
            unit=unit,
            **kwargs,
        )
        self._resources[resource.id] = resource
        return resource

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        """Get resource by ID."""
        return self._resources.get(resource_id)

    def update_resource(self, resource_id: str, **kwargs) -> Optional[Resource]:
        """Update resource fields."""
        resource = self._resources.get(resource_id)
        if not resource:
            return None
        for key, value in kwargs.items():
            if hasattr(resource, key):
                setattr(resource, key, value)
        return resource

    def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource."""
        if resource_id not in self._resources:
            return False
        # Remove from project associations
        for project in self._projects.values():
            if resource_id in project.resource_ids:
                project.resource_ids.remove(resource_id)
        # Unassign tasks
        resource = self._resources[resource_id]
        for task_id in resource.assigned_tasks:
            task = self._tasks.get(task_id)
            if task and task.assigned_to == resource_id:
                task.assigned_to = None
        del self._resources[resource_id]
        return True

    def list_resources(
        self, type: Optional[ResourceType] = None
    ) -> List[Resource]:
        """List all resources, optionally filtered by type."""
        resources = list(self._resources.values())
        if type:
            resources = [r for r in resources if r.type == type]
        return resources

    def assign_resource_to_task(
        self, resource_id: str, task_id: str
    ) -> bool:
        """Assign a resource to a task."""
        resource = self._resources.get(resource_id)
        task = self._tasks.get(task_id)
        if not resource or not task:
            return False
        if task_id not in resource.assigned_tasks:
            resource.assigned_tasks.append(task_id)
        task.assigned_to = resource_id
        return True

    def unassign_resource_from_task(
        self, resource_id: str, task_id: str
    ) -> bool:
        """Unassign a resource from a task."""
        resource = self._resources.get(resource_id)
        task = self._tasks.get(task_id)
        if not resource or not task:
            return False
        if task_id in resource.assigned_tasks:
            resource.assigned_tasks.remove(task_id)
        if task.assigned_to == resource_id:
            task.assigned_to = None
        return True

    def get_resource_allocation(self, resource_id: str) -> Dict:
        """Get allocation details for a resource."""
        resource = self._resources.get(resource_id)
        if not resource:
            return {}
        allocated_hours = sum(
            self._tasks[tid].duration_days * 8
            for tid in resource.assigned_tasks
            if tid in self._tasks
        )
        return {
            "resource_id": resource.id,
            "name": resource.name,
            "type": resource.type.value,
            "capacity": resource.capacity,
            "allocated_hours": allocated_hours,
            "utilization_percentage": resource.utilization_percentage(allocated_hours),
            "is_overallocated": resource.is_overallocated(allocated_hours),
            "assigned_tasks": len(resource.assigned_tasks),
            "cost_rate": resource.cost_rate,
        }

    def get_project_resource_allocation(self, project_id: str) -> Dict:
        """Get resource allocation for a project."""
        project = self._projects.get(project_id)
        if not project:
            return {}
        allocations = []
        for rid in project.resource_ids:
            resource = self._resources.get(rid)
            if resource:
                allocations.append(self.get_resource_allocation(rid))
        return {
            "project_id": project_id,
            "project_name": project.name,
            "total_resources": len(allocations),
            "allocations": allocations,
        }

    def check_overallocation(self) -> List[Dict]:
        """Check for overallocated resources."""
        overallocated = []
        for resource in self._resources.values():
            allocated_hours = sum(
                self._tasks[tid].duration_days * 8
                for tid in resource.assigned_tasks
                if tid in self._tasks
            )
            if resource.is_overallocated(allocated_hours):
                overallocated.append(
                    {
                        "resource_id": resource.id,
                        "name": resource.name,
                        "capacity": resource.capacity,
                        "allocated_hours": allocated_hours,
                        "overallocation_percentage": resource.utilization_percentage(
                            allocated_hours
                        )
                        - 100.0,
                    }
                )
        return overallocated

    # ── Time Tracking ──────────────────────────────────────────────

    def start_time_entry(
        self,
        task_id: str,
        user_id: str,
        description: str = "",
        billable: bool = True,
        start_time: Optional[datetime] = None,
    ) -> TimeEntry:
        """Start a new time entry."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        entry = TimeEntry(
            id=str(uuid.uuid4()),
            task_id=task_id,
            user_id=user_id,
            start_time=start_time or datetime.now(),
            description=description,
            billable=billable,
        )
        self._time_entries[entry.id] = entry
        return entry

    def stop_time_entry(
        self, entry_id: str, end_time: Optional[datetime] = None
    ) -> Optional[TimeEntry]:
        """Stop a running time entry."""
        entry = self._time_entries.get(entry_id)
        if not entry:
            return None
        if entry.is_running():
            entry.end_time = end_time or datetime.now()
            duration = entry.duration()
            if duration:
                entry.hours = duration.total_seconds() / 3600.0
        return entry

    def get_time_entry(self, entry_id: str) -> Optional[TimeEntry]:
        """Get time entry by ID."""
        return self._time_entries.get(entry_id)

    def delete_time_entry(self, entry_id: str) -> bool:
        """Delete a time entry."""
        if entry_id not in self._time_entries:
            return False
        del self._time_entries[entry_id]
        return True

    def list_time_entries(
        self,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        billable: Optional[bool] = None,
    ) -> List[TimeEntry]:
        """List time entries with optional filters."""
        entries = list(self._time_entries.values())
        if task_id:
            entries = [e for e in entries if e.task_id == task_id]
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        if billable is not None:
            entries = [e for e in entries if e.billable == billable]
        return entries

    def get_task_time_summary(self, task_id: str) -> Dict:
        """Get time summary for a task."""
        entries = [e for e in self._time_entries.values() if e.task_id == task_id]
        total_hours = sum(e.hours for e in entries)
        billable_hours = sum(e.hours for e in entries if e.billable)
        return {
            "task_id": task_id,
            "total_entries": len(entries),
            "total_hours": total_hours,
            "billable_hours": billable_hours,
            "non_billable_hours": total_hours - billable_hours,
        }

    def get_project_time_summary(self, project_id: str) -> Dict:
        """Get time summary for a project."""
        project = self._projects.get(project_id)
        if not project:
            return {}
        entries = [
            e for e in self._time_entries.values() if e.task_id in project.task_ids
        ]
        total_hours = sum(e.hours for e in entries)
        billable_hours = sum(e.hours for e in entries if e.billable)
        return {
            "project_id": project_id,
            "project_name": project.name,
            "total_entries": len(entries),
            "total_hours": total_hours,
            "billable_hours": billable_hours,
            "non_billable_hours": total_hours - billable_hours,
        }

    def get_user_time_summary(self, user_id: str) -> Dict:
        """Get time summary for a user."""
        entries = [e for e in self._time_entries.values() if e.user_id == user_id]
        total_hours = sum(e.hours for e in entries)
        billable_hours = sum(e.hours for e in entries if e.billable)
        tasks_worked = len(set(e.task_id for e in entries))
        return {
            "user_id": user_id,
            "total_entries": len(entries),
            "total_hours": total_hours,
            "billable_hours": billable_hours,
            "non_billable_hours": total_hours - billable_hours,
            "tasks_worked": tasks_worked,
        }

    def get_running_timers(self) -> List[TimeEntry]:
        """Get all running time entries."""
        return [e for e in self._time_entries.values() if e.is_running()]

    # ── Reporting ──────────────────────────────────────────────────

    def generate_project_report(self, project_id: str) -> Dict:
        """Generate comprehensive project report."""
        project = self._projects.get(project_id)
        if not project:
            return {}

        summary = self.project_summary(project_id)
        time_summary = self.get_project_time_summary(project_id)
        resource_allocation = self.get_project_resource_allocation(project_id)

        # Task breakdown by status
        tasks = self.get_project_tasks(project_id)
        tasks_by_status: Dict[str, int] = {}
        for status in TaskStatus:
            count = sum(1 for t in tasks if t.status == status)
            if count > 0:
                tasks_by_status[status.value] = count

        # Priority breakdown
        tasks_by_priority: Dict[str, int] = {}
        for priority in Priority:
            count = sum(1 for t in tasks if t.priority == priority)
            if count > 0:
                tasks_by_priority[priority.name] = count

        return {
            "project": summary,
            "time": time_summary,
            "resources": resource_allocation,
            "tasks_by_status": tasks_by_status,
            "tasks_by_priority": tasks_by_priority,
            "critical_path": self.get_critical_path(project_id),
        }
