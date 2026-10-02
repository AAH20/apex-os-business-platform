"""Tests for the document management system."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from apex_os_bp.documents import (
    Document,
    DocumentShare,
    DocumentVersion,
    LocalStorage,
    Permission,
    SearchEngine,
    ShareManager,
    UploadManager,
    VersionManager,
)
from apex_os_bp.documents.sharing import SharingError
from apex_os_bp.documents.upload import UploadError
from apex_os_bp.documents.versioning import VersioningError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def storage(tmp_path):
    """Create a temporary storage backend."""
    return LocalStorage(tmp_path / "doc_storage")


@pytest.fixture
def upload_manager(storage):
    """Create an upload manager."""
    return UploadManager(storage)


@pytest.fixture
def version_manager(storage, upload_manager):
    """Create a version manager."""
    return VersionManager(storage, upload_manager)


@pytest.fixture
def share_manager():
    """Create a share manager."""
    return ShareManager()


@pytest.fixture
def search_engine():
    """Create a search engine."""
    return SearchEngine()


@pytest.fixture
def sample_pdf():
    """Sample PDF-like binary content."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


@pytest.fixture
def sample_text():
    """Sample text content."""
    return b"Hello World! This is a test document for the APEX-OS platform.\n"


@pytest.fixture
def sample_document(upload_manager, sample_text):
    """Upload a sample document and return (document, version)."""
    return upload_manager.upload(
        name="test_document.txt",
        data=sample_text,
        owner_id="user_001",
        tags=["test", "sample"],
        metadata={"department": "engineering", "project": "apex"},
    )


# ===========================================================================
# 1. Document Upload Tests
# ===========================================================================


class TestDocumentUpload:
    """Tests for document upload functionality."""

    def test_upload_basic(self, upload_manager, sample_text):
        """Test basic document upload."""
        doc, ver = upload_manager.upload(
            name="report.pdf",
            data=sample_text,
            owner_id="user_42",
        )

        assert doc.id is not None
        assert doc.name == "report.pdf"
        assert doc.size == len(sample_text)
        assert doc.checksum != ""
        assert doc.owner_id == "user_42"
        assert doc.current_version == 1
        assert not doc.is_deleted

        assert ver.document_id == doc.id
        assert ver.version_number == 1
        assert ver.size == len(sample_text)
        assert ver.checksum == doc.checksum
        assert ver.change_summary == "Initial upload"

    def test_upload_with_tags_and_metadata(self, upload_manager, sample_text):
        """Test upload with tags and metadata."""
        doc, _ = upload_manager.upload(
            name="tagged_doc.txt",
            data=sample_text,
            owner_id="user_1",
            tags=["important", "q4", "finance"],
            metadata={"author": "Alice", "department": "Finance", "year": 2026},
        )

        assert doc.tags == ["important", "q4", "finance"]
        assert doc.metadata["author"] == "Alice"
        assert doc.metadata["department"] == "Finance"
        assert doc.metadata["year"] == 2026

    def test_upload_empty_name_raises_error(self, upload_manager, sample_text):
        """Test that empty document name is rejected."""
        with pytest.raises(UploadError, match="name cannot be empty"):
            upload_manager.upload(name="", data=sample_text)

        with pytest.raises(UploadError, match="name cannot be empty"):
            upload_manager.upload(name="   ", data=sample_text)

    def test_upload_empty_content_raises_error(self, upload_manager):
        """Test that empty content is rejected."""
        with pytest.raises(UploadError, match="content cannot be empty"):
            upload_manager.upload(name="empty.txt", data=b"")

    def test_upload_blocked_extension_raises_error(self, upload_manager):
        """Test that blocked file extensions are rejected."""
        with pytest.raises(UploadError, match="not allowed"):
            upload_manager.upload(name="malware.exe", data=b"evil payload")

        with pytest.raises(UploadError, match="not allowed"):
            upload_manager.upload(name="script.sh", data=b"#!/bin/bash\nrm -rf /")

    def test_upload_oversized_raises_error(self, upload_manager):
        """Test that oversized files are rejected."""
        huge_data = b"x" * (101 * 1024 * 1024)  # 101 MB
        with pytest.raises(UploadError, match="exceeds maximum size"):
            upload_manager.upload(name="huge.bin", data=huge_data)

    def test_upload_auto_detects_content_type(self, upload_manager, sample_text):
        """Test MIME type auto-detection."""
        doc, _ = upload_manager.upload(name="data.json", data=b'{"key": "val"}')
        assert doc.content_type == "application/json"

        doc2, _ = upload_manager.upload(name="page.html", data=b"<html></html>")
        assert doc2.content_type == "text/html"

    def test_upload_explicit_content_type(self, upload_manager, sample_text):
        """Test explicit content type override."""
        doc, _ = upload_manager.upload(
            name="file.dat",
            data=sample_text,
            content_type="application/pdf",
        )
        assert doc.content_type == "application/pdf"

    def test_upload_stores_data(self, upload_manager, storage, sample_text):
        """Test that uploaded data is actually stored."""
        doc, ver = upload_manager.upload(name="stored.txt", data=sample_text)
        assert storage.exists(ver.storage_path)
        retrieved = storage.read(ver.storage_path)
        assert retrieved == sample_text

    def test_reupload_creates_new_version(self, upload_manager, sample_text):
        """Test re-uploading creates a new version."""
        doc, ver1 = upload_manager.upload(name="versioned.txt", data=sample_text)

        new_content = b"Updated content for version 2"
        ver2 = upload_manager.reupload(
            doc, new_content, uploaded_by="user_1", change_summary="Fixed typo"
        )

        assert ver2.version_number == 2
        assert ver2.size == len(new_content)
        assert ver2.change_summary == "Fixed typo"
        assert doc.current_version == 2
        assert doc.size == len(new_content)

    def test_upload_generates_unique_ids(self, upload_manager, sample_text):
        """Test that each upload gets a unique document ID."""
        doc1, _ = upload_manager.upload(name="doc1.txt", data=sample_text)
        doc2, _ = upload_manager.upload(name="doc2.txt", data=sample_text)
        assert doc1.id != doc2.id

    def test_upload_checksum_is_sha256(self, upload_manager, sample_text):
        """Test that checksum is computed correctly."""
        import hashlib

        doc, _ = upload_manager.upload(name="checksum_test.txt", data=sample_text)
        expected = hashlib.sha256(sample_text).hexdigest()
        assert doc.checksum == expected


