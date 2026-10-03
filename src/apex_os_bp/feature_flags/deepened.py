"""Deepened feature flags: targeting, analytics, lifecycle, dependencies, audit."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ── 1. Targeting with Segments ──────────────────────────────────────────────

class SegmentOperator(str, Enum):
    IN = "in"
    NOT_IN = "not_in"
    GT = "gt"
    LT = "lt"
    EQ = "eq"
    CONTAINS = "contains"


@dataclass
class SegmentRule:
    attribute: str
    operator: SegmentOperator
    value: Any

    def matches(self, context: dict[str, Any]) -> bool:
        actual = context.get(self.attribute)
        if actual is None:
            return False
        match self.operator:
            case SegmentOperator.IN:
                return actual in self.value
            case SegmentOperator.NOT_IN:
                return actual not in self.value
            case SegmentOperator.GT:
                return actual > self.value
            case SegmentOperator.LT:
                return actual < self.value
            case SegmentOperator.EQ:
                return actual == self.value
            case SegmentOperator.CONTAINS:
                return self.value in actual
        return False


@dataclass
class Segment:
    name: str
    rules: list[SegmentRule] = field(default_factory=list)

    def matches(self, context: dict[str, Any]) -> bool:
        return all(r.matches(context) for r in self.rules)


# ── 2. Analytics with Impact Measurement ───────────────────────────────────

@dataclass
class FlagAnalytics:
    flag_name: str
    evaluations: int = 0
    hits: int = 0
    misses: int = 0
    impact_score: float = 0.0
    _samples: list[float] = field(default_factory=list)

    def record(self, enabled: bool, metric_value: float | None = None) -> None:
        self.evaluations += 1
        if enabled:
            self.hits += 1
        else:
            self.misses += 1
        if metric_value is not None:
            self._samples.append(metric_value)
            self.impact_score = sum(self._samples) / len(self._samples)

    @property
    def hit_rate(self) -> float:
        return self.hits / self.evaluations if self.evaluations else 0.0


# ── 3. Lifecycle with Cleanup ───────────────────────────────────────────────

class FlagState(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class FlagLifecycle:
    state: FlagState = FlagState.DRAFT
    created_at: float = field(default_factory=time.time)
    activated_at: float | None = None
    deprecated_at: float | None = None
    archived_at: float | None = None

    def activate(self) -> None:
        self.state = FlagState.ACTIVE
        self.activated_at = time.time()

    def deprecate(self) -> None:
        self.state = FlagState.DEPRECATED
        self.deprecated_at = time.time()

    def archive(self) -> None:
        self.state = FlagState.ARCHIVED
        self.archived_at = time.time()

    def is_stale(self, max_age_days: float = 90) -> bool:
        if self.state != FlagState.DEPRECATED or not self.deprecated_at:
            return False
        return (time.time() - self.deprecated_at) > max_age_days * 86400


# ── 4. Flag Dependencies with Ordering ──────────────────────────────────────

@dataclass
class FlagDependency:
    flag_name: str
    requires: list[str] = field(default_factory=list)

    def resolve_order(self, all_flags: dict[str, "FlagDependency"]) -> list[str]:
        visited: set[str] = set()
        order: list[str] = []

        def _visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            dep = all_flags.get(name)
            if dep:
                for req in dep.requires:
                    _visit(req)
            order.append(name)

        _visit(self.flag_name)
        return order


# ── 5. Flag Audit with Change History ───────────────────────────────────────

class AuditAction(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    ACTIVATED = "activated"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    TARGETING_UPDATED = "targeting_updated"


@dataclass
class AuditEntry:
    action: AuditAction
    timestamp: float
    actor: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlagAudit:
    entries: list[AuditEntry] = field(default_factory=list)

    def log(self, action: AuditAction, actor: str, **details: Any) -> None:
        self.entries.append(AuditEntry(action, time.time(), actor, details))

    def history(self) -> list[AuditEntry]:
        return sorted(self.entries, key=lambda e: e.timestamp)


# ── Unified Flag ────────────────────────────────────────────────────────────

@dataclass
class FeatureFlag:
    name: str
    enabled: bool = False
    segments: list[Segment] = field(default_factory=list)
    analytics: FlagAnalytics | None = None
    lifecycle: FlagLifecycle = field(default_factory=FlagLifecycle)
    dependency: FlagDependency | None = None
    audit: FlagAudit = field(default_factory=FlagAudit)

    def evaluate(self, context: dict[str, Any], actor: str = "system") -> bool:
        if self.lifecycle.state == FlagState.ARCHIVED:
            return False
        if not self.segments:
            result = self.enabled
        else:
            result = self.enabled and any(s.matches(context) for s in self.segments)
        if self.analytics:
            self.analytics.record(result)
        return result

    def transition(self, new_state: FlagState, actor: str) -> None:
        action_map = {
            FlagState.ACTIVE: AuditAction.ACTIVATED,
            FlagState.DEPRECATED: AuditAction.DEPRECATED,
            FlagState.ARCHIVED: AuditAction.ARCHIVED,
        }
        if new_state == FlagState.ACTIVE:
            self.lifecycle.activate()
        elif new_state == FlagState.DEPRECATED:
            self.lifecycle.deprecate()
        elif new_state == FlagState.ARCHIVED:
            self.lifecycle.archive()
        self.audit.log(action_map.get(new_state, AuditAction.MODIFIED), actor)


# ── Cleanup helper ──────────────────────────────────────────────────────────

def cleanup_stale_flags(flags: list[FeatureFlag], max_age_days: float = 90) -> list[str]:
    """Archive deprecated flags older than max_age_days. Returns archived names."""
    archived: list[str] = []
    for flag in flags:
        if flag.lifecycle.is_stale(max_age_days):
            flag.transition(FlagState.ARCHIVED, actor="cleanup")
            archived.append(flag.name)
    return archived
