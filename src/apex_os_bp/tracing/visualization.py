"""Trace visualization for APEX-OS Business Platform.

Renders trace data as text-based visualizations:
- Hierarchical tree view of spans
- Timeline view showing span durations
- Summary tables for trace analysis
- ASCII-based Gantt chart for trace timeline
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from apex_os_bp.tracing.span import Span, SpanKind, SpanStatus


@dataclass
class TraceTree:
    """Represents a trace as a tree structure for visualization."""
    span: Span
    children: List[TraceTree] = field(default_factory=list)

    def add_child(self, node: TraceTree) -> None:
        self.children.append(node)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span": self.span.to_dict(),
            "children": [c.to_dict() for c in self.children],
        }


class TraceVisualizer:
    """Text-based trace visualization.

    Produces human-readable representations of trace data
    suitable for terminal output or log files.
    """

    INDENT = "  "
    BRANCH = "├── "
    LAST_BRANCH = "└── "
    VERTICAL = "│   "

    def __init__(self, max_name_width: int = 40):
        self._max_name_width = max_name_width

    def render_tree(self, spans: List[Span]) -> str:
        """Render spans as an ASCII tree.

        Args:
            spans: List of spans to visualize.

        Returns:
            String representation of the trace tree.
        """
        if not spans:
            return "(no spans)"

        tree = self._build_tree(spans)
        lines: List[str] = []
        self._render_node(tree, "", "", lines, is_last=True)
        return "\n".join(lines)

    def render_timeline(self, spans: List[Span], width: int = 80) -> str:
        """Render spans as a timeline/Gantt chart.

        Args:
            spans: List of spans to visualize.
            width: Width of the timeline in characters.

        Returns:
            ASCII timeline representation.
        """
        if not spans:
            return "(no spans)"

        # Find time range
        start_times = [s.start_time for s in spans]
        end_times = [s.end_time for s in spans if s.end_time is not None]
        if not end_times:
            return "(no completed spans)"

        min_start = min(start_times)
        max_end = max(end_times)
        total_duration = max_end - min_start

        if total_duration <= 0:
            return "(zero duration trace)"

        lines: List[str] = []
        header = f"{'Span':<{self._max_name_width}} | {'Duration':>10} | Timeline"
        lines.append(header)
        lines.append("-" * len(header))

        for span in sorted(spans, key=lambda s: s.start_time):
            name = self._truncate(span.name, self._max_name_width)
            duration = span.duration_ms
            duration_str = f"{duration:.1f}ms" if duration is not None else "N/A"

            # Calculate position
            offset = (span.start_time - min_start) / total_duration
            bar_len = ((span.end_time or max_end) - span.start_time) / total_duration if span.end_time else 0

            bar_start = int(offset * (width - self._max_name_width - 20))
            bar_length = max(1, int(bar_len * (width - self._max_name_width - 20)))

            bar = " " * bar_start + "█" * bar_length
            status_indicator = self._status_indicator(span)

            lines.append(
                f"{name:<{self._max_name_width}} | {duration_str:>10} | {bar} {status_indicator}"
            )

        return "\n".join(lines)

    def render_summary(self, spans: List[Span]) -> str:
        """Render a summary table of trace statistics.

        Args:
            spans: List of spans to summarize.

        Returns:
            Formatted summary table.
        """
        if not spans:
            return "(no spans)"

        total = len(spans)
        errors = sum(1 for s in spans if s.status == SpanStatus.ERROR)
        durations = [s.duration_ms for s in spans if s.duration_ms is not None]
        services = set()
        for s in spans:
            svc = s.attributes.get("service.name")
            if svc:
                services.add(svc)

        avg_duration = sum(durations) / len(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0
        min_duration = min(durations) if durations else 0.0

        lines = [
            "╔══════════════════════════════════════╗",
            "║         Trace Summary                ║",
            "╠══════════════════════════════════════╣",
            f"║ Total Spans:    {total:>18} ║",
            f"║ Errors:          {errors:>18} ║",
            f"║ Services:        {len(services):>18} ║",
            f"║ Avg Duration:    {avg_duration:>14.1f}ms ║",
            f"║ Min Duration:    {min_duration:>14.1f}ms ║",
            f"║ Max Duration:    {max_duration:>14.1f}ms ║",
            "╚══════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def render_span_details(self, span: Span) -> str:
        """Render detailed information about a single span.

        Args:
            span: The span to render.

        Returns:
            Formatted span details.
        """
        lines = [
            f"Span: {span.name}",
            f"  Trace ID:  {span.trace_id}",
            f"  Span ID:   {span.span_id}",
            f"  Parent ID: {span.parent_span_id or '(root)'}",
            f"  Kind:      {span.kind.value}",
            f"  Status:    {span.status.value}",
        ]

        if span.status_message:
            lines.append(f"  Message:   {span.status_message}")

        duration = span.duration_ms
        if duration is not None:
            lines.append(f"  Duration:  {duration:.2f}ms")

        if span.attributes:
            lines.append("  Attributes:")
            for key, value in sorted(span.attributes.items()):
                lines.append(f"    {key}: {value}")

        if span.events:
            lines.append("  Events:")
            for event in span.events:
                lines.append(f"    [{event.timestamp:.6f}] {event.name}")
                for k, v in event.attributes.items():
                    lines.append(f"      {k}: {v}")

        return "\n".join(lines)

    def render_flat(self, spans: List[Span]) -> str:
        """Render spans as a flat list with indentation by depth.

        Args:
            spans: List of spans to render.

        Returns:
            Flat list representation.
        """
        if not spans:
            return "(no spans)"

        span_map = {s.span_id: s for s in spans}
        lines: List[str] = []

        # Find root spans
        roots = [s for s in spans if s.parent_span_id is None or s.parent_span_id not in span_map]

        for root in roots:
            self._render_flat_node(root, 0, span_map, lines)

        # Handle orphaned spans
        orphan_ids = {s.span_id for s in spans} - {s.span_id for s in roots}
        for span in spans:
            if span.span_id in orphan_ids and span.parent_span_id is not None:
                self._render_flat_node(span, 0, span_map, lines)
                orphan_ids.discard(span.span_id)

        return "\n".join(lines)

    def _build_tree(self, spans: List[Span]) -> TraceTree:
        """Build a tree structure from a flat list of spans."""
        span_map = {s.span_id: s for s in spans}
        children_map: Dict[str, List[Span]] = {}
        roots: List[Span] = []

        for span in spans:
            if span.parent_span_id and span.parent_span_id in span_map:
                children_map.setdefault(span.parent_span_id, []).append(span)
            else:
                roots.append(span)

        def build_node(span: Span) -> TraceTree:
            node = TraceTree(span=span)
            for child in children_map.get(span.span_id, []):
                node.add_child(build_node(child))
            return node

        # Create a virtual root if multiple roots
        if len(roots) == 1:
            return build_node(roots[0])
        elif len(roots) > 1:
            # Create virtual root
            virtual_span = Span(
                name="(virtual-root)",
                trace_id=roots[0].trace_id,
                span_id="virtual-root",
            )
            virtual_span.end()
            node = TraceTree(span=virtual_span)
            for root in roots:
                node.add_child(build_node(root))
            return node
        else:
            # No roots found, use first span
            virtual_span = Span(
                name="(virtual-root)",
                trace_id=spans[0].trace_id if spans else "empty",
                span_id="virtual-root",
            )
            virtual_span.end()
            return TraceTree(span=virtual_span)

    def _render_node(
        self,
        node: TraceTree,
        prefix: str,
        child_prefix: str,
        lines: List[str],
        is_last: bool,
    ) -> None:
        """Recursively render a tree node."""
        span = node.span
        branch = self.LAST_BRANCH if is_last else self.BRANCH
        status = self._status_indicator(span)
        duration_str = f"{span.duration_ms:.1f}ms" if span.duration_ms is not None else "N/A"
        name = self._truncate(span.name, self._max_name_width)

        lines.append(f"{prefix}{branch}{name} [{span.kind.value}] {duration_str} {status}")

        for i, child in enumerate(node.children):
            last = i == len(node.children) - 1
            self._render_node(
                child,
                child_prefix,
                child_prefix + ("    " if last else self.VERTICAL),
                lines,
                last,
            )

    def _render_flat_node(
        self,
        span: Span,
        depth: int,
        span_map: Dict[str, Span],
        lines: List[str],
    ) -> None:
        """Render a flat node with depth-based indentation."""
        indent = self.INDENT * depth
        status = self._status_indicator(span)
        duration_str = f"{span.duration_ms:.1f}ms" if span.duration_ms is not None else "N/A"
        name = self._truncate(span.name, self._max_name_width - depth * 2)

        lines.append(f"{indent}{name} [{span.kind.value}] {duration_str} {status}")

        # Find children
        children = [s for s in span_map.values() if s.parent_span_id == span.span_id]
        for child in children:
            self._render_flat_node(child, depth + 1, span_map, lines)

    def _status_indicator(self, span: Span) -> str:
        """Get a visual status indicator for a span."""
        if span.status == SpanStatus.ERROR:
            return "❌"
        elif span.status == SpanStatus.OK:
            return "✅"
        return "⚪"

    def _truncate(self, text: str, max_width: int) -> str:
        """Truncate text to fit within max_width."""
        if len(text) <= max_width:
            return text
        return text[: max_width - 3] + "..."
