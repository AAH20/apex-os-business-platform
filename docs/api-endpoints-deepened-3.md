# APEX-OS API — Deepened Modules (v3)

Base URL: `https://api.apex-os.io/v3` · Auth: `Authorization: Bearer <token>` · Content-Type: `application/json`

---

## 1. E-Commerce

### Cart

#### GET /ecommerce/cart
Retrieve the current user's active cart.
- **Response 200:** `{ "cart_id": "cart_abc", "items": [{ "sku": "SKU-001", "qty": 2, "unit_price": 29.99 }], "subtotal": 59.98, "currency": "USD" }`
- **Status:** 200, 401

#### POST /ecommerce/cart/items
Add item to cart.
- **Request:** `{ "sku": "SKU-001", "qty": 2 }`
- **Response 201:** `{ "cart_id": "cart_abc", "item_id": "itm_xyz", "subtotal": 59.98 }`
- **Status:** 201, 400, 404, 409

#### PATCH /ecommerce/cart/items/{item_id}
Update item quantity.
- **Request:** `{ "qty": 3 }`
- **Response 200:** `{ "item_id": "itm_xyz", "qty": 3, "subtotal": 89.97 }`
- **Status:** 200, 400, 404

#### DELETE /ecommerce/cart/items/{item_id}
Remove item from cart.
- **Response 204**
- **Status:** 204, 404

### Orders

#### GET /ecommerce/orders
List orders (paginated, filterable).
- **Query:** `?status=shipped&page=1&limit=20`
- **Response 200:** `{ "data": [{ "order_id": "ord_123", "status": "shipped", "total": 149.99 }], "total": 57, "page": 1 }`
- **Status:** 200, 401

#### GET /ecommerce/orders/{order_id}
Get order detail.
- **Response 200:** `{ "order_id": "ord_123", "status": "shipped", "items": [...], "total": 149.99, "tracking": "1Z999AA10123456784" }`
- **Status:** 200, 404

#### POST /ecommerce/orders
Create order from cart.
- **Request:** `{ "cart_id": "cart_abc", "shipping_address_id": "addr_1", "payment_method_id": "pm_card" }`
- **Response 201:** `{ "order_id": "ord_123", "status": "pending", "total": 149.99 }`
- **Status:** 201, 400, 402, 409

#### POST /ecommerce/orders/{order_id}/cancel
Cancel a pending/processing order.
- **Response 200:** `{ "order_id": "ord_123", "status": "cancelled" }`
- **Status:** 200, 409

### Payments

#### POST /ecommerce/payments/intent
Create payment intent.
- **Request:** `{ "order_id": "ord_123", "amount": 149.99, "currency": "USD", "method": "card" }`
- **Response 201:** `{ "intent_id": "pi_3Oq", "client_secret": "pi_3Oq_secret", "status": "requires_confirmation" }`
- **Status:** 201, 400, 402

#### POST /ecommerce/payments/{intent_id}/confirm
Confirm payment intent.
- **Request:** `{ "payment_method_id": "pm_card" }`
- **Response 200:** `{ "intent_id": "pi_3Oq", "status": "succeeded", "receipt_url": "https://pay.receipts/r_123" }`
- **Status:** 200, 402, 409

#### GET /ecommerce/payments/{intent_id}
Retrieve payment status.
- **Response 200:** `{ "intent_id": "pi_3Oq", "status": "succeeded", "amount": 149.99 }`
- **Status:** 200, 404

#### POST /ecommerce/payments/{intent_id}/refund
Refund a captured payment.
- **Request:** `{ "amount": 149.99, "reason": "customer_request" }`
- **Response 200:** `{ "refund_id": "re_3Oq", "status": "succeeded", "amount": 149.99 }`
- **Status:** 200, 400, 409

### Inventory

#### GET /ecommerce/inventory/{sku}
Get stock level for a SKU.
- **Response 200:** `{ "sku": "SKU-001", "on_hand": 250, "reserved": 12, "available": 238, "warehouse": "WH-EAST" }`
- **Status:** 200, 404

