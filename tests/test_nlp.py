"""Tests for the NLP module."""

import os
import sys
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.nlp.text_analysis import (
    AnalysisResult,
    ReadabilityScores,
    TextAnalyzer,
    TextStatistics,
)
from apex_os_bp.nlp.sentiment import (
    SentimentAnalyzer,
    SentimentLabel,
    SentimentResult,
)
from apex_os_bp.nlp.entities import (
    Entity,
    EntityExtractionResult,
    EntityExtractor,
    EntityType,
)
from apex_os_bp.nlp.translation import (
    LanguageCode,
    TranslationResult,
    Translator,
)
from apex_os_bp.nlp.generation import (
    GenerationResult,
    TextGenerator,
)


class TestTextAnalyzer(unittest.TestCase):
    """Tests for TextAnalyzer."""

    def setUp(self):
        self.analyzer = TextAnalyzer()

    def test_tokenize_words_basic(self):
        text = "Hello world, this is a test."
        tokens = self.analyzer.tokenize_words(text)
        self.assertEqual(tokens, ["hello", "world", "this", "is", "a", "test"])

    def test_tokenize_words_empty(self):
        self.assertEqual(self.analyzer.tokenize_words(""), [])

    def test_tokenize_words_contractions(self):
        text = "It's a beautiful day, isn't it?"
        tokens = self.analyzer.tokenize_words(text)
        self.assertIn("it's", tokens)
        self.assertIn("isn't", tokens)

    def test_tokenize_sentences_basic(self):
        text = "Hello world. How are you? I am fine!"
        sentences = self.analyzer.tokenize_sentences(text)
        self.assertEqual(len(sentences), 3)

    def test_tokenize_sentences_empty(self):
        self.assertEqual(self.analyzer.tokenize_sentences(""), [])

    def test_tokenize_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        paragraphs = self.analyzer.tokenize_paragraphs(text)
        self.assertEqual(len(paragraphs), 3)

    def test_word_frequency(self):
        text = "the cat sat on the mat the cat ran"
        freq = self.analyzer.word_frequency(text)
        self.assertEqual(freq["the"], 3)
        self.assertEqual(freq["cat"], 2)
        self.assertEqual(freq["sat"], 1)

    def test_word_frequency_remove_stopwords(self):
        text = "the cat sat on the mat"
        freq = self.analyzer.word_frequency(text, remove_stopwords=True)
        self.assertNotIn("the", freq)
        self.assertIn("cat", freq)

    def test_top_n_words(self):
        text = "apple banana apple cherry banana apple"
        top = self.analyzer.top_n_words(text, n=2)
        self.assertEqual(top[0], ("apple", 3))
        self.assertEqual(top[1], ("banana", 2))

    def test_extract_bigrams(self):
        text = "the quick brown fox"
        bigrams = self.analyzer.extract_ngrams(text, n=2)
        self.assertIn(("the", "quick"), bigrams)
        self.assertIn(("quick", "brown"), bigrams)
        self.assertIn(("brown", "fox"), bigrams)

    def test_extract_trigrams(self):
        text = "the quick brown fox jumps"
        trigrams = self.analyzer.extract_ngrams(text, n=3)
        self.assertIn(("the", "quick", "brown"), trigrams)
        self.assertIn(("quick", "brown", "fox"), trigrams)

    def test_extract_ngrams_too_short(self):
        text = "hello"
        bigrams = self.analyzer.extract_ngrams(text, n=2)
        self.assertEqual(bigrams, [])

    def test_count_syllables_simple(self):
        self.assertEqual(self.analyzer._count_syllables("cat"), 1)
        self.assertEqual(self.analyzer._count_syllables("dog"), 1)

    def test_count_syllables_complex(self):
        self.assertEqual(self.analyzer._count_syllables("beautiful"), 3)
        self.assertGreaterEqual(self.analyzer._count_syllables("computer"), 3)

    def test_compute_statistics_basic(self):
        text = "Hello world. This is a test."
        stats = self.analyzer.compute_statistics(text)
        self.assertEqual(stats.word_count, 6)
        self.assertEqual(stats.sentence_count, 2)
        self.assertGreater(stats.char_count, 0)
        self.assertGreater(stats.avg_word_length, 0)

    def test_compute_statistics_empty(self):
        stats = self.analyzer.compute_statistics("")
        self.assertEqual(stats.word_count, 0)
        self.assertEqual(stats.char_count, 0)

    def test_compute_statistics_reading_time(self):
        text = "word " * 200
        stats = self.analyzer.compute_statistics(text)
        self.assertAlmostEqual(stats.reading_time_seconds, 60.0, delta=5)

    def test_compute_readability(self):
        text = "The cat sat on the mat. The dog ran in the park."
        scores = self.analyzer.compute_readability(text)
        self.assertIsInstance(scores, ReadabilityScores)
        self.assertGreater(scores.flesch_reading_ease, 0)

    def test_compute_readability_empty(self):
        scores = self.analyzer.compute_readability("")
        self.assertEqual(scores.flesch_reading_ease, 0.0)

    def test_detect_language_english(self):
        text = "the quick brown fox jumps over the lazy dog"
        lang = self.analyzer.detect_language(text)
        self.assertEqual(lang, "en")

    def test_detect_language_spanish(self):
        text = "el gato rápido salta sobre el perro perezoso"
        lang = self.analyzer.detect_language(text)
        self.assertEqual(lang, "es")

    def test_detect_language_french(self):
        text = "le chat rapide saute par dessus le chien paresseux"
        lang = self.analyzer.detect_language(text)
        self.assertEqual(lang, "fr")

    def test_detect_language_german(self):
        text = "der schnelle katze springt über den faulen hund"
        lang = self.analyzer.detect_language(text)
        self.assertEqual(lang, "de")

    def test_detect_language_empty(self):
        self.assertEqual(self.analyzer.detect_language(""), "en")

    def test_analyze_full(self):
        text = "The quick brown fox jumps over the lazy dog. " * 5
        result = self.analyzer.analyze(text)
        self.assertIsInstance(result, AnalysisResult)
        self.assertGreater(result.statistics.word_count, 0)
        self.assertIsNotNone(result.readability)
        self.assertIsInstance(result.top_words, list)
        self.assertIsInstance(result.bigrams, list)
        self.assertIsInstance(result.trigrams, list)
        self.assertEqual(result.language, "en")

    def test_analyze_result_dataclass(self):
        result = AnalysisResult()
        self.assertIsInstance(result.statistics, TextStatistics)
        self.assertIsInstance(result.readability, ReadabilityScores)


