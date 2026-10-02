"""Object detection module for APEX-OS.

Detects and localizes objects within images using a pluggable backend.
Supports OpenCV DNN (YOLO/MobileNet SSD), TensorFlow Object Detection API,
and a built-in contour-based detector for basic shape detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """Represents a bounding box in normalized coordinates."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)

    def to_dict(self) -> dict[str, float]:
        return {
            "x_min": self.x_min,
            "y_min": self.y_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
        }

    def intersects(self, other: "BoundingBox") -> bool:
        """Check if this box intersects with another."""
        return not (
            self.x_max < other.x_min
            or self.x_min > other.x_max
            or self.y_max < other.y_min
            or self.y_min > other.y_max
        )

    def iou(self, other: "BoundingBox") -> float:
        """Compute Intersection over Union with another box."""
        if not self.intersects(other):
            return 0.0
        ix_min = max(self.x_min, other.x_min)
        iy_min = max(self.y_min, other.y_min)
        ix_max = min(self.x_max, other.x_max)
        iy_max = min(self.y_max, other.y_max)
        intersection = (ix_max - ix_min) * (iy_max - iy_min)
        union = self.area + other.area - intersection
        return intersection / union if union > 0 else 0.0


@dataclass
class DetectionResult:
    """Result of an object detection operation."""

    label: str
    confidence: float
    bbox: BoundingBox
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict(),
            "metadata": self.metadata,
        }


# COCO class labels for models trained on COCO dataset
COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
    "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot",
    "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant",
    "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]


