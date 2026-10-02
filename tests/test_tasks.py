"""Tests for the task management system."""

import pytest
from datetime import datetime, timedelta

from apex_os_bp.tasks.models import Task, TaskStatus, TaskPriority, TaskEvent
from apex_os_bp.tasks.creation import TaskCreator
from apex_os_bp.tasks.assignment import TaskAssigner
from apex_os_bp.tasks.scheduling import TaskScheduler
from apex_os_bp.tasks.tracking import TaskTracker
from apex_os_bp.tasks.notifications import NotificationService
from apex_os_bp.tasks.manager import TaskManager


# ── Models ──────────────────────────────────────────────────────────────────

class TestTaskModel:
    def test_task_defaults(self):
        task = Task(title="Test")
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.progress == 0
        assert task.assignee is None
        assert task.tags == []
        assert task.events == []

    def test_task_to_dict(self):
        task = Task(title="Test", description="Desc")
        d = task.to_dict()
        assert d["title"] == "Test"
        assert d["description"] == "Desc"
        assert d["status"] == "pending"
        assert d["priority"] == "medium"
        assert "task_id" in d
        assert "created_at" in d

    def test_task_event(self):
        event = TaskEvent(task_id="t1", event_type="created")
        assert event.task_id == "t1"
        assert event.event_type == "created"
        assert event.details == {}


# ── Creation ────────────────────────────────────────────────────────────────

class TestTaskCreator:
    def test_create_task(self):
        creator = TaskCreator()
        task = creator.create_task("My Task", "Description")
        assert task.title == "My Task"
        assert task.description == "Description"
        assert task.status == TaskStatus.PENDING
        assert len(task.events) == 1
        assert task.events[0].event_type == "created"

    def test_create_task_with_priority(self):
        creator = TaskCreator()
        task = creator.create_task("Urgent", priority=TaskPriority.HIGH)
        assert task.priority == TaskPriority.HIGH

    def test_create_task_with_tags(self):
        creator = TaskCreator()
        task = creator.create_task("Tagged", tags=["work", "urgent"])
        assert task.tags == ["work", "urgent"]

    def test_create_task_empty_title_raises(self):
        creator = TaskCreator()
        with pytest.raises(ValueError):
            creator.create_task("")

    def test_create_task_whitespace_title_raises(self):
        creator = TaskCreator()
        with pytest.raises(ValueError):
            creator.create_task("   ")

    def test_create_task_with_due_date(self):
        creator = TaskCreator()
        due = datetime.utcnow() + timedelta(days=1)
        task = creator.create_task("Due", due_date=due)
        assert task.due_date == due


# ── Assignment ──────────────────────────────────────────────────────────────

class TestTaskAssigner:
    def test_assign(self):
        assigner = TaskAssigner()
        task = Task(title="Test")
        result = assigner.assign(task, "alice")
        assert result.assignee == "alice"
        assert result.events[-1].event_type == "assigned"

    def test_assign_empty_raises(self):
        assigner = TaskAssigner()
        task = Task(title="Test")
        with pytest.raises(ValueError):
            assigner.assign(task, "")

    def test_unassign(self):
        assigner = TaskAssigner()
        task = Task(title="Test", assignee="alice")
        result = assigner.unassign(task)
        assert result.assignee is None
        assert result.events[-1].event_type == "unassigned"

    def test_reassign(self):
        assigner = TaskAssigner()
        task = Task(title="Test", assignee="alice")
        result = assigner.reassign(task, "bob")
        assert result.assignee == "bob"
        assert result.events[-1].event_type == "assigned"
        assert result.events[-1].details["old_assignee"] == "alice"


# ── Scheduling ──────────────────────────────────────────────────────────────

