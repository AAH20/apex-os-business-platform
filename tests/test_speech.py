"""Comprehensive tests for the APEX-OS speech processing system."""

from __future__ import annotations

import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from apex_os_bp.speech import (
    AudioConfig,
    AudioSegment,
    EmotionConfig,
    EmotionDetector,
    EmotionResult,
    MockEmotionDetector,
    MockSTT,
    MockTTS,
    MockVoiceCloner,
    MockSpeakerRecognition,
    SpeakerConfig,
    SpeakerEmbedding,
    SpeakerRecognition,
    SpeechError,
    SpeechToText,
    STTConfig,
    TextToSpeech,
    TranscriptionResult,
    TTSConfig,
    TTSResult,
    VoiceCloner,
    VoiceCloningConfig,
    VoiceCloneResult,
    WhisperSTT,
    Pyttsx3TTS,
    SpeakerIdentifier,
)


class TestAudioConfig(unittest.TestCase):
    """Tests for AudioConfig."""

    def test_default_values(self) -> None:
        config = AudioConfig()
        self.assertEqual(config.sample_rate, 16000)
        self.assertEqual(config.channels, 1)
        self.assertEqual(config.sample_width, 2)
        self.assertEqual(config.chunk_size, 1024)
        self.assertTrue(config.normalize)

    def test_custom_values(self) -> None:
        config = AudioConfig(sample_rate=44100, channels=2, sample_width=4)
        self.assertEqual(config.sample_rate, 44100)
        self.assertEqual(config.channels, 2)
        self.assertEqual(config.sample_width, 4)

    def test_invalid_sample_rate(self) -> None:
        with self.assertRaises(ValueError):
            AudioConfig(sample_rate=0)
        with self.assertRaises(ValueError):
            AudioConfig(sample_rate=-1)

    def test_invalid_channels(self) -> None:
        with self.assertRaises(ValueError):
            AudioConfig(channels=0)

    def test_invalid_sample_width(self) -> None:
        with self.assertRaises(ValueError):
            AudioConfig(sample_width=0)

    def test_invalid_chunk_size(self) -> None:
        with self.assertRaises(ValueError):
            AudioConfig(chunk_size=0)


