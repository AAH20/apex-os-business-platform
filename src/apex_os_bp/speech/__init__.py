"""APEX-OS Speech Processing System.

Provides speech-to-text, text-to-speech, speaker recognition,
emotion detection, and voice cloning capabilities.
"""

from apex_os_bp.speech.base import (
    AudioConfig,
    AudioSegment,
    SpeechComponent,
    SpeechError,
)
from apex_os_bp.speech.stt import (
    STTConfig,
    TranscriptionResult,
    SpeechToText,
    WhisperSTT,
    MockSTT,
)
from apex_os_bp.speech.tts import (
    TTSConfig,
    TTSResult,
    TextToSpeech,
    Pyttsx3TTS,
    MockTTS,
)
from apex_os_bp.speech.speaker import (
    SpeakerConfig,
    SpeakerEmbedding,
    SpeakerRecognition,
    SpeakerIdentifier,
    MockSpeakerRecognition,
)
from apex_os_bp.speech.emotion import (
    EmotionConfig,
    EmotionResult,
    EmotionDetector,
    MockEmotionDetector,
)
from apex_os_bp.speech.voice_cloning import (
    VoiceCloningConfig,
    VoiceCloneResult,
    VoiceCloner,
    MockVoiceCloner,
)

__all__ = [
    # Base
    "AudioConfig",
    "AudioSegment",
    "SpeechComponent",
    "SpeechError",
    # STT
    "STTConfig",
    "TranscriptionResult",
    "SpeechToText",
    "WhisperSTT",
    "MockSTT",
    # TTS
    "TTSConfig",
    "TTSResult",
    "TextToSpeech",
    "Pyttsx3TTS",
    "MockTTS",
    # Speaker
    "SpeakerConfig",
    "SpeakerEmbedding",
    "SpeakerRecognition",
    "SpeakerIdentifier",
    "MockSpeakerRecognition",
    # Emotion
    "EmotionConfig",
    "EmotionResult",
    "EmotionDetector",
    "MockEmotionDetector",
    # Voice Cloning
    "VoiceCloningConfig",
    "VoiceCloneResult",
    "VoiceCloner",
    "MockVoiceCloner",
]
