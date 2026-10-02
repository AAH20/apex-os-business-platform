"""Base classes for file storage backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import BinaryIO, Dict, List, Optional
import hashlib
import io


class StorageError(Exception):
    """Raised when a storage operation fails."""

    def __init__(self, message: str, backend: str = "", original_error: Optional[Exception] = None):
        self.backend = backend
        self.original_error = original_error
        super().__init__(message)


@dataclass
class StorageObject:
    """Represents a stored file/object."""

    key: str
    size: int
    content_type: str = "application/octet-stream"
    metadata: Dict[str, str] = field(default_factory=dict)
    etag: str = ""
    last_modified: Optional[datetime] = None
    version_id: Optional[str] = None

    def __post_init__(self):
        if self.last_modified is None:
            self.last_modified = datetime.utcnow()


class StorageBackend(ABC):
    """Abstract base class for all storage backends."""

    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the storage backend."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the storage backend."""
        pass

    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream",
            metadata: Optional[Dict[str, str]] = None) -> StorageObject:
        """Upload/store a file."""
        pass

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve a file's content."""
        pass

    @abstractmethod
    def get_object(self, key: str) -> StorageObject:
        """Retrieve a file's metadata without downloading content."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a file."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a file exists."""
        pass

    @abstractmethod
    def list_objects(self, prefix: str = "") -> List[StorageObject]:
        """List files, optionally filtered by prefix."""
        pass

    @abstractmethod
    def copy(self, source_key: str, dest_key: str) -> StorageObject:
        """Copy a file within the same backend."""
        pass

    @abstractmethod
    def move(self, source_key: str, dest_key: str) -> StorageObject:
        """Move/rename a file within the same backend."""
        pass

    @abstractmethod
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Get a pre-signed URL for temporary access."""
        pass

    @abstractmethod
    def get_hash(self, key: str) -> str:
        """Get the hash/checksum of a stored file."""
        pass

    def _compute_hash(self, data: bytes) -> str:
        """Compute MD5 hash of data."""
        return hashlib.md5(data).hexdigest()

    def _ensure_connected(self) -> None:
        """Ensure the backend is connected before operations."""
        if not self._connected:
            raise StorageError(f"Backend '{self.name}' is not connected", backend=self.name)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
