"""Faceted search engine with dynamic facet computation and filtering."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from apex_os_bp.search.models import (
    Facet,
    FacetValue,
    FacetedSearchResult,
    SearchResult,
    SearchableDocument,
)
from apex_os_bp.search.full_text import FullTextSearchEngine


class FacetedSearchEngine:
    """Faceted search engine that extends full-text search with faceted navigation.

    Supports:
    - Dynamic facet computation (doc_type, category, status, tags, priority)
    - Multi-select facet filtering
    - Facet count aggregation
    - Pagination within faceted results
    """

    DEFAULT_FACET_FIELDS = ["doc_type", "category", "status", "tags"]

    def __init__(self, full_text_engine: Optional[FullTextSearchEngine] = None) -> None:
        self._engine = full_text_engine or FullTextSearchEngine()

    @property
    def engine(self) -> FullTextSearchEngine:
        return self._engine

    def add_document(self, document: SearchableDocument) -> SearchableDocument:
        return self._engine.add_document(document)

    def add_documents(self, documents: List[SearchableDocument]) -> List[SearchableDocument]:
        return self._engine.add_documents(documents)

    def remove_document(self, doc_id: str) -> bool:
        return self._engine.remove_document(doc_id)

    def clear(self) -> None:
        self._engine.clear()

    @property
    def document_count(self) -> int:
        return self._engine.document_count

    def search(
        self,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        facet_fields: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "relevance",
        sort_order: str = "desc",
    ) -> FacetedSearchResult:
        """Execute a faceted search with filtering and pagination.

        Args:
            query: Full-text search query string.
            filters: Dict of facet field -> value(s) to filter on.
            facet_fields: List of fields to compute facets for.
            page: 1-indexed page number.
            per_page: Results per page.
            sort_by: Sort field ("relevance", "title", "created_at", "priority").
            sort_order: "asc" or "desc".

        Returns:
            FacetedSearchResult with results, facets, and pagination info.
        """
        filters = filters or {}
        facet_fields = facet_fields or self.DEFAULT_FACET_FIELDS

        # Execute full-text search with filters
        if query.strip():
            all_results = self._engine.search(
                query=query,
                limit=self._engine.document_count,
                offset=0,
                filters=filters if filters else None,
            )
        else:
            # Empty query: return all documents (with filters applied)
            all_results = []
            for doc in self._engine._documents.values():
                if filters and not self._engine._apply_filters(doc, filters):
                    continue
                all_results.append(SearchResult(
                    document=doc,
                    score=0.0,
                    highlights=[],
                    matched_fields=[],
                ))

        # Apply sorting
        all_results = self._sort_results(all_results, sort_by, sort_order)

        # Compute facets from ALL documents matching the query (not just filtered)
        facets = self._compute_facets(query, facet_fields, filters)

        # Paginate
        total_count = len(all_results)
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0
        start = (page - 1) * per_page
        end = start + per_page
        page_results = all_results[start:end]

        return FacetedSearchResult(
            results=page_results,
            facets=facets,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    def get_facet_counts(
        self,
        query: str = "",
        facet_field: str = "doc_type",
    ) -> List[Tuple[str, int]]:
        """Get facet value counts for a single facet field."""
        if query.strip():
            all_results = self._engine.search(
                query=query,
                limit=self._engine.document_count,
                offset=0,
            )
        else:
            all_results = [
                SearchResult(document=doc, score=0.0)
                for doc in self._engine._documents.values()
            ]
        counter: Counter = Counter()
        for result in all_results:
            doc = result.document
            value = getattr(doc, facet_field, None)
            if value is None:
                continue
            if isinstance(value, list):
                for v in value:
                    counter[str(v)] += 1
            else:
                counter[str(value)] += 1
        return counter.most_common()

    def _compute_facets(
        self,
        query: str,
        facet_fields: List[str],
        active_filters: Dict[str, Any],
    ) -> List[Facet]:
        """Compute facet values and counts for the given fields.

        Facet counts are computed from documents matching the query,
        excluding the filter for the facet's own field (so users
        can see all available values).
        """
        # Get all documents matching the query (without facet filters)
        if query.strip():
            all_results = self._engine.search(
                query=query,
                limit=self._engine.document_count,
                offset=0,
            )
        else:
            all_results = [
                SearchResult(document=doc, score=0.0)
                for doc in self._engine._documents.values()
            ]

        facets: List[Facet] = []

        for field_name in facet_fields:
            counter: Counter = Counter()
            for result in all_results:
                doc = result.document
                value = getattr(doc, field_name, None)
                if value is None:
                    continue
                if isinstance(value, list):
                    for v in value:
                        counter[str(v)] += 1
                else:
                    counter[str(value)] += 1

            # Mark selected values
            active_values = active_filters.get(field_name, [])
            if not isinstance(active_values, list):
                active_values = [active_values]

            facet_values = [
                FacetValue(
                    value=val,
                    count=count,
                    selected=val in active_values,
                )
                for val, count in counter.most_common()
            ]

            facets.append(Facet(name=field_name, values=facet_values))

        return facets

    def _sort_results(
        self,
        results: List[SearchResult],
        sort_by: str,
        sort_order: str,
    ) -> List[SearchResult]:
        """Sort search results by the specified field."""
        reverse = sort_order == "desc"

        if sort_by == "relevance":
            results.sort(key=lambda r: r.score, reverse=reverse)
        elif sort_by == "title":
            results.sort(key=lambda r: r.document.title.lower(), reverse=reverse)
        elif sort_by == "created_at":
            results.sort(
                key=lambda r: r.document.created_at or "",
                reverse=reverse,
            )
        elif sort_by == "priority":
            results.sort(
                key=lambda r: r.document.priority or 0,
                reverse=reverse,
            )
        else:
            results.sort(key=lambda r: r.score, reverse=reverse)

        return results
