"""Backup manager - orchestrates all backup operations."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from apex_os_bp.backup.types import BackupManifest, BackupType, FileEntry, BackupError
from apex_os_bp.backup.full_backup import FullBackup
from apex_os_bp.backup.incremental_backup import IncrementalBackup
from apex_os_bp.backup.differential_backup import DifferentialBackup
from apex_os_bp.backup.verification import BackupVerifier
from apex_os_bp.backup.restoration import BackupRestorer

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages all backup operations."""

    def __init__(self, source_path: str | Path, backup_dir: str | Path):
        self.source_path = Path(source_path).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._full_backup = FullBackup(self.source_path, self.backup_dir)
        self._incremental_backup = IncrementalBackup(self.source_path, self.backup_dir)
        self._differential_backup = DifferentialBackup(self.source_path, self.backup_dir)
        self._verifier = BackupVerifier(self.backup_dir)
        self._restorer = BackupRestorer(self.backup_dir)

    def create_full_backup(self, backup_id: Optional[str] = None) -> BackupManifest:
        """Create a full backup."""
        return self._full_backup.create(backup_id)

    def create_incremental_backup(self, parent_id: Optional[str] = None,
                                   backup_id: Optional[str] = None) -> BackupManifest:
        """Create an incremental backup."""
        if parent_id is None:
            parent_manifest = self._get_last_backup()
        else:
            parent_manifest = self._load_manifest(parent_id)

        if parent_manifest is None:
            raise BackupError("No parent backup found for incremental backup")

        return self._incremental_backup.create(parent_manifest, backup_id)

    def create_differential_backup(self, backup_id: Optional[str] = None) -> BackupManifest:
        """Create a differential backup."""
        full_manifest = self._get_last_full_backup()

        if full_manifest is None:
            raise BackupError("No full backup found for differential backup")

        return self._differential_backup.create(full_manifest, backup_id)

    def verify_backup(self, backup_id: str) -> tuple:
        """Verify a backup."""
        return self._verifier.verify(backup_id)

    def verify_all_backups(self) -> Dict[str, tuple]:
        """Verify all backups."""
        return self._verifier.verify_all()

    def restore_backup(self, backup_id: str, target_path: str | Path,
                       incremental_chain: Optional[List[str]] = None) -> None:
        """Restore from a backup."""
        self._restorer.restore(backup_id, target_path, incremental_chain)

    def list_backups(self) -> List[Dict]:
        """List all backups."""
        backups = []
        for item in self.backup_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                manifest = self._load_manifest(item.name)
                if manifest:
                    backups.append({
                        "backup_id": manifest.backup_id,
                        "type": manifest.backup_type.value,
                        "timestamp": manifest.timestamp,
                        "total_files": manifest.total_files,
                        "total_size": manifest.total_size,
                        "parent": manifest.parent_backup_id,
                    })
        return sorted(backups, key=lambda x: x["timestamp"])

    def _get_last_backup(self) -> Optional[BackupManifest]:
        """Get the most recent backup manifest."""
        backups = self.list_backups()
        if not backups:
            return None
        return self._load_manifest(backups[-1]["backup_id"])

    def _get_last_full_backup(self) -> Optional[BackupManifest]:
        """Get the most recent full backup manifest."""
        backups = self.list_backups()
        for backup in reversed(backups):
            if backup["type"] == "full":
                return self._load_manifest(backup["backup_id"])
        return None

    def _load_manifest(self, backup_id: str) -> Optional[BackupManifest]:
        """Load a manifest by backup ID."""
        manifest_path = self.backup_dir / backup_id / "manifest.json"
        if not manifest_path.exists():
            return None

        data = json.loads(manifest_path.read_text())
        files = {}
        for path, entry_data in data.get("files", {}).items():
            files[path] = FileEntry(
                path=entry_data["path"],
                hash=entry_data["hash"],
                size=entry_data["size"],
                mtime=entry_data["mtime"],
            )
        return BackupManifest(
            backup_id=data["backup_id"],
            backup_type=BackupType(data["backup_type"]),
            timestamp=data["timestamp"],
            source_path=data["source_path"],
            files=files,
            total_files=data.get("total_files", 0),
            total_size=data.get("total_size", 0),
            parent_backup_id=data.get("parent_backup_id"),
        )
