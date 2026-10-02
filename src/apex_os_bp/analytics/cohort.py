"""Cohort analysis.

Groups users into cohorts by the period of their first observed event
(typically signup) and computes how many members of each cohort remain
active in each subsequent period — the classic retention matrix.

Input events are :class:`CohortEvent` records with a ``user_id``, an
ISO-8601 ``timestamp`` and an ``event`` name. The cohort key is the
period of the user's *first* event; retention in period *k* is the
fraction of the cohort with at least one event in that period.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from datetime import datetime


@dataclass
class CohortEvent:
    """A single user event used for cohort analysis."""

    user_id: str
    timestamp: str
    event: str = "active"

    def period(self, granularity: str = "month") -> str:
        """Return the period bucket (e.g. ``2026-01``) for this event."""
        dt = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        return _period_key(dt, granularity)


@dataclass
class Cohort:
    """A single cohort with its retention vector."""

    key: str
    size: int
    retention: List[float] = field(default_factory=list)

    @property
    def average_retention(self) -> float:
        if not self.retention:
            return 0.0
        return sum(self.retention) / len(self.retention)

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "size": self.size,
            "retention": self.retention,
            "average_retention": self.average_retention,
        }


def _period_key(dt: datetime, granularity: str) -> str:
    """Bucket a datetime into a period string."""
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    if granularity == "week":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if granularity == "month":
        return dt.strftime("%Y-%m")
    if granularity == "quarter":
        quarter = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{quarter}"
    if granularity == "year":
        return dt.strftime("%Y")
    raise ValueError(
        "granularity must be one of {'day', 'week', 'month', 'quarter', 'year'}"
    )


def _period_index(key: str, granularity: str) -> Tuple:
    """Return a sortable index for a period key."""
    if granularity == "month":
        year, month = key.split("-")
        return (int(year), int(month))
    if granularity == "day":
        year, month, day = key.split("-")
        return (int(year), int(month), int(day))
    if granularity == "week":
        year, week = key.split("-W")
        return (int(year), int(week))
    if granularity == "quarter":
        year, q = key.split("-Q")
        return (int(year), int(q))
    if granularity == "year":
        return (int(key),)
    return (key,)


def _shift_period(key: str, granularity: str, delta: int) -> str:
    """Return the period key *delta* periods after *key*."""
    idx = _period_index(key, granularity)
    if granularity == "month":
        year, month = idx
        total = year * 12 + (month - 1) + delta
        return f"{total // 12:04d}-{total % 12 + 1:02d}"
    if granularity == "day":
        dt = datetime.strptime(key, "%Y-%m-%d")
        from datetime import timedelta

        dt = dt + timedelta(days=delta)
        return dt.strftime("%Y-%m-%d")
    if granularity == "week":
        year, week = idx
        dt = datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u")
        from datetime import timedelta

        dt = dt + timedelta(weeks=delta)
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if granularity == "quarter":
        year, q = idx
        total = year * 4 + (q - 1) + delta
        return f"{total // 4:04d}-Q{total % 4 + 1}"
    if granularity == "year":
        return str(idx[0] + delta)
    raise ValueError(f"unsupported granularity: {granularity}")


class CohortAnalysis:
    """Build a retention matrix from a stream of user events."""

    def __init__(
        self,
        events: Sequence[CohortEvent],
        granularity: str = "month",
    ):
        if granularity not in {"day", "week", "month", "quarter", "year"}:
            raise ValueError("invalid granularity")
        self.events = list(events)
        self.granularity = granularity
        self._cohorts: Optional[List[Cohort]] = None

    def _build(self) -> List[Cohort]:
        if self._cohorts is not None:
            return self._cohorts

        # First period per user defines their cohort.
        first_period: Dict[str, str] = {}
        # (user_id, period) -> set of events
        activity: Dict[Tuple[str, str], set] = {}

        for ev in self.events:
            period = ev.period(self.granularity)
            uid = ev.user_id
            if uid not in first_period or period < first_period[uid]:
                first_period[uid] = period
            activity.setdefault((uid, period), set()).add(ev.event)

        # Group users by cohort.
        cohort_users: Dict[str, set] = {}
        for uid, period in first_period.items():
            cohort_users.setdefault(period, set()).add(uid)

        # Determine the global period range.
        all_periods = sorted(
            {p for (_, p) in activity.keys()},
            key=lambda p: _period_index(p, self.granularity),
        )
        if not all_periods:
            self._cohorts = []
            return self._cohorts

        first_all = all_periods[0]
        last_all = all_periods[-1]
        n_periods = 0
        cursor = first_all
        while _period_index(cursor, self.granularity) <= _period_index(
            last_all, self.granularity
        ):
            n_periods += 1
            cursor = _shift_period(cursor, self.granularity, 1)

        cohorts: List[Cohort] = []
        for key in sorted(
            cohort_users.keys(), key=lambda k: _period_index(k, self.granularity)
        ):
            users = cohort_users[key]
            size = len(users)
            retention: List[float] = []
            for k in range(n_periods):
                period = _shift_period(key, self.granularity, k)
                active = sum(
                    1 for u in users if (u, period) in activity
                )
                retention.append(active / size if size else 0.0)
            cohorts.append(Cohort(key=key, size=size, retention=retention))

        self._cohorts = cohorts
        return cohorts

    @property
    def cohorts(self) -> List[Cohort]:
        """Return the list of cohorts (built lazily)."""
        return self._build()

    def retention_matrix(self) -> Dict:
        """Return the full retention matrix as a dict."""
        cohorts = self._build()
        if not cohorts:
            return {"granularity": self.granularity, "cohorts": [], "periods": 0}
        return {
            "granularity": self.granularity,
            "periods": len(cohorts[0].retention),
            "cohorts": [c.to_dict() for c in cohorts],
        }

    def average_retention(self) -> List[float]:
        """Return the average retention per period index across cohorts."""
        cohorts = self._build()
        if not cohorts:
            return []
        n = len(cohorts[0].retention)
        out: List[float] = []
        for k in range(n):
            vals = [c.retention[k] for c in cohorts if len(c.retention) > k]
            out.append(sum(vals) / len(vals) if vals else 0.0)
        return out

    def summary(self) -> Dict:
        """Return a compact summary of the cohort analysis."""
        matrix = self.retention_matrix()
        avg = self.average_retention()
        return {
            "granularity": self.granularity,
            "cohort_count": len(matrix["cohorts"]),
            "total_users": sum(c["size"] for c in matrix["cohorts"]),
            "average_retention": avg,
            "matrix": matrix,
        }
