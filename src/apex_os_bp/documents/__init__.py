"""Document management system for APEX-OS Business Platform.

Provides upload, storage, search, versioning, and sharing capabilities.
"""

from .models import Document, DocumentVersion, DocumentShare, Permission
from .storage import LocalStorage, StorageBackend
from .upload import UploadManager
from .search import SearchEngine
from .versioning import VersionManager
from .sharing import ShareManager

__all__ = [
    "Document",
    "DocumentVersion",
    "DocumentShare",
    "Permission",
    "LocalStorage",
    "StorageBackend",
    "UploadManager",
    "SearchEngine",
    "VersionManager",
    "ShareManager",
]
