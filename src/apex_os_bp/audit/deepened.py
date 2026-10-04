"""Deepened audit module: immutable trail, SOC2 compliance, lineage, analytics, e-discovery export."""
from __future__ import annotations
import csv, hashlib, io, json, statistics, uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class AuditLevel(str, Enum):
    DEBUG = "debug"; INFO = "info"; WARNING = "warning"; ERROR = "error"; CRITICAL = "critical"

# 1. Immutable Audit Trail


@dataclass(frozen=True)
class AuditEntry:
    timestamp: str; event_id: str; actor: str; action: str; resource: str
    level: str; metadata: dict[str, Any]; prev_hash: str; entry_hash: str = ""
    def compute_hash(self) -> str:
        payload = json.dumps({k: v for k, v in asdict(self).items() if k != "entry_hash"}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()
    def verify(self) -> bool:
        return self.entry_hash == self.compute_hash()


class ImmutableAuditTrail:
    """Append-only, hash-chained audit log."""
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []; self._last_hash = "0" * 64
    def append(self, actor: str, action: str, resource: str,
               level: AuditLevel = AuditLevel.INFO, metadata: dict | None = None) -> AuditEntry:
        entry = AuditEntry(datetime.now(timezone.utc).isoformat(), str(uuid.uuid4()),
            actor, action, resource, level.value, metadata or {}, self._last_hash)
        object.__setattr__(entry, "entry_hash", entry.compute_hash())
        self._entries.append(entry); self._last_hash = entry.entry_hash
        return entry
    def verify_chain(self) -> tuple[bool, int | None]:
        prev = "0" * 64
        for i, e in enumerate(self._entries):
            if e.prev_hash != prev or not e.verify(): return False, i
            prev = e.entry_hash
        return True, None
    def entries(self) -> list[AuditEntry]: return list(self._entries)
    def persist(self, path: str | Path) -> None:
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w") as fh:
            for e in self._entries: fh.write(json.dumps(asdict(e), default=str) + "\n")
    @classmethod
    def load(cls, path: str | Path) -> "ImmutableAuditTrail":
        trail = cls()
        with Path(path).open() as fh:
            for line in fh:
                entry = AuditEntry(**json.loads(line))
                trail._entries.append(entry); trail._last_hash = entry.entry_hash
        return trail

# 2. SOC2 Compliance Reporting
SOC2_CRITERIA = {"CC6.1": "Logical access restrictions", "CC6.2": "Access removal timeliness",
    "CC6.3": "Access reviews", "CC7.1": "Security monitoring",
    "CC7.2": "Incident response", "CC7.3": "Risk mitigation", "CC8.1": "Change management"}


@dataclass
class ComplianceFinding:
    criterion: str; description: str; status: str; evidence: list[str] = field(default_factory=list)


class SOC2ComplianceReport:
    def __init__(self, trail: ImmutableAuditTrail) -> None:
        self.trail = trail; self.findings: list[ComplianceFinding] = []
    def evaluate(self) -> list[ComplianceFinding]:
        entries = self.trail.entries(); actions = {e.action for e in entries}
        self.findings = [
            ComplianceFinding("CC6.1", SOC2_CRITERIA["CC6.1"],
                "pass" if all(e.actor for e in entries) else "fail", [f"{len(entries)} entries"]),
            ComplianceFinding("CC6.2", SOC2_CRITERIA["CC6.2"],
                "pass" if any("revoke" in a or "remove" in a for a in actions) else "review",
                [f"revoke/remove: {any('revoke' in a or 'remove' in a for a in actions)}"]),
            ComplianceFinding("CC7.1", SOC2_CRITERIA["CC7.1"],
                "pass" if len({"login","logout","permission_change","access_denied"} & actions) >= 2 else "review",
                [f"security events: {sorted({'login','logout','permission_change','access_denied'} & actions)}"]),
            ComplianceFinding("CC7.2", SOC2_CRITERIA["CC7.2"],
                "pass" if any(e.level == "critical" for e in entries) else "review",
                [f"critical events: {any(e.level == 'critical' for e in entries)}"]),
            ComplianceFinding("CC8.1", SOC2_CRITERIA["CC8.1"],
                "pass" if any("deploy" in a or "config_change" in a for a in actions) else "review",
                [f"change events: {any('deploy' in a or 'config_change' in a for a in actions)}"]),
        ]
        return self.findings
    def summary(self) -> dict[str, Any]:
        if not self.findings: self.evaluate()
        s = Counter(f.status for f in self.findings)
        return {"total": len(self.findings), "passed": s["pass"], "failed": s["fail"],
                "review": s["review"], "compliant": s["fail"] == 0,
                "generated_at": datetime.now(timezone.utc).isoformat()}
    def to_dict(self) -> dict[str, Any]:
        return {"summary": self.summary(), "findings": [asdict(f) for f in self.findings]}

# 3. Data Lineage Tracking


@dataclass
class LineageNode:
    node_id: str; name: str; node_type: str; system: str; created_at: str
    upstream: list[str] = field(default_factory=list); downstream: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class DataLineageTracker:
    def __init__(self) -> None: self._nodes: dict[str, LineageNode] = {}
    def register(self, name: str, node_type: str, system: str,
                 upstream: list[str] | None = None, metadata: dict | None = None) -> LineageNode:
        nid = str(uuid.uuid4())[:8]
        node = LineageNode(nid, name, node_type, system, datetime.now(
            timezone.utc).isoformat(), upstream or [], [], metadata or {})
        self._nodes[nid] = node
        for up in node.upstream:
            if up in self._nodes: self._nodes[up].downstream.append(nid)
        return node
    def get_lineage(self, node_id: str, direction: str = "upstream") -> list[LineageNode]:
        if node_id not in self._nodes: return []
        result, queue, visited = [], [node_id], set()
        while queue:
            cur = queue.pop(0)
            if cur in visited: continue
            visited.add(cur); node = self._nodes[cur]; result.append(node)
            queue.extend(n for n in (node.upstream if direction == "upstream" else node.downstream) if n not in visited)
        return result
    def impact_analysis(self, node_id: str) -> dict[str, Any]:
        ds = self.get_lineage(node_id, "downstream")
        return {"source_node": node_id, "affected_count": len(ds),
                "affected_systems": list({n.system for n in ds}), "affected_nodes": [n.name for n in ds]}
    def to_dict(self) -> dict[str, Any]: return {nid: asdict(n) for nid, n in self._nodes.items()}

# 4. Audit Analytics with Anomaly Detection


@dataclass
class Anomaly:
    event_id: str; actor: str; action: str; score: float; reason: str


class AuditAnalytics:
    def __init__(self, trail: ImmutableAuditTrail) -> None: self.trail = trail
    def detect_anomalies(self, z_threshold: float = 2.0) -> list[Anomaly]:
        entries = self.trail.entries()
        if len(entries) < 5: return []
        actor_events: dict[str, list[AuditEntry]] = defaultdict(list)
        for e in entries: actor_events[e.actor].append(e)
        action_counts = Counter(e.action for e in entries); total = len(entries); anomalies: list[Anomaly] = []
        for e in entries:
            score, reasons = 0.0, []; actor_evts = actor_events[e.actor]
            actor_actions = Counter(ev.action for ev in actor_evts)
            if actor_actions[e.action] == 1 and action_counts[e.action] < total * 0.05:
                score += 0.4; reasons.append(f"rare_action:{e.action}")
            ts_list = sorted(datetime.fromisoformat(ev.timestamp).timestamp() for ev in actor_evts)
            idx = actor_evts.index(e)
            if idx > 0:
                intervals = [ts_list[i+1] - ts_list[i] for i in range(len(ts_list)-1)]
                if len(intervals) > 1:
                    mean, std = statistics.fmean(intervals), statistics.stdev(intervals)
                    if std > 0:
                        z = ((datetime.fromisoformat(e.timestamp).timestamp() - ts_list[idx-1]) - mean) / std
                        if abs(z) > z_threshold: score += 0.3; reasons.append(f"timing_zscore:{z:.2f}")
            hour = datetime.fromisoformat(e.timestamp).hour
            if 0 <= hour <= 5: score += 0.2; reasons.append(f"off_hours:{hour}")
            if e.level == "critical": score += 0.1; reasons.append("critical_level")
            if score >= 0.5: anomalies.append(Anomaly(e.event_id, e.actor, e.action,
                                              round(score, 3), "; ".join(reasons)))
        return anomalies
    def actor_summary(self) -> dict[str, dict[str, Any]]:
        actor_events: dict[str, list[AuditEntry]] = defaultdict(list)
        for e in self.trail.entries(): actor_events[e.actor].append(e)
        return {
            a: {
                "total_events": len(evts),
                "actions": dict(Counter(e.action for e in evts)),
                "levels": dict(Counter(e.level for e in evts)),
                "first_seen": evts[0].timestamp if evts else None,
                "last_seen": evts[-1].timestamp if evts else None,
            }
            for a, evts in actor_events.items()
        }

# 5. E-Discovery Export


class EDiscoveryExport:
    def __init__(self, trail: ImmutableAuditTrail) -> None: self.trail = trail
    def to_csv(self) -> str:
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["event_id","timestamp","actor","action","resource","level","prev_hash","entry_hash"])
        for e in self.trail.entries(): w.writerow(
            [e.event_id,e.timestamp,e.actor,e.action,e.resource,e.level,e.prev_hash,e.entry_hash])
        return buf.getvalue()
    def to_json(self, indent: int = 2) -> str:
        return json.dumps([asdict(e) for e in self.trail.entries()], indent=indent, default=str)
    def to_load_file(self) -> str:
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["DOCID","SHA256","FILEPATH","FILESIZE","DATETIME_UTC"])
        for e in self.trail.entries(): w.writerow(
            [e.event_id, e.entry_hash, f"native/{e.event_id}.json", len(json.dumps(asdict(e))), e.timestamp])
        return buf.getvalue()
    def filter_for_discovery(self, actors: list[str] | None = None, actions: list[str] | None = None,
                              start: str | None = None, end: str | None = None) -> list[AuditEntry]:
        result = self.trail.entries()
        if actors: result = [e for e in result if e.actor in actors]
        if actions: result = [e for e in result if e.action in actions]
        if start: result = [e for e in result if e.timestamp >= start]
        if end: result = [e for e in result if e.timestamp <= end]
        return result
    def export_package(self, output_dir: str | Path, actors: list[str] | None = None,
                       actions: list[str] | None = None, start: str | None = None,
                       end: str | None = None) -> dict[str, str]:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        filtered = self.filter_for_discovery(actors, actions, start, end)
        json_path = out / "audit_data.json"
        json_path.write_text(json.dumps([asdict(e) for e in filtered], indent=2, default=str))
        load_path = out / "load_file.csv"; buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["DOCID","SHA256","FILEPATH","FILESIZE","DATETIME_UTC"])
        for e in filtered: w.writerow(
            [e.event_id, e.entry_hash, f"native/{e.event_id}.json", len(json.dumps(asdict(e))), e.timestamp])
        load_path.write_text(buf.getvalue())
        manifest = {"generated_at": datetime.now(timezone.utc).isoformat(), "total_entries": len(filtered),
                    "filters": {"actors": actors, "actions": actions, "start": start, "end": end},
                    "chain_valid": self.trail.verify_chain()[0], "files": ["audit_data.json", "load_file.csv"]}
        manifest_path = out / "manifest.json"; manifest_path.write_text(json.dumps(manifest, indent=2))
        return {"data": str(json_path), "load_file": str(load_path), "manifest": str(manifest_path)}
