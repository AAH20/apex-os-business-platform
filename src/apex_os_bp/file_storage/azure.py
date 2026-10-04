"""Azure Blob Storage backend."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.file_storage.base import StorageBackend, StorageObject, StorageError


class AzureStorage(StorageBackend):
    """Azure Blob Storage backend using azure-storage-blob."""

    def __init__(self, name: str = "azure", config: Optional[Dict] = None):
        super().__init__(name, config)
        self.account_name = self.config.get("account_name", "")
        self.account_key = self.config.get("account_key", "")
        self.connection_string = self.config.get("connection_string", "")
        self.container = self.config.get("container", "")
        self._service_client = None
        self._container_client = None

    def connect(self) -> None:
        """Establish connection to Azure Blob Storage."""
        try:
            from azure.storage.blob import BlobServiceClient

            if self.connection_string:
                self._service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
            elif self.account_name and self.account_key:
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self._service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.account_key,
                )
            else:
                raise StorageError(
                    "Azure storage requires either connection_string or account_name + account_key",
                    backend=self.name,
                )

            # Get or create container
            self._container_client = self._service_client.get_container_client(self.container)
            if not self._container_client.exists():
                self._container_client.create_container()

            self._connected = True
        except ImportError:
            raise StorageError(
                "azure-storage-blob is required for Azure storage. "
                "Install with: pip install azure-storage-blob",
                backend=self.name,
            )
        except Exception as e:
            raise StorageError(
                f"Failed to connect to Azure Blob Storage: {e}",
                backend=self.name,
                original_error=e,
            )

    def disconnect(self) -> None:
        """Close Azure connection."""
        if self._container_client:
            self._container_client.close()
        if self._service_client:
            self._service_client.close()
        self._container_client = None
        self._service_client = None
        self._connected = False

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream",
            metadata: Optional[Dict[str, str]] = None) -> StorageObject:
        """Upload a file to Azure Blob Storage."""
        self._ensure_connected()
        try:
            blob_client = self._container_client.get_blob_client(key)
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_type=content_type,
                metadata=metadata or {},
            )
            return self.get_object(key)
        except Exception as e:
            raise StorageError(
                f"Failed to upload '{key}' to Azure: {e}",
                backend=self.name,
                original_error=e,
            )

    def get(self, key: str) -> bytes:
        """Download a file from Azure Blob Storage."""
        self._ensure_connected()
        try:
            blob_client = self._container_client.get_blob_client(key)
            if not blob_client.exists():
                raise StorageError(f"File not found in Azure: {key}", backend=self.name)
            downloader = blob_client.download_blob()
            return downloader.readall()
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to download '{key}' from Azure: {e}",
                backend=self.name,
                original_error=e,
            )

    def get_object(self, key: str) -> StorageObject:
        """Get Azure blob metadata."""
        self._ensure_connected()
        try:
            blob_client = self._container_client.get_blob_client(key)
            if not blob_client.exists():
                raise StorageError(f"File not found in Azure: {key}", backend=self.name)
            props = blob_client.get_blob_properties()
            return StorageObject(
                key=key,
                size=props.size,
                content_type=props.content_settings.content_type or "application/octet-stream",
                metadata=dict(props.metadata or {}),
                etag=props.etag.strip('"') if props.etag else "",
                last_modified=props.last_modified,
            )
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to get Azure blob info '{key}': {e}",
                backend=self.name,
                original_error=e,
            )

    def delete(self, key: str) -> bool:
        """Delete a file from Azure Blob Storage."""
        self._ensure_connected()
        try:
            blob_client = self._container_client.get_blob_client(key)
            if not blob_client.exists():
                return False
            blob_client.delete_blob()
            return True
        except Exception as e:
            raise StorageError(
                f"Failed to delete '{key}' from Azure: {e}",
                backend=self.name,
                original_error=e,
            )

    def exists(self, key: str) -> bool:
        """Check if a file exists in Azure Blob Storage."""
        self._ensure_connected()
        try:
            blob_client = self._container_client.get_blob_client(key)
            return blob_client.exists()
        except Exception as e:
            raise StorageError(
                f"Failed to check existence of '{key}' in Azure: {e}",
                backend=self.name,
                original_error=e,
            )

    def list_objects(self, prefix: str = "") -> List[StorageObject]:
        """List blobs in Azure container, optionally filtered by prefix."""
        self._ensure_connected()
        try:
            results = []
            blobs = self._container_client.list_blobs(name_starts_with=prefix)
            for blob in blobs:
                results.append(StorageObject(
                    key=blob.name,
                    size=blob.size,
                    etag=blob.etag.strip('"') if blob.etag else "",
                    last_modified=blob.last_modified,
                ))
            return sorted(results, key=lambda o: o.key)
        except Exception as e:
            raise StorageError(
                f"Failed to list objects in Azure: {e}",
                backend=self.name,
                original_error=e,
            )

    def copy(self, source_key: str, dest_key: str) -> StorageObject:
        """Copy a blob within Azure Storage."""
        self._ensure_connected()
        try:
            source_blob = self._container_client.get_blob_client(source_key)
            dest_blob = self._container_client.get_blob_client(dest_key)
            if not source_blob.exists():
                raise StorageError(f"Source blob not found: {source_key}", backend=self.name)
            dest_blob.start_copy_from_url(source_blob.url)
            return self.get_object(dest_key)
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to copy '{source_key}' to '{dest_key}' in Azure: {e}",
                backend=self.name,
                original_error=e,
            )

    def move(self, source_key: str, dest_key: str) -> StorageObject:
        """Move/rename a blob within Azure Storage (copy + delete)."""
        self._ensure_connected()
        try:
            result = self.copy(source_key, dest_key)
            self.delete(source_key)
            return result
        except Exception as e:
            raise StorageError(
                f"Failed to move '{source_key}' to '{dest_key}' in Azure: {e}",
                backend=self.name,
                original_error=e,
            )

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a SAS URL for temporary access."""
        self._ensure_connected()
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions

            blob_client = self._container_client.get_blob_client(key)
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container,
                blob_name=key,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expires_in),
            )
            return f"{blob_client.url}?{sas_token}"
        except Exception as e:
            raise StorageError(
                f"Failed to generate SAS URL for '{key}': {e}",
                backend=self.name,
                original_error=e,
            )

    def get_hash(self, key: str) -> str:
        """Get the MD5 hash of an Azure blob."""
        self._ensure_connected()
        try:
            blob_client = self._container_client.get_blob_client(key)
            if not blob_client.exists():
                raise StorageError(f"File not found in Azure: {key}", backend=self.name)
            props = blob_client.get_blob_properties()
            content_md5 = props.content_settings.content_md5
            if content_md5:
                return content_md5.hex()
            # Fallback: compute from etag
            return props.etag.strip('"') if props.etag else ""
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to get hash of '{key}' from Azure: {e}",
                backend=self.name,
                original_error=e,
            )
