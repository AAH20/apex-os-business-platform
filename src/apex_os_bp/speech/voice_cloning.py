"""Voice Cloning component.

Clones a voice from a reference audio sample and synthesizes speech
in that voice.
"""

from __future__ import annotations

import abc
import math
from dataclasses import dataclass, field
from typing import Any

from apex_os_bp.speech.base import AudioSegment, SpeechComponent, SpeechError


@dataclass
class VoiceCloningConfig:
    """Configuration for voice cloning.

    Attributes:
        model_name: Cloning model name ("mock", "tacotron2", "vits").
        sample_rate: Output sample rate in Hz.
        max_ref_duration: Maximum reference audio duration in seconds.
        min_ref_duration: Minimum reference audio duration in seconds.
        quality: Quality preset ("low", "medium", "high").
        preserve_prosody: Whether to preserve prosody from reference.
    """

    model_name: str = "mock"
    sample_rate: int = 22050
    max_ref_duration: float = 30.0
    min_ref_duration: float = 1.0
    quality: str = "medium"
    preserve_prosody: bool = True

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.min_ref_duration <= 0.0:
            raise ValueError("min_ref_duration must be positive")
        if self.max_ref_duration <= self.min_ref_duration:
            raise ValueError("max_ref_duration must be > min_ref_duration")
        if self.quality not in ("low", "medium", "high"):
            raise ValueError("quality must be 'low', 'medium', or 'high'")


@dataclass
class VoiceCloneResult:
    """Result of voice cloning synthesis.

    Attributes:
        audio: The synthesized audio in the cloned voice.
        text: The text that was synthesized.
        sample_rate: Sample rate of the output audio.
        duration: Duration of the synthesized audio in seconds.
        voice_id: Identifier for the cloned voice.
        metadata: Additional metadata.
    """

    audio: AudioSegment
    text: str
    sample_rate: int = 22050
    duration: float = 0.0
    voice_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class VoiceCloner(SpeechComponent):
    """Abstract base class for voice cloning engines."""

    @property
    def config(self) -> VoiceCloningConfig:
        return self._config  # type: ignore[return-value]

    def clone(self, reference_audio: AudioSegment, voice_id: str = "") -> Any:
        """Clone a voice from a reference audio sample.

        Args:
            reference_audio: The reference audio of the target voice.
            voice_id: An identifier for the cloned voice.

        Returns:
            A voice model/representation (type depends on implementation).
        """
        if not voice_id.strip():
            raise ValueError("voice_id must not be empty")
        if reference_audio.duration < self.config.min_ref_duration:
            raise SpeechError(
                f"Reference audio too short: {reference_audio.duration:.2f}s < "
                f"{self.config.min_ref_duration:.2f}s",
                "voice_cloning",
            )
        if reference_audio.duration > self.config.max_ref_duration:
            raise SpeechError(
                f"Reference audio too long: {reference_audio.duration:.2f}s > "
                f"{self.config.max_ref_duration:.2f}s",
                "voice_cloning",
            )
        self._ensure_initialized()
        return self._clone_impl(reference_audio, voice_id)

    def synthesize(
        self,
        text: str,
        voice_model: Any,
    ) -> VoiceCloneResult:
        """Synthesize text in the cloned voice.

        Args:
            text: The text to synthesize.
            voice_model: The voice model returned by clone().

        Returns:
            A VoiceCloneResult.
        """
        if not text.strip():
            raise ValueError("text must not be empty or whitespace")
        self._ensure_initialized()
        return self._synthesize_impl(text, voice_model)

    @abc.abstractmethod
    def _clone_impl(self, reference_audio: AudioSegment, voice_id: str) -> Any:
        """Implementation-specific voice cloning logic."""
        raise NotImplementedError

    @abc.abstractmethod
    def _synthesize_impl(self, text: str, voice_model: Any) -> VoiceCloneResult:
        """Implementation-specific synthesis logic."""
        raise NotImplementedError

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


