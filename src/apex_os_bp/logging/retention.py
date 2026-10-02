"""Log retention — policies, archival, compression, and cleanup."""

from __future__ import annotations

import gzip
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from .structured import LogEntry, LogLevel


@dataclass
class RetentionPolicy:
    """Defines retention rules for log files."""

    name: str = "default"
    max_age_days: int = 30
    max_size_bytes: int = 1_000_000_000  # 1 GB
    max_files: int = 100
    archive_after_days: int = 7
    compress_archives: bool = True
    delete_after_archive: bool = False
    keep_levels: Optional[Set[LogLevel]] = None
    archive_path: Optional[Path] = None

    def should_archive(self, file_mtime: datetime) -> bool:
        """Check if a file should be archived based on age."""
        age = datetime.now(timezone.utc) - file_mtime
        return age.days >= self.archive_after_days

    def should_delete(self, file_mtime: datetime) -> bool:
        """Check if a file should be deleted based on age."""
        age = datetime.now(timezone.utc) - file_mtime
        return age.days >= self.max_age_days

    def is_within_size(self, current_size: int) -> bool:
        """Check if current size is within the limit."""
        return current_size < self.max_size_bytes


@dataclass
class RetentionReport:
    """Report of retention operations."""

    files_archived: int = 0
    files_deleted: int = 0
    files_compressed: int = 0
    bytes_freed: int = 0
    bytes_archived: int = 0
    errors: List[str] = field(default_factory=list)
    archived_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files_archived": self.files_archived,
            "files_deleted": self.files_deleted,
            "files_compressed": self.files_compressed,
            "bytes_freed": self.bytes_freed,
            "bytes_archived": self.bytes_archived,
            "errors": self.errors,
            "archived_files": self.archived_files,
            "deleted_files": self.deleted_files,
        }