# ===========================================================================
# 2. Document Storage Tests
# ===========================================================================


class TestDocumentStorage:
    """Tests for document storage backend."""

    def test_save_and_read(self, storage, sample_text):
        """Test basic save and read."""
        storage.save("test/file.txt", sample_text)
        assert storage.read("test/file.txt") == sample_text

    def test_save_creates_directories(self, storage, sample_text):
        """Test that save creates intermediate directories."""
        storage.save("a/b/c/d/file.txt", sample_text)
        assert storage.exists("a/b/c/d/file.txt")

    def test_read_nonexistent_raises_error(self, storage):
        """Test reading a non-existent key raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            storage.read("no/such/file.txt")

    def test_delete(self, storage, sample_text):
        """Test deletion of stored data."""
        storage.save("to_delete.txt", sample_text)
        assert storage.exists("to_delete.txt")

        result = storage.delete("to_delete.txt")
        assert result is True
        assert not storage.exists("to_delete.txt")

    def test_delete_nonexistent_returns_false(self, storage):
        """Test deleting non-existent key returns False."""
        result = storage.delete("nonexistent.txt")
        assert result is False

    def test_exists(self, storage, sample_text):
        """Test existence check."""
        assert not storage.exists("check.txt")
        storage.save("check.txt", sample_text)
        assert storage.exists("check.txt")

    def test_size(self, storage, sample_text):
        """Test size reporting."""
        storage.save("sized.txt", sample_text)
        assert storage.size("sized.txt") == len(sample_text)

    def test_size_nonexistent_raises_error(self, storage):
        """Test size of non-existent key raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            storage.size("nonexistent.txt")

    def test_list_keys(self, storage, sample_text):
        """Test key listing."""
        storage.save("docs/a.txt", sample_text)
        storage.save("docs/b.txt", sample_text)
        storage.save("docs/sub/c.txt", sample_text)
        storage.save("other/d.txt", sample_text)

        all_keys = storage.list_keys()
        assert len(all_keys) == 4

        docs_keys = storage.list_keys("docs")
        assert len(docs_keys) == 3

        sub_keys = storage.list_keys("docs/sub")
        assert len(sub_keys) == 1

    def test_list_keys_nonexistent_prefix(self, storage):
        """Test listing with non-existent prefix returns empty list."""
        assert storage.list_keys("nonexistent") == []

    def test_path_traversal_prevention(self, storage, sample_text):
        """Test that path traversal attacks are prevented."""
        with pytest.raises(ValueError, match="Invalid storage path"):
            storage.save("../escape.txt", sample_text)

        with pytest.raises(ValueError, match="Invalid storage path"):
            storage.save("docs/../../escape.txt", sample_text)

    def test_clear(self, storage, sample_text):
        """Test clearing all stored data."""
        storage.save("a.txt", sample_text)
        storage.save("b.txt", sample_text)
        assert len(storage.list_keys()) == 2

        storage.clear()
        assert len(storage.list_keys()) == 0

    def test_overwrite(self, storage, sample_text):
        """Test overwriting existing data."""
        storage.save("overwrite.txt", b"old content")
        storage.save("overwrite.txt", sample_text)
        assert storage.read("overwrite.txt") == sample_text


# ===========================================================================
# 3. Document Search Tests
# ===========================================================================