#### POST /ecommerce/inventory/reserve
Reserve stock for an order.
- **Request:** `{ "sku": "SKU-001", "qty": 2, "order_id": "ord_123" }`
- **Response 201:** `{ "reservation_id": "rsv_001", "expires_at": "2026-10-03T12:00:00Z" }`
- **Status:** 201, 409

#### POST /ecommerce/inventory/adjust
Adjust stock level (admin).
- **Request:** `{ "sku": "SKU-001", "delta": -5, "reason": "damaged" }`
- **Response 200:** `{ "sku": "SKU-001", "on_hand": 245 }`
- **Status:** 200, 400, 403

### Catalog

#### GET /ecommerce/catalog/products
List products with filters.
- **Query:** `?category=electronics&min_price=10&max_price=500&page=1`
- **Response 200:** `{ "data": [{ "sku": "SKU-001", "name": "Widget", "price": 29.99, "category": "electronics" }], "total": 128 }`
- **Status:** 200

#### GET /ecommerce/catalog/products/{sku}
Get product detail.
- **Response 200:** `{ "sku": "SKU-001", "name": "Widget", "description": "...", "price": 29.99, "images": [...], "attributes": { "color": "blue" } }`
- **Status:** 200, 404

#### POST /ecommerce/catalog/products
Create product (admin).
- **Request:** `{ "sku": "SKU-NEW", "name": "New Widget", "price": 49.99, "category": "electronics" }`
- **Response 201:** `{ "sku": "SKU-NEW", "status": "active" }`
- **Status:** 201, 400, 403

#### PATCH /ecommerce/catalog/products/{sku}
Update product.
- **Request:** `{ "price": 39.99 }`
- **Response 200:** `{ "sku": "SKU-001", "price": 39.99 }`
- **Status:** 200, 403, 404

---

## 2. Marketing

### Campaigns

#### GET /marketing/campaigns
List campaigns.
- **Query:** `?status=active&channel=email`
- **Response 200:** `{ "data": [{ "campaign_id": "cmp_001", "name": "Spring Sale", "status": "active", "channel": "email" }] }`
- **Status:** 200, 401

#### POST /marketing/campaigns
Create campaign.
- **Request:** `{ "name": "Spring Sale", "channel": "email", "audience_id": "seg_123", "start": "2026-03-01", "end": "2026-03-31" }`
- **Response 201:** `{ "campaign_id": "cmp_001", "status": "draft" }`
- **Status:** 201, 400

#### PATCH /marketing/campaigns/{campaign_id}
Update campaign.
- **Request:** `{ "status": "active" }`
- **Response 200:** `{ "campaign_id": "cmp_001", "status": "active" }`
- **Status:** 200, 404

#### DELETE /marketing/campaigns/{campaign_id}
Archive campaign.
- **Response 204**
- **Status:** 204, 404

### Email

#### POST /marketing/email/send
Send transactional email.
- **Request:** `{ "to": ["user@example.com"], "template": "order_confirmation", "variables": { "order_id": "ord_123" } }`
- **Response 202:** `{ "message_id": "msg_001", "status": "queued" }`
- **Status:** 202, 400

#### GET /marketing/email/templates
List email templates.
- **Response 200:** `{ "data": [{ "template_id": "tpl_order", "name": "Order Confirmation", "subject": "Your order" }] }`
- **Status:** 200

#### POST /marketing/email/bulk
Send bulk campaign email.
- **Request:** `{ "campaign_id": "cmp_001", "segment_id": "seg_123", "template": "spring_sale" }`
- **Response 202:** `{ "batch_id": "batch_001", "recipients": 5000, "status": "sending" }`
- **Status:** 202, 400

### Social

#### GET /marketing/social/accounts
List connected social accounts.
- **Response 200:** `{ "data": [{ "account_id": "acc_tw", "platform": "twitter", "handle": "@brand" }] }`
- **Status:** 200

