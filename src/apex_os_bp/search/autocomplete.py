"""Autocomplete with prefix matching."""
from typing import List, Set

from .index import tokenize


class Autocomplete:
    def __init__(self):
        self._terms: Set[str] = set()

    def add(self, text: str) -> None:
        self._terms.update(tokenize(text))

    def complete(self, prefix: str, limit: int = 10) -> List[str]:
        prefix = prefix.lower()
        matches = [t for t in self._terms if t.startswith(prefix)]
        return sorted(matches)[:limit]

    def __len__(self) -> int:
        return len(self._terms)


class AutocompleteEngine:
    """Autocomplete engine with prefix matching."""
    def __init__(self, engine=None):
        self._autocomplete = Autocomplete()

    def add_document(self, document):
        self._autocomplete.add(document.title)
        self._autocomplete.add(document.content)

    def complete(self, prefix, limit=10):
        return self._autocomplete.complete(prefix, limit)

    def clear(self):
        self._autocomplete = Autocomplete()

    def __len__(self):
        return len(self._autocomplete)
