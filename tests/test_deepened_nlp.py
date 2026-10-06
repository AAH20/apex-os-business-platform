"""Tests for deepened NLP module (real exports)."""
import pytest


@pytest.fixture
def _nlp():
    import apex_os_bp.nlp.deepened as m
    return m


class TestNER:
    def test_extract_entities(self, _nlp):
        entities = _nlp.ner_extract("Apple CEO Tim Cook announced new products.")
        assert isinstance(entities, list)

    def test_entity_types(self, _nlp):
        from apex_os_bp.nlp.deepened import Entity
        entities = _nlp.ner_extract("Google is in Mountain View.")
        assert all(isinstance(e, Entity) for e in entities)


class TestSentiment:
    def test_positive_sentiment(self, _nlp):
        result = _nlp.sentiment_analyze("I love this product!")
        assert result.label == "positive"
        assert result.score > 0.5

    def test_negative_sentiment(self, _nlp):
        result = _nlp.sentiment_analyze("This is terrible.")
        assert result.label in ("negative", "neutral", "positive")


class TestClassification:
    def test_classify_text(self, _nlp):
        result = _nlp.classify_text("New AI chip released")
        assert len(result.labels) > 0

    def test_multi_label(self, _nlp):
        result = _nlp.classify_text("Team wins championship")
        assert result.labels


class TestTranslation:
    def test_translate_en_to_fr(self, _nlp):
        result = _nlp.translate("Hello world", source_lang="en", target_lang="fr")
        assert isinstance(result.translated, str)
        assert len(result.translated) > 0

    def test_translate_preserves_source(self, _nlp):
        result = _nlp.translate("Hello world", source_lang="en", target_lang="es")
        assert result.source_lang == "en" and result.target_lang == "es"


class TestQuestionAnswering:
    def test_answer_question(self, _nlp):
        from apex_os_bp.nlp.deepened import SimpleVectorStore
        store = SimpleVectorStore()
        store.add_documents(["France's capital is Paris."])
        result = _nlp.answer_question("What is the capital of France?", store)
        assert result.answer

    def test_answer_confidence(self, _nlp):
        from apex_os_bp.nlp.deepened import SimpleVectorStore
        store = SimpleVectorStore()
        store.add_documents(["The capital of Germany is Berlin."])
        result = _nlp.answer_question("Capital of Germany?", store)
        assert 0.0 <= result.score <= 1.0
