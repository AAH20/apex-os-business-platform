"""Advanced Continuous BI module for APEX-OS Business Platform.

Provides real-time dashboard rendering, threshold-based alerting,
data freshness monitoring, scheduled report delivery, and
self-service analytics capabilities.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Protocol


# ─── Exceptions ───────────────────────────────────────────────────────────────

class ContinuousBIError(Exception):
    """Base exception for ContinuousBI operations."""


class DashboardNotFoundError(ContinuousBIError):
    """Raised when a requested dashboard does not exist."""


class AlertRuleError(ContinuousBIError):
    """Raised when alert rule configuration is invalid."""


class ReportScheduleError(ContinuousBIError):
    """Raised when report scheduling fails."""


class DataFreshnessError(ContinuousBIError):
    """Raised when data freshness check fails."""


# ─── Enums ────────────────────────────────────────────────────────────────────

class AlertSeverity(Enum):
    """Severity levels for alert notifications."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DeliveryChannel(Enum):
    """Supported delivery channels for reports."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"


class FreshnessStatus(Enum):
    """Data freshness status indicators."""
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class MetricValue:
    """Represents a single metric data point."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Defines an alert rule with threshold conditions."""
    name: str
    metric: str
    threshold: float
    operator: str  # 'gt', 'lt', 'gte', 'lte', 'eq'
    severity: AlertSeverity = AlertSeverity.WARNING
    cooldown_seconds: int = 300
    enabled: bool = True
    _last_triggered: Optional[datetime] = field(default=None, repr=False)

    def evaluate(self, value: float) -> bool:
        """Evaluate if the given value triggers this alert rule."""
        ops: Dict[str, Callable[[float, float], bool]] = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
        }
        if self.operator not in ops:
            raise AlertRuleError(f"Unknown operator: {self.operator}")
        return ops[self.operator](value, self.threshold)

    def is_in_cooldown(self) -> bool:
        """Check if the alert is currently in cooldown period."""
        if self._last_triggered is None:
            return False
        elapsed = (datetime.utcnow() - self._last_triggered).total_seconds()
        return elapsed < self.cooldown_seconds

    def mark_triggered(self) -> None:
        """Mark the alert as triggered at the current time."""
        self._last_triggered = datetime.utcnow()


@dataclass
class AlertNotification:
    """Represents an alert notification to be delivered."""
    rule_name: str
    metric: str
    value: float
    threshold: float
    severity: AlertSeverity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str = ""


@dataclass
class Dashboard:
    """Represents a real-time dashboard configuration."""
    dashboard_id: str
    title: str
    metrics: List[str]
    refresh_interval_seconds: int = 30
    widgets: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReportSchedule:
    """Defines a scheduled report with delivery configuration."""
    schedule_id: str
    name: str
    dashboard_id: str
    cron_expression: str
    channels: List[DeliveryChannel]
    recipients: List[str]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


@dataclass
class FreshnessCheck:
    """Configuration for data freshness monitoring."""
    source_name: str
    max_age_seconds: int
    status: FreshnessStatus = FreshnessStatus.FRESH
    last_check: Optional[datetime] = None
    last_data_timestamp: Optional[datetime] = None


# ─── Protocols ────────────────────────────────────────────────────────────────

class DataProvider(Protocol):
    """Protocol for data providers that supply metrics."""

    async def fetch_metrics(self, metric_names: List[str]) -> List[MetricValue]:
        """Fetch current values for the specified metrics."""
        ...


class NotificationSender(Protocol):
    """Protocol for notification delivery implementations."""

    async def send(self, notification: AlertNotification, channel: DeliveryChannel,
                   recipients: List[str]) -> bool:
        """Send a notification to the specified recipients via the given channel."""
        ...


# ─── Core Classes ─────────────────────────────────────────────────────────────

class AlertManager:
    """Manages alert rules and evaluates incoming metric values."""

    def __init__(self) -> None:
        self._rules: Dict[str, AlertRule] = {}
        self._handlers: List[Callable[[AlertNotification], Coroutine[Any, Any, None]]] = []

    def add_rule(self, rule: AlertRule) -> None:
        """Register a new alert rule."""
        if not rule.name or not rule.metric:
            raise AlertRuleError("Rule name and metric are required")
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        """Remove an alert rule by name."""
        self._rules.pop(name, None)

    def add_handler(self, handler: Callable[[AlertNotification], Coroutine[Any, Any, None]]) -> None:
        """Register an async handler for alert notifications."""
        self._handlers.append(handler)

    async def evaluate(self, metric: MetricValue) -> List[AlertNotification]:
        """Evaluate all rules against a metric value and return triggered alerts."""
        notifications: List[AlertNotification] = []
        for rule in self._rules.values():
            if not rule.enabled or rule.metric != metric.name:
                continue
            if rule.is_in_cooldown():
                continue
            if rule.evaluate(metric.value):
                rule.mark_triggered()
                notification = AlertNotification(
                    rule_name=rule.name,
                    metric=metric.name,
                    value=metric.value,
                    threshold=rule.threshold,
                    severity=rule.severity,
                    message=(
                        f"Alert '{rule.name}': {metric.name}={metric.value} "
                        f"triggered threshold ({rule.operator} {rule.threshold})"
                    ),
                )
                notifications.append(notification)
                for handler in self._handlers:
                    await handler(notification)
        return notifications


