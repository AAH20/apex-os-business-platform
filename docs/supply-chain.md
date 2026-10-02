# Supply Chain Management

## 1. Supply Chain Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph SUPPLIERS[Suppliers]
        S1[Raw Material]
        S2[Components]
        S3[Packaging]
    end

    subgraph WAREHOUSE[Warehouses]
        W1[Regional DC]
        W2[Central DC]
        W3[Fulfillment Center]
    end

    subgraph PRODUCTION[Production]
        P1[Assembly Line A]
        P2[Assembly Line B]
        P3[Quality Control]
    end

    subgraph DISTRIBUTION[Distribution]
        D1[Last-Mile Delivery]
        D2[Cross-Dock]
        D3[Returns Center]
    end

    subgraph CUSTOMERS[Customers]
        C1[B2B Orders]
        C2[B2C Orders]
        C3[Retail Partners]
    end

    S1 --> W1
    S2 --> W1
    S3 --> W2
    W1 --> P1
    W1 --> P2
    W2 --> P1
    W2 --> P2
    P1 --> P3
    P2 --> P3
    P3 --> W3
    W3 --> D1
    W3 --> D2
    D1 --> C1
    D1 --> C2
    D2 --> C3
    C2 --> D3
    D3 --> W2
```

## 2. Demand Forecasting

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    A[Historical Sales Data] --> B[Data Cleaning]
    B --> C[Feature Engineering]
    C --> D[Model Selection]
    D --> E[ARIMA]
    D --> F[Prophet]
    D --> F2[LSTM Neural Net]
    E --> G[Ensemble Forecast]
    F --> G
    F2 --> G
    G --> H[Demand Plan]
    H --> I[S&OP Review]
    I --> J[Approved Forecast]
```

**Key Methods:**
- **Time-series models** (ARIMA, Prophet) for baseline seasonal patterns
- **ML models** (LSTM, XGBoost) for non-linear demand signals
- **Ensemble approach** combining multiple models for accuracy
- **External signals**: promotions, weather, economic indicators, social trends

**Forecast KPIs:**
| Metric | Target |
|--------|--------|
| MAPE | < 15% |
| Bias | ± 5% |
| Forecast Horizon | 13 weeks rolling |

## 3. Inventory Management

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph POLICIES[Policies]
        ROP[Reorder Point]
        EOQ[Economic Order Quantity]
        SS[Safety Stock]
        ABC[ABC Analysis]
    end

    subgraph MONITORING[Monitoring]
        RT[Real-time Stock Levels]
        LT[Lead Time Tracking]
        SLA[Shelf-life Alerts]
        INV[Inventory Turns]
    end

    subgraph ACTIONS[Actions]
        PO[Purchase Orders]
        TO[Transfer Orders]
        MO[Markdown/Disposal]
        RE[Replenishment]
    end

    ROP --> RE
    EOQ --> PO
    SS --> RE
    ABC --> MO
    RT --> ROP
    LT --> SS
    SLA --> MO
    INV --> EOQ
```

**Inventory Policies:**
- **ABC Classification**: A-items (top 20% by value) — tight control, daily review; B-items — weekly review; C-items — monthly review, bulk ordering
- **Safety Stock**: Calculated as `Z × σ_LT × √L` where Z = service factor, σ_LT = demand std dev during lead time, L = lead time
- **Reorder Point**: `ROP = (Avg Daily Demand × Lead Time) + Safety Stock`
- **EOQ**: `√(2DS/H)` where D = annual demand, S = ordering cost, H = holding cost

**Stock Status Flow:**
```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> InStock
    InStock --> LowStock: Below ROP
    LowStock --> ReorderPlaced: PO issued
    ReorderPlaced --> InStock: Received
    InStock --> OutOfStock: Stock = 0
    OutOfStock --> ReorderPlaced: Emergency PO
    InStock --> Excess: > Max level
    Excess --> InStock: Transfer/Markdown
    InStock --> Obsolete: No movement 90d
    Obsolete --> Disposed: Write-off
    Disposed --> [*]
