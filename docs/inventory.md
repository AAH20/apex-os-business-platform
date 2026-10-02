# Inventory Module

## 1. Inventory Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    subgraph Sources[External Sources]
        PO[Purchase Orders]
        SUP[Supplier API]
        EC[E-commerce Channels]
    end

    subgraph Core[Inventory Core]
        SKU[(SKU Catalog)]
        STOCK[(Stock Ledger)]
        WH[(Warehouse Master)]
        RES[(Reservations)]
    end

    subgraph Ops[Operations]
        REC[Receiving]
        PUT[Putaway]
        PICK[Picking]
        PACK[Packing]
        SHIP[Shipping]
    end

    subgraph Downstream[Downstream]
        ORD[Order Management]
        RPT[Reporting]
        FIN[Finance]
    end

    PO --> REC
    SUP --> REC
    REC --> PUT
    PUT --> STOCK
    STOCK --> SKU
    STOCK --> WH
    EC --> ORD
    ORD --> RES
    RES --> STOCK
    STOCK --> PICK
    PICK --> PACK
    PACK --> SHIP
    SHIP --> EC
    STOCK --> RPT
    STOCK --> FIN
    WH --> RPT
```

## 2. Stock Management

Stock is tracked per SKU per warehouse location using a double-entry ledger.

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph Ledger[Stock Ledger]
        IN[Receipts +IN]
        OUT[Issues -OUT]
        ADJ[Adjustments ±]
        TRF[Transfers ⇄]
    end

    IN --> BAL((Available Qty))
    OUT --> BAL
    ADJ --> BAL
    TRF --> BAL
    BAL --> AVL[Available to Promise]
    BAL --> RESV[Reserved]
```

**Key rules:**
- Every stock movement creates an immutable ledger entry (before/after quantities).
- Available = On-hand − Reserved − Quarantined.
- ATP (Available-to-Promise) computed in real time for order promising.
- Negative stock blocked by default; configurable per SKU.

## 3. Warehouse Management

Multi-warehouse support with zone-based putaway and pick path optimization.

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    subgraph WH1[Warehouse A]
        Z1[Receiving Zone]
        Z2[Reserve Zone]
        Z3[Pick Face]
        Z4[Shipping Zone]
    end

    subgraph WH2[Warehouse B]
        W1[Receiving]
        W2[Storage]
        W3[Dispatch]
    end

    Z1 --> Z2
    Z2 --> Z3
    Z3 --> Z4
    W1 --> W2
    W2 --> W3
```

**Key rules:**
- Putaway strategies: fixed slot, nearest-empty, velocity-based.
- Pick strategies: FIFO, FEFO (expiry), wave, batch.
- Inter-warehouse transfers create in-transit records until receipt confirmation.
- Cycle counts adjust stock with full audit trail.

## 4. Order Fulfillment

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    O[Order Received] --> V{Validate Stock}
    V -->|Available| R[Reserve Stock]
    V -->|Short| B[Backorder / Split]
    R --> A[Allocate to Warehouse]
    A --> P[Pick List Generated]
    P --> PK[Picking]
    PK --> CK{Count Check}
    CK -->|Match| PC[Packing]
    CK -->|Mismatch| ADJ[Adjust & Re-pick]
    PC --> LB[Label & Manifest]
    LB --> SP[Shipped]
    SP --> INV[Invoice]
    B --> FU[Fulfillment Queue]
```

**Key rules:**
- Reservation is soft (TTL) until pick confirmation; hard-reserved at shipment.
- Split shipments supported when partial stock available.
- Auto-allocation by proximity, cost, or priority rules.

## 5. Reporting

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    D[(Stock Ledger)] --> R1[Stock Valuation]
    D --> R2[Stock Aging]
    D --> R3[Movement History]
    D --> R4[Turnover Analysis]
    D --> R5[Low Stock Alerts]
    D --> R6[Dead Stock Report]
    WH[(Warehouse)] --> R7[Capacity Utilization]
    ORD[(Orders)] --> R8[Fulfillment SLA]
```

**Standard reports:**
- Stock valuation (FIFO / weighted average).
- Aging buckets: 0-30, 31-60, 61-90, 90+ days.
- Turnover ratio = COGS / Average inventory.
- Fill rate = Orders shipped complete / Total orders.
