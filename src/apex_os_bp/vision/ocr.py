"""OCR (Optical Character Recognition) module for APEX-OS.

Extracts text from images using pytesseract with a built-in fallback
that uses basic image analysis for simple text detection.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of an OCR operation."""

    text: str
    confidence: float
    blocks: list[dict[str, Any]] = field(default_factory=list)
    language: str = "eng"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "blocks": self.blocks,
            "language": self.language,
            "metadata": self.metadata,
        }

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def line_count(self) -> int:
        return len([l for l in self.text.split("\n") if l.strip()])

    def search(self, pattern: str) -> list[str]:
        """Search for regex pattern in extracted text."""
        return re.findall(pattern, self.text, re.IGNORECASE)

    def extract_emails(self) -> list[str]:
        """Extract email addresses from text."""
        return self.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    def extract_phone_numbers(self) -> list[str]:
        """Extract phone numbers from text."""
        return self.search(r"[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}")

    def extract_urls(self) -> list[str]:
        """Extract URLs from text."""
        return self.search(r"https?://[^\s]+|www\.[^\s]+")

    def extract_dates(self) -> list[str]:
        """Extract dates in common formats."""
        patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            r"\d{4}[/-]\d{1,2}[/-]\d{1,2}",
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}",
        ]
        results = []
        for p in patterns:
            results.extend(self.search(p))
        return results


class OCREngine:
    """OCR engine with preprocessing and multi-language support.

    Uses pytesseract when available, with a built-in fallback for
    basic text region detection.
    """

    def __init__(
        self,
        language: str = "eng",
        preprocess: bool = True,
        psm_mode: int = 3,
    ):
        self.language = language
        self.preprocess = preprocess
        self.psm_mode = psm_mode
        self._tesseract_available = self._check_tesseract()

    @staticmethod
    def _check_tesseract() -> bool:
        """Check if pytesseract and tesseract binary are available."""
        try:
            import pytesseract  # noqa: F401

            # Try a minimal call to verify the binary works
            from PIL import Image

            test_img = Image.new("L", (10, 10), 255)
            pytesseract.image_to_string(test_img)
            return True
        except Exception:
            logger.warning("Tesseract not available, using builtin OCR fallback")
            return False

    def extract_text(
        self, image_input: str | Path | Image.Image | np.ndarray
    ) -> OCRResult:
        """Extract text from an image.

        Args:
            image_input: Path to image file, PIL Image, or numpy array.

        Returns:
            OCRResult with extracted text and metadata.
        """
        img = self._load_image(image_input)

        if self._tesseract_available:
            return self._extract_with_tesseract(img)
        else:
            return self._extract_builtin(img)

    def _extract_with_tesseract(self, img: np.ndarray) -> OCRResult:
        """Extract text using pytesseract."""
        import pytesseract

        pil_img = Image.fromarray(img)

        if self.preprocess:
            pil_img = self._preprocess_image(pil_img)

        try:
            data = pytesseract.image_to_data(
                pil_img,
                lang=self.language,
                config=f"--psm {self.psm_mode}",
                output_type=pytesseract.Output.DICT,
            )

            blocks: list[dict[str, Any]] = []
            text_parts: list[str] = []
            confidences: list[float] = []

            n = len(data["text"])
            for i in range(n):
                text = data["text"][i].strip()
                if not text:
                    continue
                conf = float(data["conf"][i])
                if conf > 0:
                    text_parts.append(text)
                    confidences.append(conf)
                    blocks.append(
                        {
                            "text": text,
                            "confidence": conf,
                            "bbox": {
                                "x": data["left"][i],
                                "y": data["top"][i],
                                "width": data["width"][i],
                                "height": data["height"][i],
                            },
                        }
                    )

            full_text = " ".join(text_parts)
            avg_conf = float(np.mean(confidences)) if confidences else 0.0

            return OCRResult(
                text=full_text,
                confidence=round(avg_conf / 100, 4),
                blocks=blocks,
                language=self.language,
                metadata={"engine": "tesseract", "psm": self.psm_mode},
            )
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return self._extract_builtin(img)

    def _extract_builtin(self, img: np.ndarray) -> OCRResult:
        """Builtin OCR fallback using image analysis."""
        if len(img.shape) == 3:
            gray = np.mean(img, axis=2).astype(np.uint8)
        else:
            gray = img

        h, w = gray.shape

        # Detect text-like regions (high horizontal variance)
        row_var = np.var(gray.astype(np.float32), axis=1)
        text_rows = row_var > np.mean(row_var) * 1.5

        # Find text line regions
        lines: list[tuple[int, int]] = []
        in_line = False
        start = 0
        for i, is_text in enumerate(text_rows):
            if is_text and not in_line:
                start = i
                in_line = True
            elif not is_text and in_line:
                if i - start > 3:  # Minimum line height
                    lines.append((start, i))
                in_line = False
        if in_line:
            lines.append((start, h))

        # Estimate character density
        blocks: list[dict[str, Any]] = []
        total_chars = 0
        for y_start, y_end in lines:
            line_height = y_end - y_start
            line_region = gray[y_start:y_end, :]
            col_var = np.var(line_region.astype(np.float32), axis=0)
            text_cols = col_var > np.mean(col_var) * 1.2
            char_count = int(np.sum(text_cols) / max(line_height, 1))
            total_chars += char_count

            blocks.append(
                {
                    "text": f"[Line at y={y_start}-{y_end}]",
                    "confidence": 0.3,
                    "bbox": {"x": 0, "y": y_start, "width": w, "height": line_height},
                    "estimated_chars": char_count,
                }
            )

        # Generate placeholder text based on detected structure
        estimated_text = " ".join([b["text"] for b in blocks]) if blocks else ""

        return OCRResult(
            text=estimated_text,
            confidence=0.3 if blocks else 0.0,
            blocks=blocks,
            language=self.language,
            metadata={
                "engine": "builtin",
                "text_lines_detected": len(lines),
                "estimated_characters": total_chars,
            },
        )

    @staticmethod
    def _preprocess_image(img: Image.Image) -> Image.Image:
        """Apply preprocessing to improve OCR accuracy."""
        # Convert to grayscale
        if img.mode != "L":
            img = img.convert("L")

        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # Apply mild sharpening
        img = img.filter(ImageFilter.SHARPEN)

        # Resize if too small (OCR works better with larger text)
        w, h = img.size
        if w < 1000:
            scale = 1000 / w
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        return img

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

    def batch_extract(
        self, images: list[str | Path | Image.Image | np.ndarray]
    ) -> list[OCRResult]:
        """Extract text from multiple images."""
        return [self.extract_text(img) for img in images]

    @property
    def tesseract_available(self) -> bool:
        """Check if tesseract backend is available."""
        return self._tesseract_available
