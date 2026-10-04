"""Speech-to-Text (STT) component.

Provides transcription of audio into text using Whisper or a mock fallback.
"""

from __future__ import annotations

import abc
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apex_os_bp.speech.base import AudioSegment, SpeechComponent, SpeechError


@dataclass
class STTConfig:
    """Configuration for speech-to-text.

    Attributes:
        model_size: Whisper model size ("tiny", "base", "small", "medium", "large").
        language: Target language code (e.g., "en", "es"). Auto-detect if None.
        device: Compute device ("cpu", "cuda", "auto").
        compute_type: Compute precision ("float16", "float32", "int8").
        beam_size: Beam search width.
        temperature: Sampling temperature.
        condition_on_previous_text: Whether to condition on previous transcription.
        initial_prompt: Optional initial prompt to guide transcription.
    """

    model_size: str = "base"
    language: str | None = None
    device: str = "auto"
    compute_type: str = "float16"
    beam_size: int = 5
    temperature: float = 0.0
    condition_on_previous_text: bool = True
    initial_prompt: str | None = None

    def __post_init__(self) -> None:
        valid_sizes = {"tiny", "base", "small", "medium", "large", "large-v2", "large-v3"}
        if self.model_size not in valid_sizes:
            raise ValueError(f"model_size must be one of {valid_sizes}")
        if self.beam_size < 1:
            raise ValueError("beam_size must be >= 1")
        if self.temperature < 0.0:
            raise ValueError("temperature must be >= 0.0")


@dataclass
class TranscriptionResult:
    """Result of a speech-to-text transcription.

    Attributes:
        text: The transcribed text.
        language: Detected or specified language code.
        confidence: Confidence score in [0, 1].
        segments: List of (start, end, text) tuples for each segment.
        duration: Total audio duration in seconds.
        metadata: Additional metadata.
    """

    text: str
    language: str = "en"
    confidence: float = 0.0
    segments: list[tuple[float, float, str]] = field(default_factory=list)
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class SpeechToText(SpeechComponent):
    """Abstract base class for speech-to-text engines."""

    @property
    def config(self) -> STTConfig:
        return self._config  # type: ignore[return-value]

    def transcribe(self, audio: AudioSegment) -> TranscriptionResult:
        """Transcribe an audio segment to text.

        Args:
            audio: The audio segment to transcribe.

        Returns:
            A TranscriptionResult.
        """
        self._ensure_initialized()
        return self._transcribe_impl(audio)

    def transcribe_file(self, path: str | Path) -> TranscriptionResult:
        """Transcribe an audio file to text.

        Args:
            path: Path to the audio file (WAV format).

        Returns:
            A TranscriptionResult.
        """
        audio = AudioSegment.from_wav(path)
        return self.transcribe(audio)

    @abc.abstractmethod
    def _transcribe_impl(self, audio: AudioSegment) -> TranscriptionResult:
        """Implementation-specific transcription logic."""
        raise NotImplementedError

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


class WhisperSTT(SpeechToText):
    """Whisper-based speech-to-text implementation.

    Uses OpenAI's Whisper model for high-quality transcription.
    Falls back to MockSTT if whisper is not available.
    """

    def __init__(self, config: STTConfig | None = None) -> None:
        super().__init__(config or STTConfig())
        self._model: Any = None
        self._fallback: MockSTT | None = None

    def initialize(self) -> None:
        """Load the Whisper model."""
        try:
            import faster_whisper  # type: ignore

            device = self.config.device
            if device == "auto":
                device = "cuda" if self._cuda_available() else "cpu"

            self._model = faster_whisper.WhisperModel(
                self.config.model_size,
                device=device,
                compute_type=self.config.compute_type,
            )
            self._initialized = True
        except ImportError:
            self._fallback = MockSTT()
            self._fallback.initialize()
            self._initialized = True

    def shutdown(self) -> None:
        """Release the Whisper model."""
        self._model = None
        if self._fallback:
            self._fallback.shutdown()
        self._initialized = False

    def _transcribe_impl(self, audio: AudioSegment) -> TranscriptionResult:
        if self._fallback:
            return self._fallback.transcribe(audio)
        if self._model is None:
            raise SpeechError("Whisper model not loaded", "stt")

        # Write audio to a temp WAV file for Whisper
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            audio.to_wav(tmp_path)
            segments_gen, info = self._model.transcribe(
                tmp_path,
                language=self.config.language,
                beam_size=self.config.beam_size,
                temperature=self.config.temperature,
                condition_on_previous_text=self.config.condition_on_previous_text,
                initial_prompt=self.config.initial_prompt,
            )
            segments_list: list[tuple[float, float, str]] = []
            full_text_parts: list[str] = []
            for seg in segments_gen:
                segments_list.append((seg.start, seg.end, seg.text))
                full_text_parts.append(seg.text)

            full_text = "".join(full_text_parts).strip()
            return TranscriptionResult(
                text=full_text,
                language=info.language,
                confidence=getattr(info, "language_probability", 0.0),
                segments=segments_list,
                duration=audio.duration,
                metadata={"model": "whisper", "model_size": self.config.model_size},
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch  # type: ignore

            return torch.cuda.is_available()
        except ImportError:
            return False


class MockSTT(SpeechToText):
    """Mock STT for testing and fallback.

    Generates deterministic pseudo-transcriptions based on audio characteristics.
    """

    def __init__(self, config: STTConfig | None = None) -> None:
        super().__init__(config or STTConfig())

    def initialize(self) -> None:
        self._initialized = True

    def shutdown(self) -> None:
        self._initialized = False

    def _transcribe_impl(self, audio: AudioSegment) -> TranscriptionResult:
        """Generate a deterministic mock transcription.

        The output is derived from audio properties so tests are reproducible.
        """
        rms = audio.rms
        duration = audio.duration

        # Generate deterministic text based on audio characteristics
        words = self._generate_words(rms, duration)
        text = " ".join(words)

        # Create mock segments
        n_segments = max(1, int(duration / 2.0))
        seg_duration = duration / n_segments if n_segments > 0 else duration
        segments: list[tuple[float, float, str]] = []
        for i in range(n_segments):
            start = i * seg_duration
            end = start + seg_duration
            seg_text = " ".join(
                words[i * 2 : (i + 1) * 2] or [words[0] if words else "silence"]
            )
            segments.append((start, end, seg_text))

        confidence = min(1.0, 0.5 + rms * 2.0)

        return TranscriptionResult(
            text=text,
            language=self.config.language or "en",
            confidence=confidence,
            segments=segments,
            duration=duration,
            metadata={"model": "mock", "rms": rms},
        )

    def _generate_words(self, rms: float, duration: float) -> list[str]:
        """Generate a deterministic word list from audio properties."""
        vocabulary = [
            "the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
            "hello", "world", "speech", "recognition", "system", "audio",
            "processing", "language", "model", "neural", "network", "data",
            "signal", "frequency", "amplitude", "wave", "sound", "voice",
        ]
        # Use audio properties to seed word selection
        seed_val = int(rms * 10000) + int(duration * 100)
        n_words = max(3, min(20, int(duration * 2) + 3))
        words: list[str] = []
        for i in range(n_words):
            idx = (seed_val + i * 7) % len(vocabulary)
            words.append(vocabulary[idx])
        return words
