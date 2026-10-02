"""Document sharing and access control."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import Document, DocumentShare, Permission


class SharingError(Exception):
    """Raised when a sharing operation fails."""


class ShareManager:
    """Manages document share links and access control."""

    def __init__(self):
        self._shares: dict[str, DocumentShare] = {}  # share_id -> share
        self._token_index: dict[str, str] = {}  # token -> share_id
        self._doc_shares: dict[str, list[str]] = {}  # doc_id -> [share_ids]

    def create_share(
        self,
        document: Document,
        shared_by: str,
        shared_with: str = "",
        permission: Permission = Permission.VIEW,
        expires_in_days: Optional[int] = None,
    ) -> DocumentShare:
        """Create a share link for a document.

        Args:
            document: The document to share.
            shared_by: ID of the user creating the share.
            shared_with: ID of the user being shared with (empty for public link).
            permission: Access level to grant.
            expires_in_days: Optional expiration in days.

        Returns:
            The created DocumentShare.
        """
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        share = DocumentShare(
            document_id=document.id,
            shared_by=shared_by,
            shared_with=shared_with,
            permission=permission,
            share_token=secrets.token_urlsafe(32),
            expires_at=expires_at,
        )

        self._shares[share.id] = share
        self._token_index[share.share_token] = share.id

        if document.id not in self._doc_shares:
            self._doc_shares[document.id] = []
        self._doc_shares[document.id].append(share.id)

        return share

    def get_share(self, share_id: str) -> Optional[DocumentShare]:
        """Get a share by its ID."""
        return self._shares.get(share_id)

    def get_share_by_token(self, token: str) -> Optional[DocumentShare]:
        """Get a share by its public token."""
        share_id = self._token_index.get(token)
        if share_id:
            return self._shares.get(share_id)
        return None

    def validate_access(
        self, token: str, required_permission: Permission = Permission.VIEW
    ) -> DocumentShare:
        """Validate a share token and check permission level.

        Args:
            token: The share token to validate.
            required_permission: Minimum permission required.

        Returns:
            The valid DocumentShare.

        Raises:
            SharingError: If token is invalid, expired, or insufficient permission.
        """
        share = self.get_share_by_token(token)
        if share is None:
            raise SharingError("Invalid share token")

        if not share.is_active:
            raise SharingError("Share link has been revoked")

        if share.expires_at and datetime.now(timezone.utc) > share.expires_at:
            raise SharingError("Share link has expired")

        if not self._permission_sufficient(share.permission, required_permission):
            raise SharingError(
                f"Insufficient permissions: {share.permission.value} "
                f"(required: {required_permission.value})"
            )

        # Increment access counter
        share.access_count += 1
        return share

    def revoke_share(self, share_id: str, revoked_by: str = "") -> bool:
        """Revoke a share link.

        Returns:
            True if the share was revoked, False if not found.
        """
        share = self._shares.get(share_id)
        if share is None:
            return False

        share.is_active = False
        return True

    def revoke_all_shares(self, document_id: str) -> int:
        """Revoke all shares for a document.

        Returns:
            Number of shares revoked.
        """
        share_ids = self._doc_shares.get(document_id, [])
        count = 0
        for sid in share_ids:
            share = self._shares.get(sid)
            if share and share.is_active:
                share.is_active = False
                count += 1
        return count

    def update_permission(
        self, share_id: str, new_permission: Permission
    ) -> DocumentShare:
        """Update the permission level of a share.

        Returns:
            The updated DocumentShare.

        Raises:
            SharingError: If share not found.
        """
        share = self._shares.get(share_id)
        if share is None:
            raise SharingError(f"Share {share_id} not found")

        share.permission = new_permission
        return share

    def list_shares(self, document_id: str) -> list[DocumentShare]:
        """List all shares for a document."""
        share_ids = self._doc_shares.get(document_id, [])
        return [self._shares[sid] for sid in share_ids if sid in self._shares]

    def list_active_shares(self, document_id: str) -> list[DocumentShare]:
        """List all active (non-revoked, non-expired) shares for a document."""
        shares = self.list_shares(document_id)
        now = datetime.now(timezone.utc)
        return [
            s for s in shares
            if s.is_active and (s.expires_at is None or s.expires_at > now)
        ]

    def get_share_stats(self, document_id: str) -> dict:
        """Get sharing statistics for a document."""
        shares = self.list_shares(document_id)
        active = [s for s in shares if s.is_active]
        expired = [
            s for s in shares
            if s.expires_at and datetime.now(timezone.utc) > s.expires_at
        ]
        total_access = sum(s.access_count for s in shares)

        return {
            "total_shares": len(shares),
            "active_shares": len(active),
            "expired_shares": len(expired),
            "total_access_count": total_access,
        }

    def cleanup_expired(self) -> int:
        """Deactivate all expired shares.

        Returns:
            Number of shares deactivated.
        """
        now = datetime.now(timezone.utc)
        count = 0
        for share in self._shares.values():
            if share.is_active and share.expires_at and share.expires_at <= now:
                share.is_active = False
                count += 1
        return count

    def clear(self) -> None:
        """Clear all share data. Useful for testing."""
        self._shares.clear()
        self._token_index.clear()
        self._doc_shares.clear()

    @staticmethod
    def _permission_sufficient(
        have: Permission, required: Permission
    ) -> bool:
        """Check if the held permission meets the required level."""
        hierarchy = {
            Permission.VIEW: 1,
            Permission.EDIT: 2,
            Permission.ADMIN: 3,
        }
        return hierarchy.get(have, 0) >= hierarchy.get(required, 0)
