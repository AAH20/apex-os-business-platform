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


# Alias for backward compatibility
AutocompleteEngine = Autocomplete
