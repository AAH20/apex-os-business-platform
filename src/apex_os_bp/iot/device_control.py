"""Device control module for the IoT platform.

Manages sending commands to IoT devices, tracking command status,
and maintaining command history.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class CommandStatus(str, Enum):
    """Lifecycle states for a device command."""

    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


_TERMINAL_STATUSES: set[CommandStatus] = {
    CommandStatus.COMPLETED,
    CommandStatus.FAILED,
    CommandStatus.TIMED_OUT,
    CommandStatus.CANCELLED,
}


@dataclass
class Command:
    """Represents a command to be sent to an IoT device.

    Attributes:
        device_id: Target device ID.
        command_type: Type of command (e.g., 'reboot', 'set_threshold').
        parameters: Command parameters.
        command_id: Unique command identifier.
        status: Current command status.
        created_at: When the command was created.
        sent_at: When the command was sent to the device.
        completed_at: When the command reached a terminal state.
        result: Result data from the device.
        error_message: Error description if failed.
        priority: Command priority (1=highest, 5=lowest).
        timeout_seconds: Maximum time to wait for completion.
        callback: Optional callback function for status changes.
    """

    device_id: str
    command_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: CommandStatus = CommandStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None
    priority: int = 3
    timeout_seconds: float = 30.0
    callback: Callable[["Command"], None] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize command to a dictionary."""
        return {
            "command_id": self.command_id,
            "device_id": self.device_id,
            "command_type": self.command_type,
            "parameters": dict(self.parameters),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": dict(self.result) if self.result else None,
            "error_message": self.error_message,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
        }

    @property
    def is_terminal(self) -> bool:
        """Whether the command has reached a terminal state."""
        return self.status in {
            CommandStatus.COMPLETED,
            CommandStatus.FAILED,
            CommandStatus.TIMED_OUT,
            CommandStatus.CANCELLED,
        }

    @property
    def duration_seconds(self) -> float | None:
        """Duration from creation to completion, if completed."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.created_at).total_seconds()


@dataclass
class CommandResult:
    """Result of a command execution.

    Attributes:
        command_id: ID of the command.
        success: Whether the command succeeded.
        status: Final command status.
        result_data: Data returned by the device.
        error_message: Error description if failed.
        execution_time_seconds: Time taken to execute.
    """

    command_id: str
    success: bool
    status: CommandStatus
    result_data: dict[str, Any] | None = None
    error_message: str | None = None
    execution_time_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to a dictionary."""
        return {
            "command_id": self.command_id,
            "success": self.success,
            "status": self.status.value,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "execution_time_seconds": self.execution_time_seconds,
        }