class TestSentimentAnalyzer(unittest.TestCase):
    """Tests for SentimentAnalyzer."""

    def setUp(self):
        self.analyzer = SentimentAnalyzer()

    def test_analyze_positive(self):
        text = "This is a great and amazing product. I love it!"
        result = self.analyzer.analyze(text)
        self.assertGreater(result.score, 0)
        self.assertIn(result.label, [
            SentimentLabel.POSITIVE,
            SentimentLabel.VERY_POSITIVE,
            SentimentLabel.SLIGHTLY_POSITIVE,
        ])

    def test_analyze_negative(self):
        text = "This is a terrible and awful product. I hate it!"
        result = self.analyzer.analyze(text)
        self.assertLess(result.score, 0)
        self.assertIn(result.label, [
            SentimentLabel.NEGATIVE,
            SentimentLabel.VERY_NEGATIVE,
            SentimentLabel.SLIGHTLY_NEGATIVE,
        ])

    def test_analyze_neutral(self):
        text = "The sky is blue. The grass is green."
        result = self.analyzer.analyze(text)
        self.assertAlmostEqual(result.score, 0.0, delta=0.1)

    def test_analyze_empty(self):
        result = self.analyzer.analyze("")
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.label, SentimentLabel.NEUTRAL)

    def test_analyze_with_negation(self):
        text = "This is not good at all"
        result = self.analyzer.analyze(text)
        self.assertLess(result.score, 0.5)

    def test_analyze_with_intensifier(self):
        text = "This is very good and extremely amazing"
        result = self.analyzer.analyze(text)
        self.assertGreater(result.score, 0.3)

    def test_positive_words_detected(self):
        text = "I love this great product"
        result = self.analyzer.analyze(text)
        self.assertIn("love", result.positive_words)
        self.assertIn("great", result.positive_words)

    def test_negative_words_detected(self):
        text = "I hate this terrible product"
        result = self.analyzer.analyze(text)
        self.assertIn("hate", result.negative_words)
        self.assertIn("terrible", result.negative_words)

    def test_is_positive(self):
        self.assertTrue(self.analyzer.is_positive("This is great!"))
        self.assertFalse(self.analyzer.is_positive("This is terrible!"))

    def test_is_negative(self):
        self.assertTrue(self.analyzer.is_negative("This is terrible!"))
        self.assertFalse(self.analyzer.is_negative("This is great!"))

    def test_batch_analyze(self):
        texts = ["Great!", "Terrible!", "Okay."]
        results = self.analyzer.batch_analyze(texts)
        self.assertEqual(len(results), 3)
        self.assertGreater(results[0].score, 0)
        self.assertLess(results[1].score, 0)

    def test_sentiment_result_dataclass(self):
        result = SentimentResult()
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.label, SentimentLabel.NEUTRAL)

    def test_confidence(self):
        text = "I really love this amazing great wonderful product"
        result = self.analyzer.analyze(text)
        self.assertGreater(result.confidence, 0)

    def test_comparative_score(self):
        text = "good " * 10
        result = self.analyzer.analyze(text)
        self.assertGreater(result.comparative, 0)


