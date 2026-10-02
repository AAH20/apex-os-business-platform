"""Incremental backup implementation."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from apex_os_bp.backup.types import BackupManifest, BackupType, FileEntry, BackupError

logger = logging.getLogger(__name__)


class IncrementalBackup:
    """Incremental backup - backs up only files changed since last backup."""

    def __init__(self, source_path: str | Path, backup_dir: str | Path):
        self.source_path = Path(source_path).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self._validate_paths()

    def _validate_paths(self) -> None:
        if not self.source_path.exists():
            raise BackupError(f"Source path does not exist: {self.source_path}")
        if not self.source_path.is_dir():
            raise BackupError(f"Source path is not a directory: {self.source_path}")

    def create(self, parent_manifest: BackupManifest, backup_id: Optional[str] = None) -> BackupManifest:
        """Create an incremental backup based on parent manifest."""
        if backup_id is None:
            backup_id = f"incremental_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)

        files_data: Dict[str, FileEntry] = {}
        total_size = 0

        for file_path in self._walk_files():
            relative_path = str(file_path.relative_to(self.source_path))
            stat = file_path.stat()

            if self._has_changed(relative_path, stat, parent_manifest):
                file_hash = self._compute_hash(file_path)

                entry = FileEntry(
                    path=relative_path,
                    hash=file_hash,
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                )
                files_data[relative_path] = entry
                total_size += stat.st_size

                dest_path = backup_path / "data" / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)

        manifest = BackupManifest(
            backup_id=backup_id,
            backup_type=BackupType.INCREMENTAL,
            timestamp=datetime.now().isoformat(),
            source_path=str(self.source_path),
            files=files_data,
            total_files=len(files_data),
            total_size=total_size,
            parent_backup_id=parent_manifest.backup_id,
        )

        self._write_manifest(backup_path, manifest)
        logger.info(f"Incremental backup created: {backup_id} ({len(files_data)} files changed)")

        return manifest

    def _has_changed(self, relative_path: str, stat: os.stat_result, parent_manifest: BackupManifest) -> bool:
        """Check if file has changed since parent backup."""
        if relative_path not in parent_manifest.files:
            return True

        parent_entry = parent_manifest.files[relative_path]
        if stat.st_size != parent_entry.size:
            return True
        if stat.st_mtime != parent_entry.mtime:
            return True

        return False

    def _walk_files(self) -> List[Path]:
        """Walk all files in source directory."""
        files = []
        for item in self.source_path.rglob("*"):
            if item.is_file():
                files.append(item)
        return sorted(files)

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _write_manifest(self, backup_path: Path, manifest: BackupManifest) -> None:
        """Write manifest to backup directory."""
        manifest_path = backup_path / "manifest.json"
        data = {
            "backup_id": manifest.backup_id,
            "backup_type": manifest.backup_type.value,
            "timestamp": manifest.timestamp,
            "source_path": manifest.source_path,
            "files": {
                path: {
                    "path": entry.path,
                    "hash": entry.hash,
                    "size": entry.size,
                    "mtime": entry.mtime,
                }
                for path, entry in manifest.files.items()
            },
            "total_files": manifest.total_files,
            "total_size": manifest.total_size,
            "parent_backup_id": manifest.parent_backup_id,
        }
        manifest_path.write_text(json.dumps(data, indent=2))
