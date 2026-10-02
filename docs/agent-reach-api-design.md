# Agent Reach API Design

## 1. REST API

**Base URL:** `https://api.apex-os.io/v1`
**Auth:** `Authorization: Bearer <token>`

### Agents
| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | List agents (paginated) |
| POST | `/agents` | Create agent |
| GET | `/agents/{id}` | Get agent details |
| PATCH | `/agents/{id}` | Update agent |
| DELETE | `/agents/{id}` | Delete agent |
| POST | `/agents/{id}/deploy` | Deploy to environment |
| POST | `/agents/{id}/undeploy` | Remove from environment |
| GET | `/agents/{id}/status` | Runtime status |
| GET | `/agents/{id}/logs` | Stream logs (SSE) |

### Tasks
| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List tasks (filter by agent/status) |
| POST | `/tasks` | Create task |
| GET | `/tasks/{id}` | Get task details |
| PATCH | `/tasks/{id}` | Cancel/retry task |
| DELETE | `/tasks/{id}` | Delete task |
| GET | `/tasks/{id}/result` | Get task result |
| POST | `/tasks/{id}/retry` | Retry failed task |

### Environments
| Method | Path | Description |
|--------|------|-------------|
| GET | `/environments` | List environments |
| POST | `/environments` | Create environment |
| GET | `/environments/{id}` | Get environment |
| DELETE | `/environments/{id}` | Delete environment |

### Tools
| Method | Path | Description |
|--------|------|-------------|
| GET | `/tools` | List available tools |
| POST | `/tools/{id}/invoke` | Invoke tool directly |

**Query params:** `page`, `limit` (max 200), `sort`, `filter`

**Response envelope:**
```json
{ "data": {}, "meta": { "page": 1, "limit": 50, "total": 120 }, "links": { "self": "...", "next": "..." } }
```

**Error envelope:**
```json
{ "error": { "code": "AGENT_NOT_FOUND", "message": "...", "details": {} } }
```

---

## 2. WebSocket API

**Endpoint:** `wss://api.apex-os.io/v1/ws?token=<jwt>`

### Client → Server
```json
{ "type": "subscribe", "channel": "agent:{id}", "events": ["status_change", "log"] }
{ "type": "subscribe", "channel": "task:{id}", "events": ["progress", "result"] }
{ "type": "command", "agent_id": "...", "command": "pause", "payload": {} }
{ "type": "unsubscribe", "channel": "agent:{id}" }
```

### Server → Client
```json
{ "type": "event", "channel": "agent:{id}", "event": "status_change",
  "data": { "agent_id": "...", "previous": "running", "current": "paused", "timestamp": "..." } }
{ "type": "event", "channel": "task:{id}", "event": "progress",
  "data": { "task_id": "...", "percent": 45, "message": "..." } }
{ "type": "event", "channel": "agent:{id}", "event": "log",
  "data": { "level": "info", "message": "...", "timestamp": "..." } }
{ "type": "ping", "timestamp": 1696240200 }
```

**Lifecycle:** connect → `connected` (session ID) → subscribe → events → ping/pong (30s) → `close`

---

## 3. gRPC API

**Proto:** `agent_reach.proto` | **Package:** `agentreach.v1`

