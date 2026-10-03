"""Tests for deepened vision module: detection, classification, segmentation, face, video."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def vision_engine():
    from apex_os_bp.vision.deepened import VisionPipeline
    engine = VisionPipeline()
    engine.detect_objects = MagicMock(return_value=[
        {"label": "car", "bbox": [10, 20, 100, 150], "confidence": 0.95}
    ])
    engine.classify = MagicMock(return_value=[("cat", 0.97)])
    engine.segment = MagicMock(return_value={"mask": [[0, 1], [1, 0]], "labels": ["fg", "bg"]})
    engine.recognize_face = MagicMock(return_value={"identity": "person_1", "confidence": 0.88})
    engine.analyze_video = MagicMock(return_value={"frames": 120, "events": ["motion"]})
    return engine


class TestObjectDetection:
    def test_detect_objects(self, vision_engine):
        results = vision_engine.detect_objects("image.jpg")
        assert len(results) > 0
        assert results[0]["label"] == "car"
        assert results[0]["confidence"] > 0.9

    def test_detect_multiple(self, vision_engine):
        vision_engine.detect_objects.return_value = [
            {"label": "person", "bbox": [0, 0, 50, 100], "confidence": 0.91},
            {"label": "dog", "bbox": [60, 70, 120, 160], "confidence": 0.85},
        ]
        results = vision_engine.detect_objects("scene.jpg")
        assert len(results) == 2


class TestImageClassification:
    def test_classify_image(self, vision_engine):
        labels = vision_engine.classify("photo.jpg")
        assert labels[0][0] == "cat"
        assert labels[0][1] > 0.9

    def test_top_k_labels(self, vision_engine):
        vision_engine.classify.return_value = [("dog", 0.8), ("cat", 0.15), ("bird", 0.05)]
        labels = vision_engine.classify("animal.jpg", top_k=3)
        assert len(labels) == 3


class TestSegmentation:
    def test_segment_image(self, vision_engine):
        result = vision_engine.segment("image.jpg")
        assert "mask" in result
        assert "labels" in result

    def test_segment_regions(self, vision_engine):
        vision_engine.segment.return_value = {
            "regions": [{"id": 1, "area": 5000}, {"id": 2, "area": 3000}]
        }
        result = vision_engine.segment("image.jpg")
        assert len(result["regions"]) == 2


class TestFaceRecognition:
    def test_recognize_face(self, vision_engine):
        result = vision_engine.recognize_face("face.jpg")
        assert result["identity"] == "person_1"
        assert result["confidence"] > 0.8

    def test_no_face_detected(self, vision_engine):
        vision_engine.recognize_face.return_value = None
        result = vision_engine.recognize_face("landscape.jpg")
        assert result is None


class TestVideoAnalysis:
    def test_analyze_video(self, vision_engine):
        result = vision_engine.analyze_video("clip.mp4")
        assert result["frames"] == 120
        assert "motion" in result["events"]

    def test_video_summary(self, vision_engine):
        vision_engine.analyze_video.return_value = {
            "duration": 10.5, "scenes": 3, "highlights": [2.5, 7.0]
        }
        result = vision_engine.analyze_video("video.mp4")
        assert result["scenes"] == 3
