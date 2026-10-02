# APEX-OS Workflow Module — Benchmarks

> Last updated: 2026-10-02 · Scope: `src/apex_os_bp/workflow/engine.py` (225 lines, 7.9 KB)

---

## 1. Performance Benchmarks

### 1.1 Architecture Summary

| Component | Implementation | Overhead |
|---|---|---|
| Storage | In-memory `dict` (`_workflows`, `_versions`) | O(1) lookup, no I/O |
| Sequential execution | `for` loop over `workflow.steps` | ~0.1 ms/step (no I/O) |
| Parallel execution | `ThreadPoolExecutor(max_workers=len(steps))` | Thread spawn ~0.5 ms |
| Error handling | `for attempt in range(max_retries + 1)` + `time.sleep` | Configurable delay |
| Branching | `on_success` / `on_failure` via `get_step()` | O(n) linear scan |
| Versioning | `dict` of lists (`_versions[name]`) | O(1) append |

### 1.2 Single-Workflow Execution (Estimated)

Based on code analysis — no I/O, pure Python dataclasses, no external calls:

| Scenario | Steps | Est. Time | Bottleneck |
|---|---|---|---|
| Single step, no retries | 1 | ~0.05 ms | Python call overhead |
| 10 sequential steps | 10 | ~0.5 ms | Loop iteration |
| 100 sequential steps | 100 | ~5 ms | Loop iteration |
| 10 parallel steps (1 group) | 10 | ~1 ms | Thread pool spawn |
| 100 parallel steps (1 group) | 100 | ~5 ms | GIL contention |
| Step with 3 retries, 100 ms delay | 1 | ~300 ms | `time.sleep(0.1)` |
| Step with 5 retries, 500 ms delay | 1 | ~2.5 s | `time.sleep(0.5)` |

**Key insight:** The engine is CPU-bound for sequential workflows and GIL-bound for parallel groups. Thread pools help only for I/O-bound actions.

### 1.3 Parallel Execution Scaling

`ThreadPoolExecutor` with `max_workers=len(steps)` — one thread per step:

| Group Size | Threads | Est. Overhead | Effective Parallelism |
|---|---|---|---|
| 2 | 2 | ~1 ms | 2x (I/O-bound only) |
| 4 | 4 | ~2 ms | 4x (I/O-bound only) |
| 8 | 8 | ~4 ms | 8x (I/O-bound only) |
| 16 | 16 | ~8 ms | Degrades (GIL + context switching) |
| 32+ | 32+ | ~16 ms+ | No benefit for CPU-bound work |

**Caveat:** Python's GIL means CPU-bound steps see no speedup from threads. Parallel groups are effective only when steps perform I/O (HTTP calls, DB queries).

### 1.4 Error Handling & Retry Performance

| Config | Attempts | Delay/Attempt | Total Wait | Use Case |
|---|---|---|---|---|
| `max_retries=0` | 1 | 0 ms | 0 ms | Fail-fast |
| `max_retries=2, delay=0.01` | 3 | 10 ms | 20 ms | Transient network errors |
| `max_retries=3, delay=0.1` | 4 | 100 ms | 300 ms | DB connection retries |
| `max_retries=5, delay=0.5` | 6 | 500 ms | 2.5 s | External API with backoff |

**No exponential backoff** — `retry_delay` is fixed. This is a gap vs. production engines.

---

## 2. Scalability Benchmarks

### 2.1 In-Memory Storage Limits

The engine stores all workflows in `self._workflows: Dict[str, Workflow]` — no persistence, no eviction.

| Workflow Instances | Memory (est.) | Lookup Time | Notes |
|---|---|---|---|
| 1,000 | ~5 MB | O(1) | Negligible |
| 10,000 | ~50 MB | O(1) | Fits in L3 cache |
| 100,000 | ~500 MB | O(1) | RAM pressure, GC pauses |
| 1,000,000 | ~5 GB | O(1) | OOM risk on small instances |

**Memory estimate:** Each `Workflow` with 10 `WorkflowStep` objects ≈ 5 KB (dataclass overhead + dicts).

### 2.2 Execution Throughput (Estimated)

Single-threaded, no I/O:

| Metric | 1K Instances | 10K Instances | 100K Instances |
|---|---|---|---|
| Sequential (10 steps each) | ~5 s | ~50 s | ~500 s |
| With 4x parallel groups | ~2 s | ~20 s | ~200 s |
| With retries (avg 2x) | ~10 s | ~100 s | ~1000 s |
| API endpoint (FastAPI) | ~8 s | ~80 s | ~800 s |

**API overhead:** FastAPI + Pydantic validation adds ~30% latency vs. direct engine calls.

### 2.3 Concurrency Limits

The engine is **not thread-safe** — `_workflows` dict has no locking:

| Concurrent Writers | Risk | Mitigation |
|---|---|---|
| 1 (single-threaded) | None | Default FastAPI async |
| 2-4 | Race condition on dict | `asyncio.Lock` needed |
| 8+ | Data corruption | External state store required |

**Critical gap:** `WorkflowEngine` cannot be shared across multiple workers without external synchronization.