class DashboardRenderer:
    """Renders real-time dashboards from metric data."""

    def __init__(self) -> None:
        self._dashboards: Dict[str, Dashboard] = {}
        self._data_cache: Dict[str, List[MetricValue]] = {}

    def register(self, dashboard: Dashboard) -> None:
        """Register a dashboard for rendering."""
        self._dashboards[dashboard.dashboard_id] = dashboard

    def unregister(self, dashboard_id: str) -> None:
        """Remove a dashboard from rendering."""
        self._dashboards.pop(dashboard_id, None)
        self._data_cache.pop(dashboard_id, None)

    def update_data(self, dashboard_id: str, metrics: List[MetricValue]) -> None:
        """Update cached metric data for a dashboard."""
        if dashboard_id not in self._dashboards:
            raise DashboardNotFoundError(f"Dashboard '{dashboard_id}' not found")
        self._data_cache.setdefault(dashboard_id, []).extend(metrics)

    def render(self, dashboard_id: str) -> Dict[str, Any]:
        """Render a dashboard as a serializable dictionary."""
        if dashboard_id not in self._dashboards:
            raise DashboardNotFoundError(f"Dashboard '{dashboard_id}' not found")
        dashboard = self._dashboards[dashboard_id]
        data = self._data_cache.get(dashboard_id, [])
        return {
            "dashboard_id": dashboard.dashboard_id,
            "title": dashboard.title,
            "rendered_at": datetime.utcnow().isoformat(),
            "refresh_interval_seconds": dashboard.refresh_interval_seconds,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat(),
                    "labels": m.labels,
                }
                for m in data
            ],
            "widgets": dashboard.widgets,
        }

    async def refresh_loop(self, dashboard_id: str, provider: DataProvider) -> None:
        """Continuously refresh dashboard data from a provider."""
        if dashboard_id not in self._dashboards:
            raise DashboardNotFoundError(f"Dashboard '{dashboard_id}' not found")
        dashboard = self._dashboards[dashboard_id]
        while True:
            try:
                metrics = await provider.fetch_metrics(dashboard.metrics)
                self.update_data(dashboard_id, metrics)
            except Exception:
                pass
            await asyncio.sleep(dashboard.refresh_interval_seconds)


class FreshnessMonitor:
    """Monitors data freshness for configured sources."""

    def __init__(self) -> None:
        self._checks: Dict[str, FreshnessCheck] = {}

    def register(self, check: FreshnessCheck) -> None:
        """Register a data source for freshness monitoring."""
        self._checks[check.source_name] = check

    def update_timestamp(self, source_name: str, timestamp: Optional[datetime] = None) -> None:
        """Update the last known data timestamp for a source."""
        if source_name not in self._checks:
            raise DataFreshnessError(f"Source '{source_name}' not registered")
        self._checks[source_name].last_data_timestamp = timestamp or datetime.utcnow()
        self._checks[source_name].last_check = datetime.utcnow()

    def check_freshness(self, source_name: str) -> FreshnessStatus:
        """Check and return the freshness status of a data source."""
        if source_name not in self._checks:
            raise DataFreshnessError(f"Source '{source_name}' not registered")
        check = self._checks[source_name]
        if check.last_data_timestamp is None:
            check.status = FreshnessStatus.EXPIRED
            return check.status
        age = (datetime.utcnow() - check.last_data_timestamp).total_seconds()
        if age > check.max_age_seconds * 2:
            check.status = FreshnessStatus.EXPIRED
        elif age > check.max_age_seconds:
            check.status = FreshnessStatus.STALE
        else:
            check.status = FreshnessStatus.FRESH
        check.last_check = datetime.utcnow()
        return check.status

    def get_all_statuses(self) -> Dict[str, FreshnessStatus]:
        """Get freshness status for all registered sources."""
        return {name: self.check_freshness(name) for name in self._checks}


