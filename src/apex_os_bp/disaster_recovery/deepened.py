"""Deepened DR module: planning, testing, failover, runbooks, metrics."""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── 1. DR Planning (RPO/RTO) ──────────────────────────────────────────────

class DRTier(str, Enum):
    TIER_1 = "tier_1"; TIER_2 = "tier_2"; TIER_3 = "tier_3"; TIER_4 = "tier_4"

@dataclass
class DRPlan:
    service_name: str; tier: DRTier; rpo_minutes: int; rto_minutes: int
    primary_region: str; dr_region: str; backup_schedule: str = "0 */6 * * *"
    replication_mode: str = "async"; dependencies: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        e: List[str] = []
        if self.rpo_minutes < 1: e.append("rpo_minutes must be >= 1")
        if self.rto_minutes < 1: e.append("rto_minutes must be >= 1")
        if self.rpo_minutes > self.rto_minutes: e.append("RPO should not exceed RTO")
        if self.tier == DRTier.TIER_1 and self.rpo_minutes > 15: e.append("Tier-1 RPO must be <= 15 min")
        if self.tier == DRTier.TIER_1 and self.rto_minutes > 60: e.append("Tier-1 RTO must be <= 60 min")
        return e

    def to_dict(self) -> Dict[str, Any]:
        return {k: (v.value if isinstance(v, Enum) else v) for k, v in self.__dict__.items()}

class DRPlanner:
    def __init__(self) -> None: self._plans: Dict[str, DRPlan] = {}
    def register(self, plan: DRPlan) -> None:
        errs = plan.validate()
        if errs: raise ValueError(f"Invalid DR plan for {plan.service_name}: {errs}")
        self._plans[plan.service_name] = plan
    def get_plan(self, name: str) -> Optional[DRPlan]: return self._plans.get(name)
    def all_plans(self) -> List[DRPlan]: return list(self._plans.values())
    def compliance_report(self) -> Dict[str, Any]:
        bt: Dict[str, int] = {}
        for p in self._plans.values(): bt[p.tier.value] = bt.get(p.tier.value, 0) + 1
        return {"total_services": len(self._plans), "by_tier": bt, "services": list(self._plans)}

# ── 2. DR Testing (Chaos Engineering) ─────────────────────────────────────

class ChaosAction(str, Enum):
    KILL_PROCESS = "kill_process"; NETWORK_PARTITION = "network_partition"
    LATENCY_INJECTION = "latency_injection"; DISK_FILL = "disk_fill"
    CPU_STRESS = "cpu_stress"; DNS_FAILURE = "dns_failure"; REGION_BLACKOUT = "region_blackout"

@dataclass
class ChaosExperiment:
    name: str; action: ChaosAction; target_service: str; duration_seconds: int
    expected_rto_minutes: int; blast_radius: str = "single_instance"; rollback_automatic: bool = True
    def to_dict(self) -> Dict[str, Any]:
        return {k: (v.value if isinstance(v, Enum) else v) for k, v in self.__dict__.items()}

@dataclass
class ChaosResult:
    experiment: ChaosExperiment; started_at: float; ended_at: float
    recovered: bool; actual_rto_seconds: float; data_loss_seconds: float = 0.0
    @property
    def rto_met(self) -> bool: return self.actual_rto_seconds <= self.experiment.expected_rto_minutes * 60
    def to_dict(self) -> Dict[str, Any]:
        d = {k: (v.value if isinstance(v, Enum) else v) for k, v in self.__dict__.items()}
        d["rto_met"] = self.rto_met; return d

class ChaosEngine:
    def __init__(self) -> None: self._results: List[ChaosResult] = []
    def run(self, exp: ChaosExperiment,
            injector: Optional[Callable[[ChaosExperiment], None]] = None,
            checker: Optional[Callable[[], bool]] = None) -> ChaosResult:
        start = time.time()
        if injector: injector(exp)
        time.sleep(min(exp.duration_seconds, 0.1))
        recovered = checker() if checker else True; end = time.time()
        r = ChaosResult(exp, start, end, recovered, end - start, 0.0 if recovered else end - start)
        self._results.append(r); return r
    def results_for(self, svc: str) -> List[ChaosResult]:
        return [r for r in self._results if r.experiment.target_service == svc]
    def summary(self) -> Dict[str, Any]:
        t = len(self._results); rec = sum(1 for r in self._results if r.recovered)
        met = sum(1 for r in self._results if r.rto_met)
        return {"total_experiments": t, "recovered": rec, "recovery_rate": rec/t if t else 0.0,
                "rto_met_count": met, "rto_met_rate": met/t if t else 0.0}

