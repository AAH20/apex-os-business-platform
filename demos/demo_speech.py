#!/usr/bin/env python3
"""Speech demos: TTS, STT, voice cloning, emotion detection, speech generation.

Run all demos:  python demo_speech.py
Run one demo:   python demo_speech.py tts
"""

import sys
import tempfile
import wave
import struct
import math


def tts_demo():
    """1. Text-to-speech — synthesize speech from text."""
    print("=== 1. Text-to-Speech (TTS) ===")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say("Hello, this is a text to speech demonstration.")
        engine.runAndWait()
        print("[OK] Spoke text via pyttsx3")
    except ImportError:
        print("[SKIP] pyttsx3 not installed — pip install pyttsx3")
    print()


def stt_demo():
    """2. Speech-to-text — transcribe audio to text."""
    print("=== 2. Speech-to-Text (STT) ===")
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening... (speak now)")
            audio = r.listen(source, timeout=5)
        text = r.recognize_google(audio)
        print(f"[OK] Transcribed: {text}")
    except ImportError:
        print("[SKIP] SpeechRecognition not installed — pip install SpeechRecognition")
    except Exception as e:
        print(f"[INFO] STT unavailable: {e}")
    print()


def clone_voice_demo():
    """3. Voice cloning — synthesize speech in a target voice."""
    print("=== 3. Voice Cloning ===")
    try:
        from TTS.api import TTS
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                  progress_bar=False, gpu=False)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out = f.name
        tts.tts_to_file(
            text="This is a cloned voice speaking.",
            file_path=out,
            speaker_wav=None,  # path to a reference voice clip
            language="en",
        )
        print(f"[OK] Cloned voice saved to {out}")
    except ImportError:
        print("[SKIP] TTS (Coqui) not installed — pip install TTS")
    except Exception as e:
        print(f"[INFO] Voice cloning unavailable: {e}")
    print()


def detect_emotion_demo():
    """4. Detect emotion — classify emotion from audio."""
    print("=== 4. Emotion Detection ===")
    try:
        from transformers import pipeline
        classifier = pipeline("audio-classification",
                              model="ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition")
        # Use a synthetic tone as a stand-in for real audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            for i in range(16000):
                val = int(32767 * 0.3 * math.sin(2 * math.pi * 220 * i / 16000))
                wf.writeframes(struct.pack("<h", val))
        result = classifier(path)
        top = max(result, key=lambda x: x["score"])
        print(f"[OK] Detected emotion: {top['label']} (confidence: {top['score']:.2f})")
    except ImportError:
        print("[SKIP] transformers not installed — pip install transformers torch")
    except Exception as e:
        print(f"[INFO] Emotion detection unavailable: {e}")
    print()


def generate_speech_demo():
    """5. Generate speech — create audio from text with prosody control."""
    print("=== 5. Generate Speech ===")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.setProperty("volume", 0.9)
        voices = engine.getProperty("voices")
        if voices:
            engine.setProperty("voice", voices[0].id)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out = f.name
        engine.save_to_file("Generated speech with custom rate and volume.", out)
        engine.runAndWait()
        print(f"[OK] Generated speech saved to {out}")
    except ImportError:
        print("[SKIP] pyttsx3 not installed — pip install pyttsx3")
    except Exception as e:
        print(f"[INFO] Speech generation unavailable: {e}")
    print()


DEMOS = {
    "tts": tts_demo,
    "stt": stt_demo,
    "clone": clone_voice_demo,
    "emotion": detect_emotion_demo,
    "generate": generate_speech_demo,
}


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg == "all":
        for fn in DEMOS.values():
            fn()
    elif arg in DEMOS:
        DEMOS[arg]()
    else:
        print(f"Unknown demo: {arg}. Choose from: {', '.join(DEMOS)} or 'all'")
        sys.exit(1)


if __name__ == "__main__":
    main()
