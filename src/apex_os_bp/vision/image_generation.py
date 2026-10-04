"""Image generation module for APEX-OS.

Generates images procedurally using Pillow. Supports gradients, patterns,
shapes, noise, and text rendering. Can also use Stable Diffusion via
diffusers when available for AI-powered generation.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of an image generation operation."""

    image: Image.Image
    seed: int
    width: int
    height: int
    format: str = "PNG"
    metadata: dict[str, Any] = field(default_factory=dict)

    def save(self, path: str | Path, **kwargs: Any) -> Path:
        """Save the generated image to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(path, **kwargs)
        return path

    def to_array(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array(self.image)

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)


class ImageGenerator:
    """Procedural and AI-powered image generator.

    Modes:
        - "procedural": Generate images using Pillow (always available)
        - "stable_diffusion": Use diffusers library if available
    """

    def __init__(self, mode: str = "procedural", seed: Optional[int] = None):
        self.mode = mode
        self.seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        self._diffusers_available = self._check_diffusers()
        self._rng = random.Random(self.seed)

    @staticmethod
    def _check_diffusers() -> bool:
        """Check if diffusers library is available."""
        try:
            import diffusers  # noqa: F401

            return True
        except ImportError:
            return False

    def generate(
        self,
        width: int = 512,
        height: int = 512,
        prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate an image.

        Args:
            width: Image width in pixels.
            height: Image height in pixels.
            prompt: Text prompt (used for AI generation, seed hint for procedural).
            **kwargs: Additional generation parameters.

        Returns:
            GenerationResult with the generated image.
        """
        if self.mode == "stable_diffusion" and self._diffusers_available:
            return self._generate_stable_diffusion(width, height, prompt, **kwargs)
        else:
            return self._generate_procedural(width, height, prompt, **kwargs)

    def _generate_procedural(
        self, width: int, height: int, prompt: Optional[str] = None, **kwargs: Any
    ) -> GenerationResult:
        """Generate image procedurally based on prompt keywords."""
        prompt = (prompt or "").lower()

        # Determine generation strategy from prompt
        if "gradient" in prompt or "sky" in prompt:
            img = self._gen_gradient(width, height, prompt)
        elif "noise" in prompt or "texture" in prompt:
            img = self._gen_noise(width, height, prompt)
        elif "pattern" in prompt or "tile" in prompt:
            img = self._gen_pattern(width, height, prompt)
        elif "shape" in prompt or "geometric" in prompt:
            img = self._gen_shapes(width, height, prompt)
        elif "text" in prompt or "typography" in prompt:
            img = self._gen_text_image(width, height, prompt)
        elif "landscape" in prompt or "mountain" in prompt:
            img = self._gen_landscape(width, height, prompt)
        elif "abstract" in prompt:
            img = self._gen_abstract(width, height, prompt)
        else:
            # Default: colorful gradient
            img = self._gen_gradient(width, height, prompt)

        return GenerationResult(
            image=img,
            seed=self.seed,
            width=width,
            height=height,
            metadata={"mode": "procedural", "prompt": prompt},
        )

    def _generate_stable_diffusion(
        self, width: int, height: int, prompt: Optional[str] = None, **kwargs: Any
    ) -> GenerationResult:
        """Generate image using Stable Diffusion."""
        try:
            import torch
            from diffusers import StableDiffusionPipeline

            pipe = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5", torch_dtype=torch.float16
            )
            pipe = pipe.to("cuda" if torch.cuda.is_available() else "cpu")

            generator = torch.Generator(device="cpu").manual_seed(self.seed)
            result = pipe(
                prompt or "a beautiful landscape",
                width=width,
                height=height,
                generator=generator,
                **kwargs,
            )
            img = result.images[0]

            return GenerationResult(
                image=img,
                seed=self.seed,
                width=width,
                height=height,
                metadata={"mode": "stable_diffusion", "prompt": prompt},
            )
        except Exception as e:
            logger.error(f"Stable Diffusion generation failed: {e}")
            return self._generate_procedural(width, height, prompt, **kwargs)

    def _gen_gradient(self, width: int, height: int, prompt: str) -> Image.Image:
        """Generate a gradient image."""
        # Parse colors from prompt or use defaults
        colors = self._extract_colors(prompt)
        if len(colors) < 2:
            colors = [(66, 133, 244), (219, 68, 55), (244, 180, 0), (15, 157, 88)]

        direction = "horizontal" if "horizontal" in prompt else "vertical"
        if "diagonal" in prompt:
            direction = "diagonal"

        img = Image.new("RGB", (width, height))
        pixels = img.load()

        c1, c2 = colors[0], colors[1]
        for y in range(height):
            for x in range(width):
                if direction == "horizontal":
                    t = x / max(width - 1, 1)
                elif direction == "diagonal":
                    t = (x + y) / max(width + height - 2, 1)
                else:
                    t = y / max(height - 1, 1)

                r = int(c1[0] * (1 - t) + c2[0] * t)
                g = int(c1[1] * (1 - t) + c2[1] * t)
                b = int(c1[2] * (1 - t) + c2[2] * t)
                pixels[x, y] = (r, g, b)

        return img

    def _gen_noise(self, width: int, height: int, prompt: str) -> Image.Image:
        """Generate a noise texture."""
        scale = 1.0
        if "fine" in prompt:
            scale = 0.5
        elif "coarse" in prompt:
            scale = 2.0

        arr = np.random.RandomState(self.seed).randint(0, 256, (height, width, 3), dtype=np.uint8)
        img = Image.fromarray(arr)

        if scale != 1.0:
            new_w = int(width * scale)
            new_h = int(height * scale)
            img = img.resize((new_w, new_h), Image.BILINEAR)
            img = img.crop((0, 0, width, height))

        return img

    def _gen_pattern(self, width: int, height: int, prompt: str) -> Image.Image:
        """Generate a repeating pattern."""
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        pattern_type = "grid"
        if "circle" in prompt or "dot" in prompt:
            pattern_type = "circles"
        elif "stripe" in prompt or "line" in prompt:
            pattern_type = "stripes"
        elif "checker" in prompt:
            pattern_type = "checkerboard"
        elif "wave" in prompt:
            pattern_type = "waves"

        colors = self._extract_colors(prompt)
        if not colors:
            colors = [(66, 133, 244), (219, 68, 55)]

        if pattern_type == "grid":
            spacing = 40
            for x in range(0, width, spacing):
                draw.line([(x, 0), (x, height)], fill=colors[0], width=2)
            for y in range(0, height, spacing):
                draw.line([(0, y), (width, y)], fill=colors[0], width=2)

        elif pattern_type == "circles":
            spacing = 50
            for x in range(spacing // 2, width, spacing):
                for y in range(spacing // 2, height, spacing):
                    r = spacing // 3
                    color = colors[(x // spacing + y // spacing) % len(colors)]
                    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)

        elif pattern_type == "stripes":
            spacing = 30
            for i, x in enumerate(range(0, width, spacing)):
                color = colors[i % len(colors)]
                draw.rectangle([x, 0, x + spacing // 2, height], fill=color)

        elif pattern_type == "checkerboard":
            size = 40
            for x in range(0, width, size):
                for y in range(0, height, size):
                    if (x // size + y // size) % 2 == 0:
                        draw.rectangle([x, y, x + size, y + size], fill=colors[0])

        elif pattern_type == "waves":
            for y in range(0, height, 20):
                points = []
                for x in range(0, width + 10, 10):
                    y_offset = int(20 * math.sin(x / 50.0 + y / 100.0))
                    points.append((x, y + y_offset))
                if len(points) > 1:
                    draw.line(points, fill=colors[0], width=2)

        return img

    def _gen_shapes(self, width: int, height: int, prompt: str) -> Image.Image:
        """Generate geometric shapes."""
        img = Image.new("RGB", (width, height), (245, 245, 245))
        draw = ImageDraw.Draw(img)

        colors = self._extract_colors(prompt)
        if not colors:
            colors = [
                (66, 133, 244), (219, 68, 55), (244, 180, 0),
                (15, 157, 88), (171, 71, 188),
            ]

        num_shapes = 10
        if "many" in prompt:
            num_shapes = 30
        elif "few" in prompt:
            num_shapes = 5

        for i in range(num_shapes):
            color = colors[i % len(colors)]
            shape_type = self._rng.choice(["circle", "rectangle", "triangle", "ellipse"])

            x1 = self._rng.randint(0, width - 50)
            y1 = self._rng.randint(0, height - 50)
            x2 = x1 + self._rng.randint(30, 150)
            y2 = y1 + self._rng.randint(30, 150)

            if shape_type == "circle":
                r = min(x2 - x1, y2 - y1) // 2
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
            elif shape_type == "rectangle":
                draw.rectangle([x1, y1, x2, y2], fill=color)
            elif shape_type == "ellipse":
                draw.ellipse([x1, y1, x2, y2], fill=color)
            elif shape_type == "triangle":
                points = [
                    ((x1 + x2) // 2, y1),
                    (x1, y2),
                    (x2, y2),
                ]
                draw.polygon(points, fill=color)

        return img

    def _gen_text_image(self, width: int, height: int, prompt: str) -> Image.Image:
        """Generate an image with text."""
        bg_color = (255, 255, 255)
        text_color = (0, 0, 0)

        if "dark" in prompt:
            bg_color = (30, 30, 30)
            text_color = (255, 255, 255)

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        text = prompt.replace("text", "").replace("typography", "").strip() or "Hello"

        # Try to use a nice font, fall back to default
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
            except (OSError, IOError):
                font = ImageFont.load_default()

        # Center text
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (width - tw) // 2
        y = (height - th) // 2
        draw.text((x, y), text, fill=text_color, font=font)

        return img

    def _gen_landscape(self, width: int, height: int, prompt: str) -> Image.Image:
        """Generate a procedural landscape."""
        img = Image.new("RGB", (width, height))
        pixels = img.load()

        # Sky gradient
        for y in range(height):
            t = y / max(height - 1, 1)
            if t < 0.6:
                # Sky: blue to light blue
                sky_t = t / 0.6
                r = int(100 * (1 - sky_t) + 180 * sky_t)
                g = int(150 * (1 - sky_t) + 220 * sky_t)
                b = int(255 * (1 - sky_t) + 255 * sky_t)
            else:
                # Ground: green to dark green
                ground_t = (t - 0.6) / 0.4
                r = int(100 * (1 - ground_t) + 50 * ground_t)
                g = int(180 * (1 - ground_t) + 120 * ground_t)
                b = int(80 * (1 - ground_t) + 40 * ground_t)

            for x in range(width):
                pixels[x, y] = (r, g, b)

        # Add mountains
        draw = ImageDraw.Draw(img)
        mountain_color = (80, 80, 100)
        points = [(0, int(height * 0.6))]
        for x in range(0, width + 1, width // 8):
            y = int(height * 0.3 + self._rng.randint(-30, 30))
            points.append((x, y))
        points.append((width, int(height * 0.6)))
        points.append((width, height))
        points.append((0, height))
        draw.polygon(points, fill=mountain_color)

        return img

    def _gen_abstract(self, width: int, height: int, prompt: str) -> Image.Image:
        """Generate abstract art."""
        img = Image.new("RGB", (width, height), (20, 20, 30))
        draw = ImageDraw.Draw(img)

        colors = self._extract_colors(prompt)
        if not colors:
            palette = [
                (255, 107, 107), (78, 205, 196), (255, 230, 109),
                (155, 89, 182), (52, 152, 219), (231, 76, 60),
                (46, 204, 113), (241, 196, 15),
            ]
            colors = palette

        # Draw flowing curves
        for _ in range(20):
            color = self._rng.choice(colors)
            points = []
            x = self._rng.randint(0, width)
            y = self._rng.randint(0, height)
            for _ in range(5):
                points.append((x, y))
                x += self._rng.randint(-100, 100)
                y += self._rng.randint(-100, 100)
                x = max(0, min(width, x))
                y = max(0, min(height, y))
            if len(points) > 1:
                draw.line(points, fill=color, width=self._rng.randint(2, 8))

        # Add some circles
        for _ in range(10):
            color = self._rng.choice(colors)
            x = self._rng.randint(0, width)
            y = self._rng.randint(0, height)
            r = self._rng.randint(10, 80)
            draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=3)

        return img

    @staticmethod
    def _extract_colors(prompt: str) -> list[tuple[int, int, int]]:
        """Extract color names from prompt and convert to RGB."""
        color_map = {
            "red": (219, 68, 55),
            "blue": (66, 133, 244),
            "green": (15, 157, 88),
            "yellow": (244, 180, 0),
            "purple": (171, 71, 188),
            "orange": (255, 152, 0),
            "pink": (233, 30, 99),
            "cyan": (0, 188, 212),
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "gray": (128, 128, 128),
            "brown": (139, 90, 43),
            "navy": (0, 0, 128),
            "teal": (0, 128, 128),
        }

        found = []
        for name, rgb in color_map.items():
            if name in prompt.lower():
                found.append(rgb)
        return found

    def generate_thumbnail(
        self,
        image_input: str | Path | Image.Image | np.ndarray,
        size: tuple[int, int] = (128, 128),
    ) -> GenerationResult:
        """Generate a thumbnail from an existing image."""
        if isinstance(image_input, (str, Path)):
            img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            img = Image.fromarray(image_input).convert("RGB")
        else:
            img = image_input.convert("RGB")

        img.thumbnail(size, Image.LANCZOS)

        # Create a canvas of the exact size and center the thumbnail
        canvas = Image.new("RGB", size, (255, 255, 255))
        x = (size[0] - img.width) // 2
        y = (size[1] - img.height) // 2
        canvas.paste(img, (x, y))

        return GenerationResult(
            image=canvas,
            seed=self.seed,
            width=size[0],
            height=size[1],
            metadata={"mode": "thumbnail", "source_size": img.size},
        )

    def generate_avatar(
        self, name: str, size: int = 256
    ) -> GenerationResult:
        """Generate an avatar image from a name."""
        # Generate deterministic color from name
        name_hash = int(hashlib.md5(name.encode()).hexdigest(), 16)
        rng = random.Random(name_hash)

        bg_color = (
            rng.randint(50, 200),
            rng.randint(50, 200),
            rng.randint(50, 200),
        )
        text_color = (
            255 - bg_color[0] // 3,
            255 - bg_color[1] // 3,
            255 - bg_color[2] // 3,
        )

        img = Image.new("RGB", (size, size), bg_color)
        draw = ImageDraw.Draw(img)

        # Draw initials
        initials = "".join([w[0].upper() for w in name.split()[:2]]) or name[0].upper()

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size // 2)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size // 2)
            except (OSError, IOError):
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), initials, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - tw) // 2
        y = (size - th) // 2
        draw.text((x, y), initials, fill=text_color, font=font)

        return GenerationResult(
            image=img,
            seed=name_hash,
            width=size,
            height=size,
            metadata={"mode": "avatar", "name": name},
        )

    @property
    def diffusers_available(self) -> bool:
        """Check if Stable Diffusion backend is available."""
        return self._diffusers_available