class TestDocumentSearch:
    """Tests for document search functionality."""

    def test_add_and_search_by_name(self, search_engine, sample_document):
        """Test searching by document name."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        results = search_engine.search("test_document")
        assert len(results) == 1
        assert results[0].document.id == doc.id
        assert results[0].score > 0

    def test_search_by_tag(self, search_engine, sample_document):
        """Test searching by tag."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        results = search_engine.search("sample")
        assert len(results) == 1
        assert "tags" in results[0].matched_fields

    def test_search_by_metadata(self, search_engine, sample_document):
        """Test searching by metadata value."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        results = search_engine.search("engineering")
        assert len(results) == 1
        assert "metadata" in results[0].matched_fields

    def test_search_by_content(self, search_engine, sample_document, sample_text):
        """Test searching by document content."""
        doc, _ = sample_document
        search_engine.add_document(doc, content=sample_text)

        results = search_engine.search("APEX-OS")
        assert len(results) >= 1

    def test_search_no_results(self, search_engine, sample_document):
        """Test search with no matching results."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        results = search_engine.search("nonexistent_xyz_123")
        assert len(results) == 0

    def test_search_with_tag_filter(self, search_engine, upload_manager, sample_text):
        """Test search with tag filtering."""
        doc1, _ = upload_manager.upload(
            name="doc1.txt", data=sample_text, tags=["finance", "q4"]
        )
        doc2, _ = upload_manager.upload(
            name="doc2.txt", data=sample_text, tags=["finance", "q3"]
        )
        doc3, _ = upload_manager.upload(
            name="doc3.txt", data=sample_text, tags=["engineering"]
        )

        search_engine.add_document(doc1)
        search_engine.add_document(doc2)
        search_engine.add_document(doc3)

        results = search_engine.search("doc", tags=["finance"])
        assert len(results) == 2

        results = search_engine.search("doc", tags=["finance", "q4"])
        assert len(results) == 1
        assert results[0].document.id == doc1.id

    def test_search_with_owner_filter(self, search_engine, upload_manager, sample_text):
        """Test search with owner filtering."""
        doc1, _ = upload_manager.upload(
            name="alpha_doc.txt", data=sample_text, owner_id="user_a"
        )
        doc2, _ = upload_manager.upload(
            name="beta_doc.txt", data=sample_text, owner_id="user_b"
        )

        search_engine.add_document(doc1)
        search_engine.add_document(doc2)

        results = search_engine.search("alpha", owner_id="user_a")
        assert len(results) == 1
        assert results[0].document.id == doc1.id

        results = search_engine.search("beta", owner_id="user_a")
        assert len(results) == 0

    def test_search_pagination(self, search_engine, upload_manager, sample_text):
        """Test search result pagination."""
        for i in range(10):
            doc, _ = upload_manager.upload(
                name=f"page_doc_{i}.txt", data=sample_text
            )
            search_engine.add_document(doc)

        results = search_engine.search("page_doc", limit=3)
        assert len(results) == 3

        results_page2 = search_engine.search("page_doc", limit=3, offset=3)
        assert len(results_page2) == 3

        # Ensure no overlap
        ids_page1 = {r.document.id for r in results}
        ids_page2 = {r.document.id for r in results_page2}
        assert ids_page1.isdisjoint(ids_page2)

    def test_search_result_ordering(self, search_engine, upload_manager, sample_text):
        """Test that results are ordered by relevance score."""
        doc1, _ = upload_manager.upload(
            name="exact_match.txt", data=sample_text, tags=["exact"]
        )
        doc2, _ = upload_manager.upload(
            name="partial.txt", data=sample_text, tags=["exact", "extra"]
        )

        search_engine.add_document(doc1)
        search_engine.add_document(doc2)

        results = search_engine.search("exact")
        assert len(results) == 2
        # Both should have positive scores
        assert all(r.score > 0 for r in results)

    def test_search_by_name_prefix(self, search_engine, upload_manager, sample_text):
        """Test name prefix search."""
        doc1, _ = upload_manager.upload(name="report_2026_q1.txt", data=sample_text)
        doc2, _ = upload_manager.upload(name="report_2026_q2.txt", data=sample_text)
        doc3, _ = upload_manager.upload(name="summary.txt", data=sample_text)

        search_engine.add_document(doc1)
        search_engine.add_document(doc2)
        search_engine.add_document(doc3)

        results = search_engine.search_by_name("report_2026")
        assert len(results) == 2

    def test_remove_document(self, search_engine, sample_document):
        """Test removing a document from search index."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        results = search_engine.search("test_document")
        assert len(results) == 1

        search_engine.remove_document(doc.id)
        results = search_engine.search("test_document")
        assert len(results) == 0

    def test_update_document(self, search_engine, sample_document):
        """Test updating a document in the search index."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        doc.name = "renamed_document.pdf"
        doc.tags = ["updated", "new_tags"]
        search_engine.update_document(doc)

        # Old content tokens should not match (content was "Hello World!...")
        results = search_engine.search("Hello")
        assert len(results) == 0

        # New name should match
        results = search_engine.search("renamed")
        assert len(results) == 1

    def test_search_excludes_deleted(self, search_engine, sample_document):
        """Test that deleted documents don't appear in search results."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        doc.is_deleted = True
        search_engine.update_document(doc)

        results = search_engine.search("test_document")
        assert len(results) == 0

    def test_search_empty_query_no_tags(self, search_engine, sample_document):
        """Test that empty query with no tags returns no results."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        results = search_engine.search("")
        assert len(results) == 0

    def test_search_stats(self, search_engine, sample_document):
        """Test search index statistics."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        stats = search_engine.get_stats()
        assert stats["total_documents"] == 1
        assert stats["total_tokens"] > 0

    def test_clear_search_index(self, search_engine, sample_document):
        """Test clearing the search index."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        search_engine.clear()
        stats = search_engine.get_stats()
        assert stats["total_documents"] == 0
        assert stats["total_tokens"] == 0

    def test_search_case_insensitive(self, search_engine, sample_document):
        """Test that search is case-insensitive."""
        doc, _ = sample_document
        search_engine.add_document(doc)

        results_lower = search_engine.search("test_document")
        results_upper = search_engine.search("TEST_DOCUMENT")
        results_mixed = search_engine.search("TeSt_DoCuMeNt")

        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert len(results_mixed) == 1

    def test_search_name_boost(self, search_engine, upload_manager, sample_text):
        """Test that exact name matches get a score boost."""
        doc1, _ = upload_manager.upload(
            name="budget_report.xlsx", data=sample_text, tags=["finance"]
        )
        doc2, _ = upload_manager.upload(
            name="random_name.txt",
            data=sample_text,
            tags=["finance", "budget", "report"],
        )

        search_engine.add_document(doc1)
        search_engine.add_document(doc2)

        results = search_engine.search("budget_report")
        # doc1 has exact name match, should rank higher
        assert results[0].document.id == doc1.id
        assert results[0].score > results[1].score