#### POST /marketing/social/posts
Create social post.
- **Request:** `{ "account_id": "acc_tw", "content": "New product launch!", "media": ["https://cdn.img/launch.png"], "scheduled_at": "2026-10-05T14:00:00Z" }`
- **Response 201:** `{ "post_id": "post_001", "status": "scheduled" }`
- **Status:** 201, 400

#### GET /marketing/social/posts/{post_id}/metrics
Get post performance.
- **Response 200:** `{ "post_id": "post_001", "impressions": 12000, "engagement": 340, "clicks": 89 }`
- **Status:** 200, 404

### Attribution

#### GET /marketing/attribution/conversions
List conversion events.
- **Query:** `?utm_source=google&start=2026-09-01&end=2026-09-30`
- **Response 200:** `{ "data": [{ "conversion_id": "cnv_001", "revenue": 149.99, "utm_source": "google", "utm_campaign": "spring" }] }`
- **Status:** 200

#### POST /marketing/attribution/track
Track conversion event.
- **Request:** `{ "order_id": "ord_123", "utm_source": "google", "utm_campaign": "spring", "revenue": 149.99 }`
- **Response 201:** `{ "conversion_id": "cnv_001" }`
- **Status:** 201, 400

### ROI

#### GET /marketing/roi/summary
Get ROI summary by campaign/channel.
- **Query:** `?start=2026-09-01&end=2026-09-30&group_by=campaign`
- **Response 200:** `{ "data": [{ "campaign_id": "cmp_001", "spend": 5000, "revenue": 25000, "roi": 4.0 }] }`
- **Status:** 200

#### GET /marketing/roi/campaigns/{campaign_id}
Get campaign ROI detail.
- **Response 200:** `{ "campaign_id": "cmp_001", "spend": 5000, "revenue": 25000, "roi": 4.0, "roas": 5.0, "cpa": 25.00 }`
- **Status:** 200, 404

---

## 3. Support

### Tickets

#### GET /support/tickets
List tickets.
- **Query:** `?status=open&priority=high&assignee=agent_1`
- **Response 200:** `{ "data": [{ "ticket_id": "tkt_001", "subject": "Login issue", "status": "open", "priority": "high" }] }`
- **Status:** 200, 401

#### POST /support/tickets
Create ticket.
- **Request:** `{ "subject": "Login issue", "description": "Cannot log in", "priority": "high", "category": "account" }`
- **Response 201:** `{ "ticket_id": "tkt_001", "status": "open" }`
- **Status:** 201, 400

#### GET /support/tickets/{ticket_id}
Get ticket detail.
- **Response 200:** `{ "ticket_id": "tkt_001", "subject": "Login issue", "status": "open", "messages": [...], "assignee": "agent_1" }`
- **Status:** 200, 404

#### PATCH /support/tickets/{ticket_id}
Update ticket (status, priority, assignee).
- **Request:** `{ "status": "in_progress", "assignee": "agent_2" }`
- **Response 200:** `{ "ticket_id": "tkt_001", "status": "in_progress", "assignee": "agent_2" }`
- **Status:** 200, 404

#### POST /support/tickets/{ticket_id}/messages
Add message to ticket.
- **Request:** `{ "body": "Please try resetting your password.", "internal": false }`
- **Response 201:** `{ "message_id": "msg_001", "ticket_id": "tkt_001" }`
- **Status:** 201, 400

### Knowledge Base

#### GET /support/kb/articles
Search KB articles.
- **Query:** `?q=password+reset&category=account`
- **Response 200:** `{ "data": [{ "article_id": "art_001", "title": "Reset Password", "category": "account" }] }`
- **Status:** 200

#### GET /support/kb/articles/{article_id}
Get article detail.
- **Response 200:** `{ "article_id": "art_001", "title": "Reset Password", "body": "...", "views": 1200 }`
- **Status:** 200, 404

#### POST /support/kb/articles
Create KB article (admin).
- **Request:** `{ "title": "Reset Password", "body": "...", "category": "account", "published": true }`
- **Response 201:** `{ "article_id": "art_001" }`
- **Status:** 201, 403

### Live Chat

