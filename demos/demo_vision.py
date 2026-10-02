#!/usr/bin/env python3
"""Vision demos: detection, recognition, OCR, face recognition, generation."""

import os
import json
import time
import random
from pathlib import Path


# 1. Object Detection
def detect_objects(image_path=None):
    """Detect objects using OpenCV or fallback to simulation."""
    print("\n" + "=" * 50)
    print("1. OBJECT DETECTION")
    print("=" * 50)
    try:
        import cv2
        import numpy as np

        if image_path and Path(image_path).exists():
            img = cv2.imread(image_path)
        else:
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(img, (100, 100), (300, 300), (0, 255, 0), -1)
            cv2.circle(img, (450, 200), 80, (255, 0, 0), -1)

        cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if Path(cascade).exists():
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            found = cv2.CascadeClassifier(cascade).detectMultiScale(gray, 1.1, 4)
            objs = [{"type": "face", "bbox": [int(v) for v in b]} for b in found]
        else:
            objs = [{"type": "shape", "bbox": [100, 100, 200, 200]}]

        print(f"  Found {len(objs)} objects: {objs}")
        return {"count": len(objs), "objects": objs}
    except ImportError:
        fake = [{"type": "person", "bbox": [10, 20, 100, 200], "conf": 0.92}]
        print(f"  [fallback] {fake}")
        return {"count": 1, "objects": fake}


# 2. Image Recognition
def recognize_image(image_path=None):
    """Classify image by dominant color."""
    print("\n" + "=" * 50)
    print("2. IMAGE RECOGNITION")
    print("=" * 50)
    try:
        from PIL import Image
        import numpy as np

        if image_path and Path(image_path).exists():
            img = Image.open(image_path).convert("RGB")
        else:
            img = Image.new("RGB", (224, 224), (random.randint(0, 255),
                                                random.randint(0, 255),
                                                random.randint(0, 255)))
        arr = np.array(img)
        r, g, b = arr.mean(axis=(0, 1))
        label = ("nature" if g > r and g > b else
                 "sky/water" if b > r and b > g else
                 "warm" if r > g and r > b else "mixed")
        result = {"label": label, "confidence": 0.75, "rgb": [int(r), int(g), int(b)]}
        print(f"  Label: {label} (conf={result['confidence']})")
        return result
    except ImportError:
        print("  [fallback] label=unknown")
        return {"label": "unknown", "confidence": 0.5}


# 3. OCR
def extract_text(image_path=None):
    """Extract text via pytesseract or fallback."""
    print("\n" + "=" * 50)
    print("3. OCR - TEXT EXTRACTION")
    print("=" * 50)
    try:
        from PIL import Image, ImageDraw
        import pytesseract

        if image_path and Path(image_path).exists():
            img = Image.open(image_path)
        else:
            img = Image.new("RGB", (400, 100), "white")
            ImageDraw.Draw(img).text((10, 30), "Hello Vision 123", fill="black")

        text = pytesseract.image_to_string(img).strip()
        print(f"  Text: '{text}'")
        return {"text": text, "words": len(text.split())}
    except ImportError:
        print("  [fallback] text='Simulated OCR output'")
        return {"text": "Simulated OCR output", "words": 3}


# 4. Face Recognition
def recognize_face(image_path=None):
    """Detect faces via face_recognition lib or fallback."""
    print("\n" + "=" * 50)
    print("4. FACE RECOGNITION")
    print("=" * 50)
    try:
        import face_recognition
        import numpy as np

        if image_path and Path(image_path).exists():
            img = face_recognition.load_image_file(image_path)
        else:
            img = np.zeros((200, 200, 3), dtype=np.uint8)

        locs = face_recognition.face_locations(img)
        encs = face_recognition.face_encodings(img, locs)
        faces = [{"id": i, "loc": [int(v) for v in l],
                  "enc": [round(float(x), 4) for x in e[:4]]}
                 for i, (l, e) in enumerate(zip(locs, encs))]
        print(f"  Found {len(faces)} face(s)")
        return {"count": len(faces), "faces": faces}
    except ImportError:
        print("  [fallback] 1 face detected")
        return {"count": 1, "faces": [{"id": 0, "loc": [50, 150, 150, 50]}]}


# 5. Image Generation
def generate_image(output_path="generated_demo.png", prompt=None):
    """Generate procedural art via PIL or fallback."""
    print("\n" + "=" * 50)
    print("5. IMAGE GENERATION")
    print("=" * 50)
    try:
        from PIL import Image, ImageDraw

        prompt = prompt or "sunset gradient"
        random.seed(hash(prompt) % (2**32))
        w, h = 512, 512
        img = Image.new("RGB", (w, h), (15, 15, 35))
        draw = ImageDraw.Draw(img)

        for y in range(h):
            r = int(255 * (1 - y / h) * random.uniform(0.7, 1.0))
            g = int(100 * (y / h) * random.uniform(0.5, 1.0))
            b = int(200 * (1 - y / h) * random.uniform(0.3, 0.8))
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        for _ in range(random.randint(5, 15)):
            x, y = random.randint(0, w), random.randint(0, h)
            s = random.randint(20, 100)
            c = tuple(random.randint(100, 255) for _ in range(3))
            draw.ellipse([x, y, x + s, y + s], fill=c)

        img.save(output_path)
        sz = round(os.path.getsize(output_path) / 1024, 1)
        print(f"  Saved: {output_path} ({sz} KB)")
        return {"path": output_path, "prompt": prompt, "size_kb": sz}
    except ImportError:
        print("  [fallback] would generate image")
        return {"path": output_path, "prompt": prompt}


def main():
    print("=" * 50)
    print("  APEX-OS VISION DEMO SUITE")
    print("=" * 50)
    t0 = time.time()
    results = {
        "detection": detect_objects(),
        "recognition": recognize_image(),
        "ocr": extract_text(),
        "face": recognize_face(),
        "generation": generate_image(),
    }
    print(f"\nAll 5 demos done in {time.time() - t0:.2f}s")
    print(json.dumps(results, indent=2, default=str))
    return results


if __name__ == "__main__":
    main()
