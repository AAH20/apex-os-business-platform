"""Report scheduler — schedule recurring and one-time report generation."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable


class ScheduleFrequency(str, Enum):
    """Schedule frequency options."""

    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"


class ScheduleStatus(str, Enum):
    """Schedule status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ScheduleConfig:
    """Configuration for a report schedule."""

    name: str
    frequency: ScheduleFrequency
    report_definition_id: str
    cron_expression: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    max_runs: int | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: ScheduleStatus = ScheduleStatus.PENDING
    last_run: datetime | None = None
    next_run: datetime | None = None
    run_count: int = 0


@dataclass
class ScheduleRun:
    """Record of a single schedule execution."""

    schedule_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: ScheduleStatus = ScheduleStatus.RUNNING
    result_id: str | None = None
    error: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class ReportScheduler:
    """Schedules and executes report generation."""

    def __init__(self) -> None:
        self._schedules: dict[str, ScheduleConfig] = {}
        self._runs: dict[str, list[ScheduleRun]] = {}
        self._callbacks: dict[str, Callable] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def create_schedule(self, config: ScheduleConfig) -> ScheduleConfig:
        """Create a new schedule."""
        if config.frequency == ScheduleFrequency.CRON and not config.cron_expression:
            raise ValueError("Cron expression required for CRON frequency")
        if config.start_time is None:
            config.start_time = datetime.utcnow()
        config.next_run = self._compute_next_run(config)
        with self._lock:
            self._schedules[config.id] = config
            self._runs[config.id] = []
        return config

    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a schedule."""
        with self._lock:
            if schedule_id not in self._schedules:
                return False
            self._schedules[schedule_id].status = ScheduleStatus.CANCELLED
            return True

    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule."""
        with self._lock:
            if schedule_id not in self._schedules:
                return False
            self._schedules[schedule_id].status = ScheduleStatus.PAUSED
            return True

    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule."""
        with self._lock:
            if schedule_id not in self._schedules:
                return False
            sched = self._schedules[schedule_id]
            sched.status = ScheduleStatus.PENDING
            sched.next_run = self._compute_next_run(sched)
            return True

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule permanently."""
        with self._lock:
            if schedule_id not in self._schedules:
                return False
            del self._schedules[schedule_id]
            self._runs.pop(schedule_id, None)
            return True

    def get_schedule(self, schedule_id: str) -> ScheduleConfig | None:
        """Get a schedule by ID."""
        return self._schedules.get(schedule_id)

    def list_schedules(
        self, status: ScheduleStatus | None = None
    ) -> list[ScheduleConfig]:
        """List all schedules, optionally filtered by status."""
        schedules = list(self._schedules.values())
        if status is not None:
            schedules = [s for s in schedules if s.status == status]
        return schedules

    def register_callback(
        self, schedule_id: str, callback: Callable[[ScheduleRun], None]
    ) -> None:
        """Register a callback for schedule completion."""
        self._callbacks[schedule_id] = callback

    def execute_now(self, schedule_id: str) -> ScheduleRun | None:
        """Execute a schedule immediately."""
        with self._lock:
            sched = self._schedules.get(schedule_id)
            if sched is None:
                return None
            if sched.status == ScheduleStatus.CANCELLED:
                return None

        run = ScheduleRun(
            schedule_id=schedule_id,
            started_at=datetime.utcnow(),
        )
        with self._lock:
            self._runs.setdefault(schedule_id, []).append(run)

        try:
            sched.status = ScheduleStatus.RUNNING
            sched.last_run = datetime.utcnow()
            sched.run_count += 1
            run.status = ScheduleStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            sched.status = ScheduleStatus.PENDING
            sched.next_run = self._compute_next_run(sched)
        except Exception as exc:
            run.status = ScheduleStatus.FAILED
            run.error = str(exc)
            run.completed_at = datetime.utcnow()
            sched.status = ScheduleStatus.FAILED

        callback = self._callbacks.get(schedule_id)
        if callback:
            callback(run)

        return run

    def get_runs(self, schedule_id: str) -> list[ScheduleRun]:
        """Get run history for a schedule."""
        return list(self._runs.get(schedule_id, []))

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler background thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _run_loop(self) -> None:
        """Background loop that checks for due schedules."""
        while self._running:
            now = datetime.utcnow()
            with self._lock:
                due = [
                    s
                    for s in self._schedules.values()
                    if s.status == ScheduleStatus.PENDING
                    and s.next_run is not None
                    and s.next_run <= now
                    and (
                        s.max_runs is None or s.run_count < s.max_runs
                    )
                    and (s.end_time is None or now < s.end_time)
                ]
            for sched in due:
                self.execute_now(sched.id)
            time.sleep(1)

    def _compute_next_run(self, sched: ScheduleConfig) -> datetime | None:
        """Compute the next run time for a schedule."""
        base = sched.last_run or sched.start_time or datetime.utcnow()
        freq = sched.frequency
        if freq == ScheduleFrequency.ONCE:
            return None
        if freq == ScheduleFrequency.HOURLY:
            return base + timedelta(hours=1)
        if freq == ScheduleFrequency.DAILY:
            return base + timedelta(days=1)
        if freq == ScheduleFrequency.WEEKLY:
            return base + timedelta(weeks=1)
        if freq == ScheduleFrequency.MONTHLY:
            # Approximate: add 30 days
            return base + timedelta(days=30)
        if freq == ScheduleFrequency.CRON:
            # Simplified: treat cron as daily for this implementation
            return base + timedelta(days=1)
        return None