#### POST /support/chat/sessions
Start chat session.
- **Request:** `{ "visitor_id": "vis_123", "page": "/checkout" }`
- **Response 201:** `{ "session_id": "chat_001", "status": "waiting", "queue_position": 2 }`
- **Status:** 201

#### GET /support/chat/sessions/{session_id}
Get chat session state.
- **Response 200:** `{ "session_id": "chat_001", "status": "active", "agent": "agent_1", "messages": [...] }`
- **Status:** 200, 404

#### POST /support/chat/sessions/{session_id}/messages
Send chat message.
- **Request:** `{ "body": "I need help with my order" }`
- **Response 201:** `{ "message_id": "msg_001", "sender": "visitor" }`
- **Status:** 201, 400

### Surveys

#### GET /support/surveys
List surveys.
- **Response 200:** `{ "data": [{ "survey_id": "srv_001", "title": "Post-Purchase", "status": "active" }] }`
- **Status:** 200

#### POST /support/surveys/{survey_id}/responses
Submit survey response.
- **Request:** `{ "ticket_id": "tkt_001", "rating": 5, "feedback": "Great service!" }`
- **Response 201:** `{ "response_id": "resp_001" }`
- **Status:** 201, 400

### Analytics

#### GET /support/analytics/csAT
CSAT metrics.
- **Query:** `?start=2026-09-01&end=2026-09-30`
- **Response 200:** `{ "average_csat": 4.5, "responses": 320, "distribution": { "5": 200, "4": 80, "3": 25, "2": 10, "1": 5 } }`
- **Status:** 200

#### GET /support/analytics/response-times
First-response and resolution times.
- **Response 200:** `{ "avg_first_response_min": 12, "avg_resolution_hours": 4.2, "sla_compliance_pct": 96 }`
- **Status:** 200

---

## 4. Supply Chain

### Forecasting

#### GET /supply-chain/forecasts
List demand forecasts.
- **Query:** `?sku=SKU-001&horizon=30d`
- **Response 200:** `{ "data": [{ "forecast_id": "fc_001", "sku": "SKU-001", "horizon_days": 30, "predicted_demand": 1200, "confidence": 0.87 }] }`
- **Status:** 200

#### POST /supply-chain/forecasts/generate
Generate new forecast.
- **Request:** `{ "sku": "SKU-001", "horizon_days": 30, "model": "arima" }`
- **Response 202:** `{ "forecast_id": "fc_002", "status": "generating" }`
- **Status:** 202, 400

### Suppliers

#### GET /supply-chain/suppliers
List suppliers.
- **Response 200:** `{ "data": [{ "supplier_id": "sup_001", "name": "Acme Parts", "lead_time_days": 14, "rating": 4.5 }] }`
- **Status:** 200

#### POST /supply-chain/suppliers
Create supplier.
- **Request:** `{ "name": "Acme Parts", "contact_email": "orders@acme.com", "lead_time_days": 14 }`
- **Response 201:** `{ "supplier_id": "sup_001" }`
- **Status:** 201, 400

#### GET /supply-chain/suppliers/{supplier_id}/performance
Get supplier performance metrics.
- **Response 200:** `{ "supplier_id": "sup_001", "on_time_pct": 94, "quality_pct": 98, "fill_rate": 96 }`
- **Status:** 200, 404

### Logistics

#### GET /supply-chain/shipments
List shipments.
- **Query:** `?status=in_transit&carrier=fedex`
- **Response 200:** `{ "data": [{ "shipment_id": "shp_001", "status": "in_transit", "carrier": "fedex", "tracking": "7890123456" }] }`
- **Status:** 200

#### POST /supply-chain/shipments
Create shipment.
- **Request:** `{ "order_ids": ["ord_123"], "carrier": "fedex", "service": "ground", "origin": "WH-EAST", "destination": "addr_1" }`
- **Response 201:** `{ "shipment_id": "shp_001", "tracking": "7890123456", "label_url": "https://labels.fedex/l_001" }`
- **Status:** 201, 400

