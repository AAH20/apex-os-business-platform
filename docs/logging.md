# Logging

## 1. Logging Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph Apps["Applications"]
        A1[API Server]
        A2[Worker]
        A3[CLI]
    end
    subgraph Lib["Logging Library"]
        L1[Logger]
        L2[Context]
        L3[Sampler]
    end
    subgraph Sinks["Sinks"]
        S1[Console]
        S2[File]
        S3[HTTP]
    end
    subgraph Pipeline["Log Pipeline"]
        P1[Collector]
        P2[Parser]
        P3[Enricher]
        P4[Queue]
    end
    subgraph Store["Storage"]
        E1[(Hot Store)]
        E2[(Warm Store)]
        E3[(Cold Store)]
    end
    A1 --> L1
    A2 --> L1
    A3 --> L1
    L1 --> L2 --> L3
    L3 --> S1
    L3 --> S2
    L3 --> S3
    S3 --> P1 --> P2 --> P3 --> P4
    P4 --> E1
    P4 --> E2
    P4 --> E3
```

## 2. Log Levels

| Level | Value | Use |
|-------|-------|-----|
| TRACE | 5 | Function entry/exit, loop iterations |
| DEBUG | 10 | Detailed diagnostics, state dumps |
| INFO | 20 | Normal operations, lifecycle events |
| WARN | 30 | Recoverable issues, deprecated usage |
| ERROR | 40 | Operation failed, exception caught |
| FATAL | 50 | Unrecoverable, process exiting |

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    E["Log Event"] --> C{Level >= Threshold?}
    C -- No --> D[Drop]
    C -- Yes --> F[Format]
    F --> B[Buffer]
    B --> S[Emit to Sinks]
```

## 3. Log Aggregation

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph Producers
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker N]
    end
    subgraph Buffer["Ring Buffer"]
        R1[Slot 1]
        R2[Slot 2]
        R3[Slot N]
    end
    subgraph Batcher
        B1[Batch 100]
        B2[Flush 5s]
    end
    subgraph Shippers
        H1[HTTP Shipper]
        H2[gRPC Shipper]
    end
    W1 --> R1
    W2 --> R2
    W3 --> R3
    R1 --> B1
    R2 --> B1
    R3 --> B1
    B1 --> B2
    B2 --> H1
    B2 --> H2
```

- **Batch size**: 100 events or 5s flush interval
- **Compression**: gzip for HTTP, zstd for gRPC
- **Retry**: exponential backoff, max 3 attempts
- **Backpressure**: drop oldest when buffer full

## 4. Log Search

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    Q["Query"] --> P[Parser]
    P --> AST[AST]
    AST --> IDX[Index Lookup]
    IDX --> RES[Results]
    RES --> H[Highlight]
```

**Query syntax:**

```
level:error service:api after:2026-10-01 "connection refused"
```

| Operator | Example | Description |
|----------|---------|-------------|
| `field:value` | `level:error` | Exact match |
| `field:>value` | `duration:>1000` | Range |
| `"text"` | `"timeout"` | Full-text |
| `AND` / `OR` | `level:error AND service:api` | Boolean |
| `NOT` | `NOT level:debug` | Negation |

## 5. Log Retention

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph Hot["Hot (7d)"]
        H1[SSD]
    end
    subgraph Warm["Warm (30d)"]
        W1[HDD]
    end
    subgraph Cold["Cold (365d)"]
        C1[Object Storage]
    end
    H1 -->|7d| W1
    W1 -->|30d| C1
    C1 -->|365d| DEL[Delete]
```

| Tier | Age | Storage | Compression |
|------|-----|---------|-------------|
| Hot | 0–7d | Local SSD | None |
| Warm | 7–30d | HDD | zstd |
| Cold | 30–365d | S3/GCS | zstd |
| Archive | >365d | Glacier | zstd |

- **Sampling**: 100% ERROR, 10% INFO, 1% DEBUG after 7d
- **PII**: redacted at collector before storage
- **Compliance**: immutable cold tier with WORM lock