class TestAudioSegment(unittest.TestCase):
    """Tests for AudioSegment."""

    def test_basic_creation(self) -> None:
        seg = AudioSegment(samples=[0.0, 0.5, -0.5], sample_rate=16000)
        self.assertEqual(len(seg.samples), 3)
        self.assertEqual(seg.sample_rate, 16000)
        self.assertAlmostEqual(seg.duration, 3.0 / 16000.0)

    def test_empty_samples_raises(self) -> None:
        with self.assertRaises(ValueError):
            AudioSegment(samples=[])

    def test_invalid_sample_rate(self) -> None:
        with self.assertRaises(ValueError):
            AudioSegment(samples=[0.0], sample_rate=0)

    def test_end_before_start_raises(self) -> None:
        with self.assertRaises(ValueError):
            AudioSegment(samples=[0.0], start_time=5.0, end_time=3.0)

    def test_rms(self) -> None:
        seg = AudioSegment(samples=[1.0, -1.0, 1.0, -1.0])
        self.assertAlmostEqual(seg.rms, 1.0)

    def test_rms_silence(self) -> None:
        seg = AudioSegment(samples=[0.0] * 100)
        self.assertAlmostEqual(seg.rms, 0.0)

    def test_to_bytes_16bit(self) -> None:
        seg = AudioSegment(samples=[0.0, 1.0, -1.0])
        raw = seg.to_bytes(2)
        self.assertEqual(len(raw), 6)  # 3 samples * 2 bytes
        vals = struct.unpack("<3h", raw)
        self.assertEqual(vals[0], 0)
        self.assertEqual(vals[1], 32767)
        self.assertEqual(vals[2], -32767)

    def test_to_bytes_8bit(self) -> None:
        seg = AudioSegment(samples=[0.0, 1.0, -1.0])
        raw = seg.to_bytes(1)
        self.assertEqual(len(raw), 3)

    def test_to_bytes_32bit(self) -> None:
        seg = AudioSegment(samples=[0.0, 0.5])
        raw = seg.to_bytes(4)
        self.assertEqual(len(raw), 8)

    def test_to_bytes_invalid_width(self) -> None:
        seg = AudioSegment(samples=[0.0])
        with self.assertRaises(ValueError):
            seg.to_bytes(3)

    def test_from_bytes_16bit(self) -> None:
        raw = struct.pack("<3h", 0, 16384, -16384)
        seg = AudioSegment.from_bytes(raw, sample_rate=16000, sample_width=2)
        self.assertEqual(len(seg.samples), 3)
        self.assertAlmostEqual(seg.samples[0], 0.0)
        self.assertAlmostEqual(seg.samples[1], 16384 / 32768.0, places=5)
        self.assertAlmostEqual(seg.samples[2], -16384 / 32768.0, places=5)

    def test_from_bytes_8bit(self) -> None:
        raw = bytes([128, 255, 0])
        seg = AudioSegment.from_bytes(raw, sample_rate=16000, sample_width=1)
        self.assertEqual(len(seg.samples), 3)
        self.assertAlmostEqual(seg.samples[0], 0.0, places=2)

    def test_from_bytes_32bit(self) -> None:
        raw = struct.pack("<2i", 0, 1073741824)
        seg = AudioSegment.from_bytes(raw, sample_rate=16000, sample_width=4)
        self.assertEqual(len(seg.samples), 2)

    def test_to_wav_and_back(self) -> None:
        seg = AudioSegment(samples=[0.0, 0.5, -0.5, 0.25], sample_rate=16000)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            seg.to_wav(path)
            loaded = AudioSegment.from_wav(path)
            self.assertEqual(len(loaded.samples), 4)
            self.assertEqual(loaded.sample_rate, 16000)
            for a, b in zip(seg.samples, loaded.samples):
                self.assertAlmostEqual(a, b, places=3)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_from_wav_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            AudioSegment.from_wav("/nonexistent/path.wav")

    def test_silence(self) -> None:
        seg = AudioSegment.silence(1.0, sample_rate=16000)
        self.assertEqual(len(seg.samples), 16000)
        self.assertAlmostEqual(seg.duration, 1.0)
        self.assertAlmostEqual(seg.rms, 0.0)

    def test_generate_tone(self) -> None:
        seg = AudioSegment.generate_tone(440.0, 0.1, sample_rate=16000)
        self.assertEqual(len(seg.samples), 1600)
        self.assertAlmostEqual(seg.duration, 0.1)
        # A 440Hz tone should have non-zero RMS
        self.assertGreater(seg.rms, 0.0)

    def test_metadata(self) -> None:
        seg = AudioSegment(samples=[0.0], metadata={"source": "test"})
        self.assertEqual(seg.metadata["source"], "test")


class TestSTTConfig(unittest.TestCase):
    """Tests for STTConfig."""

    def test_defaults(self) -> None:
        config = STTConfig()
        self.assertEqual(config.model_size, "base")
        self.assertIsNone(config.language)
        self.assertEqual(config.device, "auto")
        self.assertEqual(config.beam_size, 5)

    def test_invalid_model_size(self) -> None:
        with self.assertRaises(ValueError):
            STTConfig(model_size="invalid")

    def test_invalid_beam_size(self) -> None:
        with self.assertRaises(ValueError):
            STTConfig(beam_size=0)

    def test_invalid_temperature(self) -> None:
        with self.assertRaises(ValueError):
            STTConfig(temperature=-0.1)


class TestTranscriptionResult(unittest.TestCase):
    """Tests for TranscriptionResult."""

    def test_creation(self) -> None:
        result = TranscriptionResult(
            text="hello world",
            language="en",
            confidence=0.95,
            segments=[(0.0, 1.0, "hello"), (1.0, 2.0, "world")],
            duration=2.0,
        )
        self.assertEqual(result.text, "hello world")
        self.assertEqual(result.language, "en")
        self.assertAlmostEqual(result.confidence, 0.95)
        self.assertEqual(len(result.segments), 2)
        self.assertAlmostEqual(result.duration, 2.0)


