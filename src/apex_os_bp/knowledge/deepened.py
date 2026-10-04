"""Deepened knowledge module: RDF graph, OWL ontology, reasoning, semantic search, NER extraction."""
from __future__ import annotations
import re
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

# ── 1. Knowledge Graph with RDF ──────────────────────────────────────────────


@dataclass(frozen=True)
class Triple:
    subject: str
    predicate: str
    obj: str


class RDFGraph:
    """Minimal RDF triple store with SPARQL-like pattern matching."""
    def __init__(self):
        self.triples: Set[Triple] = set()

    def add(self, s: str, p: str, o: str) -> None:
        self.triples.add(Triple(s, p, o))

    def query(self, s: Optional[str] = None, p: Optional[str] = None, o: Optional[str] = None) -> List[Triple]:
        return [t for t in self.triples
                if (not s or t.subject == s) and (not p or t.predicate == p) and (not o or t.obj == o)]

    def serialize_turtle(self) -> str:
        lines = ["@prefix ex: <http://example.org/> ."]
        for t in sorted(self.triples, key=lambda x: (x.subject, x.predicate)):
            lines.append(f"ex:{t.subject} ex:{t.predicate} ex:{t.obj} .")
        return "\n".join(lines)


# ── 2. Ontology Management with OWL ──────────────────────────────────────────

@dataclass
class OWLClass:
    name: str
    parent: Optional[str] = None
    properties: List[str] = field(default_factory=list)


@dataclass
class OWLProperty:
    name: str
    domain: str
    range: str
    inverse: Optional[str] = None


class OWLOntology:
    """Lightweight OWL ontology with class hierarchy and property constraints."""
    def __init__(self, iri: str = "http://apex-os.org/ontology"):
        self.iri = iri
        self.classes: Dict[str, OWLClass] = {}
        self.properties: Dict[str, OWLProperty] = {}
        self.individuals: Dict[str, str] = {}

    def add_class(self, name: str, parent: Optional[str] = None, properties: List[str] = None) -> None:
        self.classes[name] = OWLClass(name, parent, properties or [])

    def add_property(self, name: str, domain: str, range_: str, inverse: Optional[str] = None) -> None:
        self.properties[name] = OWLProperty(name, domain, range_, inverse)

    def add_individual(self, name: str, class_name: str) -> None:
        self.individuals[name] = class_name

    def is_a(self, class_name: str, ancestor: str) -> bool:
        current = self.classes.get(class_name)
        while current:
            if current.name == ancestor: return True
            current = self.classes.get(current.parent) if current.parent else None
        return False

    def ancestors(self, class_name: str) -> List[str]:
        result, current = [], self.classes.get(class_name)
        while current and current.parent:
            result.append(current.parent)
            current = self.classes.get(current.parent)
        return result

    def to_owl_xml(self) -> str:
        lines = [f'<Ontology xmlns="{self.iri}">']
        for cls in self.classes.values():
            p = f' rdf:resource="#{cls.parent}"' if cls.parent else ''
            lines.append(f'  <Class rdf:about="#{cls.name}"><subClassOf{p}/></Class>')
        for prop in self.properties.values():
            lines.append(
                f'  <ObjectProperty rdf:about="#{prop.name}">'
                f'<domain rdf:resource="#{prop.domain}"/>'
                f'<range rdf:resource="#{prop.range}"/></ObjectProperty>'
            )
        lines.append('</Ontology>')
        return "\n".join(lines)


# ── 3. Reasoning Engine with Inference ───────────────────────────────────────

@dataclass
class InferenceRule:
    name: str
    premises: List[Tuple[str, str, str]]
    conclusion: Tuple[str, str, str]


class ReasoningEngine:
    """Forward-chaining inference engine over RDF graph + OWL ontology."""
    def __init__(self, graph: RDFGraph, ontology: OWLOntology):
        self.graph, self.ontology, self.rules = graph, ontology, []
        self._add_default_rules()

    def _add_default_rules(self) -> None:
        self.rules = [
            InferenceRule("transitive_subclass", [("?a", "subClassOf", "?b"),
                          ("?b", "subClassOf", "?c")], ("?a", "subClassOf", "?c")),
            InferenceRule("symmetric_knows", [("?a", "knows", "?b")], ("?b", "knows", "?a")),
            InferenceRule("type_inference", [("?x", "type", "?c"), ("?c", "subClassOf", "?d")], ("?x", "type", "?d")),
        ]

    def add_rule(self, rule: InferenceRule) -> None:
        self.rules.append(rule)

    def _match(self, pattern, binding):
        s, p, o = pattern
        results = []
        for t in self.graph.triples:
            nb = dict(binding)
            for var, val in ((s, t.subject), (p, t.predicate), (o, t.obj)):
                if var is None: continue
                if not var.startswith("?"):
                    if val != var: break
                else:
                    v = var[1:]
                    if v in nb and nb[v] != val: break
                    nb[v] = val
            else:
                results.append(nb)
        return results

    def infer(self, max_iterations: int = 10) -> List[Triple]:
        new_triples = []
        for _ in range(max_iterations):
            added = False
            for rule in self.rules:
                bindings = [{}]
                for premise in rule.premises:
                    bindings = [nb for b in bindings for nb in self._match(premise, b)]
                for b in bindings:
                    s, p, o = rule.conclusion
                    sv = b.get(s[1:], s) if s and s.startswith("?") else s
                    pv = b.get(p[1:], p) if p and p.startswith("?") else p
                    ov = b.get(o[1:], o) if o and o.startswith("?") else o
                    if sv and pv and ov and Triple(sv, pv, ov) not in self.graph.triples:
                        self.graph.add(sv, pv, ov)
                        new_triples.append(Triple(sv, pv, ov))
                        added = True
            if not added: break
        return new_triples


