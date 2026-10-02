# APEX-OS Business Platform — Security

## 1. Security Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    subgraph Edge["Edge Layer"]
        WAF["WAF / DDoS Shield"]
        LB["TLS Termination LB"]
    end
    subgraph App["Application Layer"]
        GW["API Gateway"]
        AUTH["Auth Service"]
        SVC["Business Services"]
    end
    subgraph Data["Data Layer"]
        DB[(Encrypted DB)]
        CACHE[(Redis + TLS)]
        KMS["KMS / Vault"]
    end
    subgraph Obs["Observability"]
        SIEM["SIEM"]
        AUDIT["Audit Log Store"]
    end
    WAF --> LB --> GW
    GW --> AUTH
    GW --> SVC
    AUTH --> KMS
    SVC --> DB
    SVC --> CACHE
    SVC --> AUDIT
    AUDIT --> SIEM
    style WAF fill:#1a1a2e,stroke:#e94560,color:#fff
    style LB fill:#1a1a2e,stroke:#e94560,color:#fff
    style GW fill:#16213e,stroke:#0f3460,color:#fff
    style AUTH fill:#16213e,stroke:#0f3460,color:#fff
    style SVC fill:#16213e,stroke:#0f3460,color:#fff
    style DB fill:#0f3460,stroke:#533483,color:#fff
    style CACHE fill:#0f3460,stroke:#533483,color:#fff
    style KMS fill:#533483,stroke:#e94560,color:#fff
    style SIEM fill:#1a1a2e,stroke:#e94560,color:#fff
    style AUDIT fill:#1a1a2e,stroke:#e94560,color:#fff
```

**Principles:** zero-trust network, least-privilege access, defense in depth, encrypt-everything, audit-all-actions.

---

## 2. Authentication

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant U as User
    participant C as Client
    participant GW as API Gateway
    participant AS as Auth Service
    participant KMS as KMS/Vault
    U->>C: Enter credentials
    C->>GW: POST /auth/login
    GW->>AS: Forward request
    AS->>KMS: Fetch user secret
    KMS-->>AS: Secret material
    AS->>AS: Verify password (Argon2id)
    AS->>AS: Check MFA if enrolled
    AS-->>GW: JWT access + refresh tokens
    GW-->>C: Set HttpOnly cookies
    C-->>U: Authenticated session
    style U fill:#1a1a2e,stroke:#e94560,color:#fff
    style C fill:#1a1a2e,stroke:#e94560,color:#fff
    style GW fill:#16213e,stroke:#0f3460,color:#fff
    style AS fill:#16213e,stroke:#0f3460,color:#fff
    style KMS fill:#533483,stroke:#e94560,color:#fff
```

| Mechanism | Detail |
|---|---|
| Password hashing | Argon2id (memory=64MB, iterations=3, parallelism=4) |
| MFA | TOTP (RFC 6238) + WebAuthn/FIDO2 |
| Token format | JWT (RS256), 15-min access / 7-day refresh |
| Session storage | Redis with TLS, key = `sess:{user_id}` |
| Brute-force protection | Rate-limit 5 attempts / 15 min per IP+user |
| Password policy | Min 12 chars, zxcvbn score ≥ 3, breach-check via HIBP k-anon |

---

## 3. Authorization

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Identity
        U["User"]
        R["Role"]
        P["Permission"]
    end
    subgraph Resources
        ORG["Org"]
        PROJ["Project"]
        ENT["Entity"]
    end
    U -->|member of| ORG
    R -->|granted on| ORG
    R -->|granted on| PROJ
    R -->|has| P
    P -->|acts on| ENT
    style U fill:#1a1a2e,stroke:#e94560,color:#fff
    style R fill:#16213e,stroke:#0f3460,color:#fff
    style P fill:#16213e,stroke:#0f3460,color:#fff
    style ORG fill:#0f3460,stroke:#533483,color:#fff
    style PROJ fill:#0f3460,stroke:#533483,color:#fff
    style ENT fill:#0f3460,stroke:#533483,color:#fff