class TestEntityExtractor(unittest.TestCase):
    """Tests for EntityExtractor."""

    def setUp(self):
        self.extractor = EntityExtractor()

    def test_extract_emails(self):
        text = "Contact us at support@example.com or sales@company.org"
        entities = self.extractor.extract_emails(text)
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0].text, "support@example.com")
        self.assertEqual(entities[0].type, EntityType.EMAIL)

    def test_extract_urls(self):
        text = "Visit https://example.com or www.test.org for more info"
        entities = self.extractor.extract_urls(text)
        self.assertGreaterEqual(len(entities), 2)

    def test_extract_phones(self):
        text = "Call us at 555-123-4567 or +1-800-555-0199"
        entities = self.extractor.extract_phones(text)
        self.assertGreaterEqual(len(entities), 1)

    def test_extract_dates(self):
        text = "Meeting on 12/25/2023 and 01/15/2024"
        entities = self.extractor.extract_dates(text)
        self.assertGreaterEqual(len(entities), 2)

    def test_extract_times(self):
        text = "Meeting at 10:30 AM and 2:45 PM"
        entities = self.extractor.extract_times(text)
        self.assertGreaterEqual(len(entities), 2)

    def test_extract_money(self):
        text = "The price is $99.99 or €50"
        entities = self.extractor.extract_money(text)
        self.assertGreaterEqual(len(entities), 1)

    def test_extract_percents(self):
        text = "The rate is 25% or 50 percent"
        entities = self.extractor.extract_percents(text)
        self.assertGreaterEqual(len(entities), 2)

    def test_extract_hashtags(self):
        text = "Check out #AI and #MachineLearning"
        entities = self.extractor.extract_hashtags(text)
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0].text, "#AI")

    def test_extract_mentions(self):
        text = "Thanks @john and @jane for the help"
        entities = self.extractor.extract_mentions(text)
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0].text, "@john")

    def test_extract_numbers(self):
        text = "There are 100 items and 3.14 is pi"
        entities = self.extractor.extract_numbers(text)
        self.assertGreaterEqual(len(entities), 2)

    def test_extract_persons_with_title(self):
        text = "Dr. Smith and Mr. Johnson attended the meeting"
        entities = self.extractor.extract_persons(text)
        self.assertGreaterEqual(len(entities), 2)

    def test_extract_organizations(self):
        text = "Microsoft Inc and Google Corp are tech companies"
        entities = self.extractor.extract_organizations(text)
        self.assertGreaterEqual(len(entities), 2)

    def test_extract_locations(self):
        text = "The meeting is in New York or London"
        entities = self.extractor.extract_locations(text)
        self.assertGreaterEqual(len(entities), 1)

    def test_extract_all(self):
        text = "Contact Dr. Smith at support@example.com or visit https://example.com. Meeting on 12/25/2023 in New York."
        result = self.extractor.extract_all(text)
        self.assertIsInstance(result, EntityExtractionResult)
        self.assertGreater(result.count(), 0)
        types_found = set(e.type for e in result.entities)
        self.assertIn(EntityType.EMAIL, types_found)
        self.assertIn(EntityType.URL, types_found)

    def test_get_by_type(self):
        text = "Email: test@example.com, Phone: 555-123-4567"
        result = self.extractor.extract_all(text)
        emails = result.get_by_type(EntityType.EMAIL)
        phones = result.get_by_type(EntityType.PHONE)
        self.assertEqual(len(emails), 1)
        self.assertGreaterEqual(len(phones), 1)

    def test_entity_dataclass(self):
        entity = Entity(text="test", type=EntityType.EMAIL, start=0, end=4)
        self.assertEqual(entity.text, "test")
        self.assertEqual(entity.type, EntityType.EMAIL)
        self.assertEqual(entity.confidence, 1.0)

    def test_overlapping_entities_removed(self):
        text = "Email: test@example.com"
        result = self.extractor.extract_all(text)
        for i in range(len(result.entities) - 1):
            self.assertLessEqual(
                result.entities[i].end,
                result.entities[i + 1].start,
            )


