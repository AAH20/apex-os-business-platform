"""Google Cloud Storage backend."""

import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.file_storage.base import StorageBackend, StorageObject, StorageError


class GCPStorage(StorageBackend):
    """Google Cloud Storage backend using google-cloud-storage."""

    def __init__(self, name: str = "gcp", config: Optional[Dict] = None):
        super().__init__(name, config)
        self.project_id = self.config.get("project_id", "")
        self.bucket_name = self.config.get("bucket", "")
        self.credentials_path = self.config.get("credentials_path", None)
        self._client = None
        self._bucket = None

    def connect(self) -> None:
        """Establish connection to Google Cloud Storage."""
        try:
            from google.cloud import storage as gcs

            client_kwargs = {}
            if self.project_id:
                client_kwargs["project"] = self.project_id
            if self.credentials_path:
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
                client_kwargs["credentials"] = credentials

            self._client = gcs.Client(**client_kwargs)

            # Get or create bucket
            self._bucket = self._client.bucket(self.bucket_name)
            if not self._bucket.exists():
                self._bucket = self._client.create_bucket(self.bucket_name)

            self._connected = True
        except ImportError:
            raise StorageError(
                "google-cloud-storage is required for GCP storage. "
                "Install with: pip install google-cloud-storage",
                backend=self.name,
            )
        except Exception as e:
            raise StorageError(
                f"Failed to connect to Google Cloud Storage: {e}",
                backend=self.name,
                original_error=e,
            )

    def disconnect(self) -> None:
        """Close GCP connection."""
        if self._client:
            self._client.close()
        self._client = None
        self._bucket = None
        self._connected = False

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream",
            metadata: Optional[Dict[str, str]] = None) -> StorageObject:
        """Upload a file to Google Cloud Storage."""
        self._ensure_connected()
        try:
            blob = self._bucket.blob(key)
            if metadata:
                blob.metadata = metadata
            blob.upload_from_string(data, content_type=content_type)
            return self.get_object(key)
        except Exception as e:
            raise StorageError(
                f"Failed to upload '{key}' to GCS: {e}",
                backend=self.name,
                original_error=e,
            )

    def get(self, key: str) -> bytes:
        """Download a file from Google Cloud Storage."""
        self._ensure_connected()
        try:
            blob = self._bucket.blob(key)
            if not blob.exists():
                raise StorageError(f"File not found in GCS: {key}", backend=self.name)
            return blob.download_as_bytes()
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to download '{key}' from GCS: {e}",
                backend=self.name,
                original_error=e,
            )

    def get_object(self, key: str) -> StorageObject:
        """Get GCS blob metadata."""
        self._ensure_connected()
        try:
            blob = self._bucket.get_blob(key)
            if blob is None:
                raise StorageError(f"File not found in GCS: {key}", backend=self.name)
            return StorageObject(
                key=key,
                size=blob.size or 0,
                content_type=blob.content_type or "application/octet-stream",
                metadata=dict(blob.metadata or {}),
                etag=blob.etag or "",
                last_modified=blob.updated,
            )
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to get GCS blob info '{key}': {e}",
                backend=self.name,
                original_error=e,
            )

    def delete(self, key: str) -> bool:
        """Delete a file from Google Cloud Storage."""
        self._ensure_connected()
        try:
            blob = self._bucket.blob(key)
            if not blob.exists():
                return False
            blob.delete()
            return True
        except Exception as e:
            raise StorageError(
                f"Failed to delete '{key}' from GCS: {e}",
                backend=self.name,
                original_error=e,
            )

    def exists(self, key: str) -> bool:
        """Check if a file exists in Google Cloud Storage."""
        self._ensure_connected()
        try:
            blob = self._bucket.blob(key)
            return blob.exists()
        except Exception as e:
            raise StorageError(
                f"Failed to check existence of '{key}' in GCS: {e}",
                backend=self.name,
                original_error=e,
            )

    def list_objects(self, prefix: str = "") -> List[StorageObject]:
        """List blobs in GCS bucket, optionally filtered by prefix."""
        self._ensure_connected()
        try:
            results = []
            blobs = self._client.list_blobs(self.bucket_name, prefix=prefix)
            for blob in blobs:
                results.append(StorageObject(
                    key=blob.name,
                    size=blob.size or 0,
                    content_type=blob.content_type or "application/octet-stream",
                    metadata=dict(blob.metadata or {}),
                    etag=blob.etag or "",
                    last_modified=blob.updated,
                    generation=blob.generation,
                ))
            return sorted(results, key=lambda o: o.key)
        except Exception as e:
            raise StorageError(
                f"Failed to list objects in GCS: {e}",
                backend=self.name,
                original_error=e,
            )

    def copy(self, source_key: str, dest_key: str) -> StorageObject:
        """Copy a blob within GCS."""
        self._ensure_connected()
        try:
            source_blob = self._bucket.blob(source_key)
            if not source_blob.exists():
                raise StorageError(f"Source blob not found: {source_key}", backend=self.name)
            self._bucket.copy_blob(source_blob, self._bucket, dest_key)
            return self.get_object(dest_key)
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to copy '{source_key}' to '{dest_key}' in GCS: {e}",
                backend=self.name,
                original_error=e,
            )

    def move(self, source_key: str, dest_key: str) -> StorageObject:
        """Move/rename a blob within GCS (copy + delete)."""
        self._ensure_connected()
        try:
            result = self.copy(source_key, dest_key)
            self.delete(source_key)
            return result
        except Exception as e:
            raise StorageError(
                f"Failed to move '{source_key}' to '{dest_key}' in GCS: {e}",
                backend=self.name,
                original_error=e,
            )

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a signed URL for temporary access."""
        self._ensure_connected()
        try:
            blob = self._bucket.blob(key)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires_in),
                method="GET",
            )
            return url
        except Exception as e:
            raise StorageError(
                f"Failed to generate signed URL for '{key}': {e}",
                backend=self.name,
                original_error=e,
            )

    def get_hash(self, key: str) -> str:
        """Get the MD5 hash of a GCS blob."""
        self._ensure_connected()
        try:
            blob = self._bucket.get_blob(key)
            if blob is None:
                raise StorageError(f"File not found in GCS: {key}", backend=self.name)
            if blob.md5_hash:
                return blob.md5_hash
            return blob.crc32c or ""
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to get hash of '{key}' from GCS: {e}",
                backend=self.name,
                original_error=e,
            )
