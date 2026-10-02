"""Local filesystem storage backend."""

import os
import shutil
import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from apex_os_bp.file_storage.base import StorageBackend, StorageObject, StorageError


class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, name: str = "local", config: Optional[Dict] = None):
        super().__init__(name, config)
        self.base_path = Path(self.config.get("base_path", "/tmp/apex_storage"))
        self._objects: Dict[str, StorageObject] = {}

    def connect(self) -> None:
        """Create the base directory if it doesn't exist."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            self._connected = True
            self._load_existing_objects()
        except OSError as e:
            raise StorageError(f"Failed to initialize local storage: {e}", backend=self.name, original_error=e)

    def disconnect(self) -> None:
        """No-op for local storage."""
        self._connected = False

    def _load_existing_objects(self) -> None:
        """Scan the base path and load existing objects into memory."""
        self._objects.clear()
        if not self.base_path.exists():
            return
        for file_path in self.base_path.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(self.base_path))
                stat = file_path.stat()
                content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
                self._objects[rel_path] = StorageObject(
                    key=rel_path,
                    size=stat.st_size,
                    content_type=content_type,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                    etag=self._compute_etag(file_path),
                )

    def _compute_etag(self, file_path: Path) -> str:
        """Compute ETag (MD5 hash) for a file."""
        h = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _full_path(self, key: str) -> Path:
        """Resolve a key to a full filesystem path, preventing path traversal."""
        full = (self.base_path / key).resolve()
        base_resolved = self.base_path.resolve()
        if not str(full).startswith(str(base_resolved)):
            raise StorageError(f"Invalid key (path traversal): {key}", backend=self.name)
        return full

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream",
            metadata: Optional[Dict[str, str]] = None) -> StorageObject:
        """Store a file on the local filesystem."""
        self._ensure_connected()
        try:
            file_path = self._full_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(data)

            # Write metadata sidecar if provided
            if metadata:
                meta_path = file_path.with_suffix(file_path.suffix + ".meta")
                import json
                with open(meta_path, "w") as f:
                    json.dump(metadata, f)

            stat = file_path.stat()
            obj = StorageObject(
                key=key,
                size=len(data),
                content_type=content_type,
                metadata=metadata or {},
                etag=self._compute_etag(file_path),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
            )
            self._objects[key] = obj
            return obj
        except OSError as e:
            raise StorageError(f"Failed to store file '{key}': {e}", backend=self.name, original_error=e)

    def get(self, key: str) -> bytes:
        """Retrieve file content from local filesystem."""
        self._ensure_connected()
        try:
            file_path = self._full_path(key)
            if not file_path.exists():
                raise StorageError(f"File not found: {key}", backend=self.name)
            with open(file_path, "rb") as f:
                return f.read()
        except OSError as e:
            raise StorageError(f"Failed to read file '{key}': {e}", backend=self.name, original_error=e)

    def get_object(self, key: str) -> StorageObject:
        """Get file metadata."""
        self._ensure_connected()
        if key in self._objects:
            return self._objects[key]
        # Try to load from disk
        try:
            file_path = self._full_path(key)
            if not file_path.exists():
                raise StorageError(f"File not found: {key}", backend=self.name)
            stat = file_path.stat()
            content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            return StorageObject(
                key=key,
                size=stat.st_size,
                content_type=content_type,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                etag=self._compute_etag(file_path),
            )
        except OSError as e:
            raise StorageError(f"Failed to get file info '{key}': {e}", backend=self.name, original_error=e)

    def delete(self, key: str) -> bool:
        """Delete a file from local filesystem."""
        self._ensure_connected()
        try:
            file_path = self._full_path(key)
            if not file_path.exists():
                return False
            file_path.unlink()
            # Also delete metadata sidecar if it exists
            meta_path = file_path.with_suffix(file_path.suffix + ".meta")
            if meta_path.exists():
                meta_path.unlink()
            self._objects.pop(key, None)
            return True
        except OSError as e:
            raise StorageError(f"Failed to delete file '{key}': {e}", backend=self.name, original_error=e)

    def exists(self, key: str) -> bool:
        """Check if a file exists."""
        self._ensure_connected()
        try:
            return self._full_path(key).exists()
        except StorageError:
            return False

    def list_objects(self, prefix: str = "") -> List[StorageObject]:
        """List all files, optionally filtered by prefix."""
        self._ensure_connected()
        results = []
        for key, obj in self._objects.items():
            if key.startswith(prefix):
                results.append(obj)
        return sorted(results, key=lambda o: o.key)

    def copy(self, source_key: str, dest_key: str) -> StorageObject:
        """Copy a file within local storage."""
        self._ensure_connected()
        try:
            src = self._full_path(source_key)
            dst = self._full_path(dest_key)
            if not src.exists():
                raise StorageError(f"Source file not found: {source_key}", backend=self.name)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            # Copy metadata sidecar if it exists
            src_meta = src.with_suffix(src.suffix + ".meta")
            if src_meta.exists():
                dst_meta = dst.with_suffix(dst.suffix + ".meta")
                shutil.copy2(src_meta, dst_meta)
            return self.get_object(dest_key)
        except OSError as e:
            raise StorageError(f"Failed to copy '{source_key}' to '{dest_key}': {e}", backend=self.name, original_error=e)

    def move(self, source_key: str, dest_key: str) -> StorageObject:
        """Move/rename a file within local storage."""
        self._ensure_connected()
        try:
            src = self._full_path(source_key)
            dst = self._full_path(dest_key)
            if not src.exists():
                raise StorageError(f"Source file not found: {source_key}", backend=self.name)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            # Move metadata sidecar if it exists
            src_meta = src.with_suffix(src.suffix + ".meta")
            if src_meta.exists():
                dst_meta = dst.with_suffix(dst.suffix + ".meta")
                shutil.move(str(src_meta), str(dst_meta))
            self._objects.pop(source_key, None)
            return self.get_object(dest_key)
        except OSError as e:
            raise StorageError(f"Failed to move '{source_key}' to '{dest_key}': {e}", backend=self.name, original_error=e)

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Get a file:// URL for local access."""
        self._ensure_connected()
        file_path = self._full_path(key)
        return file_path.as_uri()

    def get_hash(self, key: str) -> str:
        """Get the MD5 hash of a stored file."""
        self._ensure_connected()
        try:
            file_path = self._full_path(key)
            if not file_path.exists():
                raise StorageError(f"File not found: {key}", backend=self.name)
            return self._compute_etag(file_path)
        except OSError as e:
            raise StorageError(f"Failed to hash file '{key}': {e}", backend=self.name, original_error=e)