# ===========================================================================
# 4. Document Versioning Tests
# ===========================================================================


class TestDocumentVersioning:
    """Tests for document versioning functionality."""

    def test_register_document(self, version_manager, sample_document):
        """Test registering a document for versioning."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        versions = version_manager.list_versions(doc.id)
        assert len(versions) == 1
        assert versions[0].version_number == 1

    def test_create_version(self, version_manager, sample_document, sample_text):
        """Test creating a new version."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        new_content = b"Version 2 content with more data"
        ver2 = version_manager.create_version(
            doc, new_content, created_by="user_1", change_summary="Added section"
        )

        assert ver2.version_number == 2
        assert ver2.size == len(new_content)
        assert ver2.change_summary == "Added section"
        assert doc.current_version == 2

    def test_get_version(self, version_manager, sample_document):
        """Test retrieving a specific version."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        retrieved = version_manager.get_version(doc.id, 1)
        assert retrieved is not None
        assert retrieved.version_number == 1

        not_found = version_manager.get_version(doc.id, 99)
        assert not_found is None

    def test_get_version_content(self, version_manager, sample_document, sample_text):
        """Test retrieving version content."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        content = version_manager.get_version_content(ver)
        assert content == sample_text

    def test_list_versions(self, version_manager, sample_document, sample_text):
        """Test listing all versions."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        # Create additional versions
        for i in range(3):
            version_manager.create_version(
                doc, f"Content v{i+2}".encode(), change_summary=f"Update {i+2}"
            )

        versions = version_manager.list_versions(doc.id)
        assert len(versions) == 4
        assert [v.version_number for v in versions] == [1, 2, 3, 4]

    def test_get_version_history(self, version_manager, sample_document):
        """Test version history serialization."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        history = version_manager.get_version_history(doc.id)
        assert len(history) == 1
        assert history[0]["version_number"] == 1
        assert history[0]["document_id"] == doc.id

    def test_restore_version(self, version_manager, sample_document, sample_text):
        """Test restoring a previous version."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        # Create version 2
        new_content = b"Modified content"
        version_manager.create_version(doc, new_content, change_summary="Changed")

        # Restore to version 1
        restored = version_manager.restore_version(doc.id, 1, restored_by="admin")

        assert restored.version_number == 3
        assert "Restored from version 1" in restored.change_summary

        # Content should match original
        content = version_manager.get_version_content(restored)
        assert content == sample_text

    def test_restore_nonexistent_version_raises_error(self, version_manager, sample_document):
        """Test restoring a non-existent version raises error."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        with pytest.raises(VersioningError, match="not found"):
            version_manager.restore_version(doc.id, 99)

    def test_compare_versions(self, version_manager, sample_document, sample_text):
        """Test comparing two versions."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        new_content = b"Modified content - longer than before"
        ver2 = version_manager.create_version(doc, new_content, change_summary="Changed")

        comparison = version_manager.compare_versions(doc.id, 1, 2)
        assert comparison["version_a"] == 1
        assert comparison["version_b"] == 2
        assert comparison["size_a"] == len(sample_text)
        assert comparison["size_b"] == len(new_content)
        assert comparison["size_diff"] == len(new_content) - len(sample_text)
        assert comparison["identical"] is False

    def test_compare_identical_versions(self, version_manager, sample_document, sample_text):
        """Test comparing a version with itself."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        comparison = version_manager.compare_versions(doc.id, 1, 1)
        assert comparison["identical"] is True
        assert comparison["checksum_match"] is True

    def test_delete_version(self, version_manager, sample_document, sample_text):
        """Test deleting a non-current version."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        # Create versions 2 and 3
        version_manager.create_version(doc, b"v2", change_summary="v2")
        ver3 = version_manager.create_version(doc, b"v3", change_summary="v3")

        # Delete version 2
        result = version_manager.delete_version(doc.id, 2)
        assert result is True

        versions = version_manager.list_versions(doc.id)
        version_numbers = [v.version_number for v in versions]
        assert 2 not in version_numbers
        assert len(versions) == 2

    def test_delete_current_version_raises_error(self, version_manager, sample_document):
        """Test that deleting the current version is prevented."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        with pytest.raises(VersioningError, match="Cannot delete the current version"):
            version_manager.delete_version(doc.id, 1)

    def test_get_latest_version(self, version_manager, sample_document):
        """Test getting the latest version."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        latest = version_manager.get_latest_version(doc.id)
        assert latest is not None
        assert latest.version_number == 1

        # Add more versions
        version_manager.create_version(doc, b"v2", change_summary="v2")
        version_manager.create_version(doc, b"v3", change_summary="v3")

        latest = version_manager.get_latest_version(doc.id)
        assert latest.version_number == 3

    def test_prune_old_versions(self, version_manager, sample_document, sample_text):
        """Test pruning old versions."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        # Create 5 more versions (total 6)
        for i in range(5):
            version_manager.create_version(
                doc, f"Content v{i+2}".encode(), change_summary=f"v{i+2}"
            )

        assert len(version_manager.list_versions(doc.id)) == 6

        # Keep only 3
        pruned = version_manager.prune_old_versions(doc.id, keep=3)
        assert pruned == 3
        assert len(version_manager.list_versions(doc.id)) == 3

    def test_prune_does_not_delete_current(self, version_manager, sample_document):
        """Test that pruning never deletes the current version."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        # Create 3 more versions
        for i in range(3):
            version_manager.create_version(
                doc, f"v{i+2}".encode(), change_summary=f"v{i+2}"
            )

        # Try to keep only 1 (which would be the current version)
        pruned = version_manager.prune_old_versions(doc.id, keep=1)
        assert pruned == 3

        versions = version_manager.list_versions(doc.id)
        assert len(versions) == 1
        assert versions[0].version_number == doc.current_version

    def test_unregistered_document_raises_error(self, version_manager, sample_text):
        """Test that operations on unregistered documents raise errors."""
        doc = Document(name="unregistered.txt")

        with pytest.raises(VersioningError, match="not registered"):
            version_manager.create_version(doc, sample_text)

    def test_clear_version_data(self, version_manager, sample_document):
        """Test clearing all version data."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        version_manager.clear()
        versions = version_manager.list_versions(doc.id)
        assert len(versions) == 0


