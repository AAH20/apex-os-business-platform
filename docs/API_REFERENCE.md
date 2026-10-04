# APEX-OS Business Platform API Reference

Base URL: `https://api.apex-os.example.com/v1`

All endpoints require Bearer token authentication via `Authorization: Bearer <token>` header.

Rate limit: 1000 requests/minute per API key. Exceeding returns `429 Too Many Requests`.

---

## Authentication

### POST /auth/register

Register a new user account.

**Request Body:**
```typescript
{
  email: string;          // required, valid email format
  password: string;       // required, min 8 chars, 1 uppercase, 1 number
  name: string;           // required, 2-100 chars
  organization?: string;  // optional
}
```

**Response (201):**
```typescript
{
  user: {
    id: string;
    email: string;
    name: string;
    organization: string | null;
    created_at: string;   // ISO 8601
  };
  token: string;          // JWT, expires in 24h
}
```

**Errors:**
| Code | Message |
|------|---------|
| 400 | `email` is required and must be valid |
| 400 | `password` must be at least 8 characters |
| 409 | Email already registered |

---

### POST /auth/login

Authenticate and receive JWT token.

**Request Body:**
```typescript
{
  email: string;
  password: string;
}
```

**Response (200):**
```typescript
{
  token: string;
  expires_at: string;
  user: { id: string; email: string; name: string };
}
```

**Errors:**
| Code | Message |
|------|---------|
| 401 | Invalid email or password |
| 423 | Account locked after 5 failed attempts |

---

### POST /auth/refresh

Refresh an expiring token.

**Headers:** `Authorization: Bearer <current_token>`

**Response (200):**
```typescript
{ token: string; expires_at: string; }
```

**Errors:**
| Code | Message |
|------|---------|
| 401 | Token expired or invalid |

---

### POST /auth/logout

Invalidate current token.

**Response (204):** No content.

---

## Users

### GET /users

List all users in the organization.

**Query Params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | number | 1 | Page number |
| per_page | number | 20 | Items per page (max 100) |
| sort | string | `created_at` | Sort field |
| order | string | `desc` | `asc` or `desc` |

**Response (200):**
```typescript
{
  data: Array<{
    id: string;
    email: string;
    name: string;
    role: 'admin' | 'member' | 'viewer';
    created_at: string;
    last_login: string | null;
  }>;
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}
```

**Errors:**
| Code | Message |
|------|---------|
| 401 | Unauthorized |
| 403 | Insufficient permissions (requires admin) |

---

### GET /users/:id

Get a specific user by ID.

**Response (200):**
```typescript
{
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'member' | 'viewer';
  organization: string;
  created_at: string;
  last_login: string | null;
}
```

**Errors:**
| Code | Message |
|------|---------|
| 401 | Unauthorized |
| 404 | User not found |

---

### PATCH /users/:id

Update user profile.

**Request Body:**
```typescript
{
  name?: string;
  email?: string;
  role?: 'admin' | 'member' | 'viewer';
}
```

**Response (200):** Updated user object.

**Errors:**
| Code | Message |
|------|---------|
| 400 | Invalid email format |
| 403 | Cannot modify own role |
| 404 | User not found |

---

### DELETE /users/:id

Remove a user from the organization.

**Response (204):** No content.

**Errors:**
| Code | Message |
|------|---------|
| 403 | Cannot delete self |
| 404 | User not found |

---

## Projects

### GET /projects

List all projects.

**Query Params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | number | 1 | Page number |
| per_page | number | 20 | Items per page |
| status | string | — | Filter by status |
| owner | string | — | Filter by owner ID |

**Response (200):**
```typescript
{
  data: Array<{
    id: string;
    name: string;
    description: string;
    status: 'active' | 'archived' | 'completed';
    owner_id: string;
    created_at: string;
    updated_at: string;
  }>;
  pagination: { page: number; per_page: number; total: number; total_pages: number; };
}
```

---

### POST /projects

Create a new project.

**Request Body:**
```typescript
{
  name: string;           // required, 1-200 chars
  description?: string;   // optional, max 2000 chars
  owner_id?: string;      // defaults to authenticated user
}
```

**Response (201):**
```typescript
{
  id: string;
  name: string;
  description: string;
  status: 'active';
  owner_id: string;
  created_at: string;
  updated_at: string;
}
```

**Errors:**
| Code | Message |
|------|---------|
| 400 | `name` is required |
| 400 | `name` exceeds 200 characters |

---

### GET /projects/:id

Get project details.

**Response (200):**
```typescript
{
  id: string;
  name: string;
  description: string;
  status: 'active' | 'archived' | 'completed';
  owner_id: string;
  members: Array<{ user_id: string; role: string }>;
  created_at: string;
  updated_at: string;
}
```

**Errors:**
| Code | Message |
|------|---------|
| 404 | Project not found |

---

### PATCH /projects/:id

Update project.

**Request Body:**
```typescript
{
  name?: string;
  description?: string;
  status?: 'active' | 'archived' | 'completed';
}
```

**Response (200):** Updated project object.

**Errors:**
| Code | Message |
|------|---------|
| 400 | Invalid status value |
| 404 | Project not found |

---

### DELETE /projects/:id

Delete a project.

**Response (204):** No content.

**Errors:**
| Code | Message |
|------|---------|
| 403 | Only project owner or admin can delete |
| 404 | Project not found |

---

## Tasks

### GET /tasks

List tasks with filtering.

