"""Data models for the document management system."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Permission(Enum):
    """Access levels for shared documents."""

    VIEW = "view"
    EDIT = "edit"
    ADMIN = "admin"


@dataclass
class Document:
    """Represents a document in the system."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    content_type: str = "application/octet-stream"
    size: int = 0
    checksum: str = ""
    owner_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    current_version: int = 1
    is_deleted: bool = False

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "content_type": self.content_type,
            "size": self.size,
            "checksum": self.checksum,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
            "current_version": self.current_version,
            "is_deleted": self.is_deleted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Document:
        """Deserialize from dictionary."""
        doc = cls(
            id=data["id"],
            name=data["name"],
            content_type=data.get("content_type", "application/octet-stream"),
            size=data.get("size", 0),
            checksum=data.get("checksum", ""),
            owner_id=data.get("owner_id", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            current_version=data.get("current_version", 1),
            is_deleted=data.get("is_deleted", False),
        )
        if "created_at" in data:
            doc.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            doc.updated_at = datetime.fromisoformat(data["updated_at"])
        return doc


@dataclass
class DocumentVersion:
    """Represents a single version of a document."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    version_number: int = 1
    storage_path: str = ""
    size: int = 0
    checksum: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    change_summary: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "version_number": self.version_number,
            "storage_path": self.storage_path,
            "size": self.size,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "change_summary": self.change_summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DocumentVersion:
        """Deserialize from dictionary."""
        ver = cls(
            id=data["id"],
            document_id=data["document_id"],
            version_number=data["version_number"],
            storage_path=data.get("storage_path", ""),
            size=data.get("size", 0),
            checksum=data.get("checksum", ""),
            created_by=data.get("created_by", ""),
            change_summary=data.get("change_summary", ""),
        )
        if "created_at" in data:
            ver.created_at = datetime.fromisoformat(data["created_at"])
        return ver


@dataclass
class DocumentShare:
    """Represents a share link or permission grant for a document."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    shared_by: str = ""
    shared_with: str = ""
    permission: Permission = Permission.VIEW
    share_token: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    is_active: bool = True
    access_count: int = 0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "shared_by": self.shared_by,
            "shared_with": self.shared_with,
            "permission": self.permission.value,
            "share_token": self.share_token,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DocumentShare:
        """Deserialize from dictionary."""
        share = cls(
            id=data["id"],
            document_id=data["document_id"],
            shared_by=data.get("shared_by", ""),
            shared_with=data.get("shared_with", ""),
            permission=Permission(data.get("permission", "view")),
            share_token=data.get("share_token", str(uuid.uuid4())),
            is_active=data.get("is_active", True),
            access_count=data.get("access_count", 0),
        )
        if "created_at" in data:
            share.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("expires_at"):
            share.expires_at = datetime.fromisoformat(data["expires_at"])
        return share


def compute_checksum(data: bytes) -> str:
    """Compute SHA-256 checksum of binary data."""
    return hashlib.sha256(data).hexdigest()
