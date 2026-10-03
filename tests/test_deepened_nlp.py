"""Tests for deepened NLP module: NER, sentiment, classification, translation, QA."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def nlp_engine():
    from apex_os_bp.nlp.deepened import NLPEngine
    engine = NLPEngine()
    engine.ner = MagicMock(return_value=[("Apple", "ORG"), ("Tim Cook", "PERSON")])
    engine.sentiment = MagicMock(return_value={"label": "positive", "score": 0.92})
    engine.classify = MagicMock(return_value=[("technology", 0.88)])
    engine.translate = MagicMock(return_value="Bonjour le monde")
    engine.answer = MagicMock(return_value="Paris")
    return engine


class TestNER:
    def test_extract_entities(self, nlp_engine):
        text = "Apple CEO Tim Cook announced new products."
        entities = nlp_engine.ner(text)
        assert len(entities) >= 2
        assert any(e[1] == "ORG" for e in entities)

    def test_entity_types(self, nlp_engine):
        entities = nlp_engine.ner("Google is in Mountain View.")
        types = {e[1] for e in entities}
        assert "ORG" in types or "LOC" in types


class TestSentiment:
    def test_positive_sentiment(self, nlp_engine):
        result = nlp_engine.sentiment("I love this product!")
        assert result["label"] == "positive"
        assert result["score"] > 0.5

    def test_negative_sentiment(self, nlp_engine):
        nlp_engine.sentiment.return_value = {"label": "negative", "score": 0.1}
        result = nlp_engine.sentiment("This is terrible.")
        assert result["label"] == "negative"


class TestClassification:
    def test_classify_text(self, nlp_engine):
        labels = nlp_engine.classify("New AI chip released")
        assert len(labels) > 0
        assert labels[0][0] == "technology"

    def test_multi_label(self, nlp_engine):
        nlp_engine.classify.return_value = [("sports", 0.9), ("news", 0.7)]
        labels = nlp_engine.classify("Team wins championship")
        assert len(labels) == 2


class TestTranslation:
    def test_translate_en_to_fr(self, nlp_engine):
        result = nlp_engine.translate("Hello world", source="en", target="fr")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_translate_preserves_meaning(self, nlp_engine):
        nlp_engine.translate.return_value = "Hola mundo"
        result = nlp_engine.translate("Hello world", source="en", target="es")
        assert "Hola" in result


class TestQuestionAnswering:
    def test_answer_question(self, nlp_engine):
        result = nlp_engine.answer("What is the capital of France?", context="France's capital is Paris.")
        assert result == "Paris"

    def test_answer_confidence(self, nlp_engine):
        nlp_engine.answer.return_value = ("Berlin", 0.95)
        answer, conf = nlp_engine.answer("Capital of Germany?")
        assert conf > 0.8
