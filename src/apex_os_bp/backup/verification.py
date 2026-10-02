"""Backup verification implementation."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from apex_os_bp.backup.types import BackupManifest, BackupType, FileEntry, BackupVerificationError

logger = logging.getLogger(__name__)


class BackupVerifier:
    """Verifies backup integrity."""

    def __init__(self, backup_dir: str | Path):
        self.backup_dir = Path(backup_dir).resolve()

    def verify(self, backup_id: str) -> Tuple[bool, List[str]]:
        """Verify a backup by checking all file hashes."""
        backup_path = self.backup_dir / backup_id
        manifest_path = backup_path / "manifest.json"

        if not manifest_path.exists():
            raise BackupVerificationError(f"Manifest not found: {manifest_path}")

        manifest = self._load_manifest(manifest_path)
        errors = []

        for relative_path, entry in manifest.files.items():
            file_path = backup_path / "data" / relative_path

            if not file_path.exists():
                errors.append(f"Missing file: {relative_path}")
                continue

            actual_hash = self._compute_hash(file_path)
            if actual_hash != entry.hash:
                errors.append(f"Hash mismatch: {relative_path} (expected {entry.hash}, got {actual_hash})")

            actual_size = file_path.stat().st_size
            if actual_size != entry.size:
                errors.append(f"Size mismatch: {relative_path} (expected {entry.size}, got {actual_size})")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info(f"Backup {backup_id} verified successfully")
        else:
            logger.warning(f"Backup {backup_id} verification failed with {len(errors)} errors")

        return is_valid, errors

    def verify_all(self) -> Dict[str, Tuple[bool, List[str]]]:
        """Verify all backups in the backup directory."""
        results = {}
        for item in self.backup_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                backup_id = item.name
                results[backup_id] = self.verify(backup_id)
        return results

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

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