# ── 3. DR Failover (Automation) ────────────────────────────────────────────

class FailoverState(str, Enum):
    IDLE = "idle"; DETECTING = "detecting"; DECIDING = "deciding"
    FAILOVER_IN_PROGRESS = "failover_in_progress"; FAILOVER_COMPLETE = "failover_complete"
    FAILBACK_IN_PROGRESS = "failback_in_progress"; FAILED = "failed"

@dataclass
class FailoverEvent:
    service_name: str; from_region: str; to_region: str; trigger: str
    state: FailoverState; started_at: float; completed_at: Optional[float] = None; error: Optional[str] = None
    def to_dict(self) -> Dict[str, Any]:
        return {k: (v.value if isinstance(v, Enum) else v) for k, v in self.__dict__.items()}

class FailoverAutomator:
    _TX = {FailoverState.DETECTING: FailoverState.DECIDING,
           FailoverState.DECIDING: FailoverState.FAILOVER_IN_PROGRESS,
           FailoverState.FAILOVER_IN_PROGRESS: FailoverState.FAILOVER_COMPLETE,
           FailoverState.FAILOVER_COMPLETE: FailoverState.FAILBACK_IN_PROGRESS,
           FailoverState.FAILBACK_IN_PROGRESS: FailoverState.IDLE}
    def __init__(self, planner: DRPlanner) -> None:
        self._planner = planner; self._events: List[FailoverEvent] = []; self._state: Dict[str, FailoverState] = {}
    def current_state(self, svc: str) -> FailoverState: return self._state.get(svc, FailoverState.IDLE)
    def initiate_failover(self, svc: str, trigger: str = "manual") -> FailoverEvent:
        plan = self._planner.get_plan(svc)
        if not plan: raise ValueError(f"No DR plan for '{svc}'")
        ev = FailoverEvent(svc, plan.primary_region, plan.dr_region, trigger, FailoverState.DETECTING, time.time())
        self._events.append(ev); self._state[svc] = FailoverState.DETECTING; return ev
    def advance(self, svc: str) -> FailoverEvent:
        ev = next((e for e in reversed(self._events) if e.service_name == svc), None)
        if not ev: raise ValueError(f"No failover event for '{svc}'")
        nxt = self._TX.get(ev.state)
        if nxt is None: ev.state = FailoverState.FAILED
        else:
            ev.state = nxt
            if nxt in (FailoverState.FAILOVER_COMPLETE, FailoverState.IDLE): ev.completed_at = time.time()
        self._state[svc] = ev.state; return ev
    def events_for(self, svc: str) -> List[FailoverEvent]:
        return [e for e in self._events if e.service_name == svc]
    def active_failovers(self) -> List[FailoverEvent]:
        t = {FailoverState.FAILOVER_COMPLETE, FailoverState.IDLE, FailoverState.FAILED}
        return [e for e in self._events if e.state not in t]

# ── 4. DR Runbooks (Procedures) ────────────────────────────────────────────

@dataclass
class RunbookStep:
    order: int; description: str; command: Optional[str] = None
    verification: Optional[str] = None; rollback: Optional[str] = None; estimated_minutes: int = 5

@dataclass
class Runbook:
    name: str; service: str; scenario: str; steps: List[RunbookStep]
    owner: str = "dr-team"; last_tested: Optional[str] = None
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "service": self.service, "scenario": self.scenario,
                "owner": self.owner, "last_tested": self.last_tested, "steps": [s.__dict__ for s in self.steps]}

