"""Tests for the APEX-OS search system."""
import unittest

from apex_os_bp.search import Autocomplete, InvertedIndex, tokenize


class TestTokenize(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(tokenize("Hello World"), ["hello", "world"])

    def test_punctuation(self):
        self.assertEqual(tokenize("Hello, World!"), ["hello", "world"])

    def test_empty(self):
        self.assertEqual(tokenize(""), [])

    def test_numbers(self):
        tokens = tokenize("Python 3.12")
        self.assertIn("python", tokens)
        self.assertIn("3", tokens)
        self.assertIn("12", tokens)


class TestInvertedIndex(unittest.TestCase):
    def test_add_and_search(self):
        idx = InvertedIndex()
        idx.add(1, "hello world")
        idx.add(2, "world peace")
        idx.add(3, "hello there")
        self.assertEqual(idx.search("hello"), [1, 3])
        self.assertEqual(idx.search("world"), [1, 2])
        self.assertEqual(idx.search("hello world"), [1])
        self.assertEqual(idx.search("missing"), [])

    def test_case_insensitive(self):
        idx = InvertedIndex()
        idx.add(1, "Hello World")
        self.assertEqual(idx.search("hello"), [1])
        self.assertEqual(idx.search("WORLD"), [1])

    def test_empty_query(self):
        idx = InvertedIndex()
        idx.add(1, "test")
        self.assertEqual(idx.search(""), [])

    def test_get_document(self):
        idx = InvertedIndex()
        idx.add(1, "hello world")
        self.assertEqual(idx.get(1), "hello world")
        self.assertEqual(idx.get(999), "")

    def test_len(self):
        idx = InvertedIndex()
        self.assertEqual(len(idx), 0)
        idx.add(1, "a")
        idx.add(2, "b")
        self.assertEqual(len(idx), 2)

    def test_duplicate_terms(self):
        idx = InvertedIndex()
        idx.add(1, "hello hello world")
        self.assertEqual(idx.search("hello"), [1])


class TestAutocomplete(unittest.TestCase):
    def test_complete(self):
        ac = Autocomplete()
        ac.add("hello world")
        ac.add("help me")
        ac.add("hero")
        self.assertEqual(ac.complete("hel"), ["hello", "help"])
        self.assertEqual(ac.complete("he"), ["hello", "help", "hero"])
        self.assertEqual(ac.complete("xyz"), [])

    def test_case_insensitive(self):
        ac = Autocomplete()
        ac.add("Hello")
        self.assertEqual(ac.complete("hel"), ["hello"])

    def test_limit(self):
        ac = Autocomplete()
        for i in range(20):
            ac.add(f"test{i}")
        self.assertEqual(len(ac.complete("test")), 10)

    def test_empty_prefix(self):
        ac = Autocomplete()
        ac.add("apple")
        ac.add("banana")
        self.assertEqual(len(ac.complete("")), 2)

    def test_len(self):
        ac = Autocomplete()
        self.assertEqual(len(ac), 0)
        ac.add("hello world")
        self.assertEqual(len(ac), 2)


if __name__ == "__main__":
    unittest.main()
