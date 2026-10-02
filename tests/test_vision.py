"""Tests for the APEX-OS Computer Vision System."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from apex_os_bp.vision import (
    FaceRecognition,
    FaceResult,
    ImageGenerator,
    ImageRecognition,
    ObjectDetector,
    OCREngine,
    RecognitionResult,
    DetectionResult,
    OCRResult,
    GenerationResult,
)


class TestImageRecognition(unittest.TestCase):
    """Tests for the image recognition module."""

    def setUp(self):
        self.recognizer = ImageRecognition(backend="builtin")

    def test_recognize_returns_result(self):
        """Test that recognize returns a RecognitionResult."""
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = self.recognizer.recognize(img)
        self.assertIsInstance(result, RecognitionResult)
        self.assertIsInstance(result.label, str)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_recognize_with_pil_image(self):
        """Test recognition with PIL Image input."""
        img = Image.new("RGB", (100, 100), (135, 206, 235))  # Sky blue
        result = self.recognizer.recognize(img)
        self.assertIsInstance(result, RecognitionResult)
        self.assertIn(result.label, ["sky", "water", "urban", "indoor", "portrait", "document", "night", "vegetation"])

    def test_recognize_with_file_path(self):
        """Test recognition with file path input."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 100), (135, 206, 235))
            img.save(f.name)
            result = self.recognizer.recognize(f.name)
            self.assertIsInstance(result, RecognitionResult)
            Path(f.name).unlink()

    def test_recognize_sky_image(self):
        """Test that a blue sky-like image is classified correctly."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :] = (135, 206, 235)  # Sky blue
        result = self.recognizer.recognize(img)
        self.assertIsInstance(result, RecognitionResult)
        # Should be classified as sky or water (both blue-ish)
        self.assertIn(result.label, ["sky", "water"])

    def test_recognize_dark_image(self):
        """Test that a dark image is classified as night or indoor."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :] = (10, 10, 10)  # Very dark
        result = self.recognizer.recognize(img)
        self.assertIn(result.label, ["night", "indoor"])

    def test_top_k_results(self):
        """Test that top_k results are returned."""
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = self.recognizer.recognize(img)
        self.assertGreater(len(result.top_k), 0)
        self.assertLessEqual(len(result.top_k), 5)

    def test_batch_recognize(self):
        """Test batch recognition."""
        images = [
            np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8) for _ in range(3)
        ]
        results = self.recognizer.batch_recognize(images)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIsInstance(r, RecognitionResult)

    def test_cache_key(self):
        """Test cache key generation."""
        img = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        key1 = self.recognizer.get_cache_key(img)
        key2 = self.recognizer.get_cache_key(img)
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 16)

    def test_to_dict(self):
        """Test result serialization."""
        img = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        result = self.recognizer.recognize(img)
        d = result.to_dict()
        self.assertIn("label", d)
        self.assertIn("confidence", d)
        self.assertIn("top_k", d)

    def test_active_backend(self):
        """Test that active backend is reported."""
        self.assertEqual(self.recognizer.active_backend, "builtin")

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        with self.assertRaises(FileNotFoundError):
            self.recognizer.recognize("/nonexistent/path/image.png")


