"""Backup restoration implementation."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from apex_os_bp.backup.types import BackupManifest, BackupType, FileEntry, BackupRestorationError

logger = logging.getLogger(__name__)


class BackupRestorer:
    """Restores files from backups."""

    def __init__(self, backup_dir: str | Path):
        self.backup_dir = Path(backup_dir).resolve()

    def restore(self, backup_id: str, target_path: str | Path,
                incremental_chain: Optional[List[str]] = None) -> None:
        """Restore from a backup."""
        target = Path(target_path).resolve()
        target.mkdir(parents=True, exist_ok=True)

        if incremental_chain:
            for bid in incremental_chain:
                self._restore_single(bid, target)
        else:
            self._restore_single(backup_id, target)

        logger.info(f"Restored backup {backup_id} to {target}")

    def _restore_single(self, backup_id: str, target: Path) -> None:
        """Restore a single backup."""
        backup_path = self.backup_dir / backup_id
        manifest_path = backup_path / "manifest.json"

        if not manifest_path.exists():
            raise BackupRestorationError(f"Backup not found: {backup_id}")

        manifest = self._load_manifest(manifest_path)

        for relative_path, entry in manifest.files.items():
            src_path = backup_path / "data" / relative_path
            dest_path = target / relative_path

            if not src_path.exists():
                raise BackupRestorationError(f"Backup file missing: {relative_path}")

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)

    def _load_manifest(self, manifest_path: Path) -> BackupManifest:
        """Load manifest from JSON file."""
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