# ── 4. Semantic Search with Embeddings ────────────────────────────────────────

class EmbeddingIndex:
    """TF-IDF based embedding index for semantic similarity search."""
    def __init__(self):
        self.documents: Dict[str, str] = {}
        self.vectors: Dict[str, Dict[str, float]] = {}
        self.idf: Dict[str, float] = {}
        self._doc_count = 0

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        tf = defaultdict(int)
        for t in tokens: tf[t] += 1
        total = len(tokens) or 1
        return {t: c / total for t, c in tf.items()}

    def add_document(self, doc_id: str, text: str) -> None:
        self.documents[doc_id] = text
        tokens = self._tokenize(text)
        self.vectors[doc_id] = self._compute_tf(tokens)
        self._doc_count += 1
        for term in set(tokens): self.idf[term] = self.idf.get(term, 0) + 1
        for term in self.idf:
            self.idf[term] = math.log((self._doc_count + 1) / (self.idf[term] + 1)) + 1

    def _vector(self, tf):
        return {t: tf[t] * self.idf.get(t, 0) for t in tf}

    def _cosine(self, v1, v2):
        dot = sum(v1.get(t, 0) * v2.get(t, 0) for t in set(v1) | set(v2))
        m1 = math.sqrt(sum(x * x for x in v1.values())) or 1
        m2 = math.sqrt(sum(x * x for x in v2.values())) or 1
        return dot / (m1 * m2)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        tokens = self._tokenize(query)
        if not tokens: return []
        q_vec = self._vector(self._compute_tf(tokens))
        scores = [(d, self._cosine(q_vec, self._vector(tf))) for d, tf in self.vectors.items()]
        return sorted([s for s in scores if s[1] > 0], key=lambda x: x[1], reverse=True)[:top_k]


# ── 5. Knowledge Extraction with NER ────────────────────────────────────────

@dataclass
class Entity:
    text: str
    label: str
    start: int
    end: int


class NERExtractor:
    """Rule-based NER for extracting entities from text."""
    PATTERNS = {
        "PERSON": [r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'],
        "ORG": [r'\b[A-Z][a-z]* (?:Inc|Corp|Ltd|LLC|Company|Group)\b', r'\b[A-Z]{2,6}\b'],
        "EMAIL": [r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b'],
        "URL": [r'https?://[^\s]+'],
        "MONEY": [r'\$\d+(?:,\d{3})*(?:\.\d{2})?', r'\b\d+(?:,\d{3})* (?:USD|EUR|GBP)\b'],
        "DATE": [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',
        ],
        "PRODUCT": [r'\b[A-Z][a-zA-Z0-9]*(?:Pro|Max|Plus|Ultra|Lite)\b'],
    }

    def extract(self, text: str) -> List[Entity]:
        entities = []
        for label, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for m in re.finditer(pattern, text):
                    entities.append(Entity(m.group(), label, m.start(), m.end()))
        entities.sort(key=lambda e: (e.start, -(e.end - e.start)))
        filtered, last_end = [], -1
        for e in entities:
            if e.start >= last_end:
                filtered.append(e)
                last_end = e.end
        return filtered

    def extract_to_graph(self, text: str, graph: RDFGraph, doc_id: str) -> List[Entity]:
        entities = self.extract(text)
        for ent in entities:
            graph.add(f"doc:{doc_id}", "hasEntity", f"{ent.label}:{ent.text}")
            graph.add(f"{ent.label}:{ent.text}", "type", ent.label)
        return entities


# ── Unified Knowledge Module ─────────────────────────────────────────────────

class DeepenedKnowledgeModule:
    """Unified facade combining all five capabilities."""
    def __init__(self):
        self.graph = RDFGraph()
        self.ontology = OWLOntology()
        self.reasoner = ReasoningEngine(self.graph, self.ontology)
        self.search_index = EmbeddingIndex()
        self.extractor = NERExtractor()

    def ingest(self, doc_id: str, text: str) -> List[Entity]:
        entities = self.extractor.extract_to_graph(text, self.graph, doc_id)
        self.search_index.add_document(doc_id, text)
        return entities

    def query(self, sparql_pattern: dict) -> List[Triple]:
        return self.graph.query(sparql_pattern.get("s"), sparql_pattern.get("p"), sparql_pattern.get("o"))

    def search(self, query_text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        return self.search_index.search(query_text, top_k)

    def infer(self) -> List[Triple]:
        return self.reasoner.infer()

    def add_ontology_class(self, name: str, parent: Optional[str] = None) -> None:
        self.ontology.add_class(name, parent)

    def add_ontology_property(self, name: str, domain: str, range_: str) -> None:
        self.ontology.add_property(name, domain, range_)

    def stats(self) -> Dict[str, int]:
        return {"triples": len(self.graph.triples), "classes": len(self.ontology.classes),
                "properties": len(self.ontology.properties), "documents": len(self.search_index.documents),
                "rules": len(self.reasoner.rules)}
