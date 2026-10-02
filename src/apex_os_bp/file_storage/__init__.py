"""APEX-OS File Storage System.

Provides unified file storage across multiple backends:
- Local filesystem
- AWS S3
- Azure Blob Storage
- Google Cloud Storage
- File versioning
"""

from apex_os_bp.file_storage.base import StorageBackend, StorageObject, StorageError
from apex_os_bp.file_storage.local import LocalStorage
from apex_os_bp.file_storage.s3 import S3Storage
from apex_os_bp.file_storage.azure import AzureStorage
from apex_os_bp.file_storage.gcp import GCPStorage
from apex_os_bp.file_storage.versioning import FileVersion, VersionedStorage
from apex_os_bp.file_storage.manager import StorageManager

__all__ = [
    "StorageBackend",
    "StorageObject",
    "StorageError",
    "LocalStorage",
    "S3Storage",
    "AzureStorage",
    "GCPStorage",
    "FileVersion",
    "VersionedStorage",
    "StorageManager",
]
