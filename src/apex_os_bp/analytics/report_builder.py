"""Custom report builder.

Assembles named sections of metrics into a structured report that can
be rendered as a dict, JSON, or Markdown. Supports computed metrics
(callables evaluated at build time) and automatic aggregation helpers
(sum, average, min, max, count).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Union

MetricValue = Union[int, float, str, bool, None]


@dataclass
class ReportMetric:
    """A single metric within a report section."""

    name: str
    value: MetricValue
    unit: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "description": self.description,
            "tags": list(self.tags),
        }


@dataclass
class ReportSection:
    """A titled group of metrics."""

    title: str
    metrics: List[ReportMetric] = field(default_factory=list)
    description: str = ""

    def add(
        self,
        name: str,
        value: MetricValue,
        unit: str = "",
        description: str = "",
        tags: Optional[Sequence[str]] = None,
    ) -> "ReportSection":
        """Add a metric and return the section (for chaining)."""
        self.metrics.append(
            ReportMetric(
                name=name,
                value=value,
                unit=unit,
                description=description,
                tags=list(tags or []),
            )
        )
        return self

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "description": self.description,
            "metrics": [m.to_dict() for m in self.metrics],
        }


def aggregate(series: Sequence[float], func: str) -> float:
    """Aggregate a numeric series.

    ``func`` is one of ``sum``, ``avg``/``mean``, ``min``, ``max``,
    ``count``, ``median``, ``std``.
    """
    values = [float(v) for v in series]
    if not values:
        raise ValueError("series must not be empty")
    if func in ("sum",):
        return sum(values)
    if func in ("avg", "mean"):
        return sum(values) / len(values)
    if func == "min":
        return min(values)
    if func == "max":
        return max(values)
    if func == "count":
        return float(len(values))
    if func == "median":
        s = sorted(values)
        n = len(s)
        mid = n // 2
        return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2
    if func == "std":
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / max(1, len(values) - 1)
        return var**0.5
    raise ValueError(f"unknown aggregation: {func}")


class ReportBuilder:
    """Fluent builder for structured analytics reports."""

    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description
        self._sections: List[ReportSection] = []
        self._computed: List[Callable[["ReportBuilder"], None]] = []

    def add_section(
        self, title: str, description: str = ""
    ) -> ReportSection:
        """Append a new section and return it for chaining."""
        section = ReportSection(title=title, description=description)
        self._sections.append(section)
        return section

    def add_metric(
        self,
        section: Union[str, int],
        name: str,
        value: MetricValue,
        unit: str = "",
        description: str = "",
        tags: Optional[Sequence[str]] = None,
    ) -> "ReportBuilder":
        """Add a metric to a section (by title or index)."""
        sec = self._resolve_section(section)
        sec.add(name, value, unit=unit, description=description, tags=tags)
        return self

    def add_computed(
        self, section: Union[str, int], name: str, fn: Callable[[], MetricValue],
        unit: str = "", description: str = "",
    ) -> "ReportBuilder":
        """Register a callable evaluated at build time.

        The callable receives no arguments and must return the metric
        value. Useful for pulling live data from an engine.
        """
        sec = self._resolve_section(section)
        self._computed.append(
            lambda: sec.add(name, fn(), unit=unit, description=description)
        )
        return self

    def add_aggregation(
        self,
        section: Union[str, int],
        name: str,
        series: Sequence[float],
        func: str,
        unit: str = "",
        description: str = "",
    ) -> "ReportBuilder":
        """Add an aggregated metric computed from *series*."""
        return self.add_metric(
            section, name, aggregate(series, func), unit=unit, description=description
        )

    def _resolve_section(self, section: Union[str, int]) -> ReportSection:
        if isinstance(section, int):
            if not 0 <= section < len(self._sections):
                raise IndexError(f"section index out of range: {section}")
            return self._sections[section]
        for sec in self._sections:
            if sec.title == section:
                return sec
        raise KeyError(f"section not found: {section}")

    @property
    def sections(self) -> List[ReportSection]:
        return list(self._sections)

    def build(self) -> Dict:
        """Evaluate computed metrics and return the report as a dict."""
        for fn in self._computed:
            fn()
        return {
            "title": self.title,
            "description": self.description,
            "section_count": len(self._sections),
            "metric_count": sum(len(s.metrics) for s in self._sections),
            "sections": [s.to_dict() for s in self._sections],
        }

    def to_json(self, indent: int = 2) -> str:
        """Return the report serialised as JSON."""
        return json.dumps(self.build(), indent=indent, default=str)

    def to_markdown(self) -> str:
        """Return the report rendered as Markdown."""
        lines: List[str] = [f"# {self.title}", ""]
        if self.description:
            lines += [self.description, ""]
        for sec in self._sections:
            lines.append(f"## {sec.title}")
            if sec.description:
                lines.append(f"_{sec.description}_")
            lines.append("")
            if sec.metrics:
                lines.append("| Metric | Value | Unit | Description |")
                lines.append("| --- | ---: | --- | --- |")
                for m in sec.metrics:
                    desc = m.description.replace("|", "\\|")
                    lines.append(
                        f"| {m.name} | {m.value} | {m.unit} | {desc} |"
                    )
            else:
                lines.append("_No metrics._")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"
