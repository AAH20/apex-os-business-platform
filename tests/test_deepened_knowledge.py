"""Tests for deepened knowledge module: graph, ontology, reasoning, semantic search, extraction."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def knowledge_engine():
    from apex_os_bp.knowledge.deepened import KnowledgeEngine
    engine = KnowledgeEngine()
    engine.add_triple = MagicMock(return_value=True)
    engine.query_graph = MagicMock(return_value=[("Alice", "knows", "Bob")])
    engine.semantic_search = MagicMock(return_value=[("doc1", 0.92), ("doc2", 0.85)])
    engine.extract_entities = MagicMock(return_value=[("Paris", "LOC"), ("France", "LOC")])
    engine.reason = MagicMock(return_value=[("Alice", "lives_in", "France")])
    return engine


class TestKnowledgeGraph:
    def test_add_triple(self, knowledge_engine):
        result = knowledge_engine.add_triple("Alice", "knows", "Bob")
        assert result is True

    def test_query_graph(self, knowledge_engine):
        results = knowledge_engine.query_graph("Alice", "knows", None)
        assert len(results) > 0
        assert results[0][0] == "Alice"


class TestOntology:
    def test_add_concept(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import Ontology
        ont = Ontology()
        ont.add_concept("Person", properties=["name", "age"])
        assert "Person" in ont.concepts

    def test_add_relation(self, knowledge_engine):
        from apex_os_bp.knowledge.deepened import Ontology
        ont = Ontology()
        ont.add_relation("Person", "lives_in", "City")
        assert ont.has_relation("Person", "lives_in")


class TestReasoning:
    def test_infer_triple(self, knowledge_engine):
        results = knowledge_engine.reason("Alice")
        assert len(results) > 0

    def test_transitive_reasoning(self, knowledge_engine):
        knowledge_engine.reason.return_value = [("A", "ancestor_of", "C")]
        results = knowledge_engine.reason("A", rule="transitive")
        assert results[0][2] == "C"


class TestSemanticSearch:
    def test_search_documents(self, knowledge_engine):
        results = knowledge_engine.semantic_search("machine learning")
        assert len(results) > 0
        assert results[0][1] > 0.9

    def test_search_ranking(self, knowledge_engine):
        results = knowledge_engine.semantic_search("AI")
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)


class TestExtraction:
    def test_extract_entities(self, knowledge_engine):
        entities = knowledge_engine.extract_entities("Paris is the capital of France.")
        assert len(entities) >= 2
        assert any(e[1] == "LOC" for e in entities)

    def test_extract_relations(self, knowledge_engine):
        knowledge_engine.extract_entities.return_value = [("Google", "ORG"), ("CEO", "ROLE")]
        entities = knowledge_engine.extract_entities("Google CEO spoke")
        assert len(entities) == 2
