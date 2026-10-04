"""Funnel analysis.

Tracks how users progress through an ordered sequence of steps and
computes per-step conversion and drop-off. A user counts toward a step
the first time they reach it; reaching step *k* implies the user also
counted toward all earlier steps (funnels are cumulative by default).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class FunnelStep:
    """Computed metrics for a single funnel step."""

    name: str
    count: int
    conversion_from_previous: float
    conversion_from_top: float
    dropoff_from_previous: float
    dropoff_count: int

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "count": self.count,
            "conversion_from_previous": self.conversion_from_previous,
            "conversion_from_top": self.conversion_from_top,
            "dropoff_from_previous": self.dropoff_from_previous,
            "dropoff_count": self.dropoff_count,
        }


@dataclass
class FunnelEvent:
    """A single user reaching a funnel step."""

    user_id: str
    step: str
    timestamp: Optional[str] = None


class Funnel:
    """An ordered funnel with per-step conversion metrics."""

    def __init__(self, name: str, steps: Sequence[str]):
        if not steps:
            raise ValueError("steps must not be empty")
        if len(set(steps)) != len(steps):
            raise ValueError("step names must be unique")
        self.name = name
        self.steps = list(steps)
        self._events: List[FunnelEvent] = []
        self._computed: Optional[List[FunnelStep]] = None

    def add_event(self, user_id: str, step: str, timestamp: Optional[str] = None) -> None:
        """Record that *user_id* reached *step*."""
        if step not in self.steps:
            raise ValueError(f"unknown step: {step}")
        self._events.append(FunnelEvent(user_id=user_id, step=step, timestamp=timestamp))
        self._computed = None

    def add_events(self, events: Sequence[FunnelEvent]) -> None:
        """Bulk-add events."""
        for ev in events:
            self.add_event(ev.user_id, ev.step, ev.timestamp)

    def _compute(self) -> List[FunnelStep]:
        if self._computed is not None:
            return self._computed

        # Highest step index reached per user.
        user_max_step: Dict[str, int] = {}
        for ev in self._events:
            idx = self.steps.index(ev.step)
            if ev.user_id not in user_max_step or idx > user_max_step[ev.user_id]:
                user_max_step[ev.user_id] = idx

        # Cumulative counts: reaching step k implies reaching all k' <= k.
        counts = [0] * len(self.steps)
        for idx in user_max_step.values():
            for k in range(idx + 1):
                counts[k] += 1

        top = counts[0] if counts[0] > 0 else 1
        steps: List[FunnelStep] = []
        for i, name in enumerate(self.steps):
            count = counts[i]
            prev_count = counts[i - 1] if i > 0 else count
            conv_prev = count / prev_count if prev_count > 0 else 0.0
            conv_top = count / top
            dropoff = 1.0 - conv_prev
            dropoff_count = prev_count - count
            steps.append(
                FunnelStep(
                    name=name,
                    count=count,
                    conversion_from_previous=conv_prev,
                    conversion_from_top=conv_top,
                    dropoff_from_previous=dropoff,
                    dropoff_count=dropoff_count,
                )
            )
        self._computed = steps
        return steps

    @property
    def computed_steps(self) -> List[FunnelStep]:
        """Return the computed per-step metrics."""
        return self._compute()

    @property
    def overall_conversion(self) -> float:
        """Fraction of users who complete the entire funnel."""
        steps = self._compute()
        if not steps:
            return 0.0
        top = steps[0].count
        if top == 0:
            return 0.0
        return steps[-1].count / top

    @property
    def biggest_dropoff(self) -> Optional[FunnelStep]:
        """Return the step with the largest drop-off from the previous step."""
        steps = self._compute()
        if len(steps) < 2 or steps[0].count == 0:
            return None
        return max(steps[1:], key=lambda s: s.dropoff_from_previous)

    def summary(self) -> Dict:
        """Return a JSON-serialisable funnel summary."""
        steps = self._compute()
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in steps],
            "overall_conversion": self.overall_conversion,
            "biggest_dropoff": (
                self.biggest_dropoff.to_dict() if self.biggest_dropoff else None
            ),
        }


def funnel_from_events(
    name: str,
    steps: Sequence[str],
    events: Sequence[Tuple[str, str]],
) -> Funnel:
    """Build a pre-populated :class:`Funnel` from ``(user_id, step)`` tuples."""
    funnel = Funnel(name=name, steps=steps)
    for user_id, step in events:
        funnel.add_event(user_id, step)
    return funnel
