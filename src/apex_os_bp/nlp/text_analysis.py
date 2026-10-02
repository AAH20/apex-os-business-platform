"""Text analysis: tokenization, word frequency, readability metrics."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Common English stop words
STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "ought", "used", "it", "its", "this", "that", "these", "those",
    "i", "you", "he", "she", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "our", "their", "mine", "yours", "ours",
    "theirs", "what", "which", "who", "whom", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "just", "because", "as", "until", "while",
    "about", "between", "through", "during", "before", "after", "above",
    "below", "up", "down", "out", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "also",
})

_WORD_RE = re.compile(r"[a-zA-Z']+")
_SENTENCE_RE = re.compile(r"[.!?]+")


@dataclass
class TextStatistics:
    """Aggregate statistics for a text."""

    char_count: int = 0
    char_count_no_spaces: int = 0
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    avg_word_length: float = 0.0
    avg_sentence_length: float = 0.0
    unique_word_count: int = 0
    lexical_diversity: float = 0.0
    reading_time_seconds: float = 0.0
    speaking_time_seconds: float = 0.0


@dataclass
class ReadabilityScores:
    """Readability metrics for a text."""

    flesch_reading_ease: float = 0.0
    flesch_kincaid_grade: float = 0.0
    gunning_fog_index: float = 0.0
    smog_index: float = 0.0
    coleman_liau_index: float = 0.0
    automated_readability_index: float = 0.0


@dataclass
class AnalysisResult:
    """Complete analysis result."""

    statistics: TextStatistics = field(default_factory=TextStatistics)
    readability: ReadabilityScores = field(default_factory=ReadabilityScores)
    word_frequency: List[Tuple[str, int]] = field(default_factory=list)
    top_words: List[Tuple[str, int]] = field(default_factory=list)
    bigrams: List[Tuple[str, str]] = field(default_factory=list)
    trigrams: List[Tuple[str, str, str]] = field(default_factory=list)
    language: str = "en"


class TextAnalyzer:
    """Analyze text: tokenization, frequency, readability, n-grams."""

    # Average reading speed in words per minute
    WPM_READING = 200
    # Average speaking speed in words per minute
    WPM_SPEAKING = 130

    def tokenize_words(self, text: str) -> List[str]:
        """Split text into lowercase word tokens."""
        if not text:
            return []
        return [m.group().lower() for m in _WORD_RE.finditer(text)]

    def tokenize_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        if not text:
            return []
        # Split on sentence-ending punctuation, then strip whitespace
        raw = _SENTENCE_RE.split(text)
        return [s.strip() for s in raw if s.strip()]

    def tokenize_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs (separated by blank lines)."""
        if not text:
            return []
        return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    def word_frequency(self, text: str, remove_stopwords: bool = False) -> Counter:
        """Count word frequencies, optionally excluding stop words."""
        words = self.tokenize_words(text)
        if remove_stopwords:
            words = [w for w in words if w not in STOP_WORDS]
        return Counter(words)

    def top_n_words(
        self, text: str, n: int = 10, remove_stopwords: bool = False
    ) -> List[Tuple[str, int]]:
        """Return the top *n* most frequent words."""
        freq = self.word_frequency(text, remove_stopwords=remove_stopwords)
        return freq.most_common(n)

    def extract_ngrams(
        self, text: str, n: int = 2, remove_stopwords: bool = False
    ) -> List[Tuple[str, ...]]:
        """Extract n-grams (bigrams when n=2, trigrams when n=3)."""
        words = self.tokenize_words(text)
        if remove_stopwords:
            words = [w for w in words if w not in STOP_WORDS]
        if len(words) < n:
            return []
        return [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]

    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count for an English word."""
        word = word.lower().strip("'")
        if not word:
            return 0
        if len(word) <= 3:
            return 1
        # Remove silent trailing e
        if word.endswith("e") and not word.endswith("le"):
            word = word[:-1]
        # Count vowel groups
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        for ch in word:
            is_vowel = ch in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        return max(count, 1)

    def _count_complex_words(self, words: List[str]) -> int:
        """Count words with 3+ syllables (used in Gunning Fog)."""
        return sum(1 for w in words if self._count_syllables(w) >= 3)

    def compute_statistics(self, text: str) -> TextStatistics:
        """Compute aggregate text statistics."""
        if not text:
            return TextStatistics()

        words = self.tokenize_words(text)
        sentences = self.tokenize_sentences(text)
        paragraphs = self.tokenize_paragraphs(text)

        word_count = len(words)
        sentence_count = max(len(sentences), 1)
        paragraph_count = max(len(paragraphs), 1)

        total_word_len = sum(len(w) for w in words)
        unique_words = set(words)

        stats = TextStatistics(
            char_count=len(text),
            char_count_no_spaces=len(text.replace(" ", "").replace("\n", "")),
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            avg_word_length=total_word_len / max(word_count, 1),
            avg_sentence_length=word_count / sentence_count,
            unique_word_count=len(unique_words),
            lexical_diversity=len(unique_words) / max(word_count, 1),
            reading_time_seconds=(word_count / self.WPM_READING) * 60,
            speaking_time_seconds=(word_count / self.WPM_SPEAKING) * 60,
        )
        return stats

    def compute_readability(self, text: str) -> ReadabilityScores:
        """Compute readability scores for English text."""
        if not text or not text.strip():
            return ReadabilityScores()

        words = self.tokenize_words(text)
        sentences = self.tokenize_sentences(text)

        word_count = len(words)
        sentence_count = max(len(sentences), 1)

        if word_count == 0:
            return ReadabilityScores()

        total_syllables = sum(self._count_syllables(w) for w in words)
        complex_word_count = self._count_complex_words(words)

        # Flesch Reading Ease
        flesch = (
            206.835
            - 1.015 * (word_count / sentence_count)
            - 84.6 * (total_syllables / word_count)
        )

        # Flesch-Kincaid Grade Level
        fk_grade = (
            0.39 * (word_count / sentence_count)
            + 11.8 * (total_syllables / word_count)
            - 15.59
        )

        # Gunning Fog Index
        fog = 0.4 * (
            (word_count / sentence_count)
            + 100 * (complex_word_count / word_count)
        )

        # SMOG Index
        smog = 1.0430 * math.sqrt(
            complex_word_count * (30 / sentence_count)
        ) + 3.1291

        # Coleman-Liau Index
        char_count = len(text.replace(" ", "").replace("\n", ""))
        l = (char_count / word_count) * 100  # letters per 100 words
        s = (sentence_count / word_count) * 100  # sentences per 100 words
        coleman = 0.0588 * l - 0.296 * s - 15.8

        # Automated Readability Index
        ari = (
            4.71 * (char_count / word_count)
            + 0.5 * (word_count / sentence_count)
            - 21.43
        )

        return ReadabilityScores(
            flesch_reading_ease=round(flesch, 2),
            flesch_kincaid_grade=round(fk_grade, 2),
            gunning_fog_index=round(fog, 2),
            smog_index=round(smog, 2),
            coleman_liau_index=round(coleman, 2),
            automated_readability_index=round(ari, 2),
        )

    def detect_language(self, text: str) -> str:
        """Simple language detection based on common word patterns.

        Returns an ISO 639-1 language code. Defaults to 'en'.
        """
        if not text:
            return "en"

        words = set(self.tokenize_words(text))
        if not words:
            return "en"

        # Language markers: common words per language
        markers: Dict[str, set] = {
            "en": {"the", "is", "and", "of", "to", "in", "a", "that", "it", "for"},
            "es": {"el", "la", "de", "que", "y", "en", "un", "una", "es", "por"},
            "fr": {"le", "la", "de", "et", "les", "des", "en", "un", "une", "est"},
            "de": {"der", "die", "und", "in", "den", "von", "zu", "das", "mit", "sich"},
            "it": {"il", "di", "che", "e", "la", "per", "un", "in", "una", "è"},
            "pt": {"o", "de", "a", "que", "e", "do", "da", "em", "um", "para"},
        }

        best_lang = "en"
        best_score = 0
        for lang, marker_words in markers.items():
            score = len(words & marker_words)
            if score > best_score:
                best_score = score
                best_lang = lang

        return best_lang

    def analyze(self, text: str) -> AnalysisResult:
        """Run full analysis on text and return an AnalysisResult."""
        stats = self.compute_statistics(text)
        readability = self.compute_readability(text)
        top_words = self.top_n_words(text, n=10, remove_stopwords=True)
        bigrams = self.extract_ngrams(text, n=2, remove_stopwords=True)
        trigrams = self.extract_ngrams(text, n=3, remove_stopwords=True)
        language = self.detect_language(text)

        return AnalysisResult(
            statistics=stats,
            readability=readability,
            word_frequency=top_words,
            top_words=top_words,
            bigrams=bigrams,
            trigrams=trigrams,
            language=language,
        )