class LogRetention:
    """Manages log retention policies, archival, and cleanup."""

    def __init__(
        self,
        log_dir: Path,
        policy: Optional[RetentionPolicy] = None,
    ):
        self.log_dir = Path(log_dir)
        self.policy = policy or RetentionPolicy()
        self._pre_cleanup_hooks: List[Callable[[Path], None]] = []
        self._post_cleanup_hooks: List[Callable[[RetentionReport], None]] = []

    def on_pre_cleanup(self, hook: Callable[[Path], None]) -> None:
        """Register a hook called before each file cleanup."""
        self._pre_cleanup_hooks.append(hook)

    def on_post_cleanup(self, hook: Callable[[RetentionReport], None]) -> None:
        """Register a hook called after cleanup completes."""
        self._post_cleanup_hooks.append(hook)

    def scan_files(self) -> List[Path]:
        """Scan log directory for log files."""
        if not self.log_dir.exists():
            return []
        files = []
        for pattern in ["*.log", "*.log.*", "*.jsonl"]:
            files.extend(self.log_dir.glob(pattern))
        return sorted(files, key=lambda f: f.stat().st_mtime)

    def get_file_age_days(self, filepath: Path) -> float:
        """Get age of a file in days."""
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - mtime).total_seconds() / 86400.0

    def get_total_size(self) -> int:
        """Get total size of all log files in bytes."""
        return sum(f.stat().st_size for f in self.scan_files())

    def archive_file(self, filepath: Path, archive_dir: Optional[Path] = None) -> Path:
        """Archive a log file, optionally compressing it."""
        target_dir = archive_dir or self.policy.archive_path or (self.log_dir / "archive")
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        dest = target_dir / filepath.name

        if self.policy.compress_archives:
            dest = dest.with_suffix(dest.suffix + ".gz")
            with open(filepath, "rb") as f_in:
                with gzip.open(dest, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(filepath, dest)

        return dest

    def compress_file(self, filepath: Path) -> Path:
        """Compress a single file in place, returning the compressed path."""
        compressed = filepath.with_suffix(filepath.suffix + ".gz")
        with open(filepath, "rb") as f_in:
            with gzip.open(compressed, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        filepath.unlink()
        return compressed

    def delete_file(self, filepath: Path) -> int:
        """Delete a file, returning bytes freed."""
        size = filepath.stat().st_size
        filepath.unlink()
        return size

    def cleanup(self, dry_run: bool = False) -> RetentionReport:
        """Execute retention policy: archive old files, delete expired ones."""
        report = RetentionReport()
        files = self.scan_files()

        for filepath in files:
            age_days = self.get_file_age_days(filepath)
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)

            # Run pre-cleanup hooks
            for hook in self._pre_cleanup_hooks:
                try:
                    hook(filepath)
                except Exception as e:
                    report.errors.append(f"Hook error for {filepath}: {e}")

            try:
                if self.policy.should_delete(mtime):
                    size = filepath.stat().st_size
                    if not dry_run:
                        self.delete_file(filepath)
                    report.files_deleted += 1
                    report.bytes_freed += size
                    report.deleted_files.append(str(filepath))

                elif self.policy.should_archive(mtime):
                    size = filepath.stat().st_size
                    if not dry_run:
                        dest = self.archive_file(filepath)
                        report.archived_files.append(str(dest))
                        if self.policy.compress_archives:
                            report.files_compressed += 1
                            # Optionally delete original after archiving
                            if self.policy.delete_after_archive:
                                self.delete_file(filepath)
                    else:
                        report.archived_files.append(str(filepath) + " (dry-run)")
                    report.files_archived += 1
                    report.bytes_archived += size

            except Exception as e:
                report.errors.append(f"Error processing {filepath}: {e}")

        # Enforce max_files limit
        remaining = self.scan_files()
        if len(remaining) > self.policy.max_files:
            excess = len(remaining) - self.policy.max_files
            for filepath in remaining[:excess]:
                try:
                    size = filepath.stat().st_size
                    if not dry_run:
                        self.delete_file(filepath)
                    report.files_deleted += 1
                    report.bytes_freed += size
                    report.deleted_files.append(str(filepath))
                except Exception as e:
                    report.errors.append(f"Error deleting excess file {filepath}: {e}")

        # Enforce max size limit
        total_size = self.get_total_size()
        if not self.policy.is_within_size(total_size):
            remaining = self.scan_files()
            for filepath in remaining:
                if self.policy.is_within_size(self.get_total_size()):
                    break
                try:
                    size = filepath.stat().st_size
                    if not dry_run:
                        self.delete_file(filepath)
                    report.files_deleted += 1
                    report.bytes_freed += size
                    report.deleted_files.append(str(filepath))
                except Exception as e:
                    report.errors.append(f"Error deleting for size limit {filepath}: {e}")

        # Run post-cleanup hooks
        for hook in self._post_cleanup_hooks:
            try:
                hook(report)
            except Exception as e:
                report.errors.append(f"Post-hook error: {e}")

        return report

    def cleanup_by_level(
        self, entries: Iterable[LogEntry], level: LogLevel
    ) -> List[LogEntry]:
        """Filter entries, keeping only those at or above the given level."""
        return [e for e in entries if e.level.value >= level.value]

    def prune_entries(
        self,
        entries: Iterable[LogEntry],
        max_age: Optional[timedelta] = None,
        keep_minimum: int = 100,
    ) -> List[LogEntry]:
        """Prune old entries while keeping a minimum number."""
        entries_list = list(entries)
        if max_age is None or len(entries_list) <= keep_minimum:
            return entries_list

        cutoff = datetime.now(timezone.utc) - max_age
        pruned = [e for e in entries_list if e.timestamp >= cutoff]

        # Always keep at least keep_minimum entries
        if len(pruned) < keep_minimum:
            return entries_list[-keep_minimum:]
        return pruned

    def rotate_file(
        self, filepath: Path, max_size: int, keep_copies: int = 5
    ) -> Optional[Path]:
        """Rotate a log file when it exceeds max_size."""
        if not filepath.exists():
            return None

        size = filepath.stat().st_size
        if size < max_size:
            return None

        # Shift existing rotations
        for i in range(keep_copies - 1, 0, -1):
            old = filepath.with_suffix(f".{i}{filepath.suffix}")
            new = filepath.with_suffix(f".{i + 1}{filepath.suffix}")
            if old.exists():
                old.rename(new)

        # Rotate current file
        rotated = filepath.with_suffix(f".1{filepath.suffix}")
        filepath.rename(rotated)
        return rotated

    def get_retention_summary(self) -> Dict[str, Any]:
        """Get a summary of current retention state."""
        files = self.scan_files()
        total_size = sum(f.stat().st_size for f in files)
        ages = [self.get_file_age_days(f) for f in files]

        return {
            "log_dir": str(self.log_dir),
            "total_files": len(files),
            "total_size_bytes": total_size,
            "oldest_file_days": max(ages) if ages else 0,
            "newest_file_days": min(ages) if ages else 0,
            "policy": {
                "max_age_days": self.policy.max_age_days,
                "max_size_bytes": self.policy.max_size_bytes,
                "max_files": self.policy.max_files,
                "archive_after_days": self.policy.archive_after_days,
                "compress_archives": self.policy.compress_archives,
            },
        }