**Query Params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | number | 1 | Page number |
| per_page | number | 20 | Items per page |
| project_id | string | — | Filter by project |
| assignee | string | — | Filter by assignee ID |
| status | string | — | Filter by status |
| priority | string | — | Filter by priority |

**Response (200):**
```typescript
{
  data: Array<{
    id: string;
    title: string;
    description: string;
    status: 'todo' | 'in_progress' | 'review' | 'done';
    priority: 'low' | 'medium' | 'high' | 'critical';
    project_id: string;
    assignee_id: string | null;
    due_date: string | null;
    created_at: string;
    updated_at: string;
  }>;
  pagination: { page: number; per_page: number; total: number; total_pages: number; };
}
```

---

### POST /tasks

Create a task.

**Request Body:**
```typescript
{
  title: string;              // required, 1-300 chars
  description?: string;
  project_id: string;         // required
  assignee_id?: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
  due_date?: string;          // ISO 8601 date
}
```

**Response (201):**
```typescript
{
  id: string;
  title: string;
  description: string;
  status: 'todo';
  priority: 'medium';
  project_id: string;
  assignee_id: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}
```

**Errors:**
| Code | Message |
|------|---------|
| 400 | `title` and `project_id` are required |
| 404 | Project not found |

---

### GET /tasks/:id

Get task details.

**Response (200):** Single task object with comments array.

---

### PATCH /tasks/:id

Update task fields.

**Request Body:**
```typescript
{
  title?: string;
  description?: string;
  status?: 'todo' | 'in_progress' | 'review' | 'done';
  priority?: 'low' | 'medium' | 'high' | 'critical';
  assignee_id?: string;
  due_date?: string | null;
}
```

**Response (200):** Updated task object.

**Errors:**
| Code | Message |
|------|---------|
| 404 | Task not found |

---

### DELETE /tasks/:id

Delete a task.

**Response (204):** No content.

---

## Comments

### GET /tasks/:taskId/comments

List comments on a task.

**Query Params:** `page`, `per_page` (default 20, max 100)

**Response (200):**
```typescript
{
  data: Array<{
    id: string;
    task_id: string;
    author_id: string;
    body: string;
    created_at: string;
  }>;
  pagination: { page: number; per_page: number; total: number; total_pages: number; };
}
```

---

### POST /tasks/:taskId/comments

Add a comment to a task.

**Request Body:**
```typescript
{ body: string; }  // required, 1-5000 chars
```

**Response (201):**
```typescript
{
  id: string;
  task_id: string;
  author_id: string;
  body: string;
  created_at: string;
}
```

**Errors:**
| Code | Message |
|------|---------|
| 400 | `body` is required |
| 404 | Task not found |

---

### DELETE /comments/:id

Delete a comment.

**Response (204):** No content.

**Errors:**
| Code | Message |
|------|---------|
| 403 | Only comment author or admin can delete |

---

## Organizations

### GET /organizations/:id

Get organization details.

**Response (200):**
```typescript
{
  id: string;
  name: string;
  plan: 'free' | 'pro' | 'enterprise';
  member_count: number;
  created_at: string;
}
```

---

### PATCH /organizations/:id

Update organization settings.

**Request Body:**
```typescript
{ name?: string; }
```

**Response (200):** Updated organization object.

**Errors:**
| Code | Message |
|------|---------|
| 403 | Admin role required |

---

### GET /organizations/:id/members

List organization members.

**Query Params:** `page`, `per_page`

**Response (200):**
```typescript
{
  data: Array<{
    user_id: string;
    name: string;
    email: string;
    role: 'admin' | 'member' | 'viewer';
    joined_at: string;
  }>;
  pagination: { page: number; per_page: number; total: number; total_pages: number; };
}
```

---

## Webhooks

### GET /webhooks

List configured webhooks.

**Response (200):**
```typescript
{
  data: Array<{
    id: string;
    url: string;
    events: string[];
    active: boolean;
    created_at: string;
  }>;
}
```

---

### POST /webhooks

Register a new webhook.

**Request Body:**
```typescript
{
  url: string;        // required, valid HTTPS URL
  events: string[];   // required, e.g. ["task.created", "task.updated"]
  secret?: string;    // optional, for HMAC signature
}
```

**Response (201):**
```typescript
{
  id: string;
  url: string;
  events: string[];
  active: boolean;
  secret: string;
  created_at: string;
}
```

**Errors:**
| Code | Message |
|------|---------|
| 400 | `url` must be a valid HTTPS URL |
| 400 | `events` array is required |

---

### DELETE /webhooks/:id

Remove a webhook.

**Response (204):** No content.

---

## Health & Monitoring

### GET /health

Service health check. No authentication required.

**Response (200):**
```typescript
{
  status: 'healthy';
  version: string;
  uptime: number;       // seconds
  database: 'connected';
}
```

---

### GET /metrics

Prometheus-compatible metrics. Requires admin role.

**Response (200):** Plain text Prometheus exposition format.

---

## Error Response Format

All errors return a consistent structure:

```typescript
{
  error: {
    code: string;       // machine-readable error code
    message: string;    // human-readable description
    details?: object;   // optional additional context
  };
}
```

**Common HTTP Status Codes:**
| Status | Meaning |
|--------|---------|
| 400 | Bad Request — validation error |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource does not exist |
| 409 | Conflict — resource already exists |
| 422 | Unprocessable Entity — semantic error |
| 429 | Too Many Requests — rate limit exceeded |
| 500 | Internal Server Error |
