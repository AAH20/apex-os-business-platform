"""Chart generation and rendering for Continuous BI."""

import math
from typing import Any


class ChartGenerator:
    """Generates SVG charts from data."""

    @staticmethod
    def line_chart(
        data: list[dict], x_key: str, y_key: str,
        width: int = 600, height: int = 300,
    ) -> str:
        if not data:
            return "<svg></svg>"
        xs = [d[x_key] for d in data]
        ys = [d[y_key] for d in data]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = max_x - min_x or 1
        range_y = max_y - min_y or 1
        points = []
        for d in data:
            px = (d[x_key] - min_x) / range_x * (width - 40) + 20
            py = height - 20 - (d[y_key] - min_y) / range_y * (height - 40)
            points.append(f"{px:.1f},{py:.1f}")
        path = " ".join(points)
        return (
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
            f'<polyline points="{path}" fill="none" stroke="#3b82f6" stroke-width="2"/>'
            f"</svg>"
        )

    @staticmethod
    def bar_chart(
        data: list[dict], x_key: str, y_key: str,
        width: int = 600, height: int = 300,
    ) -> str:
        if not data:
            return "<svg></svg>"
        max_y = max(d[y_key] for d in data) or 1
        bar_width = (width - 40) / len(data)
        parts = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']
        for i, d in enumerate(data):
            bh = (d[y_key] / max_y) * (height - 40)
            x = 20 + i * bar_width
            y = height - 20 - bh
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" '
                f'width="{bar_width * 0.8:.1f}" height="{bh:.1f}" fill="#3b82f6"/>'
            )
        parts.append("</svg>")
        return "".join(parts)

    @staticmethod
    def pie_chart(
        data: list[dict], label_key: str, value_key: str,
        size: int = 300,
    ) -> str:
        if not data:
            return "<svg></svg>"
        total = sum(d[value_key] for d in data) or 1
        cx, cy, r = size // 2, size // 2, size // 2 - 10
        colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6"]
        parts = [f'<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">']
        start_angle = 0.0
        for i, d in enumerate(data):
            angle = (d[value_key] / total) * 360
            end_angle = start_angle + angle
            large_arc = 1 if angle > 180 else 0
            x1 = cx + r * math.cos(math.radians(start_angle))
            y1 = cy + r * math.sin(math.radians(start_angle))
            x2 = cx + r * math.cos(math.radians(end_angle))
            y2 = cy + r * math.sin(math.radians(end_angle))
            color = colors[i % len(colors)]
            parts.append(
                f'<path d="M {cx},{cy} L {x1:.1f},{y1:.1f} '
                f'A {r},{r} 0 {large_arc},1 {x2:.1f},{y2:.1f} Z" fill="{color}"/>'
            )
            start_angle = end_angle
        parts.append("</svg>")
        return "".join(parts)


class ChartRenderer:
    """Renders charts by delegating to ChartGenerator."""

    def __init__(self):
        self._generator = ChartGenerator()

    def render(self, chart_type: str, data: list[dict], **kwargs: Any) -> str:
        if chart_type == "line":
            return self._generator.line_chart(data, **kwargs)
        elif chart_type == "bar":
            return self._generator.bar_chart(data, **kwargs)
        elif chart_type == "pie":
            return self._generator.pie_chart(data, **kwargs)
        return "<svg></svg>"
