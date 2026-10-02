"""AWS S3 storage backend."""

import hashlib
import io
import mimetypes
from datetime import datetime
from typing import Dict, List, Optional

from apex_os_bp.file_storage.base import StorageBackend, StorageObject, StorageError


class S3Storage(StorageBackend):
    """AWS S3 storage backend using boto3."""

    def __init__(self, name: str = "s3", config: Optional[Dict] = None):
        super().__init__(name, config)
        self.bucket = self.config.get("bucket", "")
        self.region = self.config.get("region", "us-east-1")
        self.access_key = self.config.get("access_key", "")
        self.secret_key = self.config.get("secret_key", "")
        self.endpoint_url = self.config.get("endpoint_url", None)
        self._client = None
        self._resource = None

    def connect(self) -> None:
        """Establish connection to S3."""
        try:
            import boto3
            from botocore.config import Config as BotoConfig

            session_kwargs = {}
            if self.access_key and self.secret_key:
                session_kwargs["aws_access_key_id"] = self.access_key
                session_kwargs["aws_secret_access_key"] = self.secret_key

            session = boto3.Session(**session_kwargs)

            client_kwargs = {
                "region_name": self.region,
                "config": BotoConfig(
                    retries={"max_attempts": 3, "mode": "standard"},
                    max_pool_connections=25,
                ),
            }
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url

            self._client = session.client("s3", **client_kwargs)
            self._resource = session.resource("s3", **client_kwargs)

            # Verify bucket exists / create it
            try:
                self._client.head_bucket(Bucket=self.bucket)
            except Exception:
                self._client.create_bucket(
                    Bucket=self.bucket,
                    CreateBucketConfiguration={"LocationConstraint": self.region}
                    if self.region != "us-east-1" else {},
                )

            self._connected = True
        except ImportError:
            raise StorageError(
                "boto3 is required for S3 storage. Install with: pip install boto3",
                backend=self.name,
            )
        except Exception as e:
            raise StorageError(f"Failed to connect to S3: {e}", backend=self.name, original_error=e)

    def disconnect(self) -> None:
        """Close S3 connection."""
        self._client = None
        self._resource = None
        self._connected = False

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream",
            metadata: Optional[Dict[str, str]] = None) -> StorageObject:
        """Upload a file to S3."""
        self._ensure_connected()
        try:
            extra_args = {
                "ContentType": content_type,
            }
            if metadata:
                extra_args["Metadata"] = metadata

            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                **extra_args,
            )

            # Get the uploaded object's info
            return self.get_object(key)
        except Exception as e:
            raise StorageError(f"Failed to upload '{key}' to S3: {e}", backend=self.name, original_error=e)

    def get(self, key: str) -> bytes:
        """Download a file from S3."""
        self._ensure_connected()
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except self._client.exceptions.NoSuchKey:
            raise StorageError(f"File not found in S3: {key}", backend=self.name)
        except Exception as e:
            raise StorageError(f"Failed to download '{key}' from S3: {e}", backend=self.name, original_error=e)

    def get_object(self, key: str) -> StorageObject:
        """Get S3 object metadata."""
        self._ensure_connected()
        try:
            response = self._client.head_object(Bucket=self.bucket, Key=key)
            return StorageObject(
                key=key,
                size=response.get("ContentLength", 0),
                content_type=response.get("ContentType", "application/octet-stream"),
                metadata=response.get("Metadata", {}),
                etag=response.get("ETag", "").strip('"'),
                last_modified=response.get("LastModified"),
                version_id=response.get("VersionId"),
            )
        except self._client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise StorageError(f"File not found in S3: {key}", backend=self.name)
            raise StorageError(f"Failed to get S3 object info '{key}': {e}", backend=self.name, original_error=e)

    def delete(self, key: str) -> bool:
        """Delete a file from S3."""
        self._ensure_connected()
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete '{key}' from S3: {e}", backend=self.name, original_error=e)

    def exists(self, key: str) -> bool:
        """Check if a file exists in S3."""
        self._ensure_connected()
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self._client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise StorageError(f"Failed to check existence of '{key}' in S3: {e}", backend=self.name, original_error=e)

    def list_objects(self, prefix: str = "") -> List[StorageObject]:
        """List objects in S3, optionally filtered by prefix."""
        self._ensure_connected()
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            results = []
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    results.append(StorageObject(
                        key=obj["Key"],
                        size=obj["Size"],
                        etag=obj.get("ETag", "").strip('"'),
                        last_modified=obj.get("LastModified"),
                    ))
            return sorted(results, key=lambda o: o.key)
        except Exception as e:
            raise StorageError(f"Failed to list objects in S3: {e}", backend=self.name, original_error=e)

    def copy(self, source_key: str, dest_key: str) -> StorageObject:
        """Copy an object within S3."""
        self._ensure_connected()
        try:
            copy_source = {"Bucket": self.bucket, "Key": source_key}
            self._client.copy_object(
                Bucket=self.bucket,
                Key=dest_key,
                CopySource=copy_source,
            )
            return self.get_object(dest_key)
        except Exception as e:
            raise StorageError(f"Failed to copy '{source_key}' to '{dest_key}' in S3: {e}", backend=self.name, original_error=e)

    def move(self, source_key: str, dest_key: str) -> StorageObject:
        """Move/rename an object within S3 (copy + delete)."""
        self._ensure_connected()
        try:
            result = self.copy(source_key, dest_key)
            self.delete(source_key)
            return result
        except Exception as e:
            raise StorageError(f"Failed to move '{source_key}' to '{dest_key}' in S3: {e}", backend=self.name, original_error=e)

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for temporary access."""
        self._ensure_connected()
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            raise StorageError(f"Failed to generate pre-signed URL for '{key}': {e}", backend=self.name, original_error=e)

    def get_hash(self, key: str) -> str:
        """Get the MD5 hash (ETag) of an S3 object."""
        self._ensure_connected()
        try:
            response = self._client.head_object(Bucket=self.bucket, Key=key)
            return response.get("ETag", "").strip('"')
        except Exception as e:
            raise StorageError(f"Failed to get hash of '{key}' from S3: {e}", backend=self.name, original_error=e)

    def enable_versioning(self) -> bool:
        """Enable versioning on the S3 bucket."""
        self._ensure_connected()
        try:
            self._client.put_bucket_versioning(
                Bucket=self.bucket,
                VersioningConfiguration={"Status": "Enabled"},
            )
            return True
        except Exception as e:
            raise StorageError(f"Failed to enable versioning on bucket '{self.bucket}': {e}", backend=self.name, original_error=e)

    def list_versions(self, key: str) -> List[StorageObject]:
        """List all versions of an object."""
        self._ensure_connected()
        try:
            paginator = self._client.get_paginator("list_object_versions")
            results = []
            for page in paginator.paginate(Bucket=self.bucket, Prefix=key):
                for version in page.get("Versions", []):
                    if version["Key"] == key:
                        results.append(StorageObject(
                            key=version["Key"],
                            size=version["Size"],
                            etag=version.get("ETag", "").strip('"'),
                            last_modified=version.get("LastModified"),
                            version_id=version.get("VersionId"),
                        ))
            return sorted(results, key=lambda o: o.last_modified or datetime.min, reverse=True)
        except Exception as e:
            raise StorageError(f"Failed to list versions of '{key}' in S3: {e}", backend=self.name, original_error=e)
