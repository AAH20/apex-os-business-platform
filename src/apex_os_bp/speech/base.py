"""Base classes and types for the speech processing system."""

from __future__ import annotations

import abc
import struct
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO


class SpeechError(Exception):
    """Base exception for all speech processing errors."""

    def __init__(self, message: str, component: str = "") -> None:
        self.component = component
        super().__init__(message)


@dataclass
class AudioConfig:
    """Configuration for audio processing.

    Attributes:
        sample_rate: Audio sample rate in Hz (default 16000).
        channels: Number of audio channels (default 1, mono).
        sample_width: Bytes per sample (default 2, 16-bit).
        chunk_size: Frames per processing chunk (default 1024).
        normalize: Whether to normalize audio to [-1, 1] range.
    """

    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    chunk_size: int = 1024
    normalize: bool = True

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.channels <= 0:
            raise ValueError("channels must be positive")
        if self.sample_width <= 0:
            raise ValueError("sample_width must be positive")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")


@dataclass
class AudioSegment:
    """A segment of audio data.

    Attributes:
        samples: Raw audio samples as a list of floats in [-1, 1].
        sample_rate: Sample rate in Hz.
        start_time: Start time in seconds relative to the source.
        end_time: End time in seconds relative to the source.
        metadata: Arbitrary metadata associated with this segment.
    """

    samples: list[float]
    sample_rate: int = 16000
    start_time: float = 0.0
    end_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.samples:
            raise ValueError("AudioSegment must contain at least one sample")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.end_time < self.start_time:
            raise ValueError("end_time must be >= start_time")

    @property
    def duration(self) -> float:
        """Duration of the segment in seconds."""
        return len(self.samples) / self.sample_rate

    @property
    def rms(self) -> float:
        """Root-mean-square amplitude of the segment."""
        if not self.samples:
            return 0.0
        return (sum(s * s for s in self.samples) / len(self.samples)) ** 0.5

    def to_bytes(self, sample_width: int = 2) -> bytes:
        """Convert samples to raw bytes.

        Args:
            sample_width: Bytes per sample (1, 2, or 4).

        Returns:
            Raw audio bytes.
        """
        if sample_width == 1:
            return bytes(int((s + 1.0) * 127.5) & 0xFF for s in self.samples)
        elif sample_width == 2:
            return b"".join(
                struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767))
                for s in self.samples
            )
        elif sample_width == 4:
            return b"".join(
                struct.pack("<i", int(max(-1.0, min(1.0, s)) * 2147483647))
                for s in self.samples
            )
        else:
            raise ValueError(f"Unsupported sample_width: {sample_width}")

    def to_wav(self, path: str | Path) -> Path:
        """Write the segment to a WAV file.

        Args:
            path: Output file path.

        Returns:
            The path that was written.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(self.to_bytes(2))
        return path

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        sample_rate: int = 16000,
        sample_width: int = 2,
        start_time: float = 0.0,
    ) -> AudioSegment:
        """Create an AudioSegment from raw bytes.

        Args:
            data: Raw audio bytes.
            sample_rate: Sample rate in Hz.
            sample_width: Bytes per sample.
            start_time: Start time offset in seconds.

        Returns:
            A new AudioSegment.
        """
        if sample_width == 2:
            count = len(data) // 2
            samples = [
                struct.unpack_from("<h", data, i * 2)[0] / 32768.0
                for i in range(count)
            ]
        elif sample_width == 1:
            samples = [(b - 128) / 128.0 for b in data]
        elif sample_width == 4:
            count = len(data) // 4
            samples = [
                struct.unpack_from("<i", data, i * 4)[0] / 2147483648.0
                for i in range(count)
            ]
        else:
            raise ValueError(f"Unsupported sample_width: {sample_width}")

        duration = len(samples) / sample_rate if sample_rate > 0 else 0.0
        return cls(
            samples=samples,
            sample_rate=sample_rate,
            start_time=start_time,
            end_time=start_time + duration,
        )

    @classmethod
    def from_wav(cls, path: str | Path) -> AudioSegment:
        """Load an AudioSegment from a WAV file.

        Args:
            path: Path to the WAV file.

        Returns:
            A new AudioSegment.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"WAV file not found: {path}")
        with wave.open(str(path), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        segment = cls.from_bytes(raw, sample_rate, sample_width)
        if channels > 1:
            # Downmix to mono by averaging channels
            samples = segment.samples
            mono: list[float] = []
            for i in range(0, len(samples), channels):
                chunk = samples[i : i + channels]
                mono.append(sum(chunk) / channels)
            segment = cls(
                samples=mono,
                sample_rate=sample_rate,
                start_time=0.0,
                end_time=len(mono) / sample_rate,
            )
        return segment

    @classmethod
    def silence(cls, duration: float, sample_rate: int = 16000) -> AudioSegment:
        """Create a silent audio segment.

        Args:
            duration: Duration in seconds.
            sample_rate: Sample rate in Hz.

        Returns:
            A silent AudioSegment.
        """
        n_samples = int(duration * sample_rate)
        return cls(
            samples=[0.0] * n_samples,
            sample_rate=sample_rate,
            start_time=0.0,
            end_time=duration,
        )

    @classmethod
    def generate_tone(
        cls,
        frequency: float,
        duration: float,
        sample_rate: int = 16000,
        amplitude: float = 0.5,
    ) -> AudioSegment:
        """Generate a sine wave tone.

        Args:
            frequency: Frequency in Hz.
            duration: Duration in seconds.
            sample_rate: Sample rate in Hz.
            amplitude: Amplitude in [0, 1].

        Returns:
            An AudioSegment containing the tone.
        """
        import math

        n_samples = int(duration * sample_rate)
        samples = [
            amplitude * math.sin(2.0 * math.pi * frequency * i / sample_rate)
            for i in range(n_samples)
        ]
        return cls(
            samples=samples,
            sample_rate=sample_rate,
            start_time=0.0,
            end_time=duration,
        )


class SpeechComponent(abc.ABC):
    """Abstract base class for all speech processing components.

    All concrete speech components must inherit from this class
    and implement the required abstract methods.
    """

    def __init__(self, config: Any = None) -> None:
        self._config = config
        self._initialized = False

    @property
    def config(self) -> Any:
        """The configuration object for this component."""
        return self._config

    @property
    def initialized(self) -> bool:
        """Whether the component has been initialized."""
        return self._initialized

    @abc.abstractmethod
    def initialize(self) -> None:
        """Initialize the component (load models, allocate resources)."""
        raise NotImplementedError

    @abc.abstractmethod
    def shutdown(self) -> None:
        """Release resources held by the component."""
        raise NotImplementedError

    def __enter__(self) -> SpeechComponent:
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.shutdown()
