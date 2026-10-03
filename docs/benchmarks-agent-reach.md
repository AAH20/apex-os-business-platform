# Agent-Reach Benchmark Tests

Comprehensive benchmark suite for the Agent-Reach subsystem covering agent creation, message routing, load balancing, health monitoring, and performance metrics.

## 1. Agent Creation Speed

### Test: Single Agent Creation Latency
- **Method**: Create one agent via `AgentFactory.create()` and measure wall-clock time
- **Metric**: p50, p95, p99 latency in milliseconds
- **Acceptance**: p50 < 50ms, p95 < 150ms, p99 < 300ms
- **Iterations**: 1000 runs, discard first 100 as warmup

### Test: Concurrent Agent Creation
- **Method**: Spawn N goroutines creating agents simultaneously
- **Parameters**: N = 10, 50, 100, 500
- **Metric**: Total creation time, throughput (agents/sec), error rate
- **Acceptance**: No duplicate IDs, error rate < 0.1%, throughput scales linearly up to 100 concurrent

### Test: Agent Creation with Full Capability Registration
- **Method**: Create agent with 10+ capabilities, tools, and metadata
- **Metric**: p50, p95 latency
- **Acceptance**: p50 < 100ms, p95 < 250ms

### Test: Agent Pool Initialization
- **Method**: Pre-warm agent pool to target size
- **Parameters**: Pool sizes = 5, 25, 100
- **Metric**: Time to full pool readiness
- **Acceptance**: Pool of 100 ready in < 5s

## 2. Message Routing Latency

### Test: Direct Agent-to-Agent Message
- **Method**: Send message from Agent A to Agent B (same node)
- **Metric**: End-to-end delivery time (send to receive callback)
- **Acceptance**: p50 < 5ms, p95 < 20ms, p99 < 50ms
- **Iterations**: 5000 messages

### Test: Broadcast Message Fan-Out
- **Method**: One sender broadcasts to N receivers
- **Parameters**: N = 5, 20, 100
- **Metric**: Time until all receivers acknowledge
- **Acceptance**: N=100 broadcast completes in < 100ms

### Test: Cross-Node Message Routing
- **Method**: Route message between agents on different cluster nodes
- **Metric**: p50, p95, p99 latency including network hop
- **Acceptance**: p50 < 15ms, p95 < 50ms, p99 < 100ms

### Test: Message Routing Under Load
- **Method**: Sustain 1000 msg/sec while measuring routing latency
- **Metric**: Latency percentiles under sustained load
- **Acceptance**: p99 < 100ms at 1000 msg/sec sustained

### Test: Priority Message Preemption
- **Method**: Send high-priority message while queue is saturated with normal messages
- **Metric**: Time from send to delivery for priority message
- **Acceptance**: Priority message delivered in < 10ms regardless of queue depth

## 3. Load Balancing Performance

### Test: Round-Robin Distribution
- **Method**: Send 1000 tasks to a pool of 10 agents
- **Metric**: Standard deviation of task count per agent
- **Acceptance**: Std dev < 5% of mean (near-perfect distribution)

### Test: Weighted Load Balancing
- **Method**: Configure agents with weights 1:2:3:4:5, send 1500 tasks
- **Metric**: Actual distribution vs expected weighted distribution
- **Acceptance**: Chi-squared test p-value > 0.05

### Test: Least-Connections Balancing
- **Method**: Agents report varying active connection counts; send 500 tasks
- **Metric**: Final connection count variance
- **Acceptance**: Max/min connection ratio < 1.5 after balancing

### Test: Agent Failure Rebalancing
- **Method**: Kill 3 of 10 agents mid-task-distribution
- **Metric**: Time to detect failure and redistribute load
- **Acceptance**: Detection < 2s, redistribution complete < 5s, zero message loss

### Test: Scale-Out Latency
- **Method**: Add 5 new agents to existing pool of 10 under load
- **Metric**: Time until new agents receive tasks
- **Acceptance**: New agents receive traffic within 3s of registration

## 4. Health Monitoring Accuracy

### Test: Liveness Detection Precision
- **Method**: Stop agent process abruptly; measure detection time
- **Metric**: Time from process death to health check failure
- **Acceptance**: Detected within 2 health check intervals (default: 10s)

### Test: False Positive Rate
- **Method**: Run healthy agents for 24 hours with normal workload
- **Metric**: Number of false "unhealthy" transitions
- **Acceptance**: Zero false positives in 24h period

### Test: Graceful Degradation Detection
- **Method**: Introduce artificial latency (200ms) in agent responses
- **Metric**: Time to mark agent as degraded
- **Acceptance**: Degraded status within 3 health check intervals

### Test: Recovery Detection
- **Method**: Restore killed agent; measure time to mark healthy
- **Metric**: Time from agent restart to healthy status
- **Acceptance**: Healthy within 3 health check intervals of restart

### Test: Health Check Overhead
- **Method**: Measure CPU and memory overhead of health checking
- **Metric**: Additional CPU% and memory bytes per agent
- **Acceptance**: < 0.1% CPU, < 1MB memory per agent

## 5. Performance Metrics

### Test: Throughput Benchmark
- **Method**: Measure max sustained messages/sec across cluster
- **Parameters**: Cluster sizes = 1, 3, 5, 10 nodes
- **Metric**: Peak throughput, throughput per node
- **Acceptance**: Linear scaling: 10-node cluster achieves >= 8x single-node throughput

### Test: Memory Footprint per Agent
- **Method**: Measure heap usage for idle and active agents
- **Metric**: Bytes per idle agent, bytes per active agent
- **Acceptance**: Idle < 2MB, Active < 10MB per agent

### Test: Connection Pool Efficiency
- **Method**: Measure connection reuse rate under varying load
- **Metric**: Connection reuse ratio, pool exhaustion events
- **Acceptance**: Reuse ratio > 95%, zero pool exhaustion at 80% capacity

### Test: Serialization Overhead
- **Method**: Measure time spent in message serialization/deserialization
- **Metric**: p50, p95 serialization time per message
- **Acceptance**: p50 < 1ms, p95 < 3ms for messages up to 64KB

### Test: End-to-End Pipeline Latency
- **Method**: Full round-trip: client -> router -> agent -> router -> client
- **Metric**: p50, p95, p99, p99.9 latency
- **Acceptance**: p50 < 20ms, p95 < 80ms, p99 < 200ms, p99.9 < 500ms

### Test: Resource Utilization Under Load
- **Method**: Run at 50%, 80%, 95% of max throughput for 1 hour each
- **Metric**: CPU%, memory%, goroutine count, GC pause times
- **Acceptance**: No memory leaks, GC pauses < 10ms, goroutine count stable

## Running the Benchmarks

```bash
# Run all benchmarks
go test -bench=BenchmarkAgentReach -benchmem -count=10 ./...

# Run specific benchmark category
go test -bench=BenchmarkAgentCreation -benchmem ./...
go test -bench=BenchmarkMessageRouting -benchmem ./...
go test -bench=BenchmarkLoadBalancing -benchmem ./...
go test -bench=BenchmarkHealthMonitoring -benchmem ./...
go test -bench=BenchmarkPerformance -benchmem ./...

# Generate benchmark report
go test -bench=BenchmarkAgentReach -benchmem -count=10 ./... | tee benchmark-results.txt
```

## Benchmark Environment

- **Go version**: 1.22+
- **OS**: Linux (production parity)
- **CPU**: 4+ cores recommended
- **Memory**: 8GB+ RAM
- **Network**: Loopback for single-node, 1Gbps for multi-node
- **Isolation**: Run on dedicated CI runners to avoid noisy-neighbor effects
