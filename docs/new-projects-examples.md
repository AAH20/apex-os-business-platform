# New Projects — Runnable Examples

This document provides runnable code examples for all four APEX-OS projects plus cross-project integrations.

---

## 1. Agent-Reach Examples

### 1.1 Basic Agent Communication

```python
# agent_reach_basic.py
import asyncio
from apex_os import Agent, MessageBus

async def main():
    bus = MessageBus()
    agent_a = Agent("agent-a", bus)
    agent_b = Agent("agent-b", bus)

    await agent_a.send("agent-b", {"type": "greeting", "text": "Hello!"})
    response = await agent_b.receive(timeout=5)
    print(f"Agent-B received: {response.payload}")

asyncio.run(main())
```

### 1.2 Multi-Agent Broadcast

```python
# agent_broadcast.py
import asyncio
from apex_os import Agent, MessageBus

async def worker(name: str, bus: MessageBus):
    agent = Agent(name, bus)
    msg = await agent.receive(timeout=10)
    print(f"{name} got: {msg.payload['data']}")

async def main():
    bus = MessageBus()
    agents = [asyncio.create_task(worker(f"w{i}", bus)) for i in range(5)]
    await asyncio.sleep(0.5)
    await bus.broadcast({"type": "ping", "data": "hello-all"})
    await asyncio.gather(*agents)

asyncio.run(main())
```

### 1.3 Agent with Retry Logic

```python
# agent_retry.py
import asyncio
from apex_os import Agent, MessageBus, RetryPolicy

async def main():
    bus = MessageBus()
    agent = Agent("resilient-agent", bus, retry_policy=RetryPolicy(max_retries=3, backoff=1.0))

    try:
        result = await agent.request("target-agent", {"task": "compute"}, timeout=10)
        print(f"Result: {result}")
    except TimeoutError:
        print("Request timed out after retries")

asyncio.run(main())
```

---

## 2. Big Data Examples

### 2.1 Parallel Data Processing

```python
# bigdata_parallel.py
import asyncio
from apex_os import DataPipeline, ChunkProcessor

async def process_chunk(chunk_id: int, data: list) -> dict:
    await asyncio.sleep(0.01)  # simulate I/O
    return {"chunk": chunk_id, "sum": sum(data), "count": len(data)}

async def main():
    pipeline = DataPipeline(workers=8)
    chunks = [list(range(i * 1000, (i + 1) * 1000)) for i in range(20)]

    results = await pipeline.map(process_chunk, chunks)
    total = sum(r["sum"] for r in results)
    print(f"Total sum: {total}, Chunks processed: {len(results)}")

asyncio.run(main())
```

### 2.2 Stream Processing with Backpressure

```python
# bigdata_stream.py
import asyncio
from apex_os import StreamProcessor, BackpressureConfig

async def main():
    config = BackpressureConfig(max_buffer=1000, watermark=0.8)
    processor = StreamProcessor(config)

    async def source():
        for i in range(10_000):
            await processor.emit({"id": i, "value": i * 2})
        await processor.close()

    async def sink():
        count = 0
        async for record in processor.consume():
            count += 1
        print(f"Processed {count} records")

    await asyncio.gather(source(), sink())

asyncio.run(main())
```

### 2.3 Distributed Aggregation

```python
# bigdata_aggregate.py
import asyncio
from apex_os import Aggregator, ShardManager

async def main():
    shards = ShardManager(shard_count=4)
    aggregator = Aggregator(shards)

    async def load_shard(shard_id: int):
        data = [{"key": f"k{i%10}", "val": i} for i in range(shard_id * 250, (shard_id + 1) * 250)]
        await shards.load(shard_id, data)

    await asyncio.gather(*[load_shard(i) for i in range(4)])
    result = await aggregator.group_by("key", agg="sum", field="val")
    print(f"Aggregated {len(result)} groups")

asyncio.run(main())
```

---

## 3. Data Science Examples

### 3.1 Feature Engineering Pipeline

