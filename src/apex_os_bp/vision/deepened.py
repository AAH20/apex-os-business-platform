"""Deepened vision module: YOLO detection, CNN classification,
U-Net segmentation, face recognition, and video tracking."""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]
    confidence: float
    class_id: int
    class_name: str = ""

@dataclass
class SegmentationMask:
    class_id: int
    class_name: str
    mask: np.ndarray
    area_fraction: float

@dataclass
class FaceEmbedding:
    vector: np.ndarray
    face_id: str
    confidence: float
    bbox: Tuple[int, int, int, int]

@dataclass
class Track:
    track_id: int
    class_name: str
    positions: List[Tuple[int, int]] = field(default_factory=list)
    frames_active: int = 0
    last_seen: int = 0

class YOLODetector:
    COCO_CLASSES = (
        "person bicycle car motorcycle airplane bus train truck boat traffic light "
        "fire hydrant stop sign parking meter bench bird cat dog horse sheep cow "
        "elephant bear zebra giraffe backpack umbrella handbag tie suitcase frisbee "
        "skis snowboard sports ball kite baseball bat baseball glove skateboard "
        "surfboard tennis racket bottle wine glass cup fork knife spoon bowl banana "
        "apple sandwich orange broccoli carrot hot dog pizza donut cake chair couch "
        "potted plant bed dining table toilet tv laptop mouse remote keyboard "
        "cell phone microwave oven toaster sink refrigerator book clock vase "
        "scissors teddy bear hair drier toothbrush"
    ).split()
    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.5):
        self.model_path, self.conf_threshold, self._model = model_path, conf_threshold, None
    def _load(self):
        if self._model is None:
            try:
                from ultralytics import YOLO
                self._model = YOLO(self.model_path)
            except ImportError:
                self._model = "mock"
        return self._model
    def detect(self, image: np.ndarray) -> List[Detection]:
        model = self._load()
        if model == "mock":
            h, w = image.shape[:2]
            return [Detection((int(w*0.1), int(h*0.1), int(w*0.5), int(h*0.8)), 0.87, 0, "person")]
        results = model(image, verbose=False)
        dets: List[Detection] = []
        for r in results:
            if r.boxes is None:
                continue
            for i in range(len(r.boxes)):
                conf = float(r.boxes.conf[i])
                if conf < self.conf_threshold:
                    continue
                cls_id = int(r.boxes.cls[i])
                x1, y1, x2, y2 = r.boxes.xyxy[i].tolist()
                dets.append(Detection((int(x1), int(y1), int(x2), int(y2)), conf, cls_id,
                    self.COCO_CLASSES[cls_id] if cls_id < len(self.COCO_CLASSES) else f"class_{cls_id}"))
        return dets