class ReportScheduler:
    """Schedules and delivers reports on a cron-like schedule."""

    def __init__(self, renderer: DashboardRenderer) -> None:
        self._renderer = renderer
        self._schedules: Dict[str, ReportSchedule] = {}
        self._senders: Dict[DeliveryChannel, NotificationSender] = {}

    def register_sender(self, channel: DeliveryChannel, sender: NotificationSender) -> None:
        """Register a notification sender for a delivery channel."""
        self._senders[channel] = sender

    def add_schedule(self, schedule: ReportSchedule) -> None:
        """Add a report delivery schedule."""
        if not schedule.name or not schedule.dashboard_id:
            raise ReportScheduleError("Schedule name and dashboard_id are required")
        self._schedules[schedule.schedule_id] = schedule

    def remove_schedule(self, schedule_id: str) -> None:
        """Remove a report schedule."""
        self._schedules.pop(schedule_id, None)

    async def run_schedule(self, schedule_id: str) -> bool:
        """Execute a scheduled report delivery immediately."""
        if schedule_id not in self._schedules:
            raise ReportScheduleError(f"Schedule '{schedule_id}' not found")
        schedule = self._schedules[schedule_id]
        if not schedule.enabled:
            return False
        try:
            report_data = self._renderer.render(schedule.dashboard_id)
            payload = json.dumps(report_data, default=str)
            for channel in schedule.channels:
                sender = self._senders.get(channel)
                if sender is None:
                    continue
                await sender.send(
                    AlertNotification(
                        rule_name=schedule.name,
                        metric="report",
                        value=0,
                        threshold=0,
                        severity=AlertSeverity.INFO,
                        message=f"Scheduled report: {schedule.name}",
                    ),
                    channel,
                    schedule.recipients,
                )
            schedule.last_run = datetime.utcnow()
            return True
        except Exception as e:
            raise ReportScheduleError(f"Failed to run schedule '{schedule_id}': {e}") from e

    async def scheduler_loop(self) -> None:
        """Continuously check and run due schedules."""
        while True:
            now = datetime.utcnow()
            for schedule in self._schedules.values():
                if not schedule.enabled:
                    continue
                if schedule.next_run is None or now >= schedule.next_run:
                    try:
                        await self.run_schedule(schedule.schedule_id)
                    except ReportScheduleError:
                        pass
                    schedule.next_run = now + timedelta(minutes=5)
            await asyncio.sleep(30)


class SelfServiceAnalytics:
    """Provides self-service analytics query capabilities."""

    def __init__(self) -> None:
        self._queries: Dict[str, Dict[str, Any]] = {}
        self._saved_views: Dict[str, Any] = {}

    def create_query(self, query_id: str, metric: str, filters: Optional[Dict[str, Any]] = None,
                     group_by: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create and register a self-service analytics query."""
        query = {
            "query_id": query_id,
            "metric": metric,
            "filters": filters or {},
            "group_by": group_by or [],
            "created_at": datetime.utcnow().isoformat(),
        }
        self._queries[query_id] = query
        return query

    def get_query(self, query_id: str) -> Dict[str, Any]:
        """Retrieve a saved query by ID."""
        if query_id not in self._queries:
            raise ContinuousBIError(f"Query '{query_id}' not found")
        return self._queries[query_id]

    def delete_query(self, query_id: str) -> None:
        """Delete a saved query."""
        self._queries.pop(query_id, None)

    def save_view(self, view_id: str, query_id: str, config: Dict[str, Any]) -> None:
        """Save a query as a reusable view."""
        if query_id not in self._queries:
            raise ContinuousBIError(f"Query '{query_id}' not found")
        self._saved_views[view_id] = {
            "query_id": query_id,
            "config": config,
            "saved_at": datetime.utcnow().isoformat(),
        }

    def list_views(self) -> List[Dict[str, Any]]:
        """List all saved views."""
        return [{"view_id": vid, **data} for vid, data in self._saved_views.items()]


# ─── Module Facade ────────────────────────────────────────────────────────────

class ContinuousBI:
    """Main facade for the Continuous BI module.

    Orchestrates dashboards, alerts, freshness monitoring,
    report scheduling, and self-service analytics.
    """

    def __init__(self) -> None:
        self.alerts = AlertManager()
        self.dashboards = DashboardRenderer()
        self.freshness = FreshnessMonitor()
        self.reports = ReportScheduler(self.dashboards)
        self.analytics = SelfServiceAnalytics()

    async def start(self) -> None:
        """Start all background monitoring tasks."""
        tasks = [self.reports.scheduler_loop()]
        await asyncio.gather(*tasks)

    async def stop(self) -> None:
        """Stop all background tasks (placeholder for cleanup)."""
