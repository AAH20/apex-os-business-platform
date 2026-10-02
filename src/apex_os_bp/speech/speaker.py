"""Speaker Recognition component.

Identifies and verifies speakers from audio using voice embeddings.
"""

from __future__ import annotations

import abc
import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apex_os_bp.speech.base import AudioSegment, SpeechComponent, SpeechError


@dataclass
class SpeakerConfig:
    """Configuration for speaker recognition.

    Attributes:
        model_name: Embedding model name ("speechbrain", "resemblyzer", "mock").
        embedding_dim: Dimensionality of speaker embeddings.
        threshold: Cosine similarity threshold for verification.
        min_audio_duration: Minimum audio duration in seconds for enrollment.
        max_speakers: Maximum number of speakers in the gallery.
        normalize_embeddings: Whether to L2-normalize embeddings.
    """

    model_name: str = "mock"
    embedding_dim: int = 256
    threshold: float = 0.65
    min_audio_duration: float = 1.0
    max_speakers: int = 100
    normalize_embeddings: bool = True

    def __post_init__(self) -> None:
        if self.embedding_dim <= 0:
            raise ValueError("embedding_dim must be positive")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be in [0.0, 1.0]")
        if self.min_audio_duration < 0.0:
            raise ValueError("min_audio_duration must be >= 0")
        if self.max_speakers <= 0:
            raise ValueError("max_speakers must be positive")


@dataclass
class SpeakerEmbedding:
    """A speaker embedding vector with associated metadata.

    Attributes:
        vector: The embedding vector (list of floats).
        speaker_id: The speaker identifier.
        metadata: Additional metadata (e.g., audio source, timestamp).
    """

    vector: list[float]
    speaker_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.vector:
            raise ValueError("Embedding vector must not be empty")

    @property
    def dim(self) -> int:
        """Dimensionality of the embedding."""
        return len(self.vector)

    def cosine_similarity(self, other: SpeakerEmbedding) -> float:
        """Compute cosine similarity with another embedding.

        Args:
            other: The other speaker embedding.

        Returns:
            Cosine similarity in [-1, 1].
        """
        if len(self.vector) != len(other.vector):
            raise ValueError("Embedding dimensions must match")
        dot = sum(a * b for a, b in zip(self.vector, other.vector))
        norm_a = math.sqrt(sum(a * a for a in self.vector))
        norm_b = math.sqrt(sum(b * b for b in other.vector))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        import struct

        return struct.pack(f"<{len(self.vector)}f", *self.vector)

    @classmethod
    def from_bytes(cls, data: bytes, speaker_id: str = "") -> SpeakerEmbedding:
        """Deserialize from bytes."""
        import struct

        n_floats = len(data) // 4
        vector = list(struct.unpack_from(f"<{n_floats}f", data))
        return cls(vector=vector, speaker_id=speaker_id)


class SpeakerRecognition(SpeechComponent):
    """Abstract base class for speaker recognition engines."""

    @property
    def config(self) -> SpeakerConfig:
        return self._config  # type: ignore[return-value]

    def enroll(self, audio: AudioSegment, speaker_id: str) -> SpeakerEmbedding:
        """Enroll a new speaker from an audio sample.

        Args:
            audio: The audio sample of the speaker.
            speaker_id: A unique identifier for the speaker.

        Returns:
            The speaker embedding.
        """
        if not speaker_id.strip():
            raise ValueError("speaker_id must not be empty")
        if audio.duration < self.config.min_audio_duration:
            raise SpeechError(
                f"Audio too short: {audio.duration:.2f}s < "
                f"{self.config.min_audio_duration:.2f}s",
                "speaker",
            )
        self._ensure_initialized()
        return self._enroll_impl(audio, speaker_id)

    def verify(
        self, audio: AudioSegment, reference: SpeakerEmbedding
    ) -> tuple[bool, float]:
        """Verify if audio matches a reference speaker embedding.

        Args:
            audio: The audio sample to verify.
            reference: The reference speaker embedding.

        Returns:
            A tuple of (is_match, similarity_score).
        """
        self._ensure_initialized()
        embedding = self._extract_embedding(audio)
        similarity = embedding.cosine_similarity(reference)
        is_match = similarity >= self.config.threshold
        return is_match, similarity

    def identify(
        self, audio: AudioSegment, gallery: list[SpeakerEmbedding]
    ) -> tuple[str, float]:
        """Identify the speaker from a gallery of embeddings.

        Args:
            audio: The audio sample to identify.
            gallery: List of known speaker embeddings.

        Returns:
            A tuple of (speaker_id, confidence). Returns ("unknown", 0.0)
            if no match exceeds the threshold.
        """
        if not gallery:
            return "unknown", 0.0
        self._ensure_initialized()
        embedding = self._extract_embedding(audio)

        best_id = "unknown"
        best_score = -1.0
        for ref in gallery:
            sim = embedding.cosine_similarity(ref)
            if sim > best_score:
                best_score = sim
                best_id = ref.speaker_id

        if best_score < self.config.threshold:
            return "unknown", best_score
        return best_id, best_score

    @abc.abstractmethod
    def _enroll_impl(self, audio: AudioSegment, speaker_id: str) -> SpeakerEmbedding:
        """Implementation-specific enrollment logic."""
        raise NotImplementedError

    @abc.abstractmethod
    def _extract_embedding(self, audio: AudioSegment) -> SpeakerEmbedding:
        """Extract a speaker embedding from audio."""
        raise NotImplementedError

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