```protobuf
service AgentReachService {
  rpc ListAgents(ListAgentsRequest) returns (ListAgentsResponse);
  rpc GetAgent(GetAgentRequest) returns (Agent);
  rpc CreateAgent(CreateAgentRequest) returns (Agent);
  rpc UpdateAgent(UpdateAgentRequest) returns (Agent);
  rpc DeleteAgent(DeleteAgentRequest) returns (google.protobuf.Empty);
  rpc DeployAgent(DeployAgentRequest) returns (Agent);
  rpc GetAgentStatus(GetAgentStatusRequest) returns (AgentStatus);
  rpc ListTasks(ListTasksRequest) returns (ListTasksResponse);
  rpc GetTask(GetTaskRequest) returns (Task);
  rpc CreateTask(CreateTaskRequest) returns (Task);
  rpc CancelTask(CancelTaskRequest) returns (Task);
  rpc StreamTaskEvents(StreamTaskEventsRequest) returns (stream TaskEvent);
  rpc StreamAgentEvents(StreamAgentEventsRequest) returns (stream AgentEvent);
  rpc SendCommand(SendCommandRequest) returns (CommandResponse);
  rpc BidirectionalStream(stream ClientMessage) returns (stream ServerMessage);
  rpc InvokeTool(InvokeToolRequest) returns (InvokeToolResponse);
  rpc ListTools(ListToolsRequest) returns (ListToolsResponse);
}

message Agent {
  string id = 1; string name = 2; string description = 3; string status = 4;
  string environment_id = 5; google.protobuf.Timestamp created_at = 6;
  google.protobuf.Timestamp updated_at = 7; map<string, string> labels = 8;
  AgentConfig config = 9;
}
message AgentConfig {
  string model = 1; float temperature = 2; int32 max_tokens = 3;
  repeated string tools = 4; map<string, string> parameters = 5;
}
message Task {
  string id = 1; string agent_id = 2; string status = 3; string input = 4;
  string result = 5; int32 progress_percent = 6;
  google.protobuf.Timestamp created_at = 7; google.protobuf.Timestamp completed_at = 8;
  string error_message = 9;
}
message TaskEvent { string task_id = 1; string event_type = 2; string data = 3; google.protobuf.Timestamp timestamp = 4; }
message AgentEvent { string agent_id = 1; string event_type = 2; string data = 3; google.protobuf.Timestamp timestamp = 4; }
message ClientMessage { oneof payload { CommandRequest command = 1; SubscriptionRequest subscription = 2; Ping ping = 3; } }
message ServerMessage { oneof payload { AgentEvent agent_event = 1; TaskEvent task_event = 2; CommandResponse command_response = 3; Pong pong = 4; } }
message CommandRequest { string command = 1; map<string, string> payload = 2; }
message SubscriptionRequest { string channel = 1; repeated string events = 2; }
message Ping { int64 timestamp = 1; }
message Pong { int64 timestamp = 1; }
message ListAgentsRequest { int32 page = 1; int32 limit = 2; string filter = 3; }
message ListAgentsResponse { repeated Agent agents = 1; int32 total = 2; int32 page = 3; }
message GetAgentRequest { string id = 1; }
message CreateAgentRequest { string name = 1; string description = 2; AgentConfig config = 3; }
message UpdateAgentRequest { string id = 1; string name = 2; AgentConfig config = 3; }
message DeleteAgentRequest { string id = 1; }
message DeployAgentRequest { string id = 1; string environment_id = 2; }
message GetAgentStatusRequest { string id = 1; }
message AgentStatus { string agent_id = 1; string status = 2; int32 active_tasks = 3; google.protobuf.Timestamp last_heartbeat = 4; }
message ListTasksRequest { int32 page = 1; int32 limit = 2; string agent_id = 3; string status = 4; }
message ListTasksResponse { repeated Task tasks = 1; int32 total = 2; }
message GetTaskRequest { string id = 1; }
message CreateTaskRequest { string agent_id = 1; string input = 2; map<string, string> parameters = 3; }
message CancelTaskRequest { string id = 1; }
message StreamTaskEventsRequest { string task_id = 1; }
message StreamAgentEventsRequest { string agent_id = 1; }
message SendCommandRequest { string agent_id = 1; string command = 2; map<string, string> payload = 3; }
message CommandResponse { bool success = 1; string message = 2; string result = 3; }
message InvokeToolRequest { string tool_id = 1; map<string, string> parameters = 2; string agent_id = 3; }
message InvokeToolResponse { bool success = 1; string result = 2; string error = 3; }
message ListToolsRequest { string agent_id = 1; }
message ListToolsResponse { repeated Tool tools = 1; }
message Tool { string id = 1; string name = 2; string description = 3; map<string, string> parameters_schema = 4; }
```

---

## 4. GraphQL Schema

