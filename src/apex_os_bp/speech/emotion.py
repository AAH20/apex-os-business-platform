"""Emotion Detection component.

Detects emotional states from speech audio.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from apex_os_bp.speech.base import AudioSegment, SpeechComponent


# Standard emotion labels
EMOTION_LABELS = [
    "neutral",
    "happy",
    "sad",
    "angry",
    "fearful",
    "disgusted",
    "surprised",
]


@dataclass
class EmotionConfig:
    """Configuration for emotion detection.

    Attributes:
        model_name: Emotion model name ("speechbrain", "mock").
        labels: List of emotion labels to detect.
        threshold: Minimum confidence to report an emotion.
        use_smoothing: Whether to apply temporal smoothing.
        smoothing_window: Number of frames for smoothing.
    """

    model_name: str = "mock"
    labels: list[str] = field(default_factory=lambda: list(EMOTION_LABELS))
    threshold: float = 0.3
    use_smoothing: bool = True
    smoothing_window: int = 5

    def __post_init__(self) -> None:
        if not self.labels:
            raise ValueError("labels must not be empty")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be in [0.0, 1.0]")
        if self.smoothing_window < 1:
            raise ValueError("smoothing_window must be >= 1")


@dataclass
class EmotionResult:
    """Result of emotion detection.

    Attributes:
        primary_emotion: The dominant emotion label.
        confidence: Confidence score for the primary emotion in [0, 1].
        probabilities: Dict mapping emotion labels to probabilities.
        valence: Valence score in [-1, 1] (negative to positive).
        arousal: Arousal score in [0, 1] (calm to excited).
        metadata: Additional metadata.
    """

    primary_emotion: str
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)
    valence: float = 0.0
    arousal: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


class EmotionDetector(SpeechComponent):
    """Abstract base class for emotion detection engines."""

    @property
    def config(self) -> EmotionConfig:
        return self._config  # type: ignore[return-value]

    def detect(self, audio: AudioSegment) -> EmotionResult:
        """Detect emotion from an audio segment.

        Args:
            audio: The audio segment to analyze.

        Returns:
            An EmotionResult.
        """
        self._ensure_initialized()
        return self._detect_impl(audio)

    def detect_batch(self, segments: list[AudioSegment]) -> list[EmotionResult]:
        """Detect emotions for a batch of audio segments.

        Args:
            segments: List of audio segments.

        Returns:
            List of EmotionResult objects.
        """
        return [self.detect(seg) for seg in segments]

    @abc.abstractmethod
    def _detect_impl(self, audio: AudioSegment) -> EmotionResult:
        """Implementation-specific emotion detection logic."""
        raise NotImplementedError

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


class MockEmotionDetector(EmotionDetector):
    """Mock emotion detector for testing and fallback.

    Generates deterministic emotion predictions from audio features.
    """

    def __init__(self, config: EmotionConfig | None = None) -> None:
        super().__init__(config or EmotionConfig())

    def initialize(self) -> None:
        self._initialized = True

    def shutdown(self) -> None:
        self._initialized = False

    def _detect_impl(self, audio: AudioSegment) -> EmotionResult:
        """Generate deterministic emotion predictions from audio features.

        Uses audio statistics (RMS, zero-crossing rate, spectral centroid proxy)
        to derive emotion probabilities.
        """
        samples = audio.samples
        if not samples:
            samples = [0.0]

        n = len(samples)
        rms = audio.rms

        # Zero-crossing rate
        zcr = 0.0
        if n > 1:
            zcr = sum(
                1 for i in range(1, n) if samples[i - 1] * samples[i] < 0
            ) / n

        # Spectral centroid proxy (using sample differences)
        if n > 1:
            diffs = [abs(samples[i] - samples[i - 1]) for i in range(1, n)]
            mean_diff = sum(diffs) / len(diffs)
        else:
            mean_diff = 0.0

        # Map features to emotion probabilities
        # High RMS + high ZCR -> angry/surprised
        # Low RMS + low ZCR -> sad/neutral
        # Medium RMS + medium ZCR -> happy
        probs = self._compute_probabilities(rms, zcr, mean_diff)

        # Apply smoothing if enabled
        if self.config.use_smoothing:
            probs = self._smooth_probabilities(probs)

        # Find primary emotion
        primary = max(probs, key=probs.get)
        confidence = probs[primary]

        # Compute valence and arousal
        valence = self._compute_valence(probs)
        arousal = self._compute_arousal(probs, rms)

        return EmotionResult(
            primary_emotion=primary,
            confidence=confidence,
            probabilities=probs,
            valence=valence,
            arousal=arousal,
            metadata={
                "model": "mock",
                "rms": rms,
                "zcr": zcr,
                "mean_diff": mean_diff,
            },
        )

    def _compute_probabilities(
        self, rms: float, zcr: float, mean_diff: float
    ) -> dict[str, float]:
        """Compute emotion probabilities from audio features."""
        labels = self.config.labels
        probs: dict[str, float] = {label: 0.0 for label in labels}

        # Normalize features to [0, 1]
        norm_rms = min(1.0, rms * 3.0)
        norm_zcr = min(1.0, zcr * 5.0)
        norm_diff = min(1.0, mean_diff * 5.0)

        # Arousal-related emotions
        arousal = (norm_rms + norm_zcr + norm_diff) / 3.0

        if "angry" in probs:
            probs["angry"] = max(0.0, arousal - 0.3) * (0.5 + norm_zcr * 0.5)
        if "surprised" in probs:
            probs["surprised"] = max(0.0, arousal - 0.4) * (0.3 + norm_diff * 0.7)
        if "fearful" in probs:
            probs["fearful"] = max(0.0, arousal - 0.5) * norm_zcr

        # Positive emotions
        if "happy" in probs:
            probs["happy"] = max(0.0, 0.5 - abs(arousal - 0.5)) * (0.5 + norm_rms * 0.5)

        # Negative low-arousal emotions
        if "sad" in probs:
            probs["sad"] = max(0.0, 0.5 - arousal) * (0.5 + (1.0 - norm_rms) * 0.5)
        if "disgusted" in probs:
            probs["disgusted"] = max(0.0, 0.4 - arousal) * norm_diff * 0.5

        # Neutral
        if "neutral" in probs:
            probs["neutral"] = max(0.0, 1.0 - arousal * 2.0) * 0.8

        # Normalize to sum to 1
        total = sum(probs.values())
        if total > 0.0:
            probs = {k: v / total for k, v in probs.items()}
        else:
            # Fallback: uniform distribution
            uniform = 1.0 / len(labels)
            probs = {label: uniform for label in labels}

        return probs

    def _smooth_probabilities(self, probs: dict[str, float]) -> dict[str, float]:
        """Apply simple smoothing to probabilities."""
        # Simple smoothing: blend with uniform distribution
        n = len(probs)
        uniform = 1.0 / n
        alpha = 0.8  # Weight for original probabilities
        smoothed = {k: alpha * v + (1.0 - alpha) * uniform for k, v in probs.items()}
        # Renormalize
        total = sum(smoothed.values())
        if total > 0.0:
            smoothed = {k: v / total for k, v in smoothed.items()}
        return smoothed

    def _compute_valence(self, probs: dict[str, float]) -> float:
        """Compute valence in [-1, 1] from emotion probabilities."""
        positive = probs.get("happy", 0.0) + probs.get("surprised", 0.0) * 0.3
        negative = (
            probs.get("sad", 0.0)
            + probs.get("angry", 0.0)
            + probs.get("fearful", 0.0)
            + probs.get("disgusted", 0.0)
        )
        total = positive + negative
        if total == 0.0:
            return 0.0
        return (positive - negative) / total

    def _compute_arousal(self, probs: dict[str, float], rms: float) -> float:
        """Compute arousal in [0, 1] from emotion probabilities and RMS."""
        high_arousal = (
            probs.get("angry", 0.0)
            + probs.get("surprised", 0.0)
            + probs.get("fearful", 0.0)
        )
        low_arousal = probs.get("sad", 0.0) + probs.get("neutral", 0.0)
        total = high_arousal + low_arousal
        if total == 0.0:
            return min(1.0, rms * 3.0)
        return high_arousal / total