class TestTranslator(unittest.TestCase):
    """Tests for Translator."""

    def setUp(self):
        self.translator = Translator()

    def test_is_supported_pair(self):
        self.assertTrue(self.translator.is_supported_pair("en", "es"))
        self.assertTrue(self.translator.is_supported_pair("en", "fr"))
        self.assertTrue(self.translator.is_supported_pair("en", "de"))
        self.assertTrue(self.translator.is_supported_pair("en", "it"))
        self.assertTrue(self.translator.is_supported_pair("en", "pt"))

    def test_is_unsupported_pair(self):
        self.assertFalse(self.translator.is_supported_pair("en", "ja"))
        self.assertFalse(self.translator.is_supported_pair("es", "fr"))

    def test_get_supported_languages(self):
        langs = self.translator.get_supported_languages()
        self.assertIn("en", langs)
        self.assertIn("es", langs)
        self.assertIn("fr", langs)
        self.assertIn("de", langs)
        self.assertIn("it", langs)
        self.assertIn("pt", langs)

    def test_get_supported_pairs(self):
        pairs = self.translator.get_supported_pairs()
        self.assertIn(("en", "es"), pairs)
        self.assertIn(("en", "fr"), pairs)

    def test_translate_word(self):
        result = self.translator.translate_word("hello", "en", "es")
        self.assertEqual(result, "hola")

    def test_translate_word_not_found(self):
        result = self.translator.translate_word("xyznonexistent", "en", "es")
        self.assertIsNone(result)

    def test_translate_basic(self):
        text = "hello world"
        result = self.translator.translate(text, source="en", target="es")
        self.assertIsInstance(result, TranslationResult)
        self.assertIn("hola", result.translated_text.lower())

    def test_translate_empty(self):
        result = self.translator.translate("", source="en", target="es")
        self.assertEqual(result.translated_text, "")

    def test_translate_unsupported_pair(self):
        text = "hello"
        result = self.translator.translate(text, source="en", target="ja")
        self.assertEqual(result.translated_text, text)
        self.assertEqual(result.confidence, 0.0)

    def test_translate_preserves_case(self):
        text = "Hello"
        result = self.translator.translate(text, source="en", target="es")
        self.assertTrue(result.translated_text[0].isupper())

    def test_translate_confidence(self):
        text = "hello world good morning"
        result = self.translator.translate(text, source="en", target="es")
        self.assertGreater(result.confidence, 0)

    def test_translate_word_count(self):
        text = "hello world"
        result = self.translator.translate(text, source="en", target="es")
        self.assertEqual(result.word_count, 2)

    def test_batch_translate(self):
        texts = ["hello", "world", "good morning"]
        results = self.translator.batch_translate(texts, source="en", target="es")
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIsInstance(r, TranslationResult)

    def test_detect_and_translate(self):
        text = "hola mundo"
        result = self.translator.detect_and_translate(text, target="en")
        self.assertIsInstance(result, TranslationResult)

    def test_add_translation(self):
        self.translator.add_translation("en", "es", "computer", "computadora")
        result = self.translator.translate_word("computer", "en", "es")
        self.assertEqual(result, "computadora")

    def test_translation_result_dataclass(self):
        result = TranslationResult()
        self.assertEqual(result.original_text, "")
        self.assertEqual(result.translated_text, "")
        self.assertEqual(result.confidence, 0.0)

    def test_translate_french(self):
        text = "hello world"
        result = self.translator.translate(text, source="en", target="fr")
        self.assertIn("bonjour", result.translated_text.lower())

    def test_translate_german(self):
        text = "hello world"
        result = self.translator.translate(text, source="en", target="de")
        self.assertIn("hallo", result.translated_text.lower())

    def test_translate_italian(self):
        text = "hello world"
        result = self.translator.translate(text, source="en", target="it")
        self.assertIn("ciao", result.translated_text.lower())

    def test_translate_portuguese(self):
        text = "hello world"
        result = self.translator.translate(text, source="en", target="pt")
        self.assertIn("olá", result.translated_text.lower())