# ===========================================================================
# 5. Document Sharing Tests
# ===========================================================================


class TestDocumentSharing:
    """Tests for document sharing functionality."""

    def test_create_share(self, share_manager, sample_document):
        """Test creating a share link."""
        doc, _ = sample_document
        share = share_manager.create_share(
            document=doc,
            shared_by="user_1",
            shared_with="user_2",
            permission=Permission.VIEW,
        )

        assert share.id is not None
        assert share.document_id == doc.id
        assert share.shared_by == "user_1"
        assert share.shared_with == "user_2"
        assert share.permission == Permission.VIEW
        assert share.share_token is not None
        assert share.is_active is True
        assert share.access_count == 0

    def test_create_share_with_expiration(self, share_manager, sample_document):
        """Test creating a share with expiration."""
        doc, _ = sample_document
        share = share_manager.create_share(
            document=doc,
            shared_by="user_1",
            expires_in_days=7,
        )

        assert share.expires_at is not None
        expected = datetime.now(timezone.utc) + timedelta(days=7)
        # Allow 1 second tolerance
        assert abs((share.expires_at - expected).total_seconds()) < 1

    def test_get_share(self, share_manager, sample_document):
        """Test retrieving a share by ID."""
        doc, _ = sample_document
        share = share_manager.create_share(document=doc, shared_by="user_1")

        retrieved = share_manager.get_share(share.id)
        assert retrieved is not None
        assert retrieved.id == share.id

        not_found = share_manager.get_share("nonexistent")
        assert not_found is None

    def test_get_share_by_token(self, share_manager, sample_document):
        """Test retrieving a share by token."""
        doc, _ = sample_document
        share = share_manager.create_share(document=doc, shared_by="user_1")

        retrieved = share_manager.get_share_by_token(share.share_token)
        assert retrieved is not None
        assert retrieved.id == share.id

        not_found = share_manager.get_share_by_token("invalid_token")
        assert not_found is None

    def test_validate_access_valid(self, share_manager, sample_document):
        """Test validating a valid share token."""
        doc, _ = sample_document
        share = share_manager.create_share(
            document=doc, shared_by="user_1", permission=Permission.EDIT
        )

        validated = share_manager.validate_access(share.share_token)
        assert validated.id == share.id
        assert validated.access_count == 1

    def test_validate_access_invalid_token(self, share_manager):
        """Test validating an invalid token raises error."""
        with pytest.raises(SharingError, match="Invalid share token"):
            share_manager.validate_access("bad_token")

    def test_validate_access_revoked(self, share_manager, sample_document):
        """Test validating a revoked share raises error."""
        doc, _ = sample_document
        share = share_manager.create_share(document=doc, shared_by="user_1")

        share_manager.revoke_share(share.id)

        with pytest.raises(SharingError, match="revoked"):
            share_manager.validate_access(share.share_token)

    def test_validate_access_expired(self, share_manager, sample_document):
        """Test validating an expired share raises error."""
        doc, _ = sample_document
        share = share_manager.create_share(
            document=doc, shared_by="user_1", expires_in_days=-1
        )

        with pytest.raises(SharingError, match="expired"):
            share_manager.validate_access(share.share_token)

    def test_validate_access_insufficient_permission(self, share_manager, sample_document):
        """Test that insufficient permissions are rejected."""
        doc, _ = sample_document
        share = share_manager.create_share(
            document=doc, shared_by="user_1", permission=Permission.VIEW
        )

        # VIEW should work for VIEW requirement
        share_manager.validate_access(share.share_token, Permission.VIEW)

        # VIEW should NOT work for EDIT requirement
        with pytest.raises(SharingError, match="Insufficient permissions"):
            share_manager.validate_access(share.share_token, Permission.EDIT)

    def test_revoke_share(self, share_manager, sample_document):
        """Test revoking a share."""
        doc, _ = sample_document
        share = share_manager.create_share(document=doc, shared_by="user_1")

        result = share_manager.revoke_share(share.id)
        assert result is True

        retrieved = share_manager.get_share(share.id)
        assert retrieved.is_active is False

    def test_revoke_nonexistent_share(self, share_manager):
        """Test revoking a non-existent share returns False."""
        result = share_manager.revoke_share("nonexistent")
        assert result is False

    def test_revoke_all_shares(self, share_manager, sample_document):
        """Test revoking all shares for a document."""
        doc, _ = sample_document
        share_manager.create_share(document=doc, shared_by="user_1")
        share_manager.create_share(document=doc, shared_by="user_1")
        share_manager.create_share(document=doc, shared_by="user_2")

        count = share_manager.revoke_all_shares(doc.id)
        assert count == 3

        active = share_manager.list_active_shares(doc.id)
        assert len(active) == 0

    def test_update_permission(self, share_manager, sample_document):
        """Test updating share permission."""
        doc, _ = sample_document
        share = share_manager.create_share(
            document=doc, shared_by="user_1", permission=Permission.VIEW
        )

        updated = share_manager.update_permission(share.id, Permission.EDIT)
        assert updated.permission == Permission.EDIT

    def test_update_permission_nonexistent(self, share_manager):
        """Test updating permission on non-existent share raises error."""
        with pytest.raises(SharingError, match="not found"):
            share_manager.update_permission("nonexistent", Permission.ADMIN)

    def test_list_shares(self, share_manager, sample_document):
        """Test listing shares for a document."""
        doc, _ = sample_document
        share_manager.create_share(document=doc, shared_by="user_1")
        share_manager.create_share(document=doc, shared_by="user_2")

        shares = share_manager.list_shares(doc.id)
        assert len(shares) == 2

    def test_list_active_shares(self, share_manager, sample_document):
        """Test listing only active shares."""
        doc, _ = sample_document
        share1 = share_manager.create_share(document=doc, shared_by="user_1")
        share2 = share_manager.create_share(document=doc, shared_by="user_2")
        share_manager.create_share(
            document=doc, shared_by="user_3", expires_in_days=-1
        )

        # Revoke one
        share_manager.revoke_share(share1.id)

        active = share_manager.list_active_shares(doc.id)
        assert len(active) == 1
        assert active[0].id == share2.id

    def test_get_share_stats(self, share_manager, sample_document):
        """Test share statistics."""
        doc, _ = sample_document
        share1 = share_manager.create_share(document=doc, shared_by="user_1")
        share2 = share_manager.create_share(document=doc, shared_by="user_2")

        # Simulate some access
        share_manager.validate_access(share1.share_token)
        share_manager.validate_access(share1.share_token)
        share_manager.validate_access(share2.share_token)

        stats = share_manager.get_share_stats(doc.id)
        assert stats["total_shares"] == 2
        assert stats["active_shares"] == 2
        assert stats["total_access_count"] == 3

    def test_cleanup_expired(self, share_manager, sample_document):
        """Test cleaning up expired shares."""
        doc, _ = sample_document
        share_manager.create_share(document=doc, shared_by="user_1", expires_in_days=-1)
        share_manager.create_share(document=doc, shared_by="user_2", expires_in_days=-2)
        share_manager.create_share(document=doc, shared_by="user_3", expires_in_days=7)

        count = share_manager.cleanup_expired()
        assert count == 2

        active = share_manager.list_active_shares(doc.id)
        assert len(active) == 1

    def test_clear_share_data(self, share_manager, sample_document):
        """Test clearing all share data."""
        doc, _ = sample_document
        share_manager.create_share(document=doc, shared_by="user_1")

        share_manager.clear()
        shares = share_manager.list_shares(doc.id)
        assert len(shares) == 0

    def test_share_token_uniqueness(self, share_manager, sample_document):
        """Test that each share gets a unique token."""
        doc, _ = sample_document
        tokens = set()
        for _ in range(100):
            share = share_manager.create_share(document=doc, shared_by="user_1")
            tokens.add(share.share_token)

        assert len(tokens) == 100

    def test_permission_hierarchy(self, share_manager, sample_document):
        """Test that permission hierarchy works correctly."""
        doc, _ = sample_document

        view_share = share_manager.create_share(
            document=doc, shared_by="user_1", permission=Permission.VIEW
        )
        edit_share = share_manager.create_share(
            document=doc, shared_by="user_1", permission=Permission.EDIT
        )
        admin_share = share_manager.create_share(
            document=doc, shared_by="user_1", permission=Permission.ADMIN
        )

        # ADMIN can do everything
        share_manager.validate_access(admin_share.share_token, Permission.VIEW)
        share_manager.validate_access(admin_share.share_token, Permission.EDIT)
        share_manager.validate_access(admin_share.share_token, Permission.ADMIN)

        # EDIT can view and edit
        share_manager.validate_access(edit_share.share_token, Permission.VIEW)
        share_manager.validate_access(edit_share.share_token, Permission.EDIT)
        with pytest.raises(SharingError):
            share_manager.validate_access(edit_share.share_token, Permission.ADMIN)

        # VIEW can only view
        share_manager.validate_access(view_share.share_token, Permission.VIEW)
        with pytest.raises(SharingError):
            share_manager.validate_access(view_share.share_token, Permission.EDIT)

    def test_access_count_increments(self, share_manager, sample_document):
        """Test that access counter increments on each validation."""
        doc, _ = sample_document
        share = share_manager.create_share(document=doc, shared_by="user_1")

        assert share.access_count == 0

        share_manager.validate_access(share.share_token)
        assert share.access_count == 1

        share_manager.validate_access(share.share_token)
        assert share.access_count == 2

        share_manager.validate_access(share.share_token)
        assert share.access_count == 3


