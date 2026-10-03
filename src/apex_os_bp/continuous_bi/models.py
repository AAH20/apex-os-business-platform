"""Data models for Continuous BI."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class WidgetType(Enum):
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    TABLE = "table"
    METRIC = "metric"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Query:
    id: str
    name: str
    sql: str
    parameters: dict[str, Any] = field(default_factory=dict)
    ttl_seconds: int = 60
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Widget:
    id: str
    dashboard_id: str
    query_id: str
    widget_type: WidgetType
    title: str
    config: dict[str, Any] = field(default_factory=dict)
    position: dict[str, int] = field(default_factory=dict)


@dataclass
class Dashboard:
    id: str
    name: str
    description: str = ""
    widgets: list[Widget] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Alert:
    id: str
    name: str
    query_id: str
    condition: str
    severity: AlertSeverity
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