class TestObjectDetection(unittest.TestCase):
    """Tests for the object detection module."""

    def setUp(self):
        self.detector = ObjectDetector(backend="builtin", confidence_threshold=0.1)

    def test_detect_returns_list(self):
        """Test that detect returns a list of DetectionResult."""
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        results = self.detector.detect(img)
        self.assertIsInstance(results, list)

    def test_detect_with_pil_image(self):
        """Test detection with PIL Image input."""
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        results = self.detector.detect(img)
        self.assertIsInstance(results, list)

    def test_detect_with_file_path(self):
        """Test detection with file path input."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 100), (255, 255, 255))
            img.save(f.name)
            results = self.detector.detect(f.name)
            self.assertIsInstance(results, list)
            Path(f.name).unlink()

    def test_detect_uniform_image(self):
        """Test that a uniform image has no detections."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :] = (128, 128, 128)
        results = self.detector.detect(img)
        self.assertEqual(len(results), 0)

    def test_detect_contrasting_regions(self):
        """Test detection with contrasting regions returns a list."""
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[:, :] = (255, 255, 255)
        img[50:150, 50:150] = (0, 0, 0)  # Black square
        detector = ObjectDetector(backend="builtin", confidence_threshold=0.01)
        results = detector.detect(img)
        self.assertIsInstance(results, list)

    def test_bounding_box(self):
        """Test BoundingBox properties."""
        from apex_os_bp.vision.object_detection import BoundingBox

        bbox = BoundingBox(x_min=0.1, y_min=0.2, x_max=0.5, y_max=0.8)
        self.assertAlmostEqual(bbox.width, 0.4)
        self.assertAlmostEqual(bbox.height, 0.6)
        self.assertAlmostEqual(bbox.area, 0.24)
        self.assertEqual(bbox.center, (0.3, 0.5))

    def test_bounding_box_iou(self):
        """Test IoU calculation."""
        from apex_os_bp.vision.object_detection import BoundingBox

        box1 = BoundingBox(0.0, 0.0, 1.0, 1.0)
        box2 = BoundingBox(0.5, 0.5, 1.5, 1.5)
        iou = box1.iou(box2)
        self.assertGreater(iou, 0.0)
        self.assertLess(iou, 1.0)

        # Identical boxes
        box3 = BoundingBox(0.0, 0.0, 1.0, 1.0)
        self.assertAlmostEqual(box1.iou(box3), 1.0)

        # Non-overlapping
        box4 = BoundingBox(2.0, 2.0, 3.0, 3.0)
        self.assertEqual(box1.iou(box4), 0.0)

    def test_detection_result_to_dict(self):
        """Test DetectionResult serialization."""
        from apex_os_bp.vision.object_detection import BoundingBox

        result = DetectionResult(
            label="test",
            confidence=0.9,
            bbox=BoundingBox(0.1, 0.1, 0.5, 0.5),
        )
        d = result.to_dict()
        self.assertEqual(d["label"], "test")
        self.assertEqual(d["confidence"], 0.9)
        self.assertIn("bbox", d)

    def test_batch_detect(self):
        """Test batch detection."""
        images = [
            np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8) for _ in range(3)
        ]
        results = self.detector.batch_detect(images)
        self.assertEqual(len(results), 3)

    def test_active_backend(self):
        """Test that active backend is reported."""
        self.assertEqual(self.detector.active_backend, "builtin")

    def test_confidence_threshold(self):
        """Test that confidence threshold filters results."""
        detector = ObjectDetector(backend="builtin", confidence_threshold=0.99)
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[:, :] = (255, 255, 255)
        img[50:150, 50:150] = (0, 0, 0)
        results = detector.detect(img)
        for r in results:
            self.assertGreaterEqual(r.confidence, 0.99)


