# Asset Management

## 1. Architecture

```mermaid
graph TB
    subgraph External["External Systems"]
        ERP[ERP / Accounting]
        IoT[IoT Sensors]
        HR[HR System]
    end

    subgraph Core["Asset Management Core"]
        REG[Asset Registry]
        TRK[Tracking Engine]
        DEP[Depreciation Engine]
        MNT[Maintenance Scheduler]
        DSP[Disposal Workflow]
        RPT[Reporting Service]
    end

    subgraph Data["Data Layer"]
        DB[(Asset DB)]
        FS[(Document Store)]
        CACHE[(Cache)]
    end

    ERP -->|purchase orders| REG
    IoT -->|condition data| TRK
    HR -->|custodian changes| REG
    REG --> DB
    TRK --> DB
    DEP --> DB
    MNT --> DB
    DSP --> DB
    REG --> FS
    DSP --> FS
    RPT --> CACHE
    DB --> RPT
    FS --> RPT

    classDef external fill:#1e3a5f,stroke:#4a9eff,color:#e0e0e0
    classDef core fill:#2d1b4e,stroke:#9b59b6,color:#e0e0e0
    classDef data fill:#1b3a2d,stroke:#27ae60,color:#e0e0e0
    class ERP,IoT,HR external
    class REG,TRK,DEP,MNT,DSP,RPT core
    class DB,FS,CACHE data
```

## 2. Asset Tracking

Every asset receives a unique identifier (UUID + human-readable tag). Location, custodian, and status are updated via events.

```mermaid
stateDiagram-v2
    [*] --> Registered: create asset
    Registered --> InUse: assign custodian
    InUse --> InTransfer: initiate transfer
    InTransfer --> InUse: confirm receipt
    InUse --> InMaintenance: schedule repair
    InMaintenance --> InUse: complete repair
    InUse --> Disposed: approve disposal
    InTransfer --> Disposed: write-off
    Disposed --> [*]
```

**Tracked attributes:** asset ID, category, serial number, purchase date, cost, location, custodian, status, condition score, warranty expiry, custom fields.

**Tracking methods:** barcode/RFID scan, GPS (vehicles/equipment), IoT sensors (condition monitoring), manual audit.

## 3. Depreciation

Straight-line and declining-balance methods supported per asset category.

```mermaid
flowchart LR
    A[Asset Cost] --> B{Method}
    B -->|Straight-Line| C["(Cost - Salvage) / Useful Life"]
    B -->|Declining Balance| D["Book Value × (2 / Useful Life)"]
    C --> E[Monthly Depreciation]
    D --> E
    E --> F[Accumulated Depreciation]
    F --> G[Net Book Value]
    G --> H{Fully Depreciated?}
    H -->|No| E
    H -->|Yes| I[Stop Depreciation]

    classDef input fill:#4a3000,stroke:#e67e22,color:#e0e0e0
    classDef process fill:#1a3a4a,stroke:#2980b9,color:#e0e0e0
    classDef decision fill:#3a1a3a,stroke:#8e44ad,color:#e0e0e0
    classDef terminal fill:#3a1a1a,stroke:#c0392b,color:#e0e0e0
    class A input
    class C,D,E,F,G process
    class B,H decision
    class I terminal
```

**Key rules:**
- Depreciation starts the month after acquisition (or at acquisition if configured).
- Salvage value defaults to 0 unless set per category.
- Impairments trigger immediate write-down and recalculation.
- Reversals allowed within the same fiscal period.

## 4. Maintenance

Preventive and corrective maintenance workflows with scheduling and cost tracking.

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant A as Asset
    participant T as Technician
    participant I as Inventory

    S->>A: check maintenance due
    A-->>S: due / not due
    S->>S: create work order
    T->>T: diagnose issue
    T->>I: request parts
    I-->>T: parts issued
    T->>A: perform repair
    A-->>T: condition updated
    T->>S: close work order
    S->>A: update next due date
```

**Maintenance types:**
- **Preventive:** time-based (every N days) or usage-based (every N hours/km).
- **Corrective:** triggered by breakdown report or IoT anomaly alert.
- **Predictive:** IoT sensor thresholds trigger proactive work orders.

**Tracked data:** work order ID, asset, technician, labor hours, parts used, cost, downtime hours, condition before/after.

## 5. Disposal

Assets move through approval, execution, and accounting write-off.

```mermaid
flowchart TD
    A[Initiate Disposal] --> B{Disposal Type}
    B -->|Sale| C[Create Sales Order]
    B -->|Scrap| D[Scrap Authorization]
    B -->|Donation| E[Donation Certificate]
    B -->|Transfer| F[Inter-company Transfer]
    C --> G[Receive Payment]
    D --> H[Remove from Service]
    E --> H
    F --> H
    G --> I[Write Off Asset]
    H --> I
    I --> J[Update GL]
    J --> K[Archive Records]
    K --> L[Close Disposal]

    classDef start fill:#1a3a1a,stroke:#27ae60,color:#e0e0e0
    classDef action fill:#1a2a3a,stroke:#2980b9,color:#e0e0e0
    classDef decision fill:#3a2a1a,stroke:#e67e22,color:#e0e0e0
    classDef end fill:#3a1a1a,stroke:#c0392b,color:#e0e0e0
    class A start
    class C,D,E,F,G,H action
    class B decision
    class I,J,K,L end
```

**Disposal checklist:**
- [ ] Asset removed from active registry
- [ ] Accumulated depreciation reconciled
- [ ] Gain/loss calculated (proceeds - net book value)
- [ ] GL entries posted
- [ ] Documents archived (certificate of disposal, sale receipt)
- [ ] Custodian notified