```python
# ds_features.py
import asyncio
from apex_os import FeaturePipeline, Transformer

class StandardScaler(Transformer):
    def fit(self, data: list[dict]) -> dict:
        vals = [d["value"] for d in data]
        self.mean = sum(vals) / len(vals)
        self.std = (sum((v - self.mean) ** 2 for v in vals) / len(vals)) ** 0.5
        return self

    def transform(self, record: dict) -> dict:
        record["scaled"] = (record["value"] - self.mean) / (self.std or 1)
        return record

async def main():
    pipeline = FeaturePipeline()
    pipeline.add(StandardScaler())

    raw = [{"value": float(i)} for i in range(1000)]
    fitted = pipeline.fit(raw)
    transformed = [fitted.transform(r) for r in raw[:5]]
    print(f"Sample: {transformed}")

asyncio.run(main())
```

### 3.2 Model Training Loop

```python
# ds_training.py
import asyncio
from apex_os import Trainer, MetricTracker

async def main():
    tracker = MetricTracker(metrics=["loss", "accuracy"])
    trainer = Trainer(epochs=10, tracker=tracker)

    for epoch in range(trainer.epochs):
        await asyncio.sleep(0.05)  # simulate training step
        loss = 1.0 / (epoch + 1)
        acc = 1.0 - loss
        tracker.log(epoch=epoch, loss=loss, accuracy=acc)
        print(f"Epoch {epoch}: loss={loss:.4f}, acc={acc:.4f}")

    summary = tracker.summary()
    print(f"Final: {summary}")

asyncio.run(main())
```

### 3.3 Cross-Validation

```python
# ds_crossval.py
import asyncio
from apex_os import CrossValidator, Fold

async def train_fold(fold: Fold) -> float:
    await asyncio.sleep(0.05)
    return 0.85 + fold.index * 0.01  # simulated accuracy

async def main():
    cv = CrossValidator(n_folds=5)
    scores = await cv.run(train_fold)
    mean_score = sum(scores) / len(scores)
    print(f"CV scores: {scores}")
    print(f"Mean accuracy: {mean_score:.4f}")

asyncio.run(main())
```

---

## 4. Continuous BI Examples

### 4.1 Real-Time Dashboard Feed

```python
# bi_realtime.py
import asyncio
from apex_os import BIConnector, Dashboard

async def main():
    connector = BIConnector(dsn="apex_bi")
    dashboard = Dashboard(connector, refresh_interval=5)

    async def on_update(metrics: dict):
        print(f"[BI] Revenue: {metrics['revenue']}, Orders: {metrics['orders']}")

    dashboard.subscribe(on_update)

    # Simulate live data for 30 seconds
    await dashboard.start()
    await asyncio.sleep(30)
    await dashboard.stop()

asyncio.run(main())
```

### 4.2 Scheduled Report Generation

```python
# bi_scheduled.py
import asyncio
from apex_os import ReportScheduler, Report

async def generate_daily_report(date: str) -> Report:
    await asyncio.sleep(0.1)  # simulate query
    return Report(title=f"Daily Report {date}", rows=1000, metrics={"total": 42000})

async def main():
    scheduler = ReportScheduler()
    scheduler.add_job("daily", "0 6 * * *", generate_daily_report)

    # Run once immediately for demo
    report = await generate_daily_report("2026-10-02")
    print(f"Report: {report.title}, rows={report.rows}")

asyncio.run(main())
```

### 4.3 Anomaly Detection Alert

```python
# bi_anomaly.py
import asyncio
from apex_os import AnomalyDetector, AlertChannel

async def main():
    detector = AnomalyDetector(sensitivity=2.0)
    alerts = AlertChannel()

    async def on_anomaly(metric: str, value: float, expected: float):
        await alerts.send(f"ANOMALY: {metric}={value} (expected {expected})")

    detector.on_anomaly(on_anomaly)

    # Stream some metrics
    for i in range(100):
        value = 100.0 + (i * 0.1)
        if i == 50:
            value = 500.0  # spike
        await detector.check("cpu_usage", value)
        await asyncio.sleep(0.01)

asyncio.run(main())
```

---

## 5. Cross-Project Examples

### 5.1 Agent-Driven Data Pipeline