class TestOCREngine(unittest.TestCase):
    """Tests for the OCR module."""

    def setUp(self):
        self.ocr = OCREngine()

    def test_extract_text_returns_result(self):
        """Test that extract_text returns an OCRResult."""
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = self.ocr.extract_text(img)
        self.assertIsInstance(result, OCRResult)

    def test_extract_text_with_pil_image(self):
        """Test OCR with PIL Image input."""
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        result = self.ocr.extract_text(img)
        self.assertIsInstance(result, OCRResult)

    def test_extract_text_with_file_path(self):
        """Test OCR with file path input."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 100), (255, 255, 255))
            img.save(f.name)
            result = self.ocr.extract_text(f.name)
            self.assertIsInstance(result, OCRResult)
            Path(f.name).unlink()

    def test_ocr_result_properties(self):
        """Test OCRResult helper properties."""
        result = OCRResult(text="Hello world\nTest line", confidence=0.9)
        self.assertEqual(result.word_count, 4)
        self.assertEqual(result.line_count, 2)

    def test_ocr_extract_emails(self):
        """Test email extraction from OCR result."""
        result = OCRResult(text="Contact us at test@example.com", confidence=0.9)
        emails = result.extract_emails()
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0], "test@example.com")

    def test_ocr_extract_urls(self):
        """Test URL extraction from OCR result."""
        result = OCRResult(text="Visit https://example.com for more", confidence=0.9)
        urls = result.extract_urls()
        self.assertEqual(len(urls), 1)

    def test_ocr_extract_dates(self):
        """Test date extraction from OCR result."""
        result = OCRResult(text="Meeting on 12/25/2024", confidence=0.9)
        dates = result.extract_dates()
        self.assertGreater(len(dates), 0)

    def test_ocr_extract_phone_numbers(self):
        """Test phone number extraction from OCR result."""
        result = OCRResult(text="Call +1-555-123-4567", confidence=0.9)
        phones = result.extract_phone_numbers()
        self.assertGreater(len(phones), 0)

    def test_ocr_search(self):
        """Test regex search in OCR result."""
        result = OCRResult(text="The quick brown fox", confidence=0.9)
        matches = result.search(r"brown")
        self.assertEqual(len(matches), 1)

    def test_ocr_to_dict(self):
        """Test OCRResult serialization."""
        result = OCRResult(text="test", confidence=0.5)
        d = result.to_dict()
        self.assertIn("text", d)
        self.assertIn("confidence", d)
        self.assertIn("blocks", d)

    def test_batch_extract(self):
        """Test batch OCR."""
        images = [
            np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8) for _ in range(3)
        ]
        results = self.ocr.batch_extract(images)
        self.assertEqual(len(results), 3)

    def test_tesseract_availability(self):
        """Test that tesseract availability is reported."""
        self.assertIsInstance(self.ocr.tesseract_available, bool)


class TestFaceRecognition(unittest.TestCase):
    """Tests for the face recognition module."""

    def setUp(self):
        self.fr = FaceRecognition()

    def test_detect_faces_returns_list(self):
        """Test that detect_faces returns a list."""
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        results = self.fr.detect_faces(img)
        self.assertIsInstance(results, list)

    def test_detect_faces_with_pil_image(self):
        """Test face detection with PIL Image input."""
        img = Image.new("RGB", (100, 100), (255, 220, 177))  # Skin tone
        results = self.fr.detect_faces(img)
        self.assertIsInstance(results, list)

    def test_detect_faces_with_file_path(self):
        """Test face detection with file path input."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 100), (255, 220, 177))
            img.save(f.name)
            results = self.fr.detect_faces(f.name)
            self.assertIsInstance(results, list)
            Path(f.name).unlink()

    def test_face_result_properties(self):
        """Test FaceResult properties."""
        face = FaceResult(
            face_id="abc123",
            bbox=(10, 50, 60, 20),
            confidence=0.9,
        )
        self.assertEqual(face.center, (35, 35))
        self.assertEqual(face.area, 1500)

    def test_face_result_to_dict(self):
        """Test FaceResult serialization."""
        face = FaceResult(face_id="abc123", bbox=(10, 50, 60, 20), confidence=0.9)
        d = face.to_dict()
        self.assertEqual(d["face_id"], "abc123")
        self.assertIn("bbox", d)

    def test_register_face(self):
        """Test face registration."""
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        face_id = self.fr.register_face("test_person", img)
        # May or may not detect a face depending on backend
        if face_id:
            self.assertIn("test_person", self.fr.get_known_faces())

    def test_recognize_faces(self):
        """Test face recognition against registered faces."""
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        results = self.fr.recognize_faces(img)
        self.assertIsInstance(results, list)

    def test_compare_faces(self):
        """Test face comparison between two images."""
        img1 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        img2 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = self.fr.compare_faces(img1, img2)
        self.assertIn("match", result)
        self.assertIsInstance(result["match"], bool)

    def test_remove_face(self):
        """Test face removal."""
        fr = FaceRecognition()
        # Force builtin backend for reliable testing
        fr._face_recognition_available = False
        fr._cv2_available = False

        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[:, :] = (255, 220, 177)  # Skin tone
        face_id = fr.register_face("temp_person", img)
        self.assertIsNotNone(face_id)
        removed = fr.remove_face("temp_person")
        self.assertTrue(removed)
        self.assertNotIn("temp_person", fr.get_known_faces())

    def test_remove_nonexistent_face(self):
        """Test removing a face that doesn't exist."""
        removed = self.fr.remove_face("nonexistent")
        self.assertFalse(removed)

    def test_get_known_faces(self):
        """Test getting list of known faces."""
        faces = self.fr.get_known_faces()
        self.assertIsInstance(faces, list)

    def test_backend_property(self):
        """Test that backend is reported."""
        self.assertIn(self.fr.backend, ["face_recognition", "opencv_haar", "builtin"])

    def test_detect_skin_tone_image(self):
        """Test detection on a skin-tone colored image."""
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[:, :] = (255, 220, 177)  # Skin tone
        results = self.fr.detect_faces(img)
        self.assertIsInstance(results, list)


