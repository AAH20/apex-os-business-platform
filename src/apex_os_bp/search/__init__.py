"""APEX-OS Business Platform — Search System.

Provides full-text search with inverted index and autocomplete with prefix matching.
"""

from .index import InvertedIndex, tokenize
from .autocomplete import Autocomplete

__all__ = ["InvertedIndex", "Autocomplete", "tokenize"]