class RunbookManager:
    def __init__(self) -> None: self._rb: Dict[str, Runbook] = {}
    def add(self, rb: Runbook) -> None: self._rb[rb.name] = rb
    def get(self, name: str) -> Optional[Runbook]: return self._rb.get(name)
    def for_service(self, svc: str) -> List[Runbook]: return [r for r in self._rb.values() if r.service == svc]
    def all(self) -> List[Runbook]: return list(self._rb.values())
    def generate_default(self, plan: DRPlan) -> Runbook:
        steps = [RunbookStep(1, "Confirm primary region failure", verification="Health checks failing > 2 min"),
                 RunbookStep(2, "Notify stakeholders", command="pagerduty escalate --service " + plan.service_name),
                 RunbookStep(3, "Promote DR database", command=f"aws rds promote-read-replica --region {plan.dr_region}",
                             verification="Database writable in DR region"),
                 RunbookStep(4, "Update DNS to DR region", command=f"aws route53 update-record --region {plan.dr_region}",
                             verification="DNS TTL expired, traffic routed"),
                 RunbookStep(5, "Verify service health in DR", verification="All health endpoints 200"),
                 RunbookStep(6, "Monitor stability (15 min)", verification="Error rate < 0.1%")]
        return Runbook(f"{plan.service_name}-failover", plan.service_name, "primary_region_outage", steps)

# ── 5. DR Metrics (Availability) ───────────────────────────────────────────

@dataclass
class AvailabilityWindow:
    service: str; window_start: float; window_end: float; total_seconds: float; downtime_seconds: float
    @property
    def availability_pct(self) -> float:
        return 100.0 if self.total_seconds <= 0 else round(((self.total_seconds - self.downtime_seconds) / self.total_seconds) * 100, 4)
    @property
    def sla_met(self) -> bool: return self.availability_pct >= 99.9
    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy(); d["availability_pct"] = self.availability_pct; d["sla_met"] = self.sla_met; return d

class DRMetricsCollector:
    def __init__(self) -> None: self._w: List[AvailabilityWindow] = []
    def record_outage(self, svc: str, start: float, end: float) -> None:
        d = end - start; self._w.append(AvailabilityWindow(svc, start, end, d, d))
    def record_uptime(self, svc: str, start: float, end: float) -> None:
        self._w.append(AvailabilityWindow(svc, start, end, end - start, 0.0))
    def availability_for(self, svc: str, since: Optional[float] = None) -> Optional[AvailabilityWindow]:
        rel = [w for w in self._w if w.service == svc]
        if since is not None: rel = [w for w in rel if w.window_start >= since]
        if not rel: return None
        return AvailabilityWindow(svc, min(w.window_start for w in rel), max(w.window_end for w in rel),
                                  sum(w.total_seconds for w in rel), sum(w.downtime_seconds for w in rel))
    def report(self) -> Dict[str, Any]:
        svcs = list({w.service for w in self._w})
        ps = {s: self.availability_for(s).to_dict() for s in svcs if self.availability_for(s)}
        return {"services": ps, "overall_availability_pct": round(sum(s["availability_pct"] for s in ps.values()) / len(ps), 4) if ps else 100.0}

# ── Convenience ────────────────────────────────────────────────────────────

def build_default_dr_stack() -> Dict[str, Any]:
    planner = DRPlanner(); rbm = RunbookManager()
    for p in [DRPlan("payments", DRTier.TIER_1, 5, 30, "us-east-1", "us-west-2", replication_mode="sync"),
              DRPlan("orders", DRTier.TIER_1, 15, 60, "us-east-1", "us-west-2"),
              DRPlan("analytics", DRTier.TIER_3, 240, 480, "us-east-1", "eu-west-1", replication_mode="snapshot")]:
        planner.register(p); rbm.add(rbm.generate_default(p))
    return {"planner": planner, "chaos_engine": ChaosEngine(), "failover_automator": FailoverAutomator(planner),
            "runbook_manager": rbm, "metrics_collector": DRMetricsCollector()}

__all__ = ["DRTier","DRPlan","DRPlanner","ChaosAction","ChaosExperiment","ChaosResult","ChaosEngine",
           "FailoverState","FailoverEvent","FailoverAutomator","RunbookStep","Runbook","RunbookManager",
           "AvailabilityWindow","DRMetricsCollector","build_default_dr_stack"]
