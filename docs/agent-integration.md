# APEX-OS Business Platform — AI Agent Integration Framework

> **Version:** 1.0.0  
> **Last Updated:** 2026-10-01  
> **Status:** Draft  
> **Owner:** APEX-OS Platform Team

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Agent Orchestration](#3-agent-orchestration)
4. [Agent Communication](#4-agent-communication)
5. [Agent Monitoring](#5-agent-monitoring)
6. [Agent Security](#6-agent-security)
7. [Agent Evaluation](#7-agent-evaluation)
8. [Deployment Topology](#8-deployment-topology)
9. [Operational Runbooks](#9-operational-runbooks)
10. [Appendices](#10-appendices)

---

## 1. Overview

### 1.1 Purpose

This document defines the comprehensive framework for integrating AI agents into the APEX-OS Business Platform. It covers the full agent lifecycle: orchestration, communication, monitoring, security, and evaluation. The framework is designed to operate across the multi-cloud infrastructure (AWS, Azure, GCP) and Kubernetes clusters that constitute the APEX-OS platform.

### 1.2 Scope

| Domain | In Scope | Out of Scope |
|--------|----------|--------------|
| Orchestration | Multi-agent coordination, task decomposition, DAG scheduling, human-in-the-loop | Model training, fine-tuning |
| Communication | Inter-agent messaging, shared state, event streaming, tool-calling protocols | End-user chat interfaces |
| Monitoring | Agent health, performance tracing, cost tracking, anomaly detection | Infrastructure-only monitoring (covered by existing Prometheus/Grafana stack) |
| Security | Agent identity, authorization, sandboxing, prompt injection defense, audit logging | Network-level security (covered by existing WAF/Shield/GuardDuty) |
| Evaluation | Benchmark suites, regression testing, quality gates, A/B testing | Model benchmarking (MMLU, etc.) |

### 1.3 Design Principles

1. **Cloud-Agnostic** — Agents deploy identically on AWS EKS, Azure AKS, and GCP GKE.
2. **Zero-Trust** — Every agent authenticates, authorizes, and encrypts by default.
3. **Observable by Default** — Every agent emits metrics, logs, and traces without extra configuration.
4. **Human-in-the-Loop** — Critical decisions require configurable human approval gates.
5. **Graceful Degradation** — Agent failures cascade minimally; the platform continues operating.
6. **Cost-Aware** — Token usage, compute, and API costs are tracked per agent, per task, per tenant.

### 1.4 Glossary

| Term | Definition |
|------|-----------|
| **Agent** | An autonomous software entity that perceives its environment, reasons about goals, and takes actions via tools. |
| **Orchestrator** | A control-plane component that decomposes tasks, assigns them to agents, and manages dependencies. |
| **Tool** | A callable function exposed to an agent (API endpoint, CLI command, database query). |
| **Skill** | A packaged set of tools, prompts, and workflows that extend an agent's capability. |
| **Run** | A single execution of an agent from task receipt to completion. |
| **Trace** | A complete record of an agent's reasoning steps, tool calls, and outputs. |
| **HITL** | Human-in-the-loop; a checkpoint requiring human approval before proceeding. |

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        APEX-OS Agent Platform                        │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Agent       │  │   Agent       │  │   Agent       │  ...        │
│  │   Gateway     │  │   Gateway     │  │   Gateway     │              │
│  │  (Ingress)    │  │  (Ingress)    │  │  (Ingress)    │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                  │                       │
│  ┌──────▼──────────────────▼──────────────────▼───────┐              │
│  │              Agent Orchestrator Service             │              │
│  │  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌───────┐ │              │
│  │  │ Task    │ │ Agent    │ │ Workflow  │ │ HITL  │ │              │
│  │  │ Queue   │ │ Registry │ │ Engine    │ │ Manager│ │              │
│  │  └─────────┘ └──────────┘ └───────────┘ └───────┘ │              │
│  └──────┬──────────────────┬──────────────────┬───────┘              │
│         │                  │                  │                       │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐              │
│  │  Agent       │  │  Agent       │  │  Agent       │              │
│  │  Runtime     │  │  Runtime     │  │  Runtime     │              │
│  │  (Sandbox)   │  │  (Sandbox)   │  │  (Sandbox)   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                  │                       │
│  ┌──────▼──────────────────▼──────────────────▼───────┐              │
│  │              Shared Services Layer                  │              │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐ │              │
│  │  │ Message│ │ State  │ │ Secret │ │  Tool        │ │              │
│  │  │ Bus    │ │ Store  │ │ Manager│ │  Registry    │ │              │
│  │  └────────┘ └────────┘ └────────┘ └──────────────┘ │              │
│  └────────────────────────────────────────────────────┘              │
│                                                                     │
│  ┌────────────────────────────────────────────────────┐              │
│  │           Observability & Evaluation               │              │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │              │
│  │  │ Metrics  │ │ Logging  │ │  Evaluation       │  │              │
│  │  │ (Prom.)  │ │ (Loki)   │ │  Engine           │  │              │
│  │  └──────────┘ └──────────┘ └───────────────────┘  │              │
│  └────────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Inventory

| # | Component | Technology | Purpose |
|---|-----------|-----------|---------|
| 1 | Agent Gateway | Envoy + custom auth filter | TLS termination, rate limiting, JWT validation |
| 2 | Orchestrator Service | Go (Gin/Echo) | Task decomposition, agent scheduling, DAG execution |
| 3 | Task Queue | NATS JetStream / Redis Streams | Durable task queue with priority and delay |
| 4 | Agent Registry | PostgreSQL + Redis | Agent metadata, capabilities, health status |
| 5 | Workflow Engine | Temporal.io | Durable execution, saga patterns, retry logic |
| 6 | HITL Manager | Go + WebSocket | Human approval workflow, notification routing |
| 7 | Agent Runtime | Python 3.12 + gRPC | Sandboxed agent execution environment |
| 8 | Message Bus | NATS JetStream | Inter-agent pub/sub and request/reply |
| 9 | State Store | Redis Cluster + PostgreSQL | Shared state, session data, checkpointing |
| 10 | Secret Manager | HashiCorp Vault | API keys, credentials, certificates |
| 11 | Tool Registry | gRPC + OpenAPI | Tool discovery, schema validation, versioning |
| 12 | Metrics Pipeline | Prometheus + OpenTelemetry | Agent performance and health metrics |
| 13 | Log Aggregation | Loki + Fluent Bit | Centralized agent logging |
| 14 | Trace Collector | Tempo + OpenTelemetry | Distributed tracing across agent calls |
| 15 | Evaluation Engine | Python + pytest | Benchmark suites, regression tests, scoring |
| 16 | Cost Tracker | PostgreSQL + custom exporter | Token usage, compute cost, API call tracking |
| 17 | Policy Engine | OPA (Open Policy Agent) | Authorization, compliance, guardrails |
| 18 | Audit Log | PostgreSQL + S3 | Immutable audit trail for all agent actions |

### 2.3 Infrastructure Mapping

The agent platform deploys on top of existing APEX-OS infrastructure:

| APEX-OS Resource | Agent Platform Use |
|-----------------|-------------------|
| AWS EKS / Azure AKS / GCP GKE | Agent Runtime, Orchestrator, Gateway |
| AWS RDS (PostgreSQL) | Agent Registry, State Store, Audit Log |
| AWS S3 / Azure Blob / GCS | Trace storage, evaluation datasets, model artifacts |
| Istio Service Mesh | mTLS between agent services, traffic management |
| cert-manager | Automatic TLS certificates for agent endpoints |
| Prometheus + Grafana | Agent metrics and dashboards |
| Loki | Agent log aggregation |
| Tempo | Agent distributed tracing |
| Alertmanager | Agent alert routing |
| VPC Flow Logs | Network-level agent traffic audit |
| AWS WAF | Agent API protection |
| AWS GuardDuty | Threat detection for agent infrastructure |
| AWS Security Hub | Compliance posture for agent workloads |

---

## 3. Agent Orchestration

### 3.1 Orchestration Model

APEX-OS uses a **hierarchical orchestration** model with three tiers:

```
┌─────────────────────────────────────────┐
│          Meta-Orchestrator              │
│  (Cross-domain task decomposition)      │
│  - Receives high-level business goals   │
│  - Decomposes into domain sub-tasks     │
│  - Assigns to Domain Orchestrators      │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐
│Domain  │ │Domain  │ │Domain  │
│Orch. A │ │Orch. B │ │Orch. C │
│(Infra) │ │(Data)  │ │(Apps)  │
└───┬────┘ └───┬────┘ └───┬────┘
    │          │          │
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│Worker  │ │Worker  │ │Worker  │
│Agents  │ │Agents  │ │Agents  │
└────────┘ └────────┘ └────────┘
```

- **Meta-Orchestrator**: Receives business objectives (e.g., "Deploy a new microservice with monitoring"). Decomposes into domain-specific sub-tasks and coordinates cross-domain dependencies.
- **Domain Orchestrators**: Manage agents within a specific domain (infrastructure, data, applications). Handle intra-domain task DAGs.
- **Worker Agents**: Execute atomic tasks. Each agent has a specific role, tool set, and skill set.

### 3.2 Task Decomposition

#### 3.2.1 Task Representation

Tasks are represented as DAGs (Directed Acyclic Graphs) using a YAML-based DSL:

```yaml
apiVersion: agents.apex-os.io/v1
kind: Workflow
metadata:
  name: deploy-microservice
  namespace: apex-os-core
spec:
  description: "Deploy a new microservice with full observability"
  timeout: 30m
  retryPolicy:
    maxRetries: 3
    backoff: exponential
    initialInterval: 5s
  tasks:
    - id: validate-input
      name: "Validate Input"
      agent: input-validator
      tools: [schema-validator, policy-checker]
      inputs:
        service_name: "{{input.service_name}}"
        docker_image: "{{input.docker_image}}"
      outputs: [validation_result]
      onFailure: reject

    - id: provision-namespace
      name: "Provision K8s Namespace"
      agent: infra-agent
      tools: [kubectl, helm]
      dependsOn: [validate-input]
      inputs:
        namespace: "{{input.service_name}}"
        labels: {team: "{{input.team}}", env: "{{input.environment}}"}
      outputs: [namespace_status]
      onFailure: rollback

    - id: deploy-service
      name: "Deploy Microservice"
      agent: deploy-agent
      tools: [kubectl, helm, istioctl]
      dependsOn: [provision-namespace]
      inputs:
        chart: "{{input.helm_chart}}"
        values: "{{input.helm_values}}"
        namespace: "{{tasks.provision-namespace.outputs.namespace}}"
      outputs: [deployment_status, service_endpoint]
      onFailure: rollback

    - id: configure-monitoring
      name: "Configure Monitoring"
      agent: monitoring-agent
      tools: [prometheus-api, grafana-api, alertmanager-api]
      dependsOn: [deploy-service]
      inputs:
        service: "{{tasks.deploy-service.outputs.service_endpoint}}"
        namespace: "{{tasks.provision-namespace.outputs.namespace}}"
        slo_targets:
          availability: 99.9
          latency_p99: 500ms
      outputs: [dashboard_url, alert_rules]
      onFailure: warn

    - id: configure-security
      name: "Configure Security Policies"
      agent: security-agent
      tools: [opa, vault, cert-manager]
      dependsOn: [deploy-service]
      inputs:
        namespace: "{{tasks.provision-namespace.outputs.namespace}}"
        service: "{{tasks.deploy-service.outputs.service_endpoint}}"
        policies: [network-policy, pod-security, rbac]
      outputs: [policy_status]
      onFailure: rollback

    - id: notify-stakeholders
      name: "Notify Stakeholders"
      agent: notification-agent
      tools: [slack, email, pagerduty]
      dependsOn: [configure-monitoring, configure-security]
      inputs:
        channel: "#deployments"
        message: "Service {{input.service_name}} deployed successfully"
        endpoint: "{{tasks.deploy-service.outputs.service_endpoint}}"
      onFailure: warn

  rollback:
    strategy: reverse-order
    tasks: [deploy-service, provision-namespace]
```

#### 3.2.2 Decomposition Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **Static DAG** | Pre-defined task graph | Well-known, repeatable workflows |
| **Dynamic DAG** | Tasks generated at runtime based on inputs | Variable infrastructure, conditional paths |
| **LLM-Planned** | LLM generates task decomposition | Novel tasks, exploratory operations |
| **Hybrid** | Static skeleton with dynamic leaf tasks | Mostly predictable with variable details |

### 3.3 Scheduling

#### 3.3.1 Priority Classes

| Priority | Class | Preemption | Use Case |
|----------|-------|-----------|----------|
| 0 | `critical` | Yes | Incident response, security remediation |
| 1 | `high` | Yes | Production deployments, SLA-critical tasks |
| 2 | `normal` | No | Standard operations, routine maintenance |
| 3 | `low` | No | Background optimization, reporting |
| 4 | `best-effort` | No | Evaluation runs, non-urgent analytics |

#### 3.3.2 Scheduling Constraints

```yaml
scheduling:
  # Affinity: prefer nodes with GPU
  nodeAffinity:
    requiredDuringScheduling:
      - matchExpressions:
          - key: node.kubernetes.io/instance-type
            operator: In
            values: ["p3.2xlarge", "p3.8xlarge"]
  
  # Anti-affinity: spread across availability zones
  podAntiAffinity:
    preferredDuringScheduling:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: agent-runtime
          topologyKey: topology.kubernetes.io/zone
  
  # Resource guarantees
  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2000m"
      memory: "4Gi"
  
  # Tolerations for dedicated agent nodes
  tolerations:
    - key: "dedicated"
      operator: "Equal"
      value: "agents"
      effect: "NoSchedule"
```

### 3.4 Human-in-the-Loop (HITL)

#### 3.4.1 Checkpoint Types

| Checkpoint | Trigger | Timeout | Escalation |
|-----------|---------|---------|------------|
| **Approval** | Before destructive action | 30 min | Escalate to on-call |
| **Review** | After code generation | 2 hours | Auto-approve with warning |
| **Confirmation** | Before production deploy | 15 min | Block and alert |
| **Override** | When agent confidence < threshold | 10 min | Escalate to senior engineer |

#### 3.4.2 HITL Configuration

```yaml
hitl:
  enabled: true
  defaultTimeout: 30m
  defaultEscalation: on-call-engineer
  
  rules:
    - name: "production-deploy-approval"
      match:
        task: deploy-service
        environment: prod
      action: require-approval
      approvers: [team-lead, sre-oncall]
      minApprovers: 1
      timeout: 15m
      
    - name: "destructive-action-guard"
      match:
        tool: kubectl
        argsContains: ["delete", "apply --prune"]
      action: require-approval
      approvers: [sre-oncall]
      minApprovers: 2
      timeout: 10m
      
    - name: "low-confidence-escalation"
      match:
        agentConfidence: "< 0.7"
      action: require-review
      approvers: [agent-owner]
      timeout: 30m
```

### 3.5 Multi-Agent Coordination Patterns

#### 3.5.1 Patterns

| Pattern | Description | Implementation |
|---------|-------------|---------------|
| **Pipeline** | Sequential task execution | Temporal workflow with activities |
| **Fan-Out/Fan-In** | Parallel execution with aggregation | NATS scatter-gather |
| **Supervisor** | One agent monitors and restarts others | Kubernetes-style supervisor loop |
| **Blackboard** | Agents read/write shared state | Redis-backed shared state store |
| **Auction** | Agents bid for tasks | Priority queue with capability matching |
| **Consensus** | Agents vote on decisions | Raft-based consensus for critical decisions |

#### 3.5.2 Conflict Resolution

When multiple agents attempt to modify the same resource:

1. **Optimistic Locking**: Each resource has a version number. Agents must provide the expected version.
2. **Lease-Based Locking**: Agents acquire time-bound leases before modification.
3. **Merge Strategies**: For non-conflicting changes, automatic merge (e.g., CRDTs for configuration).
4. **Arbitration**: The Orchestrator acts as final arbiter for unresolvable conflicts.

---

## 4. Agent Communication

### 4.1 Communication Model

APEX-OS uses a **hybrid communication model** combining synchronous and asynchronous patterns:

```
┌─────────────────────────────────────────────────────────┐
│                   Communication Matrix                    │
│                                                         │
│  ┌─────────────┐    Sync (gRPC)    ┌─────────────┐     │
│  │   Agent A   │◄─────────────────►│   Agent B   │     │
│  └──────┬──────┘                    └──────┬──────┘     │
│         │                                  │            │
│         │  Async (NATS JetStream)           │            │
│         │  ┌──────────────────────────┐    │            │
│         └──┤      Message Bus         ├────┘            │
│            │  - Pub/Sub               │                 │
│            │  - Request/Reply         │                 │
│            │  - Event Streaming       │                 │
│            └──────────────────────────┘                 │
│                         │                               │
│            ┌────────────▼────────────┐                  │
│            │     State Store         │                  │
│            │  - Shared blackboard    │                  │
│            │  - Session state        │                  │
│            │  - Checkpoint data      │                  │
│            └─────────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Message Protocol

#### 4.2.1 Message Envelope

All inter-agent messages use a standardized envelope:

```protobuf
syntax = "proto3";

package apexos.agents.v1;

import "google/protobuf/timestamp.proto";
import "google/protobuf/struct.proto";

message AgentMessage {
  // Unique message identifier
  string message_id = 1;
  
  // Correlation ID for request/reply patterns
  string correlation_id = 2;
  
  // Sender and recipient
  string sender_id = 3;
  string recipient_id = 4;  // Empty for broadcast
  
  // Message type
  MessageType type = 5;
  
  // Payload
  google.protobuf.Struct payload = 6;
  
  // Metadata
  map<string, string> metadata = 7;
  
  // Timestamps
  google.protobuf.Timestamp created_at = 8;
  google.protobuf.Timestamp expires_at = 9;
  
  // Priority (0-4, matching scheduling priorities)
  int32 priority = 10;
  
  // TTL for the message
  int32 ttl_seconds = 11;
  
  // Trace context
  string trace_id = 12;
  string span_id = 13;
}

enum MessageType {
  MESSAGE_TYPE_UNSPECIFIED = 0;
  TASK_REQUEST = 1;       // Orchestrator → Agent: execute this task
  TASK_RESPONSE = 2;      // Agent → Orchestrator: task result
  TOOL_CALL = 3;          // Agent → Tool: invoke this tool
  TOOL_RESULT = 4;        // Tool → Agent: tool output
  EVENT = 5;              // Any → Any: broadcast event
  HEARTBEAT = 6;          // Agent → Orchestrator: health signal
  STATE_UPDATE = 7;       // Agent → State Store: update shared state
  STATE_QUERY = 8;        // Agent → State Store: read shared state
  HITL_REQUEST = 9;       // Orchestrator → Human: approval needed
  HITL_RESPONSE = 10;     // Human → Orchestrator: approval decision
  ERROR = 11;             // Any → Any: error notification
}
```

#### 4.2.2 Subject Naming Convention

NATS subjects follow a hierarchical naming convention:

```
apexos.{environment}.{domain}.{agent-id}.{message-type}

Examples:
  apexos.prod.infra.deploy-agent.task-request
  apexos.prod.data.analytics-agent.event
  apexos.staging.apps.notification-agent.heartbeat
```

### 4.3 Shared State Management

#### 4.3.1 State Categories

| Category | Store | TTL | Consistency |
|----------|-------|-----|-------------|
| **Session State** | Redis | Session duration | Eventual |
| **Task State** | PostgreSQL | Task lifetime | Strong |
| **Blackboard** | Redis + PostgreSQL | Workflow duration | Eventual |
| **Checkpoint** | S3 + PostgreSQL | Indefinite | Strong |
| **Cache** | Redis | Configurable | Eventual |

#### 4.3.2 State Schema

```json
{
  "workflow_id": "wf-12345",
  "task_id": "task-67890",
  "agent_id": "deploy-agent-01",
  "state_type": "task_checkpoint",
  "version": 42,
  "data": {
    "deployment_status": "in_progress",
    "helm_release": "my-service-v2",
    "replicas_ready": 3,
    "last_error": null
  },
  "created_at": "2026-10-01T10:00:00Z",
  "updated_at": "2026-10-01T10:05:30Z",
  "ttl": "3600s"
}
```

### 4.4 Tool Calling Protocol

#### 4.4.1 Tool Registration

Tools are registered with the Tool Registry using OpenAPI 3.0 specifications:

```yaml
apiVersion: agents.apex-os.io/v1
kind: Tool
metadata:
  name: kubectl-apply
  namespace: apex-os-core
  labels:
    domain: infrastructure
    agent: infra-agent
spec:
  version: "1.2.0"
  description: "Apply Kubernetes manifests"
  endpoint:
    type: grpc
    service: k8s-tool-service
    method: ApplyManifest
  parameters:
    type: object
    required: [manifest, namespace]
    properties:
      manifest:
        type: string
        description: "YAML/JSON manifest to apply"
      namespace:
        type: string
        description: "Target namespace"
      dryRun:
        type: boolean
        default: false
      timeout:
        type: string
        default: "30s"
  response:
    type: object
    properties:
      applied:
        type: boolean
      resources:
        type: array
        items:
          type: object
          properties:
            kind: { type: string }
            name: { type: string }
            namespace: { type: string }
            status: { type: string }
  rbac:
    requiredRoles: [infra-operator]
    resourceTypes: [ConfigMap, Deployment, Service, Ingress]
  rateLimit:
    requestsPerMinute: 60
    burst: 10
  timeout: 60s
  retryPolicy:
    maxRetries: 2
    retryOn: [timeout, transient-error]
```

#### 4.4.2 Tool Discovery

Agents discover tools at startup and on-demand:

```python
# Agent-side tool discovery
class ToolDiscovery:
    def __init__(self, registry_endpoint: str):
        self.registry = ToolRegistryClient(registry_endpoint)
    
    async def discover_tools(
        self, 
        capability: str | None = None,
        domain: str | None = None
    ) -> list[Tool]:
        """Discover available tools matching criteria."""
        query = ToolQuery(capability=capability, domain=domain)
        return await self.registry.list_tools(query)
    
    async def call_tool(
        self, 
        tool_name: str, 
        arguments: dict,
        timeout: timedelta = timedelta(seconds=30)
    ) -> ToolResult:
        """Invoke a tool with automatic retry and circuit breaking."""
        tool = await self.registry.get_tool(tool_name)
        return await self._execute_with_resilience(tool, arguments, timeout)
```

### 4.5 Event Streaming

#### 4.5.1 Event Types

| Event Type | Producer | Consumers | Retention |
|-----------|----------|-----------|-----------|
| `task.created` | Orchestrator | All agents in workflow | 24h |
| `task.started` | Agent | Orchestrator, Monitoring | 24h |
| `task.completed` | Agent | Orchestrator, Monitoring, Evaluation | 7d |
| `task.failed` | Agent | Orchestrator, Monitoring, Alerting | 7d |
| `tool.called` | Agent | Monitoring, Audit | 30d |
| `state.updated` | Agent | Orchestrator, other agents | 1h |
| `hitl.requested` | Orchestrator | HITL Manager, UI | 24h |
| `agent.registered` | Agent | Orchestrator, Registry | 24h |
| `agent.heartbeat` | Agent | Orchestrator, Monitoring | 1h |

#### 4.5.2 Event Schema (CloudEvents)

```json
{
  "specversion": "1.0",
  "id": "evt-20261001-001",
  "source": "orchestrator.prod.apex-os",
  "type": "apexos.agents.task.completed",
  "subject": "wf-12345/task-67890",
  "time": "2026-10-01T10:05:30Z",
  "datacontenttype": "application/json",
  "data": {
    "workflow_id": "wf-12345",
    "task_id": "task-67890",
    "agent_id": "deploy-agent-01",
    "status": "success",
    "duration_ms": 45000,
    "output": {
      "service_endpoint": "https://my-service.prod.apex-os.io"
    },
    "metrics": {
      "tokens_used": 1500,
      "tool_calls": 5,
      "cost_usd": 0.03
    }
  },
  "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
}
```

---

## 5. Agent Monitoring

### 5.1 Monitoring Stack

The agent monitoring layer extends the existing APEX-OS observability infrastructure:

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Observability                       │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Agent      │  │  Agent      │  │  Agent      │         │
│  │  Runtime    │  │  Runtime    │  │  Runtime    │         │
│  │  (OTel SDK) │  │  (OTel SDK) │  │  (OTel SDK) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│  ┌──────▼────────────────▼────────────────▼──────┐         │
│  │         OpenTelemetry Collector               │         │
│  │  - Batch processing                           │         │
│  │  - Attribute enrichment                       │         │
│  │  - Tail-based sampling                        │         │
│  └──────┬────────────────┬────────────────┬──────┘         │
│         │                │                │                 │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐         │
│  │ Prometheus  │  │    Loki     │  │    Tempo    │         │
│  │ (Metrics)   │  │  (Logs)     │  │  (Traces)   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│  ┌──────▼────────────────▼────────────────▼──────┐         │
│  │              Grafana Dashboards               │         │
│  │  - Agent Health Overview                      │         │
│  │  - Workflow Progress                          │         │
│  │  - Cost Analytics                             │         │
│  │  - SLO Compliance                             │         │
│  └──────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Metrics

#### 5.2.1 Agent-Level Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `agent_runs_total` | Counter | agent_id, status, workflow_id | Total agent runs by status |
| `agent_run_duration_seconds` | Histogram | agent_id, task_type | Agent execution duration |
| `agent_tool_calls_total` | Counter | agent_id, tool_name, status | Tool invocations by tool and status |
| `agent_tool_duration_seconds` | Histogram | agent_id, tool_name | Tool call latency |
| `agent_tokens_used` | Counter | agent_id, model, token_type | Token consumption (input/output) |
| `agent_cost_usd` | Counter | agent_id, model, task_id | Estimated cost per agent |
| `agent_queue_wait_seconds` | Histogram | agent_id, priority | Time spent waiting in queue |
| `agent_errors_total` | Counter | agent_id, error_type, tool_name | Error count by type |
| `agent_retries_total` | Counter | agent_id, task_id | Retry count |
| `agent_confidence_score` | Gauge | agent_id, task_id | Self-reported confidence |
| `agent_memory_usage_bytes` | Gauge | agent_id | Memory consumption |
| `agent_cpu_usage_seconds` | Counter | agent_id | CPU time consumed |
| `agent_active_sessions` | Gauge | agent_id | Currently active sessions |
| `agent_last_heartbeat_seconds` | Gauge | agent_id | Time since last heartbeat |

#### 5.2.2 Workflow-Level Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `workflow_runs_total` | Counter | workflow_name, status | Total workflow executions |
| `workflow_duration_seconds` | Histogram | workflow_name | End-to-end workflow duration |
| `workflow_task_duration_seconds` | Histogram | workflow_name, task_name | Per-task duration |
| `workflow_tasks_total` | Counter | workflow_name, status | Task count by status |
| `workflow_rollback_total` | Counter | workflow_name, reason | Rollback frequency |
| `workflow_hitl_wait_seconds` | Histogram | workflow_name, checkpoint_type | HITL wait time |
| `workflow_cost_usd` | Counter | workflow_name | Total workflow cost |

#### 5.2.3 Platform-Level Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `platform_agents_registered` | Gauge | domain, version | Registered agent count |
| `platform_agents_healthy` | Gauge | domain | Healthy agent count |
| `platform_queue_depth` | Gauge | priority, domain | Pending task count |
| `platform_tool_errors_total` | Counter | tool_name, error_type | Tool-level errors |
| `platform_api_requests_total` | Counter | endpoint, method, status | Gateway API metrics |
| `platform_api_latency_seconds` | Histogram | endpoint, method | Gateway API latency |

### 5.3 Logging

#### 5.3.1 Log Levels and Content

| Level | Content | Retention |
|-------|---------|-----------|
| `DEBUG` | Tool call parameters, intermediate reasoning steps | 24h |
| `INFO` | Task start/completion, state transitions, agent registration | 7d |
| `WARN` | Retries, degraded performance, low confidence scores | 30d |
| `ERROR` | Task failures, tool errors, policy violations | 90d |
| `AUDIT` | Security-relevant events (auth, authorization, data access) | 1y |

#### 5.3.2 Structured Log Format

```json
{
  "timestamp": "2026-10-01T10:05:30.123Z",
  "level": "INFO",
  "agent_id": "deploy-agent-01",
  "workflow_id": "wf-12345",
  "task_id": "task-67890",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "message": "Task completed successfully",
  "event": "task.completed",
  "duration_ms": 45000,
  "tool_calls": 5,
  "tokens_used": 1500,
  "cost_usd": 0.03,
  "environment": "prod",
  "namespace": "apex-os-core"
}
```

### 5.4 Tracing

#### 5.4.1 Trace Context

Every agent run produces a distributed trace with the following span hierarchy:

```
Workflow Span (root)
├── Task Span: validate-input
│   └── Tool Span: schema-validator
├── Task Span: provision-namespace
│   ├── Tool Span: kubectl (create namespace)
│   └── Tool Span: kubectl (apply labels)
├── Task Span: deploy-service
│   ├── Tool Span: helm (install)
│   ├── Tool Span: kubectl (wait for rollout)
│   └── Tool Span: istioctl (configure routing)
├── Task Span: configure-monitoring
│   ├── Tool Span: prometheus-api (create rules)
│   └── Tool Span: grafana-api (create dashboard)
└── Task Span: notify-stakeholders
    └── Tool Span: slack (send message)
```

#### 5.4.2 Span Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent.id` | string | Agent identifier |
| `agent.version` | string | Agent version |
| `agent.model` | string | LLM model used |
| `task.id` | string | Task identifier |
| `task.type` | string | Task type |
| `tool.name` | string | Tool name |
| `tool.version` | string | Tool version |
| `workflow.id` | string | Workflow identifier |
| `workflow.name` | string | Workflow name |
| `error` | boolean | Whether the span represents an error |
| `error.type` | string | Error classification |
| `tokens.input` | int | Input tokens consumed |
| `tokens.output` | int | Output tokens consumed |
| `cost.usd` | float | Estimated cost |

### 5.5 Alerting

#### 5.5.1 Alert Rules

```yaml
groups:
  - name: agent-health
    rules:
      - alert: AgentDown
        expr: up{job="agent-runtime"} == 0
        for: 2m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Agent {{ $labels.agent_id }} is down"
          description: "Agent {{ $labels.agent_id }} in {{ $labels.namespace }} has been unreachable for more than 2 minutes."
          
      - alert: AgentHighErrorRate
        expr: |
          rate(agent_errors_total[5m]) 
          / 
          rate(agent_runs_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High error rate for agent {{ $labels.agent_id }}"
          description: "Agent {{ $labels.agent_id }} has an error rate above 10% over the last 5 minutes."
          
      - alert: AgentHighLatency
        expr: |
          histogram_quantile(0.99, 
            rate(agent_run_duration_seconds_bucket[5m])
          ) > 300
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Agent {{ $labels.agent_id }} P99 latency > 5 minutes"
          
      - alert: WorkflowStuck
        expr: |
          time() - workflow_last_activity_timestamp > 1800
          and
          workflow_status == "running"
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Workflow {{ $labels.workflow_id }} appears stuck"
          
      - alert: AgentCostSpike
        expr: |
          rate(agent_cost_usd[1h]) 
          > 
          2 * avg_over_time(rate(agent_cost_usd[1h])[24h:1h])
        for: 15m
        labels:
          severity: warning
          team: finance
        annotations:
          summary: "Cost spike detected for agent {{ $labels.agent_id }}"
          
      - alert: HITLQueueBacklog
        expr: hitl_pending_requests > 10
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "HITL approval queue backlog"
          
      - alert: AgentTokenBudgetExceeded
        expr: |
          agent_tokens_used{period="daily"} 
          > 
          agent_token_budget_daily
        for: 1m
        labels:
          severity: warning
          team: finance
        annotations:
          summary: "Agent {{ $labels.agent_id }} exceeded daily token budget"
```

### 5.6 Dashboards

#### 5.6.1 Dashboard Inventory

| Dashboard | Purpose | Key Panels |
|-----------|---------|------------|
| **Agent Health Overview** | Fleet-wide agent status | Agent status grid, error rates, latency heatmaps |
| **Workflow Monitor** | Real-time workflow progress | Active workflows, task DAG visualization, bottleneck identification |
| **Cost Analytics** | Token and compute cost tracking | Cost by agent, by workflow, by model; trend lines; budget gauges |
| **Tool Performance** | Tool reliability and latency | Tool success rates, latency percentiles, error breakdown |
| **HITL Queue** | Human approval backlog | Pending requests, wait times, approver workload |
| **SLO Compliance** | Agent SLO tracking | Availability, latency, and error budget burn-down |
| **Model Usage** | LLM model utilization | Requests by model, token consumption, cost per model |

---

## 6. Agent Security

### 6.1 Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Security Layers                         │
│                                                                 │
│  Layer 7: Application    ┌─────────────────────────────────┐   │
│  ─────────────────────── │ Prompt Injection Defense         │   │
│                          │ Output Filtering                 │   │
│                          │ Content Policy Enforcement       │   │
│                          └─────────────────────────────────┘   │
│                                                                 │
│  Layer 6: Agent          ┌─────────────────────────────────┐   │
│  ─────────────────────── │ Agent Identity (SPIFFE/SPIRE)    │   │
│                          │ Capability-Based Access Control │   │
│                          │ Sandbox Isolation                │   │
│                          └─────────────────────────────────┘   │
│                                                                 │
│  Layer 5: Tool           ┌─────────────────────────────────┐   │
│  ─────────────────────── │ Tool Authorization (OPA)        │   │
│                          │ Rate Limiting                   │   │
│                          │ Input Validation                │   │
│                          └─────────────────────────────────┘   │
│                                                                 │
│  Layer 4: Communication ┌─────────────────────────────────┐   │
│  ─────────────────────── │ mTLS (Istio)                    │   │
│                          │ Message Encryption              │   │
│                          │ API Authentication (JWT/OAuth2)  │   │
│                          └─────────────────────────────────┘   │
│                                                                 │
│  Layer 3: Infrastructure┌─────────────────────────────────┐   │
│  ─────────────────────── │ Network Policies                │   │
│                          │ Pod Security Standards          │   │
│                          │ Secrets Encryption (Vault)      │   │
│                          └─────────────────────────────────┘   │
│                                                                 │
│  Layer 2: Audit          ┌─────────────────────────────────┐   │
│  ─────────────────────── │ Immutable Audit Log             │   │
│                          │ Anomaly Detection               │   │
│                          │ Compliance Reporting            │   │
│                          └─────────────────────────────────┘   │
│                                                                 │
│  Layer 1: Governance     ┌─────────────────────────────────┐   │
│  ─────────────────────── │ Policy as Code (OPA/Rego)       │   │
│                          │ Approval Workflows              │   │
│                          │ Segregation of Duties           │   │
│                          └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Agent Identity and Authentication

#### 6.2.1 Identity Model

Each agent has a unique, cryptographically verifiable identity:

```yaml
# Agent identity document
apiVersion: agents.apex-os.io/v1
kind: AgentIdentity
metadata:
  name: deploy-agent-01
  namespace: apex-os-core
spec:
  # SPIFFE ID for workload identity
  spiffeId: spiffe://apex-os.io/ns/apex-os-core/sa/deploy-agent
  
  # Agent metadata
  agentType: worker
  domain: infrastructure
  version: "2.1.0"
  capabilities:
    - kubernetes-deploy
    - helm-management
    - istio-configuration
  
  # Authentication
  authentication:
    method: mtls
    certificate:
      issuer: apex-os-ca
      ttl: 24h
      autoRotate: true
  
  # Authorization
  authorization:
    maxTokenBudget: 100000  # per hour
    allowedTools:
      - kubectl-apply
      - kubectl-get
      - helm-install
      - helm-upgrade
      - istioctl-configure
    deniedTools:
      - kubectl-delete
      - vault-delete
    allowedNamespaces:
      - apex-os-core
      - apex-os-data
    deniedNamespaces:
      - kube-system
      - apex-os-security
```

#### 6.2.2 Authentication Flow

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│  Agent   │     │  SPIRE       │     │  Istio      │     │  Tool    │
│  Runtime │     │  Server      │     │  Sidecar    │     │  Service │
└────┬─────┘     └──────┬───────┘     └──────┬──────┘     └────┬─────┘
     │                  │                    │                  │
     │  1. Request SVID │                    │                  │
     │─────────────────►│                    │                  │
     │                  │                    │                  │
     │  2. X.509 SVID   │                    │                  │
     │◄─────────────────│                    │                  │
     │                  │                    │                  │
     │  3. mTLS handshake (using SVID)       │                  │
     │───────────────────────────────────────►│                  │
     │                  │                    │                  │
     │                  │  4. Forward with client cert          │
     │                  │                    │─────────────────►│
     │                  │                    │                  │
     │                  │                    │  5. Verify cert   │
     │                  │                    │     + check RBAC  │
     │                  │                    │◄─────────────────│
     │                  │                    │                  │
     │  6. Response     │                    │                  │
     │◄───────────────────────────────────────│                  │
     │                  │                    │                  │
```

### 6.3 Authorization

#### 6.3.1 Policy Engine (OPA/Rego)

All tool calls are authorized through OPA policies:

```rego
package apexos.agent.authz

import future.keywords.if
import future.keywords.in

# Default deny
default allow := false

# Allow if all conditions are met
allow if {
    valid_identity
    tool_permitted
    namespace_permitted
    rate_limit_ok
    budget_ok
    not_suspended
}

# Identity validation
valid_identity if {
    input.identity.spiffe_id != ""
    input.identity.issuer == "apex-os-ca"
    time.now_ns() < time.parse_rfc3339_ns(input.identity.expires_at)
}

# Tool permission check
tool_permitted if {
    input.tool.name in input.identity.allowed_tools
    not input.tool.name in input.identity.denied_tools
}

# Namespace permission check
namespace_permitted if {
    input.tool.namespace in input.identity.allowedNamespaces
    not input.tool.namespace in input.identity.deniedNamespaces
}

# Rate limit check
rate_limit_ok if {
    count := data.apexos.rate_limits[input.identity.agent_id].count
    count < data.apexos.rate_limits[input.identity.agent_id].limit
}

# Token budget check
budget_ok if {
    data.apexos.budgets[input.identity.agent_id].used 
    < data.apexos.budgets[input.identity.agent_id].limit
}

# Agent suspension check
not_suspended if {
    not data.apexos.suspensions[input.identity.agent_id]
}

# Denial reason for debugging
denial_reason := "invalid_identity" if { not valid_identity }
denial_reason := "tool_not_permitted" if { valid_identity; not tool_permitted }
denial_reason := "namespace_not_permitted" if { valid_identity; tool_permitted; not namespace_permitted }
denial_reason := "rate_limit_exceeded" if { valid_identity; tool_permitted; namespace_permitted; not rate_limit_ok }
denial_reason := "budget_exceeded" if { valid_identity; tool_permitted; namespace_permitted; rate_limit_ok; not budget_ok }
denial_reason := "agent_suspended" if { valid_identity; tool_permitted; namespace_permitted; rate_limit_ok; budget_ok; not_suspended }
```

#### 6.3.2 RBAC Matrix

| Role | Kubernetes | Helm | Vault | Monitoring | Notifications |
|------|-----------|------|-------|-----------|--------------|
| `infra-agent` | read, apply | install, upgrade | read | read | none |
| `deploy-agent` | read, apply | install, upgrade | read | read, create | send |
| `monitoring-agent` | read | none | none | read, create, update | send |
| `security-agent` | read, apply | none | read, write | read | send |
| `data-agent` | read | none | read | read | none |
| `admin-agent` | full | full | full | full | full |

### 6.4 Sandbox Isolation

#### 6.4.1 Sandbox Architecture

Each agent runs in an isolated sandbox with:

```
┌─────────────────────────────────────────────────┐
│              Agent Sandbox Pod                   │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │         Agent Runtime Container           │  │
│  │  - Agent code and dependencies            │  │
│  │  - Read-only root filesystem              │  │
│  │  - No network egress (except allowlisted)  │  │
│  │  - Resource limits enforced               │  │
│  │  - Non-root user                          │  │
│  │  - Seccomp profile                        │  │
│  │  - AppArmor/SELinux profile               │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │         Istio Sidecar Proxy               │  │
│  │  - mTLS termination                       │  │
│  │  - Traffic policy enforcement             │  │
│  │  - Egress gateway routing                 │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │         OPA Sidecar                       │  │
│  │  - Authorization checks                   │  │
│  │  - Policy enforcement                     │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  Network: Deny all egress, allow via EgressGateway│
│  Storage: EmptyDir only (no persistent volumes)   │
│  Secrets: Injected via Vault Agent, not env vars │
└─────────────────────────────────────────────────┘
```

#### 6.4.2 Pod Security Standards

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: agent-sandbox
  namespace: apex-os-core
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 65534
    runAsGroup: 65534
    fsGroup: 65534
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: agent-runtime
      image: apexos/agent-runtime:2.1.0
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
      resources:
        requests:
          cpu: "500m"
          memory: "512Mi"
        limits:
          cpu: "2000m"
          memory: "2Gi"
      volumeMounts:
        - name: tmp
          mountPath: /tmp
  volumes:
    - name: tmp
      emptyDir: {}
```

### 6.5 Prompt Injection Defense

#### 6.5.1 Defense Layers

| Layer | Mechanism | Implementation |
|-------|-----------|---------------|
| **Input Sanitization** | Strip control characters, normalize Unicode | Custom sanitizer in Agent Gateway |
| **Instruction Separation** | System prompt in separate channel from user input | gRPC metadata vs. message body |
| **Content Marking** | Delimit untrusted content with random tokens | `<untrusted>...</untrusted>` with UUID delimiters |
| **Output Filtering** | Scan outputs for PII, secrets, injection patterns | Presidio + custom regex patterns |
| **Tool Call Validation** | Validate all tool arguments against schema | JSON Schema validation in Tool Registry |
| **Rate Limiting** | Limit tool call frequency per agent | Token bucket per agent per tool |
| **Anomaly Detection** | Detect unusual tool call patterns | ML-based anomaly detection on tool call sequences |

#### 6.5.2 Prompt Injection Response

```yaml
promptInjectionDefense:
  enabled: true
  
  # Input filters
  inputFilters:
    - name: control-character-strip
      action: strip
      pattern: "[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"
    
    - name: unicode-normalization
      action: normalize
      form: NFKC
    
    - name: instruction-override-detection
      action: block
      patterns:
        - "(?i)ignore (all |any )?(previous|above|prior) instructions?"
        - "(?i)you are now"
        - "(?i)new (role|persona|identity)"
        - "(?i)system prompt"
        - "(?i)disregard (all |any )?(previous|above|prior)"
      actionOnMatch: block-and-alert
  
  # Output filters
  outputFilters:
    - name: pii-redaction
      engine: presidio
      entities: [PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IBAN]
      action: redact
    
    - name: secret-redaction
      patterns:
        - "(?i)api[_-]?key['\"]?\\s*[:=]\\s*['\"]?[A-Za-z0-9+/=]{20,}"
        - "(?i)password['\"]?\\s*[:=]\\s*['\"]?\\S+"
        - "(?i)token['\"]?\\s*[:=]\\s*['\"]?[A-Za-z0-9._-]{20,}"
      action: redact
    
    - name: injection-pattern-detection
      patterns:
        - "(?i)<!--\\s*system\\s*-->"
        - "(?i)\\[INST\\]"
        - "(?i)<<SYS>>"
      action: flag-for-review
  
  # Alerting
  alerts:
    onDetected: log-and-alert
    severity: high
    notify: [security-team, agent-owner]
```

### 6.6 Secrets Management

#### 6.6.1 Secret Types and Handling

| Secret Type | Storage | Injection | Rotation |
|------------|---------|-----------|----------|
| API Keys | HashiCorp Vault | Vault Agent sidecar | 90 days |
| Database Credentials | Vault (dynamic) | Dynamic secrets with TTL | 30 days |
| TLS Certificates | cert-manager | Automatic via CSI driver | 60 days |
| Model API Keys | Vault | Vault Agent sidecar | 90 days |
| Encryption Keys | AWS KMS / Azure Key Vault / GCP KMS | CSI driver | 365 days |

#### 6.6.2 Secret Access Pattern

```python
# Agent-side secret access (via Vault Agent)
class SecretManager:
    def __init__(self, vault_addr: str, role: str):
        self.vault = VaultClient(vault_addr, role)
    
    async def get_database_credentials(self, database: str) -> DatabaseCredentials:
        """Get dynamic database credentials with automatic lease renewal."""
        creds = await self.vault.read(f"database/creds/{database}")
        return DatabaseCredentials(
            username=creds.data["username"],
            password=creds.data["password"],
            lease_id=creds.lease_id,
            lease_duration=creds.lease_duration
        )
    
    async def get_api_key(self, service: str) -> str:
        """Get API key from Vault KV store."""
        secret = await self.vault.kv2.read(
            path=f"apikeys/{service}",
            mount_point="apexos"
        )
        return secret.data["key"]
```

### 6.7 Audit Logging

#### 6.7.1 Audit Events

Every security-relevant action is logged to an immutable audit trail:

```json
{
  "event_id": "audit-20261001-001",
  "timestamp": "2026-10-01T10:05:30.123Z",
  "event_type": "tool.call",
  "severity": "info",
  "actor": {
    "type": "agent",
    "id": "deploy-agent-01",
    "spiffe_id": "spiffe://apex-os.io/ns/apex-os-core/sa/deploy-agent",
    "ip": "10.0.1.15"
  },
  "resource": {
    "type": "tool",
    "name": "kubectl-apply",
    "namespace": "apex-os-core"
  },
  "action": {
    "operation": "apply",
    "parameters": {
      "manifest": "Deployment/my-service",
      "namespace": "apex-os-core",
      "dryRun": false
    },
    "result": "success"
  },
  "context": {
    "workflow_id": "wf-12345",
    "task_id": "task-67890",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
  },
  "policy_decision": {
    "allowed": true,
    "policy": "default-allow",
    "reason": "all checks passed"
  }
}
```

#### 6.7.2 Audit Storage

| Storage | Purpose | Retention | Encryption |
|---------|---------|-----------|-----------|
| PostgreSQL (hot) | Real-time queries, alerting | 90 days | AES-256 at rest |
| S3 / GCS (cold) | Long-term archival, compliance | 7 years | SSE-KMS |
| Write-once | Tamper-proof legal hold | Indefensive | Object lock (WORM) |

### 6.8 Network Security

#### 6.8.1 Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-sandbox-policy
  namespace: apex-os-core
spec:
  podSelector:
    matchLabels:
      app: agent-runtime
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow from Istio ingress gateway
    - from:
        - namespaceSelector:
            matchLabels:
              name: istio-system
      ports:
        - protocol: TCP
          port: 8080
    # Allow from OPA sidecar
    - from:
        - podSelector:
            matchLabels:
              app: opa-sidecar
      ports:
        - protocol: TCP
          port: 8181
  egress:
    # Allow to Istio egress gateway
    - to:
        - namespaceSelector:
            matchLabels:
              name: istio-system
      ports:
        - protocol: TCP
          port: 15443
    # Allow to Vault
    - to:
        - podSelector:
            matchLabels:
              app: vault
      ports:
        - protocol: TCP
          port: 8200
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
```

#### 6.8.2 Egress Control

All agent egress traffic flows through a dedicated egress gateway with:

1. **Allowlist-based routing**: Only pre-approved destinations are reachable.
2. **TLS inspection**: Outbound TLS is inspected for data exfiltration.
3. **Rate limiting**: Per-destination rate limits prevent abuse.
4. **Audit logging**: All egress connections are logged.

---

## 7. Agent Evaluation

### 7.1 Evaluation Framework

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Evaluation Framework                    │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Benchmark   │  │  Regression  │  │  A/B Testing │         │
│  │  Suites      │  │  Tests       │  │  Engine      │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│  ┌──────▼──────────────────▼──────────────────▼───────┐         │
│  │              Evaluation Orchestrator               │         │
│  │  - Test discovery and scheduling                   │         │
│  │  - Result aggregation                              │         │
│  │  - Score computation                               │         │
│  │  - Report generation                               │         │
│  └──────┬──────────────────┬──────────────────┬───────┘         │
│         │                  │                  │                 │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐         │
│  │  Metrics     │  │  Quality     │  │  Cost        │         │
│  │  Store       │  │  Gates       │  │  Analysis    │         │
│  │  (PostgreSQL)│  │  (OPA)       │  │  (Dashboard) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Benchmark Suites

#### 7.2.1 Suite Categories

| Category | Suites | Frequency | Purpose |
|----------|--------|-----------|---------|
| **Functional** | Tool correctness, task completion | Every deployment | Verify basic functionality |
| **Robustness** | Error handling, edge cases, adversarial inputs | Weekly | Verify resilience |
| **Performance** | Latency, throughput, concurrency | Weekly | Verify performance SLAs |
| **Security** | Prompt injection, privilege escalation, data exfiltration | Every deployment | Verify security posture |
| **Cost** | Token efficiency, API call optimization | Monthly | Verify cost targets |
| **E2E** | End-to-end workflow scenarios | Every deployment | Verify integration |

#### 7.2.2 Benchmark Definition

```yaml
apiVersion: agents.apex-os.io/v1
kind: BenchmarkSuite
metadata:
  name: deploy-agent-functional
  namespace: apex-os-evaluation
spec:
  description: "Functional tests for the deploy-agent"
  agent: deploy-agent
  version: "2.1.0"
  schedule: "0 */6 * * *"  # Every 6 hours
  
  tests:
    - name: "deploy-simple-service"
      description: "Deploy a simple stateless service"
      category: functional
      priority: critical
      timeout: 5m
      setup:
        - create-namespace: test-ns
      input:
        service_name: test-service
        docker_image: nginx:latest
        replicas: 2
        port: 80
      expected:
        - deployment_exists: test-service
        - service_exists: test-service
        - replicas_ready: 2
        - endpoint_responds: true
      scoring:
        - metric: task_completion
          weight: 0.4
        - metric: correctness
          weight: 0.4
        - metric: latency
          weight: 0.2
      teardown:
        - delete-namespace: test-ns
    
    - name: "deploy-with-helm-values"
      description: "Deploy using custom Helm values"
      category: functional
      priority: high
      timeout: 5m
      setup:
        - create-namespace: test-ns
      input:
        service_name: test-service
        docker_image: nginx:latest
        helm_values:
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
          ingress:
            enabled: true
            host: test.example.com
      expected:
        - deployment_exists: test-service
        - ingress_exists: test-service
        - resource_limits_set: true
      scoring:
        - metric: task_completion
          weight: 0.3
        - metric: correctness
          weight: 0.5
        - metric: latency
          weight: 0.2
      teardown:
        - delete-namespace: test-ns
    
    - name: "handle-invalid-manifest"
      description: "Gracefully handle invalid Kubernetes manifest"
      category: robustness
      priority: high
      timeout: 2m
      input:
        manifest: |
          apiVersion: v1
          kind: InvalidResource
          metadata:
            name: test
          spec:
            invalidField: true
      expected:
        - graceful_failure: true
        - error_message_contains: "error"
        - no_partial_deployment: true
      scoring:
        - metric: error_handling
          weight: 0.6
        - metric: correctness
          weight: 0.4
```

### 7.3 Scoring and Quality Gates

#### 7.3.1 Scoring Model

Each test produces a score from 0.0 to 1.0:

```
Test Score = Σ(metric_score × metric_weight)

Overall Score = Σ(test_score × test_weight) / Σ(test_weight)
```

#### 7.3.2 Quality Gates

```yaml
qualityGates:
  # Deployment blocking gates
  - name: "minimum-overall-score"
    condition: "overall_score >= 0.85"
    action: block-deployment
    severity: critical
    
  - name: "zero-critical-failures"
    condition: "critical_test_failures == 0"
    action: block-deployment
    severity: critical
    
  - name: "security-tests-pass"
    condition: "security_suite_pass_rate == 1.0"
    action: block-deployment
    severity: critical
    
  # Warning gates
  - name: "performance-regression"
    condition: "p99_latency_regression < 20%"
    action: warn
    severity: warning
    
  - name: "cost-regression"
    condition: "cost_increase < 30%"
    action: warn
    severity: warning
    
  # Auto-rollback triggers
  - name: "auto-rollback"
    condition: "error_rate > 5% OR p99_latency > 2x_baseline"
    action: auto-rollback
    severity: critical
```

### 7.4 Regression Testing

#### 7.4.1 Regression Test Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Agent   │───►│  Test    │───►│  Result  │───►│  Gate    │
│  Build   │    │  Runner  │    │  Compare │    │  Decision│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                     │               │               │
                     ▼               ▼               ▼
               ┌──────────┐   ┌──────────┐   ┌──────────┐
               │ Baseline │   │ Diff     │   │ Deploy / │
               │ Results  │   │ Analysis │   │ Block    │
               └──────────┘   └──────────┘   └──────────┘
```

#### 7.4.2 Regression Detection

```python
class RegressionDetector:
    def __init__(self, baseline_store: ResultStore):
        self.baseline = baseline_store
    
    def detect_regression(
        self, 
        current: TestResult, 
        baseline: TestResult
    ) -> RegressionReport:
        """Compare current results against baseline."""
        report = RegressionReport()
        
        # Performance regression
        if current.p99_latency > baseline.p99_latency * 1.2:
            report.add_finding(
                type="performance_regression",
                severity="warning",
                metric="p99_latency",
                baseline=baseline.p99_latency,
                current=current.p99_latency,
                delta_pct=(current.p99_latency / baseline.p99_latency - 1) * 100
            )
        
        # Correctness regression
        if current.correctness_score < baseline.correctness_score * 0.95:
            report.add_finding(
                type="correctness_regression",
                severity="critical",
                metric="correctness_score",
                baseline=baseline.correctness_score,
                current=current.correctness_score,
                delta_pct=(current.correctness_score / baseline.correctness_score - 1) * 100
            )
        
        # Cost regression
        if current.cost_usd > baseline.cost_usd * 1.3:
            report.add_finding(
                type="cost_regression",
                severity="warning",
                metric="cost_usd",
                baseline=baseline.cost_usd,
                current=current.cost_usd,
                delta_pct=(current.cost_usd / baseline.cost_usd - 1) * 100
            )
        
        return report
```

### 7.5 A/B Testing

#### 7.5.1 A/B Test Configuration

```yaml
apiVersion: agents.apex-os.io/v1
kind: ABTest
metadata:
  name: deploy-agent-v2-vs-v1
  namespace: apex-os-evaluation
spec:
  description: "Compare deploy-agent v2.1.0 against v2.0.0"
  duration: 7d
  trafficSplit:
    control: 50
    treatment: 50
  
  variants:
    control:
      agent: deploy-agent
      version: "2.0.0"
    treatment:
      agent: deploy-agent
      version: "2.1.0"
  
  metrics:
    - name: task_completion_rate
      type: rate
      direction: higher_is_better
    - name: p99_latency
      type: histogram
      direction: lower_is_better
    - name: cost_per_task
      type: gauge
      direction: lower_is_better
    - name: error_rate
      type: rate
      direction: lower_is_better
  
  successCriteria:
    - metric: task_completion_rate
      minImprovement: 0.05  # 5% improvement required
    - metric: p99_latency
      maxRegression: 0.10   # No more than 10% regression
  
  analysis:
    method: bayesian
    confidenceLevel: 0.95
    minSampleSize: 100
```

### 7.6 Continuous Evaluation

#### 7.6.1 Production Evaluation Loop

```
┌──────────────────────────────────────────────────────────────┐
│                Continuous Evaluation Loop                      │
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ Production│──►│  Sample  │──►│  Evaluate│──►│  Score   │ │
│  │  Traffic  │   │  Runs    │   │  Runs    │   │  & Rank  │ │
│  └──────────┘   └──────────┘   └──────────┘   └────┬─────┘ │
│                                                    │        │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐        │        │
│  │  Model   │◄──│  Fine-   │◄──│  Identify│◄───────┘        │
│  │  Update  │   │  tune    │   │  Gaps    │                 │
│  └──────────┘   └──────────┘   └──────────┘                 │
│                                                              │
│  Feedback sources:                                           │
│  - Human feedback (thumbs up/down on agent outputs)          │
│  - Automatic validation (schema checks, integration tests)   │
│  - Peer review (other agents review outputs)                 │
│  - User corrections (when users fix agent mistakes)          │
└──────────────────────────────────────────────────────────────┘
```

#### 7.6.2 Evaluation Metrics Summary

| Metric | Type | Target | Measurement |
|--------|------|--------|-------------|
| Task Completion Rate | Functional | ≥ 95% | Successful tasks / total tasks |
| Correctness Score | Functional | ≥ 90% | Output matches expected schema and semantics |
| P50 Latency | Performance | < 30s | Median task completion time |
| P99 Latency | Performance | < 5m | 99th percentile task completion time |
| Error Rate | Reliability | < 2% | Failed tasks / total tasks |
| Retry Rate | Reliability | < 10% | Retried tasks / total tasks |
| Cost per Task | Cost | < $0.10 | Average cost per completed task |
| Token Efficiency | Cost | < 2000 tokens/task | Average tokens per task |
| Security Pass Rate | Security | 100% | Security tests passed / total |
| User Satisfaction | Quality | ≥ 4.0/5.0 | Average user rating |

---

## 8. Deployment Topology

### 8.1 Kubernetes Deployment

#### 8.1.1 Namespace Layout

```
apex-os-agents/
├── apex-os-agents-gateway/       # Agent Gateway (Envoy + auth)
├── apex-os-agents-orchestrator/  # Orchestrator Service
├── apex-os-agents-runtime/        # Agent Runtime pods (per-agent)
├── apex-os-agents-workflows/      # Temporal.io workflow engine
├── apex-os-agents-state/          # Redis, PostgreSQL
├── apex-os-agents-messaging/      # NATS JetStream
├── apex-os-agents-evaluation/     # Evaluation Engine
├── apex-os-agents-monitoring/     # Prometheus, Grafana, Loki, Tempo
├── apex-os-agents-security/       # OPA, Vault Agent, SPIRE
└── apex-os-agents-secrets/        # Vault server
```

#### 8.1.2 Helm Values

```yaml
# values-production.yaml
global:
  environment: prod
  region: us-east-1
  
agentGateway:
  replicas: 3
  resources:
    requests: { cpu: "500m", memory: "512Mi" }
    limits: { cpu: "2000m", memory: "2Gi" }
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilization: 70
  
orchestrator:
  replicas: 3
  resources:
    requests: { cpu: "1000m", memory: "1Gi" }
    limits: { cpu: "4000m", memory: "4Gi" }
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 6
  
agentRuntime:
  defaultPoolSize: 5
  maxPoolSize: 50
  resources:
    requests: { cpu: "500m", memory: "512Mi" }
    limits: { cpu: "2000m", memory: "2Gi" }
  sandbox:
    enabled: true
    readOnlyRootFilesystem: true
    runAsNonRoot: true
  
messaging:
  nats:
    replicas: 3
    resources:
      requests: { cpu: "500m", memory: "1Gi" }
      limits: { cpu: "2000m", memory: "4Gi" }
    jetStream:
      enabled: true
      storage: 50Gi
  
stateStore:
  redis:
    replicas: 3
    resources:
      requests: { cpu: "250m", memory: "512Mi" }
      limits: { cpu: "1000m", memory: "2Gi" }
  postgresql:
    replicas: 2
    resources:
      requests: { cpu: "500m", memory: "1Gi" }
      limits: { cpu: "2000m", memory: "4Gi" }
    storage: 100Gi
  
evaluation:
  enabled: true
  schedule: "0 */6 * * *"
  resources:
    requests: { cpu: "500m", memory: "1Gi" }
    limits: { cpu: "2000m", memory: "4Gi" }
  
monitoring:
  prometheus:
    retention: 30d
    storage: 100Gi
  grafana:
    enabled: true
    adminPassword: "${GRAFANA_ADMIN_PASSWORD}"
  loki:
    retention: 7d
    storage: 200Gi
  tempo:
    retention: 7d
    storage: 100Gi
  
security:
  opa:
    enabled: true
  vault:
    enabled: true
    ha: true
  spire:
    enabled: true
```

### 8.2 Multi-Region Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Region Topology                         │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   us-east-1     │  │   us-west-2     │  │   eu-west-1     │ │
│  │  (Primary)      │  │  (Secondary)    │  │  (DR)           │ │
│  │                 │  │                 │  │                 │ │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │ │
│  │ │ Agent GW    │ │  │ │ Agent GW    │ │  │ │ Agent GW    │ │ │
│  │ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │ │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │ │
│  │ │ Orchestrator│ │  │ │ Orchestrator│ │  │ │ Orchestrator│ │ │
│  │ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │ │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │ │
│  │ │ Agent Pool  │ │  │ │ Agent Pool  │ │  │ │ Agent Pool  │ │ │
│  │ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │ │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │ │
│  │ │ State Store │ │◄─┼►│ State Store │◄─┼─►│ State Store │ │ │
│  │ │ (Primary)   │ │  │ │ (Replica)   │ │  │ │ (Replica)   │ │ │
│  │ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  Global Load Balancer (Route 53 / Cloudflare)                   │
│  └── Health-check based routing                                 │
│  └── Latency-based failover                                     │
│  └── Geo-proximity routing                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Scaling Strategy

| Component | Scaling Trigger | Min | Max | Cooldown |
|-----------|----------------|-----|-----|----------|
| Agent Gateway | CPU > 70% or latency P99 > 100ms | 3 | 20 | 60s |
| Orchestrator | Queue depth > 100 or CPU > 70% | 3 | 10 | 120s |
| Agent Runtime | Active tasks > pool size | 5 | 100 | 30s |
| NATS | Connections > 1000 or CPU > 70% | 3 | 9 | 120s |
| Redis | Memory > 80% or CPU > 70% | 3 | 12 | 300s |
| PostgreSQL | Connections > 80% or CPU > 70% | 2 | 6 | 300s |

---

## 9. Operational Runbooks

### 9.1 Agent Failure Recovery

#### 9.1.1 Automatic Recovery

```yaml
autoRecovery:
  # Agent crash recovery
  agentCrash:
    detection: "heartbeat_timeout > 30s"
    action: restart-agent
    maxRestarts: 3
    backoff: exponential
    escalation: "alert-oncall after 3 failures"
  
  # Task failure recovery
  taskFailure:
    detection: "task.status == 'failed'"
    action: retry-task
    maxRetries: 3
    retryOn: [timeout, transient-error, tool-available]
    noRetryOn: [auth-error, validation-error, policy-violation]
    backoff: exponential
  
  # Workflow failure recovery
  workflowFailure:
    detection: "workflow.status == 'failed'"
    action: rollback
    strategy: reverse-order
    maxRollbackTime: 10m
    escalation: "alert-oncall"
  
  # State corruption recovery
  stateCorruption:
    detection: "state checksum mismatch"
    action: restore-from-checkpoint
    checkpointInterval: 5m
    maxRestoreAge: 1h
```

#### 9.1.2 Manual Recovery Procedures

**Scenario: Agent unresponsive**

```bash
# 1. Check agent status
kubectl get pods -n apex-os-agents-runtime -l agent_id=deploy-agent-01

# 2. Check agent logs
kubectl logs -n apex-os-agents-runtime deploy-agent-01 --tail=100

# 3. Check resource usage
kubectl top pod -n apex-os-agents-runtime deploy-agent-01

# 4. If OOMKilled, increase memory limit
kubectl patch deployment -n apex-os-agents-runtime deploy-agent-01 \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"agent-runtime","resources":{"limits":{"memory":"4Gi"}}}]}}}}'

# 5. If still failing, drain and restart
kubectl delete pod -n apex-os-agents-runtime deploy-agent-01

# 6. Verify recovery
kubectl wait --for=condition=ready pod -n apex-os-agents-runtime -l agent_id=deploy-agent-01 --timeout=60s
```

### 9.2 Cost Management

#### 9.2.1 Cost Controls

| Control | Mechanism | Threshold | Action |
|---------|-----------|-----------|--------|
| Daily token budget | Per-agent token counter | $50/day | Block agent |
| Monthly token budget | Per-agent token counter | $1000/month | Alert + review |
| Per-task cost | Task-level cost tracking | $5/task | Require approval |
| Idle agent reclamation | No activity for 30 min | 30 min | Terminate agent |
| Model downgrade | Cost per task exceeds threshold | 2x baseline | Use cheaper model |

#### 9.2.2 Cost Optimization

```yaml
costOptimization:
  # Model selection based on task complexity
  modelRouting:
    simpleTasks:
      model: gpt-4o-mini
      maxTokens: 1000
      costPerToken: 0.0001
    complexTasks:
      model: gpt-4o
      maxTokens: 4000
      costPerToken: 0.001
    reasoningTasks:
      model: o1-preview
      maxTokens: 8000
      costPerToken: 0.01
  
  # Caching
  promptCaching:
    enabled: true
    ttl: 1h
    maxCacheSize: 10000
  
  # Batch processing
  batchApi:
    enabled: true
    window: 5s
    maxBatchSize: 100
```

### 9.3 Incident Response

#### 9.3.1 Severity Levels

| Severity | Description | Response Time | Escalation |
|----------|-------------|---------------|------------|
| **SEV1** | Agent platform down or security breach | 5 min | Immediate page to on-call + management |
| **SEV2** | Significant degradation or data loss risk | 15 min | Page to on-call |
| **SEV3** | Partial degradation or single agent failure | 1 hour | Slack alert to team |
| **SEV4** | Minor issue or performance degradation | 4 hours | Ticket creation |

#### 9.3.2 Incident Response Playbook

```yaml
incidentResponse:
  detection:
    - alertmanager: agent-down
    - alertmanager: high-error-rate
    - alertmanager: cost-spike
    - manual: user-report
  
  triage:
    - identify affected agents
    - assess blast radius
    - determine severity
    - create incident channel
  
  mitigation:
    sev1:
      - scale-up-healthy-agents
      - drain-affected-agents
      - rollback-recent-deployments
      - enable-fallback-mode
    sev2:
      - restart-affected-agents
      - increase-resources
      - disable-problematic-tools
  
  communication:
    - status-page-update
    - stakeholder-notification
    - incident-timeline
  
  postIncident:
    - root-cause-analysis
    - action-items
    - timeline-documentation
    - blameless-postmortem
```

---

## 10. Appendices

### 10.1 API Reference

#### 10.1.1 Orchestrator API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/workflows` | POST | Create a new workflow |
| `/api/v1/workflows/{id}` | GET | Get workflow status |
| `/api/v1/workflows/{id}/cancel` | POST | Cancel a running workflow |
| `/api/v1/workflows/{id}/retry` | POST | Retry a failed workflow |
| `/api/v1/agents` | GET | List registered agents |
| `/api/v1/agents/{id}` | GET | Get agent details |
| `/api/v1/agents/{id}/health` | GET | Get agent health |
| `/api/v1/tasks` | GET | List tasks |
| `/api/v1/tasks/{id}` | GET | Get task details |
| `/api/v1/tools` | GET | List available tools |
| `/api/v1/tools/{name}/invoke` | POST | Invoke a tool directly |

#### 10.1.2 Agent SDK (Python)

```python
from apexos.agents import Agent, Tool, WorkflowContext

class DeployAgent(Agent):
    """Agent for deploying microservices."""
    
    name = "deploy-agent"
    version = "2.1.0"
    domain = "infrastructure"
    
    tools = [
        Tool("kubectl-apply", namespace="*"),
        Tool("helm-install", namespace="*"),
        Tool("kubectl-get", namespace="*"),
    ]
    
    async def on_task(self, context: WorkflowContext, task: Task):
        """Handle an assigned task."""
        if task.type == "deploy-service":
            return await self._handle_deploy(context, task)
        elif task.type == "rollback-service":
            return await self._handle_rollback(context, task)
        else:
            raise UnsupportedTaskError(task.type)
    
    async def _handle_deploy(self, context: WorkflowContext, task: Task):
        """Deploy a microservice."""
        # Validate input
        service_name = task.inputs["service_name"]
        docker_image = task.inputs["docker_image"]
        
        # Create namespace if needed
        await self.tools["kubectl-apply"].call(
            manifest=f"Namespace/{service_name}",
            namespace="default"
        )
        
        # Deploy service
        result = await self.tools["helm-install"].call(
            chart="microservice",
            release=service_name,
            namespace=service_name,
            values={"image": docker_image}
        )
        
        # Wait for rollout
        await self.tools["kubectl-get"].call(
            resource="deployment",
            name=service_name,
            namespace=service_name,
            wait_for="condition=Available"
        )
        
        return TaskResult(
            status="success",
            outputs={"service_endpoint": f"https://{service_name}.apex-os.io"}
        )
```

### 10.2 Configuration Reference

#### 10.2.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APEXOS_AGENT_ID` | (required) | Unique agent identifier |
| `APEXOS_AGENT_VERSION` | (required) | Agent version |
| `APEXOS_AGENT_DOMAIN` | (required) | Agent domain |
| `APEXOS_ORCHESTRATOR_URL` | `http://orchestrator:8080` | Orchestrator endpoint |
| `APEXOS_MESSAGE_BUS_URL` | `nats://nats:4222` | NATS endpoint |
| `APEXOS_STATE_STORE_URL` | `redis://redis:6379` | Redis endpoint |
| `APEXOS_VAULT_ADDR` | `http://vault:8200` | Vault endpoint |
| `APEXOS_VAULT_ROLE` | (required) | Vault role for auth |
| `APEXOS_OTEL_ENDPOINT` | `http://otel-collector:4317` | OpenTelemetry collector |
| `APEXOS_LOG_LEVEL` | `INFO` | Logging level |
| `APEXOS_MAX_CONCURRENT_TASKS` | `5` | Max concurrent tasks per agent |
| `APEXOS_TASK_TIMEOUT` | `30m` | Default task timeout |
| `APEXOS_TOKEN_BUDGET_HOURLY` | `100000` | Hourly token budget |
| `APEXOS_TOOL_RATE_LIMIT` | `60` | Tool calls per minute |

### 10.3 Compliance Mapping

| Framework | Control | Implementation |
|-----------|---------|---------------|
| **SOC 2** | CC6.1 (Logical Access) | Agent identity via SPIFFE, RBAC via OPA |
| **SOC 2** | CC6.2 (Access Provisioning) | Agent registration workflow with approval |
| **SOC 2** | CC6.3 (Access Deprovisioning) | Automatic agent suspension on role change |
| **SOC 2** | CC7.2 (Monitoring) | Prometheus metrics, audit logging |
| **SOC 2** | CC7.3 (Incident Response) | Automated alerting, runbooks |
| **ISO 27001** | A.9.4 (Access Control) | Tool-level authorization, namespace isolation |
| **ISO 27001** | A.12.4 (Logging) | Immutable audit trail, 7-year retention |
| **ISO 27001** | A.14.2 (Secure Development) | Evaluation framework, quality gates |
| **GDPR** | Art. 32 (Security) | Encryption at rest and in transit, sandboxing |
| **HIPAA** | §164.312 (Access Control) | Agent RBAC, minimum necessary access |
| **PCI DSS** | Req. 7 (Access Limitation) | Tool-level authorization, segregation of duties |

### 10.4 References

1. [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)
2. [Temporal.io Documentation](https://docs.temporal.io/)
3. [NATS JetStream Documentation](https://docs.nats.io/nats-concepts/jetstream)
4. [Open Policy Agent (OPA)](https://www.openpolicyagent.org/docs/)
5. [HashiCorp Vault](https://developer.hashicorp.com/vault/docs)
6. [SPIFFE/SPIRE](https://spiffe.io/docs/latest/spire-about/spire-concepts/)
7. [Istio Service Mesh](https://istio.io/latest/docs/)
8. [CloudEvents Specification](https://cloudevents.io/)
9. [Presidio - PII Detection](https://microsoft.github.io/presidio/)
10. [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)

---

*End of document.*