class TestTextGenerator(unittest.TestCase):
    """Tests for TextGenerator."""

    def setUp(self):
        self.generator = TextGenerator(seed=42)

    def test_generate_from_template(self):
        sentences = self.generator.generate_from_template(style="informative", count=3)
        self.assertEqual(len(sentences), 3)
        for s in sentences:
            self.assertTrue(s[0].isupper())
            self.assertTrue(s.endswith("."))

    def test_generate_from_template_descriptive(self):
        sentences = self.generator.generate_from_template(style="descriptive", count=2)
        self.assertEqual(len(sentences), 2)

    def test_generate_from_template_narrative(self):
        sentences = self.generator.generate_from_template(style="narrative", count=2)
        self.assertEqual(len(sentences), 2)

    def test_generate_from_template_persuasive(self):
        sentences = self.generator.generate_from_template(style="persuasive", count=2)
        self.assertEqual(len(sentences), 2)

    def test_generate_markov(self):
        text = self.generator.generate_markov(seed="the", length=10)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertTrue(text.endswith("."))

    def test_generate_markov_no_seed(self):
        text = self.generator.generate_markov(length=10)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)

    def test_generate_markov_unknown_seed(self):
        text = self.generator.generate_markov(seed="xyznonexistent", length=10)
        self.assertIsInstance(text, str)

    def test_generate_paragraph(self):
        text = self.generator.generate_paragraph(sentences=3, style="informative")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)

    def test_generate_paragraph_with_topic(self):
        text = self.generator.generate_paragraph(topic="the", sentences=2)
        self.assertIsInstance(text, str)

    def test_generate_bullet_points(self):
        bullets = self.generator.generate_bullet_points(count=5)
        self.assertEqual(len(bullets), 5)
        for b in bullets:
            self.assertTrue(b.startswith("•"))

    def test_generate_summary(self):
        text = "The quick brown fox jumps over the lazy dog. " * 10
        summary = self.generator.generate_summary(text, max_sentences=2)
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)

    def test_generate_summary_short_text(self):
        text = "Hello world."
        summary = self.generator.generate_summary(text, max_sentences=3)
        self.assertIsInstance(summary, str)

    def test_generate_summary_empty(self):
        summary = self.generator.generate_summary("")
        self.assertEqual(summary, "")

    def test_generate_template_method(self):
        result = self.generator.generate(method="template", style="informative", count=2)
        self.assertIsInstance(result, GenerationResult)
        self.assertEqual(result.method, "template")
        self.assertGreater(result.word_count, 0)

    def test_generate_markov_method(self):
        result = self.generator.generate(method="markov", seed="the", length=10)
        self.assertIsInstance(result, GenerationResult)
        self.assertEqual(result.method, "markov")
        self.assertGreater(result.word_count, 0)

    def test_generate_paragraph_method(self):
        result = self.generator.generate(method="paragraph", sentences=3)
        self.assertIsInstance(result, GenerationResult)
        self.assertEqual(result.method, "paragraph")

    def test_generate_summary_method(self):
        text = "The cat sat on the mat. " * 5
        result = self.generator.generate(method="summary", text=text, max_sentences=2)
        self.assertIsInstance(result, GenerationResult)
        self.assertEqual(result.method, "summary")

    def test_generate_unknown_method(self):
        result = self.generator.generate(method="unknown")
        self.assertEqual(result.method, "unknown")
        self.assertEqual(result.text, "")

    def test_train(self):
        corpus = ["the cat sat on the mat", "the dog ran in the park"]
        self.generator.train(corpus)
        text = self.generator.generate_markov(seed="the", length=5)
        self.assertIsInstance(text, str)

    def test_add_template(self):
        self.generator.add_template("custom", "The {noun} is {adj}.")
        sentences = self.generator.generate_from_template(style="custom", count=1)
        self.assertEqual(len(sentences), 1)

    def test_add_words(self):
        self.generator.add_words("noun", ["testword"])
        sentences = self.generator.generate_from_template(count=1)
        self.assertEqual(len(sentences), 1)

    def test_generation_result_dataclass(self):
        result = GenerationResult()
        self.assertEqual(result.text, "")
        self.assertEqual(result.method, "")
        self.assertEqual(result.word_count, 0)

    def test_reproducibility_with_seed(self):
        gen1 = TextGenerator(seed=123)
        gen2 = TextGenerator(seed=123)
        text1 = gen1.generate_markov(seed="the", length=10)
        text2 = gen2.generate_markov(seed="the", length=10)
        self.assertEqual(text1, text2)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple NLP components."""

    def setUp(self):
        self.analyzer = TextAnalyzer()
        self.sentiment = SentimentAnalyzer()
        self.extractor = EntityExtractor()
        self.translator = Translator()
        self.generator = TextGenerator(seed=42)

    def test_full_pipeline(self):
        text = "Apple Inc. is a great company. Contact them at info@apple.com. They make amazing products."
        analysis = self.analyzer.analyze(text)
        self.assertGreater(analysis.statistics.word_count, 0)
        sentiment = self.sentiment.analyze(text)
        self.assertGreater(sentiment.score, 0)
        entities = self.extractor.extract_all(text)
        self.assertGreater(entities.count(), 0)
        translation = self.translator.translate(text, source="en", target="es")
        self.assertIsInstance(translation, TranslationResult)
        generated = self.generator.generate(method="template", count=1)
        self.assertGreater(len(generated.text), 0)

    def test_sentiment_of_generated_text(self):
        generated = self.generator.generate(method="template", style="persuasive", count=1)
        sentiment = self.sentiment.analyze(generated.text)
        self.assertIsInstance(sentiment, SentimentResult)

    def test_entities_in_generated_text(self):
        generated = self.generator.generate(method="template", count=1)
        entities = self.extractor.extract_all(generated.text)
        self.assertIsInstance(entities, EntityExtractionResult)

    def test_translate_and_analyze(self):
        text = "hello world"
        translated = self.translator.translate(text, source="en", target="es")
        analysis = self.analyzer.analyze(translated.translated_text)
        self.assertGreater(analysis.statistics.word_count, 0)

    def test_summary_of_analysis(self):
        text = "The quick brown fox jumps over the lazy dog. " * 20
        summary = self.generator.generate_summary(text, max_sentences=3)
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)


if __name__ == "__main__":
    unittest.main()
