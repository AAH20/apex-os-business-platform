"""Deepened NLP: NER, sentiment, classification, translation, QA/RAG."""
from __future__ import annotations
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable
import numpy as np

_TOKEN_RE = re.compile(r"\b\w+\b", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0

# 1. NER


@dataclass
class Entity:
    text: str; label: str; start: int; end: int; confidence: float = 1.0

GAZETTEERS: dict[str, set[str]] = {
    "PERSON": {"alice","bob","carol","dave","eve","frank","grace","heidi"},
    "ORG": {"acme","globex","initech","umbrella","stark","wayne","aperture"},
    "GPE": {"london","paris","tokyo","berlin","madrid","rome","cairo"},
    "PRODUCT": {"iphone","tesla","pixel","galaxy","surface","macbook"},
}
_TITLE_RE = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MONEY_RE = re.compile(r"\$\d+(?:,\d{3})*(?:\.\d+)?|\d+\s?(?:USD|EUR|GBP)")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")


def ner_extract(text: str) -> list[Entity]:
    entities: list[Entity] = []
    lower = text.lower()
    for label, terms in GAZETTEERS.items():
        for term in terms:
            for m in re.finditer(rf"\b{re.escape(term)}\b", lower):
                entities.append(Entity(text[m.start():m.end()], label, m.start(), m.end()))
    for pattern, label in [(
        _TITLE_RE,
        "PERSON"
    ),(_EMAIL_RE,"EMAIL"),(_URL_RE,"URL"),(_MONEY_RE,"MONEY"),(_PHONE_RE,"PHONE")]:
        for m in pattern.finditer(text):
            entities.append(Entity(m.group(), label, m.start(), m.end()))
    entities.sort(key=lambda e: (e.start, -(e.end - e.start)))
    filtered: list[Entity] = []
    for ent in entities:
        if any(ent.start < prev.end and ent.end > prev.start for prev in filtered):
            continue
        filtered.append(ent)
    return filtered

# 2. Sentiment


@dataclass
class SentimentResult:
    label: str; score: float; valence: float; arousal: float
    emotions: dict[str, float] = field(default_factory=dict)

POSITIVE_WORDS = {"excellent","amazing","great","good","love","fantastic","wonderful","happy","joy","delighted",
    "pleased","awesome","brilliant","perfect","best","beautiful","excited","grateful","impressive","outstanding"}
NEGATIVE_WORDS = {"terrible","awful","bad","hate","worst","horrible","disgusting","angry","sad",
    "disappointed","frustrated","annoying","poor","broken","useless","fail","wrong","ugly","painful","regret"}
EMOTION_LEXICON: dict[str, set[str]] = {
    "joy": {"happy","joy","delighted","excited","glad","cheerful"},
    "anger": {"angry","furious","rage","irritated","annoyed"},
    "sadness": {"sad","unhappy","depressed","gloomy","sorrow"},
    "fear": {"afraid","scared","terrified","anxious","worried"},
    "surprise": {"surprised","amazed","astonished","shocked"},
    "disgust": {"disgusted","repulsed","revolted","sickened"},
}
_INTENSIFIERS = {"very":1.5,"extremely":2.0,"incredibly":2.0,"really":1.3}
_NEGATORS = {"not","no","never","neither","nor","hardly","barely"}


def sentiment_analyze(text: str) -> SentimentResult:
    tokens = tokenize(text)
    valence = 0.0; arousal = 0.0; emotions: Counter[str] = Counter()
    for i, tok in enumerate(tokens):
        score = 0.0
        if tok in POSITIVE_WORDS: score = 1.0
        elif tok in NEGATIVE_WORDS: score = -1.0
        if i > 0:
            prev = tokens[i - 1]
            if prev in _INTENSIFIERS: score *= _INTENSIFIERS[prev]
            if prev in _NEGATORS or (i > 1 and tokens[i - 2] in _NEGATORS): score *= -0.8
        valence += score; arousal += abs(score)
        for emotion, words in EMOTION_LEXICON.items():
            if tok in words: emotions[emotion] += 1.0
    max_val = len(tokens) or 1
    valence = np.clip(valence / max_val * 5, -1.0, 1.0)
    arousal = np.clip(arousal / max_val * 5, 0.0, 1.0)
    label = "positive" if valence > 0.15 else "negative" if valence < -0.15 else "neutral"
    return SentimentResult(
        label,
        round(valence,4),
        round(valence,4),
        round(arousal,4),
        {k: v/max_val for k,v in emotions.items()}
    )

# 3. Classification


@dataclass
class ClassificationResult:
    labels: list[str]; probabilities: dict[str, float]

LABEL_KEYWORDS: dict[str, set[str]] = {
    "billing": {"invoice","payment","charge","refund","billing","subscription","price"},
    "technical": {"error","bug","crash","login","api","server","timeout","broken"},
    "shipping": {"delivery","shipping","tracking","package","arrived","courier"},
    "account": {"password","login","account","profile","email","username","2fa"},
    "feature_request": {"feature","suggestion","would be nice","add","improve","enhance"},
    "complaint": {"terrible","worst","awful","disappointed","frustrated","angry"},
    "praise": {"great","excellent","amazing","love","awesome","perfect","best"},
    "urgent": {"urgent","asap","immediately","critical","emergency","blocking"},
}


def classify_text(text: str, threshold: float = 0.15) -> ClassificationResult:
    tokens = set(tokenize(text)); text_lower = text.lower(); probs: dict[str, float] = {}
    for label, keywords in LABEL_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text_lower or kw in tokens)
        score = matches / max(len(keywords), 1)
        if score >= threshold: probs[label] = round(min(score * 2.0, 1.0), 4)
    if not probs: probs["general"] = 1.0
    return ClassificationResult(sorted(probs, key=probs.get, reverse=True), probs)