# ===========================================================================
# Model Serialization Tests
# ===========================================================================


class TestModelSerialization:
    """Tests for model serialization and deserialization."""

    def test_document_to_dict(self, sample_document):
        """Test Document serialization."""
        doc, _ = sample_document
        data = doc.to_dict()

        assert data["id"] == doc.id
        assert data["name"] == doc.name
        assert data["size"] == doc.size
        assert data["checksum"] == doc.checksum
        assert data["owner_id"] == doc.owner_id
        assert "created_at" in data
        assert "updated_at" in data

    def test_document_from_dict(self, sample_document):
        """Test Document deserialization."""
        doc, _ = sample_document
        data = doc.to_dict()
        restored = Document.from_dict(data)

        assert restored.id == doc.id
        assert restored.name == doc.name
        assert restored.size == doc.size
        assert restored.checksum == doc.checksum
        assert restored.owner_id == doc.owner_id
        assert restored.tags == doc.tags
        assert restored.metadata == doc.metadata
        assert restored.current_version == doc.current_version

    def test_document_version_to_dict(self, sample_document):
        """Test DocumentVersion serialization."""
        _, ver = sample_document
        data = ver.to_dict()

        assert data["id"] == ver.id
        assert data["document_id"] == ver.document_id
        assert data["version_number"] == ver.version_number
        assert data["storage_path"] == ver.storage_path

    def test_document_version_from_dict(self, sample_document):
        """Test DocumentVersion deserialization."""
        _, ver = sample_document
        data = ver.to_dict()
        restored = DocumentVersion.from_dict(data)

        assert restored.id == ver.id
        assert restored.document_id == ver.document_id
        assert restored.version_number == ver.version_number
        assert restored.storage_path == ver.storage_path

    def test_document_share_to_dict(self, share_manager, sample_document):
        """Test DocumentShare serialization."""
        doc, _ = sample_document
        share = share_manager.create_share(document=doc, shared_by="user_1")
        data = share.to_dict()

        assert data["id"] == share.id
        assert data["document_id"] == share.document_id
        assert data["permission"] == "view"
        assert data["share_token"] == share.share_token

    def test_document_share_from_dict(self, share_manager, sample_document):
        """Test DocumentShare deserialization."""
        doc, _ = sample_document
        share = share_manager.create_share(
            document=doc, shared_by="user_1", permission=Permission.EDIT
        )
        data = share.to_dict()
        restored = DocumentShare.from_dict(data)

        assert restored.id == share.id
        assert restored.document_id == share.document_id
        assert restored.permission == Permission.EDIT
        assert restored.share_token == share.share_token


