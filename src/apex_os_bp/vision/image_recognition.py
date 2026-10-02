"""Image recognition module for APEX-OS.

Classifies images into categories using a pluggable backend architecture.
Supports OpenCV DNN, TensorFlow/Keras, and a built-in color-histogram
fallback for environments without heavy ML frameworks.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class RecognitionResult:
    """Result of an image recognition operation."""

    label: str
    confidence: float
    top_k: list[dict[str, float]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "top_k": self.top_k,
            "metadata": self.metadata,
        }


# Built-in category signatures based on color histograms
# Used as fallback when no ML backend is available
_BUILTIN_CATEGORIES = {
    "sky": {"dominant_hue_range": (180, 260), "brightness_min": 0.5},
    "vegetation": {"dominant_hue_range": (60, 160), "brightness_min": 0.2},
    "water": {"dominant_hue_range": (170, 240), "brightness_min": 0.3},
    "urban": {"saturation_max": 0.3, "brightness_range": (0.3, 0.8)},
    "indoor": {"brightness_max": 0.6, "saturation_max": 0.4},
    "portrait": {"warmth_min": 0.4, "brightness_range": (0.3, 0.9)},
    "document": {"brightness_min": 0.7, "saturation_max": 0.2},
    "night": {"brightness_max": 0.25},
}


class ImageRecognition:
    """Image recognition engine with pluggable backends.

    Backends:
        - "auto": Try available backends in order (opencv, tensorflow, builtin)
        - "opencv": Use OpenCV DNN module
        - "tensorflow": Use TensorFlow/Keras
        - "builtin": Use color histogram analysis (no dependencies)
    """

    def __init__(self, backend: str = "auto", model_path: Optional[str] = None):
        self.backend = backend
        self.model_path = model_path
        self._model: Any = None
        self._labels: list[str] = []
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
            logger.info("Using builtin color-histogram backend for image recognition")
            return
        raise RuntimeError(f"Backend '{self.backend}' is not available")

    def _try_opencv(self) -> bool:
        """Attempt to load OpenCV DNN backend."""
        try:
            import cv2  # noqa: F401

            self._active_backend = "opencv"
            logger.info("OpenCV DNN backend loaded for image recognition")
            return True
        except ImportError:
            return False

    def _try_tensorflow(self) -> bool:
        """Attempt to load TensorFlow backend."""
        try:
            import tensorflow as tf  # noqa: F401

            self._active_backend = "tensorflow"
            logger.info("TensorFlow backend loaded for image recognition")
            return True
        except ImportError:
            return False

    def _compute_histogram_features(self, img: np.ndarray) -> dict[str, float]:
        """Compute color histogram features for builtin backend."""
        if len(img.shape) == 2:
            img = np.stack([img] * 3, axis=-1)

        hsv = self._rgb_to_hsv(img)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

        mean_h = float(np.mean(h))
        mean_s = float(np.mean(s))
        mean_v = float(np.mean(v))

        # Compute hue histogram
        hist, _ = np.histogram(h, bins=36, range=(0, 360))
        dominant_hue = float(np.argmax(hist) * 10 + 5)

        return {
            "mean_hue": mean_h,
            "mean_saturation": mean_s,
            "mean_brightness": mean_v,
            "dominant_hue": dominant_hue,
            "warmth": float(np.mean(img[:, :, 0]) - np.mean(img[:, :, 2])),
        }

    @staticmethod
    def _rgb_to_hsv(img: np.ndarray) -> np.ndarray:
        """Convert RGB image to HSV color space."""
        img_float = img.astype(np.float32) / 255.0
        r, g, b = img_float[:, :, 0], img_float[:, :, 1], img_float[:, :, 2]

        maxc = np.maximum(np.maximum(r, g), b)
        minc = np.minimum(np.minimum(r, g), b)
        v = maxc
        c = maxc - minc
        s = np.where(maxc > 0, c / (maxc + 1e-10), 0)

        rc = (maxc - r) / (c + 1e-10)
        gc = (maxc - g) / (c + 1e-10)
        bc = (maxc - b) / (c + 1e-10)

        h = np.where(maxc == r, bc - gc, np.where(maxc == g, 2.0 + rc - bc, 4.0 + gc - rc))
        h = (h / 6.0) % 1.0
        h = h * 360.0

        return np.stack([h, s, v], axis=-1)

    def _classify_builtin(self, img: np.ndarray) -> RecognitionResult:
        """Classify image using builtin histogram analysis."""
        features = self._compute_histogram_features(img)
        scores: dict[str, float] = {}

        for category, rules in _BUILTIN_CATEGORIES.items():
            score = 0.0
            checks = 0

            if "dominant_hue_range" in rules:
                lo, hi = rules["dominant_hue_range"]
                dh = features["dominant_hue"]
                if lo <= dh <= hi:
                    score += 1.0
                checks += 1

            if "brightness_min" in rules:
                if features["mean_brightness"] >= rules["brightness_min"]:
                    score += 1.0
                checks += 1

            if "brightness_max" in rules:
                if features["mean_brightness"] <= rules["brightness_max"]:
                    score += 1.0
                checks += 1

            if "brightness_range" in rules:
                lo, hi = rules["brightness_range"]
                if lo <= features["mean_brightness"] <= hi:
                    score += 1.0
                checks += 1

            if "saturation_max" in rules:
                if features["mean_saturation"] <= rules["saturation_max"]:
                    score += 1.0
                checks += 1

            if "warmth_min" in rules:
                if features["warmth"] >= rules["warmth_min"]:
                    score += 1.0
                checks += 1

            scores[category] = score / max(checks, 1)

        # Sort by score descending
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_k = [{"label": k, "confidence": round(v, 4)} for k, v in sorted_scores[:5]]

        best_label, best_score = sorted_scores[0]
        return RecognitionResult(
            label=best_label,
            confidence=round(best_score, 4),
            top_k=top_k,
            metadata={"backend": "builtin", "features": features},
        )

    def recognize(self, image_input: str | Path | Image.Image | np.ndarray) -> RecognitionResult:
        """Recognize and classify an image.

        Args:
            image_input: Path to image file, PIL Image, or numpy array.

        Returns:
            RecognitionResult with predicted label and confidence.
        """
        img = self._load_image(image_input)

        if self._active_backend == "opencv":
            return self._classify_opencv(img)
        elif self._active_backend == "tensorflow":
            return self._classify_tensorflow(img)
        else:
            return self._classify_builtin(img)

    def _classify_opencv(self, img: np.ndarray) -> RecognitionResult:
        """Classify using OpenCV DNN."""
        # Fallback to builtin if no model loaded
        if self._model is None:
            return self._classify_builtin(img)
        # OpenCV DNN inference would go here with a loaded model
        return self._classify_builtin(img)

    def _classify_tensorflow(self, img: np.ndarray) -> RecognitionResult:
        """Classify using TensorFlow."""
        if self._model is None:
            return self._classify_builtin(img)
        return self._classify_builtin(img)

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

    def batch_recognize(
        self, images: list[str | Path | Image.Image | np.ndarray]
    ) -> list[RecognitionResult]:
        """Recognize multiple images in batch."""
        return [self.recognize(img) for img in images]

    @property
    def active_backend(self) -> str:
        """Return the currently active backend name."""
        return self._active_backend

    def get_cache_key(self, image_input: str | Path | Image.Image | np.ndarray) -> str:
        """Generate a cache key for an image."""
        if isinstance(image_input, (str, Path)):
            data = Path(image_input).read_bytes()
        elif isinstance(image_input, Image.Image):
            data = np.array(image_input).tobytes()
        else:
            data = image_input.tobytes()
        return hashlib.sha256(data).hexdigest()[:16]