# 4. Translation


@dataclass
class TranslationResult:
    translated: str; source_lang: str; target_lang: str; confidence: float

_DICT_EN_ES = {
    "hello": "hola", "world": "mundo", "good": "bueno", "morning": "mañana",
    "thank": "gracias", "you": "tú", "the": "el", "a": "un", "is": "es",
    "are": "son", "and": "y", "or": "o", "but": "pero", "not": "no",
    "this": "esto", "that": "eso", "with": "con", "for": "para",
    "have": "tener", "from": "de", "they": "ellos", "we": "nosotros",
    "say": "decir", "she": "ella", "he": "él", "it": "ello",
    "product": "producto", "service": "servicio", "price": "precio",
    "order": "pedido", "customer": "cliente", "company": "empresa",
}
_DICT_EN_FR = {
    "hello": "bonjour", "world": "monde", "good": "bon", "morning": "matin",
    "thank": "merci", "you": "vous", "the": "le", "a": "un", "is": "est",
    "are": "sont", "and": "et", "or": "ou", "but": "mais", "not": "pas",
    "this": "ceci", "that": "cela", "with": "avec", "for": "pour",
    "have": "avoir", "from": "de", "they": "ils", "we": "nous",
    "say": "dire", "she": "elle", "he": "il", "it": "ce",
    "product": "produit", "service": "service", "price": "prix",
    "order": "commande", "customer": "client", "company": "entreprise",
}
_DICT_EN_DE = {
    "hello": "hallo", "world": "welt", "good": "gut", "morning": "morgen",
    "thank": "danke", "you": "du", "the": "der", "a": "ein", "is": "ist",
    "are": "sind", "and": "und", "or": "oder", "but": "aber", "not": "nicht",
    "this": "dies", "that": "das", "with": "mit", "for": "für",
    "have": "haben", "from": "von", "they": "sie", "we": "wir",
    "say": "sagen", "she": "sie", "he": "er", "it": "es",
    "product": "produkt", "service": "dienst", "price": "preis",
    "order": "bestellung", "customer": "kunde", "company": "unternehmen",
}
_TRANSLATION_DICTS: dict[tuple[str,str], dict[str,str]] = {
    ("en","es"):_DICT_EN_ES,("en","fr"):_DICT_EN_FR,("en","de"):_DICT_EN_DE}


