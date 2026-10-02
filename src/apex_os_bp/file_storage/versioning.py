"""File versioning system for storage backends."""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Callable

from apex_os_bp.file_storage.base import StorageBackend, StorageObject, StorageError


@dataclass
class FileVersion:
    """Represents a single version of a file."""

    key: str
    version_id: str
    size: int
    content_type: str = "application/octet-stream"
    metadata: Dict[str, str] = field(default_factory=dict)
    etag: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_latest: bool = False
    comment: str = ""
    storage_backend: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "FileVersion":
        """Create from dictionary."""
        data = dict(data)
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class VersionedStorage:
    """Wraps a storage backend with file versioning capabilities.

    Stores version metadata alongside the actual file data. Each version
    is preserved as a separate object with a versioned key pattern:
    `{key}` for the latest version, and `{key}#{version_id}` for historical versions.
    """

    VERSION_META_SUFFIX = ".versions"
    VERSION_SEPARATOR = "#"

    def __init__(self, backend: StorageBackend, max_versions: int = 50):
        self.backend = backend
        self.max_versions = max_versions
        self._version_cache: Dict[str, List[FileVersion]] = {}

    @property
    def name(self) -> str:
        return f"versioned_{self.backend.name}"

    def _versioned_key(self, key: str, version_id: str) -> str:
        """Generate the storage key for a specific version."""
        return f"{key}{self.VERSION_SEPARATOR}{version_id}"

    def _meta_key(self, key: str) -> str:
        """Generate the metadata key for version tracking."""
        return f"{key}{self.VERSION_META_SUFFIX}"

    def _generate_version_id(self, data: bytes) -> str:
        """Generate a unique version ID based on content hash and timestamp."""
        content_hash = hashlib.sha256(data).hexdigest()[:12]
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"v{timestamp}-{content_hash}"

    def _load_versions(self, key: str) -> List[FileVersion]:
        """Load version metadata from storage."""
        if key in self._version_cache:
            return self._version_cache[key]

        meta_key = self._meta_key(key)
        try:
            if self.backend.exists(meta_key):
                data = self.backend.get(meta_key)
                versions_data = json.loads(data.decode("utf-8"))
                versions = [FileVersion.from_dict(v) for v in versions_data]
            else:
                versions = []
        except (StorageError, json.JSONDecodeError):
            versions = []

        self._version_cache[key] = versions
        return versions

    def _save_versions(self, key: str, versions: List[FileVersion]) -> None:
        """Save version metadata to storage."""
        meta_key = self._meta_key(key)
        versions_data = json.dumps([v.to_dict() for v in versions])
        self.backend.put(meta_key, versions_data.encode("utf-8"), content_type="application/json")
        self._version_cache[key] = versions

    def _cleanup_old_versions(self, key: str, versions: List[FileVersion]) -> List[FileVersion]:
        """Remove oldest versions if exceeding max_versions limit."""
        if len(versions) <= self.max_versions:
            return versions

        # Sort by created_at descending (newest first)
        versions.sort(key=lambda v: v.created_at, reverse=True)
        to_remove = versions[self.max_versions:]
        versions = versions[:self.max_versions]

        # Delete old version data
        for old_version in to_remove:
            versioned_key = self._versioned_key(key, old_version.version_id)
            try:
                self.backend.delete(versioned_key)
            except StorageError:
                pass  # Best effort cleanup

        return versions

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream",
            metadata: Optional[Dict[str, str]] = None, comment: str = "") -> FileVersion:
        """Store a new version of a file.

        Args:
            key: The file key/path.
            data: The file content as bytes.
            content_type: MIME type of the file.
            metadata: Optional metadata dict.
            comment: Optional version comment.

        Returns:
            The created FileVersion.
        """
        self.backend._ensure_connected()

        # Generate version ID
        version_id = self._generate_version_id(data)

        # Store the versioned copy
        versioned_key = self._versioned_key(key, version_id)
        self.backend.put(versioned_key, data, content_type=content_type, metadata=metadata)

        # Also store as the latest version
        self.backend.put(key, data, content_type=content_type, metadata=metadata)

        # Create version record
        file_version = FileVersion(
            key=key,
            version_id=version_id,
            size=len(data),
            content_type=content_type,
            metadata=metadata or {},
            etag=hashlib.md5(data).hexdigest(),
            is_latest=True,
            comment=comment,
            storage_backend=self.backend.name,
        )

        # Update version history
        versions = self._load_versions(key)
        # Mark all previous versions as not latest
        for v in versions:
            v.is_latest = False
        versions.insert(0, file_version)

        # Cleanup old versions
        versions = self._cleanup_old_versions(key, versions)

        # Save version metadata
        self._save_versions(key, versions)

        return file_version

    def get(self, key: str, version_id: Optional[str] = None) -> bytes:
        """Retrieve file content, optionally a specific version.

        Args:
            key: The file key/path.
            version_id: Optional specific version to retrieve. If None, gets latest.

        Returns:
            The file content as bytes.
        """
        self.backend._ensure_connected()

        if version_id is None:
            return self.backend.get(key)

        versioned_key = self._versioned_key(key, version_id)
        return self.backend.get(versioned_key)

    def get_version(self, key: str, version_id: str) -> FileVersion:
        """Get metadata for a specific version."""
        versions = self._load_versions(key)
        for v in versions:
            if v.version_id == version_id:
                return v
        raise StorageError(
            f"Version '{version_id}' not found for key '{key}'",
            backend=self.backend.name,
        )

    def list_versions(self, key: str) -> List[FileVersion]:
        """List all versions of a file, newest first."""
        return self._load_versions(key)

    def get_latest_version(self, key: str) -> Optional[FileVersion]:
        """Get the latest version of a file."""
        versions = self._load_versions(key)
        if not versions:
            return None
        return versions[0]

    def restore_version(self, key: str, version_id: str) -> FileVersion:
        """Restore a specific version as the latest.

        Args:
            key: The file key/path.
            version_id: The version to restore.

        Returns:
            The new FileVersion created by the restore.
        """
        self.backend._ensure_connected()

        # Get the version data
        versioned_key = self._versioned_key(key, version_id)
        data = self.backend.get(versioned_key)

        # Get version metadata
        versions = self._load_versions(key)
        target_version = None
        for v in versions:
            if v.version_id == version_id:
                target_version = v
                break

        if target_version is None:
            raise StorageError(
                f"Version '{version_id}' not found for key '{key}'",
                backend=self.backend.name,
            )

        # Store as new version (restore creates a new version with old content)
        return self.put(
            key,
            data,
            content_type=target_version.content_type,
            metadata=target_version.metadata,
            comment=f"Restored from version {version_id}",
        )

    def delete_version(self, key: str, version_id: str) -> bool:
        """Delete a specific version of a file.

        Cannot delete the latest version; use delete() to remove the entire file.
        """
        versions = self._load_versions(key)

        # Find the version to delete
        target_idx = None
        for i, v in enumerate(versions):
            if v.version_id == version_id:
                target_idx = i
                break

        if target_idx is None:
            return False

        # Don't allow deleting the latest version
        if versions[target_idx].is_latest:
            raise StorageError(
                "Cannot delete the latest version. Use delete() to remove the entire file.",
                backend=self.backend.name,
            )

        # Delete the versioned data
        versioned_key = self._versioned_key(key, version_id)
        self.backend.delete(versioned_key)

        # Remove from version list
        versions.pop(target_idx)
        self._save_versions(key, versions)

        return True

    def delete(self, key: str) -> bool:
        """Delete a file and all its versions."""
        self.backend._ensure_connected()

        versions = self._load_versions(key)

        # Delete all versioned copies
        for v in versions:
            versioned_key = self._versioned_key(key, v.version_id)
            try:
                self.backend.delete(versioned_key)
            except StorageError:
                pass

        # Delete the latest version
        self.backend.delete(key)

        # Delete version metadata
        meta_key = self._meta_key(key)
        try:
            self.backend.delete(meta_key)
        except StorageError:
            pass

        # Clear cache
        self._version_cache.pop(key, None)

        return True

    def get_version_count(self, key: str) -> int:
        """Get the number of versions for a file."""
        return len(self._load_versions(key))

    def compare_versions(self, key: str, version_id1: str, version_id2: str) -> Dict:
        """Compare two versions of a file.

        Returns:
            Dict with 'identical', 'size_diff', and 'metadata_diff' keys.
        """
        v1 = self.get_version(key, version_id1)
        v2 = self.get_version(key, version_id2)

        # Compare content by hash
        data1 = self.get(key, version_id1)
        data2 = self.get(key, version_id2)
        hash1 = hashlib.md5(data1).hexdigest()
        hash2 = hashlib.md5(data2).hexdigest()

        metadata_diff = {}
        all_keys = set(v1.metadata.keys()) | set(v2.metadata.keys())
        for k in all_keys:
            val1 = v1.metadata.get(k)
            val2 = v2.metadata.get(k)
            if val1 != val2:
                metadata_diff[k] = {"old": val1, "new": val2}

        return {
            "identical": hash1 == hash2,
            "size_diff": len(data1) - len(data2),
            "metadata_diff": metadata_diff,
        }

    def set_max_versions(self, max_versions: int) -> None:
        """Update the maximum number of versions to keep."""
        self.max_versions = max_versions

    def clear_cache(self) -> None:
        """Clear the version metadata cache."""
        self._version_cache.clear()
