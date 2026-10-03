# APEX-OS Business Platform — CRUD API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Error Codes](#error-codes)
5. [CRUD Operations](#crud-operations)
6. [Endpoints Reference](#endpoints-reference)

---

## Overview

The APEX-OS Business Platform provides a RESTful API for managing business entities including users, organizations, projects, tasks, products, orders, invoices, and more. All endpoints follow standard HTTP conventions and return JSON responses.

**Base URL:** `https://api.apex-os.com/v1`

**Content-Type:** `application/json`

---

## Authentication

All API requests require authentication via Bearer token in the Authorization header.

### Obtaining a Token

```http
POST /auth/token
Content-Type: application/json

{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "grant_type": "client_credentials"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read write"
}
```

### Using the Token

```http
GET /users
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Refresh

```http
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

### Authentication Errors

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 401 | `UNAUTHORIZED` | Missing or invalid token |
| 401 | `TOKEN_EXPIRED` | Token has expired |
| 403 | `FORBIDDEN` | Insufficient permissions |

---

## Rate Limiting

Rate limits are applied per API key and per endpoint category.

### Default Limits

| Category | Limit | Window |
|----------|-------|--------|
| Standard CRUD | 100 requests | 1 minute |
| Bulk Operations | 10 requests | 1 minute |
| Authentication | 5 requests | 1 minute |
| Search | 30 requests | 1 minute |

### Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699999999
```

### Rate Limit Exceeded

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Try again in 45 seconds.",
    "retry_after": 45
  }
}
```

---

## Error Codes

### Standard Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": {},
    "request_id": "req_abc123"
  }
}
```

### HTTP Status Codes

| Status | Meaning |
|--------|---------|
| 200 | OK — Request succeeded |
| 201 | Created — Resource created successfully |
| 204 | No Content — Resource deleted successfully |
| 400 | Bad Request — Invalid input |
| 401 | Unauthorized — Authentication required |
| 403 | Forbidden — Insufficient permissions |
| 404 | Not Found — Resource does not exist |
| 409 | Conflict — Resource already exists or conflicts |
| 422 | Unprocessable Entity — Validation failed |
| 429 | Too Many Requests — Rate limit exceeded |
| 500 | Internal Server Error — Server error |
| 503 | Service Unavailable — Maintenance or overload |

### Application Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource not found |
| `DUPLICATE_RESOURCE` | 409 | Resource with same unique key exists |
| `INSUFFICIENT_FUNDS` | 400 | Not enough balance for operation |
| `OPERATION_NOT_ALLOWED` | 403 | Action not permitted on this resource |
| `DEPENDENCY_EXISTS` | 409 | Cannot delete: dependent resources exist |
| `QUOTA_EXCEEDED` | 429 | Resource quota exceeded |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## CRUD Operations

### Create (POST)

Create a new resource.

```http
POST /users
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "member"
}
```

**Response (201 Created):**
```json
{
  "id": "usr_abc123",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "member",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Read (GET)

Retrieve a single resource or a list of resources.

```http
GET /users/usr_abc123
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": "usr_abc123",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "member",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**List with pagination:**
```http
GET /users?page=1&limit=20&sort=name&order=asc
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "usr_abc123",
      "name": "John Doe",
      "email": "john@example.com"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

### Update (PUT/PATCH)

Update an existing resource.

**Full update (PUT):**
```http
PUT /users/usr_abc123
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "John Updated",
  "email": "john.new@example.com",
  "role": "admin"
}
```

**Partial update (PATCH):**
```http
PATCH /users/usr_abc123
Authorization: Bearer <token>
Content-Type: application/json

{
  "role": "admin"
}
```

**Response (200 OK):**
```json
{
  "id": "usr_abc123",
  "name": "John Updated",
  "email": "john.new@example.com",
  "role": "admin",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

### Delete (DELETE)

Remove a resource.

```http
DELETE /users/usr_abc123
Authorization: Bearer <token>
```

**Response (204 No Content):** Empty body

**Soft delete response (200 OK):**
```json
{
  "id": "usr_abc123",
  "deleted": true,
  "deleted_at": "2024-01-15T11:30:00Z"
}
```

---

## Endpoints Reference

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/users` | Create a new user |
| GET | `/users` | List all users |
| GET | `/users/{id}` | Get user by ID |
| PUT | `/users/{id}` | Full update of user |
| PATCH | `/users/{id}` | Partial update of user |
| DELETE | `/users/{id}` | Delete a user |

### Organizations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/organizations` | Create organization |
| GET | `/organizations` | List organizations |
| GET | `/organizations/{id}` | Get organization by ID |
| PUT | `/organizations/{id}` | Full update |
| PATCH | `/organizations/{id}` | Partial update |
| DELETE | `/organizations/{id}` | Delete organization |

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects` | Create project |
| GET | `/projects` | List projects |
| GET | `/projects/{id}` | Get project by ID |
| PUT | `/projects/{id}` | Full update |
| PATCH | `/projects/{id}` | Partial update |
| DELETE | `/projects/{id}` | Delete project |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tasks` | Create task |
| GET | `/tasks` | List tasks |
| GET | `/tasks/{id}` | Get task by ID |
| PUT | `/tasks/{id}` | Full update |
| PATCH | `/tasks/{id}` | Partial update |
| DELETE | `/tasks/{id}` | Delete task |

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/products` | Create product |
| GET | `/products` | List products |
| GET | `/products/{id}` | Get product by ID |
| PUT | `/products/{id}` | Full update |
| PATCH | `/products/{id}` | Partial update |
| DELETE | `/products/{id}` | Delete product |

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orders` | Create order |
| GET | `/orders` | List orders |
| GET | `/orders/{id}` | Get order by ID |
| PUT | `/orders/{id}` | Full update |
| PATCH | `/orders/{id}` | Partial update |
| DELETE | `/orders/{id}` | Delete order |

### Invoices

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/invoices` | Create invoice |
| GET | `/invoices` | List invoices |
| GET | `/invoices/{id}` | Get invoice by ID |
| PUT | `/invoices/{id}` | Full update |
| PATCH | `/invoices/{id}` | Partial update |
| DELETE | `/invoices/{id}` | Delete invoice |

### Customers

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/customers` | Create customer |
| GET | `/customers` | List customers |
| GET | `/customers/{id}` | Get customer by ID |
| PUT | `/customers/{id}` | Full update |
| PATCH | `/customers/{id}` | Partial update |
| DELETE | `/customers/{id}` | Delete customer |

### Suppliers

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/suppliers` | Create supplier |
| GET | `/suppliers` | List suppliers |
| GET | `/suppliers/{id}` | Get supplier by ID |
| PUT | `/suppliers/{id}` | Full update |
| PATCH | `/suppliers/{id}` | Partial update |
| DELETE | `/suppliers/{id}` | Delete supplier |

### Inventory

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/inventory` | Create inventory item |
| GET | `/inventory` | List inventory items |
| GET | `/inventory/{id}` | Get inventory item by ID |
| PUT | `/inventory/{id}` | Full update |
| PATCH | `/inventory/{id}` | Partial update |
| DELETE | `/inventory/{id}` | Delete inventory item |

### Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/payments` | Create payment |
| GET | `/payments` | List payments |
| GET | `/payments/{id}` | Get payment by ID |
| PUT | `/payments/{id}` | Full update |
| PATCH | `/payments/{id}` | Partial update |
| DELETE | `/payments/{id}` | Delete payment |

### Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reports` | Generate report |
| GET | `/reports` | List reports |
| GET | `/reports/{id}` | Get report by ID |
| PUT | `/reports/{id}` | Full update |
| PATCH | `/reports/{id}` | Partial update |
| DELETE | `/reports/{id}` | Delete report |

### Roles & Permissions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/roles` | Create role |
| GET | `/roles` | List roles |
| GET | `/roles/{id}` | Get role by ID |
| PUT | `/roles/{id}` | Full update |
| PATCH | `/roles/{id}` | Partial update |
| DELETE | `/roles/{id}` | Delete role |

### Audit Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/audit-logs` | List audit logs |
| GET | `/audit-logs/{id}` | Get audit log by ID |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhooks` | Create webhook |
| GET | `/webhooks` | List webhooks |
| GET | `/webhooks/{id}` | Get webhook by ID |
| PUT | `/webhooks/{id}` | Full update |
| PATCH | `/webhooks/{id}` | Partial update |
| DELETE | `/webhooks/{id}` | Delete webhook |

### Bulk Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/bulk/users` | Bulk create users |
| PUT | `/bulk/users` | Bulk update users |
| DELETE | `/bulk/users` | Bulk delete users |
| POST | `/bulk/projects` | Bulk create projects |
| PUT | `/bulk/projects` | Bulk update projects |
| DELETE | `/bulk/projects` | Bulk delete projects |

---

## Query Parameters

### Pagination

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 20 | Items per page (max 100) |

### Sorting

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sort` | string | `created_at` | Field to sort by |
| `order` | string | `desc` | Sort order: `asc` or `desc` |

### Filtering

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter[field]` | string | Filter by field value |
| `q` | string | Search query string |

---

## Request & Response Headers

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | Bearer token |
| `Content-Type` | Yes | `application/json` |
| `X-Request-ID` | No | Unique request identifier |
| `X-Idempotency-Key` | No | Idempotency key for safe retries |

### Response Headers

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Request identifier for debugging |
| `X-RateLimit-Limit` | Request limit per window |
| `X-RateLimit-Remaining` | Remaining requests in window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |

---

## Idempotency

For safe retries, include an `X-Idempotency-Key` header with POST, PUT, PATCH, and DELETE requests. The server will return the original response if the same key is reused within 24 hours.

---

## Versioning

The API uses URL path versioning. Current version: `v1`. Breaking changes will increment the version.

---

## SDKs & Libraries

- JavaScript: `npm install @apex-os/sdk`
- Python: `pip install apex-os-sdk`
- Ruby: `gem install apex-os-sdk`

---

## Support

- Documentation: https://docs.apex-os.com
- API Status: https://status.apex-os.com
- Support Email: api-support@apex-os.com
