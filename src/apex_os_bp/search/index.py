import re
from collections import defaultdict
from typing import Dict, List, Set

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class InvertedIndex:
    def __init__(self):
        self._index: Dict[str, Set[int]] = defaultdict(set)
        self._docs: Dict[int, str] = {}

    def add(self, doc_id: int, text: str) -> None:
        self._docs[doc_id] = text
        for term in set(tokenize(text)):
            self._index[term].add(doc_id)

    def search(self, query: str) -> List[int]:
        terms = tokenize(query)
        if not terms:
            return []
        result = None
        for term in terms:
            docs = self._index.get(term, set())
            if result is None:
                result = docs.copy()
            else:
                result &= docs
            if not result:
                return []
        return sorted(result) if result else []

    def get(self, doc_id: int) -> str:
        return self._docs.get(doc_id, "")

    def __len__(self) -> int:
        return len(self._docs)
