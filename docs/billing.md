# APEX-OS Billing

## 1. Billing Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    subgraph Sources
        A[Usage Events]
        B[Subscription Plans]
        C[One-time Charges]
    end

    subgraph Engine
        D[Rating Engine]
        E[Invoice Generator]
        F[Tax Calculator]
    end

    subgraph Payments
        G[Payment Gateway]
        H[Payment Method Vault]
        I[Retry Queue]
    end

    subgraph Lifecycle
        J[Subscription Manager]
        K[Dunning Engine]
        L[Notification Service]
    end

    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    G -->|failed| I
    I --> K
    K --> L
    J --> D
    J --> E
```

### Core Entities

| Entity | Description |
|--------|-------------|
| `Customer` | Billing profile with tax region and currency |
| `Subscription` | Recurring plan with billing cycle and status |
| `Invoice` | Generated document with line items and totals |
| `Payment` | Transaction against an invoice |
| `DunningRule` | Retry schedule and escalation policy |

---

## 2. Invoice Management

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> Draft
    Draft --> Open: finalize
    Open --> Paid: payment received
    Open --> Overdue: due date passed
    Overdue --> Paid: late payment
    Overdue --> Uncollectible: dunning exhausted
    Paid --> [*]
    Uncollectible --> [*]
    Open --> Void: cancel
    Draft --> Void: discard
```

### Invoice Lifecycle

- **Draft**: Line items being assembled; not yet visible to customer
- **Open**: Finalized and sent; awaiting payment
- **Paid**: Full payment received; PDF archived
- **Overdue**: Past due date; dunning sequence initiated
- **Uncollectible**: All retries failed; flagged for write-off

### Line Item Types

| Type | Example |
|------|---------|
| `recurring` | Monthly platform fee |
| `usage` | API calls, storage GB-hours |
| `one_time` | Setup fee, add-on purchase |
| `credit` | Proration, promotional credit |
| `tax` | VAT, sales tax |

---

## 3. Payment Processing

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant E as Invoice Engine
    participant G as Payment Gateway
    participant V as Method Vault
    participant C as Customer

    E->>G: charge(invoice, method_token)
    G->>V: tokenize(payment_details)
    V-->>G: token
    G->>G: authorize + capture
    alt Success
        G-->>E: payment_confirmed
        E->>C: receipt_email
    else Soft Decline
        G-->>E: retryable_failure
        E->>E: schedule_retry
    else Hard Decline
        G-->>E: terminal_failure
        E->>C: update_payment_method
    end
```

### Gateway Abstraction

All gateways implement a common interface:

```
authorize(amount, currency, method_token) -> AuthResult
capture(auth_id) -> CaptureResult
refund(payment_id, amount) -> RefundResult
void(auth_id) -> VoidResult
```

### Supported Gateways

| Gateway | Regions | Methods |
|---------|---------|---------|
| Stripe | Global | Cards, SEPA, ACH |
| Adyen | EU/APAC | Cards, iDEAL, Klarna |
| PayPal | Global | PayPal, Venmo |

---

## 4. Subscription Management

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph States
        A[Active]
        B[Past Due]
        C[Canceled]
        D[Paused]
    end

    A -->|payment failed| B
    B -->|payment recovered| A
    B -->|dunning exhausted| C
    A -->|user request| D
    D -->|resume| A
    A -->|user request| C
    C -->|reactivate| A
```

### Billing Cycles

- **Monthly**: Billed on the same day each month
- **Annual**: Billed upfront; prorated upgrades
- **Usage-based**: Metered billing with committed spend

### Proration

When a subscription changes mid-cycle:

1. Calculate unused time on old plan
2. Apply credit to new plan
3. Generate prorated invoice immediately
4. Reset billing anchor to change date

---

## 5. Dunning

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    A[Invoice Overdue] --> B[Day 1: Email reminder]
    B --> C{Payment retry}
    C -->|success| Z[Resolved]
    C -->|fail| D[Day 3: Retry + email]
    D --> E{Payment retry}
    E -->|success| Z
    E -->|fail| F[Day 7: Final notice + SMS]
    F --> G{Payment retry}
    G -->|success| Z
    G -->|fail| H[Day 10: Suspend service]
    H --> I[Day 30: Mark uncollectible]
```

### Dunning Rules

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | 4 | Total retry attempts |
| `retry_interval` | 3 days | Days between retries |
| `escalation_channels` | email → sms → call | Notification ladder |
| `suspension_threshold` | 10 days | Days before service pause |
| `writeoff_threshold` | 30 days | Days before bad debt |

### Dunning Configuration

```yaml
dunning_policies:
  standard:
    retries: 4
    interval_days: 3
    channels: [email, sms]
    suspend_after_days: 10
    writeoff_after_days: 30
  enterprise:
    retries: 6
    interval_days: 5
    channels: [email, sms, call]
    suspend_after_days: 21
    writeoff_after_days: 60
```

### Recovery Flow

1. Customer updates payment method
2. System retries outstanding invoices (oldest first)
3. On success: reactivate subscription, send confirmation
4. On failure: resume dunning from last step