class TestTaskScheduler:
    def test_schedule(self):
        scheduler = TaskScheduler()
        task = Task(title="Test")
        future = datetime.utcnow() + timedelta(hours=2)
        result = scheduler.schedule(task, future)
        assert result.scheduled_at == future
        assert result.events[-1].event_type == "scheduled"

    def test_schedule_past_raises(self):
        scheduler = TaskScheduler()
        task = Task(title="Test")
        past = datetime.utcnow() - timedelta(hours=1)
        with pytest.raises(ValueError):
            scheduler.schedule(task, past)

    def test_reschedule(self):
        scheduler = TaskScheduler()
        task = Task(title="Test")
        future1 = datetime.utcnow() + timedelta(hours=2)
        future2 = datetime.utcnow() + timedelta(hours=4)
        scheduler.schedule(task, future1)
        result = scheduler.reschedule(task, future2)
        assert result.scheduled_at == future2

    def test_set_due_date(self):
        scheduler = TaskScheduler()
        task = Task(title="Test")
        due = datetime.utcnow() + timedelta(days=3)
        result = scheduler.set_due_date(task, due)
        assert result.due_date == due
        assert result.events[-1].event_type == "due_date_set"

    def test_is_overdue_false_when_no_due_date(self):
        scheduler = TaskScheduler()
        task = Task(title="Test")
        assert scheduler.is_overdue(task) is False

    def test_is_overdue_true(self):
        scheduler = TaskScheduler()
        task = Task(title="Test", due_date=datetime.utcnow() - timedelta(hours=1))
        assert scheduler.is_overdue(task) is True

    def test_is_overdue_false_when_completed(self):
        scheduler = TaskScheduler()
        task = Task(title="Test", due_date=datetime.utcnow() - timedelta(hours=1), status=TaskStatus.COMPLETED)
        assert scheduler.is_overdue(task) is False

    def test_is_due_soon_true(self):
        scheduler = TaskScheduler()
        task = Task(title="Test", due_date=datetime.utcnow() + timedelta(hours=12))
        assert scheduler.is_due_soon(task, within_hours=24) is True

    def test_is_due_soon_false(self):
        scheduler = TaskScheduler()
        task = Task(title="Test", due_date=datetime.utcnow() + timedelta(hours=48))
        assert scheduler.is_due_soon(task, within_hours=24) is False


# ── Tracking ────────────────────────────────────────────────────────────────

class TestTaskTracker:
    def test_start(self):
        tracker = TaskTracker()
        task = Task(title="Test")
        result = tracker.start(task)
        assert result.status == TaskStatus.IN_PROGRESS
        assert result.events[-1].event_type == "status_changed"

    def test_complete(self):
        tracker = TaskTracker()
        task = Task(title="Test")
        result = tracker.complete(task)
        assert result.status == TaskStatus.COMPLETED
        assert result.progress == 100
        assert result.completed_at is not None
        assert result.events[-1].event_type == "completed"

    def test_cancel(self):
        tracker = TaskTracker()
        task = Task(title="Test")
        result = tracker.cancel(task, reason="No longer needed")
        assert result.status == TaskStatus.CANCELLED
        assert result.events[-1].event_type == "cancelled"
        assert result.events[-1].details["reason"] == "No longer needed"

    def test_update_progress(self):
        tracker = TaskTracker()
        task = Task(title="Test")
        result = tracker.update_progress(task, 50)
        assert result.progress == 50
        assert result.events[-1].event_type == "progress_updated"

    def test_update_progress_invalid_raises(self):
        tracker = TaskTracker()
        task = Task(title="Test")
        with pytest.raises(ValueError):
            tracker.update_progress(task, 101)
        with pytest.raises(ValueError):
            tracker.update_progress(task, -1)

    def test_update_progress_100_completes_task(self):
        tracker = TaskTracker()
        task = Task(title="Test")
        result = tracker.update_progress(task, 100)
        assert result.status == TaskStatus.COMPLETED

    def test_update_progress_nonzero_starts_task(self):
        tracker = TaskTracker()
        task = Task(title="Test")
        result = tracker.update_progress(task, 10)
        assert result.status == TaskStatus.IN_PROGRESS

    def test_get_progress(self):
        tracker = TaskTracker()
        task = Task(title="Test", progress=75)
        assert tracker.get_progress(task) == 75

    def test_get_status(self):
        tracker = TaskTracker()
        task = Task(title="Test", status=TaskStatus.IN_PROGRESS)
        assert tracker.get_status(task) == TaskStatus.IN_PROGRESS

    def test_get_completion_time(self):
        tracker = TaskTracker()
        task = Task(title="Test")
        assert tracker.get_completion_time(task) is None
        tracker.complete(task)
        assert tracker.get_completion_time(task) is not None


