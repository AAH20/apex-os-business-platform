#!/usr/bin/env python3
"""NLP demos: sentiment, entities, classification, generation, translation."""

import re
import random
from collections import Counter

# ── 1. Sentiment Analysis ────────────────────────────────────────────────────

POSITIVE = {"good", "great", "excellent", "amazing", "love", "best", "fantastic", "happy"}
NEGATIVE = {"bad", "terrible", "awful", "hate", "worst", "horrible", "sad", "angry"}

def analyze_sentiment(text: str) -> dict:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    pos = len(words & POSITIVE)
    neg = len(words & NEGATIVE)
    score = pos - neg
    label = "positive" if score > 0 else "negative" if score < 0 else "neutral"
    return {"text": text, "label": label, "score": score, "pos_words": pos, "neg_words": neg}

# ── 2. Entity Extraction ─────────────────────────────────────────────────────

def extract_entities(text: str) -> dict:
    emails = re.findall(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b", text)
    urls = re.findall(r"https?://\S+|www\.\S+", text)
    phones = re.findall(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", text)
    capitalized = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
    return {"emails": emails, "urls": urls, "phones": phones, "proper_nouns": capitalized}

# ── 3. Text Classification ───────────────────────────────────────────────────

CATEGORIES = {
    "technology": {"software", "hardware", "computer", "app", "code", "data", "ai", "cloud"},
    "sports": {"game", "team", "player", "score", "match", "league", "goal"},
    "finance": {"stock", "market", "price", "invest", "bank", "money", "trade", "fund"},
    "health": {"doctor", "patient", "disease", "treatment", "drug", "health", "medical"},
}

def classify_text(text: str) -> dict:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    scores = {cat: len(words & keywords) for cat, keywords in CATEGORIES.items()}
    best = max(scores, key=scores.get)
    label = best if scores[best] > 0 else "unknown"
    return {"text": text, "category": label, "scores": scores}

# ── 4. Text Generation ───────────────────────────────────────────────────────

def generate_text(seed: str, length: int = 30) -> str:
    words = seed.split()
    if len(words) < 2:
        return seed
    bigrams = list(zip(words, words[1:]))
    model = {}
    for a, b in bigrams:
        model.setdefault(a, []).append(b)
    current = random.choice(words)
    output = [current]
    for _ in range(length - 1):
        choices = model.get(current)
        if not choices:
            current = random.choice(words)
        else:
            current = random.choice(choices)
        output.append(current)
    return " ".join(output)

# ── 5. Translation ───────────────────────────────────────────────────────────

DICT = {
    "hello": "hola", "world": "mundo", "good": "bueno", "morning": "mañana",
    "thank": "gracias", "you": "tú", "please": "por favor", "yes": "sí", "no": "no",
}

def translate(text: str, src: str = "en", tgt: str = "es") -> str:
    words = re.findall(r"\b\w+\b", text.lower())
    translated = [DICT.get(w, f"[{w}]") for w in words]
    return " ".join(translated)

# ── Demo runner ──────────────────────────────────────────────────────────────

def main():
    sample = "The new software is amazing and the team loves it! Contact john@example.com."
    print("=" * 60)
    print("1. SENTIMENT ANALYSIS")
    print(f"   {analyze_sentiment(sample)}")

    print("\n2. ENTITY EXTRACTION")
    print(f"   {extract_entities(sample + ' Visit https://example.com or call 555-123-4567')}")

    print("\n3. TEXT CLASSIFICATION")
    print(f"   {classify_text('The stock market invest trade fund price went up today.')}")

    print("\n4. TEXT GENERATION")
    random.seed(42)
    print(f"   {generate_text('the quick brown fox jumps over the lazy dog', 15)}")

    print("\n5. TRANSLATION (en→es)")
    print(f"   {translate('hello world good morning thank you please')}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
