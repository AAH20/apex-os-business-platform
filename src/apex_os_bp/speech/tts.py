"""Text-to-Speech (TTS) component.

Converts text into spoken audio using pyttsx3 or a mock fallback.
"""

from __future__ import annotations

import abc
import io
import math
import struct
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apex_os_bp.speech.base import AudioSegment, SpeechComponent, SpeechError


@dataclass
class TTSConfig:
    """Configuration for text-to-speech.

    Attributes:
        voice: Voice identifier (engine-specific).
        rate: Speech rate in words per minute (default 150).
        volume: Volume level in [0.0, 1.0].
        pitch: Pitch adjustment (engine-specific, default 1.0).
        sample_rate: Output sample rate in Hz.
        output_format: Output audio format ("wav", "raw").
    """

    voice: str | None = None
    rate: int = 150
    volume: float = 0.9
    pitch: float = 1.0
    sample_rate: int = 22050
    output_format: str = "wav"

    def __post_init__(self) -> None:
        if self.rate < 50 or self.rate > 400:
            raise ValueError("rate must be between 50 and 400")
        if not 0.0 <= self.volume <= 1.0:
            raise ValueError("volume must be in [0.0, 1.0]")
        if self.pitch <= 0.0:
            raise ValueError("pitch must be positive")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")


@dataclass
class TTSResult:
    """Result of a text-to-speech synthesis.

    Attributes:
        audio: The synthesized audio segment.
        text: The input text that was synthesized.
        sample_rate: Sample rate of the output audio.
        duration: Duration of the synthesized audio in seconds.
        metadata: Additional metadata.
    """

    audio: AudioSegment
    text: str
    sample_rate: int = 22050
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class TextToSpeech(SpeechComponent):
    """Abstract base class for text-to-speech engines."""

    @property
    def config(self) -> TTSConfig:
        return self._config  # type: ignore[return-value]

    def synthesize(self, text: str) -> TTSResult:
        """Synthesize text into audio.

        Args:
            text: The text to synthesize.

        Returns:
            A TTSResult containing the synthesized audio.
        """
        if not text.strip():
            raise ValueError("text must not be empty or whitespace")
        self._ensure_initialized()
        return self._synthesize_impl(text)

    def synthesize_to_file(self, text: str, path: str | Path) -> Path:
        """Synthesize text and save to a WAV file.

        Args:
            text: The text to synthesize.
            path: Output file path.

        Returns:
            The path that was written.
        """
        result = self.synthesize(text)
        return result.audio.to_wav(path)

    @abc.abstractmethod
    def _synthesize_impl(self, text: str) -> TTSResult:
        """Implementation-specific synthesis logic."""
        raise NotImplementedError

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


class Pyttsx3TTS(TextToSpeech):
    """pyttsx3-based text-to-speech implementation.

    Uses the pyttsx3 offline TTS engine. Falls back to MockTTS if
    pyttsx3 is not available.
    """

    def __init__(self, config: TTSConfig | None = None) -> None:
        super().__init__(config or TTSConfig())
        self._engine: Any = None
        self._fallback: MockTTS | None = None

    def initialize(self) -> None:
        """Initialize the pyttsx3 engine."""
        try:
            import pyttsx3  # type: ignore

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.config.rate)
            self._engine.setProperty("volume", self.config.volume)
            if self.config.voice:
                voices = self._engine.getProperty("voices")
                for v in voices:
                    if self.config.voice in v.id:
                        self._engine.setProperty("voice", v.id)
                        break
            self._initialized = True
        except ImportError:
            self._fallback = MockTTS(self.config)
            self._fallback.initialize()
            self._initialized = True

    def shutdown(self) -> None:
        """Stop the pyttsx3 engine."""
        if self._engine:
            self._engine.stop()
        self._engine = None
        if self._fallback:
            self._fallback.shutdown()
        self._initialized = False

    def _synthesize_impl(self, text: str) -> TTSResult:
        if self._fallback:
            return self._fallback.synthesize(text)
        if self._engine is None:
            raise SpeechError("TTS engine not initialized", "tts")

        # pyttsx3 writes to file; use a temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            self._engine.save_to_file(text, tmp_path)
            self._engine.runAndWait()
            audio = AudioSegment.from_wav(tmp_path)
            return TTSResult(
                audio=audio,
                text=text,
                sample_rate=audio.sample_rate,
                duration=audio.duration,
                metadata={"engine": "pyttsx3", "voice": self.config.voice},
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class MockTTS(TextToSpeech):
    """Mock TTS for testing and fallback.

    Generates deterministic synthetic audio from text characteristics.
    """

    def __init__(self, config: TTSConfig | None = None) -> None:
        super().__init__(config or TTSConfig())

    def initialize(self) -> None:
        self._initialized = True

    def shutdown(self) -> None:
        self._initialized = False

    def _synthesize_impl(self, text: str) -> TTSResult:
        """Generate deterministic synthetic audio from text.

        The output is a sequence of tones whose frequencies and durations
        are derived from the text content, making tests reproducible.
        """
        sample_rate = self.config.sample_rate
        words = text.split()
        if not words:
            words = ["silence"]

        all_samples: list[float] = []
        for i, word in enumerate(words):
            # Derive frequency from word content
            word_hash = sum(ord(c) for c in word)
            freq = 100.0 + (word_hash % 400)  # 100-500 Hz
            # Duration proportional to word length
            word_duration = max(0.1, min(0.5, len(word) * 0.06))
            n_samples = int(word_duration * sample_rate)
            for j in range(n_samples):
                t = j / sample_rate
                # Apply pitch and amplitude envelope
                envelope = math.sin(math.pi * j / n_samples) ** 0.5
                sample_val = (
                    self.config.volume
                    * 0.3
                    * envelope
                    * math.sin(2.0 * math.pi * freq * self.config.pitch * t)
                )
                all_samples.append(sample_val)
            # Add brief silence between words
            silence_samples = int(0.05 * sample_rate)
            all_samples.extend([0.0] * silence_samples)

        audio = AudioSegment(
            samples=all_samples,
            sample_rate=sample_rate,
            start_time=0.0,
            end_time=len(all_samples) / sample_rate,
        )
        return TTSResult(
            audio=audio,
            text=text,
            sample_rate=sample_rate,
            duration=audio.duration,
            metadata={"engine": "mock", "n_words": len(words)},
        )
