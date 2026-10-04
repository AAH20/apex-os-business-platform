"""Text generation using Markov chains and template-based approaches."""

from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional


# Common English words for template-based generation
_COMMON_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her",
    "she", "or", "an", "will", "my", "one", "all", "would", "there",
    "their", "what", "so", "up", "out", "if", "about", "who", "get",
    "which", "go", "me", "when", "make", "can", "like", "time", "no",
    "just", "him", "know", "take", "people", "into", "year", "your",
    "good", "some", "could", "them", "see", "other", "than", "then",
    "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first",
    "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us",
}

# Sentence templates for different purposes
_TEMPLATES = {
    "informative": [
        "The {noun} is {adj} and {adj}.",
        "A {noun} can be {adj} when it {verb}.",
        "Many {noun_plural} are {adj} in {place}.",
        "The {noun} has been {verb} for {time}.",
        "It is {adj} to {verb} a {noun}.",
        "The {noun} will {verb} in {place}.",
        "Every {noun} needs to {verb}.",
        "The {noun} was {adj} because it {verb}.",
    ],
    "descriptive": [
        "The {adj} {noun} {verb} through the {place}.",
        "A {adj} {noun} {verb} in the {place}.",
        "The {noun} looks {adj} and {adj}.",
        "There is a {adj} {noun} in the {place}.",
        "The {noun} feels {adj} when it {verb}.",
    ],
    "narrative": [
        "Once upon a time, a {noun} {verb} in {place}.",
        "The {noun} decided to {verb} because it was {adj}.",
        "After {time}, the {noun} finally {verb}.",
        "In {place}, the {noun} {verb} every day.",
        "The {noun} was {adj} when it {verb}.",
    ],
    "persuasive": [
        "You should {verb} because it is {adj}.",
        "The {noun} is the best way to {verb}.",
        "Everyone needs a {noun} to {verb}.",
        "It is {adj} to {verb} a {noun}.",
        "The {noun} will make you {adj}.",
    ],
}

# Word banks for template filling
_WORD_BANK = {
    "noun": [
        "system", "process", "method", "approach", "strategy", "solution",
        "product", "service", "tool", "technique", "framework", "model",
        "platform", "application", "device", "component", "feature",
        "function", "operation", "activity", "task", "project", "program",
        "initiative", "effort", "venture", "enterprise", "endeavor",
        "algorithm", "protocol", "interface", "architecture", "design",
        "structure", "mechanism", "procedure", "workflow", "pipeline",
    ],
    "noun_plural": [
        "systems", "processes", "methods", "approaches", "strategies",
        "solutions", "products", "services", "tools", "techniques",
        "frameworks", "models", "platforms", "applications", "devices",
        "components", "features", "functions", "operations", "activities",
        "tasks", "projects", "programs", "initiatives", "efforts",
        "ventures", "enterprises", "endeavors", "algorithms", "protocols",
        "interfaces", "architectures", "designs", "structures",
        "mechanisms", "procedures", "workflows", "pipelines",
    ],
    "verb": [
        "work", "function", "operate", "perform", "execute", "run",
        "process", "analyze", "evaluate", "assess", "determine",
        "identify", "recognize", "detect", "measure", "calculate",
        "compute", "generate", "produce", "create", "develop",
        "implement", "deploy", "configure", "optimize", "enhance",
        "improve", "upgrade", "update", "modify", "adjust", "adapt",
        "transform", "convert", "translate", "interpret", "understand",
        "learn", "train", "predict", "classify", "categorize", "organize",
    ],
    "adj": [
        "efficient", "effective", "reliable", "robust", "scalable",
        "flexible", "adaptable", "innovative", "advanced", "sophisticated",
        "comprehensive", "integrated", "automated", "intelligent",
        "powerful", "versatile", "modular", "dynamic", "responsive",
        "accurate", "precise", "consistent", "stable", "secure",
        "fast", "quick", "rapid", "smooth", "seamless", "intuitive",
        "user-friendly", "cost-effective", "high-performance", "state-of-the-art",
        "cutting-edge", "next-generation", "enterprise-grade", "production-ready",
    ],
    "place": [
        "the cloud", "the enterprise", "the organization", "the network",
        "the platform", "the system", "the environment", "the infrastructure",
        "the data center", "the server", "the database", "the application",
        "the framework", "the architecture", "the ecosystem", "the market",
        "the industry", "the domain", "the field", "the sector",
    ],
    "time": [
        "a moment", "a while", "some time", "a period", "a duration",
        "a long time", "a short time", "an instant", "a minute", "an hour",
        "a day", "a week", "a month", "a year", "a decade", "a century",
    ],
}

