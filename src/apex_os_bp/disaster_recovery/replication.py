"""Data replication module — manages cross-region data replication."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReplicationType(str, Enum):
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    SEMI_SYNCHRONOUS = "semi_synchronous"


class ReplicationStatus(str, Enum):
    HEALTHY = "healthy"
    LAGGING = "lagging"
    DEGRADED = "degaged"
    BROKEN = "broken"
    UNKNOWN = "unknown"


@dataclass
class ReplicationLink:
    """Represents a replication link between two regions."""

    source_region: str
    target_region: str
    data_source: str
    replication_type: ReplicationType
    lag_seconds: float = 0.0
    last_sync: float | None = None
    bytes_replicated: int = 0
    status: ReplicationStatus = ReplicationStatus.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_region": self.source_region,
            "target_region": self.target_region,
            "data_source": self.data_source,
            "replication_type": self.replication_type.value,
            "lag_seconds": self.lag_seconds,
            "last_sync": self.last_sync,
            "bytes_replicated": self.bytes_replicated,
            "status": self.status.value,
            "metadata": dict(self.metadata),
        }


class ReplicationManager:
    """Manages data replication links across regions."""

    # Lag thresholds (seconds) for status determination
    LAGGING_THRESHOLD = 30.0
    DEGRADED_THRESHOLD = 300.0
    BROKEN_THRESHOLD = 3600.0

    def __init__(self) -> None:
        self._links: dict[str, ReplicationLink] = {}

    def _link_id(self, source: str, target: str, data_source: str) -> str:
        return f"{source}:{target}:{data_source}"

    def register_link(
        self,
        source_region: str,
        target_region: str,
        data_source: str,
        replication_type: ReplicationType = ReplicationType.ASYNCHRONOUS,
        metadata: dict[str, Any] | None = None,
    ) -> ReplicationLink:
        link = ReplicationLink(
            source_region=source_region,
            target_region=target_region,
            data_source=data_source,
            replication_type=replication_type,
            metadata=metadata or {},
        )
        link_id = self._link_id(source_region, target_region, data_source)
        self._links[link_id] = link
        return link

    def get_link(
        self, source_region: str, target_region: str, data_source: str
    ) -> ReplicationLink | None:
        link_id = self._link_id(source_region, target_region, data_source)
        return self._links.get(link_id)

    def list_links(self) -> list[ReplicationLink]:
        return list(self._links.values())

    def links_for_region(self, region: str) -> list[ReplicationLink]:
        return [
            link
            for link in self._links.values()
            if link.source_region == region or link.target_region == region
        ]

    def update_lag(
        self,
        source_region: str,
        target_region: str,
        data_source: str,
        lag_seconds: float,
        bytes_replicated: int | None = None,
    ) -> ReplicationStatus:
        """Update replication lag and return the computed status."""
        link = self.get_link(source_region, target_region, data_source)
        if link is None:
            raise ValueError(
                f"No replication link found for {source_region} -> {target_region}:{data_source}"
            )

        link.lag_seconds = lag_seconds
        link.last_sync = time.time()
        if bytes_replicated is not None:
            link.bytes_replicated = bytes_replicated

        link.status = self._compute_status(lag_seconds, link.replication_type)
        return link.status

    def _compute_status(
        self, lag_seconds: float, replication_type: ReplicationType
    ) -> ReplicationStatus:
        if replication_type == ReplicationType.SYNCHRONOUS:
            if lag_seconds > 0:
                return ReplicationStatus.DEGRADED
            return ReplicationStatus.HEALTHY

        if lag_seconds >= self.BROKEN_THRESHOLD:
            return ReplicationStatus.BROKEN
        if lag_seconds >= self.DEGRADED_THRESHOLD:
            return ReplicationStatus.DEGRADED
        if lag_seconds >= self.LAGGING_THRESHOLD:
            return ReplicationStatus.LAGGING
        return ReplicationStatus.HEALTHY

    def healthy_links(self) -> list[ReplicationLink]:
        return [l for l in self._links.values() if l.status == ReplicationStatus.HEALTHY]

    def unhealthy_links(self) -> list[ReplicationLink]:
        return [l for l in self._links.values() if l.status != ReplicationStatus.HEALTHY]

    def remove_link(
        self, source_region: str, target_region: str, data_source: str
    ) -> bool:
        link_id = self._link_id(source_region, target_region, data_source)
        if link_id in self._links:
            del self._links[link_id]
            return True
        return False

    def summary(self) -> dict[str, Any]:
        links = list(self._links.values())
        return {
            "total_links": len(links),
            "healthy": sum(1 for l in links if l.status == ReplicationStatus.HEALTHY),
            "lagging": sum(1 for l in links if l.status == ReplicationStatus.LAGGING),
            "degraded": sum(1 for l in links if l.status == ReplicationStatus.DEGRADED),
            "broken": sum(1 for l in links if l.status == ReplicationStatus.BROKEN),
            "unknown": sum(1 for l in links if l.status == ReplicationStatus.UNKNOWN),
        }
