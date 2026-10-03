# APEX-OS Business Platform API

Base URL: `https://api.apex-os.com/v1`

---

## 1. Authentication

All endpoints require a Bearer token in the `Authorization` header.

```http
Authorization: Bearer <access_token>
```

### Obtain a Token

```http
POST /auth/token
Content-Type: application/json

{
  "api_key": "your-api-key",
  "api_secret": "your-api-secret"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Refresh a Token

```http
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 3600
}
```

---

## 2. Endpoints

### Users

#### List Users
```http
GET /users
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "usr_01",
      "name": "Jane Doe",
      "email": "jane@example.com",
      "role": "admin",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150
  }
}
```

#### Get User
```http
GET /users/{id}
```

**Response (200):**
```json
{
  "id": "usr_01",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "role": "admin",
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### Create User
```http
POST /users
Content-Type: application/json

{
  "name": "John Smith",
  "email": "john@example.com",
  "role": "member"
}
```

**Response (201):**
```json
{
  "id": "usr_02",
  "name": "John Smith",
  "email": "john@example.com",
  "role": "member",
  "created_at": "2025-06-01T14:22:00Z"
}
```

#### Update User
```http
PATCH /users/{id}
Content-Type: application/json

{
  "name": "John Smith Jr."
}
```

**Response (200):**
```json
{
  "id": "usr_02",
  "name": "John Smith Jr.",
  "email": "john@example.com",
  "role": "member",
  "created_at": "2025-06-01T14:22:00Z"
}
```

#### Delete User
```http
DELETE /users/{id}
```

**Response:** `204 No Content`

---

### Projects

#### List Projects
```http
GET /projects
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "prj_01",
      "name": "Website Redesign",
      "status": "active",
      "owner_id": "usr_01",
      "created_at": "2025-03-10T09:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 42
  }
}
```

#### Get Project
```http
GET /projects/{id}
```

**Response (200):**
```json
{
  "id": "prj_01",
  "name": "Website Redesign",
  "status": "active",
  "owner_id": "usr_01",
  "tasks_count": 15,
  "created_at": "2025-03-10T09:00:00Z"
}
```

#### Create Project
```http
POST /projects
Content-Type: application/json

{
  "name": "Mobile App",
  "description": "iOS and Android app",
  "owner_id": "usr_01"
}
```

**Response (201):**
```json
{
  "id": "prj_02",
  "name": "Mobile App",
  "description": "iOS and Android app",
  "status": "active",
  "owner_id": "usr_01",
  "created_at": "2025-06-01T15:00:00Z"
}
```

#### Update Project
```http
PATCH /projects/{id}
Content-Type: application/json

{
  "status": "completed"
}
```

**Response (200):**
```json
{
  "id": "prj_02",
  "name": "Mobile App",
  "status": "completed",
  "owner_id": "usr_01",
  "created_at": "2025-06-01T15:00:00Z"
}
```

#### Delete Project
```http
DELETE /projects/{id}
```

**Response:** `204 No Content`

---

### Tasks

#### List Tasks
```http
GET /tasks
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "tsk_01",
      "title": "Design homepage",
      "status": "in_progress",
      "priority": "high",
      "project_id": "prj_01",
      "assignee_id": "usr_02",
      "due_date": "2025-07-01"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 87
  }
}
```

#### Get Task
```http
GET /tasks/{id}
```

**Response (200):**
```json
{
  "id": "tsk_01",
  "title": "Design homepage",
  "description": "Create mockups for the new homepage",
  "status": "in_progress",
  "priority": "high",
  "project_id": "prj_01",
  "assignee_id": "usr_02",
  "due_date": "2025-07-01",
  "created_at": "2025-05-20T11:00:00Z"
}
```

#### Create Task
```http
POST /tasks
Content-Type: application/json

{
  "title": "Implement auth",
  "project_id": "prj_01",
  "priority": "medium",
  "assignee_id": "usr_02"
}
```

**Response (201):**
```json
{
  "id": "tsk_02",
  "title": "Implement auth",
  "status": "todo",
  "priority": "medium",
  "project_id": "prj_01",
  "assignee_id": "usr_02",
  "created_at": "2025-06-01T16:00:00Z"
}
```

#### Update Task
```http
PATCH /tasks/{id}
Content-Type: application/json

{
  "status": "done"
}
```

**Response (200):**
```json
{
  "id": "tsk_02",
  "title": "Implement auth",
  "status": "done",
  "priority": "medium",
  "project_id": "prj_01",
  "assignee_id": "usr_02",
  "created_at": "2025-06-01T16:00:00Z"
}
```

#### Delete Task
```http
DELETE /tasks/{id}
```

**Response:** `204 No Content`

---

### Teams

#### List Teams
```http
GET /teams
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "team_01",
      "name": "Engineering",
      "member_count": 8
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5
  }
}
```

#### Get Team
```http
GET /teams/{id}
```

**Response (200):**
```json
{
  "id": "team_01",
  "name": "Engineering",
  "members": ["usr_01", "usr_02", "usr_03"]
}
```

#### Create Team
```http
POST /teams
Content-Type: application/json

{
  "name": "Marketing",
  "members": ["usr_04", "usr_05"]
}
```

**Response (201):**
```json
{
  "id": "team_02",
  "name": "Marketing",
  "members": ["usr_04", "usr_05"]
}
```

#### Update Team
```http
PATCH /teams/{id}
Content-Type: application/json

{
  "members": ["usr_04", "usr_05", "usr_06"]
}
```

**Response (200):**
```json
{
  "id": "team_02",
  "name": "Marketing",
  "members": ["usr_04", "usr_05", "usr_06"]
}
```

#### Delete Team
```http
DELETE /teams/{id}
```

**Response:** `204 No Content`

---

### Comments

#### List Comments
```http
GET /comments?task_id=tsk_01
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "cmt_01",
      "body": "Looking good!",
      "author_id": "usr_01",
      "task_id": "tsk_01",
      "created_at": "2025-06-10T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 3
  }
}
```

#### Create Comment
```http
POST /comments
Content-Type: application/json

{
  "body": "Updated the design",
  "task_id": "tsk_01"
}
```

**Response (201):**
```json
{
  "id": "cmt_02",
  "body": "Updated the design",
  "author_id": "usr_02",
  "task_id": "tsk_01",
  "created_at": "2025-06-01T17:00:00Z"
}
```

#### Delete Comment
```http
DELETE /comments/{id}
```

**Response:** `204 No Content`

---

### Notifications

#### List Notifications
```http
GET /notifications
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "ntf_01",
      "type": "task_assigned",
      "message": "You were assigned to 'Implement auth'",
      "read": false,
      "created_at": "2025-06-01T16:05:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 12
  }
}
```

#### Mark as Read
```http
PATCH /notifications/{id}
Content-Type: application/json

{
  "read": true
}
```

**Response (200):**
```json
{
  "id": "ntf_01",
  "type": "task_assigned",
  "message": "You were assigned to 'Implement auth'",
  "read": true,
  "created_at": "2025-06-01T16:05:00Z"
}
```

---

## 3. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `bad_request` | 400 | Malformed request or missing required fields |
| `unauthorized` | 401 | Missing or invalid authentication token |
| `forbidden` | 403 | Insufficient permissions for this resource |
| `not_found` | 404 | Resource does not exist |
| `conflict` | 409 | Resource already exists or state conflict |
| `unprocessable` | 422 | Validation errors in request body |
| `rate_limited` | 429 | Too many requests; retry after delay |
| `internal_error` | 500 | Unexpected server error |

**Error Response Format:**
```json
{
  "error": {
    "code": "not_found",
    "message": "User with id 'usr_99' not found",
    "details": null
  }
}
```

---

## 4. Rate Limiting

- **Limit:** 1000 requests per minute per API key
- **Headers:**
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when the window resets
- **On exceed:** Returns `429 Too Many Requests` with `Retry-After` header

---

## 5. Pagination

All list endpoints support pagination via query parameters:

| Parameter | Default | Max | Description |
|-----------|---------|-----|-------------|
| `page` | 1 | — | Page number (1-indexed) |
| `per_page` | 20 | 100 | Items per page |

**Response includes:**
```json
{
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

---

## 6. Filtering and Sorting

### Filtering

Append filter parameters to list endpoints:

```
GET /tasks?status=done&priority=high&project_id=prj_01
GET /users?role=admin
GET /projects?status=active
GET /comments?task_id=tsk_01
```

### Sorting

Use the `sort` parameter with optional `-` prefix for descending:

```
GET /tasks?sort=-due_date
GET /users?sort=name
GET /projects?sort=-created_at
```

**Common sortable fields:** `created_at`, `updated_at`, `name`, `status`, `priority`, `due_date`

---

## 7. WebSocket Events

Connect to `wss://api.apex-os.com/v1/ws` with your Bearer token.

### Client → Server

```json
{
  "type": "subscribe",
  "channel": "project:prj_01"
}
```

### Server → Client Events

| Event | Channel | Payload |
|-------|---------|---------|
| `task.created` | `project:{id}` | Full task object |
| `task.updated` | `project:{id}` | Updated task object |
| `task.deleted` | `project:{id}` | `{ "id": "tsk_01" }` |
| `comment.created` | `task:{id}` | Full comment object |
| `user.mentioned` | `user:{id}` | Notification object |
| `project.updated` | `project:{id}` | Updated project object |

**Example event:**
```json
{
  "event": "task.updated",
  "channel": "project:prj_01",
  "data": {
    "id": "tsk_01",
    "status": "done",
    "updated_at": "usr_02"
  },
  "timestamp": "2025-06-01T17:30:00Z"
}
```

---

## Changelog

- **v1.0.0** — Initial release