class TestImageGeneration(unittest.TestCase):
    """Tests for the image generation module."""

    def setUp(self):
        self.gen = ImageGenerator(mode="procedural", seed=42)

    def test_generate_returns_result(self):
        """Test that generate returns a GenerationResult."""
        result = self.gen.generate(100, 100)
        self.assertIsInstance(result, GenerationResult)
        self.assertEqual(result.width, 100)
        self.assertEqual(result.height, 100)

    def test_generate_with_prompt(self):
        """Test generation with a text prompt."""
        result = self.gen.generate(100, 100, prompt="blue gradient")
        self.assertIsInstance(result, GenerationResult)

    def test_generate_gradient(self):
        """Test gradient generation."""
        result = self.gen.generate(100, 100, prompt="gradient")
        self.assertIsInstance(result.image, Image.Image)
        self.assertEqual(result.image.size, (100, 100))

    def test_generate_noise(self):
        """Test noise generation."""
        result = self.gen.generate(100, 100, prompt="noise")
        self.assertIsInstance(result, GenerationResult)

    def test_generate_pattern(self):
        """Test pattern generation."""
        result = self.gen.generate(100, 100, prompt="pattern")
        self.assertIsInstance(result, GenerationResult)

    def test_generate_shapes(self):
        """Test shape generation."""
        result = self.gen.generate(100, 100, prompt="geometric shapes")
        self.assertIsInstance(result, GenerationResult)

    def test_generate_text_image(self):
        """Test text image generation."""
        result = self.gen.generate(200, 100, prompt="text Hello World")
        self.assertIsInstance(result, GenerationResult)

    def test_generate_landscape(self):
        """Test landscape generation."""
        result = self.gen.generate(200, 150, prompt="landscape mountain")
        self.assertIsInstance(result, GenerationResult)

    def test_generate_abstract(self):
        """Test abstract art generation."""
        result = self.gen.generate(100, 100, prompt="abstract")
        self.assertIsInstance(result, GenerationResult)

    def test_generate_deterministic_with_seed(self):
        """Test that same seed produces same image."""
        gen1 = ImageGenerator(mode="procedural", seed=42)
        gen2 = ImageGenerator(mode="procedural", seed=42)
        result1 = gen1.generate(50, 50, prompt="gradient")
        result2 = gen2.generate(50, 50, prompt="gradient")
        arr1 = np.array(result1.image)
        arr2 = np.array(result2.image)
        np.testing.assert_array_equal(arr1, arr2)

    def test_generate_different_seeds(self):
        """Test that different seeds produce different images."""
        gen1 = ImageGenerator(mode="procedural", seed=42)
        gen2 = ImageGenerator(mode="procedural", seed=99)
        result1 = gen1.generate(50, 50, prompt="noise")
        result2 = gen2.generate(50, 50, prompt="noise")
        arr1 = np.array(result1.image)
        arr2 = np.array(result2.image)
        self.assertFalse(np.array_equal(arr1, arr2))

    def test_save_image(self):
        """Test saving generated image."""
        result = self.gen.generate(50, 50)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = result.save(f.name)
            self.assertTrue(Path(path).exists())
            self.assertGreater(Path(path).stat().st_size, 0)
            Path(path).unlink()

    def test_to_array(self):
        """Test conversion to numpy array."""
        result = self.gen.generate(50, 50)
        arr = result.to_array()
        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(arr.shape, (50, 50, 3))

    def test_generate_thumbnail(self):
        """Test thumbnail generation."""
        img = Image.new("RGB", (200, 200), (128, 128, 128))
        result = self.gen.generate_thumbnail(img, (64, 64))
        self.assertEqual(result.width, 64)
        self.assertEqual(result.height, 64)

    def test_generate_avatar(self):
        """Test avatar generation."""
        result = self.gen.generate_avatar("John Doe", size=128)
        self.assertEqual(result.width, 128)
        self.assertEqual(result.height, 128)
        self.assertIsInstance(result.image, Image.Image)

    def test_generate_avatar_deterministic(self):
        """Test that avatar generation is deterministic."""
        result1 = self.gen.generate_avatar("John Doe", size=64)
        result2 = self.gen.generate_avatar("John Doe", size=64)
        arr1 = np.array(result1.image)
        arr2 = np.array(result2.image)
        np.testing.assert_array_equal(arr1, arr2)

    def test_generate_avatar_different_names(self):
        """Test that different names produce different avatars."""
        result1 = self.gen.generate_avatar("Alice", size=64)
        result2 = self.gen.generate_avatar("Bob", size=64)
        arr1 = np.array(result1.image)
        arr2 = np.array(result2.image)
        self.assertFalse(np.array_equal(arr1, arr2))

    def test_size_property(self):
        """Test GenerationResult size property."""
        result = self.gen.generate(80, 60)
        self.assertEqual(result.size, (80, 60))

    def test_diffusers_availability(self):
        """Test that diffusers availability is reported."""
        self.assertIsInstance(self.gen.diffusers_available, bool)


