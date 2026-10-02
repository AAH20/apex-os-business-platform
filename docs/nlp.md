# NLP Module

## 1. Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    A[Raw Text] --> B[Preprocessor]
    B --> C[Tokenizer]
    C --> D[Pipeline Router]
    D --> E[Text Analysis]
    D --> F[Sentiment Analysis]
    D --> G[Entity Extraction]
    D --> H[Translation]
    E --> I[Results Aggregator]
    F --> I
    G --> I
    H --> I
    I --> J[API Response]
```

## 2. Text Analysis

Tokenization, lemmatization, POS tagging, and dependency parsing.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    A[Input Text] --> B[Sentence Splitter]
    B --> C[Word Tokenizer]
    C --> D[Lemmatizer]
    D --> E[POS Tagger]
    E --> F[Dependency Parser]
    F --> G[Output: Tokens + Tags + Tree]
```

| Stage | Output |
|-------|--------|
| Sentence Split | `["Hello world.", "How are you?"]` |
| Tokenize | `["Hello", "world", "."]` |
| Lemmatize | `["hello", "world", "."]` |
| POS Tag | `[INTJ, NOUN, PUNCT]` |
| Parse | Dependency tree |

## 3. Sentiment Analysis

Classifies text polarity and intensity using a fine-tuned transformer.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    A[Text] --> B[Encoder]
    B --> C[Classification Head]
    C --> D{Label}
    D -->|score > 0.6| E[Positive]
    D -->|score < 0.4| F[Negative]
    D -->|otherwise| G[Neutral]
```

- **Model**: `distilbert-base-uncased-emotion`
- **Labels**: positive, negative, neutral
- **Output**: `{ label, score, confidence }`

## 4. Entity Extraction

Named Entity Recognition (NER) for persons, organizations, locations, and custom domain entities.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    A[Tokenized Text] --> B[NER Model]
    B --> C[Entity Chunker]
    C --> D[Entity Linker]
    D --> E[Output: Entities + Types + Spans]
```

| Entity Type | Example |
|-------------|---------|
| PER | "Alice Smith" |
| ORG | "Acme Corp" |
| LOC | "Berlin" |
| MISC | "Product X" |

## 5. Translation

Neural machine translation with language detection and batch support.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    A[Source Text] --> B[Language Detector]
    B --> C[Translation Model]
    C --> D[Post-processor]
    D --> E[Translated Text]
```

- **Engine**: Helsinki-NLP OPUS-MT
- **Languages**: 40+ language pairs
- **Batch**: Up to 32 segments per request
- **Fallback**: Pivot via English for unsupported pairs