class SpeakerIdentifier(SpeakerRecognition):
    """Production speaker identifier using speechbrain or resemblyzer.

    Falls back to MockSpeakerRecognition if the ML library is unavailable.
    """

    def __init__(self, config: SpeakerConfig | None = None) -> None:
        super().__init__(config or SpeakerConfig())
        self._model: Any = None
        self._fallback: MockSpeakerRecognition | None = None

    def initialize(self) -> None:
        """Load the speaker recognition model."""
        try:
            if self.config.model_name == "speechbrain":
                from speechbrain.pretrained import EncoderClassifier  # type: ignore

                self._model = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb"
                )
            elif self.config.model_name == "resemblyzer":
                from resemblyzer import VoiceEncoder  # type: ignore

                self._model = VoiceEncoder()
            else:
                raise ImportError(f"Unknown model: {self.config.model_name}")
            self._initialized = True
        except ImportError:
            self._fallback = MockSpeakerRecognition(self.config)
            self._fallback.initialize()
            self._initialized = True

    def shutdown(self) -> None:
        """Release model resources."""
        self._model = None
        if self._fallback:
            self._fallback.shutdown()
        self._initialized = False

    def _enroll_impl(self, audio: AudioSegment, speaker_id: str) -> SpeakerEmbedding:
        if self._fallback:
            return self._fallback.enroll(audio, speaker_id)
        if self._model is None:
            raise SpeechError("Speaker model not loaded", "speaker")
        embedding = self._extract_embedding(audio)
        return SpeakerEmbedding(
            vector=embedding.vector,
            speaker_id=speaker_id,
            metadata={"model": self.config.model_name},
        )

    def _extract_embedding(self, audio: AudioSegment) -> SpeakerEmbedding:
        if self._fallback:
            return self._fallback._extract_embedding(audio)
        if self._model is None:
            raise SpeechError("Speaker model not loaded", "speaker")

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            audio.to_wav(tmp_path)
            if self.config.model_name == "speechbrain":
                import torch  # type: ignore

                emb_tensor = self._model.encode_batch(
                    torch.tensor(audio.samples).unsqueeze(0)
                )
                vector = emb_tensor.squeeze().cpu().tolist()
            elif self.config.model_name == "resemblyzer":
                vector = self._model.embed_utterance(audio.samples)
            else:
                raise SpeechError("Unknown model type", "speaker")

            if self.config.normalize_embeddings:
                vector = self._l2_normalize(vector)

            return SpeakerEmbedding(
                vector=vector,
                metadata={"model": self.config.model_name},
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @staticmethod
    def _l2_normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]


class MockSpeakerRecognition(SpeakerRecognition):
    """Mock speaker recognition for testing and fallback.

    Generates deterministic embeddings from audio spectral characteristics.
    """

    def __init__(self, config: SpeakerConfig | None = None) -> None:
        super().__init__(config or SpeakerConfig())

    def initialize(self) -> None:
        self._initialized = True

    def shutdown(self) -> None:
        self._initialized = False

    def _enroll_impl(self, audio: AudioSegment, speaker_id: str) -> SpeakerEmbedding:
        embedding = self._extract_embedding(audio)
        return SpeakerEmbedding(
            vector=embedding.vector,
            speaker_id=speaker_id,
            metadata={"model": "mock"},
        )

    def _extract_embedding(self, audio: AudioSegment) -> SpeakerEmbedding:
        """Generate a deterministic embedding from audio characteristics.

        Uses a simple spectral-like feature extraction to produce
        reproducible embeddings for testing.
        """
        dim = self.config.embedding_dim
        samples = audio.samples
        if not samples:
            samples = [0.0]

        # Compute features from audio statistics
        n = len(samples)
        # Divide into bands and compute energy in each band
        n_bands = min(dim, 64)
        band_size = max(1, n // n_bands)
        features: list[float] = []
        for i in range(n_bands):
            start = i * band_size
            end = min(start + band_size, n)
            band = samples[start:end]
            energy = sum(s * s for s in band) / max(1, len(band))
            features.append(energy)

        # Add zero-crossing rate features
        zcr_bands = min(dim - n_bands, 32) if dim > n_bands else 0
        for i in range(zcr_bands):
            start = i * band_size
            end = min(start + band_size, n)
            band = samples[start:end]
            if len(band) > 1:
                zcr = sum(
                    1 for j in range(1, len(band)) if band[j - 1] * band[j] < 0
                ) / len(band)
            else:
                zcr = 0.0
            features.append(zcr)

        # Pad or truncate to embedding_dim
        if len(features) < dim:
            features.extend([0.0] * (dim - len(features)))
        features = features[:dim]

        # Normalize
        if self.config.normalize_embeddings:
            norm = math.sqrt(sum(f * f for f in features))
            if norm > 0.0:
                features = [f / norm for f in features]

        return SpeakerEmbedding(
            vector=features,
            metadata={"model": "mock", "sample_count": n},
        )
