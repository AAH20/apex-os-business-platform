"""Deepened speech module: ASR, TTS, speaker ID, emotion recognition, real-time transcription."""

from __future__ import annotations

import io
import tempfile
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    speaker: Optional[str] = None
    emotion: Optional[Emotion] = None
    confidence: float = 0.0


@dataclass
class SpeakerProfile:
    speaker_id: str
    name: str
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthesisResult:
    audio_data: bytes
    sample_rate: int
    duration: float
    format: str = "wav"


class ASRProcessor:
    """Speech-to-text with confidence scoring."""

    def __init__(self, model_name: str = "whisper-base", language: str = "en",
                 sample_rate: int = 16000) -> None:
        self.model_name, self.language, self.sample_rate = model_name, language, sample_rate
        self._model: Any = None
        try:
            import whisper  # type: ignore
            self._model = whisper.load_model(model_name)
        except ImportError:
            pass

    def transcribe(self, audio: bytes, language: Optional[str] = None) -> TranscriptSegment:
        if self._model is None:
            return TranscriptSegment(text="[ASR unavailable]", start=0.0,
                                     end=len(audio) / (self.sample_rate * 2), confidence=0.0)
        import numpy as np  # type: ignore
        arr = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        result = self._model.transcribe(arr, language=language or self.language)
        segs = result.get("segments", [])
        conf = max(0.0, min(1.0, 1.0 + sum(s.get("avg_logprob", -1) for s in segs) / len(segs))) if segs else 0.0
        return TranscriptSegment(text=result.get("text", "").strip(),
                                 start=segs[0].get("start", 0.0) if segs else 0.0,
                                 end=segs[-1].get("end", 0.0) if segs else 0.0, confidence=conf)

    def transcribe_file(self, path: str | Path) -> TranscriptSegment:
        return self.transcribe(Path(path).read_bytes())


class TTSProcessor:
    """Multi-backend text-to-speech."""

    def __init__(self, engine: str = "auto", voice: str = "default",
                 sample_rate: int = 22050, speed: float = 1.0) -> None:
        self.voice, self.sample_rate, self.speed = voice, sample_rate, speed
        self._engine_instance: Any = None
        if engine in ("auto", "pyttsx3"):
            try:
                import pyttsx3  # type: ignore
                self._engine_instance = pyttsx3.init()
                self._engine_instance.setProperty("rate", int(200 * speed))
                self.engine = "pyttsx3"
                return
            except ImportError:
                pass
        if engine in ("auto", "gtts"):
            try:
                import gtts  # type: ignore # noqa: F401
                self.engine = "gtts"
                return
            except ImportError:
                pass
        self.engine = "unavailable"

    def synthesize(self, text: str, voice: Optional[str] = None) -> SynthesisResult:
        if not text.strip():
            return SynthesisResult(b"", self.sample_rate, 0.0)
        if self.engine == "pyttsx3" and self._engine_instance:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp = f.name
            self._engine_instance.save_to_file(text, tmp)
            self._engine_instance.runAndWait()
            data = Path(tmp).read_bytes()
            Path(tmp).unlink(missing_ok=True)
            return SynthesisResult(data, self.sample_rate, len(data) / (self.sample_rate * 2))
        if self.engine == "gtts":
            from gtts import gTTS  # type: ignore
            buf = io.BytesIO()
            gTTS(text=text, lang="en", slow=self.speed < 0.9).write_to_fp(buf)
            data = buf.getvalue()
            return SynthesisResult(data, self.sample_rate, len(data) / (self.sample_rate * 2), "mp3")
        return SynthesisResult(b"", self.sample_rate, 0.0)

    def stream_synthesize(self, text: str, cb: Callable[[bytes], None]) -> None:
        r = self.synthesize(text)
        for i in range(0, len(r.audio_data), 4096):
            cb(r.audio_data[i:i + 4096])


class SpeakerIdentifier:
    """Speaker enrollment and identification via voice embeddings."""

    def __init__(self, threshold: float = 0.75, embedding_dim: int = 256) -> None:
        self.threshold, self.embedding_dim = threshold, embedding_dim
        self._profiles: dict[str, SpeakerProfile] = {}
        self._extractor: Any = None
        try:
            from resemblyzer import VoiceEncoder  # type: ignore
            self._extractor = VoiceEncoder()
        except ImportError:
            pass

    def enroll(self, speaker_id: str, name: str, audio_samples: list[bytes]) -> SpeakerProfile:
        embs = [self._embed(a) for a in audio_samples if a]
        if not embs:
            raise ValueError("No valid audio samples")
        avg = [sum(e[i] for e in embs) / len(embs) for i in range(self.embedding_dim)]
        prof = SpeakerProfile(speaker_id=speaker_id, name=name, embedding=avg)
        self._profiles[speaker_id] = prof
        return prof

    def identify(self, audio: bytes) -> Optional[SpeakerProfile]:
        if not self._profiles:
            return None
        emb = self._embed(audio)
        best_id, best_score = None, -1.0
        for sid, prof in self._profiles.items():
            score = self._cosine(emb, prof.embedding)
            if score > best_score:
                best_id, best_score = sid, score
        return self._profiles[best_id] if best_id and best_score >= self.threshold else None

    def _embed(self, audio: bytes) -> list[float]:
        if self._extractor:
            import numpy as np  # type: ignore
            arr = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            return self._extractor.embed_utterance(arr).tolist()
        import hashlib
        return [b / 255.0 for b in hashlib.sha256(audio).digest()[:self.embedding_dim]]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        ma, mb = sum(x * x for x in a) ** 0.5, sum(y * y for y in b) ** 0.5
        return dot / (ma * mb) if ma and mb else 0.0

    def remove_profile(self, speaker_id: str) -> bool:
        return self._profiles.pop(speaker_id, None) is not None

    @property
    def profiles(self) -> dict[str, SpeakerProfile]:
        return dict(self._profiles)