```

## 4. Logistics

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    subgraph INBOUND[Inbound Logistics]
        PO2[PO to Supplier]
        ASN[ASN Receipt]
        QC2[Quality Check]
        PUT[Put-away]
    end

    subgraph OUTBOUND[Outbound Logistics]
        PICK[Pick]
        PACK[Pack]
        SHIP[Ship]
        DELIVER[Deliver]
    end

    subgraph TRANSPORT[Transport Modes]
        FT[Full Truckload]
        LTL[Less Than Truckload]
        AIR[Air Freight]
        OCEAN[Ocean Freight]
        PARCEL[Parcel/Express]
    end

    subgraph WAREHOUSE_OPS[Warehouse Ops]
        RECEIVE[Receive]
        STORE[Store]
        PICK2[Pick]
        SHIP2[Ship]
    end

    PO2 --> ASN --> QC2 --> PUT --> RECEIVE --> STORE
    STORE --> PICK2 --> SHIP2
    PICK2 --> PICK --> PACK --> SHIP --> DELIVER
    SHIP --> FT
    SHIP --> LTL
    SHIP --> AIR
    SHIP --> OCEAN
    SHIP --> PARCEL
```

**Logistics KPIs:**
| Metric | Target |
|--------|--------|
| On-time delivery | > 97% |
| Order accuracy | > 99.5% |
| Damage rate | < 0.5% |
| Cost per unit shipped | Reduce 5% YoY |
| Warehouse utilization | 75-85% |

**Routing Strategy:**
- **Milk runs** for frequent, small-volume supplier pickups
- **Cross-docking** for fast-moving items (no storage, direct transfer)
- **Zone skipping** to consolidate shipments to regional hubs before last-mile

## 5. Supplier Management

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    subgraph SOURCING[Sourcing]
        RFQ[RFQ Process]
        NEG[Negotiation]
        CONTRACT[Contract Award]
    end

    subgraph EVALUATION[Evaluation]
        QUAL[Quality Score]
        DELIV[Delivery Score]
        COST[Cost Score]
        RISK[Risk Assessment]
    end

    subgraph RELATIONSHIP[Relationship]
        STRATEGIC[Strategic Partner]
        PREFERRED[Preferred Supplier]
        APPROVED[Approved Supplier]
        CONDITIONAL[Conditional/Probation]
    end

    subgraph MONITOR2[Monitoring]
        SLA2[SLA Compliance]
        AUDIT[Periodic Audits]
        DEV[Supplier Development]
    end

    RFQ --> NEG --> CONTRACT
    CONTRACT --> QUAL
    CONTRACT --> DELIV
    CONTRACT --> COST
    CONTRACT --> RISK
    QUAL --> STRATEGIC
    DELIV --> PREFERRED
    COST --> APPROVED
    RISK --> CONDITIONAL
    STRATEGIC --> SLA2
    PREFERRED --> SLA2
    APPROVED --> AUDIT
    CONDITIONAL --> DEV
```

**Supplier Scorecard:**
| Category | Weight | Metrics |
|----------|--------|---------|
| Quality | 35% | Defect rate, return rate, ISO certification |
| Delivery | 30% | On-time %, lead time accuracy, fill rate |
| Cost | 20% | Price competitiveness, payment terms, TCO |
| Risk | 15% | Financial stability, geographic risk, single-source risk |

**Supplier Tiers:**
- **Strategic**: Joint planning, VMI, long-term contracts, quarterly business reviews
- **Preferred**: Volume commitments, annual contracts, performance reviews
- **Approved**: Standard terms, spot orders, monitored quarterly
- **Conditional**: Probationary period, increased inspection, development plan

**Risk Mitigation:**
- Dual-sourcing for critical components (A-items)
- Geographic diversification to avoid single-region disruption
- Safety stock buffers for long-lead-time items
- Supplier financial health monitoring via third-party ratings
