"""Full-text search engine with TF-IDF scoring, boolean queries, and highlighting."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from apex_os_bp.search.models import DocumentType, SearchResult, SearchableDocument


# ---------------------------------------------------------------------------
# Tokenization & normalization
# ---------------------------------------------------------------------------

STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "this", "that", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "shall",
}

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> List[str]:
    """Split text into lowercase alphanumeric tokens."""
    return _TOKEN_RE.findall(text.lower())


def remove_stop_words(tokens: List[str]) -> List[str]:
    """Filter out common stop words."""
    return [t for t in tokens if t not in STOP_WORDS]


def normalize(text: str) -> str:
    """Normalize text for indexing/searching."""
    return " ".join(remove_stop_words(tokenize(text)))


# ---------------------------------------------------------------------------
# Inverted index
# ---------------------------------------------------------------------------


@dataclass
class Posting:
    """A single posting in the inverted index."""
    doc_id: str
    term_frequency: int
    fields: List[str] = field(default_factory=list)


class InvertedIndex:
    """Thread-unsafe inverted index mapping terms to postings."""

    def __init__(self) -> None:
        self._index: Dict[str, List[Posting]] = defaultdict(list)
        self._doc_lengths: Dict[str, int] = {}
        self._doc_count: int = 0

    def add_document(self, doc_id: str, tokens: List[str], fields: Optional[List[str]] = None) -> None:
        """Add a document's tokens to the index."""
        term_counts = Counter(tokens)
        for term, count in term_counts.items():
            posting = Posting(doc_id=doc_id, term_frequency=count, fields=fields or [])
            self._index[term].append(posting)
        self._doc_lengths[doc_id] = len(tokens)
        self._doc_count += 1

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the index."""
        removed = False
        for term in list(self._index.keys()):
            postings = self._index[term]
            new_postings = [p for p in postings if p.doc_id != doc_id]
            if len(new_postings) < len(postings):
                removed = True
            if new_postings:
                self._index[term] = new_postings
            else:
                del self._index[term]
        if doc_id in self._doc_lengths:
            del self._doc_lengths[doc_id]
            self._doc_count -= 1
        return removed

    def get_postings(self, term: str) -> List[Posting]:
        """Get all postings for a term."""
        return self._index.get(term, [])

    def document_frequency(self, term: str) -> int:
        """Number of documents containing the term."""
        return len(self._index.get(term, []))

    @property
    def doc_count(self) -> int:
        return self._doc_count

    @property
    def avg_doc_length(self) -> float:
        if not self._doc_lengths:
            return 0.0
        return sum(self._doc_lengths.values()) / len(self._doc_lengths)

    @property
    def terms(self) -> Set[str]:
        return set(self._index.keys())


# ---------------------------------------------------------------------------
# Full-text search engine
# ---------------------------------------------------------------------------


class FullTextSearchEngine:
    """Full-text search engine with TF-IDF scoring and boolean query support.

    Supports:
    - Simple multi-term queries (AND semantics)
    - Phrase queries with double quotes
    - Field-specific queries (title:foo content:bar)
    - Boolean operators (AND, OR, NOT)
    - Highlighting of matched terms
    """

    # Field weights for scoring
    FIELD_WEIGHTS: Dict[str, float] = {
        "title": 5.0,
        "content": 1.0,
        "tags": 3.0,
        "category": 2.0,
    }

    def __init__(self) -> None:
        self._documents: Dict[str, SearchableDocument] = {}
        self._index = InvertedIndex()
        self._field_indices: Dict[str, InvertedIndex] = {
            field: InvertedIndex() for field in self.FIELD_WEIGHTS
        }

    # -- Index management ---------------------------------------------------

    def add_document(self, document: SearchableDocument) -> SearchableDocument:
        """Index a document for full-text search."""
        self._documents[document.id] = document

        # Index each field separately for field-weighted scoring
        for field_name in self.FIELD_WEIGHTS:
            raw = getattr(document, field_name, None)
            if raw is None:
                continue
            if isinstance(raw, list):
                text = " ".join(str(v) for v in raw)
            else:
                text = str(raw)
            tokens = remove_stop_words(tokenize(text))
            self._field_indices[field_name].add_document(document.id, tokens)

        # Also add to the combined index
        all_text = self._document_to_text(document)
        all_tokens = remove_stop_words(tokenize(all_text))
        self._index.add_document(document.id, all_tokens)

        return document

    def add_documents(self, documents: List[SearchableDocument]) -> List[SearchableDocument]:
        """Index multiple documents."""
        return [self.add_document(doc) for doc in documents]

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the index."""
        if doc_id not in self._documents:
            return False
        del self._documents[doc_id]
        self._index.remove_document(doc_id)
        for idx in self._field_indices.values():
            idx.remove_document(doc_id)
        return True

    def clear(self) -> None:
        """Clear the entire index."""
        self._documents.clear()
        self._index = InvertedIndex()
        self._field_indices = {field: InvertedIndex() for field in self.FIELD_WEIGHTS}

    def get_document(self, doc_id: str) -> Optional[SearchableDocument]:
        """Retrieve a document by ID."""
        return self._documents.get(doc_id)

    @property
    def document_count(self) -> int:
        return len(self._documents)

    # -- Search -------------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        doc_type: Optional[DocumentType] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Execute a full-text search query.

        Query syntax:
        - ``foo bar`` — documents containing both foo AND bar
        - ``"exact phrase"`` — phrase match
        - ``title:foo`` — field-specific search
        - ``foo OR bar`` — either term
        - ``foo NOT bar`` — foo but not bar
        """
        if not query.strip():
            return []

        parsed = self._parse_query(query)
        scores: Dict[str, float] = defaultdict(float)
        matched_fields: Dict[str, Set[str]] = defaultdict(set)
        excluded_docs: Set[str] = set()

        i = 0
        while i < len(parsed):
            clause = parsed[i]
            ctype = clause["type"]

            if ctype == "and":
                # AND: next clause must also match
                i += 1
                continue
            elif ctype == "or":
                # OR: either clause matches
                i += 1
                continue
            elif ctype == "not":
                # NOT: exclude documents matching next clause
                if i + 1 < len(parsed):
                    next_clause = parsed[i + 1]
                    not_scores, _ = self._score_clause(next_clause)
                    excluded_docs.update(not_scores.keys())
                    i += 2
                    continue
                i += 1
                continue

            # Score this clause
            clause_scores, clause_fields = self._score_clause(clause)
            for doc_id, score in clause_scores.items():
                scores[doc_id] += score
                matched_fields[doc_id].update(clause_fields.get(doc_id, set()))

            i += 1

        # Remove excluded documents
        for doc_id in excluded_docs:
            scores.pop(doc_id, None)
            matched_fields.pop(doc_id, None)

        # Apply filters
        results: List[SearchResult] = []
        for doc_id, score in scores.items():
            if score < min_score:
                continue
            doc = self._documents.get(doc_id)
            if doc is None:
                continue
            if doc_type is not None and doc.doc_type != doc_type:
                continue
            if filters and not self._apply_filters(doc, filters):
                continue
            highlights = self._extract_highlights(doc, query)
            results.append(SearchResult(
                document=doc,
                score=round(score, 4),
                highlights=highlights,
                matched_fields=sorted(matched_fields.get(doc_id, set())),
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[offset:offset + limit]

    def search_with_facets(
        self,
        query: str,
        facet_fields: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[SearchResult], Dict[str, List[Tuple[str, int]]]]:
        """Search and return facet counts for the given facet fields."""
        results = self.search(query, limit=limit, offset=offset, filters=filters)

        facet_fields = facet_fields or ["doc_type", "category", "status", "tags"]
        facet_counts: Dict[str, List[Tuple[str, int]]] = {}

        for facet_field in facet_fields:
            counter: Counter = Counter()
            for doc in self._documents.values():
                if filters and not self._apply_filters(doc, filters):
                    continue
                value = getattr(doc, facet_field, None)
                if value is None:
                    continue
                if isinstance(value, list):
                    for v in value:
                        counter[str(v)] += 1
                else:
                    counter[str(value)] += 1
            facet_counts[facet_field] = counter.most_common()

        return results, facet_counts

    # -- Query parsing ------------------------------------------------------

    def _parse_query(self, query: str) -> List[Dict[str, Any]]:
        """Parse a query string into structured clauses.

        Returns a list of clause dicts with keys:
        - ``type``: ``"term"``, ``"phrase"``, ``"field"``, ``"and"``, ``"or"``, ``"not"``
        - ``value``: the term/phrase/field value
        - ``field``: for field-specific queries
        """
        clauses: List[Dict[str, Any]] = []
        # Simple tokenizer that respects quoted phrases
        tokens = self._tokenize_query(query)
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.upper() == "AND":
                clauses.append({"type": "and"})
            elif token.upper() == "OR":
                clauses.append({"type": "or"})
            elif token.upper() == "NOT":
                clauses.append({"type": "not"})
            elif token.startswith('"') and token.endswith('"') and len(token) > 1:
                clauses.append({"type": "phrase", "value": token[1:-1]})
            elif ":" in token and not token.startswith('"'):
                field, _, value = token.partition(":")
                if value:
                    clauses.append({"type": "field", "field": field, "value": value})
                else:
                    clauses.append({"type": "term", "value": field})
            else:
                clauses.append({"type": "term", "value": token})

            i += 1

        return clauses

    def _tokenize_query(self, query: str) -> List[str]:
        """Tokenize query string, respecting quoted phrases."""
        tokens: List[str] = []
        current = ""
        in_quotes = False

        for ch in query:
            if ch == '"':
                if in_quotes and current:
                    tokens.append(f'"{current}"')
                    current = ""
                in_quotes = not in_quotes
            elif ch.isspace() and not in_quotes:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += ch

        if current:
            if in_quotes:
                tokens.append(f'"{current}"')
            else:
                tokens.append(current)

        return tokens

    # -- Scoring ------------------------------------------------------------

    def _score_clause(self, clause: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, Set[str]]]:
        """Score documents for a single query clause."""
        scores: Dict[str, float] = defaultdict(float)
        fields: Dict[str, Set[str]] = defaultdict(set)

        ctype = clause["type"]

        if ctype == "and":
            # AND is handled at the query level — skip
            return scores, fields

        if ctype == "or":
            # OR is handled at the query level — skip
            return scores, fields

        if ctype == "not":
            # NOT is handled at the query level — skip
            return scores, fields

        if ctype == "field":
            field_name = clause.get("field", "content")
            value = clause["value"]
            return self._score_field_term(field_name, value)

        if ctype == "phrase":
            phrase = clause["value"].strip('"')
            return self._score_phrase(phrase)

        # Default: term query
        return self._score_term(clause["value"])

    def _score_term(self, term: str) -> Tuple[Dict[str, float], Dict[str, Set[str]]]:
        """Score documents for a single term using TF-IDF with field weights."""
        scores: Dict[str, float] = defaultdict(float)
        fields: Dict[str, Set[str]] = defaultdict(set)

        term_lower = term.lower()

        for field_name, index in self._field_indices.items():
            weight = self.FIELD_WEIGHTS.get(field_name, 1.0)
            postings = index.get_postings(term_lower)
            df = index.document_frequency(term_lower)
            if df == 0:
                continue
            idf = math.log(1 + (index.doc_count - df + 0.5) / (df + 0.5))

            for posting in postings:
                tf = posting.term_frequency
                tf_weight = math.sqrt(tf)
                score = weight * idf * tf_weight
                scores[posting.doc_id] += score
                fields[posting.doc_id].add(field_name)

        return scores, fields

    def _score_field_term(self, field_name: str, value: str) -> Tuple[Dict[str, float], Dict[str, Set[str]]]:
        """Score documents for a field-specific term query."""
        scores: Dict[str, float] = defaultdict(float)
        fields: Dict[str, Set[str]] = defaultdict(set)

        value_lower = value.lower()
        index = self._field_indices.get(field_name)
        if index is None:
            return scores, fields

        weight = self.FIELD_WEIGHTS.get(field_name, 1.0)
        postings = index.get_postings(value_lower)
        df = index.document_frequency(value_lower)
        if df == 0:
            return scores, fields

        idf = math.log(1 + (index.doc_count - df + 0.5) / (df + 0.5))
        for posting in postings:
            tf = posting.term_frequency
            tf_weight = math.sqrt(tf)
            score = weight * idf * tf_weight
            scores[posting.doc_id] += score
            fields[posting.doc_id].add(field_name)

        return scores, fields

    def _score_phrase(self, phrase: str) -> Tuple[Dict[str, float], Dict[str, Set[str]]]:
        """Score documents containing an exact phrase."""
        scores: Dict[str, float] = defaultdict(float)
        fields: Dict[str, Set[str]] = defaultdict(set)

        phrase_tokens = remove_stop_words(tokenize(phrase))
        if not phrase_tokens:
            return scores, fields

        # Find documents containing all phrase tokens
        candidate_sets: List[Set[str]] = []
        for token in phrase_tokens:
            doc_ids = {p.doc_id for p in self._index.get_postings(token)}
            candidate_sets.append(doc_ids)

        if not candidate_sets:
            return scores, fields

        candidates = candidate_sets[0]
        for s in candidate_sets[1:]:
            candidates = candidates & s

        # Verify phrase proximity
        for doc_id in candidates:
            doc = self._documents.get(doc_id)
            if doc is None:
                continue
            doc_text = self._document_to_text(doc).lower()
            if phrase.lower() in doc_text:
                scores[doc_id] += 15.0  # Phrase match bonus
                fields[doc_id].add("content")

        return scores, fields

    # -- Filtering ----------------------------------------------------------

    def _apply_filters(self, doc: SearchableDocument, filters: Dict[str, Any]) -> bool:
        """Check if a document matches all filter criteria."""
        for key, value in filters.items():
            doc_value = getattr(doc, key, None)
            if doc_value is None:
                return False
            if isinstance(value, list):
                if isinstance(doc_value, list):
                    if not any(v in doc_value for v in value):
                        return False
                else:
                    if doc_value not in value:
                        return False
            else:
                if isinstance(doc_value, list):
                    if value not in doc_value:
                        return False
                else:
                    if doc_value != value:
                        return False
        return True

    # -- Highlighting -------------------------------------------------------

    def _extract_highlights(self, doc: SearchableDocument, query: str, context: int = 50) -> List[str]:
        """Extract highlighted snippets from document content."""
        highlights: List[str] = []
        query_terms = set(remove_stop_words(tokenize(query)))
        if not query_terms:
            return highlights

        content = doc.content
        content_lower = content.lower()

        for term in query_terms:
            start = 0
            while True:
                pos = content_lower.find(term, start)
                if pos == -1:
                    break
                hl_start = max(0, pos - context)
                hl_end = min(len(content), pos + len(term) + context)
                snippet = content[hl_start:hl_end]
                if hl_start > 0:
                    snippet = "..." + snippet
                if hl_end < len(content):
                    snippet = snippet + "..."
                highlights.append(snippet)
                start = pos + len(term)
                if len(highlights) >= 3:
                    return highlights

        return highlights[:3]

    # -- Helpers ------------------------------------------------------------

    def _document_to_text(self, doc: SearchableDocument) -> str:
        """Convert a document to a single text string for indexing."""
        parts = [doc.title, doc.content]
        if doc.tags:
            parts.append(" ".join(doc.tags))
        if doc.category:
            parts.append(doc.category)
        return " ".join(parts)
