"""Tests for project management module."""
from datetime import date, datetime, timedelta

import pytest

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
from apex_os_bp.projects.engine import ProjectEngine


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def engine():
    """Create a fresh ProjectEngine."""
    return ProjectEngine()


@pytest.fixture
def sample_project(engine):
    """Create a sample project."""
    return engine.create_project(
        name="Test Project",
        description="A test project",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        budget=50000.0,
    )


@pytest.fixture
def sample_tasks(engine, sample_project):
    """Create sample tasks for a project."""
    task1 = engine.create_task(
        project_id=sample_project.id,
        name="Task 1",
        description="First task",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 15),
        duration_days=14,
        priority=Priority.HIGH,
    )
    task2 = engine.create_task(
        project_id=sample_project.id,
        name="Task 2",
        description="Second task",
        start_date=date(2026, 1, 16),
        end_date=date(2026, 2, 1),
        duration_days=16,
        dependencies=[task1.id],
        priority=Priority.MEDIUM,
    )
    task3 = engine.create_task(
        project_id=sample_project.id,
        name="Task 3",
        description="Third task",
        start_date=date(2026, 2, 2),
        end_date=date(2026, 2, 28),
        duration_days=26,
        dependencies=[task2.id],
        priority=Priority.LOW,
    )
    return [task1, task2, task3]


@pytest.fixture
def sample_resources(engine):
    """Create sample resources."""
    dev = engine.create_resource(
        name="Developer 1",
        type=ResourceType.HUMAN,
        capacity=160.0,
        cost_rate=75.0,
        unit="hour",
    )
    designer = engine.create_resource(
        name="Designer 1",
        type=ResourceType.HUMAN,
        capacity=120.0,
        cost_rate=60.0,
        unit="hour",
    )
    server = engine.create_resource(
        name="Server",
        type=ResourceType.EQUIPMENT,
        capacity=720.0,
        cost_rate=0.50,
        unit="hour",
    )
    return [dev, designer, server]


# ── Project Creation Tests ────────────────────────────────────────