class TestVisionIntegration(unittest.TestCase):
    """Integration tests for the vision system."""

    def test_full_pipeline(self):
        """Test a full vision pipeline: generate -> recognize -> detect."""
        gen = ImageGenerator(mode="procedural", seed=42)
        result = gen.generate(200, 200, prompt="blue gradient")

        # Recognize
        recognizer = ImageRecognition(backend="builtin")
        rec_result = recognizer.recognize(result.image)
        self.assertIsInstance(rec_result, RecognitionResult)

        # Detect
        detector = ObjectDetector(backend="builtin", confidence_threshold=0.01)
        det_results = detector.detect(result.image)
        self.assertIsInstance(det_results, list)

    def test_all_backends_builtin(self):
        """Test that all modules work with builtin backends."""
        recognizer = ImageRecognition(backend="builtin")
        detector = ObjectDetector(backend="builtin")
        ocr = OCREngine()
        fr = FaceRecognition()
        gen = ImageGenerator(mode="procedural")

        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        self.assertIsInstance(recognizer.recognize(img), RecognitionResult)
        self.assertIsInstance(detector.detect(img), list)
        self.assertIsInstance(ocr.extract_text(img), OCRResult)
        self.assertIsInstance(fr.detect_faces(img), list)
        self.assertIsInstance(gen.generate(50, 50), GenerationResult)


if __name__ == "__main__":
    unittest.main()
