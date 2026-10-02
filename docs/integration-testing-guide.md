# Integration Testing Guide

## 1. Integration Testing Strategy

### Scope and Goals

Integration tests verify that multiple modules, services, or layers work together correctly. They sit between unit tests (isolated, fast) and end-to-end tests (full system, slow).

**Primary goals:**
- Validate contracts between internal modules (e.g., service ↔ repository ↔ database)
- Catch wiring errors (DI misconfiguration, incorrect interface implementations)
- Verify external service interactions via controlled doubles
- Ensure data flows correctly across layer boundaries

### Test Pyramid Placement

```
         /  E2E  \          ← Few, slow, full stack
        /  Integ  \         ← Moderate count, key paths
       /   Unit    \        ← Many, fast, isolated
```

- **Unit tests** — individual classes/functions with all dependencies mocked
- **Integration tests** — real database, real service layer, mocked external APIs
- **E2E tests** — full HTTP stack, real or containerized dependencies

### What to Test

| Layer Combination | Example |
|---|---|
| Service + Repository | Business logic persists and retrieves correctly |
| Controller + Service | Request parsing, validation, response mapping |
| Event Producer + Consumer | Message serialization, handler invocation |
| Auth + Protected Routes | Token validation, role enforcement |
| Cache + Database | Cache invalidation, fallback reads |

### What NOT to Test

- Third-party library internals (mock them instead)
- Pure unit-testable logic (keep it in unit tests)
- UI rendering details (belong in component/E2E tests)

### Test Naming Convention

```
<module>__<scenario>__<expected outcome>
```

Example: `orders__create_order_with_insufficient_stock__returns_409`

### Running Integration Tests

```bash
# All integration tests
pytest tests/integration/ -v

# Single module
pytest tests/integration/test_orders.py -v

# With coverage
pytest tests/integration/ --cov=src --cov-report=term-missing
```

---

## 2. Test Fixtures

### Database Fixtures

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base