```graphql
type Agent {
  id: ID! name: String! description: String status: AgentStatus!
  environment: Environment config: AgentConfig! labels: [String!]!
  tasks(limit: Int = 50, offset: Int = 0): [Task!]!
  createdAt: DateTime! updatedAt: DateTime!
}
type AgentConfig { model: String! temperature: Float maxTokens: Int tools: [String!]! parameters: JSON }
enum AgentStatus { CREATED DEPLOYING RUNNING PAUSED ERROR UNDEPLOYED }
type Task {
  id: ID! agent: Agent! status: TaskStatus! input: String! result: String
  progressPercent: Int! errorMessage: String createdAt: DateTime! completedAt: DateTime
}
enum TaskStatus { PENDING RUNNING COMPLETED FAILED CANCELLED }
type Environment { id: ID! name: String! type: String! agents: [Agent!]! status: EnvironmentStatus! }
enum EnvironmentStatus { ACTIVE INACTIVE MAINTENANCE }
type Tool { id: ID! name: String! description: String! parametersSchema: JSON }
scalar JSON scalar DateTime

type Query {
  agents(page: Int = 1, limit: Int = 50, filter: String): AgentConnection!
  agent(id: ID!): Agent
  tasks(page: Int = 1, limit: Int = 50, agentId: ID, status: TaskStatus): TaskConnection!
  task(id: ID!): Task
  environments: [Environment!]! environment(id: ID!): Environment
  tools(agentId: ID): [Tool!]!
}
type Mutation {
  createAgent(input: CreateAgentInput!): Agent!
  updateAgent(id: ID!, input: UpdateAgentInput!): Agent!
  deleteAgent(id: ID!): Boolean!
  deployAgent(id: ID!, environmentId: ID!): Agent!
  undeployAgent(id: ID!): Agent!
  createTask(input: CreateTaskInput!): Task!
  cancelTask(id: ID!): Task! retryTask(id: ID!): Task!
  invokeTool(toolId: ID!, parameters: JSON, agentId: ID): ToolResult!
  sendCommand(agentId: ID!, command: String!, payload: JSON): CommandResult!
}
type Subscription {
  agentStatusChanged(agentId: ID): Agent!
  taskProgress(taskId: ID!): Task!
  taskCompleted(agentId: ID): Task!
  agentLog(agentId: ID!): LogEntry!
}
input CreateAgentInput { name: String! description: String config: AgentConfigInput! labels: [String!] }
input UpdateAgentInput { name: String description: String config: AgentConfigInput labels: [String!] }
input AgentConfigInput { model: String! temperature: Float maxTokens: Int tools: [String!]! parameters: JSON }
input CreateTaskInput { agentId: ID! input: String! parameters: JSON }
type AgentConnection { edges: [AgentEdge!]! pageInfo: PageInfo! totalCount: Int! }
type AgentEdge { node: Agent! cursor: String! }
type TaskConnection { edges: [TaskEdge!]! pageInfo: PageInfo! totalCount: Int! }
type TaskEdge { node: Task! cursor: String! }
type PageInfo { hasNextPage: Boolean! hasPreviousPage: Boolean! startCursor: String endCursor: String }
type ToolResult { success: Boolean! result: String error: String }
type CommandResult { success: Boolean! message: String! result: String }
type LogEntry { agentId: ID! level: LogLevel! message: String! timestamp: DateTime! }
enum LogLevel { DEBUG INFO WARN ERROR }
```

---

## 5. Webhooks

### Management Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/webhooks` | List webhooks |
| POST | `/webhooks` | Create webhook |
| GET | `/webhooks/{id}` | Get details |
| PATCH | `/webhooks/{id}` | Update |
| DELETE | `/webhooks/{id}` | Delete |
| POST | `/webhooks/{id}/test` | Send test event |
| GET | `/webhooks/{id}/deliveries` | List deliveries |
| POST | `/webhooks/{id}/retry/{delivery_id}` | Retry failed |

### Configuration
```json
{ "id": "wh-123", "url": "https://example.com/hook", "secret": "whsec_...",
  "events": ["agent.status_change", "task.completed"], "agent_id": "agent-456", "active": true }
```

### Event Payload
```json
{ "id": "evt_abc123", "type": "task.completed", "timestamp": "2026-10-02T10:30:00Z",
  "data": { "task_id": "...", "agent_id": "...", "status": "completed", "result": "...", "duration_ms": 12500 } }
```

### Events
`agent.status_change` · `agent.deployed` · `agent.undeployed` · `agent.error` · `task.created` · `task.progress` · `task.completed` · `task.failed` · `task.cancelled`

### Delivery Headers
```
X-ApexOS-Event: task.completed
X-ApexOS-Delivery: evt_abc123
X-ApexOS-Signature: sha256=<hmac_sha256>
X-ApexOS-Timestamp: 1696240200
```

**Signature:** `HMAC_SHA256(secret, "{timestamp}.{body}")` → `sha256=<hex>`

### Delivery Behavior
- **Timeout:** 10s · **Retries:** 5 with exponential backoff (1s→2s→4s→8s→16s)
- **Success:** HTTP 2xx · **Dead letter:** stored after 5 failures for manual retry
- **Idempotency:** unique delivery ID; receivers should deduplicate