---

## 3. Comparison with Temporal & Camunda

### 3.1 Feature Matrix

| Feature | APEX-OS Workflow | Temporal | Camunda |
|---|---|---|---|
| Persistence | In-memory only | SQLite/PostgreSQL/Cassandra | PostgreSQL/MySQL/Elasticsearch |
| Parallel execution | ThreadPoolExecutor (GIL-limited) | Goroutines (true parallelism) | Async job executor |
| Error handling | Fixed-delay retries | Exponential backoff + heartbeats | Retry policies + incident management |
| Human-in-the-loop | Callback-based | Signal/Query API | User tasks + forms |
| Versioning | Manual (`name@version`) | Patching API | Process versioning |
| Distributed execution | No | Yes (multi-worker) | Yes (multi-node) |
| Observability | None | Metrics + tracing | Operate UI + metrics |
| Language support | Python only | Go/Java/Python/TS/JS | Java + REST API |

### 3.2 Public Benchmark Data

**Temporal** (from temporal.io public benchmarks, 2024):
- 10M+ workflow executions/day in production (Uber, Stripe, Netflix)
- p99 workflow task latency: <100 ms
- Throughput: 100K+ workflow decisions per second per cluster
- Horizontal scaling: 100+ worker nodes

**Camunda** (from camunda.com public benchmarks, 2024):
- 1,000+ process instances/second on 4-core hardware
- p95 process completion: <500 ms for simple processes
- Supports 10M+ process instances in a single database
- Clustering: 8+ nodes with Zeebee coordination

**APEX-OS Workflow** (this codebase):
- No published benchmarks (module is <250 lines, in-memory only)
- Estimated throughput: ~200 workflows/second (sequential, no I/O)
- No horizontal scaling capability
- No persistence — all state lost on restart

### 3.3 Gap Summary

| Dimension | APEX-OS | Temporal | Camunda |
|---|---|---|---|
| Maturity | Alpha (v0.1.0) | Production (v1.20+) | Production (v8.5+) |
| Scale | Single-node, in-memory | Distributed, persistent | Distributed, persistent |
| Throughput | ~200 wf/s (est.) | 100K+ decisions/s | 1K+ instances/s |
| Reliability | No durability | Durable execution | Durable execution |
| Ecosystem | None | SDKs in 5+ languages | Java + REST |

---

## 4. Optimization Recommendations

### 4.1 Critical (P0)

1. **Add persistence layer** — Replace in-memory dict with SQLite/PostgreSQL. Current design loses all state on restart.
2. **Add thread safety** — Wrap `_workflows` access with `threading.Lock` or use `asyncio.Lock` for async contexts.
3. **Implement exponential backoff** — Replace fixed `retry_delay` with `delay * (2 ** attempt)` + jitter.

### 4.2 High Priority (P1)

4. **Add async support** — `async def execute()` with `asyncio.gather()` for parallel groups instead of `ThreadPoolExecutor`.
5. **Add workflow state machine** — Current status tracking is ad-hoc; a formal FSM (e.g., `transitions` library) would prevent invalid state transitions.
6. **Add metrics instrumentation** — Track execution time, step duration, retry counts, failure rates via Prometheus client.

### 4.3 Medium Priority (P2)

7. **Add step timeout** — No timeout on `_run_action()`; a hung step blocks the entire workflow.
8. **Add workflow cancellation** — No way to cancel a running workflow.
9. **Add step input/output schema** — Current `result: Any` is untyped; Pydantic models would enable validation.
10. **Add DAG-based execution** — Current linear + parallel group model is limited; a DAG (e.g., `networkx`) would enable complex dependencies.

### 4.4 Low Priority (P3)

11. **Add workflow templates** — Reusable workflow definitions with parameter substitution.
12. **Add event triggers** — Webhook/message-queue triggered workflows.
13. **Add workflow visualization** — Generate Mermaid/Graphviz diagrams from workflow definitions.

---

## 5. Benchmark Reproduction

To validate estimates, run:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run existing tests (functional correctness)
pytest tests/test_workflow.py tests/test_workflow_deep.py -v

# Profile execution (requires cProfile)
python -m cProfile -o workflow.prof -c "
from apex_os_bp.workflow.engine import WorkflowEngine, WorkflowStep
e = WorkflowEngine()
w = e.create_workflow('bench')
for i in range(100):
    w.add_step(WorkflowStep(name=f's{i}', action='a'))
e.execute('bench')
"
```

---

## Summary

| Category | Status | Key Gap |
|---|---|---|
| Performance | Functional but unmeasured | No I/O, GIL-limited parallelism |
| Scalability | Single-node only | No persistence, no distribution |
| Reliability | Basic retries | No durability, no exponential backoff |
| Observability | None | No metrics, no tracing |
| Production readiness | Alpha | Missing 10+ critical features |

**Bottom line:** The workflow engine is a functional prototype suitable for testing and simple automation. It is **not production-ready** — it lacks persistence, thread safety, and distributed execution. For production workloads at scale, integrate with Temporal or Camunda via the existing API layer.
