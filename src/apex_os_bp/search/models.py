"""Shared data models for the search system."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DocumentType(Enum):
    """Searchable document types."""
    ARTICLE = "article"
    PRODUCT = "product"
    CUSTOMER = "customer"
    ORDER = "order"
    INVOICE = "invoice"
    TASK = "task"
    PROJECT = "project"
    NOTE = "note"
    FAQ = "faq"
    POLICY = "policy"
    PROCEDURE = "procedure"
    GUIDE = "guide"
    OTHER = "other"


@dataclass
class SearchableDocument:
    """A document that can be indexed and searched."""
    id: str
    title: str
    content: str
    doc_type: DocumentType = DocumentType.OTHER
    author_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        title: str,
        content: str,
        doc_type: DocumentType = DocumentType.OTHER,
        **kwargs: Any,
    ) -> SearchableDocument:
        """Factory method to create a document with a generated ID."""
        return cls(id=str(uuid.uuid4()), title=title, content=content, doc_type=doc_type, **kwargs)


@dataclass
class SearchResult:
    """A single search result with relevance score and highlights."""
    document: SearchableDocument
    score: float
    highlights: List[str] = field(default_factory=list)
    matched_fields: List[str] = field(default_factory=list)


@dataclass
class FacetValue:
    """A single facet value with its count."""
    value: str
    count: int
    selected: bool = False


@dataclass
class Facet:
    """A search facet with its possible values."""
    name: str
    values: List[FacetValue] = field(default_factory=list)


@dataclass
class FacetedSearchResult:
    """Result of a faceted search."""
    results: List[SearchResult]
    facets: List[Facet]
    total_count: int
    page: int = 1
    per_page: int = 20
    total_pages: int = 0


@dataclass
class SearchSuggestion:
    """A search suggestion (autocomplete or did-you-mean)."""
    text: str
    type: str  # "completion", "correction", "related", "trending"
    score: float = 0.0
    payload: Optional[Dict[str, Any]] = None


@dataclass
class SearchAnalyticsEvent:
    """A search analytics event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    user_id: Optional[str] = None
    timestamp: Optional[str] = None
    result_count: int = 0
    clicked_result_id: Optional[str] = None
    clicked_position: Optional[int] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    latency_ms: Optional[float] = None
