"""Dashboards for APEX-OS.

Provides dashboard and panel definitions for visualizing metrics,
with support for multiple panel types and data source bindings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PanelType(Enum):
    """Types of dashboard panels."""

    GRAPH = "graph"
    STAT = "stat"
    TABLE = "table"
    GAUGE = "gauge"
    HEATMAP = "heatmap"
    LOGS = "logs"


@dataclass
class DataSource:
    """A data source for dashboard panels."""

    name: str
    source_type: str  # "prometheus", "influxdb", "elasticsearch", etc.
    url: str
    query: str = ""
    refresh_interval: float = 30.0
    headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.source_type,
            "url": self.url,
            "query": self.query,
            "refresh_interval": self.refresh_interval,
            "headers": dict(self.headers),
        }


@dataclass
class Panel:
    """A single panel within a dashboard."""

    title: str
    panel_type: PanelType
    data_source: Optional[str] = None
    query: str = ""
    unit: str = ""
    thresholds: List[Dict[str, Any]] = field(default_factory=list)
    targets: List[Dict[str, Any]] = field(default_factory=list)
    grid_pos: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 12, "h": 8})
    legend: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "type": self.panel_type.value,
            "data_source": self.data_source,
            "query": self.query,
            "unit": self.unit,
            "thresholds": list(self.thresholds),
            "targets": list(self.targets),
            "grid_pos": dict(self.grid_pos),
            "legend": self.legend,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Panel":
        """Create a Panel from a dictionary."""
        return cls(
            title=data["title"],
            panel_type=PanelType(data["type"]),
            data_source=data.get("data_source"),
            query=data.get("query", ""),
            unit=data.get("unit", ""),
            thresholds=data.get("thresholds", []),
            targets=data.get("targets", []),
            grid_pos=data.get("grid_pos", {"x": 0, "y": 0, "w": 12, "h": 8}),
            legend=data.get("legend", True),
            description=data.get("description", ""),
        )


class Dashboard:
    """A dashboard containing multiple panels."""

    def __init__(
        self,
        title: str,
        description: str = "",
        refresh_interval: float = 30.0,
        time_range: str = "1h",
        tags: Optional[List[str]] = None,
    ):
        self.title = title
        self.description = description
        self.refresh_interval = refresh_interval
        self.time_range = time_range
        self.tags = tags or []
        self._panels: List[Panel] = []
        self._data_sources: Dict[str, DataSource] = {}

    def add_panel(self, panel: Panel) -> Panel:
        """Add a panel to the dashboard."""
        self._panels.append(panel)
        return panel

    def remove_panel(self, title: str) -> bool:
        """Remove a panel by title. Returns True if removed."""
        for i, panel in enumerate(self._panels):
            if panel.title == title:
                self._panels.pop(i)
                return True
        return False

    def get_panel(self, title: str) -> Optional[Panel]:
        """Get a panel by title."""
        for panel in self._panels:
            if panel.title == title:
                return panel
        return None

    def list_panels(self) -> List[Panel]:
        """List all panels."""
        return list(self._panels)

    def add_data_source(self, source: DataSource) -> DataSource:
        """Add a data source to the dashboard."""
        self._data_sources[source.name] = source
        return source

    def remove_data_source(self, name: str) -> bool:
        """Remove a data source by name. Returns True if removed."""
        if name in self._data_sources:
            del self._data_sources[name]
            return True
        return False

    def get_data_source(self, name: str) -> Optional[DataSource]:
        """Get a data source by name."""
        return self._data_sources.get(name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert dashboard to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "refresh_interval": self.refresh_interval,
            "time_range": self.time_range,
            "tags": list(self.tags),
            "panels": [p.to_dict() for p in self._panels],
            "data_sources": {k: v.to_dict() for k, v in self._data_sources.items()},
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert dashboard to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dashboard":
        """Create a Dashboard from a dictionary."""
        dashboard = cls(
            title=data["title"],
            description=data.get("description", ""),
            refresh_interval=data.get("refresh_interval", 30.0),
            time_range=data.get("time_range", "1h"),
            tags=data.get("tags", []),
        )
        for panel_data in data.get("panels", []):
            dashboard.add_panel(Panel.from_dict(panel_data))
        for source_data in data.get("data_sources", {}).values():
            dashboard.add_data_source(DataSource(
                name=source_data["name"],
                source_type=source_data.get("type", source_data.get("source_type", "")),
                url=source_data["url"],
                query=source_data.get("query", ""),
                refresh_interval=source_data.get("refresh_interval", 30.0),
                headers=source_data.get("headers", {}),
            ))
        return dashboard

    @classmethod
    def from_json(cls, json_str: str) -> "Dashboard":
        """Create a Dashboard from a JSON string."""
        return cls.from_dict(json.loads(json_str))


class DashboardManager:
    """Manages multiple dashboards."""

    def __init__(self):
        self._dashboards: Dict[str, Dashboard] = {}

    def create_dashboard(self, title: str, **kwargs: Any) -> Dashboard:
        """Create and register a new dashboard."""
        dashboard = Dashboard(title=title, **kwargs)
        self._dashboards[title] = dashboard
        return dashboard

    def get_dashboard(self, title: str) -> Optional[Dashboard]:
        """Get a dashboard by title."""
        return self._dashboards.get(title)

    def remove_dashboard(self, title: str) -> bool:
        """Remove a dashboard by title. Returns True if removed."""
        if title in self._dashboards:
            del self._dashboards[title]
            return True
        return False

    def list_dashboards(self) -> List[Dashboard]:
        """List all dashboards."""
        return list(self._dashboards.values())

    def list_dashboard_titles(self) -> List[str]:
        """List all dashboard titles."""
        return list(self._dashboards.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Convert all dashboards to dictionary."""
        return {title: dash.to_dict() for title, dash in self._dashboards.items()}

    def to_json(self, indent: int = 2) -> str:
        """Convert all dashboards to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