class MockVoiceCloner(VoiceCloner):
    """Mock voice cloner for testing and fallback.

    Creates a deterministic voice profile from reference audio and
    synthesizes audio modulated by that profile.
    """

    def __init__(self, config: VoiceCloningConfig | None = None) -> None:
        super().__init__(config or VoiceCloningConfig())

    def initialize(self) -> None:
        self._initialized = True

    def shutdown(self) -> None:
        self._initialized = False

    def _clone_impl(self, reference_audio: AudioSegment, voice_id: str) -> dict[str, Any]:
        """Create a voice profile from reference audio.

        Extracts deterministic features from the reference audio to
        create a reproducible voice profile.
        """
        samples = reference_audio.samples
        n = len(samples)
        if n == 0:
            samples = [0.0]
            n = 1

        # Extract pitch proxy (dominant frequency via zero-crossing rate)
        zcr = 0.0
        if n > 1:
            zcr = sum(
                1 for i in range(1, n) if samples[i - 1] * samples[i] < 0
            ) / n
        pitch_proxy = zcr * reference_audio.sample_rate / 2.0

        # Extract energy profile
        rms = reference_audio.rms

        # Extract spectral features (band energies)
        n_bands = 16
        band_size = max(1, n // n_bands)
        band_energies: list[float] = []
        for i in range(n_bands):
            start = i * band_size
            end = min(start + band_size, n)
            band = samples[start:end]
            energy = sum(s * s for s in band) / max(1, len(band))
            band_energies.append(energy)

        # Compute tempo proxy (rate of energy changes)
        if n > 1:
            diffs = [abs(samples[i] - samples[i - 1]) for i in range(1, n)]
            tempo_proxy = sum(diffs) / len(diffs)
        else:
            tempo_proxy = 0.0

        voice_profile = {
            "voice_id": voice_id,
            "pitch_proxy": pitch_proxy,
            "rms": rms,
            "band_energies": band_energies,
            "tempo_proxy": tempo_proxy,
            "sample_rate": reference_audio.sample_rate,
            "duration": reference_audio.duration,
            "model": "mock",
        }
        return voice_profile

    def _synthesize_impl(self, text: str, voice_model: dict[str, Any]) -> VoiceCloneResult:
        """Synthesize audio modulated by the voice profile.

        Generates deterministic synthetic audio whose characteristics
        are influenced by the voice profile.
        """
        sample_rate = self.config.sample_rate
        words = text.split()
        if not words:
            words = ["silence"]

        pitch_proxy = voice_model.get("pitch_proxy", 200.0)
        rms = voice_model.get("rms", 0.1)
        tempo_proxy = voice_model.get("tempo_proxy", 0.01)
        band_energies = voice_model.get("band_energies", [0.0] * 16)

        all_samples: list[float] = []
        for i, word in enumerate(words):
            # Modulate frequency by voice pitch and word content
            word_hash = sum(ord(c) for c in word)
            base_freq = pitch_proxy * (0.8 + 0.4 * ((word_hash % 100) / 100.0))
            # Duration influenced by tempo proxy
            word_duration = max(0.1, min(0.6, len(word) * 0.05 + tempo_proxy * 2.0))
            n_samples = int(word_duration * sample_rate)

            # Amplitude from voice RMS
            amplitude = min(1.0, rms * 2.0) * 0.3

            for j in range(n_samples):
                t = j / sample_rate
                # Envelope
                envelope = math.sin(math.pi * j / n_samples) ** 0.5
                # Add harmonics based on band energies
                sample_val = 0.0
                for harmonic in range(1, 4):
                    harmonic_amp = amplitude / harmonic
                    sample_val += harmonic_amp * math.sin(
                        2.0 * math.pi * base_freq * harmonic * t
                    )
                sample_val *= envelope
                all_samples.append(sample_val)

            # Inter-word silence
            silence_samples = int(0.05 * sample_rate)
            all_samples.extend([0.0] * silence_samples)

        audio = AudioSegment(
            samples=all_samples,
            sample_rate=sample_rate,
            start_time=0.0,
            end_time=len(all_samples) / sample_rate,
        )
        return VoiceCloneResult(
            audio=audio,
            text=text,
            sample_rate=sample_rate,
            duration=audio.duration,
            voice_id=voice_model.get("voice_id", ""),
            metadata={
                "model": "mock",
                "pitch_proxy": pitch_proxy,
                "n_words": len(words),
            },
        )
