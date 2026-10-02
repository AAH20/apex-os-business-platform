"""Full-text search for documents."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .models import Document


@dataclass
class SearchResult:
    """A single search result with relevance score."""

    document: Document
    score: float
    matched_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "document": self.document.to_dict(),
            "score": self.score,
            "matched_fields": self.matched_fields,
        }


class SearchEngine:
    """In-memory full-text search engine for documents.

    Supports searching by name, tags, metadata, and content.
    Uses simple TF-based scoring with field weighting.
    """

    # Field weights for scoring
    NAME_WEIGHT = 3.0
    TAG_WEIGHT = 2.5
    METADATA_WEIGHT = 1.5
    CONTENT_WEIGHT = 1.0

    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._index: dict[str, set[str]] = defaultdict(set)  # token -> doc_ids
        self._content_store: dict[str, bytes] = {}

    def add_document(self, document: Document, content: Optional[bytes] = None) -> None:
        """Index a document for search."""
        self._documents[document.id] = document

        # Index name tokens
        for token in self._tokenize(document.name):
            self._index[token].add(document.id)

        # Index tag tokens
        for tag in document.tags:
            for token in self._tokenize(tag):
                self._index[token].add(document.id)

        # Index metadata values
        for key, value in document.metadata.items():
            for token in self._tokenize(str(value)):
                self._index[token].add(document.id)
            for token in self._tokenize(str(key)):
                self._index[token].add(document.id)

        # Store content for content search
        if content is not None:
            self._content_store[document.id] = content
            try:
                text = content.decode("utf-8", errors="ignore")
                for token in self._tokenize(text):
                    self._index[token].add(document.id)
            except Exception:
                pass

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the search index."""
        if doc_id not in self._documents:
            return False

        # Remove from inverted index
        tokens_to_remove = []
        for token, doc_ids in self._index.items():
            if doc_id in doc_ids:
                doc_ids.discard(doc_id)
                if not doc_ids:
                    tokens_to_remove.append(token)

        for token in tokens_to_remove:
            del self._index[token]

        del self._documents[doc_id]
        self._content_store.pop(doc_id, None)
        return True

    def update_document(self, document: Document, content: Optional[bytes] = None) -> None:
        """Update a document in the search index."""
        self.remove_document(document.id)
        self.add_document(document, content)

    def search(
        self,
        query: str,
        tags: Optional[list[str]] = None,
        owner_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[SearchResult]:
        """Search documents by query string with optional filters.

        Args:
            query: Search query string.
            tags: Filter by tags (documents must have ALL specified tags).
            owner_id: Filter by owner.
            limit: Maximum results to return.
            offset: Number of results to skip.

        Returns:
            List of SearchResult sorted by relevance score (descending).
        """
        if not query and not tags:
            return []

        query_tokens = self._tokenize(query) if query else []
        tag_tokens = []
        for tag in tags or []:
            tag_tokens.extend(self._tokenize(tag))

        # Score documents
        scores: dict[str, float] = defaultdict(float)
        matched: dict[str, set[str]] = defaultdict(set)

        # Score by query tokens
        for token in query_tokens:
            for doc_id in self._index.get(token, set()):
                doc = self._documents.get(doc_id)
                if not doc or doc.is_deleted:
                    continue

                # Determine which field matched
                field = self._match_field(doc, token)
                weight = self._field_weight(field)
                scores[doc_id] += weight
                matched[doc_id].add(field)

        # Score by tag tokens
        for token in tag_tokens:
            for doc_id in self._index.get(token, set()):
                doc = self._documents.get(doc_id)
                if not doc or doc.is_deleted:
                    continue
                scores[doc_id] += self.TAG_WEIGHT
                matched[doc_id].add("tags")

        # Apply filters
        results: list[SearchResult] = []
        for doc_id, score in scores.items():
            doc = self._documents[doc_id]

            # Filter by owner
            if owner_id and doc.owner_id != owner_id:
                continue

            # Filter by tags (must have all)
            if tags:
                doc_tags_lower = {t.lower() for t in doc.tags}
                if not all(t.lower() in doc_tags_lower for t in tags):
                    continue

            # Boost exact name matches
            if query and query.lower() in doc.name.lower():
                score *= 2.0

            results.append(SearchResult(
                document=doc,
                score=round(score, 4),
                matched_fields=sorted(matched[doc_id]),
            ))

        # Sort by score descending, then by name
        results.sort(key=lambda r: (-r.score, r.document.name))

        # Apply pagination
        return results[offset:offset + limit]

    def search_by_name(self, name_prefix: str, limit: int = 50) -> list[Document]:
        """Search documents by name prefix (case-insensitive)."""
        prefix_lower = name_prefix.lower()
        matches = [
            doc for doc in self._documents.values()
            if not doc.is_deleted and doc.name.lower().startswith(prefix_lower)
        ]
        matches.sort(key=lambda d: d.name)
        return matches[:limit]

    def get_stats(self) -> dict:
        """Return search index statistics."""
        return {
            "total_documents": len(self._documents),
            "total_tokens": len(self._index),
            "indexed_content": len(self._content_store),
        }

    def clear(self) -> None:
        """Clear the entire search index."""
        self._documents.clear()
        self._index.clear()
        self._content_store.clear()

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase alphanumeric tokens."""
        if not text:
            return []
        return re.findall(r"[a-z0-9]+", text.lower())

    def _match_field(self, doc: Document, token: str) -> str:
        """Determine which field a token matched."""
        name_tokens = set(self._tokenize(doc.name))
        if token in name_tokens:
            return "name"

        for tag in doc.tags:
            if token in set(self._tokenize(tag)):
                return "tags"

        for key, value in doc.metadata.items():
            if token in set(self._tokenize(str(value))):
                return "metadata"
            if token in set(self._tokenize(str(key))):
                return "metadata"

        return "content"

    def _field_weight(self, field_name: str) -> float:
        """Get the weight for a matched field."""
        weights = {
            "name": self.NAME_WEIGHT,
            "tags": self.TAG_WEIGHT,
            "metadata": self.METADATA_WEIGHT,
            "content": self.CONTENT_WEIGHT,
        }
        return weights.get(field_name, 1.0)
