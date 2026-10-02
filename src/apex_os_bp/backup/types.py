"""Types and exceptions for backup system."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class BackupType(Enum):
    """Backup type enumeration."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupError(Exception):
    """Base backup error."""
    pass


class BackupNotFoundError(BackupError):
    """Backup not found error."""
    pass


class BackupVerificationError(BackupError):
    """Backup verification error."""
    pass


class BackupRestorationError(BackupError):
    """Backup restoration error."""
    pass


@dataclass
class FileEntry:
    """File entry in backup manifest."""
    path: str
    hash: str
    size: int
    mtime: float


@dataclass
class BackupManifest:
    """Backup manifest."""
    backup_id: str
    backup_type: BackupType
    timestamp: str
    source_path: str
    files: Dict[str, FileEntry] = field(default_factory=dict)
    total_files: int = 0
    total_size: int = 0
    parent_backup_id: Optional[str] = None
