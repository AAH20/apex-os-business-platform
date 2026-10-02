"""Document search engine."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from apex_os_bp.knowledge.models import Document, DocumentType


@dataclass
class SearchResult:
    """Search result with relevance score."""
    document: Document
    score: float
    highlights: List[str]


class DocumentSearch:
    """Full-text document search engine."""

    def __init__(self):
        self._documents: Dict[str, Document] = {}

    def add_document(
        self,
        title: str,
        content: str,
        doc_type: DocumentType = DocumentType.ARTICLE,
        **kwargs,
    ) -> Document:
        """Add a document to the index."""
        doc = Document(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            doc_type=doc_type,
            **kwargs,
        )
        self._documents[doc.id] = doc
        return doc

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self._documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search documents by query string."""
        if not query.strip():
            return []

        query_lower = query.lower()
        query_terms = set(query_lower.split())
        results: List[SearchResult] = []

        for doc in self._documents.values():
            score = self._score_document(doc, query_lower, query_terms)
            if score > 0:
                highlights = self._extract_highlights(doc.content, query_terms)
                results.append(SearchResult(document=doc, score=score, highlights=highlights))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def search_by_type(self, doc_type: DocumentType, limit: int = 10) -> List[Document]:
        """Search documents by type."""
        results = [doc for doc in self._documents.values() if doc.doc_type == doc_type]
        return results[:limit]

    def search_by_tag(self, tag: str, limit: int = 10) -> List[Document]:
        """Search documents by tag."""
        results = [doc for doc in self._documents.values() if tag in doc.tags]
        return results[:limit]

    def get_all_documents(self) -> List[Document]:
        """Get all documents."""
        return list(self._documents.values())

    def count(self) -> int:
        """Get total document count."""
        return len(self._documents)

    def _score_document(self, doc: Document, query_lower: str, query_terms: set) -> float:
        """Calculate relevance score for a document."""
        score = 0.0
        title_lower = doc.title.lower()
        content_lower = doc.content.lower()

        # Title match (weighted higher)
        if query_lower in title_lower:
            score += 10.0
        for term in query_terms:
            if term in title_lower:
                score += 5.0

        # Content match
        if query_lower in content_lower:
            score += 3.0
        for term in query_terms:
            count = content_lower.count(term)
            score += min(count * 0.5, 5.0)

        # Tag match
        for tag in doc.tags:
            tag_lower = tag.lower()
            if query_lower in tag_lower:
                score += 4.0
            for term in query_terms:
                if term in tag_lower:
                    score += 2.0

        return score

    def _extract_highlights(self, content: str, query_terms: set, context: int = 40) -> List[str]:
        """Extract text highlights around query matches."""
        highlights: List[str] = []
        content_lower = content.lower()

        for term in query_terms:
            start = 0
            while True:
                idx = content_lower.find(term, start)
                if idx == -1:
                    break
                h_start = max(0, idx - context)
                h_end = min(len(content), idx + len(term) + context)
                snippet = content[h_start:h_end].strip()
                if snippet and snippet not in highlights:
                    highlights.append(snippet)
                start = idx + len(term)
                if len(highlights) >= 3:
                    break
            if len(highlights) >= 3:
                break

        return highlights