# ── Notifications ───────────────────────────────────────────────────────────

class TestNotificationService:
    def test_notify_creates_notification(self):
        service = NotificationService()
        task = Task(title="Test")
        event = TaskEvent(task_id=task.task_id, event_type="created")
        notification = service.notify(task, event)
        assert notification["task_id"] == task.task_id
        assert notification["event_type"] == "created"
        assert notification["read"] is False
        assert "message" in notification

    def test_register_handler_called(self):
        service = NotificationService()
        received = []
        service.register_handler(lambda n: received.append(n))
        task = Task(title="Test")
        event = TaskEvent(task_id=task.task_id, event_type="created")
        service.notify(task, event)
        assert len(received) == 1

    def test_get_notifications(self):
        service = NotificationService()
        task = Task(title="Test")
        event = TaskEvent(task_id=task.task_id, event_type="created")
        service.notify(task, event)
        service.notify(task, event)
        assert len(service.get_notifications()) == 2

    def test_get_unread_notifications(self):
        service = NotificationService()
        task = Task(title="Test")
        event = TaskEvent(task_id=task.task_id, event_type="created")
        service.notify(task, event)
        service.notify(task, event)
        service.mark_read(1)
        unread = service.get_notifications(unread_only=True)
        assert len(unread) == 1

    def test_mark_read(self):
        service = NotificationService()
        task = Task(title="Test")
        event = TaskEvent(task_id=task.task_id, event_type="created")
        service.notify(task, event)
        assert service.mark_read(1) is True
        assert service.get_notifications()[0]["read"] is True

    def test_mark_read_invalid_id(self):
        service = NotificationService()
        assert service.mark_read(999) is False

    def test_clear(self):
        service = NotificationService()
        task = Task(title="Test")
        event = TaskEvent(task_id=task.task_id, event_type="created")
        service.notify(task, event)
        service.clear()
        assert len(service.get_notifications()) == 0

    def test_message_format_created(self):
        service = NotificationService()
        task = Task(title="My Task")
        event = TaskEvent(task_id=task.task_id, event_type="created")
        notification = service.notify(task, event)
        assert "My Task" in notification["message"]
        assert "created" in notification["message"]

    def test_message_format_assigned(self):
        service = NotificationService()
        task = Task(title="My Task", assignee="alice")
        event = TaskEvent(task_id=task.task_id, event_type="assigned")
        notification = service.notify(task, event)
        assert "alice" in notification["message"]


# ── Manager ─────────────────────────────────────────────────────────────────

