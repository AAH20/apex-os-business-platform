"""DR Planning module — defines recovery tiers, DR plans, and planning logic."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RecoveryTier(str, Enum):
    """Recovery tiers ordered by criticality (lower value = more critical)."""

    TIER_0 = "tier_0"  # Mission-critical: RPO 0, RTO < 1 min
    TIER_1 = "tier_1"  # Critical: RPO < 5 min, RTO < 15 min
    TIER_2 = "tier_2"  # Important: RPO < 1 hr, RTO < 4 hr
    TIER_3 = "tier_3"  # Standard: RPO < 24 hr, RTO < 48 hr
    TIER_4 = "tier_4"  # Archive: RPO < 7 days, RTO < 1 week


@dataclass
class DRPlan:
    """A disaster recovery plan for a service or data set."""

    name: str
    tier: RecoveryTier
    rpo_seconds: int  # Recovery Point Objective in seconds
    rto_seconds: int  # Recovery Time Objective in seconds
    primary_region: str
    secondary_region: str
    services: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    runbook_url: str = ""
    last_tested: float | None = None
    notes: str = ""

    def is_compliant(self, actual_rpo: float, actual_rto: float) -> bool:
        """Check whether actual recovery metrics meet the plan's objectives."""
        return actual_rpo <= self.rpo_seconds and actual_rto <= self.rto_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier.value,
            "rpo_seconds": self.rpo_seconds,
            "rto_seconds": self.rto_seconds,
            "primary_region": self.primary_region,
            "secondary_region": self.secondary_region,
            "services": list(self.services),
            "data_sources": list(self.data_sources),
            "dependencies": list(self.dependencies),
            "runbook_url": self.runbook_url,
            "last_tested": self.last_tested,
            "notes": self.notes,
        }


class DRPlanner:
    """Creates and manages DR plans for the platform."""

    DEFAULT_TIER_OBJECTIVES: dict[RecoveryTier, tuple[int, int]] = {
        RecoveryTier.TIER_0: (0, 60),
        RecoveryTier.TIER_1: (300, 900),
        RecoveryTier.TIER_2: (3600, 14400),
        RecoveryTier.TIER_3: (86400, 172800),
        RecoveryTier.TIER_4: (604800, 604800),
    }

    def __init__(self) -> None:
        self._plans: dict[str, DRPlan] = {}

    def create_plan(
        self,
        name: str,
        tier: RecoveryTier,
        primary_region: str,
        secondary_region: str,
        services: list[str] | None = None,
        data_sources: list[str] | None = None,
        dependencies: list[str] | None = None,
        runbook_url: str = "",
        notes: str = "",
        rpo_seconds: int | None = None,
        rto_seconds: int | None = None,
    ) -> DRPlan:
        """Create a new DR plan with default or custom RPO/RTO."""
        default_rpo, default_rto = self.DEFAULT_TIER_OBJECTIVES[tier]
        plan = DRPlan(
            name=name,
            tier=tier,
            rpo_seconds=rpo_seconds if rpo_seconds is not None else default_rpo,
            rto_seconds=rto_seconds if rto_seconds is not None else default_rto,
            primary_region=primary_region,
            secondary_region=secondary_region,
            services=services or [],
            data_sources=data_sources or [],
            dependencies=dependencies or [],
            runbook_url=runbook_url,
            notes=notes,
        )
        self._plans[name] = plan
        return plan

    def get_plan(self, name: str) -> DRPlan | None:
        return self._plans.get(name)

    def list_plans(self) -> list[DRPlan]:
        return list(self._plans.values())

    def plans_by_tier(self, tier: RecoveryTier) -> list[DRPlan]:
        return [p for p in self._plans.values() if p.tier == tier]

    def untested_plans(self, max_age_seconds: float = 2592000) -> list[DRPlan]:
        """Return plans not tested within the given window (default 30 days)."""
        now = time.time()
        return [
            p
            for p in self._plans.values()
            if p.last_tested is None or (now - p.last_tested) > max_age_seconds
        ]

    def mark_tested(self, name: str, timestamp: float | None = None) -> None:
        plan = self._plans.get(name)
        if plan is not None:
            plan.last_tested = timestamp if timestamp is not None else time.time()

    def remove_plan(self, name: str) -> bool:
        if name in self._plans:
            del self._plans[name]
            return True
        return False

    def validate_plan(self, plan: DRPlan) -> list[str]:
        """Return a list of validation issues (empty = valid)."""
        issues: list[str] = []
        if not plan.name:
            issues.append("Plan name is required")
        if plan.rpo_seconds < 0:
            issues.append("RPO must be non-negative")
        if plan.rto_seconds <= 0:
            issues.append("RTO must be positive")
        if plan.primary_region == plan.secondary_region:
            issues.append("Primary and secondary regions must differ")
        if not plan.services and not plan.data_sources:
            issues.append("Plan must cover at least one service or data source")
        return issues
