"""Sentiment analysis using lexicon-based approach with negation handling."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class SentimentLabel(str, Enum):
    """Sentiment classification labels."""

    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    SLIGHTLY_NEGATIVE = "slightly_negative"
    NEUTRAL = "neutral"
    SLIGHTLY_POSITIVE = "slightly_positive"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


# Positive sentiment lexicon with weights
POSITIVE_WORDS: Dict[str, float] = {
    "good": 1.0, "great": 2.0, "excellent": 3.0, "amazing": 3.0,
    "wonderful": 3.0, "fantastic": 3.0, "awesome": 3.0, "brilliant": 2.5,
    "outstanding": 3.0, "superb": 3.0, "perfect": 3.0, "love": 2.5,
    "like": 1.0, "happy": 2.0, "joy": 2.5, "pleased": 1.5,
    "satisfied": 1.5, "delighted": 2.5, "excited": 2.0, "glad": 1.5,
    "beautiful": 2.0, "best": 2.5, "better": 1.5, "positive": 1.5,
    "success": 2.0, "successful": 2.0, "win": 2.0, "winning": 2.0,
    "recommend": 1.5, "recommended": 1.5, "impressive": 2.0,
    "remarkable": 2.0, "exceptional": 2.5, "magnificent": 3.0,
    "marvelous": 2.5, "splendid": 2.5, "terrific": 2.5, "fabulous": 2.5,
    "incredible": 2.5, "extraordinary": 2.5, "phenomenal": 3.0,
    "thrilled": 2.5, "grateful": 2.0, "thankful": 2.0, "blessed": 2.0,
    "fortunate": 1.5, "lucky": 1.5, "hopeful": 1.5, "optimistic": 1.5,
    "confident": 1.5, "proud": 2.0, "accomplished": 2.0, "effective": 1.5,
    "efficient": 1.5, "reliable": 1.5, "trustworthy": 2.0, "honest": 1.5,
    "helpful": 1.5, "useful": 1.0, "valuable": 1.5, "beneficial": 1.5,
    "productive": 1.5, "innovative": 2.0, "creative": 1.5, "elegant": 1.5,
    "smooth": 1.0, "easy": 1.0, "comfortable": 1.5, "pleasant": 1.5,
    "enjoyable": 2.0, "fun": 1.5, "entertaining": 1.5, "interesting": 1.0,
    "fascinating": 2.0, "inspiring": 2.0, "motivating": 1.5, "uplifting": 2.0,
    "peaceful": 1.5, "calm": 1.0, "relaxing": 1.5, "safe": 1.0,
    "secure": 1.0, "strong": 1.0, "powerful": 1.5, "robust": 1.5,
    "solid": 1.0, "stable": 1.0, "consistent": 1.0, "accurate": 1.0,
    "precise": 1.0, "clear": 1.0, "simple": 1.0, "fast": 1.0,
    "quick": 1.0, "affordable": 1.5, "reasonable": 1.0, "fair": 1.0,
    "generous": 1.5, "kind": 1.5, "friendly": 1.5, "warm": 1.0,
    "welcoming": 1.5, "charming": 1.5, "graceful": 1.5, "refined": 1.5,
}

# Negative sentiment lexicon with weights
NEGATIVE_WORDS: Dict[str, float] = {
    "bad": -1.0, "terrible": -3.0, "awful": -3.0, "horrible": -3.0,
    "dreadful": -3.0, "atrocious": -3.0, "abysmal": -3.0, "appalling": -3.0,
    "poor": -1.5, "worst": -3.0, "worse": -2.0, "negative": -1.5,
    "hate": -2.5, "dislike": -1.0, "angry": -2.0, "furious": -3.0,
    "sad": -2.0, "unhappy": -2.0, "disappointed": -2.0, "disappointing": -2.0,
    "frustrated": -2.0, "frustrating": -2.0, "annoyed": -1.5, "annoying": -1.5,
    "boring": -1.5, "bored": -1.5, "dull": -1.5, "tedious": -2.0,
    "ugly": -2.0, "unpleasant": -1.5, "uncomfortable": -1.5, "difficult": -1.0,
    "hard": -0.5, "complicated": -1.0, "confusing": -1.5, "confused": -1.5,
    "fail": -2.0, "failure": -2.5, "lose": -2.0, "loss": -2.0,
    "wrong": -1.5, "error": -1.5, "mistake": -1.5, "problem": -1.5,
    "issue": -1.0, "trouble": -1.5, "difficulty": -1.0, "challenge": -0.5,
    "broken": -2.0, "damage": -2.0, "damaged": -2.0, "defect": -2.0,
    "defective": -2.0, "faulty": -2.0, "useless": -2.5, "worthless": -3.0,
    "waste": -2.0, "wasted": -2.0, "expensive": -1.0, "overpriced": -2.0,
    "slow": -1.0, "delayed": -1.5, "delay": -1.5, "late": -1.0,
    "rude": -2.0, "unprofessional": -2.0, "incompetent": -2.5, "negligent": -2.5,
    "careless": -2.0, "irresponsible": -2.0, "unreliable": -2.0, "untrustworthy": -2.5,
    "dishonest": -2.5, "corrupt": -3.0, "fraud": -3.0, "scam": -3.0,
    "threat": -2.0, "dangerous": -2.0, "unsafe": -2.0, "risky": -1.5,
    "weak": -1.0, "fragile": -1.0, "unstable": -1.5, "inconsistent": -1.0,
    "inaccurate": -1.5, "unclear": -1.0, "complex": -1.0, "complicated": -1.5,
    "noisy": -1.0, "dirty": -1.5, "messy": -1.0, "disorganized": -1.5,
    "painful": -2.0, "suffering": -2.5, "hurt": -2.0, "harmful": -2.0,
    "toxic": -2.5, "polluted": -2.0, "dangerous": -2.0, "deadly": -3.0,
    "devastating": -3.0, "catastrophic": -3.0, "disastrous": -3.0, "tragic": -2.5,
    "pathetic": -2.5, "miserable": -2.5, "depressing": -2.5, "depressed": -2.5,
    "anxious": -1.5, "worried": -1.5, "stressful": -2.0, "stress": -1.5,
    "overwhelmed": -2.0, "exhausted": -2.0, "tired": -1.0, "sick": -1.5,
}

# Negation words that flip sentiment
NEGATION_WORDS = frozenset({
    "not", "no", "never", "neither", "nor", "none", "nobody", "nothing",
    "nowhere", "hardly", "scarcely", "barely", "don't", "doesn't", "didn't",
    "won't", "wouldn't", "shouldn't", "couldn't", "can't", "cannot", "isn't",
    "aren't", "wasn't", "weren't", "hasn't", "haven't", "hadn't", "mustn't",
    "needn't", "daren't", "oughtn't", "mightn't", "shan't", "without",
    "lack", "lacking", "fails", "failed", "failing",
})

# Intensifiers that amplify sentiment
INTENSIFIERS: Dict[str, float] = {
    "very": 1.5, "extremely": 2.0, "incredibly": 2.0, "absolutely": 2.0,
    "completely": 1.5, "totally": 1.5, "utterly": 2.0, "highly": 1.5,
    "really": 1.5, "quite": 1.3, "rather": 1.2, "pretty": 1.2,
    "fairly": 1.1, "somewhat": 0.8, "slightly": 0.6, "barely": 0.5,
    "hardly": 0.5, "exceptionally": 2.0, "remarkably": 1.8,
    "extraordinarily": 2.0, "tremendously": 2.0, "immensely": 2.0,
    "deeply": 1.5, "strongly": 1.5, "undoubtedly": 1.8, "truly": 1.5,
    "genuinely": 1.5, "sincerely": 1.3, "seriously": 1.5, "severely": 1.8,
}

# Diminishers that reduce sentiment
DIMINISHERS: Dict[str, float] = {
    "slightly": 0.5, "somewhat": 0.6, "a bit": 0.5, "kind of": 0.6,
    "sort of": 0.6, "barely": 0.4, "hardly": 0.4, "scarcely": 0.4,
    "marginally": 0.5, "partially": 0.7, "mildly": 0.6,
}

_WORD_RE = re.compile(r"[a-zA-Z']+")


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""

    score: float = 0.0
    comparative: float = 0.0
    label: SentimentLabel = SentimentLabel.NEUTRAL
    positive_words: List[str] = field(default_factory=list)
    negative_words: List[str] = field(default_factory=list)
    word_count: int = 0
    confidence: float = 0.0


class SentimentAnalyzer:
    """Lexicon-based sentiment analyzer with negation and intensifier support."""

    def __init__(self) -> None:
        self.positive = POSITIVE_WORDS
        self.negative = NEGATIVE_WORDS
        self.negations = NEGATION_WORDS
        self.intensifiers = INTENSIFIERS
        self.diminishers = DIMINISHERS

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        if not text:
            return []
        return [m.group().lower() for m in _WORD_RE.finditer(text)]

    def _detect_negation(self, tokens: List[str], pos: int, window: int = 3) -> bool:
        """Check if there's a negation word within the window before position."""
        start = max(0, pos - window)
        for i in range(start, pos):
            if tokens[i] in self.negations:
                return True
        return False

    def _get_intensifier(self, tokens: List[str], pos: int, window: int = 2) -> float:
        """Get intensifier multiplier from preceding words."""
        start = max(0, pos - window)
        multiplier = 1.0
        for i in range(start, pos):
            if tokens[i] in self.intensifiers:
                multiplier *= self.intensifiers[tokens[i]]
            elif tokens[i] in self.diminishers:
                multiplier *= self.diminishers[tokens[i]]
        return multiplier

    def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment of the given text.

        Returns a SentimentResult with a score between -1 and 1,
        a comparative score, and a sentiment label.
        """
        if not text or not text.strip():
            return SentimentResult()

        tokens = self._tokenize(text)
        if not tokens:
            return SentimentResult()

        positive_found: List[str] = []
        negative_found: List[str] = []
        total_score = 0.0

        for i, token in enumerate(tokens):
            score = 0.0
            if token in self.positive:
                score = self.positive[token]
                positive_found.append(token)
            elif token in self.negative:
                score = self.negative[token]
                negative_found.append(token)
            else:
                continue

            # Apply intensifier/diminisher
            intensifier = self._get_intensifier(tokens, i)
            score *= intensifier

            # Apply negation (flip the sign)
            if self._detect_negation(tokens, i):
                score *= -0.75  # Partial flip (negation doesn't fully reverse)

            total_score += score

        # Normalize score to [-1, 1]
        word_count = len(tokens)
        comparative = total_score / max(word_count, 1)

        # Clamp to [-1, 1]
        normalized_score = max(-1.0, min(1.0, comparative * 5))

        # Determine label
        label = self._score_to_label(normalized_score)

        # Confidence based on number of sentiment words found
        sentiment_word_count = len(positive_found) + len(negative_found)
        confidence = min(1.0, sentiment_word_count / max(word_count * 0.1, 1))

        return SentimentResult(
            score=round(normalized_score, 4),
            comparative=round(comparative, 4),
            label=label,
            positive_words=positive_found,
            negative_words=negative_found,
            word_count=word_count,
            confidence=round(confidence, 4),
        )

    def _score_to_label(self, score: float) -> SentimentLabel:
        """Convert a normalized score to a sentiment label."""
        if score <= -0.6:
            return SentimentLabel.VERY_NEGATIVE
        elif score <= -0.2:
            return SentimentLabel.NEGATIVE
        elif score < -0.05:
            return SentimentLabel.SLIGHTLY_NEGATIVE
        elif score < 0.05:
            return SentimentLabel.NEUTRAL
        elif score < 0.2:
            return SentimentLabel.SLIGHTLY_POSITIVE
        elif score < 0.6:
            return SentimentLabel.POSITIVE
        else:
            return SentimentLabel.VERY_POSITIVE

    def is_positive(self, text: str, threshold: float = 0.05) -> bool:
        """Check if text sentiment is positive (above threshold)."""
        return self.analyze(text).score > threshold

    def is_negative(self, text: str, threshold: float = -0.05) -> bool:
        """Check if text sentiment is negative (below threshold)."""
        return self.analyze(text).score < threshold

    def batch_analyze(self, texts: List[str]) -> List[SentimentResult]:
        """Analyze sentiment for a batch of texts."""
        return [self.analyze(t) for t in texts]
