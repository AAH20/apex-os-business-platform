"""Storage backends for document content."""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class StorageBackend(ABC):
    """Abstract base class for document storage backends."""

    @abstractmethod
    def save(self, key: str, data: bytes) -> str:
        """Store data and return the storage path."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """Retrieve data by key."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data by key. Returns True if deleted."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if data exists for the given key."""

    @abstractmethod
    def size(self, key: str) -> int:
        """Return the size in bytes of the stored data."""

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        """List all storage keys, optionally filtered by prefix."""


class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        """Resolve a key to a full filesystem path, preventing traversal."""
        full = (self.base_path / key).resolve()
        if not str(full).startswith(str(self.base_path)):
            raise ValueError(f"Invalid storage path: {key}")
        return full

    def save(self, key: str, data: bytes) -> str:
        """Store data at the given key path."""
        path = self._full_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        """Read data from the given key path."""
        path = self._full_path(key)
        if not path.exists():
            raise FileNotFoundError(f"No data found for key: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> bool:
        """Delete data at the given key path."""
        path = self._full_path(key)
        if path.exists():
            path.unlink()
            # Clean up empty parent directories
            parent = path.parent
            while parent != self.base_path and parent.exists():
                try:
                    parent.rmdir()
                    parent = parent.parent
                except OSError:
                    break
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if data exists at the given key path."""
        return self._full_path(key).exists()

    def size(self, key: str) -> int:
        """Return the size of data at the given key path."""
        path = self._full_path(key)
        if not path.exists():
            raise FileNotFoundError(f"No data found for key: {key}")
        return path.stat().st_size

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys under the given prefix."""
        search_path = self._full_path(prefix) if prefix else self.base_path
        if not search_path.exists():
            return []
        keys = []
        for root, _dirs, files in os.walk(search_path):
            for fname in files:
                full = Path(root) / fname
                rel = full.relative_to(self.base_path)
                keys.append(str(rel))
        return sorted(keys)

    def clear(self) -> None:
        """Remove all stored data. Useful for testing."""
        if self.base_path.exists():
            shutil.rmtree(self.base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
