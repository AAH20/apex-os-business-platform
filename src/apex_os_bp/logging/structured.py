"""Structured logging with JSON output and context enrichment."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union


class LogLevel(Enum):
    """Standard log levels with numeric severity."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def from_name(cls, name: str) -> "LogLevel":
        """Get LogLevel from string name (case-insensitive)."""
        try:
            return cls[name.upper()]
        except KeyError:
            raise ValueError(f"Unknown log level: {name}")

    @classmethod
    def from_value(cls, value: int) -> "LogLevel":
        """Get LogLevel from numeric value."""
        for level in cls:
            if level.value == value:
                return level
        raise ValueError(f"Unknown log level value: {value}")


class LogEntry:
    """A single structured log entry."""

    def __init__(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        timestamp: Optional[datetime] = None,
        source: str = "",
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[BaseException] = None,
        trace_id: Optional[str] = None,
    ):
        self.message = message
        self.level = level
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.source = source
        self.context = context or {}
        self.exception = exception
        self.trace_id = trace_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to a dictionary."""
        data: Dict[str, Any] = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "level_value": self.level.value,
            "message": self.message,
            "source": self.source,
        }
        if self.context:
            data["context"] = self.context
        if self.trace_id:
            data["trace_id"] = self.trace_id
        if self.exception is not None:
            data["exception"] = {
                "type": type(self.exception).__name__,
                "message": str(self.exception),
            }
        return data

    def to_json(self) -> str:
        """Serialize entry to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogEntry":
        """Create LogEntry from a dictionary."""
        level = LogLevel.from_name(data.get("level", "INFO"))
        timestamp = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else None
        exc_info = data.get("exception")
        exception = None
        if exc_info:
            exception = Exception(exc_info.get("message", ""))
        return cls(
            message=data.get("message", ""),
            level=level,
            timestamp=timestamp,
            source=data.get("source", ""),
            context=data.get("context", {}),
            exception=exception,
            trace_id=data.get("trace_id"),
        )

    @classmethod
    def from_json(cls, line: str) -> "LogEntry":
        """Parse a JSON log line into a LogEntry."""
        return cls.from_dict(json.loads(line))

    def __repr__(self) -> str:
        return f"LogEntry({self.level.name}: {self.message})"


class StructuredLogger:
    """JSON-structured logger with context propagation and multiple outputs."""

    def __init__(
        self,
        name: str = "apex-os",
        level: LogLevel = LogLevel.INFO,
        outputs: Optional[List[Union[TextIO, Path, str]]] = None,
        default_context: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.level = level
        self.default_context = default_context or {}
        self._entries: List[LogEntry] = []
        self._outputs: List[TextIO] = []
        self._file_handles: List[TextIO] = []

        if outputs is None:
            outputs = [sys.stderr]

        for out in outputs:
            self.add_output(out)

    def add_output(self, output: Union[TextIO, Path, str]) -> None:
        """Add an output destination (file path or stream)."""
        if isinstance(output, (str, Path)):
            handle = open(output, "a", encoding="utf-8")
            self._file_handles.append(handle)
            self._outputs.append(handle)
        else:
            self._outputs.append(output)

    def close(self) -> None:
        """Close all file handles."""
        for handle in self._file_handles:
            handle.close()
        self._file_handles.clear()
        self._outputs.clear()

    def _should_log(self, level: LogLevel) -> bool:
        return level.value >= self.level.value

    def _emit(self, entry: LogEntry) -> None:
        """Write entry to all outputs and internal buffer."""
        self._entries.append(entry)
        line = entry.to_json()
        for out in self._outputs:
            try:
                out.write(line + "\n")
                out.flush()
            except Exception:
                pass

    def log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[BaseException] = None,
        trace_id: Optional[str] = None,
    ) -> LogEntry:
        """Create and emit a log entry."""
        if not self._should_log(level):
            return LogEntry(message, level, context=context)

        merged_context = {**self.default_context, **(context or {})}
        entry = LogEntry(
            message=message,
            level=level,
            source=self.name,
            context=merged_context,
            exception=exception,
            trace_id=trace_id,
        )
        self._emit(entry)
        return entry

    def debug(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log(message, LogLevel.DEBUG, **kwargs)

    def info(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log(message, LogLevel.INFO, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log(message, LogLevel.WARNING, **kwargs)

    def error(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log(message, LogLevel.ERROR, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log(message, LogLevel.CRITICAL, **kwargs)

    def exception(
        self, message: str, exc: Optional[BaseException] = None, **kwargs: Any
    ) -> LogEntry:
        """Log an exception with traceback context."""
        if exc is None:
            exc = sys.exc_info()[1]
        return self.log(message, LogLevel.ERROR, exception=exc, **kwargs)

    def bind(self, **context: Any) -> "StructuredLogger":
        """Create a new logger with additional default context."""
        merged = {**self.default_context, **context}
        new_logger = StructuredLogger(
            name=self.name,
            level=self.level,
            default_context=merged,
        )
        new_logger._outputs = self._outputs.copy()
        new_logger._file_handles = self._file_handles.copy()
        return new_logger

    def get_entries(self) -> List[LogEntry]:
        """Return all buffered entries."""
        return list(self._entries)

    def clear(self) -> None:
        """Clear the internal entry buffer."""
        self._entries.clear()

    def __enter__(self) -> "StructuredLogger":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
