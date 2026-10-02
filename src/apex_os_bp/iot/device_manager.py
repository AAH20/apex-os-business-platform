"""Device management module for the IoT platform.

Handles device registration, status tracking, metadata management,
and device lifecycle operations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DeviceStatus(str, Enum):
    """Possible states for an IoT device."""

    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    DECOMMISSIONED = "decommissioned"


class DeviceType(str, Enum):
    """Supported IoT device types."""

    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    CAMERA = "camera"
    THERMOSTAT = "thermostat"
    SMART_METER = "smart_meter"
    WEARABLE = "wearable"
    INDUSTRIAL = "industrial"
    OTHER = "other"


@dataclass
class Device:
    """Represents a registered IoT device.

    Attributes:
        device_id: Unique identifier for the device.
        name: Human-readable device name.
        device_type: Category of the device.
        status: Current operational status.
        location: Physical or logical location.
        firmware_version: Installed firmware version.
        metadata: Arbitrary key-value metadata.
        tags: List of string tags for grouping/filtering.
        created_at: Registration timestamp.
        last_seen_at: Last communication timestamp.
        is_active: Whether the device is active (not decommissioned).
    """

    device_id: str
    name: str
    device_type: DeviceType
    status: DeviceStatus = DeviceStatus.OFFLINE
    location: str = ""
    firmware_version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime | None = None
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize device to a dictionary."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type.value,
            "status": self.status.value,
            "location": self.location,
            "firmware_version": self.firmware_version,
            "metadata": dict(self.metadata),
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        """Deserialize a device from a dictionary."""
        return cls(
            device_id=data["device_id"],
            name=data["name"],
            device_type=DeviceType(data["device_type"]),
            status=DeviceStatus(data.get("status", "offline")),
            location=data.get("location", ""),
            firmware_version=data.get("firmware_version", "1.0.0"),
            metadata=dict(data.get("metadata", {})),
            tags=list(data.get("tags", [])),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
            last_seen_at=datetime.fromisoformat(data["last_seen_at"]) if data.get("last_seen_at") else None,
            is_active=data.get("is_active", True),
        )


class DeviceManager:
    """Manages the lifecycle of IoT devices.

    Provides methods to register, update, query, and deregister devices.
    All devices are stored in memory keyed by their unique device_id.
    """

    def __init__(self) -> None:
        """Initialize an empty device registry."""
        self._devices: dict[str, Device] = {}

    def register_device(
        self,
        name: str,
        device_type: DeviceType | str,
        location: str = "",
        firmware_version: str = "1.0.0",
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        device_id: str | None = None,
    ) -> Device:
        """Register a new device.

        Args:
            name: Human-readable device name.
            device_type: Type of device (DeviceType enum or string).
            location: Physical/logical location.
            firmware_version: Firmware version string.
            metadata: Arbitrary metadata dictionary.
            tags: List of tags for grouping.
            device_id: Optional explicit ID (auto-generated if None).

        Returns:
            The newly created Device instance.

        Raises:
            ValueError: If a device with the same ID already exists.
        """
        if isinstance(device_type, str):
            device_type = DeviceType(device_type)

        dev_id = device_id or str(uuid.uuid4())
        if dev_id in self._devices:
            raise ValueError(f"Device with ID '{dev_id}' already exists")

        device = Device(
            device_id=dev_id,
            name=name,
            device_type=device_type,
            location=location,
            firmware_version=firmware_version,
            metadata=metadata or {},
            tags=tags or [],
        )
        self._devices[dev_id] = device
        return device

    def get_device(self, device_id: str) -> Device:
        """Retrieve a device by its ID.

        Args:
            device_id: The unique device identifier.

        Returns:
            The Device instance.

        Raises:
            KeyError: If no device with the given ID exists.
        """
        if device_id not in self._devices:
            raise KeyError(f"Device '{device_id}' not found")
        return self._devices[device_id]

    def get_all_devices(self) -> list[Device]:
        """Return all registered devices."""
        return list(self._devices.values())

    def update_device(self, device_id: str, **kwargs: Any) -> Device:
        """Update device attributes.

        Args:
            device_id: The device to update.
            **kwargs: Attributes to update (name, location, firmware_version, etc.).

        Returns:
            The updated Device.

        Raises:
            KeyError: If the device does not exist.
            AttributeError: If an invalid attribute is provided.
        """
        device = self.get_device(device_id)
        valid_fields = {
            "name", "location", "firmware_version", "metadata",
            "tags", "status", "is_active",
        }
        for key, value in kwargs.items():
            if key not in valid_fields:
                raise AttributeError(f"Cannot update unknown field '{key}'")
            if key == "status":
                if isinstance(value, str):
                    value = DeviceStatus(value)
                device.status = value
            else:
                setattr(device, key, value)
        return device

    def update_status(self, device_id: str, status: DeviceStatus | str) -> Device:
        """Update the status of a device.

        Args:
            device_id: The device to update.
            status: New status value.

        Returns:
            The updated Device.
        """
        if isinstance(status, str):
            status = DeviceStatus(status)
        return self.update_device(device_id, status=status)

    def update_last_seen(self, device_id: str, timestamp: datetime | None = None) -> Device:
        """Update the last_seen timestamp for a device.

        Args:
            device_id: The device to update.
            timestamp: Timestamp to set (defaults to now).

        Returns:
            The updated Device.
        """
        ts = timestamp or datetime.now(timezone.utc)
        device = self.get_device(device_id)
        device.last_seen_at = ts
        return device

    def deregister_device(self, device_id: str) -> Device:
        """Deregister (decommission) a device.

        The device is marked as decommissioned and inactive but retained
        in the registry for historical reference.

        Args:
            device_id: The device to deregister.

        Returns:
            The deregistered Device.
        """
        device = self.get_device(device_id)
        device.is_active = False
        device.status = DeviceStatus.DECOMMISSIONED
        return device

    def remove_device(self, device_id: str) -> None:
        """Permanently remove a device from the registry.

        Args:
            device_id: The device to remove.

        Raises:
            KeyError: If the device does not exist.
        """
        if device_id not in self._devices:
            raise KeyError(f"Device '{device_id}' not found")
        del self._devices[device_id]

    def list_devices(
        self,
        status: DeviceStatus | str | None = None,
        device_type: DeviceType | str | None = None,
        location: str | None = None,
        tag: str | None = None,
        active_only: bool = True,
    ) -> list[Device]:
        """List devices with optional filtering.

        Args:
            status: Filter by status.
            device_type: Filter by device type.
            location: Filter by location (exact match).
            tag: Filter by tag.
            active_only: If True, exclude decommissioned devices.

        Returns:
            List of matching devices.
        """
        results = list(self._devices.values())

        if active_only:
            results = [d for d in results if d.is_active]
        if status is not None:
            if isinstance(status, str):
                status = DeviceStatus(status)
            results = [d for d in results if d.status == status]
        if device_type is not None:
            if isinstance(device_type, str):
                device_type = DeviceType(device_type)
            results = [d for d in results if d.device_type == device_type]
        if location is not None:
            results = [d for d in results if d.location == location]
        if tag is not None:
            results = [d for d in results if tag in d.tags]

        return results

    def search_by_name(self, query: str) -> list[Device]:
        """Search devices by name (case-insensitive substring match).

        Args:
            query: Search string.

        Returns:
            List of devices whose name contains the query.
        """
        q = query.lower()
        return [d for d in self._devices.values() if q in d.name.lower()]

    def get_device_count(self, active_only: bool = True) -> int:
        """Return the number of registered devices.

        Args:
            active_only: If True, count only active devices.

        Returns:
            Device count.
        """
        if active_only:
            return sum(1 for d in self._devices.values() if d.is_active)
        return len(self._devices)

    def get_devices_by_tag(self, tag: str) -> list[Device]:
        """Get all devices with a specific tag.

        Args:
            tag: The tag to filter by.

        Returns:
            List of devices with the given tag.
        """
        return [d for d in self._devices.values() if tag in d.tags]

    def add_tag(self, device_id: str, tag: str) -> Device:
        """Add a tag to a device.

        Args:
            device_id: The device to tag.
            tag: The tag to add.

        Returns:
            The updated Device.
        """
        device = self.get_device(device_id)
        if tag not in device.tags:
            device.tags.append(tag)
        return device

    def remove_tag(self, device_id: str, tag: str) -> Device:
        """Remove a tag from a device.

        Args:
            device_id: The device.
            tag: The tag to remove.

        Returns:
            The updated Device.
        """
        device = self.get_device(device_id)
        if tag in device.tags:
            device.tags.remove(tag)
        return device

    def clear(self) -> None:
        """Remove all devices from the registry."""
        self._devices.clear()