# ===========================================================================
# Integration Tests
# ===========================================================================


class TestDocumentManagementIntegration:
    """End-to-end integration tests for the document management system."""

    def test_full_document_lifecycle(
        self, storage, upload_manager, version_manager, share_manager, search_engine, sample_text
    ):
        """Test complete lifecycle: upload -> version -> share -> search."""
        # 1. Upload
        doc, ver = upload_manager.upload(
            name="lifecycle_test.txt",
            data=sample_text,
            owner_id="user_1",
            tags=["test", "lifecycle"],
            metadata={"project": "apex-os"},
        )
        version_manager.register_document(doc, ver)
        search_engine.add_document(doc, content=sample_text)

        # Verify upload
        assert doc.id is not None
        assert doc.current_version == 1

        # 2. Create new version
        new_content = b"Updated lifecycle content"
        ver2 = version_manager.create_version(
            doc, new_content, created_by="user_1", change_summary="Updated"
        )
        assert ver2.version_number == 2
        assert doc.current_version == 2

        # 3. Share the document
        share = share_manager.create_share(
            document=doc,
            shared_by="user_1",
            shared_with="user_2",
            permission=Permission.VIEW,
        )
        validated = share_manager.validate_access(share.share_token)
        assert validated.document_id == doc.id

        # 4. Search finds the document
        results = search_engine.search("lifecycle")
        assert len(results) >= 1
        found_ids = [r.document.id for r in results]
        assert doc.id in found_ids

        # 5. Restore previous version
        restored = version_manager.restore_version(doc.id, 1)
        content = version_manager.get_version_content(restored)
        assert content == sample_text

        # 6. Revoke share
        share_manager.revoke_share(share.id)
        with pytest.raises(SharingError):
            share_manager.validate_access(share.share_token)

        # 7. Remove from search
        search_engine.remove_document(doc.id)
        results = search_engine.search("lifecycle")
        found_ids = [r.document.id for r in results]
        assert doc.id not in found_ids

    def test_multiple_documents_versioning_and_sharing(
        self, upload_manager, version_manager, share_manager, search_engine, sample_text
    ):
        """Test managing multiple documents simultaneously."""
        docs = []
        for i in range(5):
            doc, ver = upload_manager.upload(
                name=f"multi_doc_{i}.txt",
                data=f"Content for document {i}".encode(),
                owner_id=f"user_{i}",
                tags=["multi", f"doc_{i}"],
            )
            version_manager.register_document(doc, ver)
            search_engine.add_document(doc)
            docs.append(doc)

        # Version each document differently
        for i, doc in enumerate(docs):
            for v in range(i + 1):
                version_manager.create_version(
                    doc, f"Version {v+2} of doc {i}".encode(), change_summary=f"v{v+2}"
                )

        # Share all documents
        for doc in docs:
            share_manager.create_share(
                document=doc, shared_by=doc.owner_id, permission=Permission.VIEW
            )

        # Verify version counts
        for i, doc in enumerate(docs):
            versions = version_manager.list_versions(doc.id)
            assert len(versions) == i + 2  # initial + (i+1) more

        # Verify search
        results = search_engine.search("multi_doc")
        assert len(results) == 5

        # Verify shares
        for doc in docs:
            shares = share_manager.list_shares(doc.id)
            assert len(shares) == 1

    def test_concurrent_version_creation(
        self, version_manager, sample_document, sample_text
    ):
        """Test creating multiple versions in sequence."""
        doc, ver = sample_document
        version_manager.register_document(doc, ver)

        # Create 20 versions
        for i in range(20):
            version_manager.create_version(
                doc, f"Content version {i+2}".encode(), change_summary=f"v{i+2}"
            )

        versions = version_manager.list_versions(doc.id)
        assert len(versions) == 21
        assert versions[-1].version_number == 21
        assert doc.current_version == 21

        # Verify all versions have correct content
        for v in versions:
            content = version_manager.get_version_content(v)
            if v.version_number == 1:
                assert content == sample_text
            else:
                assert content == f"Content version {v.version_number}".encode()
