"""Document versioning management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .models import Document, DocumentVersion
from .storage import StorageBackend
from .upload import UploadManager


class VersioningError(Exception):
    """Raised when a versioning operation fails."""


class VersionManager:
    """Manages document version history and restoration."""

    def __init__(self, storage: StorageBackend, upload_manager: UploadManager):
        self.storage = storage
        self.upload_manager = upload_manager
        self._versions: dict[str, list[DocumentVersion]] = {}  # doc_id -> versions
        self._documents: dict[str, Document] = {}

    def register_document(self, document: Document, version: DocumentVersion) -> None:
        """Register a newly uploaded document with its first version."""
        self._documents[document.id] = document
        self._versions[document.id] = [version]

    def create_version(
        self,
        document: Document,
        data: bytes,
        created_by: str = "",
        change_summary: str = "",
    ) -> DocumentVersion:
        """Create a new version of an existing document.

        Args:
            document: The document to version.
            data: New binary content.
            created_by: ID of the user creating the version.
            change_summary: Description of changes.

        Returns:
            The new DocumentVersion.
        """
        if document.id not in self._documents:
            raise VersioningError(
                f"Document {document.id} is not registered for versioning"
            )

        version = self.upload_manager.reupload(
            document, data, created_by, change_summary
        )
        self._versions[document.id].append(version)
        return version

    def get_version(self, doc_id: str, version_number: int) -> Optional[DocumentVersion]:
        """Get a specific version of a document."""
        versions = self._versions.get(doc_id, [])
        for v in versions:
            if v.version_number == version_number:
                return v
        return None

    def get_version_content(self, version: DocumentVersion) -> bytes:
        """Retrieve the binary content of a specific version."""
        return self.storage.read(version.storage_path)

    def list_versions(self, doc_id: str) -> list[DocumentVersion]:
        """List all versions of a document, sorted by version number."""
        versions = self._versions.get(doc_id, [])
        return sorted(versions, key=lambda v: v.version_number)

    def get_version_history(self, doc_id: str) -> list[dict]:
        """Get version history as serializable dictionaries."""
        versions = self.list_versions(doc_id)
        return [v.to_dict() for v in versions]

    def restore_version(
        self, doc_id: str, version_number: int, restored_by: str = ""
    ) -> DocumentVersion:
        """Restore a document to a previous version.

        Creates a new version with the content of the specified old version.

        Args:
            doc_id: The document ID.
            version_number: The version number to restore.
            restored_by: ID of the user restoring.

        Returns:
            The new DocumentVersion created from the restore.

        Raises:
            VersioningError: If the version doesn't exist.
        """
        target = self.get_version(doc_id, version_number)
        if target is None:
            raise VersioningError(
                f"Version {version_number} not found for document {doc_id}"
            )

        document = self._documents.get(doc_id)
        if document is None:
            raise VersioningError(f"Document {doc_id} not found")

        content = self.get_version_content(target)
        return self.create_version(
            document,
            content,
            created_by=restored_by,
            change_summary=f"Restored from version {version_number}",
        )

    def compare_versions(
        self, doc_id: str, version_a: int, version_b: int
    ) -> dict:
        """Compare two versions of a document.

        Returns:
            Dictionary with comparison details.
        """
        va = self.get_version(doc_id, version_a)
        vb = self.get_version(doc_id, version_b)

        if va is None or vb is None:
            raise VersioningError("One or both versions not found")

        return {
            "version_a": version_a,
            "version_b": version_b,
            "size_a": va.size,
            "size_b": vb.size,
            "size_diff": vb.size - va.size,
            "checksum_match": va.checksum == vb.checksum,
            "identical": va.checksum == vb.checksum,
        }

    def delete_version(self, doc_id: str, version_number: int) -> bool:
        """Delete a specific version (cannot delete the current version).

        Returns:
            True if deleted, False otherwise.
        """
        document = self._documents.get(doc_id)
        if document is None:
            return False

        if version_number == document.current_version:
            raise VersioningError("Cannot delete the current version")

        versions = self._versions.get(doc_id, [])
        target = None
        for v in versions:
            if v.version_number == version_number:
                target = v
                break

        if target is None:
            return False

        # Remove from storage
        self.storage.delete(target.storage_path)
        versions.remove(target)
        return True

    def get_latest_version(self, doc_id: str) -> Optional[DocumentVersion]:
        """Get the latest version of a document."""
        versions = self._versions.get(doc_id, [])
        if not versions:
            return None
        return max(versions, key=lambda v: v.version_number)

    def prune_old_versions(self, doc_id: str, keep: int = 10) -> int:
        """Prune old versions, keeping only the most recent `keep` versions.

        Returns:
            Number of versions pruned.
        """
        versions = self._versions.get(doc_id, [])
        if len(versions) <= keep:
            return 0

        document = self._documents.get(doc_id)
        sorted_versions = sorted(versions, key=lambda v: v.version_number)

        # Never delete the current version
        current_num = document.current_version if document else 0

        to_delete = sorted_versions[:-keep]
        pruned = 0
        for v in to_delete:
            if v.version_number != current_num:
                self.storage.delete(v.storage_path)
                versions.remove(v)
                pruned += 1

        return pruned

    def clear(self) -> None:
        """Clear all version data. Useful for testing."""
        self._versions.clear()
        self._documents.clear()