class DeviceController:
    """Sends commands to IoT devices and tracks their lifecycle.

    Provides command queuing, dispatch, status tracking, and history.
    Supports both synchronous and asynchronous command patterns.
    """

    # Valid command types
    VALID_COMMANDS: set[str] = {
        "reboot",
        "shutdown",
        "restart_service",
        "update_firmware",
        "set_threshold",
        "set_interval",
        "set_mode",
        "calibrate",
        "reset",
        "toggle_power",
        "set_led",
        "set_buzzer",
        "request_status",
        "request_diagnostics",
        "custom",
    }

    def __init__(self) -> None:
        """Initialize the device controller."""
        self._commands: dict[str, Command] = {}
        self._command_history: list[str] = []
        self._pending_queue: list[str] = []
        self._device_commands: dict[str, list[str]] = {}

    def send_command(
        self,
        device_id: str,
        command_type: str,
        parameters: dict[str, Any] | None = None,
        priority: int = 3,
        timeout_seconds: float = 30.0,
        callback: Callable[[Command], None] | None = None,
    ) -> Command:
        """Send a command to a device.

        Args:
            device_id: Target device.
            command_type: Type of command.
            parameters: Command parameters.
            priority: Priority (1=highest, 5=lowest).
            timeout_seconds: Timeout in seconds.
            callback: Optional status change callback.

        Returns:
            The created Command instance.

        Raises:
            ValueError: If command_type is invalid or priority out of range.
        """
        if command_type not in self.VALID_COMMANDS:
            raise ValueError(
                f"Invalid command type '{command_type}'. "
                f"Valid types: {sorted(self.VALID_COMMANDS)}"
            )
        if not 1 <= priority <= 5:
            raise ValueError("Priority must be between 1 and 5")

        command = Command(
            device_id=device_id,
            command_type=command_type,
            parameters=parameters or {},
            priority=priority,
            timeout_seconds=timeout_seconds,
            callback=callback,
        )
        self._commands[command.command_id] = command
        self._command_history.append(command.command_id)
        self._pending_queue.append(command.command_id)

        # Index by device
        if device_id not in self._device_commands:
            self._device_commands[device_id] = []
        self._device_commands[device_id].append(command.command_id)

        return command

    def get_command(self, command_id: str) -> Command:
        """Retrieve a command by ID.

        Args:
            command_id: The command identifier.

        Returns:
            The Command instance.

        Raises:
            KeyError: If the command does not exist.
        """
        if command_id not in self._commands:
            raise KeyError(f"Command '{command_id}' not found")
        return self._commands[command_id]

    def update_status(
        self,
        command_id: str,
        status: CommandStatus | str,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> Command:
        """Update the status of a command.

        Args:
            command_id: The command to update.
            status: New status.
            result: Optional result data.
            error_message: Optional error message.

        Returns:
            The updated Command.
        """
        if isinstance(status, str):
            status = CommandStatus(status)

        command = self.get_command(command_id)
        old_status = command.status
        command.status = status

        if status == CommandStatus.SENT and command.sent_at is None:
            command.sent_at = datetime.now(timezone.utc)

        if status in _TERMINAL_STATUSES:
            command.completed_at = datetime.now(timezone.utc)
            if command.command_id in self._pending_queue:
                self._pending_queue.remove(command.command_id)

        if result is not None:
            command.result = result
        if error_message is not None:
            command.error_message = error_message

        # Invoke callback if set
        if command.callback and old_status != status:
            command.callback(command)

        return command

    def acknowledge(self, command_id: str) -> Command:
        """Mark a command as acknowledged by the device."""
        return self.update_status(command_id, CommandStatus.ACKNOWLEDGED)

    def complete(
        self,
        command_id: str,
        result: dict[str, Any] | None = None,
    ) -> Command:
        """Mark a command as completed."""
        return self.update_status(command_id, CommandStatus.COMPLETED, result=result)

    def fail(self, command_id: str, error_message: str) -> Command:
        """Mark a command as failed."""
        return self.update_status(command_id, CommandStatus.FAILED, error_message=error_message)

    def cancel(self, command_id: str) -> Command:
        """Cancel a pending command.

        Raises:
            ValueError: If the command is already in a terminal state.
        """
        command = self.get_command(command_id)
        if command.is_terminal:
            raise ValueError(f"Cannot cancel command in state '{command.status.value}'")
        return self.update_status(command_id, CommandStatus.CANCELLED)

    def get_pending_commands(self) -> list[Command]:
        """Get all pending commands sorted by priority."""
        pending = [self._commands[cid] for cid in self._pending_queue]
        return sorted(pending, key=lambda c: (c.priority, c.created_at))

    def get_command_history(
        self,
        device_id: str | None = None,
        status: CommandStatus | str | None = None,
        limit: int | None = None,
    ) -> list[Command]:
        """Get command history with optional filters.

        Args:
            device_id: Filter by device.
            status: Filter by status.
            limit: Maximum number of commands to return.

        Returns:
            List of Command objects.
        """
        if device_id is not None:
            cmd_ids = self._device_commands.get(device_id, [])
            commands = [self._commands[cid] for cid in cmd_ids]
        else:
            commands = list(self._commands.values())

        if status is not None:
            if isinstance(status, str):
                status = CommandStatus(status)
            commands = [c for c in commands if c.status == status]

        # Sort by creation time descending
        commands.sort(key=lambda c: c.created_at, reverse=True)

        if limit is not None:
            commands = commands[:limit]

        return commands

    def get_device_commands(self, device_id: str) -> list[Command]:
        """Get all commands for a specific device."""
        return self.get_command_history(device_id=device_id)

    def get_command_count(self, status: CommandStatus | str | None = None) -> int:
        """Get the count of commands, optionally filtered by status.

        Args:
            status: Optional status filter.

        Returns:
            Command count.
        """
        if status is None:
            return len(self._commands)
        if isinstance(status, str):
            status = CommandStatus(status)
        return sum(1 for c in self._commands.values() if c.status == status)

    def clear_history(self) -> None:
        """Clear all command history."""
        self._commands.clear()
        self._command_history.clear()
        self._pending_queue.clear()
        self._device_commands.clear()

    def process_next_pending(self) -> Command | None:
        """Get the next pending command to process (highest priority).

        Returns:
            The next Command to process, or None if no pending commands.
        """
        pending = self.get_pending_commands()
        return pending[0] if pending else None