class CNNClassifier:
    def __init__(self, model_name: str = "resnet50", top_k: int = 5):
        self.model_name, self.top_k, self._model, self._classes = model_name, top_k, None, []
    def _load(self):
        if self._model is None:
            try:
                import torch, torchvision.models as models, torchvision.transforms as transforms
                if self.model_name == "resnet50":
                    self._model = models.resnet50(weights="DEFAULT")
                    self._preprocess = transforms.Compose([
                        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
                        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
                self._model.eval()
                self._torch = torch
            except ImportError:
                self._model = "mock"
        return self._model
    def classify(self, image: np.ndarray) -> List[Tuple[str, float]]:
        model = self._load()
        if model == "mock":
            return [("golden_retriever", 0.92), ("labrador", 0.04),
                    ("tennis_ball", 0.02), ("beagle", 0.01), ("cocker_spaniel", 0.01)]
        torch = self._torch
        from PIL import Image
        tensor = self._preprocess(Image.fromarray(image)).unsqueeze(0)
        with torch.no_grad():
            probs = torch.nn.functional.softmax(model(tensor), dim=1)[0]
        top = torch.topk(probs, self.top_k)
        classes = self._get_classes()
        return [(classes[i] if i < len(classes) else f"class_{i}", float(p))
                for p, i in zip(top.values, top.indices)]
    def _get_classes(self) -> List[str]:
        if not self._classes:
            cache = Path(__file__).parent / "imagenet_classes.txt"
            if cache.exists():
                self._classes = cache.read_text().splitlines()
        return self._classes

class UNetSegmenter:
    def __init__(self, num_classes: int = 21, model_path: str = "unet_pascal.pt"):
        self.num_classes, self.model_path, self._model = num_classes, model_path, None
    def _load(self):
        if self._model is None:
            try:
                import torch, torch.nn as nn
                class UNet(nn.Module):
                    def __init__(self, n_cls):
                        super().__init__()
                        self.enc1 = self._block(3, 64)
                        self.enc2 = self._block(64, 128)
                        self.enc3 = self._block(128, 256)
                        self.dec2 = self._block(256 + 128, 128)
                        self.dec1 = self._block(128 + 64, 64)
                        self.out = nn.Conv2d(64, n_cls, 1)
                        self.pool = nn.MaxPool2d(2)
                        self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True)
                    @staticmethod
                    def _block(cin, cout):
                        return nn.Sequential(
                            nn.Conv2d(cin, cout, 3, padding=1), nn.ReLU(inplace=True),
                            nn.Conv2d(cout, cout, 3, padding=1), nn.ReLU(inplace=True))
                    def forward(self, x):
                        e1 = self.enc1(x)
                        e2 = self.enc2(self.pool(e1))
                        e3 = self.enc3(self.pool(e2))
                        d2 = self.dec2(torch.cat([self.up(e3), e2], dim=1))
                        d1 = self.dec1(torch.cat([self.up(d2), e1], dim=1))
                        return self.out(d1)
                self._model = UNet(self.num_classes)
                ckpt = Path(self.model_path)
                if ckpt.exists():
                    self._model.load_state_dict(torch.load(ckpt, map_location="cpu"))
                self._model.eval()
                self._torch = torch
            except ImportError:
                self._model = "mock"
        return self._model
    def segment(self, image: np.ndarray) -> List[SegmentationMask]:
        model = self._load()
        if model == "mock":
            h, w = image.shape[:2]
            mask = np.zeros((h, w), dtype=bool)
            mask[h//4:3*h//4, w//4:3*w//4] = True
            return [SegmentationMask(0, "foreground", mask, 0.25)]
        torch = self._torch
        from PIL import Image
        import torchvision.transforms as transforms
        orig_h, orig_w = image.shape[:2]
        tensor = transforms.Compose([
            transforms.ToTensor(), transforms.Resize((256, 256)),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])(Image.fromarray(image)).unsqueeze(0)
        with torch.no_grad():
            pred = model(tensor).argmax(1)[0].numpy()
        pred = np.array(Image.fromarray(pred.astype(np.uint8)).resize((orig_w, orig_h), Image.NEAREST))
        return [SegmentationMask(c, f"class_{c}", pred == c, float((pred == c).mean()))
                for c in range(self.num_classes) if (pred == c).mean() > 0.001]

class FaceRecognizer:
    EMBEDDING_DIM = 128
    def __init__(self, threshold: float = 0.6):
        self.threshold, self._known_faces, self._detector = threshold, {}, None
    def _load(self):
        if self._detector is None:
            try:
                import face_recognition
                self._detector = face_recognition
            except ImportError:
                self._detector = "mock"
        return self._detector
    def extract_embedding(self, image: np.ndarray,
                          bbox: Optional[Tuple[int, int, int, int]] = None) -> Optional[FaceEmbedding]:
        det = self._load()
        if det == "mock":
            vec = np.random.randn(self.EMBEDDING_DIM).astype(np.float32)
            vec /= np.linalg.norm(vec)
            return FaceEmbedding(vec, "unknown", 0.75, bbox or (0, 0, image.shape[1], image.shape[0]))
        face_img = image[bbox[1]:bbox[3], bbox[0]:bbox[2]] if bbox else image
        encs = det.face_encodings(face_img)
        if not encs:
            return None
        vec = encs[0].astype(np.float32)
        vec /= np.linalg.norm(vec)
        return FaceEmbedding(vec, "unknown", 1.0, bbox or (0, 0, image.shape[1], image.shape[0]))
    def register_face(self, name: str, image: np.ndarray,
                      bbox: Optional[Tuple[int, int, int, int]] = None) -> FaceEmbedding:
        emb = self.extract_embedding(image, bbox)
        if emb is None:
            raise ValueError("No face detected")
        emb.face_id = name
        self._known_faces[name] = emb
        return emb
    def recognize(self, image: np.ndarray,
                  bbox: Optional[Tuple[int, int, int, int]] = None) -> Optional[str]:
        emb = self.extract_embedding(image, bbox)
        if emb is None:
            return None
        best_name, best_sim = None, -1.0
        for name, known in self._known_faces.items():
            sim = float(np.dot(emb.vector, known.vector))
            if sim > best_sim:
                best_name, best_sim = name, sim
        return best_name if best_sim >= self.threshold else None
    def list_known_faces(self) -> List[str]:
        return list(self._known_faces.keys())

class VideoTracker:
    def __init__(self, max_disappeared: int = 30, iou_threshold: float = 0.3):
        self.max_disappeared, self.iou_threshold = max_disappeared, iou_threshold
        self._tracks: Dict[int, Track] = {}
        self._disappeared: Dict[int, int] = {}
        self._next_id, self._frame_count = 0, 0
    @staticmethod
    def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        x1, y1 = max(a[0], b[0]), max(a[1], b[1])
        x2, y2 = min(a[2], b[2]), min(a[3], b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
        return inter / union if union > 0 else 0.0
    def update(self, detections: List[Detection]) -> List[Track]:
        self._frame_count += 1
        matched_tracks: Dict[int, Detection] = {}
        candidates = []
        for tid, track in self._tracks.items():
            if not track.positions:
                continue
            last = track.positions[-1]
            last_bbox = (last[0]-20, last[1]-20, last[0]+20, last[1]+20)
            for di, det in enumerate(detections):
                iou = self._iou(last_bbox, det.bbox)
                if iou >= self.iou_threshold:
                    candidates.append((iou, tid, di))
        candidates.sort(reverse=True)
        used_tids, used_dis = set(), set()
        for iou, tid, di in candidates:
            if tid not in used_tids and di not in used_dis:
                matched_tracks[tid] = detections[di]
                used_tids.add(tid)
                used_dis.add(di)
        for tid, det in matched_tracks.items():
            cx = (det.bbox[0] + det.bbox[2]) // 2
            cy = (det.bbox[1] + det.bbox[3]) // 2
            self._tracks[tid].positions.append((cx, cy))
            self._tracks[tid].frames_active += 1
            self._tracks[tid].last_seen = self._frame_count
            self._disappeared[tid] = 0
        for tid in self._tracks:
            if tid not in matched_tracks:
                self._disappeared[tid] = self._disappeared.get(tid, 0) + 1
        for di, det in enumerate(detections):
            if di not in used_dis:
                tid = self._next_id
                self._next_id += 1
                cx = (det.bbox[0] + det.bbox[2]) // 2
                cy = (det.bbox[1] + det.bbox[3]) // 2
                self._tracks[tid] = Track(tid, det.class_name, [(cx, cy)], 1, self._frame_count)
                self._disappeared[tid] = 0
        stale = [tid for tid, d in self._disappeared.items() if d > self.max_disappeared]
        for tid in stale:
            del self._tracks[tid]
            del self._disappeared[tid]
        return list(self._tracks.values())
    def get_track(self, track_id: int) -> Optional[Track]:
        return self._tracks.get(track_id)
    def reset(self):
        self._tracks.clear()
        self._disappeared.clear()
        self._next_id, self._frame_count = 0, 0

class VisionPipeline:
    def __init__(self):
        self.detector = YOLODetector()
        self.classifier = CNNClassifier()
        self.segmenter = UNetSegmenter()
        self.face_recognizer = FaceRecognizer()
        self.video_tracker = VideoTracker()
    def analyze_image(self, image: np.ndarray) -> Dict[str, Any]:
        return {
            "detections": self.detector.detect(image),
            "classification": self.classifier.classify(image),
            "segmentation": self.segmenter.segment(image),
        }
    def process_video_frame(self, image: np.ndarray) -> List[Track]:
        return self.video_tracker.update(self.detector.detect(image))