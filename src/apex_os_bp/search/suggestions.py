"""Search suggestions engine with did-you-mean, related searches, and trending."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Set, Tuple

from apex_os_bp.search.models import SearchSuggestion, SearchableDocument
from apex_os_bp.search.full_text import FullTextSearchEngine, tokenize, remove_stop_words
from apex_os_bp.search.autocomplete import AutocompleteEngine
from apex_os_bp.search.analytics import SearchAnalyticsEngine


class SearchSuggestionsEngine:
    """Search suggestions engine providing did-you-mean, related searches, and trending.

    Features:
    - Did-you-mean suggestions (spell correction)
    - Related search suggestions (based on co-occurrence)
    - Trending/popular search suggestions
    - Context-aware suggestions (based on recent searches)
    """

    def __init__(
        self,
        full_text_engine: Optional[FullTextSearchEngine] = None,
        autocomplete_engine: Optional[AutocompleteEngine] = None,
        analytics_engine: Optional[SearchAnalyticsEngine] = None,
    ) -> None:
        self._engine = full_text_engine or FullTextSearchEngine()
        self._autocomplete = autocomplete_engine or AutocompleteEngine(self._engine)
        self._analytics = analytics_engine or SearchAnalyticsEngine()
        self._cooccurrence: Dict[str, Counter] = {}
        self._query_corrections: Dict[str, str] = {}

    @property
    def engine(self) -> FullTextSearchEngine:
        return self._engine

    @property
    def autocomplete(self) -> AutocompleteEngine:
        return self._autocomplete

    @property
    def analytics(self) -> SearchAnalyticsEngine:
        return self._analytics

    def add_document(self, document: SearchableDocument) -> SearchableDocument:
        doc = self._engine.add_document(document)
        self._autocomplete.add_document(doc)
        self._update_cooccurrence(doc)
        return doc

    def add_documents(self, documents: List[SearchableDocument]) -> List[SearchableDocument]:
        return [self.add_document(doc) for doc in documents]

    def remove_document(self, doc_id: str) -> bool:
        return self._engine.remove_document(doc_id)

    def clear(self) -> None:
        self._engine.clear()
        self._autocomplete.clear()
        self._analytics.clear()
        self._cooccurrence.clear()
        self._query_corrections.clear()

    # -- Did You Mean -------------------------------------------------------

    def did_you_mean(self, query: str, max_suggestions: int = 3) -> List[SearchSuggestion]:
        """Get spell-correction suggestions for a query.

        Uses edit distance against indexed terms to find close matches.
        """
        if not query.strip():
            return []

        query_lower = query.lower().strip()
        query_tokens = remove_stop_words(tokenize(query_lower))
        if not query_tokens:
            return []

        suggestions: List[SearchSuggestion] = []
        seen: Set[str] = set()

        # Check each query token against indexed terms
        for token in query_tokens:
            # Get all indexed terms
            all_terms = self._engine._index.terms
            candidates: List[Tuple[str, int]] = []
            for term in all_terms:
                dist = self._levenshtein(token, term)
                if 0 < dist <= 2:
                    candidates.append((term, dist))

            candidates.sort(key=lambda x: (x[1], x[0]))

            for term, dist in candidates:
                corrected = self._apply_correction(query_lower, token, term)
                if corrected not in seen:
                    seen.add(corrected)
                    suggestions.append(SearchSuggestion(
                        text=corrected,
                        type="correction",
                        score=1.0 / (dist + 1),
                        payload={"original": query, "corrected_token": term},
                    ))

        suggestions.sort(key=lambda s: s.score, reverse=True)
        return suggestions[:max_suggestions]

    def add_correction(self, misspelled: str, correction: str) -> None:
        """Add a manual query correction mapping."""
        self._query_corrections[misspelled.lower()] = correction

    # -- Related Searches ---------------------------------------------------

    def related_searches(self, query: str, limit: int = 5) -> List[SearchSuggestion]:
        """Get related search suggestions based on term co-occurrence."""
        if not query.strip():
            return []

        query_lower = query.lower().strip()
        query_tokens = set(remove_stop_words(tokenize(query_lower)))
        if not query_tokens:
            return []

        # Aggregate co-occurrence scores
        related_scores: Counter = Counter()
        for token in query_tokens:
            if token in self._cooccurrence:
                for co_token, count in self._cooccurrence[token].items():
                    if co_token not in query_tokens:
                        related_scores[co_token] += count

        suggestions: List[SearchSuggestion] = []
        for term, score in related_scores.most_common(limit):
            suggestions.append(SearchSuggestion(
                text=term,
                type="related",
                score=float(score),
                payload={"co_occurrence": score},
            ))

        return suggestions

    # -- Trending Searches --------------------------------------------------

    def trending_searches(self, limit: int = 10) -> List[SearchSuggestion]:
        """Get trending/popular search suggestions."""
        # From analytics
        top_queries = self._analytics.get_top_queries(limit)
        suggestions: List[SearchSuggestion] = []
        for query, count in top_queries:
            suggestions.append(SearchSuggestion(
                text=query,
                type="trending",
                score=float(count),
                payload={"search_count": count},
            ))

        # If not enough from analytics, supplement from autocomplete
        if len(suggestions) < limit:
            popular = self._autocomplete.get_popular_searches(limit)
            existing = {s.text for s in suggestions}
            for sugg in popular:
                if sugg.text not in existing:
                    suggestions.append(SearchSuggestion(
                        text=sugg.text,
                        type="trending",
                        score=sugg.score,
                        payload={"source": "autocomplete"},
                    ))
                    if len(suggestions) >= limit:
                        break

        return suggestions[:limit]

    # -- Context-Aware Suggestions -------------------------------------------

    def get_suggestions(
        self,
        query: str,
        limit: int = 10,
        include_corrections: bool = True,
        include_related: bool = True,
        include_trending: bool = True,
    ) -> Dict[str, List[SearchSuggestion]]:
        """Get all types of suggestions for a query.

        Returns a dict with keys: "corrections", "related", "trending", "completions".
        """
        result: Dict[str, List[SearchSuggestion]] = {}

        if include_corrections:
            result["corrections"] = self.did_you_mean(query)
        else:
            result["corrections"] = []

        if include_related:
            result["related"] = self.related_searches(query)
        else:
            result["related"] = []

        if include_trending:
            result["trending"] = self.trending_searches()
        else:
            result["trending"] = []

        # Always include completions
        result["completions"] = self._autocomplete.suggest(query, limit=limit)

        return result

    # -- Co-occurrence tracking ---------------------------------------------

    def _update_cooccurrence(self, doc: SearchableDocument) -> None:
        """Update term co-occurrence matrix from a document."""
        tokens = remove_stop_words(tokenize(self._document_to_text(doc)))
        unique_tokens = set(tokens)

        for token in unique_tokens:
            if token not in self._cooccurrence:
                self._cooccurrence[token] = Counter()
            for co_token in unique_tokens:
                if co_token != token:
                    self._cooccurrence[token][co_token] += 1

    def _document_to_text(self, doc: SearchableDocument) -> str:
        """Convert document to text for co-occurrence analysis."""
        parts = [doc.title, doc.content]
        if doc.tags:
            parts.append(" ".join(doc.tags))
        if doc.category:
            parts.append(doc.category)
        return " ".join(parts)

    def _apply_correction(self, query: str, original: str, correction: str) -> str:
        """Apply a correction to a query string."""
        return query.replace(original, correction)

    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        """Compute Levenshtein edit distance."""
        if len(s1) < len(s2):
            return SearchSuggestionsEngine._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)

        prev_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row

        return prev_row[-1]
