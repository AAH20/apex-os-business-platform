"""User profile management for the personalization system."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserProfile:
    """Represents a user's personalization profile.

    Attributes:
        user_id: Unique identifier for the user.
        segments: List of segment names the user belongs to.
        preferences: Key-value preference store.
        attributes: Arbitrary user attributes (demographics, metadata).
        created_at: Unix timestamp of profile creation.
        updated_at: Unix timestamp of last update.
    """

    user_id: str
    segments: list[str] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_segment(self, segment: str) -> None:
        """Add a segment to the user's profile if not already present."""
        if segment not in self.segments:
            self.segments.append(segment)
            self.updated_at = time.time()

    def remove_segment(self, segment: str) -> None:
        """Remove a segment from the user's profile."""
        if segment in self.segments:
            self.segments.remove(segment)
            self.updated_at = time.time()

    def set_preference(self, key: str, value: Any) -> None:
        """Set a preference value."""
        self.preferences[key] = value
        self.updated_at = time.time()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value with optional default."""
        return self.preferences.get(key, default)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute value."""
        self.attributes[key] = value
        self.updated_at = time.time()

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get an attribute value with optional default."""
        return self.attributes.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile to dictionary."""
        return {
            "user_id": self.user_id,
            "segments": list(self.segments),
            "preferences": dict(self.preferences),
            "attributes": dict(self.attributes),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        """Deserialize profile from dictionary."""
        return cls(
            user_id=data["user_id"],
            segments=list(data.get("segments", [])),
            preferences=dict(data.get("preferences", {})),
            attributes=dict(data.get("attributes", {})),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class ProfileStore:
    """In-memory store for user profiles with CRUD operations."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    def create(self, user_id: str, **kwargs: Any) -> UserProfile:
        """Create a new user profile."""
        if user_id in self._profiles:
            raise ValueError(f"Profile already exists for user: {user_id}")
        profile = UserProfile(user_id=user_id, **kwargs)
        self._profiles[user_id] = profile
        return profile

    def get(self, user_id: str) -> UserProfile | None:
        """Retrieve a profile by user ID."""
        return self._profiles.get(user_id)

    def get_or_create(self, user_id: str, **kwargs: Any) -> UserProfile:
        """Get existing profile or create a new one."""
        profile = self.get(user_id)
        if profile is None:
            profile = self.create(user_id, **kwargs)
        return profile

    def update(self, user_id: str, **kwargs: Any) -> UserProfile:
        """Update an existing profile."""
        profile = self._profiles.get(user_id)
        if profile is None:
            raise KeyError(f"Profile not found for user: {user_id}")
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = time.time()
        return profile

    def delete(self, user_id: str) -> bool:
        """Delete a profile. Returns True if deleted, False if not found."""
        if user_id in self._profiles:
            del self._profiles[user_id]
            return True
        return False

    def list_all(self) -> list[UserProfile]:
        """Return all profiles."""
        return list(self._profiles.values())

    def find_by_segment(self, segment: str) -> list[UserProfile]:
        """Find all profiles belonging to a segment."""
        return [p for p in self._profiles.values() if segment in p.segments]

    def count(self) -> int:
        """Return the number of stored profiles."""
        return len(self._profiles)