class TestProjectCreation:
    """Test project creation and management."""

    def test_create_project(self, engine):
        """Project can be created with basic fields."""
        project = engine.create_project(
            name="New Project",
            description="A new project",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            budget=100000.0,
        )
        assert project.id is not None
        assert project.name == "New Project"
        assert project.description == "A new project"
        assert project.start_date == date(2026, 1, 1)
        assert project.end_date == date(2026, 6, 30)
        assert project.budget == 100000.0
        assert project.status == ProjectStatus.PLANNING

    def test_create_project_minimal(self, engine):
        """Project can be created with minimal fields."""
        project = engine.create_project(name="Minimal Project")
        assert project.name == "Minimal Project"
        assert project.status == ProjectStatus.PLANNING
        assert project.budget == 0.0

    def test_get_project(self, engine, sample_project):
        """Project can be retrieved by ID."""
        retrieved = engine.get_project(sample_project.id)
        assert retrieved is not None
        assert retrieved.id == sample_project.id
        assert retrieved.name == sample_project.name

    def test_get_project_not_found(self, engine):
        """Getting non-existent project returns None."""
        result = engine.get_project("non-existent-id")
        assert result is None

    def test_update_project(self, engine, sample_project):
        """Project can be updated."""
        updated = engine.update_project(
            sample_project.id,
            name="Updated Project",
            status=ProjectStatus.ACTIVE,
            budget=75000.0,
        )
        assert updated.name == "Updated Project"
        assert updated.status == ProjectStatus.ACTIVE
        assert updated.budget == 75000.0

    def test_update_project_not_found(self, engine):
        """Updating non-existent project returns None."""
        result = engine.update_project("non-existent", name="New Name")
        assert result is None

    def test_delete_project(self, engine, sample_project):
        """Project can be deleted."""
        result = engine.delete_project(sample_project.id)
        assert result is True
        assert engine.get_project(sample_project.id) is None

    def test_delete_project_cascades_tasks(self, engine, sample_project, sample_tasks):
        """Deleting a project also deletes its tasks."""
        task_ids = [t.id for t in sample_tasks]
        engine.delete_project(sample_project.id)
        for tid in task_ids:
            assert engine.get_task(tid) is None

    def test_delete_project_not_found(self, engine):
        """Deleting non-existent project returns False."""
        result = engine.delete_project("non-existent")
        assert result is False

    def test_list_projects(self, engine):
        """All projects can be listed."""
        engine.create_project(name="Project A")
        engine.create_project(name="Project B")
        engine.create_project(name="Project C")
        projects = engine.list_projects()
        assert len(projects) == 3

    def test_list_projects_by_status(self, engine):
        """Projects can be filtered by status."""
        p1 = engine.create_project(name="Active Project")
        engine.create_project(name="Planning Project")
        engine.update_project(p1.id, status=ProjectStatus.ACTIVE)
        active = engine.list_projects(status=ProjectStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].name == "Active Project"

    def test_project_duration(self, sample_project):
        """Project duration is calculated correctly."""
        assert sample_project.duration_days() == 89

    def test_project_not_overdue(self, engine):
        """Project is not overdue when end date is in the future."""
        project = engine.create_project(
            name="Future Project",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )
        assert project.is_overdue() is False

    def test_project_overdue(self, engine):
        """Project is overdue when end date has passed."""
        project = engine.create_project(
            name="Overdue Project",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        assert project.is_overdue() is True

    def test_project_progress_no_tasks(self, sample_project):
        """Project progress is 0 with no tasks."""
        assert sample_project.progress_percentage([]) == 0.0

    def test_project_progress_with_tasks(self, sample_project, sample_tasks):
        """Project progress is calculated from tasks."""
        sample_tasks[0].status = TaskStatus.COMPLETED
        progress = sample_project.progress_percentage(sample_tasks)
        assert progress == pytest.approx(33.33, rel=0.01)

    def test_project_summary(self, engine, sample_project, sample_tasks):
        """Project summary can be generated."""
        summary = engine.project_summary(sample_project.id)
        assert summary["project_id"] == sample_project.id
        assert summary["name"] == "Test Project"
        assert summary["total_tasks"] == 3
        assert summary["completed_tasks"] == 0
        assert summary["budget"] == 50000.0

    def test_project_summary_not_found(self, engine):
        """Project summary for non-existent project returns empty dict."""
        summary = engine.project_summary("non-existent")
        assert summary == {}


# ── Task Management Tests ─────────────────────────────────────────


class TestTaskManagement:
    """Test task management."""

    def test_create_task(self, engine, sample_project):
        """Task can be created in a project."""
        task = engine.create_task(
            project_id=sample_project.id,
            name="New Task",
            description="A new task",
            duration_days=5,
            priority=Priority.HIGH,
        )
        assert task.id is not None
        assert task.project_id == sample_project.id
        assert task.name == "New Task"
        assert task.status == TaskStatus.NOT_STARTED
        assert task.priority == Priority.HIGH
        assert task.completion_percentage == 0.0

    def test_create_task_invalid_project(self, engine):
        """Creating task in non-existent project raises error."""
        with pytest.raises(ValueError, match="Project not found"):
            engine.create_task(project_id="invalid", name="Task")

    def test_get_task(self, engine, sample_tasks):
        """Task can be retrieved by ID."""
        task = engine.get_task(sample_tasks[0].id)
        assert task is not None
        assert task.name == "Task 1"

    def test_get_task_not_found(self, engine):
        """Getting non-existent task returns None."""
        result = engine.get_task("non-existent")
        assert result is None

    def test_update_task(self, engine, sample_tasks):
        """Task can be updated."""
        task = engine.update_task(
            sample_tasks[0].id,
            name="Updated Task",
            priority=Priority.CRITICAL,
        )
        assert task.name == "Updated Task"
        assert task.priority == Priority.CRITICAL

    def test_update_task_not_found(self, engine):
        """Updating non-existent task returns None."""
        result = engine.update_task("non-existent", name="New Name")
        assert result is None

    def test_delete_task(self, engine, sample_tasks):
        """Task can be deleted."""
        task_id = sample_tasks[0].id
        result = engine.delete_task(task_id)
        assert result is True
        assert engine.get_task(task_id) is None

    def test_delete_task_not_found(self, engine):
        """Deleting non-existent task returns False."""
        result = engine.delete_task("non-existent")
        assert result is False

    def test_list_tasks(self, engine, sample_project, sample_tasks):
        """All tasks can be listed."""
        tasks = engine.list_tasks()
        assert len(tasks) == 3

    def test_list_tasks_by_project(self, engine, sample_project, sample_tasks):
        """Tasks can be filtered by project."""
        tasks = engine.list_tasks(project_id=sample_project.id)
        assert len(tasks) == 3

    def test_list_tasks_by_status(self, engine, sample_tasks):
        """Tasks can be filtered by status."""
        engine.complete_task(sample_tasks[0].id)
        completed = engine.list_tasks(status=TaskStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].name == "Task 1"

    def test_list_tasks_by_assignee(self, engine, sample_tasks):
        """Tasks can be filtered by assignee."""
        engine.update_task(sample_tasks[0].id, assigned_to="user-1")
        assigned = engine.list_tasks(assigned_to="user-1")
        assert len(assigned) == 1

    def test_add_task_dependency(self, engine, sample_tasks):
        """Dependency can be added to a task."""
        result = engine.add_task_dependency(sample_tasks[2].id, sample_tasks[0].id)
        assert result is True
        task = engine.get_task(sample_tasks[2].id)
        assert sample_tasks[0].id in task.dependencies

    def test_remove_task_dependency(self, engine, sample_tasks):
        """Dependency can be removed from a task."""
        engine.add_task_dependency(sample_tasks[2].id, sample_tasks[0].id)
        result = engine.remove_task_dependency(sample_tasks[2].id, sample_tasks[0].id)
        assert result is True
        task = engine.get_task(sample_tasks[2].id)
        assert sample_tasks[0].id not in task.dependencies

    def test_start_task(self, engine, sample_tasks):
        """Task can be started."""
        task = engine.start_task(sample_tasks[0].id)
        assert task.status == TaskStatus.IN_PROGRESS

    def test_start_blocked_task(self, engine, sample_tasks):
        """Blocked task cannot be started."""
        with pytest.raises(ValueError, match="blocked"):
            engine.start_task(sample_tasks[1].id)

    def test_complete_task(self, engine, sample_tasks):
        """Task can be completed."""
        task = engine.complete_task(sample_tasks[0].id)
        assert task.status == TaskStatus.COMPLETED
        assert task.completion_percentage == 100.0

    def test_block_task(self, engine, sample_tasks):
        """Task can be blocked."""
        task = engine.block_task(sample_tasks[0].id)
        assert task.status == TaskStatus.BLOCKED

    def test_set_task_progress(self, engine, sample_tasks):
        """Task progress can be set."""
        task = engine.set_task_progress(sample_tasks[0].id, 50.0)
        assert task.completion_percentage == 50.0
        assert task.status == TaskStatus.IN_PROGRESS

    def test_set_task_progress_complete(self, engine, sample_tasks):
        """Setting progress to 100% completes the task."""
        task = engine.set_task_progress(sample_tasks[0].id, 100.0)
        assert task.status == TaskStatus.COMPLETED

    def test_set_task_progress_clamped(self, engine, sample_tasks):
        """Task progress is clamped to 0-100."""
        task = engine.set_task_progress(sample_tasks[0].id, 150.0)
        assert task.completion_percentage == 100.0
        task = engine.set_task_progress(sample_tasks[0].id, -10.0)
        assert task.completion_percentage == 0.0

    def test_task_is_overdue(self, engine, sample_project):
        """Task is overdue when end date has passed."""
        task = engine.create_task(
            project_id=sample_project.id,
            name="Overdue Task",
            end_date=date(2020, 1, 1),
        )
        assert task.is_overdue() is True

    def test_task_is_blocked(self, engine, sample_tasks):
        """Task is blocked when dependencies are incomplete."""
        task2 = engine.get_task(sample_tasks[1].id)
        tasks_dict = {t.id: t for t in sample_tasks}
        assert task2.is_blocked(tasks_dict) is True

    def test_task_can_start(self, engine, sample_tasks):
        """Task can start when dependencies are completed."""
        engine.complete_task(sample_tasks[0].id)
        task2 = engine.get_task(sample_tasks[1].id)
        tasks_dict = {t.id: t for t in sample_tasks}
        assert task2.can_start(tasks_dict) is True

    def test_task_remaining_days(self, engine, sample_project):
        """Task remaining days can be calculated."""
        task = engine.create_task(
            project_id=sample_project.id,
            name="Future Task",
            end_date=date.today() + timedelta(days=10),
        )
        assert task.remaining_days() == 10

    def test_get_critical_path(self, engine, sample_project, sample_tasks):
        """Critical path can be calculated."""
        path = engine.get_critical_path(sample_project.id)
        assert len(path) == 3
        assert path[0] == sample_tasks[0].id
        assert path[1] == sample_tasks[1].id
        assert path[2] == sample_tasks[2].id

    def test_get_critical_path_empty(self, engine, sample_project):
        """Critical path is empty for project with no tasks."""
        path = engine.get_critical_path(sample_project.id)
        assert path == []


# ── Gantt Chart Tests ─────────────────────────────────────────────


class TestGanttChart:
    """Test Gantt chart generation and management."""

    def test_generate_gantt_chart(self, engine, sample_project, sample_tasks):
        """Gantt chart can be generated for a project."""
        chart = engine.generate_gantt_chart(sample_project.id)
        assert chart.id is not None
        assert chart.project_id == sample_project.id
        assert len(chart.tasks) == 3
        assert chart.start_date is not None
        assert chart.end_date is not None

    def test_generate_gantt_chart_custom_name(self, engine, sample_project):
        """Gantt chart can have a custom name."""
        chart = engine.generate_gantt_chart(sample_project.id, name="Custom Chart")
        assert chart.name == "Custom Chart"

    def test_generate_gantt_chart_invalid_project(self, engine):
        """Generating chart for non-existent project raises error."""
        with pytest.raises(ValueError, match="Project not found"):
            engine.generate_gantt_chart("invalid")

    def test_get_gantt_chart(self, engine, sample_project):
        """Gantt chart can be retrieved by ID."""
        chart = engine.generate_gantt_chart(sample_project.id)
        retrieved = engine.get_gantt_chart(chart.id)
        assert retrieved is not None
        assert retrieved.id == chart.id

    def test_get_gantt_chart_not_found(self, engine):
        """Getting non-existent chart returns None."""
        result = engine.get_gantt_chart("non-existent")
        assert result is None

    def test_update_gantt_task(self, engine, sample_project, sample_tasks):
        """Gantt task can be updated."""
        chart = engine.generate_gantt_chart(sample_project.id)
        updated = engine.update_gantt_task(
            chart.id, sample_tasks[0].id, progress_percentage=50.0
        )
        assert updated is not None
        assert updated.progress_percentage == 50.0

    def test_update_gantt_task_not_found(self, engine, sample_project):
        """Updating non-existent Gantt task returns None."""
        chart = engine.generate_gantt_chart(sample_project.id)
        result = engine.update_gantt_task(chart.id, "invalid", progress_percentage=50.0)
        assert result is None

    def test_gantt_chart_summary(self, engine, sample_project, sample_tasks):
        """Gantt chart summary can be generated."""
        chart = engine.generate_gantt_chart(sample_project.id)
        summary = engine.gantt_chart_summary(chart.id)
        assert summary["chart_id"] == chart.id
        assert summary["total_tasks"] == 3
        assert summary["completed"] == 0
        assert summary["in_progress"] == 0
        assert summary["not_started"] == 3

    def test_gantt_chart_summary_not_found(self, engine):
        """Summary for non-existent chart returns empty dict."""
        summary = engine.gantt_chart_summary("non-existent")
        assert summary == {}

    def test_gantt_chart_total_duration(self, engine, sample_project, sample_tasks):
        """Gantt chart total duration is calculated."""
        chart = engine.generate_gantt_chart(sample_project.id)
        assert chart.total_duration_days() > 0

    def test_gantt_chart_tasks_by_date(self, engine, sample_project, sample_tasks):
        """Gantt tasks can be grouped by date."""
        chart = engine.generate_gantt_chart(sample_project.id)
        by_date = chart.tasks_by_date()
        assert len(by_date) > 0

    def test_gantt_chart_critical_path(self, engine, sample_project, sample_tasks):
        """Gantt chart critical path can be calculated."""
        chart = engine.generate_gantt_chart(sample_project.id)
        task_deps = {t.task_id: t.dependencies for t in chart.tasks}
        path = chart.critical_path(task_deps)
        assert len(path) == 3

    def test_gantt_task_creation(self):
        """GanttTask can be created."""
        task = GanttTask(
            task_id="gt-1",
            name="Gantt Task",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 15),
            duration_days=14,
            progress_percentage=0.0,
        )
        assert task.task_id == "gt-1"
        assert task.name == "Gantt Task"
        assert task.duration_days == 14

    def test_gantt_chart_creation(self):
        """GanttChart can be created."""
        chart = GanttChart(
            id="gc-1",
            project_id="p-1",
            name="Test Chart",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        assert chart.id == "gc-1"
        assert chart.total_duration_days() == 89


# ── Resource Allocation Tests ─────────────────────────────────────


class TestResourceAllocation:
    """Test resource allocation."""

    def test_create_resource(self, engine):
        """Resource can be created."""
        resource = engine.create_resource(
            name="Developer",
            type=ResourceType.HUMAN,
            capacity=160.0,
            cost_rate=75.0,
        )
        assert resource.id is not None
        assert resource.name == "Developer"
        assert resource.type == ResourceType.HUMAN
        assert resource.capacity == 160.0
        assert resource.cost_rate == 75.0

    def test_get_resource(self, engine, sample_resources):
        """Resource can be retrieved by ID."""
        resource = engine.get_resource(sample_resources[0].id)
        assert resource is not None
        assert resource.name == "Developer 1"

    def test_get_resource_not_found(self, engine):
        """Getting non-existent resource returns None."""
        result = engine.get_resource("non-existent")
        assert result is None

    def test_update_resource(self, engine, sample_resources):
        """Resource can be updated."""
        resource = engine.update_resource(
            sample_resources[0].id, capacity=200.0, cost_rate=85.0
        )
        assert resource.capacity == 200.0
        assert resource.cost_rate == 85.0

    def test_update_resource_not_found(self, engine):
        """Updating non-existent resource returns None."""
        result = engine.update_resource("non-existent", name="New Name")
        assert result is None

    def test_delete_resource(self, engine, sample_resources):
        """Resource can be deleted."""
        result = engine.delete_resource(sample_resources[0].id)
        assert result is True
        assert engine.get_resource(sample_resources[0].id) is None

    def test_delete_resource_not_found(self, engine):
        """Deleting non-existent resource returns False."""
        result = engine.delete_resource("non-existent")
        assert result is False

    def test_list_resources(self, engine, sample_resources):
        """All resources can be listed."""
        resources = engine.list_resources()
        assert len(resources) == 3

    def test_list_resources_by_type(self, engine, sample_resources):
        """Resources can be filtered by type."""
        humans = engine.list_resources(type=ResourceType.HUMAN)
        assert len(humans) == 2
        equipment = engine.list_resources(type=ResourceType.EQUIPMENT)
        assert len(equipment) == 1

    def test_assign_resource_to_task(self, engine, sample_project, sample_tasks, sample_resources):
        """Resource can be assigned to a task."""
        result = engine.assign_resource_to_task(
            sample_resources[0].id, sample_tasks[0].id
        )
        assert result is True
        task = engine.get_task(sample_tasks[0].id)
        assert task.assigned_to == sample_resources[0].id
        resource = engine.get_resource(sample_resources[0].id)
        assert sample_tasks[0].id in resource.assigned_tasks

    def test_unassign_resource_from_task(self, engine, sample_project, sample_tasks, sample_resources):
        """Resource can be unassigned from a task."""
        engine.assign_resource_to_task(sample_resources[0].id, sample_tasks[0].id)
        result = engine.unassign_resource_from_task(
            sample_resources[0].id, sample_tasks[0].id
        )
        assert result is True
        task = engine.get_task(sample_tasks[0].id)
        assert task.assigned_to is None

    def test_get_resource_allocation(self, engine, sample_project, sample_tasks, sample_resources):
        """Resource allocation details can be retrieved."""
        engine.assign_resource_to_task(sample_resources[0].id, sample_tasks[0].id)
        allocation = engine.get_resource_allocation(sample_resources[0].id)
        assert allocation["resource_id"] == sample_resources[0].id
        assert allocation["assigned_tasks"] == 1
        assert allocation["allocated_hours"] == 14 * 8  # duration_days * 8

    def test_get_resource_allocation_not_found(self, engine):
        """Allocation for non-existent resource returns empty dict."""
        allocation = engine.get_resource_allocation("non-existent")
        assert allocation == {}

    def test_get_project_resource_allocation(self, engine, sample_project, sample_tasks, sample_resources):
        """Project resource allocation can be retrieved."""
        sample_project.resource_ids = [r.id for r in sample_resources]
        engine.assign_resource_to_task(sample_resources[0].id, sample_tasks[0].id)
        allocation = engine.get_project_resource_allocation(sample_project.id)
        assert allocation["project_id"] == sample_project.id
        assert allocation["total_resources"] == 3
        assert len(allocation["allocations"]) == 3

    def test_check_overallocation(self, engine, sample_project, sample_tasks, sample_resources):
        """Overallocated resources can be detected."""
        # Assign all tasks to one resource with small capacity
        sample_resources[0].capacity = 10.0  # Very small capacity
        for task in sample_tasks:
            engine.assign_resource_to_task(sample_resources[0].id, task.id)
        overallocated = engine.check_overallocation()
        assert len(overallocated) == 1
        assert overallocated[0]["name"] == "Developer 1"

    def test_check_no_overallocation(self, engine, sample_project, sample_tasks, sample_resources):
        """No overallocation when resources have sufficient capacity."""
        sample_resources[0].capacity = 1000.0  # Large enough for all tasks
        for task in sample_tasks:
            engine.assign_resource_to_task(sample_resources[0].id, task.id)
        overallocated = engine.check_overallocation()
        assert len(overallocated) == 0

    def test_resource_utilization_percentage(self):
        """Resource utilization percentage is calculated correctly."""
        resource = Resource(
            id="r-1",
            name="Test",
            type=ResourceType.HUMAN,
            capacity=100.0,
        )
        assert resource.utilization_percentage(50.0) == 50.0
        assert resource.utilization_percentage(100.0) == 100.0
        assert resource.utilization_percentage(150.0) == 100.0

    def test_resource_is_overallocated(self):
        """Resource overallocation is detected correctly."""
        resource = Resource(
            id="r-1",
            name="Test",
            type=ResourceType.HUMAN,
            capacity=100.0,
        )
        assert resource.is_overallocated(50.0) is False
        assert resource.is_overallocated(100.0) is False
        assert resource.is_overallocated(150.0) is True


# ── Time Tracking Tests ───────────────────────────────────────────


class TestTimeTracking:
    """Test time tracking."""

    def test_start_time_entry(self, engine, sample_tasks):
        """Time entry can be started."""
        entry = engine.start_time_entry(
            task_id=sample_tasks[0].id,
            user_id="user-1",
            description="Working on task",
        )
        assert entry.id is not None
        assert entry.task_id == sample_tasks[0].id
        assert entry.user_id == "user-1"
        assert entry.is_running() is True
        assert entry.hours == 0.0

    def test_start_time_entry_invalid_task(self, engine):
        """Starting time entry for non-existent task raises error."""
        with pytest.raises(ValueError, match="Task not found"):
            engine.start_time_entry(task_id="invalid", user_id="user-1")

    def test_stop_time_entry(self, engine, sample_tasks):
        """Time entry can be stopped."""
        entry = engine.start_time_entry(
            task_id=sample_tasks[0].id,
            user_id="user-1",
        )
        stopped = engine.stop_time_entry(entry.id)
        assert stopped is not None
        assert stopped.is_running() is False
        assert stopped.hours > 0.0

    def test_stop_time_entry_not_found(self, engine):
        """Stopping non-existent time entry returns None."""
        result = engine.stop_time_entry("non-existent")
        assert result is None

    def test_get_time_entry(self, engine, sample_tasks):
        """Time entry can be retrieved by ID."""
        entry = engine.start_time_entry(
            task_id=sample_tasks[0].id,
            user_id="user-1",
        )
        retrieved = engine.get_time_entry(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id

    def test_get_time_entry_not_found(self, engine):
        """Getting non-existent time entry returns None."""
        result = engine.get_time_entry("non-existent")
        assert result is None

    def test_delete_time_entry(self, engine, sample_tasks):
        """Time entry can be deleted."""
        entry = engine.start_time_entry(
            task_id=sample_tasks[0].id,
            user_id="user-1",
        )
        result = engine.delete_time_entry(entry.id)
        assert result is True
        assert engine.get_time_entry(entry.id) is None

    def test_delete_time_entry_not_found(self, engine):
        """Deleting non-existent time entry returns False."""
        result = engine.delete_time_entry("non-existent")
        assert result is False

    def test_list_time_entries(self, engine, sample_tasks):
        """All time entries can be listed."""
        engine.start_time_entry(task_id=sample_tasks[0].id, user_id="user-1")
        engine.start_time_entry(task_id=sample_tasks[1].id, user_id="user-2")
        entries = engine.list_time_entries()
        assert len(entries) == 2

    def test_list_time_entries_by_task(self, engine, sample_tasks):
        """Time entries can be filtered by task."""
        engine.start_time_entry(task_id=sample_tasks[0].id, user_id="user-1")
        engine.start_time_entry(task_id=sample_tasks[1].id, user_id="user-2")
        entries = engine.list_time_entries(task_id=sample_tasks[0].id)
        assert len(entries) == 1

    def test_list_time_entries_by_user(self, engine, sample_tasks):
        """Time entries can be filtered by user."""
        engine.start_time_entry(task_id=sample_tasks[0].id, user_id="user-1")
        engine.start_time_entry(task_id=sample_tasks[1].id, user_id="user-1")
        engine.start_time_entry(task_id=sample_tasks[2].id, user_id="user-2")
        entries = engine.list_time_entries(user_id="user-1")
        assert len(entries) == 2

    def test_list_time_entries_by_billable(self, engine, sample_tasks):
        """Time entries can be filtered by billable status."""
        engine.start_time_entry(
            task_id=sample_tasks[0].id, user_id="user-1", billable=True
        )
        engine.start_time_entry(
            task_id=sample_tasks[1].id, user_id="user-1", billable=False
        )
        billable = engine.list_time_entries(billable=True)
        assert len(billable) == 1
        non_billable = engine.list_time_entries(billable=False)
        assert len(non_billable) == 1

    def test_get_task_time_summary(self, engine, sample_tasks):
        """Task time summary can be generated."""
        entry = engine.start_time_entry(
            task_id=sample_tasks[0].id,
            user_id="user-1",
        )
        engine.stop_time_entry(entry.id)
        summary = engine.get_task_time_summary(sample_tasks[0].id)
        assert summary["task_id"] == sample_tasks[0].id
        assert summary["total_entries"] == 1
        assert summary["total_hours"] > 0

    def test_get_project_time_summary(self, engine, sample_project, sample_tasks):
        """Project time summary can be generated."""
        entry = engine.start_time_entry(
            task_id=sample_tasks[0].id,
            user_id="user-1",
        )
        engine.stop_time_entry(entry.id)
        summary = engine.get_project_time_summary(sample_project.id)
        assert summary["project_id"] == sample_project.id
        assert summary["total_entries"] == 1
        assert summary["total_hours"] > 0

    def test_get_user_time_summary(self, engine, sample_tasks):
        """User time summary can be generated."""
        entry1 = engine.start_time_entry(
            task_id=sample_tasks[0].id,
            user_id="user-1",
        )
        engine.stop_time_entry(entry1.id)
        entry2 = engine.start_time_entry(
            task_id=sample_tasks[1].id,
            user_id="user-1",
        )
        engine.stop_time_entry(entry2.id)
        summary = engine.get_user_time_summary("user-1")
        assert summary["user_id"] == "user-1"
        assert summary["total_entries"] == 2
        assert summary["tasks_worked"] == 2

    def test_get_running_timers(self, engine, sample_tasks):
        """Running timers can be retrieved."""
        engine.start_time_entry(task_id=sample_tasks[0].id, user_id="user-1")
        engine.start_time_entry(task_id=sample_tasks[1].id, user_id="user-2")
        running = engine.get_running_timers()
        assert len(running) == 2

    def test_time_entry_duration(self):
        """Time entry duration is calculated correctly."""
        start = datetime(2026, 1, 1, 9, 0, 0)
        end = datetime(2026, 1, 1, 17, 0, 0)
        entry = TimeEntry(
            id="te-1",
            task_id="t-1",
            user_id="user-1",
            start_time=start,
            end_time=end,
        )
        duration = entry.duration()
        assert duration == timedelta(hours=8)

    def test_time_entry_is_running(self):
        """Time entry running status is correct."""
        entry = TimeEntry(
            id="te-1",
            task_id="t-1",
            user_id="user-1",
            start_time=datetime.now(),
        )
        assert entry.is_running() is True
        entry.end_time = datetime.now()
        assert entry.is_running() is False


# ── Integration Tests ─────────────────────────────────────────────


class TestProjectManagementIntegration:
    """Integration tests for the full project management workflow."""

    def test_full_project_lifecycle(self, engine):
        """Complete project lifecycle from creation to completion."""
        # Create project
        project = engine.create_project(
            name="Lifecycle Project",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            budget=100000.0,
        )
        assert project.status == ProjectStatus.PLANNING

        # Activate project
        engine.update_project(project.id, status=ProjectStatus.ACTIVE)
        assert engine.get_project(project.id).status == ProjectStatus.ACTIVE

        # Create tasks
        task1 = engine.create_task(
            project_id=project.id,
            name="Design",
            duration_days=10,
            priority=Priority.HIGH,
        )
        task2 = engine.create_task(
            project_id=project.id,
            name="Development",
            duration_days=20,
            dependencies=[task1.id],
            priority=Priority.HIGH,
        )
        task3 = engine.create_task(
            project_id=project.id,
            name="Testing",
            duration_days=10,
            dependencies=[task2.id],
            priority=Priority.MEDIUM,
        )

        # Create resources
        dev = engine.create_resource(
            name="Developer",
            type=ResourceType.HUMAN,
            capacity=160.0,
            cost_rate=75.0,
        )
        tester = engine.create_resource(
            name="Tester",
            type=ResourceType.HUMAN,
            capacity=80.0,
            cost_rate=50.0,
        )

        # Assign resources
        engine.assign_resource_to_task(dev.id, task2.id)
        engine.assign_resource_to_task(tester.id, task3.id)

        # Generate Gantt chart
        chart = engine.generate_gantt_chart(project.id)
        assert len(chart.tasks) == 3

        # Start and complete tasks
        engine.start_task(task1.id)
        engine.complete_task(task1.id)

        engine.start_task(task2.id)
        engine.complete_task(task2.id)

        engine.start_task(task3.id)
        engine.complete_task(task3.id)

        # Track time
        entry1 = engine.start_time_entry(task_id=task1.id, user_id="user-1")
        engine.stop_time_entry(entry1.id)
        entry2 = engine.start_time_entry(task_id=task2.id, user_id="user-2")
        engine.stop_time_entry(entry2.id)

        # Complete project
        engine.update_project(project.id, status=ProjectStatus.COMPLETED)

        # Verify final state
        summary = engine.project_summary(project.id)
        assert summary["completed_tasks"] == 3
        assert summary["progress_percentage"] == 100.0

        report = engine.generate_project_report(project.id)
        assert report["project"]["status"] == "completed"
        assert report["time"]["total_entries"] == 2

    def test_project_report(self, engine, sample_project, sample_tasks, sample_resources):
        """Comprehensive project report can be generated."""
        engine.assign_resource_to_task(sample_resources[0].id, sample_tasks[0].id)
        engine.complete_task(sample_tasks[0].id)

        report = engine.generate_project_report(sample_project.id)
        assert "project" in report
        assert "time" in report
        assert "resources" in report
        assert "tasks_by_status" in report
        assert "tasks_by_priority" in report
        assert "critical_path" in report
        assert report["project"]["completed_tasks"] == 1

    def test_multiple_projects_isolation(self, engine):
        """Multiple projects are isolated from each other."""
        p1 = engine.create_project(name="Project 1")
        p2 = engine.create_project(name="Project 2")

        t1 = engine.create_task(project_id=p1.id, name="Task in P1")
        t2 = engine.create_task(project_id=p2.id, name="Task in P2")

        p1_tasks = engine.get_project_tasks(p1.id)
        p2_tasks = engine.get_project_tasks(p2.id)

        assert len(p1_tasks) == 1
        assert p1_tasks[0].name == "Task in P1"
        assert len(p2_tasks) == 1
        assert p2_tasks[0].name == "Task in P2"


# ── Model Tests ───────────────────────────────────────────────────


class TestModels:
    """Test data model creation and properties."""

    def test_project_model(self):
        """Project model can be created."""
        project = Project(
            id="p-1",
            name="Test Project",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        assert project.id == "p-1"
        assert project.status == ProjectStatus.PLANNING
        assert project.duration_days() == 89

    def test_task_model(self):
        """Task model can be created."""
        task = Task(
            id="t-1",
            project_id="p-1",
            name="Test Task",
            duration_days=5,
        )
        assert task.id == "t-1"
        assert task.status == TaskStatus.NOT_STARTED
        assert task.completion_percentage == 0.0

    def test_resource_model(self):
        """Resource model can be created."""
        resource = Resource(
            id="r-1",
            name="Test Resource",
            type=ResourceType.HUMAN,
            capacity=100.0,
        )
        assert resource.id == "r-1"
        assert resource.type == ResourceType.HUMAN

    def test_time_entry_model(self):
        """TimeEntry model can be created."""
        entry = TimeEntry(
            id="te-1",
            task_id="t-1",
            user_id="user-1",
            start_time=datetime(2026, 1, 1, 9, 0, 0),
        )
        assert entry.id == "te-1"
        assert entry.is_running() is True

    def test_gantt_task_model(self):
        """GanttTask model can be created."""
        task = GanttTask(
            task_id="gt-1",
            name="Gantt Task",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 15),
            duration_days=14,
            progress_percentage=0.0,
        )
        assert task.task_id == "gt-1"
        assert task.duration_days == 14

    def test_gantt_chart_model(self):
        """GanttChart model can be created."""
        chart = GanttChart(
            id="gc-1",
            project_id="p-1",
            name="Test Chart",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        assert chart.id == "gc-1"
        assert chart.total_duration_days() == 89

    def test_priority_enum(self):
        """Priority enum has correct values."""
        assert Priority.LOW.value == 1
        assert Priority.MEDIUM.value == 2
        assert Priority.HIGH.value == 3
        assert Priority.CRITICAL.value == 4

    def test_project_status_enum(self):
        """ProjectStatus enum has correct values."""
        assert ProjectStatus.PLANNING.value == "planning"
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.ON_HOLD.value == "on_hold"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.CANCELLED.value == "cancelled"

    def test_task_status_enum(self):
        """TaskStatus enum has correct values."""
        assert TaskStatus.NOT_STARTED.value == "not_started"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_resource_type_enum(self):
        """ResourceType enum has correct values."""
        assert ResourceType.HUMAN.value == "human"
        assert ResourceType.EQUIPMENT.value == "equipment"
        assert ResourceType.MATERIAL.value == "material"
        assert ResourceType.BUDGET.value == "budget"
