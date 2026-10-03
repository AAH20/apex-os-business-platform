"""Tests for deepened speech module: ASR, TTS, speaker ID, emotion, transcription."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def speech_engine():
    from apex_os_bp.speech.deepened import SpeechPipeline
    engine = SpeechPipeline()
    engine.transcribe = MagicMock(return_value="Hello world")
    engine.synthesize = MagicMock(return_value=b"audio_bytes_data")
    engine.identify_speaker = MagicMock(return_value={"speaker_id": "spk_1", "confidence": 0.93})
    engine.detect_emotion = MagicMock(return_value={"emotion": "happy", "score": 0.87})
    engine.transcribe_file = MagicMock(return_value={"text": "full transcript", "segments": 5})
    return engine


class TestASR:
    def test_transcribe_audio(self, speech_engine):
        result = speech_engine.transcribe("audio.wav")
        assert result == "Hello world"

    def test_transcribe_with_language(self, speech_engine):
        speech_engine.transcribe.return_value = "Bonjour"
        result = speech_engine.transcribe("audio.wav", language="fr")
        assert isinstance(result, str)


class TestTTS:
    def test_synthesize_speech(self, speech_engine):
        result = speech_engine.synthesize("Hello there")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_synthesize_voice_selection(self, speech_engine):
        result = speech_engine.synthesize("Test", voice="en-US-female")
        assert result is not None


class TestSpeakerIdentification:
    def test_identify_speaker(self, speech_engine):
        result = speech_engine.identify_speaker("voice.wav")
        assert result["speaker_id"] == "spk_1"
        assert result["confidence"] > 0.9

    def test_unknown_speaker(self, speech_engine):
        speech_engine.identify_speaker.return_value = {"speaker_id": "unknown", "confidence": 0.3}
        result = speech_engine.identify_speaker("unknown.wav")
        assert result["confidence"] < 0.5


class TestEmotionRecognition:
    def test_detect_emotion(self, speech_engine):
        result = speech_engine.detect_emotion("speech.wav")
        assert result["emotion"] == "happy"
        assert result["score"] > 0.8

    def test_emotion_labels(self, speech_engine):
        speech_engine.detect_emotion.return_value = {"emotion": "angry", "score": 0.75}
        result = speech_engine.detect_emotion("angry.wav")
        assert result["emotion"] in ("happy", "sad", "angry", "neutral")


class TestTranscription:
    def test_transcribe_file(self, speech_engine):
        result = speech_engine.transcribe_file("meeting.wav")
        assert result["text"] == "full transcript"
        assert result["segments"] == 5

    def test_transcribe_with_timestamps(self, speech_engine):
        speech_engine.transcribe_file.return_value = {
            "text": "hello", "timestamps": [{"start": 0.0, "end": 0.5}]
        }
        result = speech_engine.transcribe_file("audio.wav", timestamps=True)
        assert "timestamps" in result