class TestMockSTT(unittest.TestCase):
    """Tests for MockSTT."""

    def setUp(self) -> None:
        self.stt = MockSTT()
        self.stt.initialize()

    def tearDown(self) -> None:
        self.stt.shutdown()

    def test_initialization(self) -> None:
        self.assertTrue(self.stt.initialized)

    def test_transcribe_returns_result(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        result = self.stt.transcribe(audio)
        self.assertIsInstance(result, TranscriptionResult)
        self.assertTrue(len(result.text) > 0)
        self.assertEqual(result.language, "en")
        self.assertGreater(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_transcribe_deterministic(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        result1 = self.stt.transcribe(audio)
        result2 = self.stt.transcribe(audio)
        self.assertEqual(result1.text, result2.text)
        self.assertAlmostEqual(result1.confidence, result2.confidence)

    def test_transcribe_different_audio(self) -> None:
        audio1 = AudioSegment.generate_tone(440.0, 2.0)
        audio2 = AudioSegment.generate_tone(100.0, 5.0)
        result1 = self.stt.transcribe(audio1)
        result2 = self.stt.transcribe(audio2)
        # Different audio should produce different results
        self.assertNotEqual(result1.text, result2.text)

    def test_transcribe_file(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            audio.to_wav(path)
            result = self.stt.transcribe_file(path)
            self.assertIsInstance(result, TranscriptionResult)
            self.assertTrue(len(result.text) > 0)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_transcribe_silence(self) -> None:
        audio = AudioSegment.silence(2.0)
        result = self.stt.transcribe(audio)
        self.assertIsInstance(result, TranscriptionResult)

    def test_context_manager(self) -> None:
        with MockSTT() as stt:
            self.assertTrue(stt.initialized)
            audio = AudioSegment.generate_tone(440.0, 1.0)
            result = stt.transcribe(audio)
            self.assertIsInstance(result, TranscriptionResult)
        self.assertFalse(stt.initialized)

    def test_segments_populated(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 3.0)
        result = self.stt.transcribe(audio)
        self.assertGreater(len(result.segments), 0)
        for start, end, text in result.segments:
            self.assertGreaterEqual(start, 0.0)
            self.assertGreater(end, start)
            self.assertTrue(len(text) > 0)


class TestWhisperSTT(unittest.TestCase):
    """Tests for WhisperSTT (falls back to MockSTT)."""

    def test_initialization(self) -> None:
        stt = WhisperSTT()
        stt.initialize()
        self.assertTrue(stt.initialized)
        stt.shutdown()

    def test_transcribe(self) -> None:
        stt = WhisperSTT()
        stt.initialize()
        audio = AudioSegment.generate_tone(440.0, 2.0)
        result = stt.transcribe(audio)
        self.assertIsInstance(result, TranscriptionResult)
        stt.shutdown()


class TestTTSConfig(unittest.TestCase):
    """Tests for TTSConfig."""

    def test_defaults(self) -> None:
        config = TTSConfig()
        self.assertEqual(config.rate, 150)
        self.assertAlmostEqual(config.volume, 0.9)
        self.assertAlmostEqual(config.pitch, 1.0)
        self.assertEqual(config.sample_rate, 22050)

    def test_invalid_rate(self) -> None:
        with self.assertRaises(ValueError):
            TTSConfig(rate=10)
        with self.assertRaises(ValueError):
            TTSConfig(rate=500)

    def test_invalid_volume(self) -> None:
        with self.assertRaises(ValueError):
            TTSConfig(volume=-0.1)
        with self.assertRaises(ValueError):
            TTSConfig(volume=1.1)

    def test_invalid_pitch(self) -> None:
        with self.assertRaises(ValueError):
            TTSConfig(pitch=0.0)

    def test_invalid_sample_rate(self) -> None:
        with self.assertRaises(ValueError):
            TTSConfig(sample_rate=0)


class TestTTSResult(unittest.TestCase):
    """Tests for TTSResult."""

    def test_creation(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 1.0)
        result = TTSResult(audio=audio, text="hello", sample_rate=22050, duration=1.0)
        self.assertEqual(result.text, "hello")
        self.assertEqual(result.sample_rate, 22050)
        self.assertAlmostEqual(result.duration, 1.0)


class TestMockTTS(unittest.TestCase):
    """Tests for MockTTS."""

    def setUp(self) -> None:
        self.tts = MockTTS()
        self.tts.initialize()

    def tearDown(self) -> None:
        self.tts.shutdown()

    def test_initialization(self) -> None:
        self.assertTrue(self.tts.initialized)

    def test_synthesize_returns_result(self) -> None:
        result = self.tts.synthesize("hello world")
        self.assertIsInstance(result, TTSResult)
        self.assertEqual(result.text, "hello world")
        self.assertGreater(len(result.audio.samples), 0)
        self.assertEqual(result.sample_rate, 22050)
        self.assertGreater(result.duration, 0.0)

    def test_synthesize_deterministic(self) -> None:
        result1 = self.tts.synthesize("hello world")
        result2 = self.tts.synthesize("hello world")
        self.assertEqual(len(result1.audio.samples), len(result2.audio.samples))
        for a, b in zip(result1.audio.samples, result2.audio.samples):
            self.assertAlmostEqual(a, b)

    def test_synthesize_different_text(self) -> None:
        result1 = self.tts.synthesize("hello")
        result2 = self.tts.synthesize("hello world")
        self.assertNotEqual(len(result1.audio.samples), len(result2.audio.samples))

    def test_synthesize_empty_text_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.tts.synthesize("")
        with self.assertRaises(ValueError):
            self.tts.synthesize("   ")

    def test_synthesize_to_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            result_path = self.tts.synthesize_to_file("hello", path)
            self.assertTrue(Path(result_path).exists())
            audio = AudioSegment.from_wav(result_path)
            self.assertGreater(len(audio.samples), 0)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_context_manager(self) -> None:
        with MockTTS() as tts:
            self.assertTrue(tts.initialized)
            result = tts.synthesize("test")
            self.assertIsInstance(result, TTSResult)
        self.assertFalse(tts.initialized)

    def test_longer_text_produces_longer_audio(self) -> None:
        result_short = self.tts.synthesize("hi")
        result_long = self.tts.synthesize("hi there world")
        self.assertGreater(
            len(result_long.audio.samples), len(result_short.audio.samples)
        )


class TestPyttsx3TTS(unittest.TestCase):
    """Tests for Pyttsx3TTS (falls back to MockTTS)."""

    def test_initialization(self) -> None:
        tts = Pyttsx3TTS()
        tts.initialize()
        self.assertTrue(tts.initialized)
        tts.shutdown()

    def test_synthesize(self) -> None:
        tts = Pyttsx3TTS()
        tts.initialize()
        result = tts.synthesize("hello world")
        self.assertIsInstance(result, TTSResult)
        tts.shutdown()


class TestSpeakerConfig(unittest.TestCase):
    """Tests for SpeakerConfig."""

    def test_defaults(self) -> None:
        config = SpeakerConfig()
        self.assertEqual(config.model_name, "mock")
        self.assertEqual(config.embedding_dim, 256)
        self.assertAlmostEqual(config.threshold, 0.65)

    def test_invalid_embedding_dim(self) -> None:
        with self.assertRaises(ValueError):
            SpeakerConfig(embedding_dim=0)

    def test_invalid_threshold(self) -> None:
        with self.assertRaises(ValueError):
            SpeakerConfig(threshold=-0.1)
        with self.assertRaises(ValueError):
            SpeakerConfig(threshold=1.1)

    def test_invalid_min_audio_duration(self) -> None:
        with self.assertRaises(ValueError):
            SpeakerConfig(min_audio_duration=-1.0)

    def test_invalid_max_speakers(self) -> None:
        with self.assertRaises(ValueError):
            SpeakerConfig(max_speakers=0)


class TestSpeakerEmbedding(unittest.TestCase):
    """Tests for SpeakerEmbedding."""

    def test_creation(self) -> None:
        emb = SpeakerEmbedding(vector=[0.1, 0.2, 0.3], speaker_id="spk1")
        self.assertEqual(emb.dim, 3)
        self.assertEqual(emb.speaker_id, "spk1")

    def test_empty_vector_raises(self) -> None:
        with self.assertRaises(ValueError):
            SpeakerEmbedding(vector=[])

    def test_cosine_similarity_identical(self) -> None:
        emb = SpeakerEmbedding(vector=[1.0, 0.0, 0.0])
        self.assertAlmostEqual(emb.cosine_similarity(emb), 1.0)

    def test_cosine_similarity_orthogonal(self) -> None:
        emb1 = SpeakerEmbedding(vector=[1.0, 0.0])
        emb2 = SpeakerEmbedding(vector=[0.0, 1.0])
        self.assertAlmostEqual(emb1.cosine_similarity(emb2), 0.0)

    def test_cosine_similarity_opposite(self) -> None:
        emb1 = SpeakerEmbedding(vector=[1.0, 0.0])
        emb2 = SpeakerEmbedding(vector=[-1.0, 0.0])
        self.assertAlmostEqual(emb1.cosine_similarity(emb2), -1.0)

    def test_cosine_similarity_dimension_mismatch(self) -> None:
        emb1 = SpeakerEmbedding(vector=[1.0, 0.0])
        emb2 = SpeakerEmbedding(vector=[1.0, 0.0, 0.0])
        with self.assertRaises(ValueError):
            emb1.cosine_similarity(emb2)

    def test_to_from_bytes(self) -> None:
        emb = SpeakerEmbedding(vector=[0.1, 0.2, 0.3], speaker_id="spk1")
        raw = emb.to_bytes()
        restored = SpeakerEmbedding.from_bytes(raw, speaker_id="spk1")
        self.assertEqual(restored.dim, 3)
        for a, b in zip(emb.vector, restored.vector):
            self.assertAlmostEqual(a, b, places=5)


class TestMockSpeakerRecognition(unittest.TestCase):
    """Tests for MockSpeakerRecognition."""

    def setUp(self) -> None:
        self.sr = MockSpeakerRecognition()
        self.sr.initialize()

    def tearDown(self) -> None:
        self.sr.shutdown()

    def test_initialization(self) -> None:
        self.assertTrue(self.sr.initialized)

    def test_enroll_returns_embedding(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        emb = self.sr.enroll(audio, "speaker1")
        self.assertIsInstance(emb, SpeakerEmbedding)
        self.assertEqual(emb.speaker_id, "speaker1")
        self.assertEqual(emb.dim, 256)

    def test_enroll_empty_speaker_id_raises(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        with self.assertRaises(ValueError):
            self.sr.enroll(audio, "")

    def test_enroll_short_audio_raises(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 0.1)
        with self.assertRaises(SpeechError):
            self.sr.enroll(audio, "speaker1")

    def test_verify_same_speaker(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        emb = self.sr.enroll(audio, "speaker1")
        is_match, score = self.sr.verify(audio, emb)
        self.assertTrue(is_match)
        self.assertGreater(score, 0.65)

    def test_verify_different_speaker(self) -> None:
        audio1 = AudioSegment.generate_tone(440.0, 2.0)
        audio2 = AudioSegment.generate_tone(880.0, 2.0)
        emb1 = self.sr.enroll(audio1, "speaker1")
        is_match, score = self.sr.verify(audio2, emb1)
        # Different audio should have lower similarity
        self.assertLess(score, 1.0)

    def test_identify_correct_speaker(self) -> None:
        audio1 = AudioSegment.generate_tone(440.0, 2.0)
        audio2 = AudioSegment.generate_tone(880.0, 2.0)
        emb1 = self.sr.enroll(audio1, "alice")
        emb2 = self.sr.enroll(audio2, "bob")
        gallery = [emb1, emb2]

        # Identify using audio similar to alice's enrollment
        test_audio = AudioSegment.generate_tone(440.0, 2.0)
        speaker_id, confidence = self.sr.identify(test_audio, gallery)
        self.assertEqual(speaker_id, "alice")
        self.assertGreater(confidence, 0.0)

    def test_identify_unknown_speaker(self) -> None:
        audio1 = AudioSegment.generate_tone(440.0, 2.0)
        emb1 = self.sr.enroll(audio1, "alice")
        gallery = [emb1]

        # Very different audio
        test_audio = AudioSegment.generate_tone(100.0, 2.0)
        speaker_id, confidence = self.sr.identify(test_audio, gallery)
        # May or may not be unknown depending on threshold
        self.assertIsInstance(speaker_id, str)
        self.assertIsInstance(confidence, float)

    def test_identify_empty_gallery(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        speaker_id, confidence = self.sr.identify(audio, [])
        self.assertEqual(speaker_id, "unknown")
        self.assertAlmostEqual(confidence, 0.0)

    def test_enroll_deterministic(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        emb1 = self.sr.enroll(audio, "speaker1")
        emb2 = self.sr.enroll(audio, "speaker1")
        for a, b in zip(emb1.vector, emb2.vector):
            self.assertAlmostEqual(a, b)

    def test_context_manager(self) -> None:
        with MockSpeakerRecognition() as sr:
            self.assertTrue(sr.initialized)
            audio = AudioSegment.generate_tone(440.0, 2.0)
            emb = sr.enroll(audio, "test")
            self.assertIsInstance(emb, SpeakerEmbedding)
        self.assertFalse(sr.initialized)


class TestSpeakerIdentifier(unittest.TestCase):
    """Tests for SpeakerIdentifier (falls back to MockSpeakerRecognition)."""

    def test_initialization(self) -> None:
        sr = SpeakerIdentifier()
        sr.initialize()
        self.assertTrue(sr.initialized)
        sr.shutdown()

    def test_enroll_and_verify(self) -> None:
        sr = SpeakerIdentifier()
        sr.initialize()
        audio = AudioSegment.generate_tone(440.0, 2.0)
        emb = sr.enroll(audio, "speaker1")
        self.assertIsInstance(emb, SpeakerEmbedding)
        is_match, score = sr.verify(audio, emb)
        self.assertIsInstance(is_match, bool)
        self.assertIsInstance(score, float)
        sr.shutdown()


class TestEmotionConfig(unittest.TestCase):
    """Tests for EmotionConfig."""

    def test_defaults(self) -> None:
        config = EmotionConfig()
        self.assertEqual(config.model_name, "mock")
        self.assertIn("neutral", config.labels)
        self.assertIn("happy", config.labels)
        self.assertAlmostEqual(config.threshold, 0.3)

    def test_empty_labels_raises(self) -> None:
        with self.assertRaises(ValueError):
            EmotionConfig(labels=[])

    def test_invalid_threshold(self) -> None:
        with self.assertRaises(ValueError):
            EmotionConfig(threshold=-0.1)
        with self.assertRaises(ValueError):
            EmotionConfig(threshold=1.1)

    def test_invalid_smoothing_window(self) -> None:
        with self.assertRaises(ValueError):
            EmotionConfig(smoothing_window=0)


class TestEmotionResult(unittest.TestCase):
    """Tests for EmotionResult."""

    def test_creation(self) -> None:
        result = EmotionResult(
            primary_emotion="happy",
            confidence=0.85,
            probabilities={"happy": 0.85, "neutral": 0.15},
            valence=0.7,
            arousal=0.6,
        )
        self.assertEqual(result.primary_emotion, "happy")
        self.assertAlmostEqual(result.confidence, 0.85)
        self.assertAlmostEqual(result.valence, 0.7)
        self.assertAlmostEqual(result.arousal, 0.6)


class TestMockEmotionDetector(unittest.TestCase):
    """Tests for MockEmotionDetector."""

    def setUp(self) -> None:
        self.detector = MockEmotionDetector()
        self.detector.initialize()

    def tearDown(self) -> None:
        self.detector.shutdown()

    def test_initialization(self) -> None:
        self.assertTrue(self.detector.initialized)

    def test_detect_returns_result(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        result = self.detector.detect(audio)
        self.assertIsInstance(result, EmotionResult)
        self.assertIn(result.primary_emotion, self.detector.config.labels)
        self.assertGreater(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_detect_probabilities_sum_to_one(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        result = self.detector.detect(audio)
        total = sum(result.probabilities.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_detect_deterministic(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        result1 = self.detector.detect(audio)
        result2 = self.detector.detect(audio)
        self.assertEqual(result1.primary_emotion, result2.primary_emotion)
        self.assertAlmostEqual(result1.confidence, result2.confidence)

    def test_detect_different_audio(self) -> None:
        audio1 = AudioSegment.generate_tone(440.0, 2.0)
        audio2 = AudioSegment.generate_tone(100.0, 2.0)
        result1 = self.detector.detect(audio1)
        result2 = self.detector.detect(audio2)
        # Different audio may produce different emotions
        self.assertIsInstance(result1.primary_emotion, str)
        self.assertIsInstance(result2.primary_emotion, str)

    def test_detect_silence(self) -> None:
        audio = AudioSegment.silence(2.0)
        result = self.detector.detect(audio)
        self.assertIsInstance(result, EmotionResult)

    def test_detect_batch(self) -> None:
        segments = [
            AudioSegment.generate_tone(440.0, 2.0),
            AudioSegment.generate_tone(880.0, 2.0),
            AudioSegment.silence(2.0),
        ]
        results = self.detector.detect_batch(segments)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIsInstance(r, EmotionResult)

    def test_valence_range(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        result = self.detector.detect(audio)
        self.assertGreaterEqual(result.valence, -1.0)
        self.assertLessEqual(result.valence, 1.0)

    def test_arousal_range(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 2.0)
        result = self.detector.detect(audio)
        self.assertGreaterEqual(result.arousal, 0.0)
        self.assertLessEqual(result.arousal, 1.0)

    def test_context_manager(self) -> None:
        with MockEmotionDetector() as det:
            self.assertTrue(det.initialized)
            audio = AudioSegment.generate_tone(440.0, 2.0)
            result = det.detect(audio)
            self.assertIsInstance(result, EmotionResult)
        self.assertFalse(det.initialized)

    def test_high_arousal_emotion(self) -> None:
        # High-frequency, high-amplitude audio should produce high-arousal emotion
        audio = AudioSegment.generate_tone(1000.0, 2.0, amplitude=0.9)
        result = self.detector.detect(audio)
        self.assertIsInstance(result, EmotionResult)
        # Should have some non-neutral emotion
        self.assertGreater(result.arousal, 0.0)


class TestVoiceCloningConfig(unittest.TestCase):
    """Tests for VoiceCloningConfig."""

    def test_defaults(self) -> None:
        config = VoiceCloningConfig()
        self.assertEqual(config.model_name, "mock")
        self.assertEqual(config.sample_rate, 22050)
        self.assertEqual(config.quality, "medium")

    def test_invalid_sample_rate(self) -> None:
        with self.assertRaises(ValueError):
            VoiceCloningConfig(sample_rate=0)

    def test_invalid_min_ref_duration(self) -> None:
        with self.assertRaises(ValueError):
            VoiceCloningConfig(min_ref_duration=0.0)

    def test_invalid_max_ref_duration(self) -> None:
        with self.assertRaises(ValueError):
            VoiceCloningConfig(max_ref_duration=0.5, min_ref_duration=1.0)

    def test_invalid_quality(self) -> None:
        with self.assertRaises(ValueError):
            VoiceCloningConfig(quality="ultra")


class TestVoiceCloneResult(unittest.TestCase):
    """Tests for VoiceCloneResult."""

    def test_creation(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 1.0)
        result = VoiceCloneResult(
            audio=audio,
            text="hello",
            sample_rate=22050,
            duration=1.0,
            voice_id="voice1",
        )
        self.assertEqual(result.text, "hello")
        self.assertEqual(result.voice_id, "voice1")
        self.assertAlmostEqual(result.duration, 1.0)


class TestMockVoiceCloner(unittest.TestCase):
    """Tests for MockVoiceCloner."""

    def setUp(self) -> None:
        self.cloner = MockVoiceCloner()
        self.cloner.initialize()

    def tearDown(self) -> None:
        self.cloner.shutdown()

    def test_initialization(self) -> None:
        self.assertTrue(self.cloner.initialized)

    def test_clone_returns_voice_model(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 3.0)
        voice_model = self.cloner.clone(audio, "voice1")
        self.assertIsInstance(voice_model, dict)
        self.assertEqual(voice_model["voice_id"], "voice1")

    def test_clone_empty_voice_id_raises(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 3.0)
        with self.assertRaises(ValueError):
            self.cloner.clone(audio, "")

    def test_clone_short_audio_raises(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 0.1)
        with self.assertRaises(SpeechError):
            self.cloner.clone(audio, "voice1")

    def test_clone_long_audio_raises(self) -> None:
        audio = AudioSegment.silence(35.0)
        with self.assertRaises(SpeechError):
            self.cloner.clone(audio, "voice1")

    def test_synthesize_returns_result(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 3.0)
        voice_model = self.cloner.clone(audio, "voice1")
        result = self.cloner.synthesize("hello world", voice_model)
        self.assertIsInstance(result, VoiceCloneResult)
        self.assertEqual(result.text, "hello world")
        self.assertEqual(result.voice_id, "voice1")
        self.assertGreater(len(result.audio.samples), 0)
        self.assertGreater(result.duration, 0.0)

    def test_synthesize_empty_text_raises(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 3.0)
        voice_model = self.cloner.clone(audio, "voice1")
        with self.assertRaises(ValueError):
            self.cloner.synthesize("", voice_model)

    def test_synthesize_deterministic(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 3.0)
        voice_model = self.cloner.clone(audio, "voice1")
        result1 = self.cloner.synthesize("hello", voice_model)
        result2 = self.cloner.synthesize("hello", voice_model)
        self.assertEqual(len(result1.audio.samples), len(result2.audio.samples))

    def test_different_voices_produce_different_audio(self) -> None:
        audio1 = AudioSegment.generate_tone(440.0, 3.0)
        audio2 = AudioSegment.generate_tone(880.0, 3.0)
        voice1 = self.cloner.clone(audio1, "voice1")
        voice2 = self.cloner.clone(audio2, "voice2")
        result1 = self.cloner.synthesize("hello", voice1)
        result2 = self.cloner.synthesize("hello", voice2)
        # Different voices should produce different audio
        self.assertNotEqual(len(result1.audio.samples), len(result2.audio.samples))

    def test_context_manager(self) -> None:
        with MockVoiceCloner() as cloner:
            self.assertTrue(cloner.initialized)
            audio = AudioSegment.generate_tone(440.0, 3.0)
            voice_model = cloner.clone(audio, "test")
            result = cloner.synthesize("hello", voice_model)
            self.assertIsInstance(result, VoiceCloneResult)
        self.assertFalse(cloner.initialized)

    def test_voice_profile_contains_expected_keys(self) -> None:
        audio = AudioSegment.generate_tone(440.0, 3.0)
        voice_model = self.cloner.clone(audio, "voice1")
        expected_keys = {
            "voice_id",
            "pitch_proxy",
            "rms",
            "band_energies",
            "tempo_proxy",
            "sample_rate",
            "duration",
            "model",
        }
        self.assertEqual(set(voice_model.keys()), expected_keys)


class TestSpeechError(unittest.TestCase):
    """Tests for SpeechError."""

    def test_creation(self) -> None:
        err = SpeechError("test error", "stt")
        self.assertEqual(str(err), "test error")
        self.assertEqual(err.component, "stt")

    def test_default_component(self) -> None:
        err = SpeechError("test error")
        self.assertEqual(err.component, "")


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple speech components."""

    def test_stt_tts_roundtrip(self) -> None:
        """Test that STT and TTS can work together."""
        tts = MockTTS()
        tts.initialize()
        stt = MockSTT()
        stt.initialize()

        text = "hello world"
        tts_result = tts.synthesize(text)
        stt_result = stt.transcribe(tts_result.audio)

        self.assertIsInstance(stt_result, TranscriptionResult)
        self.assertTrue(len(stt_result.text) > 0)

        tts.shutdown()
        stt.shutdown()

    def test_speaker_recognition_with_stt(self) -> None:
        """Test speaker recognition alongside STT."""
        sr = MockSpeakerRecognition()
        sr.initialize()
        stt = MockSTT()
        stt.initialize()

        audio = AudioSegment.generate_tone(440.0, 2.0)
        emb = sr.enroll(audio, "speaker1")
        stt_result = stt.transcribe(audio)

        self.assertIsInstance(emb, SpeakerEmbedding)
        self.assertIsInstance(stt_result, TranscriptionResult)

        sr.shutdown()
        stt.shutdown()

    def test_emotion_with_speaker(self) -> None:
        """Test emotion detection alongside speaker recognition."""
        sr = MockSpeakerRecognition()
        sr.initialize()
        det = MockEmotionDetector()
        det.initialize()

        audio = AudioSegment.generate_tone(440.0, 2.0)
        emb = sr.enroll(audio, "speaker1")
        emo_result = det.detect(audio)

        self.assertIsInstance(emb, SpeakerEmbedding)
        self.assertIsInstance(emo_result, EmotionResult)

        sr.shutdown()
        det.shutdown()

    def test_voice_cloning_with_tts(self) -> None:
        """Test voice cloning alongside TTS."""
        cloner = MockVoiceCloner()
        cloner.initialize()
        tts = MockTTS()
        tts.initialize()

        ref_audio = AudioSegment.generate_tone(440.0, 3.0)
        voice_model = cloner.clone(ref_audio, "voice1")
        clone_result = cloner.synthesize("hello world", voice_model)
        tts_result = tts.synthesize("hello world")

        self.assertIsInstance(clone_result, VoiceCloneResult)
        self.assertIsInstance(tts_result, TTSResult)

        cloner.shutdown()
        tts.shutdown()

    def test_full_pipeline(self) -> None:
        """Test a full speech processing pipeline."""
        # Create components
        stt = MockSTT()
        tts = MockTTS()
        sr = MockSpeakerRecognition()
        det = MockEmotionDetector()
        cloner = MockVoiceCloner()

        for comp in [stt, tts, sr, det, cloner]:
            comp.initialize()

        try:
            # 1. Synthesize speech
            text = "hello world this is a test"
            tts_result = tts.synthesize(text)
            self.assertIsInstance(tts_result, TTSResult)

            # 2. Transcribe it back
            stt_result = stt.transcribe(tts_result.audio)
            self.assertIsInstance(stt_result, TranscriptionResult)

            # 3. Enroll speaker
            emb = sr.enroll(tts_result.audio, "test_speaker")
            self.assertIsInstance(emb, SpeakerEmbedding)

            # 4. Detect emotion
            emo_result = det.detect(tts_result.audio)
            self.assertIsInstance(emo_result, EmotionResult)

            # 5. Clone voice
            voice_model = cloner.clone(tts_result.audio, "test_voice")
            clone_result = cloner.synthesize("cloned speech", voice_model)
            self.assertIsInstance(clone_result, VoiceCloneResult)

        finally:
            for comp in [stt, tts, sr, det, cloner]:
                comp.shutdown()


if __name__ == "__main__":
    unittest.main()
