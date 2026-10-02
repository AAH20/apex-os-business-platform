# Speech Module

## 1. Speech Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    subgraph Input Layer
        MIC[Microphone Input]
        FILE[Audio File]
        TXT[Text Input]
    end

    subgraph Processing Layer
        STT[Speech-to-Text Engine]
        TTS[Text-to-Speech Engine]
        VC[Voice Cloning]
        ED[Emotion Detection]
        NR[Noise Reduction]
        VAD[Voice Activity Detection]
    end

    subgraph Orchestration Layer
        SC[Speech Coordinator]
        CFG[Config Manager]
        CACHE[Audio Cache]
        QUEUE[Request Queue]
    end

    subgraph Output Layer
        SPK[Speaker Output]
        META[Metadata Stream]
        VIS[Visualizer]
    end

    MIC --> VAD
    FILE --> NR
    VAD --> STT
    NR --> STT
    STT --> ED
    STT --> SC
    TXT --> TTS
    VC --> TTS
    TTS --> SC
    SC --> SPK
    SC --> META
    SC --> VIS
    CFG --> SC
    CACHE --> TTS
    QUEUE --> SC
```

## 2. Text-to-Speech (TTS)

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph TTS Pipeline
        TXT_IN[Raw Text] --> NORM[Text Normalization]
        NORM --> PHON[Phonemization]
        PHON --> PROS[Prosody Analysis]
        PROS --> SYN[Synthesis Engine]
        SYN --> POST[Post-processing]
        POST --> WAV[Audio Output]
    end

    subgraph Synthesis Engines
        E1[Neural TTS]
        E2[Concatenative]
        E3[Formant]
        E4[Hybrid]
    end

    subgraph Voice Profiles
        VP1[Default Male]
        VP2[Default Female]
        VP3[Custom Clone]
        VP4[Multi-language]
    end

    SYN --> E1 & E2 & E3 & E4
    VP1 & VP2 & VP3 & VP4 --> SYN
```

### TTS Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `voice_id` | string | `"default"` | Voice profile identifier |
| `speed` | float | `1.0` | Speech rate multiplier |
| `pitch` | float | `1.0` | Pitch shift factor |
| `volume` | float | `0.8` | Output gain (0–1) |
| `language` | string | `"en-US"` | BCP-47 language tag |
| `format` | string | `"wav"` | Output format (wav/mp3/ogg) |
| `sample_rate` | int | `22050` | Output sample rate (Hz) |
| `streaming` | bool | `true` | Enable chunked streaming output |

### TTS API

```python
from apex_speech import TTSEngine

tts = TTSEngine(voice_id="custom_clone_01", language="en-US")
audio = tts.synthesize(
    text="Hello, welcome to Apex OS.",
    speed=1.0,
    pitch=1.0,
    emotion="neutral"
)
audio.play()
audio.save("output.wav")
```

## 3. Speech-to-Text (STT)

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    subgraph STT Pipeline
        AIN[Audio Input] --> PRE[Pre-emphasis]
        PRE --> VAD2[VAD Segmentation]
        VAD2 --> FEAT[Feature Extraction]
        FEAT --> DEC[Decoder]
        DEC --> LM[Language Model]
        LM --> RES[Result]
    end

    subgraph Decoder Modes
        D1[Streaming]
        D2[Batch]
        D3[Real-time]
    end

    subgraph Output
        R1[Transcript Text]
        R2[Word Timestamps]
        R3[Confidence Scores]
        R4[Speaker ID]
    end

    DEC --> D1 & D2 & D3
    RES --> R1 & R2 & R3 & R4
```

### STT Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `"whisper-large-v3"` | STT model identifier |
| `language` | string | `"auto"` | Source language (auto-detect if set) |
| `beam_size` | int | `5` | Beam search width |
| `temperature` | float | `0.0` | Decoding temperature |
| `vad_threshold` | float | `0.5` | Voice activity sensitivity |
| `chunk_duration` | float | `30.0` | Max segment length (seconds) |
| `diarization` | bool | `false` | Enable speaker separation |

### STT API

```python
from apex_speech import STTEngine

stt = STTEngine(model="whisper-large-v3", language="auto")
result = stt.transcribe("meeting.wav", diarization=True)

print(result.text)
for word in result.words:
    print(f"{word.start:.2f}s – {word.end:.2f}s  {word.text} ({word.confidence:.2f})")
