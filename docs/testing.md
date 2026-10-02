# APEX-OS Testing Guide

## 1. Unit Testing

Unit tests verify individual functions, classes, and modules in isolation.

### Framework
- **Python**: `pytest` with `pytest-cov` for coverage
- **JS/TS**: `vitest` or `jest`

### Commands
```bash
# Python
pytest tests/unit/ -v --tb=short
pytest tests/unit/ --cov=src --cov-report=term-missing

# JS/TS
npm run test:unit
npx vitest run --coverage
```

### Example (Python)
```python
# tests/unit/test_pricing.py
from src.pricing import calculate_discount

def test_calculate_discount_standard():
    assert calculate_discount(100, 10) == 90.0

def test_calculate_discount_zero():
    assert calculate_discount(100, 0) == 100.0

def test_calculate_discount_full():
    assert calculate_discount(100, 100) == 0.0
```

### Example (TypeScript)
```typescript
// tests/unit/pricing.test.ts
import { calculateDiscount } from '../../src/pricing';

test('applies 10% discount', () => {
  expect(calculateDiscount(100, 10)).toBe(90);
});
```

### Best Practices
- Mock external dependencies (DB, HTTP, filesystem)
- One assertion per test case
- Use fixtures for shared setup
- Target ≥ 80% line coverage on business logic

---

## 2. Integration Testing

Integration tests verify interactions between modules, APIs, and databases.

### Setup
```bash
# Start test dependencies
docker-compose -f docker-compose.test.yml up -d

# Run migrations
alembic upgrade head
# or
npm run db:migrate
```

### Commands
```bash
# Python
pytest tests/integration/ -v --tb=short

# JS/TS
npm run test:integration
```

### Example (API Integration)
```python
# tests/integration/test_orders_api.py
import requests

BASE_URL = "http://localhost:8000/api/v1"

def test_create_order_flow():
    # Create customer
    r = requests.post(f"{BASE_URL}/customers", json={"name": "Test"})
    assert r.status_code == 201
    customer_id = r.json()["id"]

    # Create order
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_id": customer_id,
        "items": [{"sku": "A1", "qty": 2}]
    })
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
```

### Best Practices
- Use a dedicated test database
- Reset state between tests (transactions or truncation)
- Test happy path + error paths + edge cases
- Verify side effects (DB rows, queue messages, events)

---

## 3. Performance Testing

Performance tests validate latency, throughput, and resource usage under load.

### Tools
- **k6**: HTTP/API load testing
- **locust**: Python-based load testing
- **pytest-benchmark**: Micro-benchmarks

### Commands
```bash
# k6 smoke test
k6 run --vus 10 --duration 30s tests/perf/smoke.js

# k6 load test
k6 run --vus 100 --duration 5m tests/perf/load.js

# Locust
locust -f tests/perf/locustfile.py --host http://localhost:8000

# Python benchmark
pytest tests/perf/ --benchmark-only
```

### Example (k6)
```javascript
// tests/perf/smoke.js
import http from 'k6/http';
import { check } from 'k6';

export default function () {
  const res = http.get('http://localhost:8000/api/v1/health');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response < 200ms': (r) => r.timings.duration < 200,
  });
}
```

### Thresholds
| Metric | Target | Max |
|--------|--------|-----|
| p50 latency | < 100ms | 200ms |
| p95 latency | < 300ms | 500ms |
| p99 latency | < 500ms | 1000ms |
| Error rate | < 0.1% | 1% |
| Throughput | > 500 RPS | — |

### Best Practices
- Run in CI on every PR (smoke) and nightly (full load)
- Profile with `cProfile` / `py-spy` for CPU bottlenecks
- Monitor memory leaks over sustained load
- Test with production-like data volumes

---

## 4. Security Testing

Security tests identify vulnerabilities in code, configs, and dependencies.

### Static Analysis
```bash
# Python
bandit -r src/ -f json -o bandit-report.json
safety check --json

# JS/TS
npm audit --audit-level=high
npx eslint --no-eslintrc --plugin security src/

# General
trivy fs --severity HIGH,CRITICAL .
```

### Dynamic / Runtime
```bash
# OWASP ZAP baseline scan
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t http://localhost:8000

# Fuzz testing (Python)
pytest tests/security/ --fuzz

# Dependency scanning
pip-audit
npm audit fix
```

### Example (Security Test)
```python
# tests/security/test_auth.py
def test_sql_injection_rejected():
    response = client.post("/api/v1/login", json={
        "email": "' OR 1=1; --",
        "password": "anything"
    })
    assert response.status_code == 401

def test_rate_limiting():
    for _ in range(100):
        response = client.get("/api/v1/public")
    assert response.status_code == 429
```

### Checklist
- [ ] Input validation on all endpoints
- [ ] Authentication/authorization enforced
- [ ] Secrets not in source code
- [ ] Dependencies free of known CVEs
- [ ] HTTPS enforced in production
- [ ] Rate limiting on auth endpoints
- [ ] CORS properly configured
- [ ] Security headers (CSP, HSTS, X-Frame-Options)

---

## 5. Test Coverage Report

### Current Coverage
| Module | Line % | Branch % | Status |
|--------|--------|----------|--------|
| `src/pricing` | 92% | 88% | ✅ |
| `src/orders` | 85% | 80% | ✅ |
| `src/customers` | 78% | 72% | ⚠️ |
| `src/auth` | 95% | 90% | ✅ |
| `src/inventory` | 65% | 58% | ❌ |
| `src/notifications` | 45% | 40% | ❌ |
| **Overall** | **76%** | **70%** | ⚠️ |

### Generating Reports
```bash
# Python
pytest --cov=src --cov-report=html --cov-report=xml
# Output: htmlcov/index.html, coverage.xml

# JS/TS
npx vitest run --coverage
# Output: coverage/
```

### Coverage Gates (CI)
```yaml
# .github/workflows/test.yml
- name: Check coverage
  run: |
    pytest --cov=src --cov-fail-under=80
```

### Priorities
1. Bring `src/inventory` to ≥ 80% (critical business logic)
2. Bring `src/notifications` to ≥ 70%
3. Add branch coverage for error handlers
4. Add mutation testing with `mutmut` (Python) or `stryker` (JS)

### Running All Tests
```bash
# Full suite
make test

# Individual suites
make test-unit
make test-integration
make test-perf
make test-security
```