```

**Model:** RBAC + ABAC hybrid. Roles define baseline permissions; attribute policies add contextual constraints (time, IP, resource ownership).

| Role | Scope | Key Permissions |
|---|---|---|
| `org_admin` | Organization | Full CRUD, member management, billing |
| `project_lead` | Project | Read/write project resources, invite members |
| `member` | Project | Read/write assigned entities |
| `viewer` | Project | Read-only |
| `auditor` | Organization | Read-only + audit log access |
| `service` | System | Scoped API keys, no UI access |

**Enforcement:** OPA (Open Policy Agent) sidecar evaluates every request. Policies stored as code in `policies/`.

---

## 4. Encryption

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    subgraph InTransit["In Transit"]
        TLS["TLS 1.3 (mandatory)"]
        mTLS["mTLS service-to-service"]
    end
    subgraph AtRest["At Rest"]
        DEK["Per-record DEK"]
        KEK["KEK in KMS/HSM"]
        ENC["AES-256-GCM"]
    end
    subgraph InUse["In Use"]
        SM["Secure enclaves (optional)"]
        MEM["Memory-zeroization"]
    end
    TLS --> ENC
    mTLS --> ENC
    DEK --> ENC
    KEK -->|wraps| DEK
    ENC --> SM
    SM --> MEM
    style TLS fill:#1a1a2e,stroke:#e94560,color:#fff
    style mTLS fill:#1a1a2e,stroke:#e94560,color:#fff
    style DEK fill:#16213e,stroke:#0f3460,color:#fff
    style KEK fill:#533483,stroke:#e94560,color:#fff
    style ENC fill:#16213e,stroke:#0f3460,color:#fff
    style SM fill:#0f3460,stroke:#533483,color:#fff
    style MEM fill:#0f3460,stroke:#533483,color:#fff
```

| Layer | Algorithm | Key Management |
|---|---|---|
| Transport | TLS 1.3, PFS (X25519) | Auto-renewed via ACME (Let's Encrypt) |
| Service mesh | mTLS (SPIFFE/SPIRE) | Short-lived SVIDs, 24h rotation |
| Data at rest | AES-256-GCM | DEK per record, KEK in cloud KMS |
| Backups | AES-256-GCM | Separate KEK, air-gapped copies |
| Passwords | Argon2id | Salted, pepper in KMS |
| API keys | HMAC-SHA256 | Hashed at rest, shown once |
| Key rotation | 90-day KEK, 30-day DEK | Automated via KMS |

---

## 5. Audit Logging

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Producers
        API["API Gateway"]
        SVC["Services"]
        AUTH["Auth Events"]
    end
    subgraph Pipeline
        BUS["Event Bus (Kafka)"]
        PROC["Stream Processor"]
    end
    subgraph Storage
        HOT["Hot Store (7d)"]
        COLD["Cold Store (S3 Glacier)"]
    end
    subgraph Consumers
        SIEM["SIEM / Alerts"]
        DASH["Compliance Dashboard"]
    end
    API --> BUS
    SVC --> BUS
    AUTH --> BUS
    BUS --> PROC
    PROC --> HOT
    PROC --> COLD
    HOT --> SIEM
    HOT --> DASH
    style API fill:#1a1a2e,stroke:#e94560,color:#fff
    style SVC fill:#1a1a2e,stroke:#e94560,color:#fff
    style AUTH fill:#1a1a2e,stroke:#e94560,color:#fff
    style BUS fill:#16213e,stroke:#0f3460,color:#fff
    style PROC fill:#16213e,stroke:#0f3460,color:#fff
    style HOT fill:#0f3460,stroke:#533483,color:#fff
    style COLD fill:#0f3460,stroke:#533483,color:#fff
    style SIEM fill:#533483,stroke:#e94560,color:#fff
    style DASH fill:#533483,stroke:#e94560,color:#fff
```

**Event schema (CloudEvents 1.0):**

```json
{
  "specversion": "1.0",
  "type": "com.apexos.audit.action",
  "source": "/services/billing",
  "id": "evt_01J...",
  "time": "2026-10-02T12:00:00Z",
  "datacontenttype": "application/json",
  "data": {
    "actor": { "type": "user", "id": "usr_123", "ip": "10.0.0.1" },
    "action": "invoice.delete",
    "resource": { "type": "invoice", "id": "inv_456" },
    "outcome": "success",
    "metadata": { "reason": "duplicate", "request_id": "req_789" }
  }
}
```

| Property | Detail |
|---|---|
| Immutability | Append-only, hash-chained (SHA-256 per batch) |
| Retention | Hot 7 days, warm 90 days, cold 7 years (WORM) |
| PII handling | Field-level redaction before ingestion |
| Alerting | Real-time SIEM rules for privilege escalation, mass export, failed auth spikes |
| Compliance | SOC 2, GDPR Art. 30, HIPAA §164.308(a)(1)(ii)(D) |
| Access | `auditor` role only; all access to audit logs is itself logged |
