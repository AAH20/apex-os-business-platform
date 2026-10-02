"""Knowledge base engine."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from apex_os_bp.knowledge.models import KnowledgeItem


class KnowledgeBase:
    """Knowledge base with CRUD operations."""

    def __init__(self):
        self._items: Dict[str, KnowledgeItem] = {}

    def add_item(
        self,
        title: str,
        content: str,
        category: str,
        tags: Optional[List[str]] = None,
        author_id: Optional[str] = None,
        **kwargs,
    ) -> KnowledgeItem:
        """Add a knowledge item."""
        item = KnowledgeItem(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            author_id=author_id,
            **kwargs,
        )
        self._items[item.id] = item
        return item

    def get_item(self, item_id: str) -> Optional[KnowledgeItem]:
        """Get item by ID."""
        return self._items.get(item_id)

    def update_item(self, item_id: str, **kwargs) -> Optional[KnowledgeItem]:
        """Update item fields."""
        item = self._items.get(item_id)
        if not item:
            return None
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        return item

    def delete_item(self, item_id: str) -> bool:
        """Delete item by ID."""
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    def get_all_items(self) -> List[KnowledgeItem]:
        """Get all items."""
        return list(self._items.values())

    def get_by_category(self, category: str) -> List[KnowledgeItem]:
        """Get items by category."""
        return [item for item in self._items.values() if item.category == category]

    def get_by_tag(self, tag: str) -> List[KnowledgeItem]:
        """Get items by tag."""
        return [item for item in self._items.values() if tag in item.tags]

    def get_by_author(self, author_id: str) -> List[KnowledgeItem]:
        """Get items by author."""
        return [item for item in self._items.values() if item.author_id == author_id]

    def count(self) -> int:
        """Get total item count."""
        return len(self._items)

    def categories(self) -> List[str]:
        """Get all unique categories."""
        return list(set(item.category for item in self._items.values()))

    def all_tags(self) -> List[str]:
        """Get all unique tags."""
        tags: set = set()
        for item in self._items.values():
            tags.update(item.tags)
        return list(tags)