#### GET /supply-chain/shipments/{shipment_id}/tracking
Get tracking events.
- **Response 200:** `{ "shipment_id": "shp_001", "events": [{ "timestamp": "2026-10-02T10:00:00Z", "status": "in_transit", "location": "Memphis, TN" }] }`
- **Status:** 200, 404

### Warehouse

#### GET /supply-chain/warehouses
List warehouses.
- **Response 200:** `{ "data": [{ "warehouse_id": "WH-EAST", "name": "East DC", "location": "Newark, NJ", "capacity": 50000 }] }`
- **Status:** 200

#### GET /supply-chain/warehouses/{warehouse_id}/inventory
Get warehouse stock levels.
- **Response 200:** `{ "warehouse_id": "WH-EAST", "items": [{ "sku": "SKU-001", "on_hand": 250, "reserved": 12 }] }`
- **Status:** 200, 404

#### POST /supply-chain/warehouses/{warehouse_id}/transfer
Transfer stock between warehouses.
- **Request:** `{ "to_warehouse": "WH-WEST", "sku": "SKU-001", "qty": 50 }`
- **Response 201:** `{ "transfer_id": "trf_001", "status": "in_transit" }`
- **Status:** 201, 400, 409

### Procurement

#### GET /supply-chain/purchase-orders
List purchase orders.
- **Query:** `?status=pending&supplier_id=sup_001`
- **Response 200:** `{ "data": [{ "po_id": "po_001", "supplier_id": "sup_001", "status": "pending", "total": 5000 }] }`
- **Status:** 200

#### POST /supply-chain/purchase-orders
Create purchase order.
- **Request:** `{ "supplier_id": "sup_001", "items": [{ "sku": "SKU-001", "qty": 100, "unit_cost": 10.00 }], "delivery_date": "2026-10-15" }`
- **Response 201:** `{ "po_id": "po_001", "status": "draft", "total": 1000 }`
- **Status:** 201, 400

#### POST /supply-chain/purchase-orders/{po_id}/approve
Approve purchase order.
- **Response 200:** `{ "po_id": "po_001", "status": "approved" }`
- **Status:** 200, 409

#### POST /supply-chain/purchase-orders/{po_id}/receive
Record PO receipt.
- **Request:** `{ "items": [{ "sku": "SKU-001", "received_qty": 100 }] }`
- **Response 200:** `{ "po_id": "po_001", "status": "received", "received_at": "2026-10-14T09:00:00Z" }`
- **Status:** 200, 400

---

## 5. Manufacturing

### MRP

#### GET /manufacturing/mrp/runs
List MRP runs.
- **Response 200:** `{ "data": [{ "run_id": "mrp_001", "status": "completed", "created_at": "2026-10-01T08:00:00Z" }] }`
- **Status:** 200

#### POST /manufacturing/mrp/runs
Execute MRP run.
- **Request:** `{ "horizon_days": 30, "plant": "PLANT-1", "items": ["SKU-001", "SKU-002"] }`
- **Response 202:** `{ "run_id": "mrp_002", "status": "running" }`
- **Status:** 202, 400

#### GET /manufacturing/mrp/runs/{run_id}
Get MRP run results.
- **Response 200:** `{ "run_id": "mrp_001", "status": "completed", "requirements": [{ "sku": "SKU-001", "gross": 500, "scheduled": 200, "net": 300 }] }`
- **Status:** 200, 404

### Quality

#### GET /manufacturing/quality/inspections
List quality inspections.
- **Query:** `?status=failed&line=LINE-A`
- **Response 200:** `{ "data": [{ "inspection_id": "insp_001", "line": "LINE-A", "result": "failed", "defects": 3 }] }`
- **Status:** 200

#### POST /manufacturing/quality/inspections
Record inspection result.
- **Request:** `{ "work_order_id": "wo_001", "line": "LINE-A", "sample_size": 50, "defects": 1, "result": "passed" }`
- **Response 201:** `{ "inspection_id": "insp_002", "result": "passed" }`
- **Status:** 201, 400

