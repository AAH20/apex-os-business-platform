"""KPI tracking module."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from collections import defaultdict


class KPIStatus(Enum):
    """KPI status levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    ON_TRACK = "on_track"
    EXCEEDING = "exceeding"


@dataclass
class KPI:
    """Key Performance Indicator data structure."""
    name: str
    value: float
    target: float
    unit: str
    category: str = "general"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    timestamp: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    @property
    def achievement_rate(self) -> float:
        """Calculate achievement rate as percentage."""
        if self.target == 0:
            return 0.0
        return (self.value / self.target) * 100.0

    @property
    def variance(self) -> float:
        """Calculate variance from target."""
        return self.value - self.target

    @property
    def variance_percent(self) -> float:
        """Calculate variance percentage from target."""
        if self.target == 0:
            return 0.0
        return ((self.value - self.target) / abs(self.target)) * 100.0

    @property
    def status(self) -> KPIStatus:
        """Determine KPI status based on achievement rate."""
        rate = self.achievement_rate
        if rate < 50:
            return KPIStatus.CRITICAL
        elif rate < 80:
            return KPIStatus.WARNING
        elif rate < 110:
            return KPIStatus.ON_TRACK
        else:
            return KPIStatus.EXCEEDING

    def to_dict(self) -> Dict:
        """Convert KPI to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "target": self.target,
            "unit": self.unit,
            "category": self.category,
            "description": self.description,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "achievement_rate": self.achievement_rate,
            "variance": self.variance,
            "variance_percent": self.variance_percent,
            "status": self.status.value,
        }


class KPITracker:
    """KPI tracking and management system."""

    def __init__(self):
        self._kpis: Dict[str, KPI] = {}
        self._history: Dict[str, List[KPI]] = defaultdict(list)

    def track(self, name: str, value: float, target: float, unit: str,
              category: str = "general", description: str = "",
              tags: Optional[List[str]] = None, **metadata) -> KPI:
        """Track a KPI measurement."""
        kpi = KPI(
            name=name,
            value=value,
            target=target,
            unit=unit,
            category=category,
            description=description,
            tags=tags or [],
            metadata=metadata,
        )
        self._kpis[kpi.id] = kpi
        self._history[name].append(kpi)
        return kpi

    def get(self, kpi_id: str) -> Optional[KPI]:
        """Get KPI by ID."""
        return self._kpis.get(kpi_id)

    def get_by_name(self, name: str) -> List[KPI]:
        """Get all KPI measurements by name."""
        return self._history.get(name, [])

    def get_latest(self, name: str) -> Optional[KPI]:
        """Get latest KPI measurement by name."""
        history = self._history.get(name, [])
        return history[-1] if history else None

    def get_all(self) -> List[KPI]:
        """Get all tracked KPIs."""
        return list(self._kpis.values())

    def get_by_category(self, category: str) -> List[KPI]:
        """Get KPIs filtered by category."""
        return [k for k in self._kpis.values() if k.category == category]

    def get_by_status(self, status: KPIStatus) -> List[KPI]:
        """Get KPIs filtered by status."""
        return [k for k in self._kpis.values() if k.status == status]

    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return list(set(k.category for k in self._kpis.values()))

    def get_trend(self, name: str, periods: int = 5) -> List[Dict]:
        """Get trend data for a KPI."""
        history = self._history.get(name, [])
        recent = history[-periods:] if len(history) > periods else history
        return [
            {
                "timestamp": k.timestamp,
                "value": k.value,
                "target": k.target,
                "achievement_rate": k.achievement_rate,
            }
            for k in recent
        ]

    def get_summary(self) -> Dict:
        """Get summary of all KPIs."""
        if not self._kpis:
            return {
                "total": 0,
                "by_status": {},
                "by_category": {},
                "overall_achievement": 0.0,
            }

        by_status = defaultdict(int)
        by_category = defaultdict(int)
        total_achievement = 0.0

        for kpi in self._kpis.values():
            by_status[kpi.status.value] += 1
            by_category[kpi.category] += 1
            total_achievement += kpi.achievement_rate

        return {
            "total": len(self._kpis),
            "by_status": dict(by_status),
            "by_category": dict(by_category),
            "overall_achievement": total_achievement / len(self._kpis),
        }

    def get_scorecard(self) -> Dict:
        """Get balanced scorecard view."""
        categories = self.get_categories()
        scorecard = {}
        for cat in categories:
            cat_kpis = self.get_by_category(cat)
            if cat_kpis:
                avg_achievement = sum(k.achievement_rate for k in cat_kpis) / len(cat_kpis)
                scorecard[cat] = {
                    "kpi_count": len(cat_kpis),
                    "average_achievement": avg_achievement,
                    "kpis": [k.to_dict() for k in cat_kpis],
                }
        return scorecard

    def clear(self) -> None:
        """Clear all tracked KPIs."""
        self._kpis.clear()
        self._history.clear()
