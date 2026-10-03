"""Deepened BI module: dashboards, ad-hoc SQL, charts, scheduling, self-service."""
from __future__ import annotations
import json, math, sqlite3, time, uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# ── Dashboard Builder ──────────────────────────────────────────────────────
class WidgetType(str, Enum):
    TABLE, BAR, LINE, PIE, METRIC, HEATMAP = "table", "bar", "line", "pie", "metric", "heatmap"

@dataclass
class Widget:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: WidgetType = WidgetType.TABLE
    title: str = ""
    query: str = ""
    position: dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 4, "h": 3})
    config: dict[str, Any] = field(default_factory=dict)

@dataclass
class Dashboard:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Untitled"
    owner: str = ""
    widgets: list[Widget] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    def add_widget(self, w: Widget) -> None: self.widgets.append(w)
    def remove_widget(self, wid: str) -> bool:
        n = len(self.widgets); self.widgets = [w for w in self.widgets if w.id != wid]; return len(self.widgets) < n
    def move_widget(self, wid: str, x: int, y: int) -> bool:
        for w in self.widgets:
            if w.id == wid: w.position["x"], w.position["y"] = x, y; return True
        return False
    def resize_widget(self, wid: str, w: int, h: int) -> bool:
        for widget in self.widgets:
            if widget.id == wid: widget.position["w"], widget.position["h"] = w, h; return True
        return False
    def to_dict(self) -> dict: return asdict(self)

class DashboardBuilder:
    def __init__(self, store_path: str = "dashboards.json"):
        self.store_path = Path(store_path); self._dashboards: dict[str, Dashboard] = {}; self._load()
    def create(self, name: str, owner: str = "") -> Dashboard:
        d = Dashboard(name=name, owner=owner); self._dashboards[d.id] = d; self._save(); return d
    def get(self, did: str) -> Dashboard | None: return self._dashboards.get(did)
    def list(self) -> list[Dashboard]: return list(self._dashboards.values())
    def delete(self, did: str) -> bool:
        if did in self._dashboards: del self._dashboards[did]; self._save(); return True
        return False
    def _save(self) -> None:
        self.store_path.write_text(json.dumps({k: v.to_dict() for k, v in self._dashboards.items()}, indent=2))
    def _load(self) -> None:
        if self.store_path.exists():
            for k, v in json.loads(self.store_path.read_text()).items():
                self._dashboards[k] = Dashboard(widgets=[Widget(**w) for w in v.pop("widgets", [])], **v)

# ── Ad-hoc SQL Reporting ────────────────────────────────────────────────────
@dataclass
class QueryResult:
    columns: list[str]; rows: list[list[Any]]; elapsed_ms: float; row_count: int
    def to_dict(self) -> dict: return asdict(self)

class AdHocReporter:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path); self.conn.row_factory = sqlite3.Row
    def execute(self, sql: str, params: tuple = ()) -> QueryResult:
        start = time.perf_counter(); cur = self.conn.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [list(r) for r in cur.fetchall()]
        return QueryResult(cols, rows, round((time.perf_counter() - start) * 1000, 2), len(rows))
    def explain(self, sql: str) -> QueryResult: return self.execute(f"EXPLAIN QUERY PLAN {sql}")
    def schema(self) -> QueryResult: return self.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    def close(self) -> None: self.conn.close()

# ── Data Visualization ───────────────────────────────────────────────────────
@dataclass
class ChartSpec:
    type: str; title: str; labels: list[str]; series: list[dict[str, Any]]; options: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict: return asdict(self)

def _detect_chart_type(data: QueryResult, preferred: str = "auto") -> str:
    if preferred != "auto": return preferred
    if len(data.columns) < 2: return "metric"
    return "pie" if len(data.rows) <= 10 else "line"

def build_chart(data: QueryResult, chart_type: str = "auto", title: str = "", label_col: int = 0, value_col: int = 1) -> ChartSpec:
    ctype = _detect_chart_type(data, chart_type)
    return ChartSpec(ctype, title or data.columns[value_col],
                     [str(r[label_col]) for r in data.rows],
                     [{"name": data.columns[value_col], "data": [r[value_col] for r in data.rows]}])

