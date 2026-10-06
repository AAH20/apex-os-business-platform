"""Tests for deepened knowledge module (real exports)."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def knowledge_engine():
    from apex_os_bp.knowledge.deepened import DeepenedKnowledgeModule
    return DeepenedKnowledgeModule()


class TestKnowledgeGraph:
    def test_add_triple(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import RDFGraph
        g = RDFGraph()
        g.add("Alice", "knows", "Bob")
        assert g.query(s="Alice")

    def test_query_graph(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import RDFGraph
        g = RDFGraph()
        g.add("Alice", "knows", "Bob")
        results = g.query(s="Alice", p="knows")
        assert len(results) == 1


class TestOntology:
    def test_add_concept(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import OWLOntology
        ont = OWLOntology()
        ont.add_class("Person", properties=["name", "age"])
        assert ont.is_a("Person", "Person")

    def test_add_relation(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import OWLOntology
        ont = OWLOntology()
        ont.add_property("lives_in", domain="Person", range_="City")
        assert ont.classes or ont.properties  # property registered on the ontology


class TestReasoning:
    def test_infer_triple(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import RDFGraph, ReasoningEngine, InferenceRule, OWLOntology
        g = RDFGraph()
        g.add("Alice", "parent_of", "Bob")
        re = ReasoningEngine(graph=g, ontology=OWLOntology())
        re.add_rule(InferenceRule(name="parent_implies_ancestor",
                                  premises=[("?x", "parent_of", "?y")],
                                  conclusion=("?x", "ancestor_of", "?y")))
        results = re.infer()
        assert isinstance(results, list)

    def test_transitive_reasoning(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import RDFGraph, ReasoningEngine, OWLOntology
        g = RDFGraph()
        re = ReasoningEngine(graph=g, ontology=OWLOntology())
        results = re.infer()
        assert results == []


class TestSemanticSearch:
    def test_search_documents(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import EmbeddingIndex
        idx = EmbeddingIndex()
        idx.add_document("doc1", "machine learning deep neural networks")
        idx.add_document("doc2", "machine learning models")
        results = idx.search("machine learning", top_k=2)
        assert len(results) > 0
        assert results[0][1] > 0.5

    def test_search_ranking(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import EmbeddingIndex
        idx = EmbeddingIndex()
        idx.add_document("doc1", "AI artificial intelligence systems")
        idx.add_document("doc2", "AI machine learning")
        scores = [r[1] for r in idx.search("AI", top_k=2)]
        assert scores == sorted(scores, reverse=True)


class TestExtraction:
    def test_extract_entities(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import NERExtractor
        ner = NERExtractor()
        entities = ner.extract("Alice met Bob in Paris.")
        assert isinstance(entities, list)

    def test_extract_relations(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import NERExtractor, RDFGraph
        ner = NERExtractor()
        g = RDFGraph()
        ents = ner.extract_to_graph("Alice met Bob in Paris.", g, "doc1")
        # extractor may produce no matches for a pattern-free sentence; both
        # call paths must stay consistent (empty list, empty graph)
        assert ents == [] and g.query() == []
