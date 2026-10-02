"""Face recognition module for APEX-OS.

Detects, encodes, and matches faces in images using the face_recognition
library with a built-in fallback using OpenCV Haar cascades.
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
class FaceResult:
    """Result of a face detection/recognition operation."""

    face_id: str
    bbox: tuple[int, int, int, int]  # (top, right, bottom, left)
    encoding: Optional[np.ndarray] = None
    confidence: float = 0.0
    landmarks: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "face_id": self.face_id,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "landmarks": self.landmarks,
            "metadata": self.metadata,
        }

    @property
    def center(self) -> tuple[int, int]:
        top, right, bottom, left = self.bbox
        return ((left + right) // 2, (top + bottom) // 2)

    @property
    def area(self) -> int:
        top, right, bottom, left = self.bbox
        return (bottom - top) * (right - left)


class FaceRecognition:
    """Face detection and recognition engine.

    Uses the face_recognition library (dlib-based) when available,
    falling back to OpenCV Haar cascades for basic detection.
    """

    def __init__(self, tolerance: float = 0.6, model: str = "hog"):
        self.tolerance = tolerance
        self.model = model
        self._known_faces: dict[str, np.ndarray] = {}
        self._face_recognition_available = self._check_face_recognition()
        self._cv2_available = self._check_opencv()

    @staticmethod
    def _check_face_recognition() -> bool:
        """Check if face_recognition library is available."""
        try:
            import face_recognition  # noqa: F401

            return True
        except ImportError:
            logger.warning("face_recognition not available, using OpenCV fallback")
            return False

    @staticmethod
    def _check_opencv() -> bool:
        """Check if OpenCV is available."""
        try:
            import cv2  # noqa: F401

            return True
        except ImportError:
            return False

    def detect_faces(
        self, image_input: str | Path | Image.Image | np.ndarray
    ) -> list[FaceResult]:
        """Detect faces in an image.

        Args:
            image_input: Path to image file, PIL Image, or numpy array.

        Returns:
            List of FaceResult objects for each detected face.
        """
        img = self._load_image(image_input)

        if self._face_recognition_available:
            return self._detect_with_face_recognition(img)
        elif self._cv2_available:
            return self._detect_with_opencv(img)
        else:
            return self._detect_builtin(img)

    def _detect_with_face_recognition(self, img: np.ndarray) -> list[FaceResult]:
        """Detect faces using face_recognition library."""
        import face_recognition

        # face_recognition expects RGB
        if len(img.shape) == 2:
            img = np.stack([img] * 3, axis=-1)

        face_locations = face_recognition.face_locations(img, model=self.model)
        face_encodings = face_recognition.face_encodings(img, face_locations)
        face_landmarks = face_recognition.face_landmarks(img, face_locations)

        results: list[FaceResult] = []
        for i, (location, encoding, landmarks) in enumerate(
            zip(face_locations, face_encodings, face_landmarks)
        ):
            top, right, bottom, left = location
            face_id = hashlib.sha256(encoding.tobytes()).hexdigest()[:16]

            results.append(
                FaceResult(
                    face_id=face_id,
                    bbox=(top, right, bottom, left),
                    encoding=encoding,
                    confidence=0.95,
                    landmarks=landmarks,
                    metadata={"model": self.model, "index": i},
                )
            )

        return results

    def _detect_with_opencv(self, img: np.ndarray) -> list[FaceResult]:
        """Detect faces using OpenCV Haar cascades."""
        import cv2

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)

        detections = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        results: list[FaceResult] = []
        for i, (x, y, w, h) in enumerate(detections):
            face_img = img[y : y + h, x : x + w]
            face_id = hashlib.sha256(face_img.tobytes()).hexdigest()[:16]

            results.append(
                FaceResult(
                    face_id=face_id,
                    bbox=(y, x + w, y + h, x),
                    confidence=0.7,
                    landmarks={},
                    metadata={"model": "haar_cascade", "index": i},
                )
            )

        return results

    def _detect_builtin(self, img: np.ndarray) -> list[FaceResult]:
        """Builtin face detection using skin-tone analysis."""
        if len(img.shape) == 2:
            return []

        h, w = img.shape[:2]
        results: list[FaceResult] = []

        # Simple skin-tone detection in YCbCr space
        ycbcr = self._rgb_to_ycbcr(img)
        cb = ycbcr[:, :, 1]
        cr = ycbcr[:, :, 2]

        # Skin tone range in YCbCr
        skin_mask = (cb >= 77) & (cb <= 127) & (cr >= 133) & (cr <= 173)

        # Find connected regions
        from scipy import ndimage

        labeled, num_features = ndimage.label(skin_mask)

        for i in range(1, num_features + 1):
            region = labeled == i
            area = np.sum(region)
            min_area = 0.005 * h * w

            if area < min_area:
                continue

            coords = np.argwhere(region)
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)

            # Filter by aspect ratio (faces are roughly oval)
            bw = x_max - x_min
            bh = y_max - y_min
            if bw == 0 or bh == 0:
                continue
            aspect = bw / bh
            if not (0.5 < aspect < 2.0):
                continue

            face_img = img[y_min:y_max, x_min:x_max]
            face_id = hashlib.sha256(face_img.tobytes()).hexdigest()[:16]

            results.append(
                FaceResult(
                    face_id=face_id,
                    bbox=(int(y_min), int(x_max), int(y_max), int(x_min)),
                    confidence=0.4,
                    landmarks={},
                    metadata={"model": "builtin_skin_tone", "skin_area": int(area)},
                )
            )

        return results

    @staticmethod
    def _rgb_to_ycbcr(img: np.ndarray) -> np.ndarray:
        """Convert RGB to YCbCr color space."""
        img_float = img.astype(np.float32)
        r, g, b = img_float[:, :, 0], img_float[:, :, 1], img_float[:, :, 2]

        y = 0.299 * r + 0.587 * g + 0.114 * b
        cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
        cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b

        return np.stack([y, cb, cr], axis=-1)

    def register_face(
        self,
        name: str,
        image_input: str | Path | Image.Image | np.ndarray,
    ) -> Optional[str]:
        """Register a known face for future matching.

        Args:
            name: Identifier for the person.
            image_input: Image containing the face.

        Returns:
            face_id if registration successful, None otherwise.
        """
        faces = self.detect_faces(image_input)
        if not faces:
            return None

        # Use the first (largest) face
        face = max(faces, key=lambda f: f.area)
        if face.encoding is not None:
            self._known_faces[name] = face.encoding
        else:
            # For backends without encoding, store a hash
            self._known_faces[name] = np.array([hash(face.face_id)])

        return face.face_id

    def recognize_faces(
        self, image_input: str | Path | Image.Image | np.ndarray
    ) -> list[dict[str, Any]]:
        """Detect faces and match against registered faces.

        Returns:
            List of dicts with face info and match results.
        """
        faces = self.detect_faces(image_input)
        results: list[dict[str, Any]] = []

        for face in faces:
            match_name: Optional[str] = None
            match_distance: Optional[float] = None

            if face.encoding is not None and self._known_faces:
                import face_recognition

                for name, known_encoding in self._known_faces.items():
                    if known_encoding.shape != face.encoding.shape:
                        continue
                    distance = float(
                        face_recognition.face_distance([known_encoding], face.encoding)[0]
                    )
                    if distance < self.tolerance:
                        match_name = name
                        match_distance = distance
                        break

            results.append(
                {
                    "face_id": face.face_id,
                    "bbox": face.bbox,
                    "confidence": face.confidence,
                    "match_name": match_name,
                    "match_distance": match_distance,
                    "is_known": match_name is not None,
                }
            )

        return results

    def compare_faces(
        self,
        image1: str | Path | Image.Image | np.ndarray,
        image2: str | Path | Image.Image | np.ndarray,
    ) -> dict[str, Any]:
        """Compare faces between two images.

        Returns:
            Dict with match result and distance metrics.
        """
        faces1 = self.detect_faces(image1)
        faces2 = self.detect_faces(image2)

        if not faces1 or not faces2:
            return {
                "match": False,
                "reason": "no_faces_detected",
                "faces_in_image1": len(faces1),
                "faces_in_image2": len(faces2),
            }

        face1 = max(faces1, key=lambda f: f.area)
        face2 = max(faces2, key=lambda f: f.area)

        if face1.encoding is not None and face2.encoding is not None:
            import face_recognition

            distance = float(
                face_recognition.face_distance([face1.encoding], face2.encoding)[0]
            )
            match = distance < self.tolerance
            return {
                "match": match,
                "distance": distance,
                "tolerance": self.tolerance,
                "face1_id": face1.face_id,
                "face2_id": face2.face_id,
            }
        else:
            # Fallback: compare face IDs (only works if same image)
            match = face1.face_id == face2.face_id
            return {
                "match": match,
                "distance": 0.0 if match else 1.0,
                "tolerance": self.tolerance,
                "face1_id": face1.face_id,
                "face2_id": face2.face_id,
                "note": "Using ID comparison (no encoding available)",
            }

    def get_known_faces(self) -> list[str]:
        """Return list of registered face names."""
        return list(self._known_faces.keys())

    def remove_face(self, name: str) -> bool:
        """Remove a registered face."""
        if name in self._known_faces:
            del self._known_faces[name]
            return True
        return False

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

    @property
    def backend(self) -> str:
        """Return the active backend name."""
        if self._face_recognition_available:
            return "face_recognition"
        elif self._cv2_available:
            return "opencv_haar"
        else:
            return "builtin"
