"""Event versioning: handle schema evolution of events."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable


class EventVersion(IntEnum):
    """Standard event version numbers."""

    V1 = 1
    V2 = 2
    V3 = 3


@dataclass
class VersionedEvent:
    """An event with version information."""

    event_type: str
    version: int
    payload: dict[str, Any]
    migrated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "version": self.version,
            "payload": self.payload,
            "migrated": self.migrated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VersionedEvent":
        return cls(**data)


class VersionMigrator:
    """Migrates events between schema versions.

    Maintains a registry of migration functions per event type.
    Migrations are applied sequentially from the source version
    to the target version.
    """

    def __init__(self) -> None:
        self._migrations: dict[str, dict[int, Callable[[dict[str, Any]], dict[str, Any]]]] = {}

    def register(
        self,
        event_type: str,
        from_version: int,
        migration: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> "VersionMigrator":
        """Register a migration function for an event type.

        Args:
            event_type: The event type name.
            from_version: The version this migration upgrades FROM.
            migration: Function that transforms the payload dict.

        Returns:
            Self for chaining.
        """
        if event_type not in self._migrations:
            self._migrations[event_type] = {}
        self._migrations[event_type][from_version] = migration
        return self

    def migrate(
        self,
        event_type: str,
        payload: dict[str, Any],
        from_version: int,
        to_version: int,
    ) -> VersionedEvent:
        """Migrate an event payload from one version to another.

        Args:
            event_type: The event type name.
            payload: The event payload dict.
            from_version: Current version of the payload.
            to_version: Target version to migrate to.

        Returns:
            VersionedEvent with the migrated payload.

        Raises:
            ValueError: If no migration path exists.
        """
        if from_version == to_version:
            return VersionedEvent(
                event_type=event_type,
                version=to_version,
                payload=payload,
                migrated=False,
            )

        if from_version > to_version:
            raise ValueError(
                f"Cannot downgrade {event_type!r} from v{from_version} to v{to_version}"
            )

        current_payload = dict(payload)
        current_version = from_version

        while current_version < to_version:
            next_version = current_version + 1
            migration_fn = self._migrations.get(event_type, {}).get(current_version)
            if migration_fn is None:
                raise ValueError(
                    f"No migration registered for {event_type!r} "
                    f"from v{current_version} to v{next_version}"
                )
            current_payload = migration_fn(current_payload)
            current_version = next_version

        return VersionedEvent(
            event_type=event_type,
            version=to_version,
            payload=current_payload,
            migrated=True,
        )

    def can_migrate(self, event_type: str, from_version: int, to_version: int) -> bool:
        """Check if a migration path exists."""
        if from_version == to_version:
            return True
        if from_version > to_version:
            return False

        current = from_version
        while current < to_version:
            if current not in self._migrations.get(event_type, {}):
                return False
            current += 1
        return True

    def get_registered_types(self) -> list[str]:
        """Get all event types with registered migrations."""
        return list(self._migrations.keys())

    def get_migration_path(self, event_type: str, from_version: int, to_version: int) -> list[int]:
        """Get the list of versions in the migration path."""
        if from_version > to_version:
            return []
        return list(range(from_version, to_version + 1))