def render_chart_svg(spec: ChartSpec, width: int = 600, height: int = 300) -> str:
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
         f'<text x="{width//2}" y="20" text-anchor="middle" font-size="14">{spec.title}</text>']
    if spec.type == "metric" and spec.series:
        p.append(f'<text x="{width//2}" y="{height//2}" text-anchor="middle" font-size="36">{spec.series[0]["data"][0]}</text>')
    elif spec.type == "bar":
        mx = max((abs(v) for s in spec.series for v in s["data"]), default=1); bw = width // max(len(spec.labels), 1)
        for i, lbl in enumerate(spec.labels):
            for s in spec.series:
                v = s["data"][i] if i < len(s["data"]) else 0; bh = int((abs(v) / mx) * (height - 60))
                p += [f'<rect x="{i*bw+10}" y="{height-30-bh}" width="{bw-4}" height="{bh}" fill="#4f81bd"/>',
                      f'<text x="{i*bw+bw//2}" y="{height-10}" font-size="10" text-anchor="middle">{lbl}</text>']
    elif spec.type == "line":
        mx = max((abs(v) for s in spec.series for v in s["data"]), default=1); pts = []
        for s in spec.series:
            for j, v in enumerate(s["data"]):
                pts.append(f"{(j+1)*width//(len(s['data'])+1)},{height-30-int((abs(v)/mx)*(height-60))}")
        p.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#4f81bd" stroke-width="2"/>')
    elif spec.type == "pie":
        total = sum(abs(v) for s in spec.series for v in s["data"]) or 1
        cx, cy, r = width // 2, height // 2, min(width, height) // 3; angle = 0
        colors = ["#4f81bd", "#c0504d", "#9bbb59", "#8064a2", "#4bacc6"]
        for s in spec.series:
            for j, v in enumerate(s["data"]):
                frac = abs(v) / total; end = angle + frac * 2 * math.pi
                x1, y1, x2, y2 = cx+r*math.cos(angle), cy+r*math.sin(angle), cx+r*math.cos(end), cy+r*math.sin(end)
                p.append(f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {1 if frac>0.5 else 0},1 {x2:.1f},{y2:.1f} Z" fill="{colors[j%5]}"/>')
                angle = end
    p.append("</svg>"); return "\n".join(p)

# ── Report Scheduling & Delivery ───────────────────────────────────────────
class DeliveryChannel(str, Enum):
    EMAIL, SLACK, WEBHOOK, FILE = "email", "slack", "webhook", "file"

@dataclass
class Schedule:
    cron: str = "0 9 * * *"; channel: DeliveryChannel = DeliveryChannel.EMAIL
    target: str = ""; enabled: bool = True; last_run: str | None = None; next_run: str | None = None

@dataclass
class ScheduledReport:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""; query: str = ""; chart_type: str = "auto"
    schedule: Schedule = field(default_factory=Schedule)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

class ReportScheduler:
    def __init__(self, store_path: str = "schedules.json"):
        self.store_path = Path(store_path); self._reports: dict[str, ScheduledReport] = {}; self._load()
    def add(self, report: ScheduledReport) -> None: self._reports[report.id] = report; self._save()
    def remove(self, rid: str) -> bool:
        if rid in self._reports: del self._reports[rid]; self._save(); return True
        return False
    def list(self) -> list[ScheduledReport]: return list(self._reports.values())
    def run_due(self, reporter: AdHocReporter, deliver: Callable[[str, str, QueryResult], None]) -> list[str]:
        executed: list[str] = []; now = datetime.utcnow()
        for r in self._reports.values():
            if not r.schedule.enabled: continue
            if r.schedule.next_run and datetime.fromisoformat(r.schedule.next_run) > now: continue
            result = reporter.execute(r.query); deliver(r.name, r.schedule.channel.value, result)
            r.schedule.last_run = now.isoformat(); r.schedule.next_run = (now + timedelta(hours=24)).isoformat()
            executed.append(r.id)
        if executed: self._save()
        return executed
    def _save(self) -> None:
        self.store_path.write_text(json.dumps({k: asdict(v) for k, v in self._reports.items()}, indent=2))
    def _load(self) -> None:
        if self.store_path.exists():
            for k, v in json.loads(self.store_path.read_text()).items():
                v["schedule"] = Schedule(**v.pop("schedule")); self._reports[k] = ScheduledReport(**v)

# ── Self-Service Analytics ──────────────────────────────────────────────────
@dataclass
class DataSource:
    name: str; connection_string: str; schema: dict[str, list[str]] = field(default_factory=dict)

@dataclass
class UserQuery:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user: str = ""; natural_language: str = ""; generated_sql: str = ""
    result: QueryResult | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

class SelfServiceAnalytics:
    def __init__(self, reporter: AdHocReporter):
        self.reporter = reporter; self._sources: dict[str, DataSource] = {}; self._saved: dict[str, UserQuery] = {}
    def register_source(self, ds: DataSource) -> None: self._sources[ds.name] = ds
    def catalog(self) -> dict[str, list[str]]: return {n: list(ds.schema) for n, ds in self._sources.items()}
    def nl_to_sql(self, question: str, context: dict[str, str] | None = None) -> str:
        ctx = context or {}; tables = list(ctx.get("tables", ["events"]).values()) if isinstance(ctx.get("tables"), dict) else ["events"]
        table = tables[0] if tables else "events"; q = question.lower()
        if "count" in q: return f"SELECT COUNT(*) AS total FROM {table}"
        if "average" in q or "avg" in q: return f"SELECT AVG(value) AS average FROM {table}"
        if "group" in q or "by" in q: return f"SELECT category, COUNT(*) AS cnt FROM {table} GROUP BY category ORDER BY cnt DESC"
        return f"SELECT * FROM {table} LIMIT 100"
    def ask(self, user: str, question: str, context: dict[str, str] | None = None) -> UserQuery:
        sql = self.nl_to_sql(question, context); result = self.reporter.execute(sql)
        uq = UserQuery(user=user, natural_language=question, generated_sql=sql, result=result)
        self._saved[uq.id] = uq; return uq
    def save_query(self, uq: UserQuery) -> None: self._saved[uq.id] = uq
    def get_query(self, qid: str) -> UserQuery | None: return self._saved.get(qid)
    def list_queries(self, user: str = "") -> list[UserQuery]:
        return [q for q in self._saved.values() if q.user == user] if user else list(self._saved.values())
    def share_query(self, qid: str, target_user: str) -> dict[str, str]:
        src = self._saved.get(qid)
        if not src: return {"error": "not found"}
        shared = UserQuery(user=target_user, natural_language=src.natural_language, generated_sql=src.generated_sql)
        self._saved[shared.id] = shared; return {"shared_id": shared.id, "target": target_user}
