"""Alert routing for directing alerts to appropriate targets."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from apex_os_bp.alerting.models import (
    Alert,
    AlertRoutingStrategy,
    AlertRoutingTarget,
    AlertSeverity,
)

logger = logging.getLogger(__name__)


class AlertRouter:
    """Routes alerts to targets based on routing strategy."""

    def __init__(self):
        self._targets: Dict[str, AlertRoutingTarget] = {}
        self._round_robin_index: Dict[str, int] = {}
        self._routing_history: List[Dict[str, Any]] = []
        self._max_history = 10000

    def add_target(self, target: AlertRoutingTarget) -> AlertRoutingTarget:
        """Add a routing target."""
        self._targets[target.id] = target
        return target

    def remove_target(self, target_id: str) -> bool:
        """Remove a routing target."""
        if target_id in self._targets:
            del self._targets[target_id]
            return True
        return False

    def get_target(self, target_id: str) -> Optional[AlertRoutingTarget]:
        """Get a routing target by ID."""
        return self._targets.get(target_id)

    def get_targets(
        self,
        enabled_only: bool = True,
        channel: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
    ) -> List[AlertRoutingTarget]:
        """Get routing targets with optional filters."""
        targets = list(self._targets.values())
        if enabled_only:
            targets = [t for t in targets if t.enabled]
        if channel:
            targets = [t for t in targets if t.channel == channel]
        if severity:
            # Filter by severity label if present
            targets = [
                t for t in targets
                if t.labels.get("severity") == severity.value or "severity" not in t.labels
            ]
        return targets

    def update_target(self, target_id: str, **kwargs: Any) -> Optional[AlertRoutingTarget]:
        """Update a routing target."""
        target = self._targets.get(target_id)
        if not target:
            return None
        for key, value in kwargs.items():
            if hasattr(target, key):
                setattr(target, key, value)
        return target

    def route(
        self,
        alert: Alert,
        strategy: Optional[AlertRoutingStrategy] = None,
        targets: Optional[List[str]] = None,
    ) -> List[AlertRoutingTarget]:
        """Route an alert to targets based on strategy."""
        routing_strategy = strategy or AlertRoutingStrategy.BROADCAST

        # Get candidate targets
        if targets:
            candidate_targets = [
                self._targets[tid] for tid in targets if tid in self._targets
            ]
        else:
            candidate_targets = self.get_targets(enabled_only=True)

        if not candidate_targets:
            logger.warning(f"No routing targets available for alert {alert.id}")
            return []

        # Filter by notification channels if specified
        if alert.notification_channels:
            channel_targets = [
                t for t in candidate_targets if t.channel in alert.notification_channels
            ]
            if channel_targets:
                candidate_targets = channel_targets

        # Apply routing strategy
        if routing_strategy == AlertRoutingStrategy.BROADCAST:
            selected = candidate_targets
        elif routing_strategy == AlertRoutingStrategy.ROUND_ROBIN:
            selected = self._round_robin_select(candidate_targets, alert.rule_id)
        elif routing_strategy == AlertRoutingStrategy.PRIORITY:
            selected = self._priority_select(candidate_targets)
        elif routing_strategy == AlertRoutingStrategy.FAILOVER:
            selected = self._failover_select(candidate_targets, alert)
        else:
            selected = candidate_targets

        # Record routing decision
        self._record_routing(alert, selected, routing_strategy)

        # Update alert with routing targets
        alert.routing_targets = [t.id for t in selected]
        return selected

    def _round_robin_select(
        self, targets: List[AlertRoutingTarget], key: str
    ) -> List[AlertRoutingTarget]:
        """Select target using round-robin."""
        if not targets:
            return []
        idx = self._round_robin_index.get(key, 0)
        self._round_robin_index[key] = (idx + 1) % len(targets)
        return [targets[idx]]

    def _priority_select(
        self, targets: List[AlertRoutingTarget]
    ) -> List[AlertRoutingTarget]:
        """Select target(s) with highest priority."""
        if not targets:
            return []
        max_priority = max(t.priority for t in targets)
        return [t for t in targets if t.priority == max_priority]

    def _failover_select(
        self, targets: List[AlertRoutingTarget], alert: Alert
    ) -> List[AlertRoutingTarget]:
        """Select target using failover (first healthy target)."""
        # Sort by priority (highest first), then by name for determinism
        sorted_targets = sorted(targets, key=lambda t: (-t.priority, t.name))
        if sorted_targets:
            return [sorted_targets[0]]
        return []

    def _record_routing(
        self,
        alert: Alert,
        targets: List[AlertRoutingTarget],
        strategy: AlertRoutingStrategy,
    ) -> None:
        """Record a routing decision in history."""
        entry = {
            "alert_id": alert.id,
            "rule_id": alert.rule_id,
            "strategy": strategy.value,
            "target_ids": [t.id for t in targets],
            "target_names": [t.name for t in targets],
            "timestamp": time.time(),
        }
        self._routing_history.append(entry)
        if len(self._routing_history) > self._max_history:
            self._routing_history = self._routing_history[-self._max_history:]

    def get_routing_history(
        self,
        alert_id: Optional[str] = None,
        rule_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get routing history with optional filters."""
        history = self._routing_history
        if alert_id:
            history = [h for h in history if h["alert_id"] == alert_id]
        if rule_id:
            history = [h for h in history if h["rule_id"] == rule_id]
        return history

    def get_target_stats(self) -> Dict[str, Any]:
        """Get routing target statistics."""
        total = len(self._targets)
        enabled = sum(1 for t in self._targets.values() if t.enabled)
        by_channel: Dict[str, int] = {}
        for target in self._targets.values():
            by_channel[target.channel] = by_channel.get(target.channel, 0) + 1

        return {
            "total_targets": total,
            "enabled_targets": enabled,
            "disabled_targets": total - enabled,
            "by_channel": by_channel,
            "total_routing_decisions": len(self._routing_history),
        }

    def clear_history(self) -> None:
        """Clear routing history."""
        self._routing_history.clear()
        self._round_robin_index.clear()