@pytest.fixture(scope="session")
def engine():
    """Create a test database engine once per test session."""
    engine = create_engine("postgresql://test:test@localhost:5432/test_db")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def db_session(engine):
    """Provide a transactional database session per test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
```

### Application Fixtures

```python
@pytest.fixture(scope="session")
def app(engine):
    """Create the FastAPI/Flask app with test config."""
    from app.main import create_app
    app = create_app(config="testing")
    app.dependency_overrides[get_db] = lambda: db_session
    return app

@pytest.fixture()
def client(app):
    """HTTP client for making requests against the app."""
    from fastapi.testclient import TestClient
    return TestClient(app)
```

### Service Fixtures

```python
@pytest.fixture
def order_service(db_session, mock_payment_gateway):
    """Order service with real DB and mocked payment provider."""
    from app.services.order_service import OrderService
    return OrderService(
        db=db_session,
        payment_gateway=mock_payment_gateway,
        event_bus=MockEventBus(),
    )
```

### Fixture Composition Patterns

- **Override dependencies** — use `app.dependency_overrides` to swap real implementations
- **Factory fixtures** — return a callable for creating test entities with defaults
- **Parametrized fixtures** — run the same test against multiple configurations

```python
@pytest.fixture
def make_user(db_session):
    def _make_user(email="test@example.com", role="user", **kwargs):
        user = User(email=email, role=role, **kwargs)
        db_session.add(user)
        db_session.commit()
        return user
    return _make_user
```

---

## 3. Mock Strategies

### When to Mock

| Dependency | Mock? | Strategy |
|---|---|---|
| Database | No | Use real test database (transaction rollback) |
| External HTTP APIs | Yes | `responses` library or `httpx.MockTransport` |
| Message queues | Yes | In-memory fake or `unittest.mock` |
| File storage | Yes | `tmp_path` + local filesystem or mocked S3 client |
| Cache (Redis) | Yes | `fakeredis` or real Redis in Docker |
| Time / randomness | Yes | `freezegun` or inject `Clock` interface |

### Mocking External HTTP Calls

```python
import responses

@responses.activate
def test_payment_processing(order_service):
    responses.add(
        responses.POST,
        "https://api.stripe.com/v1/charges",
        json={"id": "ch_123", "status": "succeeded"},
        status=200,
    )
    result = order_service.process_payment(order_id=1, amount=100.00)
    assert result.status == "succeeded"
```

### Mocking with `unittest.mock`

```python
from unittest.mock import MagicMock, patch

def test_event_published_on_order_created():
    mock_bus = MagicMock()
    service = OrderService(event_bus=mock_bus)
    service.create_order(...)
    mock_bus.publish.assert_called_once_with(
        "order.created",
        {"order_id": ANY, "user_id": ANY},
    )
```

### Mocking Time-Dependent Code

```python
from freezegun import freeze_time

@freeze_time("2026-10-02 12:00:00")
def test_token_expiry():
    token = create_token(ttl=3600)
    assert token.expires_at == datetime(2026, 10, 2, 13, 0, 0)
```

### Mocking Best Practices

1. **Mock at the boundary** — mock the external service client, not internal helpers
2. **Verify interactions sparingly** — assert on outcomes, not call counts, when possible
3. **Use `autospec=True`** — ensures mock signatures match the real interface
4. **Reset mocks between tests** — use `pytest-mock`'s `mocker` fixture for auto-cleanup
5. **Prefer fakes over mocks** — for complex interactions, a lightweight in-memory implementation is more maintainable

---

## 4. Test Data Management

### Principles

- **Isolation** — each test creates and destroys its own data
- **Determinism** — same input always produces same output
- **Minimalism** — create only the data the test needs
- **Readability** — test data should make the test's intent clear

### Factory Pattern

```python
# tests/factories.py
import factory
from app.models import User, Order, Product

class UserFactory(factory.Factory):
    class Meta:
        model = User
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    role = "user"
    is_active = True

class ProductFactory(factory.Factory):
    class Meta:
        model = Product
    name = factory.Sequence(lambda n: f"Product {n}")
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    stock = 100

class OrderFactory(factory.Factory):
    class Meta:
        model = Order
    user = factory.SubFactory(UserFactory)
    status = "pending"
```

### Database Seeding

```python
@pytest.fixture
def seeded_db(db_session):
    """Seed a standard dataset for integration tests."""
    users = UserFactory.create_batch(5, db_session=db_session)
    products = ProductFactory.create_batch(10, db_session=db_session)
    db_session.commit()
    return {"users": users, "products": products}
```

### Data Cleanup Strategies

| Strategy | When to Use |
|---|---|
| Transaction rollback | Default — wrap each test in a transaction that never commits |
| Truncate tables | When tests can't use transactions (e.g., DDL changes) |
| Drop and recreate | Session-scoped — clean slate per test run |
| Unique identifiers | Parallel test runs — avoid collisions with UUIDs or sequences |

### Environment-Specific Data

```python
# tests/conftest.py
def pytest_configure(config):
    env = config.getoption("--env", default="local")
    if env == "ci":
        os.environ["DATABASE_URL"] = "postgresql://test:test@postgres:5432/test_db"
    elif env == "local":
        os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_db"
```

### Sensitive Data

- Never commit real credentials or PII to test fixtures
- Use environment variables or `.env.test` (gitignored) for secrets
- Generate synthetic data with `factory.Faker` or `Faker`

---

## 5. CI Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  integration:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/integration/ \
            -v \
            --tb=short \
            --junitxml=reports/integration.xml \
            --cov=src \
            --cov-report=xml:reports/coverage.xml

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: integration-test-reports
          path: reports/

      - name: Upload coverage
        if: success()
        uses: codecov/codecov-action@v4
        with:
          file: reports/coverage.xml
          flags: integration
```

### CI Best Practices

1. **Service containers** — use GitHub Actions `services:` for databases, caches, queues
2. **Parallel execution** — split tests across jobs with `pytest-split` or `pytest-xdist`
3. **Fail fast** — run linting and unit tests before integration tests
4. **Artifact collection** — always upload test reports and coverage, even on failure
5. **Caching** — cache pip dependencies and Docker layers to reduce CI time
6. **Timeouts** — set reasonable timeouts to catch hung tests
7. **Retry flaky tests** — use `pytest-rerunfailures` for known-flaky integration tests

```bash
# Rerun failed tests up to 2 times
pytest tests/integration/ --reruns 2 --reruns-delay 5
```

### Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: integration-smoke
        name: Integration smoke tests
        entry: pytest tests/integration/test_smoke.py -v
        language: system
        pass_filenames: false
        stages: [push]
```

### Test Result Reporting

- **JUnit XML** — `--junitxml=reports/integration.xml` for CI dashboards
- **Coverage** — fail the build if integration coverage drops below threshold:

```bash
pytest tests/integration/ --cov=src --cov-fail-under=80
```

- **Annotations** — use `pytest-github-actions-annotator` to surface failures in PR comments

---

## Quick Reference

| Task | Command |
|---|---|
| Run all integration tests | `pytest tests/integration/ -v` |
| Run single test file | `pytest tests/integration/test_orders.py -v` |
| Run with coverage | `pytest tests/integration/ --cov=src --cov-report=term-missing` |
| Run in parallel | `pytest tests/integration/ -n auto` |
| Rerun failures | `pytest tests/integration/ --reruns 2` |
| Debug single test | `pytest tests/integration/test_orders.py::test_name -v --pdb` |
