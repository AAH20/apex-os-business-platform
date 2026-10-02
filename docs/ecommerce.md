# E-Commerce Module

## 1. Architecture Overview

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    Client[Web / Mobile Client] -->|HTTPS| GW[API Gateway]
    GW --> Auth[Auth Service]
    GW --> Catalog[Catalog Service]
    GW --> Cart[Cart Service]
    GW --> Orders[Order Service]
    GW --> Payments[Payment Service]
    Catalog --> DB1[(Product DB)]
    Cart --> DB2[(Cart DB)]
    Orders --> DB3[(Order DB)]
    Payments --> DB4[(Payment DB)]
    Orders -->|Events| Bus[Event Bus]
    Bus --> Notifications[Notification Service]
    Bus --> Analytics[Analytics Service]
    Payments -->|Webhook| PSP[Payment Provider]
```

## 2. Product Catalog

```mermaid
%%{init: {'theme': 'dark'}}%%
erDiagram
    CATEGORY ||--o{ PRODUCT : contains
    PRODUCT ||--o{ VARIANT : has
    PRODUCT ||--o{ IMAGE : has
    PRODUCT ||--o{ REVIEW : receives
    CATEGORY {
        int id PK
        string name
        int parent_id FK
        string slug
    }
    PRODUCT {
        int id PK
        string name
        string description
        int category_id FK
        decimal base_price
        string sku
        boolean active
    }
    VARIANT {
        int id PK
        int product_id FK
        string option_name
        string option_value
        decimal price_adjustment
        int stock_qty
    }
    IMAGE {
        int id PK
        int product_id FK
        string url
        int sort_order
    }
    REVIEW {
        int id PK
        int product_id FK
        int user_id FK
        int rating
        string body
    }
```

**Key endpoints:**
- `GET /api/v1/products` — list with filters (category, price range, search)
- `GET /api/v1/products/:id` — detail with variants
- `POST /api/v1/products` — create (admin)
- `PUT /api/v1/products/:id` — update
- `DELETE /api/v1/products/:id` — soft delete

## 3. Shopping Cart

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] => Empty
    Empty => Active: add_item
    Active => Active: update_qty / remove_item
    Active => Checkout: proceed
    Checkout => Active: cancel
    Checkout => OrderPlaced: payment_success
    Checkout => Abandoned: timeout_30m
    Abandoned => Active: restore
    OrderPlaced => [*]
```

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    Cart[Cart Service] -->|read/write| Redis[(Redis Cache)]
    Cart -->|persist| CartDB[(Cart DB)]
    Cart -->|validate stock| Catalog[Catalog Service]
    Cart -->|price calc| Pricing[Pricing Engine]
    Pricing --> Discounts[Discount Service]
```

**Cart operations:**
- `POST /api/v1/cart/items` — add item (product_id, variant_id, qty)
- `PUT /api/v1/cart/items/:id` — update quantity
- `DELETE /api/v1/cart/items/:id` — remove item
- `GET /api/v1/cart` — get cart with totals
- `POST /api/v1/cart/apply-coupon` — apply discount code

## 4. Payment Processing

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant C as Client
    participant API as API Gateway
    participant PAY as Payment Service
    participant PSP as Payment Provider
    participant ORD as Order Service

    C->>API: POST /payments/intent
    API->>PAY: create_intent(order_id, amount)
    PAY->>PSP: create_payment_intent
    PSP-->>PAY: client_secret
    PAY-->>C: client_secret
    C->>PSP: confirm_payment(client_secret)
    PSP-->>PAY: webhook(payment_success)
    PAY->>ORD: confirm_order_payment
    ORD-->>C: order_confirmed
```

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    PS[Payment Service] -->|stripe| Stripe[Stripe]
    PS -->|paypal| PayPal[PayPal]
    PS -->|manual| Manual[Manual / Invoice]
    PS --> Vault[Token Vault]
    PS --> Ledger[Transaction Ledger]
    PS --> Fraud[Fraud Detection]
```

**Payment flow:**
1. Client creates payment intent → receives `client_secret`
2. Client confirms with provider SDK
3. Provider webhook → Payment Service updates status
4. On success → Order Service confirms order
5. On failure → cart restored, user notified

## 5. Order Management

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] => Pending
    Pending => Confirmed: payment_received
    Confirmed => Processing: warehouse_pick
    Processing => Shipped: label_created
    Shipped => Delivered: carrier_confirm
    Delivered => Completed: return_window_close
    Pending => Cancelled: user_cancel / payment_failed
    Confirmed => Cancelled: admin_cancel
    Shipped => Returned: return_requested
    Returned => Refunded: refund_processed
    Completed => [*]
    Cancelled => [*]
    Refunded => [*]
```

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    OS[Order Service] -->|read| OrderDB[(Order DB)]
    OS -->|events| Bus[Event Bus]
    Bus --> Fulfillment[Fulfillment Service]
    Bus --> Notifications[Notification Service]
    Bus --> Analytics[Analytics]
    Fulfillment --> WMS[WMS / 3PL]
    OS --> Returns[Returns Service]
    OS --> Refunds[Refund Service]
```

**Order endpoints:**
- `POST /api/v1/orders` — create from cart
- `GET /api/v1/orders` — list user orders
- `GET /api/v1/orders/:id` — order detail
- `POST /api/v1/orders/:id/cancel` — cancel (pre-ship)
- `POST /api/v1/orders/:id/return` — initiate return
- `GET /api/v1/orders/:id/tracking` — shipment tracking

**Order data model:**

| Field | Type | Description |
|-------|------|-------------|
| id | bigint PK | Order number |
| user_id | bigint FK | Customer |
| status | enum | Order state |
| total | decimal | Grand total |
| currency | char(3) | ISO 4217 |
| shipping_addr | jsonb | Snapshot |
| billing_addr | jsonb | Snapshot |
| created_at | timestamp | Order date |
