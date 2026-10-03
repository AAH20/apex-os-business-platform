# ContinuousBI Benchmark Tests

## 1. Dashboard Rendering Speed

### Test: Initial Dashboard Load
- **Metric**: Time to first meaningful paint (TTFMP)
- **Target**: < 2.0s for standard dashboards (< 50 widgets)
- **Measurement**: `performance.now()` at dashboard mount → last widget render
- **Test Data**: 10K rows, 20 widgets, 5 chart types
- **Pass Criteria**: p95 < 2.0s, p99 < 3.5s

### Test: Widget Update Latency
- **Metric**: Time from data update to visual refresh
- **Target**: < 500ms for real-time widgets
- **Measurement**: WebSocket message timestamp → DOM update complete
- **Test Data**: 1-second tick interval, streaming data
- **Pass Criteria**: p95 < 500ms, p99 < 1.0s

### Test: Dashboard Switch Time
- **Metric**: Time to switch between saved dashboards
- **Target**: < 800ms
- **Measurement**: Navigation click → new dashboard fully rendered
- **Pass Criteria**: p95 < 800ms, p99 < 1.5s

### Test: Large Dataset Rendering
- **Metric**: Render time for 100K+ row datasets
- **Target**: < 4.0s initial render
- **Measurement**: Query start → all widgets visible
- **Pass Criteria**: p95 < 4.0s, p99 < 6.0s

---

## 2. Alert Evaluation Latency

### Test: Single Alert Evaluation
- **Metric**: Time from data point arrival to alert condition check
- **Target**: < 200ms
- **Measurement**: Ingest timestamp → evaluation complete
- **Pass Criteria**: p95 < 200ms, p99 < 500ms

### Test: Alert Notification Delivery
- **Metric**: Time from alert trigger to notification sent
- **Target**: < 1.0s (email), < 2.0s (webhook)
- **Measurement**: Alert fired → notification API response
- **Pass Criteria**: p95 < 1.0s, p99 < 2.0s

### Test: Bulk Alert Evaluation
- **Metric**: Throughput for 1000 concurrent alert rules
- **Target**: > 500 evaluations/second
- **Measurement**: Rules evaluated per second under load
- **Pass Criteria**: Sustained > 500 evals/sec for 60s

### Test: Alert Rule Complexity Scaling
- **Metric**: Evaluation time vs. rule complexity
- **Target**: Linear scaling, < 10x slowdown at 10 conditions
- **Measurement**: 1-condition vs. 10-condition rule latency
- **Pass Criteria**: 10-condition p95 < 2.0s

---

## 3. Data Freshness Accuracy

### Test: End-to-End Data Latency
- **Metric**: Time from source data change to dashboard reflection
- **Target**: < 5.0s for real-time sources
- **Measurement**: Source DB commit timestamp → widget displays new value
- **Pass Criteria**: p95 < 5.0s, p99 < 10.0s

### Test: Data Consistency Check
- **Metric**: Accuracy of displayed values vs. source
- **Target**: 100% match (zero stale reads)
- **Measurement**: Compare dashboard values against source DB at random intervals
- **Pass Criteria**: 0 mismatches in 1000 samples

### Test: Cache Invalidation Speed
- **Metric**: Time from data update to cache invalidation
- **Target**: < 500ms
- **Measurement**: Write to source → cache TTL refresh
- **Pass Criteria**: p95 < 500ms, p99 < 1.0s

### Test: Historical Data Accuracy
- **Metric**: Correctness of time-window aggregations
- **Target**: < 0.1% deviation from ground truth
- **Measurement**: Compare aggregated values against raw data computation
- **Pass Criteria**: Max deviation < 0.1% across 100 queries

---

## 4. Report Generation Performance

### Test: Standard Report Generation
- **Metric**: Time to generate a PDF/CSV report
- **Target**: < 10s for standard reports (< 10 pages)
- **Measurement**: Report request → file ready for download
- **Pass Criteria**: p95 < 10s, p99 < 20s

### Test: Large Report Generation
- **Metric**: Time to generate reports with 100K+ rows
- **Target**: < 60s
- **Measurement**: Report request → file ready
- **Pass Criteria**: p95 < 60s, p99 < 120s

### Test: Concurrent Report Generation
- **Metric**: Throughput for simultaneous report requests
- **Target**: > 10 concurrent reports without degradation
- **Measurement**: 10 simultaneous requests, measure individual completion times
- **Pass Criteria**: All complete within 2x single-report time

### Test: Scheduled Report Delivery
- **Metric**: On-time delivery rate for scheduled reports
- **Target**: > 99% delivered within 1 minute of schedule
- **Measurement**: Scheduled time → delivery confirmation
- **Pass Criteria**: > 99% on-time over 30-day window

---

## 5. Performance Metrics

### Test: API Response Time
- **Metric**: REST API endpoint latency
- **Target**: p95 < 300ms for read endpoints
- **Measurement**: Request received → response sent
- **Pass Criteria**: p95 < 300ms, p99 < 800ms

### Test: WebSocket Connection Stability
- **Metric**: Connection uptime and reconnection time
- **Target**: > 99.9% uptime, < 3s reconnection
- **Measurement**: Connection drops per 24h, reconnection duration
- **Pass Criteria**: < 3 drops/day, p95 reconnect < 3s

### Test: Memory Usage Under Load
- **Metric**: Browser memory consumption
- **Target**: < 500MB for standard dashboard session
- **Measurement**: `performance.memory.usedJSHeapSize` at 30-min intervals
- **Pass Criteria**: p95 < 500MB, no continuous growth pattern

### Test: CPU Utilization
- **Metric**: Client-side CPU usage during active dashboard viewing
- **Target**: < 30% average on mid-range hardware
- **Measurement**: `performance.now()` deltas during idle vs. active periods
- **Pass Criteria**: Average < 30% over 15-minute session

### Test: Database Query Performance
- **Metric**: Backend query execution time
- **Target**: p95 < 500ms for dashboard queries
- **Measurement**: Query start → result returned
- **Pass Criteria**: p95 < 500ms, p99 < 1.5s

### Test: Concurrent User Load
- **Metric**: System performance under 500 concurrent users
- **Target**: < 20% degradation vs. single-user baseline
- **Measurement**: Response times at 100, 250, 500 concurrent users
- **Pass Criteria**: p95 remains < 2x baseline at 500 users

---

## Benchmark Execution

```bash
# Run all benchmarks
npm run benchmark:continuous-bi

# Run specific suite
npm run benchmark:continuous-bi -- --suite=dashboard
npm run benchmark:continuous-bi -- --suite=alerts
npm run benchmark:continuous-bi -- --suite=freshness
npm run benchmark:continuous-bi -- --suite=reports
npm run benchmark:continuous-bi -- --suite=performance

# Run with custom parameters
npm run benchmark:continuous-bi -- --concurrency=100 --duration=300
```

## Reporting

Results are output to `benchmarks/results/continuous-bi-{timestamp}.json` with:
- Individual test metrics (min, max, mean, p50, p95, p99)
- Pass/fail status per test
- Comparison against previous run (regression detection)
- Environment metadata (browser version, hardware, data volume)