```python
# cross_agent_pipeline.py
import asyncio
from apex_os import Agent, MessageBus, DataPipeline

async def main():
    bus = MessageBus()
    orchestrator = Agent("orchestrator", bus)
    pipeline = DataPipeline(workers=4)

    async def agent_task(agent_name: str, data: list) -> dict:
        agent = Agent(agent_name, bus)
        result = await pipeline.map(lambda x: x * 2, data)
        return {"agent": agent_name, "result": sum(result)}

    tasks = [agent_task(f"agent-{i}", list(range(100))) for i in range(4)]
    results = await asyncio.gather(*tasks)
    for r in results:
        print(f"{r['agent']}: sum={r['result']}")

asyncio.run(main())
```

### 5.2 BI-Integrated Model Monitoring

```python
# cross_bi_ml.py
import asyncio
from apex_os import Trainer, BIConnector, MetricTracker

async def main():
    connector = BIConnector(dsn="apex_bi")
    tracker = MetricTracker(metrics=["loss", "accuracy", "latency"])
    trainer = Trainer(epochs=5, tracker=tracker)

    for epoch in range(trainer.epochs):
        await asyncio.sleep(0.05)
        tracker.log(epoch=epoch, loss=0.5 / (epoch + 1), accuracy=0.9, latency=12.0)

    # Push metrics to BI dashboard
    await connector.push("model_metrics", tracker.summary())
    print("Metrics pushed to BI dashboard")

asyncio.run(main())
```

### 5.3 End-to-End: Ingest → Process → Analyze → Alert

```python
# cross_e2e.py
import asyncio
from apex_os import (
    StreamProcessor, DataPipeline, FeaturePipeline,
    AnomalyDetector, AlertChannel, BIConnector
)

async def main():
    # Stage 1: Ingest
    stream = StreamProcessor()
    # Stage 2: Process
    pipeline = DataPipeline(workers=4)
    # Stage 3: Feature engineering
    features = FeaturePipeline()
    # Stage 4: Anomaly detection
    detector = AnomalyDetector(sensitivity=2.5)
    alerts = AlertChannel()
    # Stage 5: BI output
    bi = BIConnector(dsn="apex_bi")

    async def on_anomaly(metric, value, expected):
        await alerts.send(f"ALERT: {metric}={value} (expected {expected})")
        await bi.push("anomalies", {"metric": metric, "value": value})

    detector.on_anomaly(on_anomaly)

    # Run pipeline
    async def process_record(record):
        processed = await pipeline.map(lambda x: x + 1, [record])
        feature = features.fit_transform({"value": processed[0]})
        await detector.check("stream_value", feature["scaled"])
        return feature

    # Simulate 50 records
    for i in range(50):
        value = 10.0 + i * 0.5
        if i == 25:
            value = 999.0  # anomaly
        await stream.emit({"id": i, "value": value})
        result = await process_record(value)

    print("End-to-end pipeline complete")

asyncio.run(main())
```

### 5.4 Multi-Agent Collaborative Analysis

```python
# cross_multi_agent_analysis.py
import asyncio
from apex_os import Agent, MessageBus, Aggregator

async def analyst_agent(name: str, bus: MessageBus, data: list) -> dict:
    agent = Agent(name, bus)
    local_sum = sum(data)
    await bus.publish("analysis", {"agent": name, "partial": local_sum})
    return {"agent": name, "partial": local_sum}

async def main():
    bus = MessageBus()
    aggregator = Aggregator()

    # Split data among agents
    chunks = [list(range(i * 250, (i + 1) * 250)) for i in range(4)]
    agents = [analyst_agent(f"analyst-{i}", bus, chunk) for i, chunk in enumerate(chunks)]

    results = await asyncio.gather(*agents)
    total = sum(r["partial"] for r in results)
    print(f"Collaborative analysis total: {total}")

    # Verify: sum of 0..999 = 499500
    assert total == 499500, f"Expected 499500, got {total}"
    print("Verification passed!")

asyncio.run(main())
```

---

## Running the Examples

Each example is self-contained. Run with:

```bash
python docs/examples/agent_reach_basic.py
python docs/examples/bigdata_parallel.py
python docs/examples/ds_features.py
python docs/examples/bi_realtime.py
python docs/examples/cross_e2e.py
```

All examples use `asyncio` and the `apex-os` SDK. Install dependencies:

```bash
pip install apex-os-sdk
```
