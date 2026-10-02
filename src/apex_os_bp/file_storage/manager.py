"""Storage manager for coordinating multiple storage backends."""

import hashlib
from typing import Dict, List, Optional, Tuple

from apex_os_bp.file_storage.base import StorageBackend, StorageObject, StorageError
from apex_os_bp.file_storage.local import LocalStorage
from apex_os_bp.file_storage.s3 import S3Storage
from apex_os_bp.file_storage.azure import AzureStorage
from apex_os_bp.file_storage.gcp import GCPStorage
from apex_os_bp.file_storage.versioning import VersionedStorage, FileVersion


class StorageManager:
    """Manages multiple storage backends with failover and replication.

    Provides a unified interface for file operations across local, S3,
    Azure, and GCP storage backends. Supports primary/secondary failover
    and multi-backend replication.
    """

    BACKEND_TYPES = {
        "local": LocalStorage,
        "s3": S3Storage,
        "azure": AzureStorage,
        "gcp": GCPStorage,
    }

    def __init__(self):
        self._backends: Dict[str, StorageBackend] = {}
        self._versioned_backends: Dict[str, VersionedStorage] = {}
        self._primary: Optional[str] = None
        self._secondaries: List[str] = []
        self._replication_enabled = False

    def add_backend(self, name: str, backend_type: str, config: Optional[Dict] = None,
                    primary: bool = False) -> StorageBackend:
        """Add a storage backend.

        Args:
            name: Unique name for this backend instance.
            backend_type: One of 'local', 's3', 'azure', 'gcp'.
            config: Backend-specific configuration dict.
            primary: Whether this is the primary backend.

        Returns:
            The created StorageBackend instance.
        """
        if backend_type not in self.BACKEND_TYPES:
            raise StorageError(f"Unknown backend type: {backend_type}. "
                               f"Valid types: {list(self.BACKEND_TYPES.keys())}")

        backend_class = self.BACKEND_TYPES[backend_type]
        backend = backend_class(name=name, config=config)
        self._backends[name] = backend

        if primary:
            self._primary = name

        return backend

    def remove_backend(self, name: str) -> bool:
        """Remove a storage backend."""
        if name not in self._backends:
            return False
        if self._primary == name:
            self._primary = None
        if name in self._secondaries:
            self._secondaries.remove(name)
        self._backends.pop(name, None)
        self._versioned_backends.pop(name, None)
        return True

    def connect_all(self) -> Dict[str, bool]:
        """Connect all backends. Returns dict of name -> success."""
        results = {}
        for name, backend in self._backends.items():
            try:
                backend.connect()
                results[name] = True
            except StorageError:
                results[name] = False
        return results

    def disconnect_all(self) -> None:
        """Disconnect all backends."""
        for backend in self._backends.values():
            try:
                backend.disconnect()
            except Exception:
                pass

    def set_primary(self, name: str) -> None:
        """Set the primary backend."""
        if name not in self._backends:
            raise StorageError(f"Backend '{name}' not found")
        self._primary = name

    def set_secondaries(self, names: List[str]) -> None:
        """Set secondary backends for failover."""
        for name in names:
            if name not in self._backends:
                raise StorageError(f"Backend '{name}' not found")
        self._secondaries = list(names)

    def enable_replication(self, enabled: bool = True) -> None:
        """Enable/disable replication to secondary backends."""
        self._replication_enabled = enabled

    @property
    def primary_backend(self) -> Optional[StorageBackend]:
        """Get the primary backend."""
        if self._primary:
            return self._backends.get(self._primary)
        return None

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream",
            metadata: Optional[Dict[str, str]] = None, replicate: Optional[bool] = None) -> StorageObject:
        """Store a file on the primary backend, optionally replicating.

        Args:
            key: File key/path.
            data: File content.
            content_type: MIME type.
            metadata: Optional metadata.
            replicate: Override replication setting for this operation.

        Returns:
            StorageObject from the primary backend.
        """
        primary = self.primary_backend
        if primary is None:
            raise StorageError("No primary backend configured")

        result = primary.put(key, data, content_type=content_type, metadata=metadata)

        # Replicate if enabled
        should_replicate = replicate if replicate is not None else self._replication_enabled
        if should_replicate:
            for sec_name in self._secondaries:
                sec_backend = self._backends.get(sec_name)
                if sec_backend and sec_backend.connected:
                    try:
                        sec_backend.put(key, data, content_type=content_type, metadata=metadata)
                    except StorageError:
                        pass  # Best effort replication

        return result

    def get(self, key: str) -> bytes:
        """Retrieve a file, with failover to secondary backends."""
        # Try primary first
        primary = self.primary_backend
        if primary and primary.connected:
            try:
                return primary.get(key)
            except StorageError:
                pass

        # Failover to secondaries
        for sec_name in self._secondaries:
            sec_backend = self._backends.get(sec_name)
            if sec_backend and sec_backend.connected:
                try:
                    return sec_backend.get(key)
                except StorageError:
                    continue

        raise StorageError(f"File not found on any backend: {key}")

    def get_object(self, key: str) -> StorageObject:
        """Get file metadata, with failover."""
        primary = self.primary_backend
        if primary and primary.connected:
            try:
                return primary.get_object(key)
            except StorageError:
                pass

        for sec_name in self._secondaries:
            sec_backend = self._backends.get(sec_name)
            if sec_backend and sec_backend.connected:
                try:
                    return sec_backend.get_object(key)
                except StorageError:
                    continue

        raise StorageError(f"File not found on any backend: {key}")

    def delete(self, key: str, replicate: Optional[bool] = None) -> bool:
        """Delete a file from all backends."""
        deleted = False
        for backend in self._backends.values():
            if backend.connected:
                try:
                    if backend.delete(key):
                        deleted = True
                except StorageError:
                    pass
        return deleted

    def exists(self, key: str) -> bool:
        """Check if a file exists on any backend."""
        for backend in self._backends.values():
            if backend.connected:
                try:
                    if backend.exists(key):
                        return True
                except StorageError:
                    continue
        return False

    def list_objects(self, prefix: str = "") -> List[StorageObject]:
        """List objects from the primary backend."""
        primary = self.primary_backend
        if primary is None:
            raise StorageError("No primary backend configured")
        return primary.list_objects(prefix)

    def copy(self, source_key: str, dest_key: str) -> StorageObject:
        """Copy a file on the primary backend."""
        primary = self.primary_backend
        if primary is None:
            raise StorageError("No primary backend configured")
        return primary.copy(source_key, dest_key)

    def move(self, source_key: str, dest_key: str) -> StorageObject:
        """Move a file on the primary backend."""
        primary = self.primary_backend
        if primary is None:
            raise StorageError("No primary backend configured")
        return primary.move(source_key, dest_key)

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Get a pre-signed URL from the primary backend."""
        primary = self.primary_backend
        if primary is None:
            raise StorageError("No primary backend configured")
        return primary.get_url(key, expires_in)

    def get_hash(self, key: str) -> str:
        """Get file hash from the primary backend."""
        primary = self.primary_backend
        if primary is None:
            raise StorageError("No primary backend configured")
        return primary.get_hash(key)

    def get_versioned(self, name: str, max_versions: int = 50) -> VersionedStorage:
        """Get or create a versioned wrapper for a backend."""
        if name not in self._versioned_backends:
            if name not in self._backends:
                raise StorageError(f"Backend '{name}' not found")
            self._versioned_backends[name] = VersionedStorage(
                self._backends[name], max_versions=max_versions
            )
        return self._versioned_backends[name]

    def replicate_file(self, key: str, source_backend: str, target_backend: str) -> StorageObject:
        """Replicate a specific file between backends."""
        if source_backend not in self._backends:
            raise StorageError(f"Source backend '{source_backend}' not found")
        if target_backend not in self._backends:
            raise StorageError(f"Target backend '{target_backend}' not found")

        source = self._backends[source_backend]
        target = self._backends[target_backend]

        data = source.get(key)
        obj = source.get_object(key)

        return target.put(key, data, content_type=obj.content_type, metadata=obj.metadata)

    def sync_backends(self, source: str, target: str, prefix: str = "") -> Tuple[int, int]:
        """Sync all files from source to target backend.

        Returns:
            Tuple of (files_synced, files_failed).
        """
        if source not in self._backends:
            raise StorageError(f"Source backend '{source}' not found")
        if target not in self._backends:
            raise StorageError(f"Target backend '{target}' not found")

        source_backend = self._backends[source]
        target_backend = self._backends[target]

        objects = source_backend.list_objects(prefix)
        synced = 0
        failed = 0

        for obj in objects:
            try:
                data = source_backend.get(obj.key)
                target_backend.put(obj.key, data, content_type=obj.content_type, metadata=obj.metadata)
                synced += 1
            except StorageError:
                failed += 1

        return synced, failed

    def health_check(self) -> Dict[str, Dict]:
        """Check health of all backends.

        Returns:
            Dict mapping backend name to health info dict.
        """
        results = {}
        for name, backend in self._backends.items():
            info = {
                "connected": backend.connected,
                "type": type(backend).__name__,
                "is_primary": name == self._primary,
                "is_secondary": name in self._secondaries,
            }
            if backend.connected:
                try:
                    # Try a simple operation
                    backend.list_objects()
                    info["healthy"] = True
                    info["error"] = None
                except Exception as e:
                    info["healthy"] = False
                    info["error"] = str(e)
            else:
                info["healthy"] = False
                info["error"] = "Not connected"
            results[name] = info
        return results

    def __enter__(self):
        self.connect_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect_all()
        return False