# Markov chain training data (small corpus for demonstration)
_MARKOV_CORPUS = [
    "the quick brown fox jumps over the lazy dog",
    "a journey of a thousand miles begins with a single step",
    "to be or not to be that is the question",
    "all that glitters is not gold",
    "the early bird catches the worm",
    "actions speak louder than words",
    "where there is a will there is a way",
    "the pen is mightier than the sword",
    "when in rome do as the romans do",
    "the cat sat on the mat and looked at the rat",
    "practice makes perfect and perfect practice makes perfect",
    "knowledge is power and power is knowledge",
    "time and tide wait for no man",
    "a friend in need is a friend indeed",
    "better late than never but never late is better",
    "every cloud has a silver lining",
    "don't count your chickens before they hatch",
    "the grass is always greener on the other side",
    "you can't have your cake and eat it too",
    "when the going gets tough the tough get going",
]

_WORD_RE = re.compile(r"[a-zA-Z']+")


@dataclass
class GenerationResult:
    """Result of text generation."""

    text: str = ""
    method: str = ""
    seed: Optional[str] = None
    word_count: int = 0
    sentence_count: int = 0


class TextGenerator:
    """Generate text using Markov chains and template-based approaches."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.templates = _TEMPLATES
        self.word_bank = _WORD_BANK
        self.markov_chains: Dict[str, List[str]] = defaultdict(list)
        self._train_markov(_MARKOV_CORPUS)

    def _train_markov(self, corpus: List[str]) -> None:
        """Train Markov chains from a corpus of sentences."""
        for sentence in corpus:
            words = [w.lower() for w in _WORD_RE.findall(sentence)]
            if len(words) < 2:
                continue
            for i in range(len(words) - 1):
                self.markov_chains[words[i]].append(words[i + 1])

    def _get_random_word(self, word_type: str) -> str:
        """Get a random word from the word bank."""
        words = self.word_bank.get(word_type, ["thing"])
        return self.rng.choice(words)

    def _fill_template(self, template: str) -> str:
        """Fill a template with random words."""
        result = template
        # Find all placeholders
        placeholders = re.findall(r"\{(\w+)\}", template)
        for ph in placeholders:
            word = self._get_random_word(ph)
            result = result.replace("{" + ph + "}", word, 1)
        return result

    def generate_from_template(
        self, style: str = "informative", count: int = 1
    ) -> List[str]:
        """Generate sentences using templates."""
        templates = self.templates.get(style, self.templates["informative"])
        results = []
        for _ in range(count):
            template = self.rng.choice(templates)
            sentence = self._fill_template(template)
            # Capitalize first letter
            sentence = sentence[0].upper() + sentence[1:]
            results.append(sentence)
        return results

    def generate_markov(
        self, seed: Optional[str] = None, length: int = 20
    ) -> str:
        """Generate text using Markov chains."""
        if not self.markov_chains:
            return ""

        if seed and seed.lower() in self.markov_chains:
            current = seed.lower()
        else:
            # Pick a random starting word
            current = self.rng.choice(list(self.markov_chains.keys()))

        words = [current]
        for _ in range(length - 1):
            next_words = self.markov_chains.get(current, [])
            if not next_words:
                break
            current = self.rng.choice(next_words)
            words.append(current)

        # Capitalize first word and add period
        if words:
            words[0] = words[0][0].upper() + words[0][1:]
        text = " ".join(words)
        if not text.endswith((".", "!", "?")):
            text += "."
        return text

    def generate_paragraph(
        self,
        topic: Optional[str] = None,
        sentences: int = 3,
        style: str = "informative",
    ) -> str:
        """Generate a paragraph of text."""
        if topic and topic.lower() in self.markov_chains:
            # Use Markov chain with topic as seed
            first_sentence = self.generate_markov(seed=topic, length=sentences * 5)
            return first_sentence
        else:
            # Use template-based generation
            template_sentences = self.generate_from_template(style=style, count=sentences)
            return " ".join(template_sentences)

    def generate_bullet_points(
        self, count: int = 5, style: str = "informative"
    ) -> List[str]:
        """Generate bullet point items."""
        sentences = self.generate_from_template(style=style, count=count)
        return [f"• {s}" for s in sentences]

    def generate_summary(
        self, text: str, max_sentences: int = 3
    ) -> str:
        """Generate a simple extractive summary.

        Selects the most important sentences based on word frequency.
        """
        if not text:
            return ""

        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= max_sentences:
            return " ".join(sentences) + "."

        # Score sentences by word frequency
        word_freq = defaultdict(int)
        for sentence in sentences:
            for word in _WORD_RE.findall(sentence.lower()):
                if word not in _COMMON_WORDS:
                    word_freq[word] += 1

        sentence_scores = []
        for i, sentence in enumerate(sentences):
            words = _WORD_RE.findall(sentence.lower())
            score = sum(word_freq[w] for w in words) / max(len(words), 1)
            sentence_scores.append((i, score))

        # Sort by score and take top N
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_indices = sorted([idx for idx, _ in sentence_scores[:max_sentences]])

        summary_sentences = [sentences[i] for i in top_indices]
        return " ".join(summary_sentences) + "."

    def generate(
        self,
        method: str = "template",
        **kwargs,
    ) -> GenerationResult:
        """Generate text using the specified method.

        Methods:
            - 'template': Generate from templates
            - 'markov': Generate using Markov chains
            - 'paragraph': Generate a paragraph
            - 'summary': Generate a summary of input text
        """
        if method == "template":
            style = kwargs.get("style", "informative")
            count = kwargs.get("count", 1)
            sentences = self.generate_from_template(style=style, count=count)
            text = " ".join(sentences)
            return GenerationResult(
                text=text,
                method="template",
                word_count=len(_WORD_RE.findall(text)),
                sentence_count=len(sentences),
            )

        elif method == "markov":
            seed = kwargs.get("seed")
            length = kwargs.get("length", 20)
            text = self.generate_markov(seed=seed, length=length)
            return GenerationResult(
                text=text,
                method="markov",
                seed=seed,
                word_count=len(_WORD_RE.findall(text)),
                sentence_count=1,
            )

        elif method == "paragraph":
            topic = kwargs.get("topic")
            sentences = kwargs.get("sentences", 3)
            style = kwargs.get("style", "informative")
            text = self.generate_paragraph(
                topic=topic, sentences=sentences, style=style
            )
            return GenerationResult(
                text=text,
                method="paragraph",
                seed=topic,
                word_count=len(_WORD_RE.findall(text)),
                sentence_count=sentences,
            )

        elif method == "summary":
            text = kwargs.get("text", "")
            max_sentences = kwargs.get("max_sentences", 3)
            summary = self.generate_summary(text, max_sentences=max_sentences)
            return GenerationResult(
                text=summary,
                method="summary",
                word_count=len(_WORD_RE.findall(summary)),
                sentence_count=max_sentences,
            )

        else:
            return GenerationResult(
                text="",
                method="unknown",
                word_count=0,
                sentence_count=0,
            )

    def train(self, corpus: List[str]) -> None:
        """Train the generator on a new corpus."""
        self._train_markov(corpus)

    def add_template(self, style: str, template: str) -> None:
        """Add a custom template."""
        if style not in self.templates:
            self.templates[style] = []
        self.templates[style].append(template)

    def add_words(self, word_type: str, words: List[str]) -> None:
        """Add words to the word bank."""
        if word_type not in self.word_bank:
            self.word_bank[word_type] = []
        self.word_bank[word_type].extend(words)
