"""Deepened reporting module: builder, templates, scheduling, export, sharing."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


# ── Report Builder with Drag-Drop ──────────────────────────────────────────

class FieldType(Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    METRIC = "metric"
    DIMENSION = "dimension"


@dataclass
class ReportField:
    name: str
    field_type: FieldType
    source: str
    position: tuple[int, int] = (0, 0)  # (row, col) for drag-drop placement
    width: int = 1
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportBuilder:
    """Drag-and-drop report builder canvas."""
    name: str
    fields: list[ReportField] = field(default_factory=list)
    layout: list[list[str]] = field(default_factory=list)  # grid of field names

    def add_field(self, f: ReportField) -> None:
        self.fields.append(f)
        self._reflow()

    def remove_field(self, name: str) -> None:
        self.fields = [f for f in self.fields if f.name != name]
        self._reflow()

    def move_field(self, name: str, row: int, col: int) -> None:
        for f in self.fields:
            if f.name == name:
                f.position = (row, col)
                break
        self._reflow()

    def _reflow(self) -> None:
        max_row = max((f.position[0] for f in self.fields), default=0)
        max_col = max((f.position[1] for f in self.fields), default=0)
        self.layout = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]
        for f in self.fields:
            r, c = f.position
            if r < len(self.layout) and c < len(self.layout[r]):
                self.layout[r][c] = f.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fields": [
                {"name": f.name, "type": f.field_type.value, "source": f.source,
                 "position": f.position, "width": f.width, "config": f.config}
                for f in self.fields
            ],
            "layout": self.layout,
        }


# ── Report Templates with Library ──────────────────────────────────────────

@dataclass
class ReportTemplate:
    id: str
    name: str
    category: str
    description: str
    builder: ReportBuilder
    tags: list[str] = field(default_factory=list)
    is_builtin: bool = False


class TemplateLibrary:
    """Central registry of report templates."""

    def __init__(self) -> None:
        self._templates: dict[str, ReportTemplate] = {}

    def register(self, tpl: ReportTemplate) -> None:
        self._templates[tpl.id] = tpl

    def get(self, tpl_id: str) -> ReportTemplate | None:
        return self._templates.get(tpl_id)

    def list_all(self, category: str | None = None) -> list[ReportTemplate]:
        tpls = list(self._templates.values())
        if category:
            tpls = [t for t in tpls if t.category == category]
        return tpls

    def search(self, query: str) -> list[ReportTemplate]:
        q = query.lower()
        return [t for t in self._templates.values()
                if q in t.name.lower() or q in t.description.lower()
                or any(q in tag.lower() for tag in t.tags)]

    def create_from(self, tpl_id: str, name: str) -> ReportBuilder | None:
        tpl = self._templates.get(tpl_id)
        if not tpl:
            return None
        return ReportBuilder(name=name, fields=list(tpl.builder.fields),
                            layout=[row[:] for row in tpl.builder.layout])


# ── Report Scheduling with Delivery ────────────────────────────────────────

class ScheduleFrequency(Enum):
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DeliveryChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SFTP = "sftp"
    IN_APP = "in_app"


@dataclass
class ReportSchedule:
    id: str
    report_id: str
    frequency: ScheduleFrequency
    next_run: datetime
    channels: list[DeliveryChannel]
    recipients: list[str]
    format: str = "pdf"
    active: bool = True
    last_run: datetime | None = None
    run_count: int = 0

    def compute_next(self) -> datetime:
        deltas = {
            ScheduleFrequency.ONCE: timedelta(days=3650),
            ScheduleFrequency.HOURLY: timedelta(hours=1),
            ScheduleFrequency.DAILY: timedelta(days=1),
            ScheduleFrequency.WEEKLY: timedelta(weeks=1),
            ScheduleFrequency.MONTHLY: timedelta(days=30),
        }
        return datetime.utcnow() + deltas[self.frequency]

    def mark_run(self) -> None:
        self.last_run = datetime.utcnow()
        self.run_count += 1
        if self.frequency != ScheduleFrequency.ONCE:
            self.next_run = self.compute_next()
        else:
            self.active = False


class ScheduleManager:
    def __init__(self) -> None:
        self._schedules: dict[str, ReportSchedule] = {}

    def add(self, sched: ReportSchedule) -> None:
        self._schedules[sched.id] = sched

    def remove(self, sched_id: str) -> None:
        self._schedules.pop(sched_id, None)

    def due(self, now: datetime | None = None) -> list[ReportSchedule]:
        now = now or datetime.utcnow()
        return [s for s in self._schedules.values() if s.active and s.next_run <= now]

    def fire(self, sched_id: str) -> None:
        s = self._schedules.get(sched_id)
        if s:
            s.mark_run()


# ── Report Export with Multiple Formats ─────────────────────────────────────

class ExportFormat(Enum):
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    HTML = "html"
    PNG = "png"


@dataclass
class ExportResult:
    format: ExportFormat
    file_path: str
    size_bytes: int
    generated_at: datetime


class ReportExporter:
    def __init__(self, output_dir: str = "/tmp/reports") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, report: ReportBuilder, fmt: ExportFormat,
               data: list[dict[str, Any]] | None = None) -> ExportResult:
        data = data or []
        fname = f"{report.name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.{fmt.value}"
        fpath = self.output_dir / fname

        if fmt == ExportFormat.CSV:
            self._write_csv(fpath, data)
        elif fmt == ExportFormat.JSON:
            fpath.write_text(json.dumps(data, indent=2, default=str))
        elif fmt == ExportFormat.HTML:
            fpath.write_text(self._render_html(report, data))
        elif fmt == ExportFormat.XLSX:
            self._write_xlsx(fpath, data)
        elif fmt == ExportFormat.PDF:
            self._write_pdf(fpath, report, data)
        elif fmt == ExportFormat.PNG:
            self._write_png(fpath, report, data)

        return ExportResult(format=fmt, file_path=str(fpath),
                            size_bytes=fpath.stat().st_size,
                            generated_at=datetime.utcnow())

    def _write_csv(self, path: Path, data: list[dict]) -> None:
        import csv
        if not data:
            path.write_text("")
            return
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=data[0].keys())
            w.writeheader()
            w.writerows(data)

    def _write_xlsx(self, path: Path, data: list[dict]) -> None:
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            if data:
                ws.append(list(data[0].keys()))
                for row in data:
                    ws.append(list(row.values()))
            wb.save(path)
        except ImportError:
            path.write_text("xlsx export requires openpyxl")

    def _write_pdf(self, path: Path, report: ReportBuilder, data: list[dict]) -> None:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(str(path), pagesize=letter)
            c.drawString(72, 720, report.name)
            y = 700
            for row in data[:50]:
                c.drawString(72, y, str(row))
                y -= 14
            c.save()
        except ImportError:
            path.write_text(f"PDF: {report.name}\n{json.dumps(data, default=str)}")

    def _write_png(self, path: Path, report: ReportBuilder, data: list[dict]) -> None:
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (800, 600), "white")
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), report.name, fill="black")
            img.save(path)
        except ImportError:
            path.write_bytes(b"")

    def _render_html(self, report: ReportBuilder, data: list[dict]) -> str:
        rows = "".join(
            "<tr>" + "".join(f"<td>{v}</td>" for v in row.values()) + "</tr>"
            for row in data
        )
        headers = "".join(f"<th>{k}</th>" for k in data[0]) if data else ""
        return (
            f"<html><body><h1>{report.name}</h1><table><thead><tr>{headers}</tr></thead>"
            f"<tbody>{rows}</tbody></table></body></html>"
        )


# ── Report Sharing with Permissions ────────────────────────────────────────

class Permission(Enum):
    VIEW = "view"
    EDIT = "edit"
    SHARE = "share"
    DELETE = "delete"


@dataclass
class ShareGrant:
    report_id: str
    grantee: str  # user or group id
    permissions: set[Permission]
    granted_by: str
    granted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class ShareManager:
    def __init__(self) -> None:
        self._grants: dict[str, list[ShareGrant]] = {}

    def grant(self, g: ShareGrant) -> None:
        self._grants.setdefault(g.report_id, []).append(g)

    def revoke(self, report_id: str, grantee: str) -> None:
        if report_id in self._grants:
            self._grants[report_id] = [
                g for g in self._grants[report_id] if g.grantee != grantee
            ]

    def check(self, report_id: str, user: str, perm: Permission) -> bool:
        for g in self._grants.get(report_id, []):
            if g.grantee == user and perm in g.permissions:
                if g.expires_at is None or g.expires_at > datetime.utcnow():
                    return True
        return False

    def list_grants(self, report_id: str) -> list[ShareGrant]:
        return list(self._grants.get(report_id, []))

    def shareable_link(self, report_id: str, perm: Permission = Permission.VIEW) -> str:
        token = uuid.uuid4().hex
        return f"/shared/{report_id}?token={token}&perm={perm.value}"
