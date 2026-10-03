"""Deepened logging: structured JSON, dynamic levels, sampling, correlation, retention."""

from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Structured JSON Formatter
# ---------------------------------------------------------------------------

class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON with standard fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process,
        }
        # Merge extra structured fields
        if hasattr(record, "extra"):
            payload.update(record.extra)
        # Attach trace/correlation IDs
        if hasattr(record, "trace_id"):
            payload["trace_id"] = record.trace_id
        if hasattr(record, "span_id"):
            payload["span_id"] = record.span_id
        # Attach exception info
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Dynamic Log Level Manager
# ---------------------------------------------------------------------------

class DynamicLevelManager:
    """Allows runtime adjustment of log levels per logger or globally."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._overrides: Dict[str, int] = {}

    def set_level(self, logger_name: str, level: int | str) -> None:
        with self._lock:
            lvl = level if isinstance(level, int) else logging.getLevelName(level.upper())
            self._overrides[logger_name] = lvl
            logging.getLogger(loggerName).setLevel(lvl)

    def get_level(self, logger_name: str) -> int:
        with self._lock:
            return self._overrides.get(logger_name, logging.getLogger(loggerName).level)

    def reset(self, logger_name: str) -> None:
        with self._lock:
            self._overrides.pop(logger_name, None)
            logging.getLogger(logger_name).setLevel(logging.NOTSET)

    def set_global_level(self, level: int | str) -> None:
        self.set_level("", level)


# ---------------------------------------------------------------------------
# Sampling & Rate Limiting
# ---------------------------------------------------------------------------

@dataclass
class SamplingConfig:
    """Configuration for log sampling and rate limiting."""
    sample_rate: float = 1.0          # 0.0–1.0 fraction of logs to keep
    rate_limit_per_sec: int = 0       # 0 = unlimited
    burst_size: int = 100             # token bucket burst
    per_logger: bool = True           # apply rate limit per-logger


class TokenBucket:
    """Thread-safe token bucket for rate limiting."""

    def __init__(self, rate: float, capacity: int) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last_refill = now
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False


class SamplingFilter(logging.Filter):
    """Filters log records based on sample rate and token-bucket rate limiting."""

    def __init__(self, config: SamplingConfig) -> None:
        super().__init__()
        self._config = config
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def filter(self, record: logging.LogRecord) -> bool:
        # Sampling check
        if self._config.sample_rate < 1.0:
            if random.random() > self._config.sample_rate:
                return False
        # Rate limiting check
        if self._config.rate_limit_per_sec > 0:
            key = record.name if self._config.per_logger else "__global__"
            with self._lock:
                if key not in self._buckets:
                    self._buckets[key] = TokenBucket(
                        rate=self._config.rate_limit_per_sec,
                        capacity=self._config.burst_size,
                    )
                if not self._buckets[key].consume():
                    return False
        return True


# ---------------------------------------------------------------------------
# Trace / Correlation ID Support
# ---------------------------------------------------------------------------

class CorrelationContext:
    """Thread-local storage for trace and span IDs."""

    _local = threading.local()

    @classmethod
    def get_trace_id(cls) -> str:
        if not hasattr(cls._local, "trace_id"):
            cls._local.trace_id = uuid.uuid4().hex[:16]
        return cls._local.trace_id

    @classmethod
    def set_trace_id(cls, trace_id: str) -> None:
        cls._local.trace_id = trace_id

    @classmethod
    def clear(cls) -> None:
        cls._local = threading.local()


class CorrelationFilter(logging.Filter):
    """Injects trace_id and span_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = CorrelationContext.get_trace_id()
        record.span_id = uuid.uuid4().hex[:8]
        return True


# ---------------------------------------------------------------------------
# Retention & Archival
# ---------------------------------------------------------------------------

@dataclass
class RetentionPolicy:
    """Defines log retention and archival rules."""
    max_file_size_mb: int = 50
    max_age_days: int = 30
    archive_dir: str = "archives"
    compress_archives: bool = True
    max_archive_count: int = 10


class RetentionHandler(logging.Handler):
    """Handles log archival based on retention policy."""

    def __init__(self, log_dir: str, policy: RetentionPolicy) -> None:
        super().__init__()
        self._log_dir = Path(log_dir)
        self._policy = policy
        self._archive_path = self._log_dir / policy.archive_dir
        self._archive_path.mkdir(parents=True, exist_ok=True)
        self._current_size = 0
        self._current_file: Optional[Path] = None
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        with self._lock:
            self._rotate_if_needed()
            if self._current_file:
                with open(self._current_file, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
                self._current_size += len(msg) + 1

    def _rotate_if_needed(self) -> None:
        max_bytes = self._policy.max_file_size_mb * 1024 * 1024
        if self._current_file and self._current_size >= max_bytes:
            self._archive_current()
            self._current_size = 0
            self._current_file = None
        if self._current_file is None:
            self._current_file = self._log_dir / f"app_{int(time.time())}.log"

    def _archive_current(self) -> None:
        if not self._current_file or not self._current_file.exists():
            return
        import gzip
        import shutil
        ts = int(time.time())
        archive_name = f"app_{ts}.log"
        if self._policy.compress_archives:
            archive_name += ".gz"
            with open(self._current_file, "rb") as f_in:
                with gzip.open(self._archive_path / archive_name, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(self._current_file, self._archive_path / archive_name)
        self._current_file.unlink()
        self._cleanup_old_archives()

    def _cleanup_old_archives(self) -> None:
        cutoff = time.time() - (self._policy.max_age_days * 86400)
        archives = sorted(self._archive_path.iterdir(), key=lambda p: p.stat().st_mtime)
        for old in archives:
            if old.stat().st_mtime < cutoff:
                old.unlink()
        # Enforce max archive count
        remaining = sorted(self._archive_path.iterdir(), key=lambda p: p.stat().st_mtime)
        while len(remaining) > self._policy.max_archive_count:
            remaining.pop(0).unlink()


# ---------------------------------------------------------------------------
# Convenience: Deepened Logger Factory
# ---------------------------------------------------------------------------

def create_deepened_logger(
    name: str,
    log_dir: str = "logs",
    level: int | str = "INFO",
    sample_rate: float = 1.0,
    rate_limit_per_sec: int = 0,
    retention: Optional[RetentionPolicy] = None,
) -> logging.Logger:
    """Creates a fully configured deepened logger with all features enabled."""
    logger = logging.getLogger(name)
    logger.setLevel(level if isinstance(level, int) else logging.getLevelName(level.upper()))
    logger.handlers.clear()

    # Console handler with structured JSON
    console = logging.StreamHandler()
    console.setFormatter(StructuredJSONFormatter())
    logger.addHandler(console)

    # File handler with retention
    policy = retention or RetentionPolicy()
    file_handler = RetentionHandler(log_dir, policy)
    file_handler.setFormatter(StructuredJSONFormatter())
    logger.addHandler(file_handler)

    # Sampling filter
    sampling = SamplingFilter(SamplingConfig(
        sample_rate=sample_rate,
        rate_limit_per_sec=rate_limit_per_sec,
    ))
    logger.addFilter(sampling)

    # Correlation filter
    logger.addFilter(CorrelationFilter())

    return logger


# ---------------------------------------------------------------------------
# Module-level defaults
# ---------------------------------------------------------------------------

level_manager = DynamicLevelManager()
default_logger = create_deepened_logger("apex_os_bp")
