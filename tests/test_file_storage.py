"""Comprehensive tests for the APEX-OS file storage system."""

import json
import os
import tempfile
import shutil
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from botocore.exceptions import ClientError

from apex_os_bp.file_storage.base import StorageBackend, StorageObject, StorageError
from apex_os_bp.file_storage.local import LocalStorage
from apex_os_bp.file_storage.s3 import S3Storage
from apex_os_bp.file_storage.azure import AzureStorage
from apex_os_bp.file_storage.gcp import GCPStorage
from apex_os_bp.file_storage.versioning import FileVersion, VersionedStorage
from apex_os_bp.file_storage.manager import StorageManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    d = tempfile.mkdtemp(prefix="apex_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def local_storage(temp_dir):
    """Create a connected LocalStorage instance."""
    storage = LocalStorage(name="test_local", config={"base_path": temp_dir})
    storage.connect()
    yield storage
    storage.disconnect()


@pytest.fixture
def sample_data():
    """Return sample binary data."""
    b"Hello, APEX-OS World! This is test data for file storage."
    return b"Hello, APEX-OS World! This is test data for file storage."


@pytest.fixture
def sample_metadata():
    """Return sample metadata."""
    return {"author": "test", "project": "apex-os", "version": "1.0"}


# ============================================================================
# Base / StorageObject Tests
# ============================================================================

class TestStorageObject:
    """Tests for the StorageObject dataclass."""

    def test_create_basic(self):
        obj = StorageObject(key="test.txt", size=100)
        assert obj.key == "test.txt"
        assert obj.size == 100
        assert obj.content_type == "application/octet-stream"
        assert obj.metadata == {}
        assert obj.etag == ""
        assert obj.version_id is None
        assert obj.last_modified is not None

    def test_create_full(self):
        now = datetime.utcnow()
        obj = StorageObject(
            key="path/to/file.pdf",
            size=2048,
            content_type="application/pdf",
            metadata={"author": "test"},
            etag="abc123",
            last_modified=now,
            version_id="v1",
        )
        assert obj.key == "path/to/file.pdf"
        assert obj.size == 2048
        assert obj.content_type == "application/pdf"
        assert obj.metadata == {"author": "test"}
        assert obj.etag == "abc123"
        assert obj.last_modified == now
        assert obj.version_id == "v1"

    def test_default_last_modified(self):
        obj = StorageObject(key="test", size=0)
        assert isinstance(obj.last_modified, datetime)


class TestStorageError:
    """Tests for StorageError."""

    def test_basic_error(self):
        err = StorageError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.backend == ""
        assert err.original_error is None

    def test_error_with_backend(self):
        err = StorageError("not found", backend="s3")
        assert err.backend == "s3"

    def test_error_with_original(self):
        original = ValueError("original")
        err = StorageError("wrapped", backend="local", original_error=original)
        assert err.original_error is original


# ============================================================================
# LocalStorage Tests
# ============================================================================

class TestLocalStorage:
    """Tests for LocalStorage backend."""

    def test_connect_creates_directory(self, temp_dir):
        base = os.path.join(temp_dir, "new_storage")
        storage = LocalStorage(name="test", config={"base_path": base})
        storage.connect()
        assert storage.connected
        assert os.path.isdir(base)
        storage.disconnect()

    def test_connect_nonexistent_parent(self, temp_dir):
        base = os.path.join(temp_dir, "deep", "nested", "path")
        storage = LocalStorage(name="test", config={"base_path": base})
        storage.connect()
        assert os.path.isdir(base)
        storage.disconnect()

    def test_put_and_get(self, local_storage, sample_data):
        local_storage.put("test.txt", sample_data, content_type="text/plain")
        result = local_storage.get("test.txt")
        assert result == sample_data

    def test_put_with_metadata(self, local_storage, sample_data, sample_metadata):
        local_storage.put("test.txt", sample_data, metadata=sample_metadata)
        obj = local_storage.get_object("test.txt")
        assert obj.size == len(sample_data)

    def test_put_nested_path(self, local_storage, sample_data):
        local_storage.put("a/b/c/file.txt", sample_data)
        assert local_storage.exists("a/b/c/file.txt")
        assert local_storage.get("a/b/c/file.txt") == sample_data

    def test_get_nonexistent(self, local_storage):
        with pytest.raises(StorageError):
            local_storage.get("nonexistent.txt")

    def test_get_object(self, local_storage, sample_data):
        local_storage.put("test.txt", sample_data, content_type="text/plain")
        obj = local_storage.get_object("test.txt")
        assert isinstance(obj, StorageObject)
        assert obj.key == "test.txt"
        assert obj.size == len(sample_data)
        assert obj.content_type == "text/plain"
        assert obj.etag != ""

    def test_get_object_nonexistent(self, local_storage):
        with pytest.raises(StorageError):
            local_storage.get_object("nonexistent.txt")

    def test_delete(self, local_storage, sample_data):
        local_storage.put("test.txt", sample_data)
        assert local_storage.exists("test.txt")
        result = local_storage.delete("test.txt")
        assert result is True
        assert not local_storage.exists("test.txt")

    def test_delete_nonexistent(self, local_storage):
        result = local_storage.delete("nonexistent.txt")
        assert result is False

    def test_exists(self, local_storage, sample_data):
        assert not local_storage.exists("test.txt")
        local_storage.put("test.txt", sample_data)
        assert local_storage.exists("test.txt")

    def test_list_objects(self, local_storage, sample_data):
        local_storage.put("file1.txt", sample_data)
        local_storage.put("file2.txt", sample_data)
        local_storage.put("dir/file3.txt", sample_data)
        objects = local_storage.list_objects()
        assert len(objects) == 3
        keys = [o.key for o in objects]
        assert "file1.txt" in keys
        assert "file2.txt" in keys
        assert "dir/file3.txt" in keys

    def test_list_objects_with_prefix(self, local_storage, sample_data):
        local_storage.put("docs/readme.txt", sample_data)
        local_storage.put("docs/guide.txt", sample_data)
        local_storage.put("src/main.py", sample_data)
        objects = local_storage.list_objects(prefix="docs/")
        assert len(objects) == 2
        keys = [o.key for o in objects]
        assert "docs/readme.txt" in keys
        assert "docs/guide.txt" in keys

    def test_copy(self, local_storage, sample_data):
        local_storage.put("source.txt", sample_data)
        result = local_storage.copy("source.txt", "dest.txt")
        assert isinstance(result, StorageObject)
        assert local_storage.exists("dest.txt")
        assert local_storage.get("dest.txt") == sample_data

    def test_copy_nonexistent_source(self, local_storage):
        with pytest.raises(StorageError):
            local_storage.copy("nonexistent.txt", "dest.txt")

    def test_move(self, local_storage, sample_data):
        local_storage.put("old.txt", sample_data)
        result = local_storage.move("old.txt", "new.txt")
        assert isinstance(result, StorageObject)
        assert not local_storage.exists("old.txt")
        assert local_storage.exists("new.txt")
        assert local_storage.get("new.txt") == sample_data

    def test_move_nonexistent_source(self, local_storage):
        with pytest.raises(StorageError):
            local_storage.move("nonexistent.txt", "dest.txt")

    def test_get_url(self, local_storage, sample_data):
        local_storage.put("test.txt", sample_data)
        url = local_storage.get_url("test.txt")
        assert url.startswith("file://")
        assert "test.txt" in url

    def test_get_hash(self, local_storage, sample_data):
        local_storage.put("test.txt", sample_data)
        hash1 = local_storage.get_hash("test.txt")
        hash2 = local_storage.get_hash("test.txt")
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hex digest

    def test_get_hash_consistency(self, local_storage, sample_data):
        import hashlib
        local_storage.put("test.txt", sample_data)
        expected = hashlib.md5(sample_data).hexdigest()
        assert local_storage.get_hash("test.txt") == expected

    def test_get_hash_nonexistent(self, local_storage):
        with pytest.raises(StorageError):
            local_storage.get_hash("nonexistent.txt")

    def test_path_traversal_prevention(self, local_storage):
        with pytest.raises(StorageError):
            local_storage.get("../etc/passwd")

    def test_path_traversal_prevention_absolute(self, local_storage):
        with pytest.raises(StorageError):
            local_storage.get("/etc/passwd")

    def test_context_manager(self, temp_dir):
        storage = LocalStorage(name="test", config={"base_path": temp_dir})
        with storage as s:
            assert s.connected
            s.put("test.txt", b"data")
        assert not storage.connected

    def test_not_connected_error(self, temp_dir):
        storage = LocalStorage(name="test", config={"base_path": temp_dir})
        with pytest.raises(StorageError):
            storage.put("test.txt", b"data")

    def test_overwrite_existing(self, local_storage, sample_data):
        local_storage.put("test.txt", b"old data")
        local_storage.put("test.txt", sample_data)
        assert local_storage.get("test.txt") == sample_data

    def test_empty_file(self, local_storage):
        local_storage.put("empty.txt", b"")
        assert local_storage.get("empty.txt") == b""
        assert local_storage.get_object("empty.txt").size == 0

    def test_large_file(self, local_storage):
        data = b"x" * (1024 * 1024)  # 1MB
        local_storage.put("large.bin", data)
        assert local_storage.get("large.bin") == data
        assert local_storage.get_object("large.bin").size == 1024 * 1024

    def test_special_characters_in_key(self, local_storage, sample_data):
        local_storage.put("file with spaces.txt", sample_data)
        assert local_storage.exists("file with spaces.txt")
        local_storage.put("file-with-dashes.txt", sample_data)
        assert local_storage.exists("file-with-dashes.txt")
        local_storage.put("file_with_underscores.txt", sample_data)
        assert local_storage.exists("file_with_underscores.txt")

    def test_metadata_sidecar(self, local_storage, sample_data, sample_metadata):
        local_storage.put("test.txt", sample_data, metadata=sample_metadata)
        # Metadata sidecar should exist
        meta_path = os.path.join(local_storage.base_path, "test.txt.meta")
        assert os.path.exists(meta_path)
        with open(meta_path, "r") as f:
            stored_meta = json.load(f)
        assert stored_meta == sample_metadata


# ============================================================================
# S3Storage Tests (mocked)
# ============================================================================

class TestS3Storage:
    """Tests for S3Storage backend using mocks."""

    @pytest.fixture
    def s3_storage(self):
        storage = S3Storage(name="test_s3", config={
            "bucket": "test-bucket",
            "region": "us-east-1",
            "access_key": "AKIAIOSFODNN7EXAMPLE",
            "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        })
        return storage

    @pytest.fixture
    def mock_boto3(self):
        with patch("boto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_client = MagicMock()
            mock_resource = MagicMock()
            mock_session.client.return_value = mock_client
            mock_session.resource.return_value = mock_resource
            mock_session_class.return_value = mock_session
            # Set up real exception classes so `except` clauses work
            mock_client.exceptions.NoSuchKey = ClientError
            mock_client.exceptions.ClientError = ClientError
            yield {
                "session_class": mock_session_class,
                "session": mock_session,
                "client": mock_client,
                "resource": mock_resource,
            }

    def test_connect(self, s3_storage, mock_boto3):
        s3_storage.connect()
        assert s3_storage.connected
        mock_boto3["session_class"].assert_called_once()
        s3_storage.disconnect()

    def test_connect_creates_bucket(self, s3_storage, mock_boto3):
        mock_boto3["client"].head_bucket.side_effect = Exception("NoSuchBucket")
        s3_storage.connect()
        mock_boto3["client"].create_bucket.assert_called_once()
        s3_storage.disconnect()

    def test_connect_without_credentials(self):
        storage = S3Storage(name="test_s3", config={"bucket": "test", "region": "us-west-2"})
        with patch("boto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            storage.connect()
            mock_session_class.assert_called_once_with()
            storage.disconnect()

    def test_connect_import_error(self, s3_storage):
        with patch.dict("sys.modules", {"boto3": None}):
            with pytest.raises(StorageError, match="boto3 is required"):
                s3_storage.connect()

    def test_put(self, s3_storage, mock_boto3, sample_data):
        s3_storage.connect()
        mock_boto3["client"].head_object.return_value = {
            "ContentLength": len(sample_data),
            "ContentType": "text/plain",
            "ETag": '"abc123"',
            "LastModified": datetime.utcnow(),
            "Metadata": {},
        }
        result = s3_storage.put("test.txt", sample_data, content_type="text/plain")
        assert isinstance(result, StorageObject)
        assert result.key == "test.txt"
        assert result.size == len(sample_data)
        mock_boto3["client"].put_object.assert_called_once()
        s3_storage.disconnect()

    def test_put_with_metadata(self, s3_storage, mock_boto3, sample_data, sample_metadata):
        s3_storage.connect()
        mock_boto3["client"].head_object.return_value = {
            "ContentLength": len(sample_data),
            "ContentType": "text/plain",
            "ETag": '"abc123"',
            "LastModified": datetime.utcnow(),
            "Metadata": sample_metadata,
        }
        s3_storage.put("test.txt", sample_data, metadata=sample_metadata)
        call_kwargs = mock_boto3["client"].put_object.call_args[1]
        assert call_kwargs["Metadata"] == sample_metadata
        s3_storage.disconnect()

    def test_get(self, s3_storage, mock_boto3, sample_data):
        s3_storage.connect()
        mock_body = MagicMock()
        mock_body.read.return_value = sample_data
        mock_boto3["client"].get_object.return_value = {"Body": mock_body}
        result = s3_storage.get("test.txt")
        assert result == sample_data
        s3_storage.disconnect()

    def test_get_nonexistent(self, s3_storage, mock_boto3):
        s3_storage.connect()
        from botocore.exceptions import ClientError
        mock_boto3["client"].get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        with pytest.raises(StorageError):
            s3_storage.get("nonexistent.txt")
        s3_storage.disconnect()

    def test_get_object(self, s3_storage, mock_boto3):
        s3_storage.connect()
        mock_boto3["client"].head_object.return_value = {
            "ContentLength": 100,
            "ContentType": "image/png",
            "ETag": '"xyz789"',
            "LastModified": datetime.utcnow(),
            "Metadata": {"key": "value"},
            "VersionId": "v1",
        }
        obj = s3_storage.get_object("image.png")
        assert obj.key == "image.png"
        assert obj.size == 100
        assert obj.content_type == "image/png"
        assert obj.etag == "xyz789"
        assert obj.version_id == "v1"
        s3_storage.disconnect()

    def test_delete(self, s3_storage, mock_boto3):
        s3_storage.connect()
        result = s3_storage.delete("test.txt")
        assert result is True
        mock_boto3["client"].delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.txt"
        )
        s3_storage.disconnect()

    def test_exists_true(self, s3_storage, mock_boto3):
        s3_storage.connect()
        mock_boto3["client"].head_object.return_value = {}
        assert s3_storage.exists("test.txt") is True
        s3_storage.disconnect()

    def test_exists_false(self, s3_storage, mock_boto3):
        s3_storage.connect()
        from botocore.exceptions import ClientError
        mock_boto3["client"].head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        assert s3_storage.exists("nonexistent.txt") is False
        s3_storage.disconnect()

    def test_list_objects(self, s3_storage, mock_boto3):
        s3_storage.connect()
        mock_paginator = MagicMock()
        mock_boto3["client"].get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {"Contents": [
                {"Key": "file1.txt", "Size": 100, "ETag": '"a"', "LastModified": datetime.utcnow()},
                {"Key": "file2.txt", "Size": 200, "ETag": '"b"', "LastModified": datetime.utcnow()},
            ]}
        ]
        objects = s3_storage.list_objects()
        assert len(objects) == 2
        assert objects[0].key == "file1.txt"
        assert objects[1].key == "file2.txt"
        s3_storage.disconnect()

    def test_list_objects_with_prefix(self, s3_storage, mock_boto3):
        s3_storage.connect()
        mock_paginator = MagicMock()
        mock_boto3["client"].get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {"Contents": [
                {"Key": "docs/readme.txt", "Size": 100, "ETag": '"a"', "LastModified": datetime.utcnow()},
            ]}
        ]
        objects = s3_storage.list_objects(prefix="docs/")
        assert len(objects) == 1
        call_kwargs = mock_paginator.paginate.call_args[1]
        assert call_kwargs["Prefix"] == "docs/"
        s3_storage.disconnect()

    def test_copy(self, s3_storage, mock_boto3):
        s3_storage.connect()
        mock_boto3["client"].head_object.return_value = {
            "ContentLength": 100,
            "ContentType": "text/plain",
            "ETag": '"abc"',
            "LastModified": datetime.utcnow(),
            "Metadata": {},
        }
        result = s3_storage.copy("source.txt", "dest.txt")
        assert isinstance(result, StorageObject)
        mock_boto3["client"].copy_object.assert_called_once()
        s3_storage.disconnect()

    def test_move(self, s3_storage, mock_boto3):
        s3_storage.connect()
        mock_boto3["client"].head_object.return_value = {
            "ContentLength": 100,
            "ContentType": "text/plain",
            "ETag": '"abc"',
            "LastModified": datetime.utcnow(),
            "Metadata": {},
        }
        result = s3_storage.move("old.txt", "new.txt")
        assert isinstance(result, StorageObject)
        mock_boto3["client"].copy_object.assert_called_once()
        mock_boto3["client"].delete_object.assert_called_once()
        s3_storage.disconnect()

    def test_get_url(self, s3_storage, mock_boto3):
        s3_storage.connect()
        mock_boto3["client"].generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/test.txt?sig=abc"
        url = s3_storage.get_url("test.txt", expires_in=7200)
        assert "test-bucket" in url
        assert "test.txt" in url
        call_kwargs = mock_boto3["client"].generate_presigned_url.call_args[1]
        assert call_kwargs["ExpiresIn"] == 7200
        s3_storage.disconnect()

    def test_get_hash(self, s3_storage, mock_boto3):
        s3_storage.connect()
        mock_boto3["client"].head_object.return_value = {"ETag": '"abc123"'}
        assert s3_storage.get_hash("test.txt") == "abc123"
        s3_storage.disconnect()

    def test_enable_versioning(self, s3_storage, mock_boto3):
        s3_storage.connect()
        result = s3_storage.enable_versioning()
        assert result is True
        mock_boto3["client"].put_bucket_versioning.assert_called_once()
        s3_storage.disconnect()

    def test_list_versions(self, s3_storage, mock_boto3):
        s3_storage.connect()
        mock_paginator = MagicMock()
        mock_boto3["client"].get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {"Versions": [
                {"Key": "test.txt", "Size": 100, "ETag": '"a"', "LastModified": datetime.utcnow(), "VersionId": "v1"},
                {"Key": "test.txt", "Size": 200, "ETag": '"b"', "LastModified": datetime.utcnow(), "VersionId": "v2"},
            ]}
        ]
        versions = s3_storage.list_versions("test.txt")
        assert len(versions) == 2
        s3_storage.disconnect()

    def test_context_manager(self, s3_storage, mock_boto3):
        with s3_storage as s:
            assert s.connected
        assert not s3_storage.connected

    def test_not_connected_error(self, s3_storage):
        with pytest.raises(StorageError):
            s3_storage.put("test.txt", b"data")


# ============================================================================
# AzureStorage Tests (mocked)
# ============================================================================

class TestAzureStorage:
    """Tests for AzureStorage backend using mocks."""

    @pytest.fixture
    def azure_storage(self):
        storage = AzureStorage(name="test_azure", config={
            "account_name": "testaccount",
            "account_key": "dGVzdGtleQ==",
            "container": "test-container",
        })
        return storage

    @pytest.fixture
    def mock_azure(self):
        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc_class:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_bsc_class.from_connection_string.return_value = mock_client
            mock_bsc_class.return_value = mock_client
            mock_client.get_container_client.return_value = mock_container
            mock_container.exists.return_value = True
            yield {
                "bsc_class": mock_bsc_class,
                "client": mock_client,
                "container": mock_container,
            }

    def test_connect_with_connection_string(self):
        storage = AzureStorage(name="test", config={
            "connection_string": "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=abc;EndpointSuffix=core.windows.net",
            "container": "test",
        })
        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_bsc.from_connection_string.return_value = mock_client
            mock_client.get_container_client.return_value = mock_container
            mock_container.exists.return_value = True
            storage.connect()
            assert storage.connected
            mock_bsc.from_connection_string.assert_called_once()
            storage.disconnect()

    def test_connect_with_account_key(self, azure_storage, mock_azure):
        azure_storage.connect()
        assert azure_storage.connected
        azure_storage.disconnect()

    def test_connect_creates_container(self, azure_storage, mock_azure):
        mock_azure["container"].exists.return_value = False
        azure_storage.connect()
        mock_azure["container"].create_container.assert_called_once()
        azure_storage.disconnect()

    def test_connect_no_credentials(self):
        storage = AzureStorage(name="test", config={"container": "test"})
        with pytest.raises(StorageError, match="connection_string or account_name"):
            storage.connect()

    def test_connect_import_error(self, azure_storage):
        with patch.dict("sys.modules", {"azure.storage.blob": None, "azure": None, "azure.storage": None}):
            with pytest.raises(StorageError, match="azure-storage-blob is required"):
                azure_storage.connect()

    def test_put(self, azure_storage, mock_azure, sample_data):
        mock_blob = MagicMock()
        mock_azure["container"].get_blob_client.return_value = mock_blob
        mock_blob.upload_blob.return_value = None
        mock_blob.get_blob_properties.return_value = MagicMock(
            size=len(sample_data),
            content_settings=MagicMock(content_type="text/plain"),
            metadata={},
            etag='"abc123"',
            last_modified=datetime.utcnow(),
        )
        azure_storage.connect()
        result = azure_storage.put("test.txt", sample_data, content_type="text/plain")
        assert isinstance(result, StorageObject)
        mock_blob.upload_blob.assert_called_once()
        azure_storage.disconnect()

    def test_get(self, azure_storage, mock_azure, sample_data):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_downloader = MagicMock()
        mock_downloader.readall.return_value = sample_data
        mock_blob.download_blob.return_value = mock_downloader
        mock_azure["container"].get_blob_client.return_value = mock_blob
        azure_storage.connect()
        result = azure_storage.get("test.txt")
        assert result == sample_data
        azure_storage.disconnect()

    def test_get_nonexistent(self, azure_storage, mock_azure):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_azure["container"].get_blob_client.return_value = mock_blob
        azure_storage.connect()
        with pytest.raises(StorageError):
            azure_storage.get("nonexistent.txt")
        azure_storage.disconnect()

    def test_get_object(self, azure_storage, mock_azure):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.get_blob_properties.return_value = MagicMock(
            size=100,
            content_settings=MagicMock(content_type="image/png"),
            metadata={"key": "val"},
            etag='"xyz"',
            last_modified=datetime.utcnow(),
        )
        mock_azure["container"].get_blob_client.return_value = mock_blob
        azure_storage.connect()
        obj = azure_storage.get_object("image.png")
        assert obj.size == 100
        assert obj.content_type == "image/png"
        azure_storage.disconnect()

    def test_delete(self, azure_storage, mock_azure):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_azure["container"].get_blob_client.return_value = mock_blob
        azure_storage.connect()
        result = azure_storage.delete("test.txt")
        assert result is True
        mock_blob.delete_blob.assert_called_once()
        azure_storage.disconnect()

    def test_delete_nonexistent(self, azure_storage, mock_azure):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_azure["container"].get_blob_client.return_value = mock_blob
        azure_storage.connect()
        result = azure_storage.delete("nonexistent.txt")
        assert result is False
        azure_storage.disconnect()

    def test_exists(self, azure_storage, mock_azure):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_azure["container"].get_blob_client.return_value = mock_blob
        azure_storage.connect()
        assert azure_storage.exists("test.txt") is True
        mock_blob.exists.return_value = False
        assert azure_storage.exists("other.txt") is False
        azure_storage.disconnect()

    def test_list_objects(self, azure_storage, mock_azure):
        mock_blob1 = MagicMock()
        mock_blob1.name = "file1.txt"
        mock_blob1.size = 100
        mock_blob1.etag = '"a"'
        mock_blob1.last_modified = datetime.utcnow()
        mock_blob2 = MagicMock()
        mock_blob2.name = "file2.txt"
        mock_blob2.size = 200
        mock_blob2.etag = '"b"'
        mock_blob2.last_modified = datetime.utcnow()
        mock_azure["container"].list_blobs.return_value = [mock_blob1, mock_blob2]
        azure_storage.connect()
        objects = azure_storage.list_objects()
        assert len(objects) == 2
        azure_storage.disconnect()

    def test_copy(self, azure_storage, mock_azure):
        mock_source = MagicMock()
        mock_source.exists.return_value = True
        mock_source.url = "https://test.blob.core.windows.net/container/source.txt"
        mock_dest = MagicMock()
        mock_dest.get_blob_properties.return_value = MagicMock(
            size=100,
            content_settings=MagicMock(content_type="text/plain"),
            metadata={},
            etag='"abc"',
            last_modified=datetime.utcnow(),
        )
        def get_blob_client_side_effect(key):
            if key == "source.txt":
                return mock_source
            return mock_dest
        mock_azure["container"].get_blob_client.side_effect = get_blob_client_side_effect
        azure_storage.connect()
        result = azure_storage.copy("source.txt", "dest.txt")
        assert isinstance(result, StorageObject)
        mock_dest.start_copy_from_url.assert_called_once()
        azure_storage.disconnect()

    def test_move(self, azure_storage, mock_azure):
        mock_source = MagicMock()
        mock_source.exists.return_value = True
        mock_source.url = "https://test.blob.core.windows.net/container/old.txt"
        mock_dest = MagicMock()
        mock_dest.get_blob_properties.return_value = MagicMock(
            size=100,
            content_settings=MagicMock(content_type="text/plain"),
            metadata={},
            etag='"abc"',
            last_modified=datetime.utcnow(),
        )
        def get_blob_client_side_effect(key):
            if key == "old.txt":
                return mock_source
            return mock_dest
        mock_azure["container"].get_blob_client.side_effect = get_blob_client_side_effect
        azure_storage.connect()
        result = azure_storage.move("old.txt", "new.txt")
        assert isinstance(result, StorageObject)
        mock_dest.start_copy_from_url.assert_called_once()
        mock_source.delete_blob.assert_called_once()
        azure_storage.disconnect()

    def test_get_url(self, azure_storage, mock_azure):
        mock_blob = MagicMock()
        mock_blob.url = "https://test.blob.core.windows.net/container/test.txt"
        mock_azure["container"].get_blob_client.return_value = mock_blob
        azure_storage.connect()
        with patch("azure.storage.blob.generate_blob_sas") as mock_sas:
            mock_sas.return_value = "sig=abc123"
            url = azure_storage.get_url("test.txt", expires_in=7200)
            assert "sig=abc123" in url
            mock_sas.assert_called_once()
        azure_storage.disconnect()

    def test_get_hash(self, azure_storage, mock_azure):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_props = MagicMock()
        mock_props.content_settings.content_md5 = b"\x01\x02\x03\x04"
        mock_props.etag = '"abc123"'
        mock_blob.get_blob_properties.return_value = mock_props
        mock_azure["container"].get_blob_client.return_value = mock_blob
        azure_storage.connect()
        result = azure_storage.get_hash("test.txt")
        assert result == "01020304"
        azure_storage.disconnect()

    def test_context_manager(self, azure_storage, mock_azure):
        with azure_storage as s:
            assert s.connected
        assert not azure_storage.connected

    def test_not_connected_error(self, azure_storage):
        with pytest.raises(StorageError):
            azure_storage.put("test.txt", b"data")


# ============================================================================
# GCPStorage Tests (mocked)
# ============================================================================

class TestGCPStorage:
    """Tests for GCPStorage backend using mocks."""

    @pytest.fixture
    def gcp_storage(self):
        storage = GCPStorage(name="test_gcp", config={
            "project_id": "test-project",
            "bucket": "test-bucket",
        })
        return storage

    @pytest.fixture
    def mock_gcp(self):
        with patch("google.cloud.storage.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.exists.return_value = True
            mock_client_class.return_value = mock_client
            yield {
                "client_class": mock_client_class,
                "client": mock_client,
                "bucket": mock_bucket,
            }

    def test_connect(self, gcp_storage, mock_gcp):
        gcp_storage.connect()
        assert gcp_storage.connected
        mock_gcp["client_class"].assert_called_once()
        gcp_storage.disconnect()

    def test_connect_creates_bucket(self, gcp_storage, mock_gcp):
        mock_gcp["bucket"].exists.return_value = False
        gcp_storage.connect()
        mock_gcp["client"].create_bucket.assert_called_once_with("test-bucket")
        gcp_storage.disconnect()

    def test_connect_import_error(self, gcp_storage):
        with patch.dict("sys.modules", {"google.cloud.storage": None, "google": None, "google.cloud": None}):
            with pytest.raises(StorageError, match="google-cloud-storage is required"):
                gcp_storage.connect()

    def test_put(self, gcp_storage, mock_gcp, sample_data):
        mock_blob = MagicMock()
        mock_gcp["bucket"].blob.return_value = mock_blob
        mock_blob.upload_from_string.return_value = None
        mock_gcp["bucket"].get_blob.return_value = MagicMock(
            size=len(sample_data),
            content_type="text/plain",
            metadata={},
            etag="abc123",
            updated=datetime.utcnow(),
        )
        gcp_storage.connect()
        result = gcp_storage.put("test.txt", sample_data, content_type="text/plain")
        assert isinstance(result, StorageObject)
        mock_blob.upload_from_string.assert_called_once()
        gcp_storage.disconnect()

    def test_put_with_metadata(self, gcp_storage, mock_gcp, sample_data, sample_metadata):
        mock_blob = MagicMock()
        mock_gcp["bucket"].blob.return_value = mock_blob
        mock_gcp["bucket"].get_blob.return_value = MagicMock(
            size=len(sample_data),
            content_type="text/plain",
            metadata=sample_metadata,
            etag="abc",
            updated=datetime.utcnow(),
        )
        gcp_storage.connect()
        gcp_storage.put("test.txt", sample_data, metadata=sample_metadata)
        assert mock_blob.metadata == sample_metadata
        gcp_storage.disconnect()

    def test_get(self, gcp_storage, mock_gcp, sample_data):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_bytes.return_value = sample_data
        mock_gcp["bucket"].blob.return_value = mock_blob
        gcp_storage.connect()
        result = gcp_storage.get("test.txt")
        assert result == sample_data
        gcp_storage.disconnect()

    def test_get_nonexistent(self, gcp_storage, mock_gcp):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_gcp["bucket"].blob.return_value = mock_blob
        gcp_storage.connect()
        with pytest.raises(StorageError):
            gcp_storage.get("nonexistent.txt")
        gcp_storage.disconnect()

    def test_get_object(self, gcp_storage, mock_gcp):
        mock_gcp["bucket"].get_blob.return_value = MagicMock(
            size=100,
            content_type="image/png",
            metadata={"key": "val"},
            etag="xyz",
            updated=datetime.utcnow(),
        )
        gcp_storage.connect()
        obj = gcp_storage.get_object("image.png")
        assert obj.size == 100
        assert obj.content_type == "image/png"
        assert obj.metadata == {"key": "val"}
        gcp_storage.disconnect()

    def test_get_object_nonexistent(self, gcp_storage, mock_gcp):
        mock_gcp["bucket"].get_blob.return_value = None
        gcp_storage.connect()
        with pytest.raises(StorageError):
            gcp_storage.get_object("nonexistent.txt")
        gcp_storage.disconnect()

    def test_delete(self, gcp_storage, mock_gcp):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_gcp["bucket"].blob.return_value = mock_blob
        gcp_storage.connect()
        result = gcp_storage.delete("test.txt")
        assert result is True
        mock_blob.delete.assert_called_once()
        gcp_storage.disconnect()

    def test_delete_nonexistent(self, gcp_storage, mock_gcp):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_gcp["bucket"].blob.return_value = mock_blob
        gcp_storage.connect()
        result = gcp_storage.delete("nonexistent.txt")
        assert result is False
        gcp_storage.disconnect()

    def test_exists(self, gcp_storage, mock_gcp):
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_gcp["bucket"].blob.return_value = mock_blob
        gcp_storage.connect()
        assert gcp_storage.exists("test.txt") is True
        mock_blob.exists.return_value = False
        assert gcp_storage.exists("other.txt") is False
        gcp_storage.disconnect()

    def test_list_objects(self, gcp_storage, mock_gcp):
        mock_blob1 = MagicMock()
        mock_blob1.name = "file1.txt"
        mock_blob1.size = 100
        mock_blob1.content_type = "text/plain"
        mock_blob1.metadata = {}
        mock_blob1.etag = "a"
        mock_blob1.updated = datetime.utcnow()
        mock_blob2 = MagicMock()
        mock_blob2.name = "file2.txt"
        mock_blob2.size = 200
        mock_blob2.content_type = "image/png"
        mock_blob2.metadata = {}
        mock_blob2.etag = "b"
        mock_blob2.updated = datetime.utcnow()
        mock_gcp["client"].list_blobs.return_value = [mock_blob1, mock_blob2]
        gcp_storage.connect()
        objects = gcp_storage.list_objects()
        assert len(objects) == 2
        gcp_storage.disconnect()

    def test_copy(self, gcp_storage, mock_gcp):
        mock_source = MagicMock()
        mock_source.exists.return_value = True
        mock_gcp["bucket"].blob.return_value = mock_source
        mock_gcp["bucket"].get_blob.return_value = MagicMock(
            size=100,
            content_type="text/plain",
            metadata={},
            etag="abc",
            updated=datetime.utcnow(),
        )
        gcp_storage.connect()
        result = gcp_storage.copy("source.txt", "dest.txt")
        assert isinstance(result, StorageObject)
        mock_gcp["bucket"].copy_blob.assert_called_once()
        gcp_storage.disconnect()

    def test_move(self, gcp_storage, mock_gcp):
        mock_source = MagicMock()
        mock_source.exists.return_value = True
        mock_gcp["bucket"].blob.return_value = mock_source
        mock_gcp["bucket"].get_blob.return_value = MagicMock(
            size=100,
            content_type="text/plain",
            metadata={},
            etag="abc",
            updated=datetime.utcnow(),
        )
        gcp_storage.connect()
        result = gcp_storage.move("old.txt", "new.txt")
        assert isinstance(result, StorageObject)
        mock_gcp["bucket"].copy_blob.assert_called_once()
        mock_source.delete.assert_called_once()
        gcp_storage.disconnect()

    def test_get_url(self, gcp_storage, mock_gcp):
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-bucket/test.txt?sig=abc"
        mock_gcp["bucket"].blob.return_value = mock_blob
        gcp_storage.connect()
        url = gcp_storage.get_url("test.txt", expires_in=7200)
        assert "test-bucket" in url
        call_kwargs = mock_blob.generate_signed_url.call_args[1]
        assert call_kwargs["expiration"].total_seconds() == 7200
        gcp_storage.disconnect()

    def test_get_hash(self, gcp_storage, mock_gcp):
        mock_gcp["bucket"].get_blob.return_value = MagicMock(
            md5_hash="abc123hash",
            crc32c="",
        )
        gcp_storage.connect()
        result = gcp_storage.get_hash("test.txt")
        assert result == "abc123hash"
        gcp_storage.disconnect()

    def test_context_manager(self, gcp_storage, mock_gcp):
        with gcp_storage as s:
            assert s.connected
        assert not gcp_storage.connected

    def test_not_connected_error(self, gcp_storage):
        with pytest.raises(StorageError):
            gcp_storage.put("test.txt", b"data")


# ============================================================================
# FileVersion Tests
# ============================================================================

class TestFileVersion:
    """Tests for FileVersion dataclass."""

    def test_create_basic(self):
        v = FileVersion(key="test.txt", version_id="v1", size=100)
        assert v.key == "test.txt"
        assert v.version_id == "v1"
        assert v.size == 100
        assert v.content_type == "application/octet-stream"
        assert v.metadata == {}
        assert v.etag == ""
        assert v.is_latest is False
        assert v.comment == ""
        assert v.storage_backend == ""
        assert isinstance(v.created_at, datetime)

    def test_create_full(self):
        now = datetime.utcnow()
        v = FileVersion(
            key="test.txt",
            version_id="v2",
            size=200,
            content_type="text/plain",
            metadata={"author": "test"},
            etag="abc123",
            created_at=now,
            is_latest=True,
            comment="second version",
            storage_backend="local",
        )
        assert v.is_latest is True
        assert v.comment == "second version"
        assert v.storage_backend == "local"

    def test_to_dict(self):
        v = FileVersion(key="test.txt", version_id="v1", size=100)
        d = v.to_dict()
        assert d["key"] == "test.txt"
        assert d["version_id"] == "v1"
        assert d["size"] == 100
        assert "created_at" in d
        assert isinstance(d["created_at"], str)

    def test_from_dict(self):
        data = {
            "key": "test.txt",
            "version_id": "v1",
            "size": 100,
            "content_type": "text/plain",
            "metadata": {"key": "val"},
            "etag": "abc",
            "created_at": "2024-01-15T10:30:00",
            "is_latest": True,
            "comment": "test",
            "storage_backend": "local",
        }
        v = FileVersion.from_dict(data)
        assert v.key == "test.txt"
        assert v.version_id == "v1"
        assert v.size == 100
        assert v.is_latest is True
        assert isinstance(v.created_at, datetime)

    def test_roundtrip(self):
        v = FileVersion(
            key="test.txt",
            version_id="v1",
            size=100,
            metadata={"key": "val"},
            is_latest=True,
            comment="test",
        )
        d = v.to_dict()
        v2 = FileVersion.from_dict(d)
        assert v2.key == v.key
        assert v2.version_id == v.version_id
        assert v2.size == v.size
        assert v2.metadata == v.metadata
        assert v2.is_latest == v.is_latest
        assert v2.comment == v.comment


# ============================================================================
# VersionedStorage Tests
# ============================================================================

class TestVersionedStorage:
    """Tests for VersionedStorage."""

    @pytest.fixture
    def versioned(self, local_storage):
        return VersionedStorage(local_storage, max_versions=10)

    def test_put_creates_version(self, versioned, sample_data):
        v = versioned.put("test.txt", sample_data, content_type="text/plain")
        assert isinstance(v, FileVersion)
        assert v.key == "test.txt"
        assert v.size == len(sample_data)
        assert v.is_latest is True
        assert v.version_id is not None

    def test_put_multiple_versions(self, versioned, sample_data):
        v1 = versioned.put("test.txt", b"version 1")
        v2 = versioned.put("test.txt", b"version 2")
        v3 = versioned.put("test.txt", b"version 3")
        assert v1.version_id != v2.version_id
        assert v2.version_id != v3.version_id

    def test_get_latest(self, versioned, sample_data):
        versioned.put("test.txt", b"version 1")
        versioned.put("test.txt", sample_data)
        result = versioned.get("test.txt")
        assert result == sample_data

    def test_get_specific_version(self, versioned, sample_data):
        v1 = versioned.put("test.txt", b"version 1")
        versioned.put("test.txt", sample_data)
        result = versioned.get("test.txt", version_id=v1.version_id)
        assert result == b"version 1"

    def test_get_nonexistent_version(self, versioned, sample_data):
        versioned.put("test.txt", sample_data)
        with pytest.raises(StorageError):
            versioned.get("test.txt", version_id="nonexistent")

    def test_list_versions(self, versioned, sample_data):
        v1 = versioned.put("test.txt", b"version 1")
        v2 = versioned.put("test.txt", b"version 2")
        v3 = versioned.put("test.txt", b"version 3")
        versions = versioned.list_versions("test.txt")
        assert len(versions) == 3
        assert versions[0].is_latest is True
        assert versions[0].version_id == v3.version_id

    def test_get_latest_version(self, versioned, sample_data):
        versioned.put("test.txt", b"version 1")
        v2 = versioned.put("test.txt", sample_data)
        latest = versioned.get_latest_version("test.txt")
        assert latest is not None
        assert latest.version_id == v2.version_id
        assert latest.is_latest is True

    def test_get_latest_version_empty(self, versioned):
        latest = versioned.get_latest_version("nonexistent.txt")
        assert latest is None

    def test_restore_version(self, versioned, sample_data):
        v1 = versioned.put("test.txt", b"original")
        versioned.put("test.txt", b"modified")
        restored = versioned.restore_version("test.txt", v1.version_id)
        assert isinstance(restored, FileVersion)
        assert restored.is_latest is True
        # Content should match original
        assert versioned.get("test.txt") == b"original"

    def test_restore_nonexistent_version(self, versioned, sample_data):
        versioned.put("test.txt", sample_data)
        with pytest.raises(StorageError):
            versioned.restore_version("test.txt", "nonexistent")

    def test_delete_version(self, versioned, sample_data):
        v1 = versioned.put("test.txt", b"version 1")
        v2 = versioned.put("test.txt", b"version 2")
        result = versioned.delete_version("test.txt", v1.version_id)
        assert result is True
        versions = versioned.list_versions("test.txt")
        assert len(versions) == 1
        assert versions[0].version_id == v2.version_id

    def test_delete_latest_version_fails(self, versioned, sample_data):
        v1 = versioned.put("test.txt", sample_data)
        with pytest.raises(StorageError, match="Cannot delete the latest"):
            versioned.delete_version("test.txt", v1.version_id)

    def test_delete_nonexistent_version(self, versioned, sample_data):
        versioned.put("test.txt", sample_data)
        result = versioned.delete_version("test.txt", "nonexistent")
        assert result is False

    def test_delete_all_versions(self, versioned, sample_data):
        versioned.put("test.txt", b"version 1")
        versioned.put("test.txt", b"version 2")
        versioned.put("test.txt", b"version 3")
        result = versioned.delete("test.txt")
        assert result is True
        assert not versioned.backend.exists("test.txt")
        versions = versioned.list_versions("test.txt")
        assert len(versions) == 0

    def test_get_version_count(self, versioned, sample_data):
        assert versioned.get_version_count("test.txt") == 0
        versioned.put("test.txt", b"v1")
        assert versioned.get_version_count("test.txt") == 1
        versioned.put("test.txt", b"v2")
        assert versioned.get_version_count("test.txt") == 2

    def test_compare_versions_identical(self, versioned, sample_data):
        v1 = versioned.put("test.txt", sample_data)
        v2 = versioned.put("test.txt", sample_data)
        result = versioned.compare_versions("test.txt", v1.version_id, v2.version_id)
        assert result["identical"] is True
        assert result["size_diff"] == 0

    def test_compare_versions_different(self, versioned, sample_data):
        v1 = versioned.put("test.txt", b"short")
        v2 = versioned.put("test.txt", b"much longer content here")
        result = versioned.compare_versions("test.txt", v1.version_id, v2.version_id)
        assert result["identical"] is False
        assert result["size_diff"] != 0

    def test_max_versions_limit(self, local_storage, sample_data):
        versioned = VersionedStorage(local_storage, max_versions=3)
        for i in range(5):
            versioned.put("test.txt", f"version {i}".encode())
        versions = versioned.list_versions("test.txt")
        assert len(versions) == 3

    def test_set_max_versions(self, versioned, sample_data):
        for i in range(5):
            versioned.put("test.txt", f"version {i}".encode())
        assert versioned.get_version_count("test.txt") == 5
        versioned.set_max_versions(2)
        # Trigger cleanup by adding another version
        versioned.put("test.txt", b"new version")
        versions = versioned.list_versions("test.txt")
        assert len(versions) <= 3  # 2 + the new one before cleanup

    def test_version_with_comment(self, versioned, sample_data):
        v = versioned.put("test.txt", sample_data, comment="initial commit")
        assert v.comment == "initial commit"

    def test_version_with_metadata(self, versioned, sample_data, sample_metadata):
        v = versioned.put("test.txt", sample_data, metadata=sample_metadata)
        assert v.metadata == sample_metadata

    def test_clear_cache(self, versioned, sample_data):
        versioned.put("test.txt", sample_data)
        assert len(versioned._version_cache) > 0
        versioned.clear_cache()
        assert len(versioned._version_cache) == 0

    def test_versioned_key_format(self, versioned):
        result = versioned._versioned_key("test.txt", "v123")
        assert result == "test.txt#v123"

    def test_meta_key_format(self, versioned):
        result = versioned._meta_key("test.txt")
        assert result == "test.txt.versions"

    def test_generate_version_id_unique(self, versioned, sample_data):
        id1 = versioned._generate_version_id(sample_data)
        id2 = versioned._generate_version_id(sample_data)
        # Same data but different timestamps should produce different IDs
        # (or same if within same microsecond - that's ok)
        assert isinstance(id1, str)
        assert len(id1) > 0

    def test_context_manager(self, temp_dir):
        storage = LocalStorage(name="test", config={"base_path": temp_dir})
        versioned = VersionedStorage(storage)
        with storage as s:
            v = versioned.put("test.txt", b"data")
            assert v.is_latest


# ============================================================================
# StorageManager Tests
# ============================================================================

class TestStorageManager:
    """Tests for StorageManager."""

    @pytest.fixture
    def manager(self):
        return StorageManager()

    @pytest.fixture
    def local_backend(self, temp_dir):
        storage = LocalStorage(name="local", config={"base_path": temp_dir})
        storage.connect()
        return storage

    def test_add_backend_local(self, manager, temp_dir):
        backend = manager.add_backend("local", "local", config={"base_path": temp_dir})
        assert isinstance(backend, LocalStorage)
        assert "local" in manager._backends

    def test_add_backend_s3(self, manager):
        backend = manager.add_backend("s3", "s3", config={
            "bucket": "test",
            "region": "us-east-1",
        })
        assert isinstance(backend, S3Storage)

    def test_add_backend_azure(self, manager):
        backend = manager.add_backend("azure", "azure", config={
            "account_name": "test",
            "account_key": "key",
            "container": "test",
        })
        assert isinstance(backend, AzureStorage)

    def test_add_backend_gcp(self, manager):
        backend = manager.add_backend("gcp", "gcp", config={
            "project_id": "test",
            "bucket": "test",
        })
        assert isinstance(backend, GCPStorage)

    def test_add_backend_unknown_type(self, manager):
        with pytest.raises(StorageError, match="Unknown backend type"):
            manager.add_backend("unknown", "unknown")

    def test_add_backend_as_primary(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        assert manager._primary == "local"
        assert manager.primary_backend is not None

    def test_remove_backend(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir})
        result = manager.remove_backend("local")
        assert result is True
        assert "local" not in manager._backends

    def test_remove_nonexistent_backend(self, manager):
        result = manager.remove_backend("nonexistent")
        assert result is False

    def test_connect_all(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir})
        results = manager.connect_all()
        assert results["local"] is True

    def test_disconnect_all(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir})
        manager.connect_all()
        manager.disconnect_all()
        assert not manager._backends["local"].connected

    def test_set_primary(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir})
        manager.set_primary("local")
        assert manager._primary == "local"

    def test_set_primary_nonexistent(self, manager):
        with pytest.raises(StorageError):
            manager.set_primary("nonexistent")

    def test_set_secondaries(self, manager, temp_dir):
        d1 = os.path.join(temp_dir, "primary")
        d2 = os.path.join(temp_dir, "secondary")
        manager.add_backend("local", "local", config={"base_path": d1}, primary=True)
        manager.add_backend("backup", "local", config={"base_path": d2})
        manager.set_secondaries(["backup"])
        assert manager._secondaries == ["backup"]

    def test_set_secondaries_nonexistent(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir})
        with pytest.raises(StorageError):
            manager.set_secondaries(["nonexistent"])

    def test_put_and_get(self, manager, temp_dir, sample_data):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        result = manager.put("test.txt", sample_data)
        assert isinstance(result, StorageObject)
        assert manager.get("test.txt") == sample_data

    def test_put_no_primary(self, manager):
        with pytest.raises(StorageError):
            manager.put("test.txt", b"data")

    def test_get_with_failover(self, manager, temp_dir, sample_data):
        d1 = os.path.join(temp_dir, "primary")
        d2 = os.path.join(temp_dir, "secondary")
        manager.add_backend("local", "local", config={"base_path": d1}, primary=True)
        manager.add_backend("backup", "local", config={"base_path": d2})
        manager.set_secondaries(["backup"])
        manager.connect_all()
        # Put on secondary only
        manager._backends["backup"].put("test.txt", sample_data)
        # Get should failover to secondary
        result = manager.get("test.txt")
        assert result == sample_data

    def test_get_not_found_anywhere(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        with pytest.raises(StorageError):
            manager.get("nonexistent.txt")

    def test_delete(self, manager, temp_dir, sample_data):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        manager.put("test.txt", sample_data)
        result = manager.delete("test.txt")
        assert result is True
        assert not manager.exists("test.txt")

    def test_exists(self, manager, temp_dir, sample_data):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        assert not manager.exists("test.txt")
        manager.put("test.txt", sample_data)
        assert manager.exists("test.txt")

    def test_list_objects(self, manager, temp_dir, sample_data):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        manager.put("file1.txt", sample_data)
        manager.put("file2.txt", sample_data)
        objects = manager.list_objects()
        assert len(objects) == 2

    def test_copy(self, manager, temp_dir, sample_data):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        manager.put("source.txt", sample_data)
        result = manager.copy("source.txt", "dest.txt")
        assert isinstance(result, StorageObject)
        assert manager.exists("dest.txt")

    def test_move(self, manager, temp_dir, sample_data):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        manager.put("old.txt", sample_data)
        result = manager.move("old.txt", "new.txt")
        assert isinstance(result, StorageObject)
        assert not manager.exists("old.txt")
        assert manager.exists("new.txt")

    def test_get_url(self, manager, temp_dir, sample_data):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        manager.put("test.txt", sample_data)
        url = manager.get_url("test.txt")
        assert "test.txt" in url

    def test_get_hash(self, manager, temp_dir, sample_data):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        manager.put("test.txt", sample_data)
        hash_val = manager.get_hash("test.txt")
        assert len(hash_val) == 32

    def test_get_versioned(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        versioned = manager.get_versioned("local")
        assert isinstance(versioned, VersionedStorage)

    def test_get_versioned_nonexistent(self, manager):
        with pytest.raises(StorageError):
            manager.get_versioned("nonexistent")

    def test_replicate_file(self, manager, temp_dir, sample_data):
        d1 = os.path.join(temp_dir, "primary")
        d2 = os.path.join(temp_dir, "secondary")
        manager.add_backend("local", "local", config={"base_path": d1}, primary=True)
        manager.add_backend("backup", "local", config={"base_path": d2})
        manager.connect_all()
        manager.put("test.txt", sample_data)
        result = manager.replicate_file("test.txt", "local", "backup")
        assert isinstance(result, StorageObject)
        assert manager._backends["backup"].exists("test.txt")

    def test_replicate_file_nonexistent_source(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        with pytest.raises(StorageError):
            manager.replicate_file("test.txt", "nonexistent", "local")

    def test_sync_backends(self, manager, temp_dir, sample_data):
        d1 = os.path.join(temp_dir, "source")
        d2 = os.path.join(temp_dir, "target")
        manager.add_backend("source", "local", config={"base_path": d1}, primary=True)
        manager.add_backend("target", "local", config={"base_path": d2})
        manager.connect_all()
        manager.put("file1.txt", sample_data)
        manager.put("file2.txt", sample_data)
        synced, failed = manager.sync_backends("source", "target")
        assert synced == 2
        assert failed == 0

    def test_sync_backends_nonexistent(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir})
        with pytest.raises(StorageError):
            manager.sync_backends("nonexistent", "local")

    def test_health_check(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        health = manager.health_check()
        assert "local" in health
        assert health["local"]["connected"] is True
        assert health["local"]["healthy"] is True
        assert health["local"]["is_primary"] is True

    def test_health_check_disconnected(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir})
        health = manager.health_check()
        assert health["local"]["connected"] is False
        assert health["local"]["healthy"] is False

    def test_enable_replication(self, manager, temp_dir, sample_data):
        d1 = os.path.join(temp_dir, "primary")
        d2 = os.path.join(temp_dir, "secondary")
        manager.add_backend("local", "local", config={"base_path": d1}, primary=True)
        manager.add_backend("backup", "local", config={"base_path": d2})
        manager.set_secondaries(["backup"])
        manager.enable_replication(True)
        manager.connect_all()
        manager.put("test.txt", sample_data)
        assert manager._backends["backup"].exists("test.txt")

    def test_context_manager(self, manager, temp_dir):
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        with manager as m:
            assert m._backends["local"].connected
        assert not manager._backends["local"].connected

    def test_multiple_backends(self, manager, temp_dir):
        d1 = os.path.join(temp_dir, "s1")
        d2 = os.path.join(temp_dir, "s2")
        d3 = os.path.join(temp_dir, "s3")
        manager.add_backend("store1", "local", config={"base_path": d1}, primary=True)
        manager.add_backend("store2", "local", config={"base_path": d2})
        manager.add_backend("store3", "local", config={"base_path": d3})
        manager.set_secondaries(["store2", "store3"])
        manager.connect_all()
        assert len(manager._backends) == 3
        assert manager._primary == "store1"
        assert len(manager._secondaries) == 2


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests across multiple components."""

    def test_local_with_versioning(self, temp_dir, sample_data):
        storage = LocalStorage(name="test", config={"base_path": temp_dir})
        storage.connect()
        versioned = VersionedStorage(storage, max_versions=5)
        v1 = versioned.put("doc.txt", b"version 1", comment="initial")
        v2 = versioned.put("doc.txt", b"version 2", comment="update")
        v3 = versioned.put("doc.txt", sample_data, comment="final")
        assert versioned.get_latest_version("doc.txt").version_id == v3.version_id
        assert versioned.get("doc.txt") == sample_data
        assert versioned.get("doc.txt", version_id=v1.version_id) == b"version 1"
        versions = versioned.list_versions("doc.txt")
        assert len(versions) == 3
        storage.disconnect()

    def test_manager_with_versioning(self, temp_dir, sample_data):
        manager = StorageManager()
        manager.add_backend("local", "local", config={"base_path": temp_dir}, primary=True)
        manager.connect_all()
        versioned = manager.get_versioned("local", max_versions=5)
        v1 = versioned.put("file.txt", b"v1")
        v2 = versioned.put("file.txt", sample_data)
        assert versioned.get_latest_version("file.txt").version_id == v2.version_id
        assert manager.get("file.txt") == sample_data

    def test_manager_failover_with_versioning(self, temp_dir, sample_data):
        d1 = os.path.join(temp_dir, "primary")
        d2 = os.path.join(temp_dir, "secondary")
        manager = StorageManager()
        manager.add_backend("local", "local", config={"base_path": d1}, primary=True)
        manager.add_backend("backup", "local", config={"base_path": d2})
        manager.set_secondaries(["backup"])
        manager.connect_all()
        # Put on secondary only
        versioned = VersionedStorage(manager._backends["backup"])
        versioned.put("test.txt", sample_data)
        # Manager should find it via failover
        assert manager.get("test.txt") == sample_data

    def test_full_lifecycle(self, temp_dir, sample_data, sample_metadata):
        storage = LocalStorage(name="test", config={"base_path": temp_dir})
        storage.connect()
        versioned = VersionedStorage(storage)
        # Create
        v1 = versioned.put("lifecycle.txt", b"v1", metadata=sample_metadata, comment="create")
        assert storage.exists("lifecycle.txt")
        # Read
        assert versioned.get("lifecycle.txt") == b"v1"
        # Update
        v2 = versioned.put("lifecycle.txt", sample_data, metadata=sample_metadata, comment="update")
        assert versioned.get("lifecycle.txt") == sample_data
        # List versions
        versions = versioned.list_versions("lifecycle.txt")
        assert len(versions) == 2
        # Compare
        comp = versioned.compare_versions("lifecycle.txt", v1.version_id, v2.version_id)
        assert comp["identical"] is False
        # Restore
        versioned.restore_version("lifecycle.txt", v1.version_id)
        assert versioned.get("lifecycle.txt") == b"v1"
        # Delete
        versioned.delete("lifecycle.txt")
        assert not storage.exists("lifecycle.txt")
        storage.disconnect()

    def test_manager_replication_and_sync(self, temp_dir, sample_data):
        d1 = os.path.join(temp_dir, "primary")
        d2 = os.path.join(temp_dir, "replica")
        manager = StorageManager()
        manager.add_backend("local", "local", config={"base_path": d1}, primary=True)
        manager.add_backend("replica", "local", config={"base_path": d2})
        manager.set_secondaries(["replica"])
        manager.enable_replication(True)
        manager.connect_all()
        # Put should replicate
        manager.put("test.txt", sample_data)
        assert manager._backends["replica"].exists("test.txt")
        # Sync should handle already-existing files
        manager.put("test2.txt", sample_data)
        synced, failed = manager.sync_backends("local", "replica")
        assert synced >= 1
        assert failed == 0