class EmotionRecognizer:
    """Classify emotional content from speech."""

    EMOTIONS = list(Emotion)

    def __init__(self) -> None:
        self._model: Any = None
        try:
            from transformers import pipeline  # type: ignore
            self._model = pipeline("audio-classification",
                                   model="ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition")
        except ImportError:
            pass

    def recognize(self, audio: bytes) -> tuple[Emotion, dict[Emotion, float]]:
        if self._model is None:
            return Emotion.NEUTRAL, {e: 1.0 / len(self.EMOTIONS) for e in self.EMOTIONS}
        import numpy as np  # type: ignore
        arr = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        results = self._model(arr, sampling_rate=16000)
        scores: dict[Emotion, float] = {e: 0.0 for e in self.EMOTIONS}
        for r in results:
            for e in self.EMOTIONS:
                if e.value in r["label"].lower():
                    scores[e] = r["score"]
                    break
        return max(scores, key=scores.get), scores  # type: ignore


class RealtimeTranscriber:
    """Streaming real-time transcription with speaker and emotion tagging."""

    def __init__(self, asr: Optional[ASRProcessor] = None,
                 speaker_id: Optional[SpeakerIdentifier] = None,
                 emotion: Optional[EmotionRecognizer] = None,
                 buffer_duration: float = 3.0) -> None:
        self.asr = asr or ASRProcessor()
        self.speaker_id, self.emotion = speaker_id, emotion or EmotionRecognizer()
        self.buffer_duration = buffer_duration
        self._buf = bytearray()
        self._transcripts: list[TranscriptSegment] = []
        self._running = False
        self._cb: Optional[Callable[[TranscriptSegment], None]] = None
        self._lock = threading.Lock()

    def start(self, on_segment: Optional[Callable[[TranscriptSegment], None]] = None) -> None:
        self._cb, self._running = on_segment, True
        self._buf.clear()
        self._transcripts.clear()

    def stop(self) -> list[TranscriptSegment]:
        self._running = False
        if self._buf:
            self._process(bytes(self._buf))
            self._buf.clear()
        return list(self._transcripts)

    def feed(self, chunk: bytes) -> None:
        if not self._running:
            return
        with self._lock:
            self._buf.extend(chunk)
            max_b = int(self.buffer_duration * self.asr.sample_rate * 2)
            if len(self._buf) >= max_b:
                self._process(bytes(self._buf[:max_b]))
                self._buf = self._buf[max_b:]

    def _process(self, audio: bytes) -> None:
        seg = self.asr.transcribe(audio)
        if not seg.text or seg.text.startswith("["):
            return
        if self.speaker_id:
            spk = self.speaker_id.identify(audio)
            if spk:
                seg.speaker = spk.name
        seg.emotion, _ = self.emotion.recognize(audio)
        self._transcripts.append(seg)
        if self._cb:
            self._cb(seg)

    @property
    def transcripts(self) -> list[TranscriptSegment]:
        return list(self._transcripts)


class SpeechPipeline:
    """Unified pipeline orchestrating all speech capabilities."""

    def __init__(self, asr: Optional[ASRProcessor] = None,
                 tts: Optional[TTSProcessor] = None,
                 speaker_id: Optional[SpeakerIdentifier] = None,
                 emotion: Optional[EmotionRecognizer] = None) -> None:
        self.asr = asr or ASRProcessor()
        self.tts = tts or TTSProcessor()
        self.speaker_id = speaker_id or SpeakerIdentifier()
        self.emotion = emotion or EmotionRecognizer()
        self.realtime = RealtimeTranscriber(self.asr, self.speaker_id, self.emotion)

    def transcribe(self, audio: bytes) -> TranscriptSegment:
        seg = self.asr.transcribe(audio)
        spk = self.speaker_id.identify(audio)
        if spk:
            seg.speaker = spk.name
        seg.emotion, _ = self.emotion.recognize(audio)
        return seg

    def speak(self, text: str) -> SynthesisResult:
        return self.tts.synthesize(text)

    def enroll_speaker(self, sid: str, name: str, samples: list[bytes]) -> SpeakerProfile:
        return self.speaker_id.enroll(sid, name, samples)

    def start_realtime(self, cb: Optional[Callable[[TranscriptSegment], None]] = None) -> None:
        self.realtime.start(cb)

    def stop_realtime(self) -> list[TranscriptSegment]:
        return self.realtime.stop()

    def feed_audio(self, chunk: bytes) -> None:
        self.realtime.feed(chunk)
