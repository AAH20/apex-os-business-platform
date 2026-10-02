"""NLP module for APEX-OS Business Platform.

Provides text analysis, sentiment analysis, entity extraction,
language translation, and text generation capabilities.
"""

from .text_analysis import TextAnalyzer
from .sentiment import SentimentAnalyzer
from .entities import EntityExtractor
from .translation import Translator
from .generation import TextGenerator

__all__ = [
    "TextAnalyzer",
    "SentimentAnalyzer",
    "EntityExtractor",
    "Translator",
    "TextGenerator",
]
