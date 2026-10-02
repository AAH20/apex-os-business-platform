# Knowledge Management

## 1. Architecture

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1e3a5f','primaryTextColor':'#e0e0e0','primaryBorderColor':'#4a9eff','lineColor':'#4a9eff','secondaryColor':'#2d2d2d','tertiaryColor':'#1a1a2e','background':'#0d1117','mainBkg':'#161b22','secondBkg':'#21262d','textColor':'#c9d1d9','fontSize':'14px'}}}%%
flowchart TB
    subgraph Sources["Knowledge Sources"]
        DOCS[Documents]
        CODE[Codebase]
        WIKI[Wiki Pages]
        CHAT[Chat History]
        EXT[External APIs]
    end

    subgraph Ingestion["Ingestion Layer"]
        P[Parser & Chunker]
        E[Embedder]
        M[Metadata Extractor]
    end

    subgraph Storage["Storage Layer"]
        VDB[(Vector DB)]
        GDB[(Graph DB)]
        DOCS_[(Doc Store)]
    end

    subgraph Serving["Serving Layer"]
        S[Search API]
        R[Recommendation Engine]
        L[Learning Pipeline]
    end

    DOCS & CODE & WIKI & CHAT & EXT --> P
    P --> E
    P --> M
    E --> VDB
    M --> GDB
    P --> DOCS_
    VDB & GDB & DOCS_ --> S
    VDB & GDB --> R
    S & R --> L
    L -.->|feedback| VDB
    L -.->|feedback| GDB
```

## 2. Knowledge Graph

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1e3a5f','primaryTextColor':'#e0e0e0','primaryBorderColor':'#4a9eff','lineColor':'#4a9eff','secondaryColor':'#2d2d2d','tertiaryColor':'#1a1a2e','background':'#0d1117','mainBkg':'#161b22','secondBkg':'#21262d','textColor':'#c9d1d9','fontSize':'14px'}}}%%
erDiagram
    Document {
        string id PK
        string title
        string type
        date created
        date updated
        string author
    }
    Concept {
        string id PK
        string name
        string category
        float confidence
    }
    Entity {
        string id PK
        string name
        string type
    }
    Tag {
        string id PK
        string label
        string color
    }
    User {
        string id PK
        string name
        string role
    }
    Document ||--o{ Concept : "contains"
    Document ||--o{ Entity : "references"
    Document }o--o{ Tag : "tagged"
    Concept ||--o{ Concept : "related_to"
    Entity ||--o{ Entity : "connected_to"
    User ||--o{ Document : "authored"
    User }o--o{ Tag : "follows"
```

## 3. Search

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1e3a5f','primaryTextColor':'#e0e0e0','primaryBorderColor':'#4a9eff','lineColor':'#4a9eff','secondaryColor':'#2d2d2d','tertiaryColor':'#1a1a2e','background':'#0d1117','mainBkg':'#161b22','secondBkg':'#21262d','textColor':'#c9d1d9','fontSize':'14px'}}}%%
flowchart LR
    Q[Query] --> QP[Query Parser]
    QP --> QE[Query Embedding]
    QE --> VS[Vector Search]
    QE --> GS[Graph Search]
    QE --> FS[Full-Text Search]
    VS --> M[Rank Fusion]
    GS --> M
    FS --> M
    M --> RES[Results]
    RES --> H[Highlight & Snippet]
```

**Search modes:**
- **Semantic** — vector similarity over embeddings
- **Keyword** — BM25 full-text with fuzzy matching
- **Graph** — traversal over entity/concept relationships
- **Hybrid** — weighted fusion of all three

## 4. Recommendations

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1e3a5f','primaryTextColor':'#e0e0e0','primaryBorderColor':'#4a9eff','lineColor':'#4a9eff','secondaryColor':'#2d2d2d','tertiaryColor':'#1a1a2e','background':'#0d1117','mainBkg':'#161b22','secondBkg':'#21262d','textColor':'#c9d1d9','fontSize':'14px'}}}%%
flowchart TB
    U[User Context] --> UP[User Profile]
    UP --> CB[Content-Based]
    UP --> CF[Collaborative Filter]
    UP --> KB[Knowledge-Based]
    CB --> RR[Reranker]
    CF --> RR
    KB --> RR
    RR --> DIV[Diversity Boost]
    DIV --> EXP[Explanation Layer]
    EXP --> OUT[Ranked Recommendations]
```

**Signals:**
- Content similarity (embedding distance)
- Collaborative patterns (users like you)
- Knowledge graph proximity
- Recency & freshness decay
- Explicit feedback (thumbs, bookmarks)

## 5. Learning

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1e3a5f','primaryTextColor':'#e0e0e0','primaryBorderColor':'#4a9eff','lineColor':'#4a9eff','secondaryColor':'#2d2d2d','tertiaryColor':'#1a1a2e','background':'#0d1117','mainBkg':'#161b22','secondBkg':'#21262d','textColor':'#c9d1d9','fontSize':'14px'}}}%%
flowchart LR
    A[User Actions] --> B[Event Log]
    B --> C[Feedback Aggregator]
    C --> D[Model Trainer]
    D --> E[Embedding Update]
    D --> F[Graph Update]
    D --> G[Rank Tuning]
    E --> V[(Vector DB)]
    F --> GR[(Graph DB)]
    G --> S[Serving Config]
```

**Learning loops:**
- **Implicit** — clicks, dwell time, scroll depth
- **Explicit** — ratings, bookmarks, shares
- **Periodic** — nightly re-index, weekly model refresh
- **Online** — real-time embedding adjustments