#### GET /manufacturing/quality/defects
List defect records.
- **Response 200:** `{ "data": [{ "defect_id": "def_001", "type": "scratch", "severity": "minor", "inspection_id": "insp_001" }] }`
- **Status:** 200

### Maintenance

#### GET /manufacturing/maintenance/work-orders
List maintenance work orders.
- **Query:** `?status=open&asset=press_01`
- **Response 200:** `{ "data": [{ "wo_id": "mwo_001", "asset_id": "press_01", "status": "open", "priority": "high" }] }`
- **Status:** 200

#### POST /manufacturing/maintenance/work-orders
Create maintenance work order.
- **Request:** `{ "asset_id": "press_01", "type": "preventive", "description": "Replace hydraulic seal", "scheduled_date": "2026-10-10" }`
- **Response 201:** `{ "wo_id": "mwo_001", "status": "scheduled" }`
- **Status:** 201, 400

#### PATCH /manufacturing/maintenance/work-orders/{wo_id}
Update maintenance work order.
- **Request:** `{ "status": "completed", "completed_at": "2026-10-10T14:00:00Z", "notes": "Seal replaced" }`
- **Response 200:** `{ "wo_id": "mwo_001", "status": "completed" }`
- **Status:** 200, 404

#### GET /manufacturing/maintenance/assets
List assets.
- **Response 200:** `{ "data": [{ "asset_id": "press_01", "name": "Hydraulic Press 1", "status": "operational", "last_service": "2026-09-01" }] }`
- **Status:** 200

### BOM

#### GET /manufacturing/boms
List bills of materials.
- **Response 200:** `{ "data": [{ "bom_id": "bom_001", "product_sku": "SKU-001", "version": "1.2", "status": "active" }] }`
- **Status:** 200

#### GET /manufacturing/boms/{bom_id}
Get BOM detail with components.
- **Response 200:** `{ "bom_id": "bom_001", "product_sku": "SKU-001", "version": "1.2", "components": [{ "sku": "RAW-001", "qty": 2, "uom": "pcs" }] }`
- **Status:** 200, 404

#### POST /manufacturing/boms
Create BOM.
- **Request:** `{ "product_sku": "SKU-001", "version": "1.0", "components": [{ "sku": "RAW-001", "qty": 2, "uom": "pcs" }] }`
- **Response 201:** `{ "bom_id": "bom_002", "status": "draft" }`
- **Status:** 201, 400

### Shop Floor

#### GET /manufacturing/shop-floor/work-orders
List production work orders.
- **Query:** `?status=in_progress&line=LINE-A`
- **Response 200:** `{ "data": [{ "wo_id": "wo_001", "product_sku": "SKU-001", "qty": 100, "status": "in_progress", "line": "LINE-A" }] }`
- **Status:** 200

#### POST /manufacturing/shop-floor/work-orders
Create production work order.
- **Request:** `{ "product_sku": "SKU-001", "qty": 100, "line": "LINE-A", "bom_id": "bom_001", "due_date": "2026-10-20" }`
- **Response 201:** `{ "wo_id": "wo_001", "status": "released" }`
- **Status:** 201, 400

#### POST /manufacturing/shop-floor/work-orders/{wo_id}/start
Start production.
- **Request:** `{ "operator_id": "op_001", "line": "LINE-A" }`
- **Response 200:** `{ "wo_id": "wo_001", "status": "in_progress", "started_at": "2026-10-03T08:00:00Z" }`
- **Status:** 200, 409

#### POST /manufacturing/shop-floor/work-orders/{wo_id}/complete
Complete production.
- **Request:** `{ "produced_qty": 98, "scrap_qty": 2, "notes": "Minor tool wear" }`
- **Response 200:** `{ "wo_id": "wo_001", "status": "completed", "produced_qty": 98, "scrap_qty": 2 }`
- **Status:** 200, 400

#### GET /manufacturing/shop-floor/lines/{line_id}/status
Get real-time line status.
- **Response 200:** `{ "line_id": "LINE-A", "status": "running", "current_wo": "wo_001", "operator": "op_001", "oee": 0.87, "output_today": 450 }`
- **Status:** 200, 404
