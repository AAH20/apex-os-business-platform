"""Document upload handling."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Optional

from .models import Document, DocumentVersion, compute_checksum
from .storage import StorageBackend


# Maximum file size: 100 MB
MAX_FILE_SIZE = 100 * 1024 * 1024

# Allowed content types (empty = allow all)
ALLOWED_CONTENT_TYPES: set[str] = set()

# Blocked extensions
BLOCKED_EXTENSIONS: set[str] = {
    ".exe", ".dll", ".bat", ".cmd", ".sh", ".php", ".jsp", ".asp",
}


class UploadError(Exception):
    """Raised when a document upload fails validation."""


class UploadManager:
    """Handles document uploads, validation, and initial storage."""

    def __init__(self, storage: StorageBackend):
        self.storage = storage

    def upload(
        self,
        name: str,
        data: bytes,
        owner_id: str = "",
        content_type: str = "",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> tuple[Document, DocumentVersion]:
        """Upload a new document.

        Args:
            name: Human-readable document name.
            data: Raw binary content.
            owner_id: ID of the uploading user.
            content_type: MIME type (auto-detected if empty).
            tags: Optional list of tags.
            metadata: Optional metadata dictionary.

        Returns:
            Tuple of (Document, DocumentVersion).

        Raises:
            UploadError: If validation fails.
        """
        self._validate(name, data)

        if not content_type:
            content_type = self._detect_content_type(name)

        checksum = compute_checksum(data)
        doc_id = self._generate_id()
        storage_path = self._storage_path(doc_id, 1)

        self.storage.save(storage_path, data)

        now = Document().created_at  # get current UTC time
        document = Document(
            id=doc_id,
            name=name,
            content_type=content_type,
            size=len(data),
            checksum=checksum,
            owner_id=owner_id,
            tags=tags or [],
            metadata=metadata or {},
            current_version=1,
        )

        version = DocumentVersion(
            document_id=doc_id,
            version_number=1,
            storage_path=storage_path,
            size=len(data),
            checksum=checksum,
            created_by=owner_id,
            change_summary="Initial upload",
        )

        return document, version

    def reupload(
        self,
        document: Document,
        data: bytes,
        uploaded_by: str = "",
        change_summary: str = "",
    ) -> DocumentVersion:
        """Upload a new version of an existing document.

        Args:
            document: The existing document.
            data: New binary content.
            uploaded_by: ID of the user uploading.
            change_summary: Description of changes.

        Returns:
            The new DocumentVersion.
        """
        self._validate(document.name, data)

        checksum = compute_checksum(data)
        new_version_num = document.current_version + 1
        storage_path = self._storage_path(document.id, new_version_num)

        self.storage.save(storage_path, data)

        version = DocumentVersion(
            document_id=document.id,
            version_number=new_version_num,
            storage_path=storage_path,
            size=len(data),
            checksum=checksum,
            created_by=uploaded_by,
            change_summary=change_summary or f"Version {new_version_num}",
        )

        # Update document metadata
        document.current_version = new_version_num
        document.size = len(data)
        document.checksum = checksum
        document.updated_at = Document().created_at

        return version

    def _validate(self, name: str, data: bytes) -> None:
        """Validate upload constraints."""
        if not name or not name.strip():
            raise UploadError("Document name cannot be empty")

        if len(data) == 0:
            raise UploadError("Document content cannot be empty")

        if len(data) > MAX_FILE_SIZE:
            raise UploadError(
                f"Document exceeds maximum size of {MAX_FILE_SIZE} bytes"
            )

        ext = Path(name).suffix.lower()
        if ext in BLOCKED_EXTENSIONS:
            raise UploadError(f"File extension '{ext}' is not allowed")

        if ALLOWED_CONTENT_TYPES:
            content_type = self._detect_content_type(name)
            if content_type not in ALLOWED_CONTENT_TYPES:
                raise UploadError(
                    f"Content type '{content_type}' is not allowed"
                )

    def _detect_content_type(self, name: str) -> str:
        """Detect MIME type from filename."""
        ctype, _ = mimetypes.guess_type(name)
        return ctype or "application/octet-stream"

    def _generate_id(self) -> str:
        """Generate a unique document ID."""
        import uuid
        return str(uuid.uuid4())

    def _storage_path(self, doc_id: str, version: int) -> str:
        """Generate a storage path for a document version."""
        return f"documents/{doc_id}/v{version}"