def translate(text: str, source_lang: str = "en", target_lang: str = "es") -> TranslationResult:
    dictionary = _TRANSLATION_DICTS.get((source_lang, target_lang), {})
    tokens = tokenize(text)
    if not tokens: return TranslationResult(text, source_lang, target_lang, 0.0)
    translated = []; hits = 0
    for tok in tokens:
        if tok in dictionary: translated.append(dictionary[tok]); hits += 1
        else: translated.append(f"[{tok}]")
    return TranslationResult(" ".join(translated), source_lang, target_lang, round(hits/len(tokens), 4))

# 5. QA with RAG


@dataclass
class QAResult:
    answer: str; context: str; score: float; sources: list[str] = field(default_factory=list)


class SimpleVectorStore:
    def __init__(self) -> None:
        self.documents: list[str] = []; self.vectors: list[np.ndarray] = []
        self._idf: dict[str, float] = {}; self._vocab: dict[str, int] = {}

    def _build_vocab(self) -> None:
        all_tokens: list[set[str]] = []
        for doc in self.documents:
            toks = set(tokenize(doc)); all_tokens.append(toks)
            for t in toks: self._vocab.setdefault(t, len(self._vocab))
        n_docs = len(self.documents)
        for tok in self._vocab:
            df = sum(1 for toks in all_tokens if tok in toks)
            self._idf[tok] = np.log((1 + n_docs) / (1 + df)) + 1

    def _vectorize(self, text: str) -> np.ndarray:
        tokens = tokenize(text); vec = np.zeros(len(self._vocab))
        for tok in tokens:
            if tok in self._vocab: vec[self._vocab[tok]] += 1
        for tok in set(tokens):
            if tok in self._idf: vec[self._vocab[tok]] *= self._idf[tok]
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def add_documents(self, docs: Iterable[str]) -> None:
        for doc in docs: self.documents.append(doc)
        self._vocab.clear(); self._idf.clear(); self._build_vocab()
        self.vectors = [self._vectorize(d) for d in self.documents]

    def search(self, query: str, top_k: int = 3) -> list[tuple[int, float]]:
        if not self.documents: return []
        qvec = self._vectorize(query)
        scores = [(i, cosine_sim(qvec, v)) for i, v in enumerate(self.vectors)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


def answer_question(question: str, vector_store: SimpleVectorStore, top_k: int = 3) -> QAResult:
    results = vector_store.search(question, top_k=top_k)
    if not results: return QAResult("No relevant documents found.", "", 0.0)
    best_idx, best_score = results[0]; context = vector_store.documents[best_idx]
    sources = [f"doc_{idx}" for idx, _ in results]
    q_tokens = set(tokenize(question)); relevant: list[tuple[int,str]] = []
    for sent in re.split(r"[.!?]+", context):
        sent = sent.strip()
        if not sent: continue
        overlap = len(q_tokens & set(tokenize(sent)))
        if overlap > 0: relevant.append((overlap, sent))
    relevant.sort(key=lambda x: x[0], reverse=True)
    answer = ". ".join(s for _, s in relevant[:2]) if relevant else context[:200]
    return QAResult(answer, context, round(best_score, 4), sources)

# Pipeline


@dataclass
class NLPPipelineResult:
    entities: list[Entity]; sentiment: SentimentResult; classification: ClassificationResult
    translation: TranslationResult | None = None; qa: QAResult | None = None


def run_pipeline(
    text: str,
    *,
    target_lang: str | None = None,
    vector_store: SimpleVectorStore | None = None
) -> NLPPipelineResult:
    entities = ner_extract(text); sentiment = sentiment_analyze(text); classification = classify_text(text)
    translation = translate(text, target_lang=target_lang) if target_lang else None
    qa = answer_question(text, vector_store) if vector_store else None
    return NLPPipelineResult(entities, sentiment, classification, translation, qa)