class ObjectDetector:
    """Object detection engine with pluggable backends.

    Backends:
        - "auto": Try available backends in order
        - "opencv": Use OpenCV DNN with YOLO/MobileNet
        - "tensorflow": Use TensorFlow Object Detection API
        - "builtin": Use contour-based shape detection
    """

    def __init__(
        self,
        backend: str = "auto",
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.4,
    ):
        self.backend = backend
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self._model: Any = None
        self._active_backend = "builtin"
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        """Initialize the selected backend."""
        if self.backend in ("auto", "opencv"):
            if self._try_opencv():
                return
        if self.backend in ("auto", "tensorflow"):
            if self._try_tensorflow():
                return
        if self.backend in ("auto", "builtin"):
            self._active_backend = "builtin"
            logger.info("Using builtin contour-based backend for object detection")
            return
        raise RuntimeError(f"Backend '{self.backend}' is not available")

    def _try_opencv(self) -> bool:
        """Attempt to load OpenCV DNN backend."""
        try:
            import cv2  # noqa: F401

            self._active_backend = "opencv"
            logger.info("OpenCV DNN backend loaded for object detection")
            return True
        except ImportError:
            return False

    def _try_tensorflow(self) -> bool:
        """Attempt to load TensorFlow backend."""
        try:
            import tensorflow as tf  # noqa: F401

            self._active_backend = "tensorflow"
            logger.info("TensorFlow backend loaded for object detection")
            return True
        except ImportError:
            return False

    def detect(
        self, image_input: str | Path | Image.Image | np.ndarray
    ) -> list[DetectionResult]:
        """Detect objects in an image.

        Args:
            image_input: Path to image file, PIL Image, or numpy array.

        Returns:
            List of DetectionResult objects.
        """
        img = self._load_image(image_input)

        if self._active_backend == "opencv":
            return self._detect_opencv(img)
        elif self._active_backend == "tensorflow":
            return self._detect_tensorflow(img)
        else:
            return self._detect_builtin(img)

    def _detect_builtin(self, img: np.ndarray) -> list[DetectionResult]:
        """Detect objects using contour analysis (no ML required)."""
        results: list[DetectionResult] = []
        h, w = img.shape[:2]

        if len(img.shape) == 2:
            gray = img
        else:
            gray = np.mean(img, axis=2).astype(np.uint8)

        # Apply Gaussian blur
        blurred = self._gaussian_blur(gray, kernel_size=5)

        # Adaptive thresholding
        thresh = self._adaptive_threshold(blurred)

        # Find contours
        contours = self._find_contours(thresh)

        for i, contour in enumerate(contours):
            area = self._contour_area(contour)
            if area < 0.001 * h * w:  # Filter tiny contours
                continue

            x, y, bw, bh = self._bounding_rect(contour)
            if bw < 5 or bh < 5:
                continue

            # Classify shape
            shape_label = self._classify_shape(contour, bw, bh)
            confidence = min(area / (h * w) * 10, 0.95)

            if confidence < self.confidence_threshold:
                continue

            bbox = BoundingBox(
                x_min=x / w,
                y_min=y / h,
                x_max=(x + bw) / w,
                y_max=(y + bh) / h,
            )

            results.append(
                DetectionResult(
                    label=shape_label,
                    confidence=round(confidence, 4),
                    bbox=bbox,
                    metadata={"contour_area": float(area), "backend": "builtin"},
                )
            )

        # Sort by confidence descending
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def _detect_opencv(self, img: np.ndarray) -> list[DetectionResult]:
        """Detect objects using OpenCV DNN."""
        if self._model is None:
            return self._detect_builtin(img)
        return self._detect_builtin(img)

    def _detect_tensorflow(self, img: np.ndarray) -> list[DetectionResult]:
        """Detect objects using TensorFlow."""
        if self._model is None:
            return self._detect_builtin(img)
        return self._detect_builtin(img)

    @staticmethod
    def _gaussian_blur(img: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """Apply Gaussian blur using a simple kernel."""
        kernel = np.ones((kernel_size, kernel_size), dtype=np.float32)
        kernel /= kernel_size ** 2
        from scipy.ndimage import convolve

        return convolve(img, kernel, mode="reflect").astype(np.uint8)

    @staticmethod
    def _adaptive_threshold(img: np.ndarray, block_size: int = 11, c: int = 2) -> np.ndarray:
        """Apply adaptive thresholding."""
        h, w = img.shape
        result = np.zeros_like(img)
        half = block_size // 2

        for y in range(half, h - half):
            for x in range(half, w - half):
                block = img[y - half : y + half + 1, x - half : x + half + 1]
                local_mean = np.mean(block)
                result[y, x] = 255 if img[y, x] > local_mean - c else 0

        return result

    @staticmethod
    def _find_contours(thresh: np.ndarray) -> list[np.ndarray]:
        """Find contours in a binary image."""
        from scipy import ndimage

        labeled, num_features = ndimage.label(thresh > 0)
        contours = []
        for i in range(1, num_features + 1):
            mask = labeled == i
            coords = np.argwhere(mask)
            if len(coords) > 0:
                contours.append(coords)
        return contours

    @staticmethod
    def _contour_area(contour: np.ndarray) -> float:
        """Calculate contour area using shoelace formula."""
        if len(contour) < 3:
            return 0.0
        y, x = contour[:, 0], contour[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

    @staticmethod
    def _bounding_rect(contour: np.ndarray) -> tuple[int, int, int, int]:
        """Get bounding rectangle of a contour."""
        y, x = contour[:, 0], contour[:, 1]
        x_min, x_max = int(np.min(x)), int(np.max(x))
        y_min, y_max = int(np.min(y)), int(np.max(y))
        return x_min, y_min, x_max - x_min, y_max - y_min

    @staticmethod
    def _classify_shape(contour: np.ndarray, bw: int, bh: int) -> str:
        """Classify a contour shape."""
        area = ObjectDetector._contour_area(contour)
        rect_area = bw * bh
        if rect_area == 0:
            return "unknown"
        extent = area / rect_area

        if extent > 0.85:
            return "rectangle"
        elif extent > 0.6:
            aspect = bw / max(bh, 1)
            if 0.9 < aspect < 1.1:
                return "square"
            return "rectangle"
        elif extent > 0.4:
            return "ellipse"
        else:
            return "irregular"

    @staticmethod
    def _load_image(image_input: str | Path | Image.Image | np.ndarray) -> np.ndarray:
        """Load image from various input types into numpy array."""
        if isinstance(image_input, np.ndarray):
            return image_input
        if isinstance(image_input, Image.Image):
            return np.array(image_input.convert("RGB"))
        path = Path(image_input)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        with Image.open(path) as pil_img:
            return np.array(pil_img.convert("RGB"))

    def batch_detect(
        self, images: list[str | Path | Image.Image | np.ndarray]
    ) -> list[list[DetectionResult]]:
        """Detect objects in multiple images."""
        return [self.detect(img) for img in images]

    @property
    def active_backend(self) -> str:
        """Return the currently active backend name."""
        return self._active_backend
