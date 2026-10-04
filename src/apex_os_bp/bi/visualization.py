"""Data visualization module."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ChartType(Enum):
    """Supported chart types."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    TABLE = "table"


@dataclass
class ChartConfig:
    """Chart configuration."""
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    width: int = 800
    height: int = 600
    show_legend: bool = True
    show_grid: bool = True
    colors: List[str] = field(default_factory=lambda: [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ])


@dataclass
class DataPoint:
    """Single data point for visualization."""
    label: str
    value: float
    category: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class ChartSeries:
    """Chart data series."""
    name: str
    data: List[DataPoint] = field(default_factory=list)
    color: str = ""


class DataVisualizer:
    """Data visualization engine."""

    def __init__(self):
        self._charts: Dict[str, Dict] = {}

    def create_line_chart(self, series: List[ChartSeries], config: Optional[ChartConfig] = None) -> Dict:
        """Create a line chart."""
        config = config or ChartConfig()
        chart = {
            "type": ChartType.LINE.value,
            "config": {
                "title": config.title,
                "x_label": config.x_label,
                "y_label": config.y_label,
                "width": config.width,
                "height": config.height,
                "show_legend": config.show_legend,
                "show_grid": config.show_grid,
            },
            "series": [
                {
                    "name": s.name,
                    "color": s.color or config.colors[i % len(config.colors)],
                    "data": [{"label": d.label, "value": d.value} for d in s.data],
                }
                for i, s in enumerate(series)
            ],
        }
        chart_id = f"line_{len(self._charts)}"
        self._charts[chart_id] = chart
        return chart

    def create_bar_chart(self, series: List[ChartSeries], config: Optional[ChartConfig] = None) -> Dict:
        """Create a bar chart."""
        config = config or ChartConfig()
        chart = {
            "type": ChartType.BAR.value,
            "config": {
                "title": config.title,
                "x_label": config.x_label,
                "y_label": config.y_label,
                "width": config.width,
                "height": config.height,
                "show_legend": config.show_legend,
                "show_grid": config.show_grid,
            },
            "series": [
                {
                    "name": s.name,
                    "color": s.color or config.colors[i % len(config.colors)],
                    "data": [{"label": d.label, "value": d.value} for d in s.data],
                }
                for i, s in enumerate(series)
            ],
        }
        chart_id = f"bar_{len(self._charts)}"
        self._charts[chart_id] = chart
        return chart

    def create_pie_chart(self, data: List[DataPoint], config: Optional[ChartConfig] = None) -> Dict:
        """Create a pie chart."""
        config = config or ChartConfig()
        total = sum(d.value for d in data)
        chart = {
            "type": ChartType.PIE.value,
            "config": {
                "title": config.title,
                "width": config.width,
                "height": config.height,
                "show_legend": config.show_legend,
            },
            "data": [
                {
                    "label": d.label,
                    "value": d.value,
                    "percentage": (d.value / total * 100) if total > 0 else 0,
                    "color": config.colors[i % len(config.colors)],
                }
                for i, d in enumerate(data)
            ],
        }
        chart_id = f"pie_{len(self._charts)}"
        self._charts[chart_id] = chart
        return chart

    def create_gauge_chart(self, value: float, min_val: float, max_val: float,
                           title: str = "", unit: str = "") -> Dict:
        """Create a gauge chart."""
        percentage = ((value - min_val) / (max_val - min_val)) * 100 if max_val != min_val else 0
        chart = {
            "type": ChartType.GAUGE.value,
            "config": {
                "title": title,
                "unit": unit,
                "min": min_val,
                "max": max_val,
            },
            "value": value,
            "percentage": max(0, min(100, percentage)),
        }
        chart_id = f"gauge_{len(self._charts)}"
        self._charts[chart_id] = chart
        return chart

    def create_heatmap(self, data: List[List[float]], x_labels: List[str],
                       y_labels: List[str], title: str = "") -> Dict:
        """Create a heatmap."""
        flat = [v for row in data for v in row]
        min_val = min(flat) if flat else 0
        max_val = max(flat) if flat else 1
        chart = {
            "type": ChartType.HEATMAP.value,
            "config": {
                "title": title,
                "x_labels": x_labels,
                "y_labels": y_labels,
            },
            "data": data,
            "min_value": min_val,
            "max_value": max_val,
        }
        chart_id = f"heatmap_{len(self._charts)}"
        self._charts[chart_id] = chart
        return chart

    def create_table(self, headers: List[str], rows: List[List],
                     title: str = "") -> Dict:
        """Create a table visualization."""
        chart = {
            "type": ChartType.TABLE.value,
            "config": {
                "title": title,
            },
            "headers": headers,
            "rows": rows,
        }
        chart_id = f"table_{len(self._charts)}"
        self._charts[chart_id] = chart
        return chart

    def create_scatter_plot(self, series: List[ChartSeries], config: Optional[ChartConfig] = None) -> Dict:
        """Create a scatter plot."""
        config = config or ChartConfig()
        chart = {
            "type": ChartType.SCATTER.value,
            "config": {
                "title": config.title,
                "x_label": config.x_label,
                "y_label": config.y_label,
                "width": config.width,
                "height": config.height,
                "show_legend": config.show_legend,
                "show_grid": config.show_grid,
            },
            "series": [
                {
                    "name": s.name,
                    "color": s.color or config.colors[i % len(config.colors)],
                    "data": [{"label": d.label, "value": d.value} for d in s.data],
                }
                for i, s in enumerate(series)
            ],
        }
        chart_id = f"scatter_{len(self._charts)}"
        self._charts[chart_id] = chart
        return chart

    def create_area_chart(self, series: List[ChartSeries], config: Optional[ChartConfig] = None) -> Dict:
        """Create an area chart."""
        config = config or ChartConfig()
        chart = {
            "type": ChartType.AREA.value,
            "config": {
                "title": config.title,
                "x_label": config.x_label,
                "y_label": config.y_label,
                "width": config.width,
                "height": config.height,
                "show_legend": config.show_legend,
                "show_grid": config.show_grid,
            },
            "series": [
                {
                    "name": s.name,
                    "color": s.color or config.colors[i % len(config.colors)],
                    "data": [{"label": d.label, "value": d.value} for d in s.data],
                }
                for i, s in enumerate(series)
            ],
        }
        chart_id = f"area_{len(self._charts)}"
        self._charts[chart_id] = chart
        return chart

    def get_chart(self, chart_id: str) -> Optional[Dict]:
        """Get chart by ID."""
        return self._charts.get(chart_id)

    def get_all_charts(self) -> Dict[str, Dict]:
        """Get all created charts."""
        return self._charts.copy()

    def clear(self) -> None:
        """Clear all charts."""
        self._charts.clear()

    @staticmethod
    def generate_ascii_bar(data: List[DataPoint], width: int = 50) -> str:
        """Generate ASCII bar chart for terminal display."""
        if not data:
            return "No data"
        max_val = max(d.value for d in data)
        if max_val == 0:
            return "No data"
        lines = []
        for d in data:
            bar_len = int((d.value / max_val) * width)
            bar = "█" * bar_len
            lines.append(f"{d.label:20s} |{bar:<{width}s}| {d.value:.1f}")
        return "\n".join(lines)

    @staticmethod
    def generate_ascii_line(data: List[DataPoint], height: int = 10, width: int = 50) -> str:
        """Generate ASCII line chart for terminal display."""
        if not data:
            return "No data"
        max_val = max(d.value for d in data)
        min_val = min(d.value for d in data)
        range_val = max_val - min_val if max_val != min_val else 1
        grid = [[" " for _ in range(width)] for _ in range(height)]
        for i, d in enumerate(data):
            x = int((i / max(len(data) - 1, 1)) * (width - 1))
            y = height - 1 - int(((d.value - min_val) / range_val) * (height - 1))
            y = max(0, min(height - 1, y))
            grid[y][x] = "*"
        lines = []
        for row in grid:
            lines.append("".join(row))
        return "\n".join(lines)