```

## 4. Voice Cloning

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Cloning Pipeline
        SAMPLE[Audio Samples] --> QC[Quality Check]
        QC --> EMB[Speaker Embedding]
        EMB --> TRAIN[Fine-tune / Adapt]
        TRAIN --> EVAL[Evaluation]
        EVAL --> DEPLOY[Deploy Voice Profile]
    end

    subgraph Quality Metrics
        Q1[SNR > 20dB]
        Q2[Duration > 30s]
        Q3[No Overlap]
        Q4[Clean Transcript]
    end

    subgraph Storage
        VS[(Voice Store)]
        META2[Profile Metadata]
    end

    QC --> Q1 & Q2 & Q3 & Q4
    DEPLOY --> VS
    DEPLOY --> META2
```

### Voice Cloning Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_samples` | int | `3` | Minimum audio samples required |
| `min_duration` | float | `30.0` | Minimum total duration (seconds) |
| `embedding_model` | string | `"resemblyzer"` | Speaker encoder model |
| `finetune_epochs` | int | `100` | Adaptation training epochs |
| `similarity_threshold` | float | `0.85` | Acceptance cosine similarity |
| `max_profiles` | int | `50` | Max stored voice profiles |

### Voice Cloning API

```python
from apex_speech import VoiceCloner

cloner = VoiceCloner(embedding_model="resemblyzer")
profile = cloner.clone(
    name="Executive Voice",
    samples=["sample1.wav", "sample2.wav", "sample3.wav"],
    transcript="Transcript of spoken samples..."
)
print(f"Voice profile created: {profile.id} (similarity: {profile.similarity:.2f})")
```

## 5. Emotion Detection

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    subgraph Emotion Pipeline
        AUDIO[Audio Features] --> FEAT2[Acoustic Features]
        TEXT[Transcript] --> LING[Linguistic Features]
        FEAT2 --> FUSE[Fusion Layer]
        LING --> FUSE
        FUSE --> CLS[Emotion Classifier]
        CLS --> OUT[Emotion Output]
    end

    subgraph Acoustic Features
        A1[Pitch / F0]
        A2[Energy / RMS]
        A3[Spectral Centroid]
        A4[MFCCs]
        A5[Jitter / Shimmer]
    end

    subgraph Emotions
        E1[Neutral]
        E2[Happy]
        E3[Sad]
        E4[Angry]
        E5[Fearful]
        E6[Surprised]
        E7[Disgusted]
    end

    FEAT2 --> A1 & A2 & A3 & A4 & A5
    CLS --> E1 & E2 & E3 & E4 & E5 & E6 & E7
```

### Emotion Detection Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `"wav2vec2-emotion"` | Emotion model identifier |
| `fusion` | string | `"late"` | Fusion strategy (early/late/hybrid) |
| `granularity` | string | `"utterance"` | Analysis window (frame/utterance) |
| `num_emotions` | int | `7` | Number of emotion classes |
| `confidence_threshold` | float | `0.6` | Minimum confidence for output |
| `temporal_smoothing` | int | `5` | Moving-average window size |

### Emotion Detection API

```python
from apex_speech import EmotionDetector

detector = EmotionDetector(model="wav2vec2-emotion", fusion="hybrid")
result = detector.detect("speech.wav")

print(f"Dominant: {result.dominant_emotion} ({result.confidence:.2f})")
for emotion, score in result.distribution.items():
    print(f"  {emotion}: {score:.3f}")
```

---

## Module Dependencies

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    SPEECH[Speech Module] --> AUDIO[Audio I/O]
    SPEECH --> ML[ML Inference Runtime]
    SPEECH --> CONFIG[Configuration]
    SPEECH --> CACHE[Cache Layer]
    SPEECH --> LOG[Logging]
    SPEECH --> BUS[Event Bus]
```

## Error Handling

| Error Code | Description | Recovery |
|------------|-------------|----------|
| `SPH-001` | Audio device unavailable | Retry with fallback device |
| `SPH-002` | Model load failure | Fall back to lighter model |
| `SPH-003` | Synthesis timeout | Reduce text chunk size |
| `SPH-004` | Cloning quality reject | Request more samples |
| `SPH-005` | Emotion confidence low | Return neutral + flag |