class TestTaskManager:
    def test_create_and_get(self):
        mgr = TaskManager()
        task = mgr.create_task("Test Task")
        assert task.title == "Test Task"
        retrieved = mgr.get_task(task.task_id)
        assert retrieved is not None
        assert retrieved.title == "Test Task"

    def test_list_tasks(self):
        mgr = TaskManager()
        mgr.create_task("Task 1")
        mgr.create_task("Task 2")
        assert len(mgr.list_tasks()) == 2

    def test_list_tasks_filtered_by_status(self):
        mgr = TaskManager()
        t1 = mgr.create_task("Task 1")
        t2 = mgr.create_task("Task 2")
        mgr.start_task(t1.task_id)
        pending = mgr.list_tasks(status=TaskStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].task_id == t2.task_id

    def test_list_tasks_filtered_by_assignee(self):
        mgr = TaskManager()
        t1 = mgr.create_task("Task 1")
        t2 = mgr.create_task("Task 2")
        mgr.assign_task(t1.task_id, "alice")
        alice_tasks = mgr.list_tasks(assignee="alice")
        assert len(alice_tasks) == 1
        assert alice_tasks[0].task_id == t1.task_id

    def test_assign_task(self):
        mgr = TaskManager()
        task = mgr.create_task("Test")
        result = mgr.assign_task(task.task_id, "bob")
        assert result is not None
        assert result.assignee == "bob"

    def test_assign_nonexistent_task(self):
        mgr = TaskManager()
        assert mgr.assign_task("nonexistent", "bob") is None

    def test_schedule_task(self):
        mgr = TaskManager()
        task = mgr.create_task("Test")
        future = datetime.utcnow() + timedelta(hours=2)
        result = mgr.schedule_task(task.task_id, future)
        assert result is not None
        assert result.scheduled_at == future

    def test_start_task(self):
        mgr = TaskManager()
        task = mgr.create_task("Test")
        result = mgr.start_task(task.task_id)
        assert result is not None
        assert result.status == TaskStatus.IN_PROGRESS

    def test_complete_task(self):
        mgr = TaskManager()
        task = mgr.create_task("Test")
        result = mgr.complete_task(task.task_id)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED

    def test_update_progress(self):
        mgr = TaskManager()
        task = mgr.create_task("Test")
        result = mgr.update_progress(task.task_id, 50)
        assert result is not None
        assert result.progress == 50

    def test_delete_task(self):
        mgr = TaskManager()
        task = mgr.create_task("Test")
        assert mgr.delete_task(task.task_id) is True
        assert mgr.get_task(task.task_id) is None

    def test_delete_nonexistent_task(self):
        mgr = TaskManager()
        assert mgr.delete_task("nonexistent") is False

    def test_get_overdue_tasks(self):
        mgr = TaskManager()
        overdue = mgr.create_task("Overdue", due_date=datetime.utcnow() - timedelta(hours=1))
        not_overdue = mgr.create_task("Not Overdue", due_date=datetime.utcnow() + timedelta(hours=1))
        overdue_tasks = mgr.get_overdue_tasks()
        assert len(overdue_tasks) == 1
        assert overdue_tasks[0].task_id == overdue.task_id

    def test_get_tasks_due_soon(self):
        mgr = TaskManager()
        soon = mgr.create_task("Soon", due_date=datetime.utcnow() + timedelta(hours=12))
        later = mgr.create_task("Later", due_date=datetime.utcnow() + timedelta(hours=48))
        due_soon = mgr.get_tasks_due_soon(within_hours=24)
        assert len(due_soon) == 1
        assert due_soon[0].task_id == soon.task_id

    def test_notifications_sent_on_create(self):
        mgr = TaskManager()
        task = mgr.create_task("Test")
        notifications = mgr.notifications.get_notifications()
        assert len(notifications) >= 1
        assert notifications[0]["task_id"] == task.task_id

    def test_notifications_sent_on_assign(self):
        mgr = TaskManager()
        task = mgr.create_task("Test")
        mgr.notifications.clear()
        mgr.assign_task(task.task_id, "alice")
        notifications = mgr.notifications.get_notifications()
        assert len(notifications) == 1
        assert notifications[0]["event_type"] == "assigned"

    def test_full_lifecycle(self):
        mgr = TaskManager()
        task = mgr.create_task("Full Lifecycle", priority=TaskPriority.HIGH)
        mgr.assign_task(task.task_id, "alice")
        mgr.start_task(task.task_id)
        mgr.update_progress(task.task_id, 50)
        mgr.complete_task(task.task_id)

        final = mgr.get_task(task.task_id)
        assert final.status == TaskStatus.COMPLETED
        assert final.progress == 100
        assert final.assignee == "alice"
        assert final.completed_at is not None
